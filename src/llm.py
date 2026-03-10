import json
import logging
import re
from typing import Literal, Optional

import requests
from pydantic import BaseModel, Field

log = logging.getLogger("triage.llm")


class LLMError(RuntimeError):
    """Raised when the local LLM cannot be reached or returns invalid output."""


class TriageResult(BaseModel):
    """The structured output expected from the LLM."""

    result: Literal["Pass", "Needs Details"] = Field(
        ...,
        description='The evaluation result, either "Pass" or "Needs Details".',
    )
    reason: str = Field(
        ...,
        description="A short explanation of why this score was given (1-3 sentences).",
    )


class OllamaClient:
    """Client for the local Ollama REST API.

    Send prompts to a locally running Ollama server and parse the
    response into a structured ``TriageResult`` object.

    Args:
        model: Ollama model tag (e.g. ``"phi3"``).
        base_url: Base URL of the running Ollama server.
    """

    DEFAULT_MODEL = "phi3"
    DEFAULT_URL = "http://localhost:11434"
    REQUEST_TIMEOUT_SEC = 300

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_URL,
        think: bool = False,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.think = think

    def ask(self, prompt: str) -> dict:
        """Send a prompt to Ollama and return a parsed result.

        Uses Ollama's native structured outputs feature by passing the
        Pydantic JSON schema to the ``format`` parameter. This enforces
        that the model output strictly follows the required schema.

        Args:
            prompt: The full prompt string to send.

        Returns:
            A dict with keys ``"result"`` and ``"reason"``.
        """
        url = f"{self.base_url}/api/generate"
        schema = TriageResult.model_json_schema()
        grounded_prompt = self._ground_prompt_with_schema(prompt, schema)

        base_payload = {
            "model": self.model,
            "stream": False,
            "think": self.think,
            "options": {"temperature": 0.0},
        }

        strategies = [
            ("schema", schema, grounded_prompt),
            (
                "json_fallback",
                "json",
                f"{grounded_prompt}\n\nReturn only one JSON object with keys: result (Pass or Needs Details) and reason.",
            ),
        ]

        for name, fmt, text_prompt in strategies:
            payload = {**base_payload, "format": fmt, "prompt": text_prompt}

            try:
                raw = self._call_generate(url, payload)
            except requests.exceptions.RequestException as exc:
                raise LLMError(f"Failed to reach local LLM at {url}: {exc}") from exc

            log.info("Raw LLM response (%s):\n%s", name, raw)

            parsed = self._try_parse_result(raw)
            if parsed is not None:
                return parsed

            log.warning(
                "Model '%s' returned non-parseable output using %s strategy. Retrying...",
                self.model,
                name,
            )
        else:
            raise LLMError(
                "Failed to parse LLM structured output after retries. "
                f"Last raw output: {raw}"
            )

    def _call_generate(self, url: str, payload: dict) -> str:
        """Call Ollama generate API and return raw response text."""
        resp = requests.post(url, json=payload, timeout=self.REQUEST_TIMEOUT_SEC)

        try:
            data = resp.json()
        except ValueError:
            data = {}

        if not resp.ok:
            error_msg = data.get("error", resp.text)
            raise LLMError(f"HTTP {resp.status_code}: {error_msg}")

        return str(data.get("response", "")).strip()

    @staticmethod
    def _ground_prompt_with_schema(prompt: str, schema: dict) -> str:
        """Embed schema constraints into the prompt for weaker instruction followers."""
        return (
            f"{prompt}\n\n"
            "Respond with a single JSON object that matches this schema exactly:\n"
            f"{json.dumps(schema, separators=(',', ':'))}\n"
            "Do not include markdown fences, commentary, or extra keys."
        )

    @staticmethod
    def _try_parse_result(raw: str) -> Optional[dict]:
        """Parse raw model text into a validated TriageResult if possible."""
        for candidate in OllamaClient._json_candidates(raw):
            try:
                return TriageResult.model_validate_json(candidate).model_dump()
            except Exception:
                continue
        return None

    @staticmethod
    def _json_candidates(raw: str) -> list[str]:
        """Yield likely JSON snippets from a model response."""
        candidates = [raw.strip()]

        fenced = re.findall(
            r"```(?:json)?\s*([\s\S]*?)\s*```", raw, flags=re.IGNORECASE
        )
        candidates.extend(chunk.strip() for chunk in fenced)

        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end > start:
            candidates.append(raw[start : end + 1].strip())

        return list(dict.fromkeys(filter(None, candidates)))
