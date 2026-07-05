"""Stage 4: infer click / type / error-modal events from OCR + cursor tracking.

Day 1 returns a stubbed event log so downstream stages can run end-to-end.
Day 2: implement cursor template match + click detection + error-modal regex.
"""
from __future__ import annotations

from typing import Any


def infer_events(ocr_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # TODO(day2): real CV inference. For now, empty log is fine — pipeline still runs.
    return []
