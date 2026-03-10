import json
import logging
import os
import sys

from github_client import GitHubClient
from llm import LLMError, OllamaClient
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

    def __init__(self, *, dry_run: bool = False) -> None:
        # Core GitHub Actions environment variables.
        self.github_token = os.environ.get("GITHUB_TOKEN", "")
        self.event_path = os.environ.get("GITHUB_EVENT_PATH", "")
        self.repository = os.environ.get("GITHUB_REPOSITORY", "")

        # Action inputs forwarded as env vars by action.yml.
        self.review_label = os.environ.get("INPUT_REVIEW_LABEL", "needs-details")
        actions_str = os.environ.get("INPUT_ACTIONS", "comment,label")
        self.actions = [a.strip().lower() for a in actions_str.split(",") if a.strip()]

        self.include_pr_diff = os.environ.get("INPUT_INCLUDE_PR_DIFF", "true").lower() == "true"

        # Collaborating services.
        self.github = GitHubClient(self.github_token)
        self.llm = OllamaClient(
            model=os.environ.get("OLLAMA_MODEL", "phi3"),
            base_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
            think=os.environ.get("OLLAMA_THINK", "false").lower() == "true",
        )
        self.prompt_builder = PromptBuilder()
        self.dry_run = dry_run

    def run(self) -> dict:
        """Execute full triage: fetch → score → act."""
        if not self.event_path or not self.repository:
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

        diff_text = ""
        if is_pr and self.include_pr_diff:
            diff_text = self.github.fetch_pr_diff(self.repository, number)

        prompt = self.prompt_builder.build_triage_prompt(
            title=title,
            body=body,
            author=author,
            event_type="pull_request" if is_pr else "issue",
            diff=diff_text,
        )
        
        if self.dry_run:
            log.info("=== DEBUG: Generated Prompt ===\n%s\n===============================", prompt)

        log.info("Sending prompt to local LLM (%s)…", self.llm.model)
        try:
            result = self.llm.ask(prompt)
        except LLMError as exc:
            log.error("%s", exc)
            sys.exit(1)

        triage_result = result["result"]
        reason = result["reason"]
        log.info("Result: %s — %s", triage_result, reason)

        if triage_result == "Needs Details":
            self._apply_actions(number, author, triage_result, reason, is_pr=is_pr)

        return {
            "number": number,
            "event_type": "pull_request" if is_pr else "issue",
            "result": triage_result,
            "reason": reason,
            "would_apply_actions": triage_result == "Needs Details",
        }

    def _apply_actions(
        self, number: int, author: str, triage_result: str, reason: str, *, is_pr: bool
    ) -> None:
        """Apply configured actions to a submission that needs more details."""
        log.info(
            "Result (%s) is Needs Details — applying actions: %s",
            triage_result,
            self.actions,
        )

        if self.dry_run:
            log.info("[DRY RUN] Would apply actions: %s", self.actions)
            return

        if not self.github_token:
            log.error("GITHUB_TOKEN is required to apply GitHub actions.")
            sys.exit(1)

        msg = self.prompt_builder.build_reply_message(
            author=author, reason=reason, event_type="pull_request" if is_pr else "issue"
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


if __name__ == "__main__":
    TriageAction().run()
