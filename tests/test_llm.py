"""Unit tests for the Ollama client."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from llm import LLMError, OllamaClient


def test_ask_raises_if_ollama_is_unreachable():
    """Connection errors should fail the run instead of inventing a score."""
    client = OllamaClient()

    with patch(
        "llm.requests.post", side_effect=requests.exceptions.ConnectionError("boom")
    ):
        with pytest.raises(LLMError, match="Failed to reach local LLM"):
            client.ask("prompt")


def test_ask_raises_if_structured_output_is_invalid():
    """Invalid structured output should fail clearly."""
    client = OllamaClient()
    response1 = MagicMock()
    response1.raise_for_status.return_value = None
    response1.json.return_value = {"response": "not json"}

    response2 = MagicMock()
    response2.raise_for_status.return_value = None
    response2.json.return_value = {"response": "still not json"}

    with patch("llm.requests.post", side_effect=[response1, response2]):
        with pytest.raises(
            LLMError, match="Failed to parse LLM structured output after retries"
        ):
            client.ask("prompt")


def test_ask_parses_json_wrapped_in_markdown_fence():
    """Some models return fenced JSON; the client should still parse it."""
    client = OllamaClient()
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "response": '```json\n{"score": 3, "reason": "Needs tests."}\n```'
    }

    with patch("llm.requests.post", return_value=response):
        result = client.ask("prompt")

    assert result == {"score": 3, "reason": "Needs tests."}


def test_ask_retries_with_json_format_if_first_attempt_is_invalid():
    """If schema mode fails, the client retries once in plain JSON mode."""
    client = OllamaClient()
    bad = MagicMock()
    bad.raise_for_status.return_value = None
    bad.json.return_value = {"response": "I cannot follow that format"}

    good = MagicMock()
    good.raise_for_status.return_value = None
    good.json.return_value = {"response": '{"score": 4, "reason": "Looks good."}'}

    with patch("llm.requests.post", side_effect=[bad, good]) as post:
        result = client.ask("prompt")

    assert result == {"score": 4, "reason": "Looks good."}
    assert post.call_count == 2
    assert post.call_args_list[1].kwargs["json"]["format"] == "json"
