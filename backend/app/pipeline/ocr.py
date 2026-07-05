"""Stage 3: OCR + UI element extraction. Stubbed for day 1; wire PaddleOCR in day 1 afternoon."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def run_ocr(frames: list[Path]) -> list[dict[str, Any]]:
    # TODO(day1): replace with PaddleOCR call — return real bboxes + confidences.
    results: list[dict[str, Any]] = []
    for frame in frames:
        results.append({
            "frame": frame.name,
            "ocr": [],  # [{ "text": str, "bbox": [x,y,w,h], "conf": float }]
            "ui_elements": [],  # [{ "type": str, "bbox": [...], "label": str }]
        })
    return results
