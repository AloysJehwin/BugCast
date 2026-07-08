"""Benchmark report generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from issue_draft_generator.bench.harness import BenchmarkReport


def print_report(report: BenchmarkReport) -> None:
    print(f"Benchmark model: {report.model}")
    print("\nConfiguration summaries:")
    for summary in report.config_summaries:
        print(
            f"- {summary.config_name}: "
            f"runs={summary.runs}, failures={summary.failures}, "
            f"failure_rate={summary.failure_rate:.2%}, "
            f"avg_latency_ms={summary.avg_latency_ms:.1f}, "
            f"avg_compression={summary.avg_compression_ratio:.2f}x, "
            f"avg_quality={summary.avg_composite_score:.3f}"
        )


def save_report(report: BenchmarkReport, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    json_path = out / f"benchmark_{timestamp}.json"
    md_path = out / f"benchmark_{timestamp}.md"

    payload = report.to_dict()
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")

    lines = [
        "# Module 2 Benchmark Report",
        "",
        f"- Model: `{report.model}`",
        f"- Generated: `{timestamp}`",
        "",
        "## Configuration Summaries",
        "",
        "| Config | Runs | Failures | Failure Rate | Avg Latency (ms) | Avg Compression | Avg Quality |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for summary in report.config_summaries:
        lines.append(
            f"| {summary.config_name} | {summary.runs} | {summary.failures} | "
            f"{summary.failure_rate:.2%} | {summary.avg_latency_ms:.1f} | "
            f"{summary.avg_compression_ratio:.2f}x | {summary.avg_composite_score:.3f} |"
        )

    lines.extend(["", "## Per-fixture Results", ""])
    for item in report.fixture_results:
        status = "ok" if item.success else f"fail: {item.error}"
        lines.append(
            f"- `{item.fixture}` / `{item.config_name}`: {status}, "
            f"quality={item.composite_score:.3f}, latency={item.latency_ms:.1f}ms"
        )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path
