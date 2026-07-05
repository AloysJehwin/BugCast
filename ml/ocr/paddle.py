"""PaddleOCR 3.7 (PP-OCRv6) wrapper.

The v3 API returns a list of `OCRResult` objects with `.json` payloads.
We disable orientation/unwarping/textline extras — for UI screenshots they add
latency without helping. Mobile detection + recognition is enough.
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
            ocr_version="PP-OCRv6",
            text_detection_model_name="PP-OCRv6_mobile_det",
            text_recognition_model_name="PP-OCRv6_mobile_rec",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            lang="en",
        )
    return _ocr


def ocr_frame(path: Path) -> list[dict[str, Any]]:
    """Run OCR on one frame. Returns list of {text, bbox: [x,y,w,h], conf}."""
    results = _get().predict(str(path))
    if not results:
        return []

    payload = results[0].json  # dict per v3 API
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
