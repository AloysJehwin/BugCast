"""LLMLingua-2 prompt compression with graceful fallback."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_LINGUA_AVAILABLE = False
_PromptCompressor = None

try:
    from llmlingua import PromptCompressor as _PromptCompressor  # type: ignore

    _LINGUA_AVAILABLE = True
except ImportError:
    pass


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token for English-like text)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


class PromptCompressor:
    """Wrap LLMLingua-2 when installed; otherwise use lightweight heuristics."""

    def __init__(self, model_name: str, target_rate: float = 0.25) -> None:
        self.model_name = model_name
        self.target_rate = target_rate
        self._engine = None
        if _LINGUA_AVAILABLE and _PromptCompressor is not None:
            try:
                self._engine = _PromptCompressor(
                    model_name=model_name,
                    use_llmlingua2=True,
                )
            except Exception as exc:  # pragma: no cover - hardware/model dependent
                logger.warning("LLMLingua-2 init failed, using fallback compressor: %s", exc)
                self._engine = None

    @property
    def is_lingua_active(self) -> bool:
        return self._engine is not None

    def compress(self, prompt: str) -> tuple[str, int, int]:
        """
        Compress prompt text.

        Returns:
            (compressed_text, original_token_estimate, compressed_token_estimate)
        """
        original_tokens = estimate_tokens(prompt)
        if not prompt.strip():
            return prompt, 0, 0

        if self._engine is not None:
            try:
                result = self._engine.compress_prompt(
                    prompt,
                    rate=self.target_rate,
                    force_tokens=["##", "json", "title", "body", "labels", "severity"],
                )
                compressed = result.get("compressed_prompt", prompt)
                compressed_tokens = estimate_tokens(compressed)
                return compressed, original_tokens, compressed_tokens
            except Exception as exc:  # pragma: no cover
                logger.warning("LLMLingua-2 compression failed, using fallback: %s", exc)

        compressed = _fallback_compress(prompt, self.target_rate)
        compressed_tokens = estimate_tokens(compressed)
        return compressed, original_tokens, compressed_tokens


def _fallback_compress(prompt: str, target_rate: float) -> str:
    """Deterministic lightweight compression when LLMLingua-2 is unavailable."""
    lines = [line.strip() for line in prompt.splitlines() if line.strip()]
    if not lines:
        return prompt

    keep_every = max(1, int(round(1 / max(target_rate, 0.05))))
    selected: list[str] = []
    for index, line in enumerate(lines):
        if index % keep_every == 0 or _is_high_value_line(line):
            selected.append(line)

    compressed = "\n".join(selected)
    compressed = re.sub(r"[ \t]{2,}", " ", compressed)
    compressed = re.sub(r"\n{3,}", "\n\n", compressed)
    return compressed


def _is_high_value_line(line: str) -> bool:
    lowered = line.lower()
    keywords = ("error", "fail", "exception", "steps", "expected", "actual", "severity", "title", "body")
    return any(keyword in lowered for keyword in keywords)
