"""Tier-2: end-to-end pipeline integration test.

Synthesizes a fake bug video with ffmpeg (blank → text → button → click → error),
runs `run_pipeline` with a stub OCR fn, and asserts the multi-signal scorer
picks the meaningful frames — specifically the error-modal frame.

Skips gracefully if ffmpeg isn't on PATH.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.pipeline.orchestrator import run_pipeline
from app.utils.config import settings

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


# ---------- fixture: synthetic bug video ----------

def _draw_blank(w: int, h: int) -> np.ndarray:
    return np.full((h, w, 3), (240, 240, 240), dtype=np.uint8)


def _draw_login_form(w: int, h: int) -> np.ndarray:
    img = _draw_blank(w, h)
    cv2.putText(img, "Please log in", (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (20, 20, 20), 2)
    cv2.rectangle(img, (40, 100), (300, 130), (200, 200, 200), 2)
    cv2.putText(img, "email", (48, 122), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
    cv2.rectangle(img, (40, 150), (300, 180), (200, 200, 200), 2)
    cv2.putText(img, "password", (48, 172), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
    return img


def _draw_form_with_button(w: int, h: int) -> np.ndarray:
    img = _draw_login_form(w, h)
    cv2.rectangle(img, (40, 210), (200, 250), (100, 160, 100), -1)
    cv2.putText(img, "Sign in", (75, 236), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return img


def _draw_form_clicked(w: int, h: int) -> np.ndarray:
    img = _draw_form_with_button(w, h)
    # cursor at the button
    cv2.circle(img, (120, 230), 4, (0, 0, 0), -1)
    return img


def _draw_error(w: int, h: int) -> np.ndarray:
    img = _draw_form_with_button(w, h)
    cv2.rectangle(img, (0, 0), (w, 60), (40, 40, 220), -1)  # red bar, BGR
    cv2.putText(img, "500 Server Error", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    return img


@pytest.fixture
def synthetic_bug_video(tmp_path: Path) -> Path:
    w, h = 640, 360
    frame_dir = tmp_path / "src_frames"
    frame_dir.mkdir()

    # 15-frame flow, held for a few frames each so ffmpeg has stable input.
    scenes = (
        [_draw_blank(w, h)] * 3
        + [_draw_login_form(w, h)] * 3
        + [_draw_form_with_button(w, h)] * 3
        + [_draw_form_clicked(w, h)] * 3
        + [_draw_error(w, h)] * 3
    )
    for i, frame in enumerate(scenes):
        cv2.imwrite(str(frame_dir / f"src_{i:04d}.png"), frame)

    video_path = tmp_path / "bug.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-framerate", "2",
            "-i", str(frame_dir / "src_%04d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-hide_banner", "-loglevel", "error",
            str(video_path),
        ],
        check=True,
    )
    assert video_path.exists()
    return video_path


# ---------- helpers to keep VLM/OCR out of the picture ----------

@pytest.fixture
def stub_ocr(monkeypatch: pytest.MonkeyPatch):
    """Fake OCR: label frames by filename → keywords. Keeps paddle out of tier-2."""
    def fake_ocr_token_set(path: Path) -> set[str]:
        # Load frame, look at pixels — cheap heuristic.
        img = cv2.imread(str(path))
        if img is None:
            return set()
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        red_mask = (
            cv2.inRange(hsv, np.array([0, 100, 80]), np.array([10, 255, 255]))
            | cv2.inRange(hsv, np.array([170, 100, 80]), np.array([180, 255, 255]))
        )
        red_ratio = float(np.count_nonzero(red_mask)) / red_mask.size

        h, w = img.shape[:2]
        # Green button region check
        green_mask = cv2.inRange(hsv, np.array([40, 80, 60]), np.array([80, 255, 200]))
        has_button = float(np.count_nonzero(green_mask)) / green_mask.size > 0.01

        tokens: set[str] = set()
        if red_ratio > 0.02:
            tokens |= {"500", "server", "error"}
        elif has_button:
            tokens |= {"please", "log", "in", "email", "password", "sign", "in"}
        else:
            # blank-ish
            if img.mean() > 220:
                pass
            else:
                tokens |= {"please", "log", "in", "email", "password"}
        return tokens

    import app.pipeline.orchestrator as orch
    monkeypatch.setattr(orch, "_ocr_token_set", fake_ocr_token_set)
    return fake_ocr_token_set


@pytest.fixture
def stub_vlm_and_gen(monkeypatch: pytest.MonkeyPatch):
    """Skip real VLM + script gen — they require MI300X."""
    import app.pipeline.orchestrator as orch

    async def fake_reason(frames, events):
        return {"stub": True, "intent": "log in", "broke_at_step": 1, "symptom": "500 error"}

    async def fake_script(*, events, vlm_summary):
        return "// stub script\n"

    async def fake_replay(*, script, reference_frames):
        return {"ran": False, "reproduced": None, "note": "stub"}

    monkeypatch.setattr(orch, "reason_over_frames", fake_reason)
    monkeypatch.setattr(orch, "generate_script", fake_script)
    monkeypatch.setattr(orch, "replay_and_diff", fake_replay)


@pytest.fixture
def tmp_workdirs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Point settings.upload_dir/frames_dir/outputs_dir at tmp_path."""
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "frames_dir", str(tmp_path / "frames"))
    monkeypatch.setattr(settings, "outputs_dir", str(tmp_path / "outputs"))
    return tmp_path


# ---------- the actual test ----------

class TestPipelineIntegration:
    def test_end_to_end_picks_error_frame(
        self,
        synthetic_bug_video: Path,
        stub_ocr,
        stub_vlm_and_gen,
        tmp_workdirs: Path,
    ) -> None:
        result = asyncio.run(run_pipeline(job_id="itest", video_path=synthetic_bug_video))

        assert result["job_id"] == "itest"
        assert result["frames_total"] > 0
        assert result["frames_key"] > 0
        assert result["frames_key"] <= settings.max_key_frames

        # scores.json must exist for the UI timeline strip
        scores_path = Path(tmp_workdirs) / "outputs" / "itest" / "scores.json"
        assert scores_path.exists()
        scores = json.loads(scores_path.read_text())
        assert scores["total_input"] > 0
        assert scores["pass1_survivors"] > 0
        assert len(scores["selected"]) == result["frames_key"]

        # The scorer's error_signal weight should surface the red-modal frame.
        # We check: at least one selected frame has strong error_signal.
        selected_names = set(scores["selected"])
        error_hit = any(
            s["frame"] in selected_names and s["error_signal"] > 0.3
            for s in scores["signals"]
        )
        assert error_hit, f"No selected frame had error_signal > 0.3. signals: {scores['signals']}"

    def test_reduction_ratio(
        self,
        synthetic_bug_video: Path,
        stub_ocr,
        stub_vlm_and_gen,
        tmp_workdirs: Path,
    ) -> None:
        result = asyncio.run(run_pipeline(job_id="ratio", video_path=synthetic_bug_video))
        # We fed 15 source frames at 2fps input → ~15 raw frames → the pipeline
        # should aggressively reduce to <= max_key_frames.
        assert result["frames_key"] <= settings.max_key_frames
        assert result["frames_key"] < result["frames_total"]
