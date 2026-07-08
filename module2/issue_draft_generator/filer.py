"""Save generated issue drafts locally as JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from issue_draft_generator.models import IssueDraft, PipelineResult


def _default_drafts_dir() -> Path:
    return Path(__file__).resolve().parent / "drafts"


def save_draft(
    draft: IssueDraft,
    *,
    output_dir: str | Path | None = None,
    session_id: str | None = None,
    suffix: str = "",
) -> Path:
    """Persist an issue draft to the local drafts directory."""
    drafts_dir = Path(output_dir) if output_dir else _default_drafts_dir()
    drafts_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    session_part = session_id or "session"
    name_suffix = f"_{suffix}" if suffix else ""
    filename = f"{session_part}_{timestamp}{name_suffix}.json"
    output_path = drafts_dir / filename

    payload = draft.model_dump()
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    return output_path


def save_pipeline_result(
    result: PipelineResult,
    *,
    output_dir: str | Path | None = None,
    session_id: str | None = None,
    suffix: str = "",
) -> Path:
    """Save draft from a pipeline result and update result.output_path."""
    path = save_draft(
        result.draft,
        output_dir=output_dir,
        session_id=session_id,
        suffix=suffix or result.config_name,
    )
    result.output_path = str(path)
    return path
