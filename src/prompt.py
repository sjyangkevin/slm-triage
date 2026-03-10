import logging
import os

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
        title: str,
        body: str,
        author: str,
        event_type: str,
    ) -> str:
        """Build a complete triage prompt from submission metadata.

        Assemble the submission info block and render the
        ``triage.txt`` template.

        Args:
            title: Submission title.
            body: Submission description / body text.
            author: GitHub username of the submission author.
            event_type: ``"pull_request"`` or ``"issue"``.

        Returns:
            A fully rendered prompt string ready for the LLM.
        """
        submission_info = self._build_submission_info(
            title=title,
            body=body,
            author=author,
            event_type=event_type,
        )
        template_file = (
            "triage_pr.txt" if event_type == "pull_request" else "triage_issue.txt"
        )
        return self.render(
            template_file,
            event_type=event_type,
            submission_info=submission_info,
        )

    def build_reply_message(self, author: str, reason: str, result: str) -> str:
        """Render the automated reply message for failing submissions.

        Args:
            author: GitHub username of the submission author.
            reason: The explanation provided by the LLM.
            result: The string result ("Needs Details").

        Returns:
            The fully formatted Markdown comment ready to be posted.
        """
        return self.render(
            "reply.txt",
            author=author,
            reason=reason,
            result=result,
        )

    @staticmethod
    def _build_submission_info(
        title: str,
        body: str,
        author: str,
        event_type: str,
    ) -> str:
        """Assemble the submission metadata block."""
        info = f"Author: {author}\nTitle: {title}\nDescription:\n{body}"

        return info
