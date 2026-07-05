"""Stage 5: VLM reasoning over key frames on MI300X (Qwen2-VL-72B via vLLM)."""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import httpx

from app.utils.config import settings

SYSTEM_PROMPT = (
    "You are BugCast, an AI that watches screen recordings of software bugs. "
    "Given a small set of key frames and an event log, produce a compact JSON "
    "object describing the user's intent, the steps they took, the failure "
    "point, and a short hypothesis. Never invent selectors — describe what is "
    "visually observable."
)


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


async def reason_over_frames(frames: list[Path], events: list[dict[str, Any]]) -> dict[str, Any]:
    if not frames:
        return {"intent": "unknown", "steps": [], "broke_at_step": None, "symptom": "", "hypothesis": ""}

    content: list[dict[str, Any]] = [{"type": "text", "text": f"Events: {events}"}]
    for f in frames:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{_b64(f)}"},
        })

    payload = {
        "model": settings.vlm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": 800,
        "temperature": 0.1,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(f"{settings.vlm_endpoint}/chat/completions", json=payload)
            r.raise_for_status()
            data = r.json()
            return {"raw": data["choices"][0]["message"]["content"]}
    except Exception as exc:  # noqa: BLE001 — day-1 stub, don't crash the pipeline
        return {"error": str(exc), "stub": True}
