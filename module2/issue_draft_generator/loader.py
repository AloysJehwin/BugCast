"""Load and validate Module 1 JSON into the internal document model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from issue_draft_generator.models import Frame, Module1Document, SessionMetadata, UIElement


class LoaderError(ValueError):
    """Raised when Module 1 JSON cannot be loaded or validated."""


def _coerce_ui_elements(raw_elements: Any) -> list[dict[str, Any]]:
    if not raw_elements:
        return []
    elements: list[dict[str, Any]] = []
    for item in raw_elements:
        if isinstance(item, str):
            elements.append({"type": "text", "text": item})
        elif isinstance(item, dict):
            elements.append(item)
    return elements


def normalize_document(data: dict[str, Any]) -> Module1Document:
    """Normalize loosely structured Module 1 JSON into a strict document model."""
    metadata_raw = data.get("metadata") or {}
    if not isinstance(metadata_raw, dict):
        metadata_raw = {}

    frames: list[Frame] = []
    for index, frame_raw in enumerate(data.get("frames") or []):
        if not isinstance(frame_raw, dict):
            continue
        frame_id = str(frame_raw.get("frame_id") or frame_raw.get("id") or f"frame_{index:04d}")
        ui_elements = [UIElement.model_validate(el) for el in _coerce_ui_elements(frame_raw.get("ui_elements"))]
        frames.append(
            Frame(
                frame_id=frame_id,
                timestamp_ms=int(frame_raw.get("timestamp_ms") or frame_raw.get("timestamp") or 0),
                ocr_text=frame_raw.get("ocr_text") or [],
                ui_elements=ui_elements,
                screenshot_path=frame_raw.get("screenshot_path"),
            )
        )

    session_id = str(data.get("session_id") or data.get("id") or "unknown-session")
    metadata = SessionMetadata(
        app_name=str(metadata_raw.get("app_name") or metadata_raw.get("application") or "Unknown App"),
        platform=str(metadata_raw.get("platform") or "unknown"),
        recorded_at=str(metadata_raw.get("recorded_at") or metadata_raw.get("timestamp") or ""),
        duration_ms=int(metadata_raw.get("duration_ms") or metadata_raw.get("duration") or 0),
        reporter=str(metadata_raw.get("reporter") or ""),
    )

    return Module1Document(
        version=str(data.get("version") or "1.0"),
        session_id=session_id,
        metadata=metadata,
        frames=frames,
        events=data.get("events") or [],
    )


def load_module1_json(path: str | Path) -> Module1Document:
    """Load Module 1 JSON from disk, validate schema, and return normalized document."""
    file_path = Path(path)
    if not file_path.exists():
        raise LoaderError(f"Input file not found: {file_path}")

    try:
        with file_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise LoaderError(f"Invalid JSON in {file_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise LoaderError("Module 1 JSON root must be an object")

    try:
        document = normalize_document(data)
    except ValidationError as exc:
        raise LoaderError(f"Schema validation failed: {exc}") from exc

    if not document.frames:
        raise LoaderError("Module 1 document must contain at least one frame")

    return document


def load_module1_dict(data: dict[str, Any]) -> Module1Document:
    """Load Module 1 document from an in-memory dict."""
    if not isinstance(data, dict):
        raise LoaderError("Module 1 input must be a dict")
    document = normalize_document(data)
    if not document.frames:
        raise LoaderError("Module 1 document must contain at least one frame")
    return document
