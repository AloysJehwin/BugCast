"""PaddleOCR 3.7 (PP-OCRv6) wrapper.

The v3 API returns a list of `OCRResult` objects with `.json` payloads.
We disable orientation/unwarping/textline extras — for UI screenshots they add
latency without helping. MKLDNN is disabled: on some CPUs it hits a paddle 3.3
PIR-runtime bug on the OCR detection model.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

_ocr = None


def _get():
    global _ocr
    if _ocr is None:
        from paddleocr import PaddleOCR
        _ocr = PaddleOCR(
            lang="en",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
        )
    return _ocr


def _payload(result: Any) -> dict[str, Any]:
    """PaddleOCR 3.7 wraps the OCR result under either `.json` (dict) or `.json["res"]`.

    We normalize so callers always see rec_texts / rec_scores / rec_polys at top level.
    """
    j = result.json
    if isinstance(j, dict) and "res" in j and isinstance(j["res"], dict):
        return j["res"]
    return j if isinstance(j, dict) else {}


def ocr_frame(path: Path) -> list[dict[str, Any]]:
    """Run OCR on one frame. Returns list of {text, bbox: [x,y,w,h], conf}."""
    results = _get().predict(str(path))
    if not results:
        return []

    payload = _payload(results[0])
    rec_texts: list[str] = payload.get("rec_texts") or []
    rec_scores: list[float] = payload.get("rec_scores") or []
    rec_polys: list[list[list[float]]] = payload.get("rec_polys") or payload.get("dt_polys") or []

    tokens: list[dict[str, Any]] = []
    for text, conf, poly in zip(rec_texts, rec_scores, rec_polys, strict=False):
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        x, y = int(min(xs)), int(min(ys))
        w, h = int(max(xs) - x), int(max(ys) - y)
        tokens.append({"text": text, "bbox": [x, y, w, h], "conf": float(conf)})
    return tokens


def ocr_text_set(path: Path) -> set[str]:
    """Fast helper for the frame scorer — just the token strings, lowercased."""
    return {t["text"].strip().lower() for t in ocr_frame(path) if t["text"].strip()}
