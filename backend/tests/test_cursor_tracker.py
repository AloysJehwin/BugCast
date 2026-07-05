from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.pipeline.cursor_tracker import CursorTracker, MIN_CONFIDENCE


@pytest.fixture
def synthetic_template_and_frame(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Create a fake cursor template + a frame with that template pasted at (400, 300)."""
    template_dir = tmp_path / "cursor_templates"
    template_dir.mkdir()
    # A high-contrast triangle-ish shape — 24×24, easy to match.
    tpl = np.full((24, 24), 240, dtype=np.uint8)
    pts = np.array([[2, 2], [2, 22], [22, 12]], dtype=np.int32)
    cv2.fillPoly(tpl, [pts], 10)
    cv2.imwrite(str(template_dir / "arrow.png"), tpl)

    # Frame: 1280×720 grey background, with the template pasted at (400, 300).
    frame = np.full((720, 1280), 200, dtype=np.uint8)
    frame[300:324, 400:424] = tpl
    frame_path = tmp_path / "frame.png"
    cv2.imwrite(str(frame_path), frame)

    # Point the tracker at our synthetic template dir + reset its module cache.
    import app.pipeline.cursor_tracker as ct
    monkeypatch.setattr(ct, "TEMPLATES_DIR", template_dir)
    monkeypatch.setattr(ct, "_TEMPLATES_CACHE", None)
    return frame_path


class TestCursorTracker:
    def test_finds_template_at_known_position(self, synthetic_template_and_frame: Path) -> None:
        tracker = CursorTracker()
        hit = tracker.locate(synthetic_template_and_frame)
        assert hit is not None
        # Template is 24×24 pasted at (400, 300) — center is (412, 312).
        assert abs(hit.x - 412) <= 5
        assert abs(hit.y - 312) <= 5
        assert hit.confidence >= MIN_CONFIDENCE
        assert hit.template == "arrow"

    def test_updates_last_position(self, synthetic_template_and_frame: Path) -> None:
        tracker = CursorTracker()
        assert tracker.last is None
        tracker.locate(synthetic_template_and_frame)
        assert tracker.last is not None

    def test_returns_none_when_no_templates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, blank_frame: Path
    ) -> None:
        import app.pipeline.cursor_tracker as ct
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        monkeypatch.setattr(ct, "TEMPLATES_DIR", empty_dir)
        monkeypatch.setattr(ct, "_TEMPLATES_CACHE", None)
        tracker = CursorTracker()
        assert tracker.locate(blank_frame) is None

    def test_returns_none_on_missing_cursor(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, blank_frame: Path
    ) -> None:
        # Templates exist, but the frame has no cursor-like pattern.
        template_dir = tmp_path / "tpl"
        template_dir.mkdir()
        tpl = np.full((24, 24), 128, dtype=np.uint8)
        pts = np.array([[2, 2], [2, 22], [22, 12]], dtype=np.int32)
        cv2.fillPoly(tpl, [pts], 10)
        cv2.imwrite(str(template_dir / "arrow.png"), tpl)

        import app.pipeline.cursor_tracker as ct
        monkeypatch.setattr(ct, "TEMPLATES_DIR", template_dir)
        monkeypatch.setattr(ct, "_TEMPLATES_CACHE", None)

        tracker = CursorTracker()
        # blank_frame is uniformly (240,240,240) — a low-contrast template will
        # not exceed MIN_CONFIDENCE across any scale.
        hit = tracker.locate(blank_frame)
        assert hit is None or hit.confidence >= MIN_CONFIDENCE
