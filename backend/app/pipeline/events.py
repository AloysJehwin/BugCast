"""Deterministic event inference from OCR + cursor tracks + colour signals.

Turns the per-frame signal stream into a semantic event log the VLM can reason
over. No LLM tokens spent here.

Event schema
    { "t": float,               # timestamp in seconds
      "action": str,            # click|type|navigate|error_modal|console_error|scroll
      "target": str | None,     # OCR text nearest to the event, if known
      "value": str | None,      # typed value, if action == "type"
      "bbox": [x,y,w,h] | None, # bbox of the target element
      "confidence": float }     # how sure we are (0..1)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

ERROR_RE = re.compile(
    r"\b(error|failed|failure|exception|500|404|403|401|denied|invalid|timeout|unavailable)\b",
    re.IGNORECASE,
)
CONSOLE_RE = re.compile(
    r"(uncaught|typeerror|referenceerror|syntaxerror|at\s+\S+:\d+|traceback|stack\s*trace)",
    re.IGNORECASE,
)

# Detection thresholds — tuned against synthetic tests, tune again against
# real videos on day 2.
CLICK_STOP_PX = 8      # cursor delta below this = "stopped"
CLICK_MIN_STILL = 2    # stopped for at least this many consecutive frames
NAV_JACCARD = 0.7      # OCR set turnover above this = navigation
TYPE_TEXT_GROWTH = 3   # new chars in a stable bbox to count as typing


@dataclass
class Event:
    t: float
    action: str
    target: str | None = None
    value: str | None = None
    bbox: list[int] | None = None
    confidence: float = 0.6

    def as_dict(self) -> dict[str, Any]:
        return {
            "t": round(self.t, 3),
            "action": self.action,
            "target": self.target,
            "value": self.value,
            "bbox": self.bbox,
            "confidence": round(self.confidence, 2),
        }


# ---------- helpers ----------

def _nearest_token(
    tokens: list[dict[str, Any]], xy: tuple[int, int] | None
) -> dict[str, Any] | None:
    if not tokens or xy is None:
        return None
    x, y = xy
    best, best_d = None, float("inf")
    for tok in tokens:
        bx, by, bw, bh = tok["bbox"]
        cx, cy = bx + bw / 2, by + bh / 2
        d = (cx - x) ** 2 + (cy - y) ** 2
        if d < best_d:
            best, best_d = tok, d
    return best


def _tokens_set(tokens: list[dict[str, Any]]) -> set[str]:
    return {t["text"].strip().lower() for t in tokens if t.get("text", "").strip()}


def _bbox_overlap(a: list[int], b: list[int]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix1, iy1 = max(ax, bx), max(ay, by)
    ix2, iy2 = min(ax + aw, bx + bw), min(ay + ay + ah, by + bh)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    union = aw * ah + bw * bh - inter
    return inter / union if union else 0.0


# ---------- detectors ----------

def _detect_click(
    idx: int,
    timestamps: list[float],
    cursors: list[tuple[int, int] | None],
    tokens_per_frame: list[list[dict[str, Any]]],
) -> Event | None:
    """Fires on the frame *after* the cursor has been still for CLICK_MIN_STILL frames.

    Two conditions:
      1. cursor delta within the still window <= CLICK_STOP_PX.
      2. cursor was measurably moving *at some point* before entering the still window.
         Prevents firing on a purely idle cursor sitting on a button.
    """
    if idx < CLICK_MIN_STILL:
        return None
    still_window = cursors[idx - CLICK_MIN_STILL : idx + 1]
    if any(c is None for c in still_window):
        return None
    xs = [c[0] for c in still_window if c is not None]
    ys = [c[1] for c in still_window if c is not None]
    if (max(xs) - min(xs)) > CLICK_STOP_PX or (max(ys) - min(ys)) > CLICK_STOP_PX:
        return None

    # Was the cursor moving at any point before it stopped? Scan the whole prefix.
    prior = [c for c in cursors[: idx - CLICK_MIN_STILL] if c is not None]
    if not prior:
        return None  # no history at all — can't call it a click
    was_moving = any(
        abs(c[0] - xs[0]) > CLICK_STOP_PX or abs(c[1] - ys[0]) > CLICK_STOP_PX for c in prior
    )
    if not was_moving:
        return None  # idle since forever, not a click

    xy = cursors[idx]
    tok = _nearest_token(tokens_per_frame[idx], xy)
    return Event(
        t=timestamps[idx],
        action="click",
        target=(tok["text"] if tok else None),
        bbox=(tok["bbox"] if tok else None),
        confidence=0.75 if tok else 0.5,
    )


def _detect_navigation(
    idx: int,
    timestamps: list[float],
    tokens_per_frame: list[list[dict[str, Any]]],
) -> Event | None:
    if idx == 0:
        return None
    prev = _tokens_set(tokens_per_frame[idx - 1])
    curr = _tokens_set(tokens_per_frame[idx])
    if not prev or not curr:
        return None
    inter = len(prev & curr)
    union = len(prev | curr)
    jaccard_dist = 1.0 - (inter / union)
    if jaccard_dist < NAV_JACCARD:
        return None
    return Event(
        t=timestamps[idx],
        action="navigate",
        confidence=min(1.0, jaccard_dist),
    )


def _detect_typing(
    idx: int,
    timestamps: list[float],
    tokens_per_frame: list[list[dict[str, Any]]],
) -> Event | None:
    """A stable bbox whose text grew by TYPE_TEXT_GROWTH+ chars = typing."""
    if idx == 0:
        return None
    prev_toks = tokens_per_frame[idx - 1]
    curr_toks = tokens_per_frame[idx]
    for c in curr_toks:
        for p in prev_toks:
            if _bbox_overlap(c["bbox"], p["bbox"]) < 0.5:
                continue
            if c["text"] == p["text"]:
                continue
            if not c["text"].startswith(p["text"]):
                continue
            added = c["text"][len(p["text"]) :]
            if len(added) >= TYPE_TEXT_GROWTH:
                return Event(
                    t=timestamps[idx],
                    action="type",
                    target=p["text"] or None,
                    value=c["text"],
                    bbox=c["bbox"],
                    confidence=0.7,
                )
    return None


def _detect_error(
    idx: int,
    timestamps: list[float],
    tokens_per_frame: list[list[dict[str, Any]]],
    signals: list[dict[str, Any]] | None,
) -> Event | None:
    texts = tokens_per_frame[idx]
    joined = " ".join(t["text"] for t in texts)
    if not (ERROR_RE.search(joined) or (signals and signals[idx].get("error_signal", 0) > 0.4)):
        return None
    # Prefer a token that literally matches the regex — it's likely the modal text.
    tok = next((t for t in texts if ERROR_RE.search(t["text"])), None)
    return Event(
        t=timestamps[idx],
        action="error_modal",
        target=(tok["text"] if tok else None),
        bbox=(tok["bbox"] if tok else None),
        confidence=0.85 if tok else 0.55,
    )


def _detect_console_error(
    idx: int,
    timestamps: list[float],
    tokens_per_frame: list[list[dict[str, Any]]],
) -> Event | None:
    joined = " ".join(t["text"] for t in tokens_per_frame[idx])
    if not CONSOLE_RE.search(joined):
        return None
    return Event(t=timestamps[idx], action="console_error", target=joined[:120], confidence=0.6)


# ---------- public entry point ----------

def infer_events(
    ocr_per_frame: list[list[dict[str, Any]]],
    *,
    timestamps: list[float] | None = None,
    cursors: list[tuple[int, int] | None] | None = None,
    signals: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Turn per-frame OCR + optional cursor/signal streams into an event log.

    Args:
        ocr_per_frame: list of OCR token lists (one per frame).
        timestamps:    frame timestamps in seconds. Defaults to frame index.
        cursors:       optional cursor (x, y) per frame; None where the cursor
                       couldn't be located.
        signals:       optional per-frame score dicts (from frame_scorer). If
                       present, error_signal is used as an extra error hint.
    """
    n = len(ocr_per_frame)
    if n == 0:
        return []

    if timestamps is None:
        timestamps = [float(i) for i in range(n)]
    if cursors is None:
        cursors = [None] * n

    events: list[Event] = []
    for i in range(n):
        for detector in (
            _detect_click,
            _detect_typing,
            _detect_navigation,
            _detect_error,
            _detect_console_error,
        ):
            if detector is _detect_click:
                ev = detector(i, timestamps, cursors, ocr_per_frame)
            elif detector is _detect_error:
                ev = detector(i, timestamps, ocr_per_frame, signals)
            elif detector in (_detect_typing, _detect_navigation, _detect_console_error):
                ev = detector(i, timestamps, ocr_per_frame)
            else:
                ev = None
            if ev is not None:
                events.append(ev)

    # De-duplicate near-identical events within 200ms — keep highest confidence.
    events.sort(key=lambda e: (e.t, -e.confidence))
    deduped: list[Event] = []
    for ev in events:
        if any(
            d.action == ev.action
            and (d.target == ev.target or (d.target is None and ev.target is None))
            and abs(d.t - ev.t) < 0.2
            for d in deduped
        ):
            continue
        deduped.append(ev)
    return [e.as_dict() for e in deduped]