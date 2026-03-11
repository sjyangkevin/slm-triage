#!/usr/bin/env python3
"""Read-only CLI for testing SLM Triage against a public GitHub issue or PR.

Prerequisites:
    - Ollama running locally: ``ollama serve``
    - Model pulled: ``ollama pull phi3``
    - (Optional but recommended) GITHUB_TOKEN env var set for higher API rate limits

Usage:
    uv run scripts/simulate_triage.py <owner/repo> <number> [options]

Examples:
    uv run scripts/simulate_triage.py myorg/myrepo 42
    uv run scripts/simulate_triage.py myorg/myrepo 42 --model phi3
    uv run scripts/simulate_triage.py myorg/myrepo 42 --model deepseek-r1 --think
"""

import argparse
import json
import logging
import os
import sys
import tempfile

# Add the src/ directory to the path so we can import the action modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from github_client import GitHubClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("simulate_triage")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test SLM Triage locally against a public GitHub issue or PR.",
    )
    parser.add_argument("repo", help="GitHub repository (e.g., curl/curl)")
    parser.add_argument("number", type=int, help="Issue or PR number")
    parser.add_argument(
        "--model",
        default="gemma3",
        help="Ollama model to use (default: gemma3)",
    )
    parser.add_argument(
        "--think",
        action="store_true",
        help="Whether the model natively supports reasoning outputs (e.g. deepseek-r1)",
    )
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        log.warning(
            "GITHUB_TOKEN not set. Public repo access works but rate limits are strict."
        )

    # Fetch data from GitHub to construct the mock payload
    gh = GitHubClient(token)

    log.info("Fetching %s#%d to build local test payload...", args.repo, args.number)
    issue_data = gh.fetch_issue(args.repo, args.number)

    is_pr = "pull_request" in issue_data
    event_name = "pull_request" if is_pr else "issue"

    # Mock payload required by TriageAction._load_event_payload() and PR checking via GitHub API
    mock_payload = {
        event_name: {
            "number": args.number,
            "title": issue_data.get("title", ""),
            "body": issue_data.get("body", ""),
            "user": {"login": issue_data.get("user", {}).get("login", "unknown")},
        }
    }

    # Set up the mock GitHub Actions runtime environment
    # Write the JSON to a scratch file and point `GITHUB_EVENT_PATH` to it
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tf:
        json.dump(mock_payload, tf)
        event_path = tf.name

    try:
        # Override environment variables to emulate action.yml exactly
        os.environ["GITHUB_EVENT_PATH"] = event_path
        os.environ["GITHUB_REPOSITORY"] = args.repo
        # Use default actions. Since dry_run is True, nothing will be posted.
        os.environ["INPUT_ACTIONS"] = "comment,label"
        os.environ["OLLAMA_MODEL"] = args.model
        os.environ["OLLAMA_THINK"] = str(args.think).lower()

        # IMPORTANT: Import TriageAction *after* setting the environment variables,
        # so its `__init__` parses the mock values correctly.
        from main import TriageAction

        log.info("Starting TriageAction (DRY RUN MODE)...")
        print("\n" + "=" * 60)

        # Execute exactly how GitHub Actions would, but pass dry_run=True to intercept API writes.
        action = TriageAction(dry_run=True)
        result = action.run()

        print(f"{result['event_type']} {args.repo}#{args.number}")
        print(f"Result: {result['result']}")
        print(f"Reason: {result['reason']}")
        print(
            "Would apply actions: " + ("yes" if result["would_apply_actions"] else "no")
        )

        print("=" * 60)
        print("  (Read-only mode — no actions were taken on GitHub)")
        print("=" * 60 + "\n")

    finally:
        # Clean up the mock payload file
        if os.path.exists(event_path):
            os.remove(event_path)


if __name__ == "__main__":
    main()
