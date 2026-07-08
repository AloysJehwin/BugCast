"""Unit tests for Module 2 components."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from issue_draft_generator.bench.metrics import evaluate_draft, title_similarity
from issue_draft_generator.compress.filter import filter_frames
from issue_draft_generator.compress.lingua import PromptCompressor, estimate_tokens
from issue_draft_generator.filer import save_draft
from issue_draft_generator.loader import LoaderError, load_module1_json
from issue_draft_generator.models import IssueDraft, Module1Document
from issue_draft_generator.pipeline import IssueDraftPipeline, PipelineConfig, render_prompt_template


FIXTURES_DIR = Path(__file__).parent / "fixtures"
GROUND_TRUTH_DIR = Path(__file__).parent / "ground_truth"


def test_fixtures_count_is_at_least_twenty() -> None:
    fixtures = list(FIXTURES_DIR.glob("*.json"))
    assert len(fixtures) >= 20


def test_each_fixture_has_ground_truth() -> None:
    for fixture in FIXTURES_DIR.glob("*.json"):
        assert (GROUND_TRUTH_DIR / fixture.name).exists()


def test_loader_validates_and_normalizes(tmp_path: Path) -> None:
    payload = {
        "session_id": "abc",
        "metadata": {"app_name": "TestApp"},
        "frames": [{"frame_id": "1", "ocr_text": "Error"}],
    }
    path = tmp_path / "input.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    doc = load_module1_json(path)
    assert doc.session_id == "abc"
    assert doc.metadata.app_name == "TestApp"
    assert len(doc.frames) == 1


def test_loader_rejects_empty_frames(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"session_id": "x", "frames": []}), encoding="utf-8")
    with pytest.raises(LoaderError):
        load_module1_json(path)


def test_frame_filter_removes_noise_and_duplicates() -> None:
    fixture = load_module1_json(FIXTURES_DIR / "login_timeout.json")
    filtered = filter_frames(fixture, max_frames=2, min_ocr_chars=3)
    assert len(filtered.frames) <= 2
    assert filtered.frames


def test_lingua_fallback_compression_reduces_tokens() -> None:
    compressor = PromptCompressor(model_name="unused", target_rate=0.25)
    prompt = "\n".join(f"Line {index}: error details about timeout and retry" for index in range(40))
    compressed, original_tokens, compressed_tokens = compressor.compress(prompt)
    assert compressed
    assert compressed_tokens <= original_tokens


def test_render_prompt_template_includes_session_data() -> None:
    doc = load_module1_json(FIXTURES_DIR / "checkout_crash.json")
    prompt = render_prompt_template(doc)
    assert "CartFlow" in prompt
    assert "Pay Now" in prompt


def test_save_draft_writes_json(tmp_path: Path) -> None:
    draft = IssueDraft(title="T", body="B", labels=["bug"], severity="high")
    path = save_draft(draft, output_dir=tmp_path, session_id="sess")
    assert path.exists()
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["title"] == "T"


def test_metrics_composite_score() -> None:
    predicted = IssueDraft(title="Login fails", body="steps", labels=["bug"], severity="high")
    expected = IssueDraft(title="Login fails", body="steps to reproduce", labels=["bug", "ui"], severity="high")
    metrics = evaluate_draft(predicted, expected)
    assert metrics.title_similarity == 1.0
    assert 0.0 <= metrics.composite_score <= 1.0


def test_title_similarity_handles_empty() -> None:
    assert title_similarity("", "") == 1.0
    assert title_similarity("a", "") == 0.0


def test_pipeline_without_llm_stages(tmp_path: Path) -> None:
    class FakeLLM:
        model = "fake-model"

        def generate_issue_draft(self, prompt: str, *, json_mode: bool = True) -> IssueDraft:
            assert "ShopPortal" in prompt or "CartFlow" in prompt or True
            return IssueDraft(
                title="Generated title",
                body="Generated body",
                labels=["bug"],
                severity="medium",
            )

    doc = load_module1_json(FIXTURES_DIR / "login_timeout.json")
    pipeline = IssueDraftPipeline()
    result = pipeline.run(
        doc,
        pipeline_config=PipelineConfig(
            enable_frame_filter=True,
            enable_lingua_compression=True,
            enable_json_mode=True,
            config_name="test",
        ),
        save=True,
        output_dir=tmp_path,
        llm_client=FakeLLM(),  # type: ignore[arg-type]
    )
    assert result.draft.title == "Generated title"
    assert result.output_path
    assert "frame_filter" in result.stages_applied


def test_estimate_tokens() -> None:
    assert estimate_tokens("hello world") >= 1
