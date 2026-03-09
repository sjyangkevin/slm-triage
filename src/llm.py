import logging

import requests
from pydantic import BaseModel, Field

log = logging.getLogger("triage.llm")


class TriageResult(BaseModel):
    """The structured output expected from the LLM."""

    score: int = Field(
        ...,
        description="A quality score from 1 to 5.",
        ge=1,
        le=5,
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

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_URL,
    ) -> None:
        self.model = model
        self.base_url = base_url

    def ask(self, prompt: str) -> dict:
        """Send a prompt to Ollama and return a parsed result.

        Uses Ollama's native structured outputs feature by passing the
        Pydantic JSON schema to the ``format`` parameter. This enforces
        that the model output strictly follows the required schema.

        Args:
            prompt: The full prompt string to send.

        Returns:
            A dict with keys ``"score"`` and ``"reason"``.
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": TriageResult.model_json_schema(),
            "options": {"temperature": 0.0},
        }

        try:
            resp = requests.post(url, json=payload, timeout=300)
            resp.raise_for_status()
            raw = resp.json().get("response", "").strip()
        except requests.exceptions.RequestException as exc:
            log.error("Failed to reach local LLM: %s", exc)
            return {"score": 3, "reason": "Could not reach LLM engine."}

        log.info("Raw LLM response:\n%s", raw)

        try:
            # The output uses the Pydantic schema, so it is guaranteed to parse.
            return TriageResult.model_validate_json(raw).model_dump()
        except Exception as exc:
            log.error("Failed to parse validated JSON from LLM: %s", exc)
            return {"score": 3, "reason": "Failed to parse LLM structured output."}
