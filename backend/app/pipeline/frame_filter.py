"""Stage 2 orchestration — two-pass frame filtering.

Pass 1: cheap SSIM+pHash on every frame → drop obvious duplicates.
Pass 2: full multi-signal scoring on survivors. OCR runs here ONCE and the
        full token results are cached and returned so downstream stages don't
        redo the work.
Selection: guardrail-based picker in `frame_selector`.

Persists per-frame signals to `<out_dir>/scores.json` for threshold tuning.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import cv2

from app.pipeline.frame_scorer import FrameSignals, cheap_score, full_score
from app.pipeline.frame_selector import select_key_frames, selected_paths

CHEAP_THRESHOLD = 0.08  # pass-1 minimum "meaningful change" score


def _frame_size(path: Path) -> tuple[int, int]:
    img = cv2.imread(str(path))
    h, w = img.shape[:2]
    return (w, h)


def _tokens_to_set(tokens: list[dict[str, Any]] | set[str]) -> set[str]:
    """Accept either a full-token list or a legacy set. Legacy path kept so old
    integration tests (which stub `ocr_fn` to return a set) still work."""
    if isinstance(tokens, set):
        return tokens
    return {t["text"].strip().lower() for t in tokens if t.get("text", "").strip()}


def filter_and_score(
    frames: list[Path],
    *,
    fps: int,
    out_dir: Path,
    ocr_fn: Callable[[Path], list[dict[str, Any]] | set[str]] | None = None,
    cursor_fn: Callable[[Path], tuple[int, int] | None] | None = None,
    max_key_frames: int = 5,
) -> tuple[list[Path], list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """Run the two-pass filter.

    Returns:
        (selected_frame_paths, per_frame_signal_dicts, ocr_cache)

        `ocr_cache` maps frame filename → full OCR token list, populated for
        every Pass-2 survivor. Downstream code should reuse this instead of
        re-running OCR on the key frames.
    """
    if not frames:
        return [], [], {}

    frame_size = _frame_size(frames[0])

    # Pass 1 — cheap SSIM + pHash.
    survivors: list[Path] = [frames[0]]
    prev = frames[0]
    for f in frames[1:]:
        if cheap_score(prev, f) >= CHEAP_THRESHOLD:
            survivors.append(f)
            prev = f
    if survivors[-1] != frames[-1]:
        survivors.append(frames[-1])

    # Pass 2 — full scoring on survivors only.
    signals: list[FrameSignals] = []
    ocr_cache: dict[str, list[dict[str, Any]]] = {}
    prev_ocr: set[str] = set()
    prev_cursor: tuple[int, int] | None = None
    prev_frame = survivors[0]
    for i, f in enumerate(survivors):
        curr_tokens_raw = ocr_fn(f) if ocr_fn else []
        # Cache full-token list where available so run_ocr can reuse it.
        if isinstance(curr_tokens_raw, list):
            ocr_cache[f.name] = curr_tokens_raw
        curr_ocr = _tokens_to_set(curr_tokens_raw)
        curr_cursor = cursor_fn(f) if cursor_fn else None
        ts = i / max(fps, 1)
        sig = full_score(
            prev_frame=prev_frame,
            curr_frame=f,
            timestamp_s=ts,
            prev_ocr=prev_ocr,
            curr_ocr=curr_ocr,
            prev_cursor=prev_cursor,
            curr_cursor=curr_cursor,
            frame_size=frame_size,
        )
        signals.append(sig)
        prev_ocr, prev_cursor, prev_frame = curr_ocr, curr_cursor, f

    selected = select_key_frames(signals, survivors, max_key_frames=max_key_frames)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "scores.json").write_text(json.dumps(
        {
            "total_input": len(frames),
            "pass1_survivors": len(survivors),
            "selected": [s.frame for s in selected],
            "signals": [s.as_dict() for s in signals],
        },
        indent=2,
    ))

    return (
        selected_paths(selected, survivors),
        [s.as_dict() for s in signals],
        ocr_cache,
    )
