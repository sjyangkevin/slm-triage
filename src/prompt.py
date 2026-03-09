import logging
import os
from typing import Optional

log = logging.getLogger("triage.prompt")

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


class PromptBuilder:
    """Handles rendering of LLM prompts from text templates.

    Args:
        template_dir: Directory containing ``.txt`` template files.
            Defaults to the ``templates/`` sibling directory.
    """

    def __init__(self, template_dir: str = _TEMPLATE_DIR) -> None:
        self._template_dir = template_dir

    def render(self, template_name: str, **context: object) -> str:
        """Read a template from disk and substitute placeholders.

        Args:
            template_name: Filename inside the templates directory
                (e.g. ``"triage.txt"``).
            **context: Key/value pairs to substitute into the template.

        Returns:
            The rendered template string.
        """
        path = os.path.join(self._template_dir, template_name)
        with open(path, "r") as fh:
            template = fh.read()
        return template.format_map(context)

    def build_triage_prompt(
        self,
        guidelines: str,
        title: str,
        body: str,
        author: str,
        event_type: str,
        has_tests: Optional[bool] = None,
        file_count: Optional[int] = None,
    ) -> str:
        """Build a complete triage prompt from submission metadata.

        Assemble the submission info block (with optional PR file
        statistics) and render the ``triage.txt`` template.

        Args:
            guidelines: Raw text of the project's contribution guidelines.
            title: Submission title.
            body: Submission description / body text.
            author: GitHub username of the submission author.
            event_type: ``"pull_request"`` or ``"issue"``.
            has_tests: Whether the PR modifies test files (``None`` for
                issues).
            file_count: Number of files changed (``None`` for issues).

        Returns:
            A fully rendered prompt string ready for the LLM.
        """
        submission_info = self._build_submission_info(
            title=title,
            body=body,
            author=author,
            event_type=event_type,
            has_tests=has_tests,
            file_count=file_count,
        )
        return self.render(
            "triage.txt",
            guidelines=guidelines,
            event_type=event_type,
            submission_info=submission_info,
        )

    def build_reply_message(self, author: str, reason: str, score: int) -> str:
        """Render the automated reply message for low-scoring submissions.

        Args:
            author: GitHub username of the submission author.
            reason: The explanation provided by the LLM.
            score: The 1-5 triage score.

        Returns:
            The fully formatted Markdown comment ready to be posted.
        """
        assessment = (
            "Potential spam, low-effort, or AI-generated content detected."
            if score == 1
            else "Submission lacks required details or context."
        )
        return self.render(
            "reply.txt",
            author=author,
            reason=reason,
            score=score,
            assessment=assessment,
        )

    @staticmethod
    def _build_submission_info(
        title: str,
        body: str,
        author: str,
        event_type: str,
        has_tests: Optional[bool] = None,
        file_count: Optional[int] = None,
    ) -> str:
        """Assemble the submission metadata block."""
        info = f"Author: {author}\nTitle: {title}\nDescription:\n{body}"

        if event_type == "pull_request" and file_count is not None:
            info += f"\n\nThis is a Pull Request that modifies {file_count} files."
            if has_tests is not None:
                info += f"\nIncludes test file changes: {'YES' if has_tests else 'NO'}"

        return info
