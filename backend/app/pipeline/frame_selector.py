"""Frame selection with guardrails.

Given scored frames, pick the ~5 that best represent the flow:
  1. Always keep first and last frame.
  2. Rank the rest by score.
  3. Enforce a minimum time-gap between kept frames (dedupe rapid animations).
  4. For each big spike, keep neighbours (before/after) so the VLM sees context.
  5. Cap at `max_key_frames`.

This is "score-guided sampling", not naive top-K — top-K clusters around one
event and loses setup/aftermath, which the VLM needs to reason correctly.
"""
from __future__ import annotations

from pathlib import Path

from app.pipeline.frame_scorer import FrameSignals


def select_key_frames(
    signals: list[FrameSignals],
    all_frames: list[Path],
    *,
    max_key_frames: int = 5,
    min_gap_s: float = 0.2,
    spike_ratio: float = 2.0,
) -> list[FrameSignals]:
    if not signals:
        return []

    by_name = {p.name: p for p in all_frames}
    signals_sorted = sorted(signals, key=lambda s: s.timestamp_s)

    kept: dict[str, FrameSignals] = {}

    # 1. First + last frames — always keep.
    kept[signals_sorted[0].frame] = signals_sorted[0]
    if len(signals_sorted) > 1:
        kept[signals_sorted[-1].frame] = signals_sorted[-1]

    # 2. Spike neighbours.
    scores = [s.score for s in signals_sorted]
    avg = sum(scores) / len(scores) if scores else 0.0
    spike_threshold = max(0.2, avg * spike_ratio)
    for i, s in enumerate(signals_sorted):
        if s.score >= spike_threshold:
            if i > 0:
                kept.setdefault(signals_sorted[i - 1].frame, signals_sorted[i - 1])
            kept.setdefault(s.frame, s)

    # 3. Fill remaining slots by score, respecting min_gap.
    remaining = [s for s in signals_sorted if s.frame not in kept]
    remaining.sort(key=lambda s: s.score, reverse=True)
    for s in remaining:
        if len(kept) >= max_key_frames:
            break
        if all(abs(s.timestamp_s - k.timestamp_s) >= min_gap_s for k in kept.values()):
            kept[s.frame] = s

    # 4. If still over cap, drop lowest-scoring middle frames (never first/last).
    if len(kept) > max_key_frames:
        first, last = signals_sorted[0].frame, signals_sorted[-1].frame
        middle = sorted(
            (s for s in kept.values() if s.frame not in (first, last)),
            key=lambda s: s.score,
            reverse=True,
        )
        keep_names = {first, last, *(s.frame for s in middle[: max_key_frames - 2])}
        kept = {n: s for n, s in kept.items() if n in keep_names}

    return sorted(kept.values(), key=lambda s: s.timestamp_s)


def selected_paths(selected: list[FrameSignals], all_frames: list[Path]) -> list[Path]:
    by_name = {p.name: p for p in all_frames}
    return [by_name[s.frame] for s in selected if s.frame in by_name]
