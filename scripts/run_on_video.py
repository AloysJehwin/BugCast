"""Ad-hoc runner: process a real video through the deterministic BugCast pipeline
(ingest → filter → OCR → cursor → events) and dump the results.

Skips the VLM/coder/replay stages (they need MI300X). Used to smoke-test on
real screen recordings before Day 2.

Usage:
    python scripts/run_on_video.py samples/videos/bug_screen_recording.mov
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.pipeline.cursor_tracker import CursorTracker  # noqa: E402
from app.pipeline.events import infer_events  # noqa: E402
from app.pipeline.frame_filter import filter_and_score  # noqa: E402
from app.pipeline.ingest import extract_frames  # noqa: E402
from app.pipeline.ocr import run_ocr  # noqa: E402
from ml.ocr.paddle import ocr_frame  # noqa: E402

EXTRACT_FPS = 2
MAX_KEY_FRAMES = 5


def main(video_path: Path) -> None:
    job_id = video_path.stem
    frames_dir = REPO_ROOT / "frames" / job_id
    out_dir = REPO_ROOT / "samples" / "outputs" / job_id
    frames_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/5] ffmpeg → frames @ {EXTRACT_FPS}fps")
    t0 = time.time()
    all_frames = extract_frames(video_path, frames_dir, fps=EXTRACT_FPS)
    print(f"      {len(all_frames)} frames in {time.time() - t0:.1f}s")

    print("[2/5] two-pass frame scoring (OCR runs here, cached for stage 3)")
    tracker = CursorTracker()

    def _cursor(p: Path):
        hit = tracker.locate(p)
        return (hit.x, hit.y) if hit else None

    t0 = time.time()
    key_frames, signals, ocr_cache = filter_and_score(
        all_frames,
        fps=EXTRACT_FPS,
        out_dir=out_dir,
        ocr_fn=ocr_frame,
        cursor_fn=_cursor,
        max_key_frames=MAX_KEY_FRAMES,
    )
    print(f"      {len(all_frames)} → {len(key_frames)} key frames in {time.time() - t0:.1f}s")

    print("[3/5] OCR (from cache, zero recompute)")
    t0 = time.time()
    ocr_results = run_ocr(key_frames, cache=ocr_cache)
    print(f"      done in {time.time() - t0:.1f}s")

    print("[4/5] event inference")
    ocr_per_frame = [r["ocr"] for r in ocr_results]
    timestamps = [i / EXTRACT_FPS for i in range(len(key_frames))]
    cursors = [_cursor(f) for f in key_frames]
    events = infer_events(
        ocr_per_frame,
        timestamps=timestamps,
        cursors=cursors,
        signals=signals,
    )

    print("[5/5] persisting results")
    result = {
        "job_id": job_id,
        "video": str(video_path),
        "frames_total": len(all_frames),
        "frames_key": len(key_frames),
        "key_frame_names": [f.name for f in key_frames],
        "events": events,
        "ocr_summary": [
            {
                "frame": r["frame"],
                "token_count": len(r["ocr"]),
                "texts": [t["text"] for t in r["ocr"]][:10],
            }
            for r in ocr_results
        ],
    }
    (out_dir / "pipeline_result.json").write_text(json.dumps(result, indent=2))
    print(f"      wrote {out_dir / 'pipeline_result.json'}")

    print("\n─── summary ───")
    print(f"  frames extracted: {len(all_frames)}")
    print(f"  key frames kept:  {len(key_frames)}")
    print(f"  events inferred:  {len(events)}")
    for e in events:
        print(f"    t={e['t']:>5.2f}s  {e['action']:14s}  target={e['target']!r}  conf={e['confidence']}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: run_on_video.py <path/to/video>")
        sys.exit(1)
    main(Path(sys.argv[1]).resolve())
