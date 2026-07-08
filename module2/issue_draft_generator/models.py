"""Internal data models for Module 1 input and GitHub issue drafts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class UIElement(BaseModel):
    type: str
    text: str = ""
    bounds: list[int] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)


class SessionEvent(BaseModel):
    type: str
    timestamp_ms: int = 0
    target: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class Frame(BaseModel):
    frame_id: str
    timestamp_ms: int = 0
    ocr_text: list[str] = Field(default_factory=list)
    ui_elements: list[UIElement] = Field(default_factory=list)
    screenshot_path: str | None = None

    @field_validator("ocr_text", mode="before")
    @classmethod
    def _normalize_ocr(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value.strip() else []
        return [str(item).strip() for item in value if str(item).strip()]


class SessionMetadata(BaseModel):
    app_name: str = "Unknown App"
    platform: str = "unknown"
    recorded_at: str = ""
    duration_ms: int = 0
    reporter: str = ""


class Module1Document(BaseModel):
    """Normalized Module 1 bug session document."""

    version: str = "1.0"
    session_id: str
    metadata: SessionMetadata
    frames: list[Frame] = Field(default_factory=list)
    events: list[SessionEvent] = Field(default_factory=list)


class IssueDraft(BaseModel):
    """Generated GitHub issue draft."""

    title: str
    body: str
    labels: list[str] = Field(default_factory=list)
    severity: str = "medium"

    @field_validator("labels", mode="before")
    @classmethod
    def _normalize_labels(cls, value: Any) -> list[str]:
        if value is None:
            return []
        return [str(label).strip().lower() for label in value if str(label).strip()]

    @field_validator("severity", mode="before")
    @classmethod
    def _normalize_severity(cls, value: Any) -> str:
        if value is None:
            return "medium"
        return str(value).strip().lower()


class PipelineResult(BaseModel):
    """Result of a full pipeline run."""

    draft: IssueDraft
    output_path: str | None = None
    prompt_tokens_estimate: int = 0
    compressed_tokens_estimate: int = 0
    compression_ratio: float = 1.0
    latency_ms: float = 0.0
    config_name: str = "default"
    model: str = ""
    stages_applied: list[str] = Field(default_factory=list)
