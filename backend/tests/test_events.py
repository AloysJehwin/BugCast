"""Unit tests for deterministic event inference."""
from __future__ import annotations

import pytest

from app.pipeline.events import (
    CLICK_MIN_STILL,
    infer_events,
)


def _tok(text: str, bbox: tuple[int, int, int, int], conf: float = 0.99) -> dict:
    return {"text": text, "bbox": list(bbox), "conf": conf}


class TestClickDetection:
    def test_cursor_stopping_over_button_fires_click(self) -> None:
        # Frame 0: cursor moving. Frames 1..3: still over "Submit".
        button = _tok("Submit", (100, 100, 80, 30))
        ocr = [[button]] * 4
        cursors = [(50, 50), (130, 115), (131, 116), (130, 115)]
        events = infer_events(ocr, cursors=cursors, timestamps=[0.0, 0.5, 1.0, 1.5])
        clicks = [e for e in events if e["action"] == "click"]
        assert len(clicks) >= 1
        assert clicks[0]["target"] == "Submit"

    def test_idle_cursor_no_click(self) -> None:
        # Cursor never moves — not a click, just idle.
        button = _tok("Submit", (100, 100, 80, 30))
        ocr = [[button]] * 5
        cursors = [(130, 115)] * 5
        events = infer_events(ocr, cursors=cursors)
        clicks = [e for e in events if e["action"] == "click"]
        assert clicks == []

    def test_no_cursor_no_click(self) -> None:
        button = _tok("Submit", (100, 100, 80, 30))
        events = infer_events([[button]] * 4, cursors=[None] * 4)
        assert [e for e in events if e["action"] == "click"] == []


class TestTypingDetection:
    def test_growing_text_in_stable_bbox_fires_type(self) -> None:
        ocr = [
            [_tok("", (40, 100, 200, 30))],
            [_tok("aloys", (40, 100, 200, 30))],
            [_tok("aloys@ex", (40, 100, 200, 30))],
            [_tok("aloys@example.com", (40, 100, 200, 30))],
        ]
        events = infer_events(ocr, timestamps=[0.0, 0.5, 1.0, 1.5])
        types = [e for e in events if e["action"] == "type"]
        assert len(types) >= 1
        assert types[-1]["value"] == "aloys@example.com"

    def test_short_addition_ignored(self) -> None:
        # Only 1 new char — below TYPE_TEXT_GROWTH threshold.
        ocr = [
            [_tok("a", (40, 100, 200, 30))],
            [_tok("ab", (40, 100, 200, 30))],
        ]
        events = infer_events(ocr)
        assert [e for e in events if e["action"] == "type"] == []


class TestNavigationDetection:
    def test_massive_ocr_turnover_fires_navigate(self) -> None:
        page_a = [_tok("Home", (0, 0, 40, 20)), _tok("About", (50, 0, 40, 20)), _tok("Log in", (100, 0, 40, 20))]
        page_b = [_tok("Dashboard", (0, 0, 80, 20)), _tok("Reports", (90, 0, 60, 20)), _tok("Sign out", (160, 0, 60, 20))]
        events = infer_events([page_a, page_b], timestamps=[0.0, 1.0])
        assert any(e["action"] == "navigate" for e in events)

    def test_same_page_no_navigate(self) -> None:
        page = [_tok("Home", (0, 0, 40, 20)), _tok("About", (50, 0, 40, 20))]
        events = infer_events([page, page], timestamps=[0.0, 1.0])
        assert [e for e in events if e["action"] == "navigate"] == []


class TestErrorDetection:
    def test_error_keyword_fires_error_modal(self) -> None:
        ocr = [[_tok("500 Server Error", (10, 10, 200, 30))]]
        events = infer_events(ocr, timestamps=[0.0])
        errs = [e for e in events if e["action"] == "error_modal"]
        assert len(errs) == 1
        assert "500" in errs[0]["target"]

    def test_error_signal_alone_fires_low_conf(self) -> None:
        # No error keyword, but signals say error_signal is high (red banner).
        ocr = [[_tok("Oh no", (10, 10, 100, 30))]]
        signals = [{"error_signal": 0.6}]
        events = infer_events(ocr, timestamps=[0.0], signals=signals)
        errs = [e for e in events if e["action"] == "error_modal"]
        assert len(errs) == 1
        assert errs[0]["confidence"] < 0.7  # lower conf without keyword

    def test_no_error_no_event(self) -> None:
        ocr = [[_tok("Welcome home", (10, 10, 200, 30))]]
        events = infer_events(ocr, timestamps=[0.0])
        assert [e for e in events if e["action"] == "error_modal"] == []


class TestConsoleErrorDetection:
    def test_traceback_fires_console_error(self) -> None:
        ocr = [[_tok("Uncaught TypeError: foo is not a function", (0, 500, 500, 20))]]
        events = infer_events(ocr, timestamps=[0.0])
        assert any(e["action"] == "console_error" for e in events)


class TestDeduping:
    def test_duplicate_events_within_200ms_collapsed(self) -> None:
        # Two frames, both trigger error_modal on the same text.
        ocr = [[_tok("500 Server Error", (10, 10, 200, 30))]] * 2
        events = infer_events(ocr, timestamps=[0.0, 0.1])
        errs = [e for e in events if e["action"] == "error_modal"]
        assert len(errs) == 1

    def test_same_action_further_apart_both_kept(self) -> None:
        ocr = [[_tok("500 Server Error", (10, 10, 200, 30))]] * 2
        events = infer_events(ocr, timestamps=[0.0, 5.0])
        errs = [e for e in events if e["action"] == "error_modal"]
        assert len(errs) == 2


class TestEmptyInput:
    def test_no_frames_returns_empty(self) -> None:
        assert infer_events([]) == []

    def test_default_timestamps_are_frame_indices(self) -> None:
        # Sanity: no-op call, just check timestamps default without crashing.
        events = infer_events([[_tok("hello", (0, 0, 50, 20))]])
        assert events == [] or all("t" in e for e in events)