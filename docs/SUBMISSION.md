# lablab.ai submission — draft

## Headline
BugCast — every user bug report becomes a runnable test.

## One-liner
Upload a screen recording of a broken flow. Get a Playwright script that reproduces the bug plus a suggested fix. Powered by a 72B vision-language model running locally on AMD MI300X.

## Problem
Bug reports are videos and Slack messages. Engineers spend hours rewatching, guessing intent, and failing to reproduce. Sending every frame to a hosted VLM is expensive, slow, and leaks user data.

## Solution
BugCast does 95% of the work with deterministic CV tools (OpenCV, PaddleOCR, YOLO) and only invokes the 72B VLM on the ~5 frames that actually matter. The VLM output feeds a coder model that emits a Playwright `.spec.ts` file. The script is replayed headless to confirm reproduction.

## Why AMD MI300X
- 192 GB HBM3 → Qwen2-VL-72B and Qwen2.5-Coder-32B co-reside on one GPU. No sharding.
- Bare-metal ROCm perf keeps end-to-end latency under 15 s for a 30-s video.
- Every frame stays on our infra — this is what makes the cost + privacy story real.

## Numbers (from `samples/outputs/`)
- End-to-end time on 30-s video: **< 15 s**
- Local tokens spent per run: **~10K**
- BugCast cost / run: **~$0.03**
- Naive GPT-4o pipeline cost / run: **~$2.14**
- **~70× cheaper**

## Team
- [your names + roles]

## Links
- Demo video: [YouTube link]
- Repo: [GitHub link]
- Live demo: [URL]
