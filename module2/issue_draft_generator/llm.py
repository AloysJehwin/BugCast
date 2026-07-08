"""Ollama LLM client with JSON mode enforcement."""

from __future__ import annotations

import json
import logging
from typing import Any

import ollama

from issue_draft_generator.models import IssueDraft

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Raised when Ollama inference fails or returns invalid JSON."""


class OllamaClient:
    """Connect to Ollama and invoke local models with optional JSON mode."""

    def __init__(
        self,
        *,
        host: str = "http://localhost:11434",
        model: str = "qwen2.5:7b-instruct",
        temperature: float = 0.0,
        timeout_seconds: int = 180,
    ) -> None:
        self.host = host
        self.model = model
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self._client = ollama.Client(host=host, timeout=timeout_seconds)

    def generate_issue_draft(self, prompt: str, *, json_mode: bool = True) -> IssueDraft:
        """Single LLM call to produce a structured GitHub issue draft."""
        options: dict[str, Any] = {"temperature": self.temperature}
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "options": options,
        }
        if json_mode:
            kwargs["format"] = "json"

        try:
            response = self._client.chat(**kwargs)
        except Exception as exc:
            raise LLMError(f"Ollama request failed: {exc}") from exc

        content = _extract_content(response)
        payload = _parse_json_payload(content)
        try:
            return IssueDraft.model_validate(payload)
        except Exception as exc:
            raise LLMError(f"Model output failed schema validation: {exc}") from exc

    def is_available(self) -> bool:
        """Check whether Ollama is reachable and the configured model is present."""
        try:
            models = self._client.list()
            available = {model.model for model in models.models}
            if self.model in available:
                return True
            # Allow partial name match (e.g. qwen2.5:7b-instruct-q4_0)
            return any(self.model in name or name in self.model for name in available)
        except Exception:
            return False


def _extract_content(response: dict[str, Any]) -> str:
    message = response.get("message") or {}
    content = message.get("content")
    if not content:
        raise LLMError("Ollama returned empty content")
    return str(content).strip()


def _parse_json_payload(content: str) -> dict[str, Any]:
    """Parse JSON from model output, stripping optional markdown fences."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Model output is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise LLMError("Model JSON output must be an object")
    return payload
