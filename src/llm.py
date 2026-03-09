"""Local LLM interaction via Ollama for the AI Triage Assistant."""

import json
import logging

import requests

log = logging.getLogger("triage.llm")

DEFAULT_URL = "http://localhost:11434"
DEFAULT_MODEL = "phi3"


def ask(
    prompt: str,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_URL,
) -> dict:
    """Send *prompt* to the local Ollama instance and return a parsed result.

    Returns a dict with ``"score"`` (int 1-5) and ``"reason"`` (str).
    Falls back gracefully if the model does not return valid JSON.
    """
    url = f"{base_url}/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": False}

    try:
        resp = requests.post(url, json=payload, timeout=300)
        resp.raise_for_status()
        raw = resp.json().get("response", "").strip()
    except requests.exceptions.RequestException as exc:
        log.error("Failed to reach local LLM: %s", exc)
        return {"score": 3, "reason": "Could not reach LLM engine."}

    log.info("Raw LLM response:\n%s", raw)
    return _parse_response(raw)


def _parse_response(raw: str) -> dict:
    """Try JSON first, then fall back to first-digit extraction."""
    # Strip markdown fences if the model wraps output in ```json ... ```
    cleaned = raw.strip("`").removeprefix("json").strip()
    try:
        result = json.loads(cleaned)
        if "score" in result and "reason" in result:
            return result
    except json.JSONDecodeError:
        pass

    log.warning("LLM did not return valid JSON. Attempting fallback parsing.")
    for ch in raw:
        if ch.isdigit() and 1 <= int(ch) <= 5:
            return {"score": int(ch), "reason": raw}

    return {"score": 3, "reason": raw}
