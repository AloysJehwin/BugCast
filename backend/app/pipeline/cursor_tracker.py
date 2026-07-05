"""Cursor tracking via multi-template NCC matching.

Approach:
    - Keep a small library of cursor templates (arrow, hand/pointer, i-beam, grab).
    - For each frame, run `cv2.matchTemplate` for every (template × scale).
    - Take the best NCC score across all combinations.
    - Gate on `MIN_CONFIDENCE` — below that, return None (better than a wrong guess).

Templates are user-supplied PNGs with alpha in `backend/app/pipeline/cursor_templates/`.
If the directory is empty (day-1 state), tracking returns None silently — the
scorer just contributes 0 for the cursor_jump signal, no crash.

Why templates instead of a trained detector?
    - Cursors on macOS/Windows/Linux are ~30×30 px sprites. Template matching
      nails them at ~1 ms/frame. No model to train or ship.
    - We only need coarse (x, y). Sub-pixel accuracy doesn't matter for
      "did the user click somewhere new."

Day-2 upgrade path:
    - Add per-OS template packs (macOS retina, Windows 10/11, Linux themes).
    - Cache last-known-good (x, y) and only search a window around it.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

TEMPLATES_DIR = Path(__file__).parent / "cursor_templates"
SCALES = (0.75, 1.0, 1.25, 1.5, 2.0)  # cover retina + non-retina + zoom
MIN_CONFIDENCE = 0.70  # NCC threshold below which we don't trust the hit


@dataclass
class CursorHit:
    x: int
    y: int
    confidence: float
    template: str


def _load_templates() -> list[tuple[str, np.ndarray]]:
    if not TEMPLATES_DIR.exists():
        return []
    out: list[tuple[str, np.ndarray]] = []
    for p in sorted(TEMPLATES_DIR.glob("*.png")):
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is not None and img.size > 0:
            out.append((p.stem, img))
    return out


_TEMPLATES_CACHE: list[tuple[str, np.ndarray]] | None = None


def _templates() -> list[tuple[str, np.ndarray]]:
    global _TEMPLATES_CACHE
    if _TEMPLATES_CACHE is None:
        _TEMPLATES_CACHE = _load_templates()
    return _TEMPLATES_CACHE


class CursorTracker:
    """Stateful tracker — remembers last-known-good position to speed up search."""

    def __init__(self, search_window_px: int = 250):
        self.last: tuple[int, int] | None = None
        self.search_window = search_window_px

    def locate(self, frame_path: Path) -> CursorHit | None:
        templates = _templates()
        if not templates:
            return None

        gray = cv2.imread(str(frame_path), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            return None

        # If we've seen the cursor before, restrict the search to a window
        # around the last-known-good position. Big speedup on high-fps video.
        haystack, offset_xy = self._maybe_window(gray)

        best: CursorHit | None = None
        for name, tpl in templates:
            for scale in SCALES:
                th, tw = tpl.shape
                sw, sh = int(tw * scale), int(th * scale)
                if sw < 6 or sh < 6:
                    continue
                if sw >= haystack.shape[1] or sh >= haystack.shape[0]:
                    continue
                resized = cv2.resize(tpl, (sw, sh), interpolation=cv2.INTER_AREA)
                res = cv2.matchTemplate(haystack, resized, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                if max_val < MIN_CONFIDENCE:
                    continue
                if best is None or max_val > best.confidence:
                    x = int(max_loc[0] + sw / 2 + offset_xy[0])
                    y = int(max_loc[1] + sh / 2 + offset_xy[1])
                    best = CursorHit(x=x, y=y, confidence=float(max_val), template=name)

        # If the windowed search failed, retry on the full frame once.
        if best is None and offset_xy != (0, 0):
            self.last = None
            return self.locate(frame_path)

        if best:
            self.last = (best.x, best.y)
        return best

    def _maybe_window(self, gray: np.ndarray) -> tuple[np.ndarray, tuple[int, int]]:
        if self.last is None:
            return gray, (0, 0)
        x, y = self.last
        r = self.search_window
        h, w = gray.shape
        x0, y0 = max(0, x - r), max(0, y - r)
        x1, y1 = min(w, x + r), min(h, y + r)
        return gray[y0:y1, x0:x1], (x0, y0)


def locate_cursor_stateless(path: Path) -> tuple[int, int] | None:
    """Convenience wrapper matching the `cursor_fn(Path) -> (x, y) | None` signature."""
    hit = CursorTracker().locate(path)
    return (hit.x, hit.y) if hit else None
