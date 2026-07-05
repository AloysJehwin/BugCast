# BugCast

Turn any screen recording of a broken flow into a runnable Playwright repro script, powered by a 72B vision-language model on AMD MI300X.

**Built for:** AMD Developer Hackathon: ACT II — Unicorn Track (July 6–11, 2026)

## Pitch

Every user bug report becomes a runnable test. Upload a 30-second screen recording, and BugCast extracts the flow using OCR + OpenCV, reasons over the key frames with a 72B VLM on AMD MI300X, generates a Playwright script that reproduces the bug, and hands your team a shareable failing test plus a suggested fix. No frames leave your infra. ~70× cheaper than a naive GPT-4o pipeline.

## Why AMD MI300X

- 192 GB HBM3 per GPU means Qwen2-VL-72B and Qwen2.5-Coder-32B co-reside on a single card — no sharding, no messy multi-GPU orchestration.
- Bare-metal ROCm performance keeps latency low enough for a live demo.
- Running the whole pipeline locally is what makes the cost story real.

## Pipeline

```
video → ffmpeg → SSIM scene filter → PaddleOCR + YOLO → CV event inference
      → VLM (72B on MI300X, ~5 key frames only) → coder model → Playwright script
      → headless replay → diff vs original → fix suggestion
```

The LLM is the last resort, not the first. Deterministic tools do 95% of the work so the VLM only sees the frames that actually matter.

## Repo layout

```
backend/            FastAPI service, pipeline stages
frontend/           Next.js UI (drag-drop, live progress, cost counter)
playwright-runner/  Runs generated .spec.ts files headless, diffs screenshots
ml/                 Model wrappers (vLLM + ROCm), prompts, tokenizers
scripts/            Setup, deploy, benchmark
samples/            Test videos and expected outputs
docs/               Architecture, demo script, submission draft
config/             Env templates, model configs
```

## Quick start (dev)

```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# frontend
cd frontend && npm install && npm run dev

# playwright runner
cd playwright-runner && npm install && npx playwright install chromium
```

See `docs/ARCHITECTURE.md` for the full design and `docs/BUILD_PLAN.md` for the 5-day plan.

## Status

Day 0 — scaffolding. See `docs/BUILD_PLAN.md`.
