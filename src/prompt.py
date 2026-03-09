"""Prompt construction for the AI Triage Assistant."""


def build(
    guidelines: str,
    title: str,
    body: str,
    author: str,
    event_type: str,
    has_tests: bool | None = None,
    file_count: int | None = None,
) -> str:
    """Return a structured prompt for the local LLM.

    Parameters
    ----------
    guidelines : str
        Raw text content of the project's guidelines file.
    title, body, author : str
        Metadata from the Issue or Pull Request.
    event_type : str
        ``"pull_request"`` or ``"issue"``.
    has_tests : bool | None
        Whether the PR includes test-file changes (None for issues).
    file_count : int | None
        Number of files changed in the PR (None for issues).
    """
    submission_info = f"Author: {author}\nTitle: {title}\nDescription:\n{body}"

    if event_type == "pull_request" and file_count is not None:
        submission_info += (
            f"\n\nThis is a Pull Request that modifies {file_count} files."
        )
        if has_tests is not None:
            submission_info += (
                f"\nIncludes test file changes: {'YES' if has_tests else 'NO'}"
            )

    return f"""You are an expert open-source maintainer. Your job is to
evaluate whether a new {event_type} submission follows the project's
contribution guidelines.

=== PROJECT GUIDELINES ===
{guidelines}
=== END GUIDELINES ===

=== SUBMISSION ===
{submission_info}
=== END SUBMISSION ===

Instructions:
1. Compare the submission's title and description against the guidelines.
2. Provide a quality score from 1 to 5:
   1 = spam / clearly AI-generated slop / violates guidelines
   2 = low quality / missing required information
   3 = acceptable but could be improved
   4 = good, follows most guidelines
   5 = excellent, fully aligned with guidelines
3. Return your answer as a JSON object with exactly two keys:
   "score" (integer 1-5) and "reason" (string, 1-3 sentences).

Respond with ONLY the JSON object, nothing else.
"""
