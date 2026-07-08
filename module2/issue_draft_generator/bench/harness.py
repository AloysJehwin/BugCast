"""Benchmark harness for comparing pipeline configurations."""

from __future__ import annotations

import json
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from issue_draft_generator.bench.metrics import evaluate_draft
from issue_draft_generator.llm import LLMError, OllamaClient
from issue_draft_generator.loader import load_module1_json
from issue_draft_generator.models import IssueDraft
from issue_draft_generator.pipeline import IssueDraftPipeline, PipelineConfig


@dataclass
class FixtureRunResult:
    fixture: str
    config_name: str
    success: bool
    latency_ms: float = 0.0
    prompt_tokens_estimate: int = 0
    compressed_tokens_estimate: int = 0
    compression_ratio: float = 1.0
    title_similarity: float = 0.0
    body_rouge_l: float = 0.0
    label_f1: float = 0.0
    severity_match: float = 0.0
    composite_score: float = 0.0
    error: str | None = None


@dataclass
class ConfigSummary:
    config_name: str
    runs: int = 0
    failures: int = 0
    failure_rate: float = 0.0
    avg_latency_ms: float = 0.0
    avg_compression_ratio: float = 0.0
    avg_composite_score: float = 0.0
    avg_title_similarity: float = 0.0
    avg_body_rouge_l: float = 0.0
    avg_label_f1: float = 0.0
    avg_severity_match: float = 0.0


@dataclass
class BenchmarkReport:
    model: str
    fixture_results: list[FixtureRunResult] = field(default_factory=list)
    config_summaries: list[ConfigSummary] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "fixture_results": [asdict(item) for item in self.fixture_results],
            "config_summaries": [asdict(item) for item in self.config_summaries],
        }


def _load_ground_truth(path: Path) -> IssueDraft:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return IssueDraft.model_validate(data)


def _summarize_config(results: list[FixtureRunResult], config_name: str) -> ConfigSummary:
    subset = [item for item in results if item.config_name == config_name]
    if not subset:
        return ConfigSummary(config_name=config_name)

    successes = [item for item in subset if item.success]
    failures = len(subset) - len(successes)
    return ConfigSummary(
        config_name=config_name,
        runs=len(subset),
        failures=failures,
        failure_rate=failures / len(subset),
        avg_latency_ms=statistics.mean(item.latency_ms for item in successes) if successes else 0.0,
        avg_compression_ratio=statistics.mean(item.compression_ratio for item in successes) if successes else 0.0,
        avg_composite_score=statistics.mean(item.composite_score for item in successes) if successes else 0.0,
        avg_title_similarity=statistics.mean(item.title_similarity for item in successes) if successes else 0.0,
        avg_body_rouge_l=statistics.mean(item.body_rouge_l for item in successes) if successes else 0.0,
        avg_label_f1=statistics.mean(item.label_f1 for item in successes) if successes else 0.0,
        avg_severity_match=statistics.mean(item.severity_match for item in successes) if successes else 0.0,
    )


def run_benchmark(
    app_config: dict[str, Any],
    *,
    fixtures_dir: str | Path,
    ground_truth_dir: str | Path,
    dry_run: bool = False,
) -> BenchmarkReport:
    fixtures_path = Path(fixtures_dir)
    ground_truth_path = Path(ground_truth_dir)
    if not fixtures_path.exists():
        raise ValueError(f"Fixtures directory not found: {fixtures_path}")
    if not ground_truth_path.exists():
        raise ValueError(f"Ground truth directory not found: {ground_truth_path}")

    pipeline = IssueDraftPipeline(app_config)
    model = pipeline.llm.model

    if not dry_run and not pipeline.llm.is_available():
        raise LLMError(
            f"Ollama is not reachable or model '{model}' is missing. "
            "Start Ollama and pull the model, or use --dry-run for offline metric tests."
        )

    bench_cfg = app_config.get("benchmark") or {}
    config_defs = bench_cfg.get("configs") or []
    fixture_files = sorted(fixtures_path.glob("*.json"))
    if not fixture_files:
        raise ValueError(f"No fixture JSON files found in {fixtures_path}")

    report = BenchmarkReport(model=model)

    for fixture_file in fixture_files:
        ground_truth_file = ground_truth_path / fixture_file.name
        if not ground_truth_file.exists():
            raise ValueError(f"Missing ground truth for fixture: {fixture_file.name}")

        expected = _load_ground_truth(ground_truth_file)

        for config_def in config_defs:
            config_name = str(config_def.get("name", "unnamed"))
            pipeline_cfg = PipelineConfig.from_dict(config_def, name=config_name)
            result = FixtureRunResult(fixture=fixture_file.name, config_name=config_name, success=False)

            if dry_run:
                result.success = True
                result.composite_score = 1.0
                report.fixture_results.append(result)
                continue

            try:
                run_result = pipeline.run(
                    fixture_file,
                    pipeline_config=pipeline_cfg,
                    save=False,
                )
                metrics = evaluate_draft(run_result.draft, expected)
                result.success = True
                result.latency_ms = run_result.latency_ms
                result.prompt_tokens_estimate = run_result.prompt_tokens_estimate
                result.compressed_tokens_estimate = run_result.compressed_tokens_estimate
                result.compression_ratio = run_result.compression_ratio
                result.title_similarity = metrics.title_similarity
                result.body_rouge_l = metrics.body_rouge_l
                result.label_f1 = metrics.label_f1
                result.severity_match = metrics.severity_match
                result.composite_score = metrics.composite_score
            except Exception as exc:
                result.error = str(exc)

            report.fixture_results.append(result)

    config_names = [str(cfg.get("name", "unnamed")) for cfg in config_defs]
    report.config_summaries = [_summarize_config(report.fixture_results, name) for name in config_names]
    return report
