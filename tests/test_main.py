"""Unit tests for the main application logic."""

import os
from unittest.mock import MagicMock, patch

import pytest

from llm import LLMError
from main import TriageAction


@pytest.fixture
def mock_env():
    """Set up environment variables required by the action."""
    env_vars = {
        "GITHUB_TOKEN": "dummy_token",
        "GITHUB_EVENT_PATH": "/tmp/mock_event.json",
        "GITHUB_REPOSITORY": "octocat/Hello-World",
        "INPUT_REVIEW_LABEL": "needs-details",
    }
    with patch.dict(os.environ, env_vars):
        yield


@pytest.fixture
def mock_action(mock_env):
    """Return a TriageAction instance with mocked out collaborators."""
    action = TriageAction()
    # Replace external service clients with mocks
    action.github = MagicMock()
    action.llm = MagicMock()
    action.prompt_builder = MagicMock()
    # Mock event payload loading so we don't need real disk files
    action._load_event_payload = MagicMock()
    return action


def test_missing_env_vars_exits(mock_action):
    """If core env vars are missing, the action exits."""
    mock_action.event_path = ""
    with pytest.raises(SystemExit) as exc_info:
        mock_action.run()
    assert exc_info.value.code == 1


def test_issue_triage_runs_without_token_in_read_only_mode(mock_action):
    """A token is not required to score an issue when no write action runs."""
    mock_action.github_token = ""
    mock_action._load_event_payload.return_value = {
        "issue": {
            "number": 7,
            "title": "Closed issue",
            "body": "Still useful for triage tests.",
            "user": {"login": "reporter"},
        }
    }
    mock_action.llm.ask.return_value = {"result": "Pass", "reason": "Enough detail."}

    result = mock_action.run()

    assert result["event_type"] == "issue"
    assert result["result"] == "Pass"
    mock_action.github.post_comment.assert_not_called()
    mock_action.github.add_label.assert_not_called()


def test_triage_exits_if_llm_is_unreachable(mock_action):
    """The action should fail loudly when the local LLM is unavailable."""
    mock_action._load_event_payload.return_value = {
        "issue": {
            "number": 8,
            "title": "Issue",
            "body": "Body",
            "user": {"login": "reporter"},
        }
    }
    mock_action.prompt_builder.build_triage_prompt.return_value = "Rendered prompt"
    mock_action.llm.ask.side_effect = LLMError("local llm unavailable")

    with pytest.raises(SystemExit) as exc_info:
        mock_action.run()

    assert exc_info.value.code == 1


def test_triage_skips_if_high_score(mock_action):
    """If the LLM returns a high score, no comment or label is added."""
    # Setup standard PR payload
    mock_action._load_event_payload.return_value = {
        "pull_request": {
            "number": 42,
            "title": "Good PR",
            "body": "Fixes everything properly.",
            "user": {"login": "good_user"},
        }
    }
    mock_action.prompt_builder.build_triage_prompt.return_value = "Rendered prompt"

    # LLM returns a "passing" score
    mock_action.llm.ask.return_value = {"result": "Pass", "reason": "Looks great."}

    # Run the triage action
    mock_action.run()

    # Verify no action taken
    mock_action.github.post_comment.assert_not_called()
    mock_action.github.add_label.assert_not_called()


def test_triage_acts_if_low_score(mock_action):
    """If the LLM returns a low score, a comment and label are added."""
    # Setup low-quality PR payload
    mock_action._load_event_payload.return_value = {
        "pull_request": {
            "number": 99,
            "title": "Fix",
            "body": "",
            "user": {"login": "lazy_user"},
        }
    }
    # LLM returns a "failing" score
    mock_action.llm.ask.return_value = {
        "result": "Needs Details",
        "reason": "No description.",
    }
    mock_action.prompt_builder.build_reply_message.return_value = "mocked reply body"

    # Run the triage action
    mock_action.run()

    # Verify action taken
    mock_action.prompt_builder.build_reply_message.assert_called_once_with(
        author="lazy_user", reason="No description.", result="Needs Details"
    )
    mock_action.github.post_comment.assert_called_once_with(
        "octocat/Hello-World", 99, "mocked reply body"
    )
    mock_action.github.add_label.assert_called_once_with(
        "octocat/Hello-World", 99, "needs-details"
    )


def test_triage_custom_actions(mock_action):
    """If configured, the action can perform different steps, like closing the issue."""
    # Override configured actions
    mock_action.actions = ["close", "unknown_action"]

    # Setup low-quality Issue payload
    mock_action._load_event_payload.return_value = {
        "issue": {
            "number": 101,
            "title": "Bad issue",
            "body": "",
            "user": {"login": "spammer"},
        }
    }
    # LLM returns a "failing" score
    mock_action.llm.ask.return_value = {"result": "Needs Details", "reason": "Spam."}

    # Run triage
    mock_action.run()

    # Verify 'close' was the only real API invoked
    mock_action.github.post_comment.assert_not_called()
    mock_action.github.add_label.assert_not_called()
    mock_action.github.close_issue.assert_called_once_with("octocat/Hello-World", 101)
