"""GitHub REST API client for the AI Triage Assistant."""

import logging

import requests

log = logging.getLogger("triage.github")


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def fetch_guidelines(token: str, repo: str, filepath: str) -> str:
    """Fetch a file's raw content from the repository via the Contents API.

    Reference: https://docs.github.com/en/rest/repos/contents#get-repository-content
    """
    url = f"https://api.github.com/repos/{repo}/contents/{filepath}"
    headers = _headers(token)
    headers["Accept"] = "application/vnd.github.v3.raw"

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.text
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            log.warning("%s not found in repository %s.", filepath, repo)
            return (
                f"No {filepath} found. Evaluate based on general open-source "
                "contribution best practices."
            )
        raise


def fetch_pr_files(token: str, repo: str, pr_number: int) -> list[str]:
    """Return the list of filenames changed in a pull request.

    Reference: https://docs.github.com/en/rest/pulls/pulls#list-pull-requests-files
    """
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    resp = requests.get(url, headers=_headers(token), timeout=30)
    resp.raise_for_status()
    return [f["filename"] for f in resp.json()]


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def post_comment(token: str, repo: str, number: int, body: str):
    """Post a comment on an Issue or Pull Request."""
    url = f"https://api.github.com/repos/{repo}/issues/{number}/comments"
    resp = requests.post(
        url, headers=_headers(token), json={"body": body}, timeout=15,
    )
    resp.raise_for_status()
    log.info("Comment posted on #%d.", number)


def add_label(token: str, repo: str, number: int, label: str):
    """Add a label to an Issue or Pull Request."""
    url = f"https://api.github.com/repos/{repo}/issues/{number}/labels"
    resp = requests.post(
        url, headers=_headers(token), json={"labels": [label]}, timeout=15,
    )
    resp.raise_for_status()
    log.info("Label '%s' added to #%d.", label, number)
