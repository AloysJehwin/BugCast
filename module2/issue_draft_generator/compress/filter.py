"""Frame filtering to remove low-value OCR frames before prompt creation."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from issue_draft_generator.models import Frame, Module1Document


NOISE_PATTERNS = (
    re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$"),
    re.compile(r"^[\W_]+$"),
    re.compile(r"^(ok|cancel|x|close|back|next|done)$", re.IGNORECASE),
)


def _is_noise_text(text: str, min_chars: int) -> bool:
    cleaned = text.strip()
    if len(cleaned) < min_chars:
        return True
    return any(pattern.match(cleaned) for pattern in NOISE_PATTERNS)


def _frame_text_blob(frame: Frame) -> str:
    ocr_parts = [t.strip() for t in frame.ocr_text if t.strip()]
    ui_parts = [el.text.strip() for el in frame.ui_elements if el.text.strip()]
    return " ".join(ocr_parts + ui_parts).lower()


def _frame_score(frame: Frame, min_ocr_chars: int) -> float:
    meaningful_ocr = [t for t in frame.ocr_text if not _is_noise_text(t, min_ocr_chars)]
    meaningful_ui = [el for el in frame.ui_elements if el.text.strip()]

    score = 0.0
    score += min(len(meaningful_ocr), 8) * 1.5
    score += min(len(meaningful_ui), 6) * 2.0

    error_keywords = ("error", "fail", "exception", "crash", "unable", "invalid", "timeout")
    blob = _frame_text_blob(frame)
    score += sum(3.0 for keyword in error_keywords if keyword in blob)

    if any(el.type.lower() in {"dialog", "alert", "toast", "modal"} for el in frame.ui_elements):
        score += 4.0

    return score


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def rank_frames(frames: list[Frame], min_ocr_chars: int = 3) -> list[tuple[Frame, float]]:
    """Rank frames by information value (highest first)."""
    scored = [(frame, _frame_score(frame, min_ocr_chars)) for frame in frames]
    scored.sort(key=lambda item: (item[1], item[0].timestamp_ms), reverse=True)
    return scored


def filter_frames(
    document: Module1Document,
    *,
    min_ocr_chars: int = 3,
    max_frames: int = 15,
    duplicate_threshold: float = 0.85,
    min_score: float = 0.1,
) -> Module1Document:
    """Remove noisy or duplicate frames while preserving high-value information."""
    ranked = rank_frames(document.frames, min_ocr_chars=min_ocr_chars)

    selected: list[Frame] = []
    selected_blobs: list[str] = []

    for frame, score in ranked:
        if score < min_score:
            continue

        blob = _frame_text_blob(frame)
        if blob and any(_similarity(blob, existing) >= duplicate_threshold for existing in selected_blobs):
            continue

        cleaned_ocr = [t for t in frame.ocr_text if not _is_noise_text(t, min_ocr_chars)]
        cleaned_frame = frame.model_copy(update={"ocr_text": cleaned_ocr or frame.ocr_text})

        selected.append(cleaned_frame)
        if blob:
            selected_blobs.append(blob)

        if len(selected) >= max_frames:
            break

    if not selected and document.frames:
        selected = [document.frames[0]]

    selected.sort(key=lambda frame: frame.timestamp_ms)
    return document.model_copy(update={"frames": selected})
