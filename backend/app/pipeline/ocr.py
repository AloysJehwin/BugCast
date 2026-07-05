"""Stage 3: OCR + UI element extraction.

Real PaddleOCR wrapper lives in `ml/ocr/paddle.py`. We keep the import lazy so
the module can be loaded (and unit-tested) without paddle installed. Callers
can pass a custom `ocr_fn` for testing.

An optional `cache` maps frame filename → already-computed OCR token list
(populated by `filter_and_score`). Frames in the cache skip re-OCR.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def _default_ocr(path: Path) -> list[dict[str, Any]]:
    from ml.ocr.paddle import ocr_frame
    return ocr_frame(path)


def run_ocr(
    frames: list[Path],
    *,
    ocr_fn: Callable[[Path], list[dict[str, Any]]] | None = None,
    cache: dict[str, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    """Run OCR on every frame. Returns one dict per frame with `frame` name +
    `ocr` (list of {text, bbox, conf}) + `ui_elements` (reserved for YOLO)."""
    fn = ocr_fn or _default_ocr
    cache = cache or {}
    results: list[dict[str, Any]] = []
    for frame in frames:
        tokens = cache.get(frame.name)
        if tokens is None:
            tokens = fn(frame)
        results.append({
            "frame": frame.name,
            "ocr": tokens,
            "ui_elements": [],
        })
    return results
