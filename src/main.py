"""SLM Triage — main entrypoint.

Reads the GitHub event payload and environment variables, fetches the
project's contribution guidelines from the CONSUMER's repository (not
this action's repo), runs inference via the local Ollama instance, and
takes action on low-quality submissions.

Note: GITHUB_REPOSITORY is always set by GitHub Actions to the repo where
the workflow runs — i.e. the consumer's repo, not the action's source repo.
"""

import fnmatch
import json
import logging
import os
import sys

from github_client import fetch_guidelines, fetch_pr_files, post_comment, add_label
from llm import ask as ask_llm
from prompt import build as build_prompt

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("triage")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_EVENT_PATH = os.environ.get("GITHUB_EVENT_PATH", "")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "phi3")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

# Action inputs (set by action.yml → env)
GUIDELINES_FILE = os.environ.get("INPUT_GUIDELINES_FILE", "AGENTS.md")
TEST_FILE_PATTERN = os.environ.get("INPUT_TEST_FILE_PATTERN", "test_*")
SCORE_THRESHOLD = int(os.environ.get("INPUT_SCORE_THRESHOLD", "2"))
LOW_QUALITY_LABEL = os.environ.get("INPUT_LOW_QUALITY_LABEL", "needs-review/low-quality")


def _get_event_payload() -> dict:
    if GITHUB_EVENT_PATH and os.path.exists(GITHUB_EVENT_PATH):
        with open(GITHUB_EVENT_PATH, "r") as fh:
            return json.load(fh)
    return {}


def _matches_test_pattern(file_paths: list[str], pattern: str) -> bool:
    """Check whether any changed filename matches the test-file glob."""
    return any(fnmatch.fnmatch(os.path.basename(p), pattern) for p in file_paths)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # ------ Test mode -------------------------------------------------------
    test_target = os.environ.get("TEST_PR") or os.environ.get("TEST_ISSUE")
    if test_target:
        is_pr = bool(os.environ.get("TEST_PR"))
        repo_full, number_str = test_target.rsplit(":", 1)
        number = int(number_str)

        log.info(
            "TEST MODE — %s %s#%d",
            "PR" if is_pr else "Issue",
            repo_full,
            number,
        )

        guidelines = fetch_guidelines(GITHUB_TOKEN, repo_full, GUIDELINES_FILE)
        log.info("Guidelines length: %d characters", len(guidelines))

        if is_pr:
            files = fetch_pr_files(GITHUB_TOKEN, repo_full, number)
            log.info("Files changed (%d): %s", len(files), files[:10])
            log.info(
                "Has test files (pattern '%s'): %s",
                TEST_FILE_PATTERN,
                _matches_test_pattern(files, TEST_FILE_PATTERN),
            )

        log.info("Test mode complete — no LLM or write calls made.")
        return

    # ------ Real mode -------------------------------------------------------
    if not GITHUB_TOKEN or not GITHUB_EVENT_PATH or not GITHUB_REPOSITORY:
        log.error("Missing required environment variables.")
        sys.exit(1)

    payload = _get_event_payload()

    is_pr = "pull_request" in payload
    event_data = payload.get("pull_request") if is_pr else payload.get("issue")
    if not event_data:
        log.error("No issue or pull_request found in event payload.")
        sys.exit(0)

    number = event_data["number"]
    title = event_data.get("title", "")
    body = event_data.get("body") or "No description provided."
    author = event_data.get("user", {}).get("login", "unknown")

    # Fetch guidelines
    guidelines = fetch_guidelines(GITHUB_TOKEN, GITHUB_REPOSITORY, GUIDELINES_FILE)

    # Optionally fetch PR file list for lightweight context
    has_tests = None
    file_count = None
    if is_pr:
        files = fetch_pr_files(GITHUB_TOKEN, GITHUB_REPOSITORY, number)
        has_tests = _matches_test_pattern(files, TEST_FILE_PATTERN)
        file_count = len(files)

    # Build prompt and call local LLM
    prompt = build_prompt(
        guidelines=guidelines,
        title=title,
        body=body,
        author=author,
        event_type="pull_request" if is_pr else "issue",
        has_tests=has_tests,
        file_count=file_count,
    )
    log.info("Sending prompt to local LLM (%s)…", OLLAMA_MODEL)
    result = ask_llm(prompt, model=OLLAMA_MODEL, base_url=OLLAMA_URL)

    score = int(result["score"])
    reason = result["reason"]
    log.info("Score: %d/5 — %s", score, reason)

    # Take action on low-quality submissions
    if score <= SCORE_THRESHOLD:
        log.info("Low score detected (threshold: %d) — commenting and labeling.", SCORE_THRESHOLD)
        msg = (
            f"🤖 **Automated AI Triage (Score: {score}/5)**\n\n"
            f"Hi @{author}, thanks for the submission. Our automated triage "
            f"system flagged this as potentially not aligned with our "
            f"contribution guidelines:\n\n"
            f"> {reason}\n\n"
            f"A maintainer will review this shortly. If you believe this is "
            f"a mistake, please leave a comment explaining."
        )
        post_comment(GITHUB_TOKEN, GITHUB_REPOSITORY, number, msg)
        add_label(GITHUB_TOKEN, GITHUB_REPOSITORY, number, LOW_QUALITY_LABEL)


if __name__ == "__main__":
    main()
