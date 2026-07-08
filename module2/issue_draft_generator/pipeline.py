"""Pipeline orchestration: load → filter → compress → LLM → save."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from issue_draft_generator.compress.filter import filter_frames
from issue_draft_generator.compress.lingua import PromptCompressor, estimate_tokens
from issue_draft_generator.filer import save_pipeline_result
from issue_draft_generator.llm import LLMError, OllamaClient
from issue_draft_generator.loader import load_module1_dict, load_module1_json
from issue_draft_generator.models import IssueDraft, Module1Document, PipelineResult


@dataclass
class PipelineConfig:
    enable_frame_filter: bool = True
    enable_lingua_compression: bool = True
    enable_json_mode: bool = True
    config_name: str = "default"

    @classmethod
    def from_dict(cls, data: dict[str, Any], name: str = "default") -> "PipelineConfig":
        return cls(
            enable_frame_filter=bool(data.get("enable_frame_filter", True)),
            enable_lingua_compression=bool(data.get("enable_lingua_compression", True)),
            enable_json_mode=bool(data.get("enable_json_mode", True)),
            config_name=name,
        )


def load_app_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else Path(__file__).resolve().parent / "config.yaml"
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def render_prompt_template(document: Module1Document, template_path: str | Path | None = None) -> str:
    path = Path(template_path) if template_path else Path(__file__).resolve().parent / "prompts" / "draft_issue.md"
    template = path.read_text(encoding="utf-8")
    session_content = _format_session_content(document)
    replacements = {
        "{{app_name}}": document.metadata.app_name,
        "{{platform}}": document.metadata.platform,
        "{{session_id}}": document.session_id,
        "{{recorded_at}}": document.metadata.recorded_at,
        "{{duration_ms}}": str(document.metadata.duration_ms),
        "{{session_content}}": session_content,
    }
    prompt = template
    for key, value in replacements.items():
        prompt = prompt.replace(key, value)
    return prompt


def _format_session_content(document: Module1Document) -> str:
    lines: list[str] = []

    if document.events:
        lines.append("### User events")
        for event in document.events:
            lines.append(f"- [{event.timestamp_ms}ms] {event.type}: {event.target}")

    lines.append("### Frames")
    for frame in document.frames:
        lines.append(f"#### Frame {frame.frame_id} @ {frame.timestamp_ms}ms")
        if frame.ocr_text:
            lines.append("OCR:")
            for text in frame.ocr_text:
                lines.append(f"  - {text}")
        if frame.ui_elements:
            lines.append("UI elements:")
            for element in frame.ui_elements:
                label = element.text or element.type
                lines.append(f"  - {element.type}: {label}")

    return "\n".join(lines)


class IssueDraftPipeline:
    """Coordinate the complete Module 2 workflow."""

    def __init__(self, app_config: dict[str, Any] | None = None) -> None:
        self.app_config = app_config or load_app_config()
        ollama_cfg = self.app_config.get("ollama") or {}
        self.llm = OllamaClient(
            host=str(ollama_cfg.get("host", "http://localhost:11434")),
            model=str(ollama_cfg.get("model", "qwen2.5:7b-instruct")),
            temperature=float(ollama_cfg.get("temperature", 0)),
            timeout_seconds=int(ollama_cfg.get("timeout_seconds", 180)),
        )
        lingua_cfg = self.app_config.get("lingua") or {}
        self.compressor = PromptCompressor(
            model_name=str(lingua_cfg.get("model_name", "microsoft/llmlingua-2-xlm-roberta-large-meetingbank")),
            target_rate=float(lingua_cfg.get("target_rate", 0.25)),
        )

    def run(
        self,
        source: str | Path | dict[str, Any] | Module1Document,
        *,
        pipeline_config: PipelineConfig | None = None,
        save: bool = True,
        output_dir: str | Path | None = None,
        llm_client: OllamaClient | None = None,
    ) -> PipelineResult:
        pipeline_cfg = pipeline_config or PipelineConfig.from_dict(self.app_config.get("pipeline") or {})
        start = time.perf_counter()
        stages: list[str] = []

        if isinstance(source, Module1Document):
            document = source
        elif isinstance(source, dict):
            document = load_module1_dict(source)
        else:
            document = load_module1_json(source)

        if pipeline_cfg.enable_frame_filter:
            filter_cfg = self.app_config.get("frame_filter") or {}
            document = filter_frames(
                document,
                min_ocr_chars=int(filter_cfg.get("min_ocr_chars", 3)),
                max_frames=int(filter_cfg.get("max_frames", 15)),
                duplicate_threshold=float(filter_cfg.get("duplicate_threshold", 0.85)),
                min_score=float(filter_cfg.get("min_score", 0.1)),
            )
            stages.append("frame_filter")

        prompt = render_prompt_template(document)
        original_tokens = estimate_tokens(prompt)

        if pipeline_cfg.enable_lingua_compression:
            prompt, original_tokens, compressed_tokens = self.compressor.compress(prompt)
            stages.append("lingua_compression")
        else:
            compressed_tokens = original_tokens

        client = llm_client or self.llm
        try:
            draft = client.generate_issue_draft(prompt, json_mode=pipeline_cfg.enable_json_mode)
            if pipeline_cfg.enable_json_mode:
                stages.append("json_mode")
        except LLMError:
            raise

        latency_ms = (time.perf_counter() - start) * 1000
        compression_ratio = original_tokens / max(compressed_tokens, 1)

        result = PipelineResult(
            draft=draft,
            prompt_tokens_estimate=original_tokens,
            compressed_tokens_estimate=compressed_tokens,
            compression_ratio=compression_ratio,
            latency_ms=latency_ms,
            config_name=pipeline_cfg.config_name,
            model=client.model,
            stages_applied=stages,
        )

        if save:
            drafts_cfg = self.app_config.get("drafts") or {}
            target_dir = output_dir or drafts_cfg.get("output_dir")
            save_pipeline_result(
                result,
                output_dir=target_dir,
                session_id=document.session_id,
                suffix=pipeline_cfg.config_name,
            )

        return result
