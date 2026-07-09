# Module 2

See [module2/README.md](module2/README.md) for full documentation.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Optional: LLMLingua-2 compression dependencies
pip install -r requirements-lingua.txt

# Generate fixtures (already committed, re-run to regenerate)
python scripts/generate_fixtures.py

# Run unit tests (no Ollama required)
pytest

# Generate a draft (requires Ollama + qwen2.5:7b-instruct)
python -m module2 generate tests/fixtures/login_timeout.json

# Run benchmark suite
python -m module2 bench
```

## Project layout

- `module2/` — pipeline implementation
- `tests/fixtures/` — Module 1 input JSON (~20 scenarios)
- `tests/ground_truth/` — expected issue drafts for benchmarking
- `scripts/generate_fixtures.py` — fixture generator
