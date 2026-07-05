"""PaddleOCR 3.7 (PP-OCRv6) wrapper.

The v3 API returns a list of `OCRResult` objects with `.json` payloads.
We disable orientation/unwarping/textline extras — for UI screenshots they add
latency without helping. MKLDNN is disabled: on some CPUs it hits a paddle 3.3
PIR-runtime bug on the OCR detection model.

Retina screen recordings are typically 3000+ px wide. Running detection at that
resolution is ~4× slower than at 1600 px and gives no meaningful accuracy win
on UI text. We downscale before inference and scale bboxes back up.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

# Downscale target for OCR. UI text stays legible; det/rec run 3-4× faster.
OCR_LONG_EDGE_MAX = 1600

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
    """PaddleOCR 3.7 wraps the OCR result under either `.json` (dict) or `.json["res"]`."""
    j = result.json
    if isinstance(j, dict) and "res" in j and isinstance(j["res"], dict):
        return j["res"]
    return j if isinstance(j, dict) else {}


def _downscale(img: np.ndarray, long_edge_max: int) -> tuple[np.ndarray, float]:
    """Resize so the long edge is at most `long_edge_max`. Returns (image, scale)
    where original_coord = downscaled_coord / scale."""
    h, w = img.shape[:2]
    long_edge = max(h, w)
    if long_edge <= long_edge_max:
        return img, 1.0
    scale = long_edge_max / long_edge
    new_w, new_h = int(round(w * scale)), int(round(h * scale))
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA), scale


def ocr_frame(path: Path, *, long_edge_max: int = OCR_LONG_EDGE_MAX) -> list[dict[str, Any]]:
    """Run OCR on one frame. Returns list of {text, bbox: [x,y,w,h], conf} in
    original-image coordinates."""
    img = cv2.imread(str(path))
    if img is None:
        return []

    small, scale = _downscale(img, long_edge_max)
    results = _get().predict(small)
    if not results:
        return []

    payload = _payload(results[0])
    rec_texts: list[str] = payload.get("rec_texts") or []
    rec_scores: list[float] = payload.get("rec_scores") or []
    rec_polys: list[list[list[float]]] = payload.get("rec_polys") or payload.get("dt_polys") or []

    tokens: list[dict[str, Any]] = []
    inv_scale = 1.0 / scale
    for text, conf, poly in zip(rec_texts, rec_scores, rec_polys, strict=False):
        xs = [p[0] * inv_scale for p in poly]
        ys = [p[1] * inv_scale for p in poly]
        x, y = int(min(xs)), int(min(ys))
        w, h = int(max(xs) - x), int(max(ys) - y)
        tokens.append({"text": text, "bbox": [x, y, w, h], "conf": float(conf)})
    return tokens


def ocr_text_set(path: Path) -> set[str]:
    """Fast helper for the frame scorer — just the token strings, lowercased."""
    return {t["text"].strip().lower() for t in ocr_frame(path) if t["text"].strip()}


def tokens_to_text_set(tokens: list[dict[str, Any]]) -> set[str]:
    """Same as ocr_text_set but reuses already-computed tokens (avoids double OCR)."""
    return {t["text"].strip().lower() for t in tokens if t["text"].strip()}
