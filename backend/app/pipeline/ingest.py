"""Stage 1: ffmpeg-based frame extraction."""
from __future__ import annotations

import subprocess
from pathlib import Path


def extract_frames(video_path: Path, out_dir: Path, *, fps: int = 2) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = out_dir / "frame_%05d.png"
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", f"fps={fps}",
        "-hide_banner", "-loglevel", "error",
        str(pattern),
    ]
    subprocess.run(cmd, check=True)
    return sorted(out_dir.glob("frame_*.png"))
