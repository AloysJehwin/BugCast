"""Multi-signal frame scoring — the heart of BugCast's cost story.

Every frame gets a score in [0, 1] based on how *meaningfully* it differs from
the previous kept frame. Deterministic — zero LLM tokens.

Signals (weights sum to 1.0):
    ssim          0.15  structural change on downsampled gray
    phash         0.10  perceptual hash Hamming distance
    ocr_delta     0.30  Jaccard distance on OCR token sets
    ui_delta      0.15  new/removed UI element count (edge-detected proxy)
    cursor_jump   0.10  euclidean distance of tracked cursor
    color_hist    0.05  chi-square on HSV histograms
    error_signal  0.15  red pixel ratio + error-keyword regex on OCR

Design notes:
- Two-pass: caller runs `cheap_score` on all frames first, then `full_score`
  on the survivors. OCR + edge detection is expensive; SSIM + pHash is not.
- Every score gets logged to `scores.json` for threshold tuning on Day 2.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

import cv2
import imagehash
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim

ERROR_RE = re.compile(r"\b(error|failed|failure|exception|500|404|403|denied|invalid)\b", re.I)

WEIGHTS = {
    "ssim": 0.15,
    "phash": 0.10,
    "ocr_delta": 0.30,
    "ui_delta": 0.15,
    "cursor_jump": 0.10,
    "color_hist": 0.05,
    "error_signal": 0.15,
}


@dataclass
class FrameSignals:
    frame: str
    timestamp_s: float
    ssim: float = 0.0
    phash: float = 0.0
    ocr_delta: float = 0.0
    ui_delta: float = 0.0
    cursor_jump: float = 0.0
    color_hist: float = 0.0
    error_signal: float = 0.0
    score: float = 0.0
    ocr_tokens: set[str] = field(default_factory=set)

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["ocr_tokens"] = sorted(self.ocr_tokens)
        return d


# ---------- individual signals ----------

def _load_gray(path: Path, size: tuple[int, int] = (320, 180)) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    return cv2.resize(img, size)


def _load_hsv_hist(path: Path) -> np.ndarray:
    img = cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([img], [0, 1], None, [32, 32], [0, 180, 0, 256])
    cv2.normalize(hist, hist)
    return hist.flatten()


def ssim_distance(prev: Path, curr: Path) -> float:
    s = ssim(_load_gray(prev), _load_gray(curr))
    return float(1.0 - max(0.0, min(1.0, s)))


def phash_distance(prev: Path, curr: Path) -> float:
    h1 = imagehash.phash(Image.open(prev))
    h2 = imagehash.phash(Image.open(curr))
    return (h1 - h2) / 64.0  # normalize by hash bit length


def ocr_jaccard(prev_tokens: set[str], curr_tokens: set[str]) -> float:
    if not prev_tokens and not curr_tokens:
        return 0.0
    inter = len(prev_tokens & curr_tokens)
    union = len(prev_tokens | curr_tokens)
    return 1.0 - (inter / union if union else 0.0)


def ui_edge_delta(prev: Path, curr: Path) -> float:
    """Cheap proxy for 'UI elements appeared/disappeared' using Canny edges."""
    a = cv2.Canny(_load_gray(prev), 100, 200)
    b = cv2.Canny(_load_gray(curr), 100, 200)
    diff = np.count_nonzero(cv2.absdiff(a, b))
    return min(1.0, diff / (a.shape[0] * a.shape[1] * 0.15))


def cursor_jump_norm(prev_xy: tuple[int, int] | None, curr_xy: tuple[int, int] | None,
                     frame_size: tuple[int, int]) -> float:
    if not prev_xy or not curr_xy:
        return 0.0
    dx, dy = curr_xy[0] - prev_xy[0], curr_xy[1] - prev_xy[1]
    dist = float(np.hypot(dx, dy))
    diag = float(np.hypot(*frame_size))
    return min(1.0, dist / diag)


def color_hist_chi2(prev: Path, curr: Path) -> float:
    a = _load_hsv_hist(prev)
    b = _load_hsv_hist(curr)
    chi = float(cv2.compareHist(a.reshape(-1, 1), b.reshape(-1, 1), cv2.HISTCMP_CHISQR))
    return min(1.0, chi / 5.0)  # empirically 5.0 is "very different scene"


def error_signal(path: Path, ocr_tokens: set[str]) -> float:
    """Red-heavy pixels + error keyword in OCR. Boosts error frames hard."""
    img = cv2.imread(str(path))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower1, upper1 = np.array([0, 100, 80]), np.array([10, 255, 255])
    lower2, upper2 = np.array([170, 100, 80]), np.array([180, 255, 255])
    mask = cv2.inRange(hsv, lower1, upper1) | cv2.inRange(hsv, lower2, upper2)
    red_ratio = float(np.count_nonzero(mask)) / mask.size
    kw_hit = 1.0 if any(ERROR_RE.search(t) for t in ocr_tokens) else 0.0
    return min(1.0, red_ratio * 20.0 + kw_hit * 0.6)


# ---------- passes ----------

def cheap_score(prev: Path, curr: Path) -> float:
    """Pass 1: SSIM + pHash only. Used to drop obvious duplicates fast."""
    return 0.6 * ssim_distance(prev, curr) + 0.4 * phash_distance(prev, curr)


def full_score(
    *,
    prev_frame: Path,
    curr_frame: Path,
    timestamp_s: float,
    prev_ocr: set[str],
    curr_ocr: set[str],
    prev_cursor: tuple[int, int] | None,
    curr_cursor: tuple[int, int] | None,
    frame_size: tuple[int, int],
) -> FrameSignals:
    """Pass 2: all signals. Only run on Pass-1 survivors."""
    sig = FrameSignals(frame=curr_frame.name, timestamp_s=timestamp_s, ocr_tokens=curr_ocr)
    sig.ssim = ssim_distance(prev_frame, curr_frame)
    sig.phash = phash_distance(prev_frame, curr_frame)
    sig.ocr_delta = ocr_jaccard(prev_ocr, curr_ocr)
    sig.ui_delta = ui_edge_delta(prev_frame, curr_frame)
    sig.cursor_jump = cursor_jump_norm(prev_cursor, curr_cursor, frame_size)
    sig.color_hist = color_hist_chi2(prev_frame, curr_frame)
    sig.error_signal = error_signal(curr_frame, curr_ocr)
    sig.score = sum(getattr(sig, k) * w for k, w in WEIGHTS.items())
    return sig
