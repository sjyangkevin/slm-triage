import fnmatch
import json
import logging
import os
import sys

from github_client import GitHubClient
from llm import OllamaClient
from prompt import PromptBuilder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("triage")


class TriageAction:
    """Orchestrate the SLM triage workflow.

    Read configuration from environment variables, wire up the
    collaborating services, and run either test-mode or real-mode
    depending on the presence of ``TEST_PR`` / ``TEST_ISSUE``.
    """

    def __init__(self) -> None:
        # Core GitHub Actions environment variables.
        self.github_token = os.environ.get("GITHUB_TOKEN", "")
        self.event_path = os.environ.get("GITHUB_EVENT_PATH", "")
        self.repository = os.environ.get("GITHUB_REPOSITORY", "")

        # Action inputs forwarded as env vars by action.yml.
        self.guidelines_file = os.environ.get("INPUT_GUIDELINES_FILE", "AGENTS.md")
        self.test_file_pattern = os.environ.get("INPUT_TEST_FILE_PATTERN", "test_*")
        self.score_threshold = int(os.environ.get("INPUT_SCORE_THRESHOLD", "2"))
        self.review_label = os.environ.get(
            "INPUT_REVIEW_LABEL", "needs-details"
        )
        actions_str = os.environ.get("INPUT_ACTIONS", "comment,label")
        self.actions = [a.strip().lower() for a in actions_str.split(",") if a.strip()]

        # Collaborating services.
        self.github = GitHubClient(self.github_token)
        self.llm = OllamaClient(
            model=os.environ.get("OLLAMA_MODEL", "phi3"),
            base_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
        )
        self.prompt_builder = PromptBuilder()

    def run(self) -> None:
        """Execute full triage: fetch → score → act."""
        if not self.github_token or not self.event_path or not self.repository:
            log.error("Missing required environment variables.")
            sys.exit(1)

        payload = self._load_event_payload()

        is_pr = "pull_request" in payload
        event_data = payload.get("pull_request") if is_pr else payload.get("issue")
        if not event_data:
            log.error("No issue or pull_request found in event payload.")
            sys.exit(0)

        number = event_data["number"]
        title = event_data.get("title", "")
        body = event_data.get("body") or "No description provided."
        author = event_data.get("user", {}).get("login", "unknown")

        guidelines = self.github.fetch_guidelines(self.repository, self.guidelines_file)

        # Gather lightweight PR metadata for context.
        has_tests = None
        file_count = None
        if is_pr:
            files = self.github.fetch_pr_files(self.repository, number)
            has_tests = self._matches_test_pattern(files)
            file_count = len(files)

        prompt = self.prompt_builder.build_triage_prompt(
            guidelines=guidelines,
            title=title,
            body=body,
            author=author,
            event_type="pull_request" if is_pr else "issue",
            has_tests=has_tests,
            file_count=file_count,
        )
        log.info("Sending prompt to local LLM (%s)…", self.llm.model)
        result = self.llm.ask(prompt)

        score = int(result["score"])
        reason = result["reason"]
        log.info("Score: %d/5 — %s", score, reason)

        if score <= self.score_threshold:
            self._handle_low_score(number, author, score, reason, is_pr=is_pr)

    def _handle_low_score(
        self, number: int, author: str, score: int, reason: str, *, is_pr: bool
    ) -> None:
        """Apply configured actions to a submission that needs more details."""
        log.info(
            "Score (%d) is at or below threshold (%d) — applying actions: %s",
            score,
            self.score_threshold,
            self.actions,
        )
        msg = self.prompt_builder.build_reply_message(
            author=author, reason=reason, score=score
        )
        
        for action in self.actions:
            if action == "comment":
                self.github.post_comment(self.repository, number, msg)
            elif action == "label":
                self.github.add_label(self.repository, number, self.review_label)
            elif action == "close":
                self.github.close_issue(self.repository, number)
            else:
                log.warning("Unknown action configured: '%s'. Skipping.", action)

    def _load_event_payload(self) -> dict:
        """Load the GitHub event JSON from disk."""
        if self.event_path and os.path.exists(self.event_path):
            with open(self.event_path, "r") as fh:
                return json.load(fh)
        return {}

    def _matches_test_pattern(self, file_paths: list[str]) -> bool:
        """Check whether any filename matches the test-file glob."""
        return any(
            fnmatch.fnmatch(os.path.basename(p), self.test_file_pattern)
            for p in file_paths
        )


if __name__ == "__main__":
    TriageAction().run()
