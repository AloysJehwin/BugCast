"""Command-line interface for Module 2."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from issue_draft_generator.bench.harness import run_benchmark
from issue_draft_generator.bench.report import print_report, save_report
from issue_draft_generator.llm import LLMError
from issue_draft_generator.pipeline import IssueDraftPipeline, PipelineConfig, load_app_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="module2",
        description="Generate GitHub issue drafts from Module 1 bug session JSON (offline via Ollama).",
    )
    subparsers = parser.add_subparsers(dest="command")

    generate = subparsers.add_parser("generate", help="Generate an issue draft from a Module 1 JSON file")
    generate.add_argument("input", type=Path, help="Path to Module 1 JSON input")
    generate.add_argument("--config", type=Path, default=None, help="Path to config.yaml")
    generate.add_argument("--output-dir", type=Path, default=None, help="Directory for saved drafts")
    generate.add_argument("--no-save", action="store_true", help="Print draft to stdout without saving")
    generate.add_argument("--no-filter", action="store_true", help="Disable frame filtering")
    generate.add_argument("--no-lingua", action="store_true", help="Disable LLMLingua-2 compression")
    generate.add_argument("--no-json-mode", action="store_true", help="Disable Ollama JSON mode")
    generate.add_argument("--model", type=str, default=None, help="Override Ollama model name")
    generate.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    bench = subparsers.add_parser("bench", help="Run benchmark suite against fixtures")
    bench.add_argument("--config", type=Path, default=None, help="Path to config.yaml")
    bench.add_argument("--fixtures-dir", type=Path, default=None, help="Directory with Module 1 fixtures")
    bench.add_argument("--ground-truth-dir", type=Path, default=None, help="Directory with expected drafts")
    bench.add_argument("--report-dir", type=Path, default=None, help="Directory for benchmark reports")
    bench.add_argument("--model", type=str, default=None, help="Override Ollama model for all runs")
    bench.add_argument("--dry-run", action="store_true", help="Evaluate metrics only (no LLM calls)")
    bench.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    # Back-compat: `python -m module2 input.json`
    parser.add_argument("legacy_input", nargs="?", type=Path, help=argparse.SUPPRESS)

    return parser


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )


def _cmd_generate(args: argparse.Namespace) -> int:
    app_config = load_app_config(args.config)
    if args.model:
        app_config.setdefault("ollama", {})["model"] = args.model

    pipeline_cfg = PipelineConfig.from_dict(app_config.get("pipeline") or {})
    if args.no_filter:
        pipeline_cfg.enable_frame_filter = False
    if args.no_lingua:
        pipeline_cfg.enable_lingua_compression = False
    if args.no_json_mode:
        pipeline_cfg.enable_json_mode = False

    pipeline = IssueDraftPipeline(app_config)
    try:
        result = pipeline.run(
            args.input,
            pipeline_config=pipeline_cfg,
            save=not args.no_save,
            output_dir=args.output_dir,
        )
    except (LLMError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    payload = {
        "draft": result.draft.model_dump(),
        "metrics": {
            "latency_ms": round(result.latency_ms, 2),
            "prompt_tokens_estimate": result.prompt_tokens_estimate,
            "compressed_tokens_estimate": result.compressed_tokens_estimate,
            "compression_ratio": round(result.compression_ratio, 3),
            "stages_applied": result.stages_applied,
            "model": result.model,
            "output_path": result.output_path,
        },
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _cmd_bench(args: argparse.Namespace) -> int:
    app_config = load_app_config(args.config)
    if args.model:
        app_config.setdefault("ollama", {})["model"] = args.model

    bench_cfg = app_config.get("benchmark") or {}
    fixtures_dir = args.fixtures_dir or Path(bench_cfg.get("fixtures_dir", "tests/fixtures"))
    ground_truth_dir = args.ground_truth_dir or Path(bench_cfg.get("ground_truth_dir", "tests/ground_truth"))
    report_dir = args.report_dir or Path(bench_cfg.get("report_dir", "bench_reports"))

    try:
        report = run_benchmark(
            app_config,
            fixtures_dir=fixtures_dir,
            ground_truth_dir=ground_truth_dir,
            dry_run=args.dry_run,
        )
    except (LLMError, ValueError, OSError) as exc:
        print(f"Benchmark error: {exc}", file=sys.stderr)
        return 1

    print_report(report)
    save_report(report, report_dir)
    print(f"\nReport saved to {report_dir.resolve()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(getattr(args, "verbose", False))

    if args.command == "generate":
        return _cmd_generate(args)
    if args.command == "bench":
        return _cmd_bench(args)

    if args.legacy_input:
        args.input = args.legacy_input
        args.no_save = False
        args.no_filter = False
        args.no_lingua = False
        args.no_json_mode = False
        args.output_dir = None
        args.config = None
        args.model = None
        return _cmd_generate(args)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
