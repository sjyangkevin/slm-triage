"""Unit tests for GitHub client configuration."""

from github_client import GitHubClient


def test_github_client_omits_auth_header_without_token():
    """Public read-only API calls should work without an auth header."""
    client = GitHubClient("")

    assert "Authorization" not in client._headers


def test_github_client_sets_auth_header_with_token():
    """Authenticated calls should include the bearer token."""
    client = GitHubClient("secret")

    assert client._headers["Authorization"] == "Bearer secret"
