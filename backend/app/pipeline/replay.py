"""Stage 7: run generated Playwright script headless, screenshot each step,
diff against original video frames to confirm reproduction."""
from __future__ import annotations

from pathlib import Path
from typing import Any


async def replay_and_diff(*, script: str, reference_frames: list[Path]) -> dict[str, Any]:
    # TODO(day3): write script to playwright-runner/tests/<job>.spec.ts, run it,
    # screenshot each step, SSIM-compare against reference_frames, return verdict.
    return {"ran": False, "reproduced": None, "note": "stub — wired on day 3"}
