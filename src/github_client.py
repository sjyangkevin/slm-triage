import logging

import requests

log = logging.getLogger("triage.github")


class GitHubClient:
    """Thin wrapper around the GitHub REST API.

    Provides methods for reading repository content and writing
    comments or labels to issues and pull requests.

    Args:
        token: A GitHub personal-access token or ``GITHUB_TOKEN`` value.
    """

    API_BASE = "https://api.github.com"

    def __init__(self, token: str) -> None:
        self._token = token
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def fetch_guidelines(self, repo: str, filepath: str) -> str:
        """Fetch raw file content from a repository.

        Use the Contents API with a raw media-type header so the
        response body is plain text rather than base64-encoded JSON.

        If the file does not exist (404), return a sensible fallback
        string instead of raising.

        Args:
            repo: Repository in ``owner/name`` format.
            filepath: Path to the file within the repository.

        Returns:
            The raw text content of the requested file, or a fallback
            message when the file is not found.

        Reference:
            https://docs.github.com/en/rest/repos/contents#get-repository-content
        """
        url = f"{self.API_BASE}/repos/{repo}/contents/{filepath}"
        headers = {**self._headers, "Accept": "application/vnd.github.v3.raw"}

        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                log.warning("%s not found in repository %s.", filepath, repo)
                return (
                    f"No {filepath} found. Evaluate based on general "
                    "open-source contribution best practices."
                )
            raise

    def fetch_pr_files(self, repo: str, pr_number: int) -> list[str]:
        """Return filenames changed in a pull request.

        Args:
            repo: Repository in ``owner/name`` format.
            pr_number: Pull request number.

        Returns:
            A list of file paths modified by the pull request.

        Reference:
            https://docs.github.com/en/rest/pulls/pulls#list-pull-requests-files
        """
        url = f"{self.API_BASE}/repos/{repo}/pulls/{pr_number}/files"
        resp = requests.get(url, headers=self._headers, timeout=30)
        resp.raise_for_status()
        return [f["filename"] for f in resp.json()]

    def post_comment(self, repo: str, number: int, body: str) -> None:
        """Post a comment on an issue or pull request.

        Args:
            repo: Repository in ``owner/name`` format.
            number: Issue or pull request number.
            body: Markdown-formatted comment body.
        """
        url = f"{self.API_BASE}/repos/{repo}/issues/{number}/comments"
        resp = requests.post(
            url,
            headers=self._headers,
            json={"body": body},
            timeout=15,
        )
        resp.raise_for_status()
        log.info("Comment posted on #%d.", number)

    def add_label(self, repo: str, number: int, label: str) -> None:
        """Add a label to an issue or pull request.

        Args:
            repo: Repository in ``owner/name`` format.
            number: Issue or pull request number.
            label: Label name to apply.
        """
        url = f"{self.API_BASE}/repos/{repo}/issues/{number}/labels"
        resp = requests.post(
            url,
            headers=self._headers,
            json={"labels": [label]},
            timeout=15,
        )
        resp.raise_for_status()
        log.info("Label '%s' added to #%d.", label, number)

    def close_issue(self, repo: str, number: int) -> None:
        """Close an issue or pull request.

        Args:
            repo: Repository in ``owner/name`` format.
            number: Issue or pull request number.
        """
        url = f"{self.API_BASE}/repos/{repo}/issues/{number}"
        resp = requests.patch(
            url,
            headers=self._headers,
            json={"state": "closed"},
            timeout=15,
        )
        resp.raise_for_status()
        log.info("Closed #%d.", number)
