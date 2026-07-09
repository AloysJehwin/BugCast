# Module 2 — GitHub Issue Draft Generator

Module 2 converts **Module 1 bug session JSON** into a structured **GitHub issue draft** using a local LLM via **Ollama**. The pipeline is fully offline and saves drafts locally (no GitHub API).

## Architecture

```text
Module 1 JSON
     │
     ▼
 loader.py          Validate & normalize schema
     │
     ▼
 compress/filter.py Rank & remove low-value frames
     │
     ▼
 compress/lingua.py LLMLingua-2 compression (2–4× target)
     │
     ▼
 llm.py             Single Ollama call (JSON mode)
     │
     ▼
 filer.py           Save draft JSON locally
```

## Prerequisites

1. **Python 3.10+**
2. **Ollama** running locally
3. Default model pulled:

```bash
ollama pull qwen2.5:7b-instruct
```

4. Optional (recommended): LLMLingua-2 dependencies

```bash
pip install -r requirements-lingua.txt
```

Without LLMLingua-2, a deterministic fallback compressor is used so the pipeline still runs.

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

### Generate a single draft

```bash
python -m module2 generate tests/fixtures/login_timeout.json
```

Legacy form (same as above):

```bash
python -m module2 tests/fixtures/login_timeout.json
```

### Toggle optimization stages

```bash
python -m module2 generate input.json --no-filter --no-lingua
python -m module2 generate input.json --no-json-mode
python -m module2 generate input.json --model llama3.1:8b-instruct
```

### Benchmark

Runs five configurations (baseline, filter only, lingua only, json mode only, full pipeline) across ~20 fixtures:

```bash
python -m module2 bench
python -m module2 bench --dry-run   # structure check only, no LLM
```

Reports are written to `bench_reports/` as JSON and Markdown.

## Module 1 JSON schema

Module 2 expects JSON with:

```json
{
  "version": "1.0",
  "session_id": "unique-id",
  "metadata": {
    "app_name": "MyApp",
    "platform": "web|ios|android|desktop",
    "recorded_at": "ISO-8601 timestamp",
    "duration_ms": 45000,
    "reporter": "optional"
  },
  "frames": [
    {
      "frame_id": "f001",
      "timestamp_ms": 1200,
      "ocr_text": ["Error", "Retry"],
      "ui_elements": [
        {"type": "button", "text": "Retry"}
      ]
    }
  ],
  "events": [
    {"type": "click", "timestamp_ms": 1100, "target": "Login"}
  ]
}
```

## Output schema

```json
{
  "title": "Concise bug title",
  "body": "Markdown issue body",
  "labels": ["bug", "ui"],
  "severity": "low|medium|high|critical"
}
```

Drafts are saved under `module2/drafts/`.

## Configuration

Edit `module2/config.yaml` for:

- Ollama host/model/temperature
- Frame filter thresholds
- LLMLingua-2 model and target compression rate
- Benchmark configuration matrix

## Evaluation metrics

The benchmark harness computes:

| Metric | Description |
| --- | --- |
| Title similarity | Sequence match on normalized titles |
| Body ROUGE-L | Content overlap vs ground truth |
| Label F1 | Label set F1 score |
| Severity match | Exact match on severity |
| Composite score | Weighted combination (0–1) |

Also tracked: latency, token estimates, compression ratio, failure rate.

## Tests

```bash
pytest
```

Unit tests use a fake LLM client and do not require Ollama. Integration tests with Ollama can be run manually via the CLI.

## Assumptions

- **Module 1 schema** is inferred from the project description (not provided in the spec). If your Module 1 output differs, share a sample and the loader can be adjusted.
- **LLMLingua-2** is optional at install time because it pulls large ML dependencies; full compression requires `requirements-lingua.txt`.
