"""End-to-end orchestrator. Wires the two-pass frame filter + scoring in.

Stages 5–7 (VLM, script gen, replay) are still stubs — swapped in day 2/3.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from app.pipeline.cursor_tracker import CursorTracker
from app.pipeline.events import infer_events
from app.pipeline.frame_filter import filter_and_score
from app.pipeline.ingest import extract_frames
from app.pipeline.ocr import run_ocr
from app.pipeline.replay import replay_and_diff
from app.pipeline.script_gen import generate_script
from app.pipeline.vlm import reason_over_frames
from app.utils.config import settings


def _ocr_token_set(path: Path) -> set[str]:
    """Lazy import so tests don't need paddle installed."""
    from ml.ocr.paddle import ocr_text_set
    return ocr_text_set(path)


async def run_pipeline(*, job_id: str, video_path: Path) -> dict[str, Any]:
    t0 = time.time()

    frames_dir = Path(settings.frames_dir) / job_id
    outputs_dir = Path(settings.outputs_dir) / job_id
    frames_dir.mkdir(parents=True, exist_ok=True)

    all_frames = extract_frames(video_path, frames_dir, fps=settings.extract_fps)

    tracker = CursorTracker()

    def _cursor(path: Path) -> tuple[int, int] | None:
        hit = tracker.locate(path)
        return (hit.x, hit.y) if hit else None

    key_frames, signals = filter_and_score(
        all_frames,
        fps=settings.extract_fps,
        out_dir=outputs_dir,
        ocr_fn=_ocr_token_set,
        cursor_fn=_cursor,
        max_key_frames=settings.max_key_frames,
    )

    ocr_results = run_ocr(key_frames)
    events = infer_events(ocr_results)
    vlm_out = await reason_over_frames(key_frames, events)
    script = await generate_script(events=events, vlm_summary=vlm_out)
    replay = await replay_and_diff(script=script, reference_frames=key_frames)

    elapsed_ms = int((time.time() - t0) * 1000)
    return {
        "job_id": job_id,
        "elapsed_ms": elapsed_ms,
        "frames_total": len(all_frames),
        "frames_key": len(key_frames),
        "signals": signals,
        "events": events,
        "vlm": vlm_out,
        "script": script,
        "replay": replay,
    }
