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
            "Accept": "application/vnd.github.v3+json",
        }
        if token:
            self._headers["Authorization"] = f"Bearer {token}"

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

    def fetch_issue(self, repo: str, number: int) -> dict:
        """Fetch issue or pull request data by number.

        Args:
            repo: Repository in ``owner/name`` format.
            number: Issue or pull request number.

        Returns:
            A dict containing at least ``title``, ``body``, ``user``,
            and ``pull_request`` (if the item is a PR).

        Reference:
            https://docs.github.com/en/rest/issues/issues#get-an-issue
        """
        url = f"{self.API_BASE}/repos/{repo}/issues/{number}"
        resp = requests.get(url, headers=self._headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
