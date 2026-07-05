# BugCast — 5-Day Build Plan

Hackathon: AMD ACT II, July 6–11 2026. Each day has a **cut-line** — the minimum shippable state if everything downstream fails.

## Day 1 (Sun Jul 6) — Skeleton end-to-end
- [ ] Repo scaffold (this commit)
- [ ] `POST /analyze` accepts a video, runs stub pipeline, returns stub script
- [ ] SSIM frame filter working on a real video
- [ ] PaddleOCR on filtered frames → JSON
- [ ] Playwright runner executes a hardcoded `.spec.ts` and returns pass/fail

**Cut-line:** `curl -F video=@bug.mp4 localhost:8000/analyze` returns something end-to-end.

## Day 2 (Mon Jul 7) — MI300X + VLM online
- [ ] Provision MI300X on AMD Developer Cloud
- [ ] Install ROCm + vLLM, load Qwen2-VL-72B
- [ ] Benchmark: 5 frames + prompt → response (target <10s)
- [ ] Cursor tracking with OpenCV template match
- [ ] Click / type / error-modal event inference

**Cut-line:** real bug video → correct human-readable event log.

## Day 3 (Tue Jul 8) — Script gen + replay loop
- [ ] Qwen2.5-Coder-32B on MI300X (or Fireworks fallback)
- [ ] Playwright script template + selector filling from OCR bboxes
- [ ] Headless replay + screenshot diff vs original
- [ ] Retry loop (max 2 iterations)
- [ ] Record 3 real test videos

**Cut-line:** 2 of 3 test videos produce a script that reproduces the bug. Do not slip past this day without it.

## Day 4 (Wed Jul 9) — Fix suggestion + UI polish
- [ ] Fix suggestion endpoint
- [ ] Next.js UI: drag-drop, live progress, side-by-side view
- [ ] Cost counter (prominent) — local spend vs GPT-4o equivalent
- [ ] Download `.spec.ts`, copy-to-Jira buttons
- [ ] Edge cases: no bug, video too long, unclear intent

**Cut-line:** a stranger can use the UI without instructions.

## Day 5 (Thu Jul 10) — Demo + submission
- [ ] 2-minute demo video (scripted, not improvised)
- [ ] lablab.ai project page
- [ ] Deploy publicly + record fallback video
- [ ] Submit before deadline (Fri Jul 11 buffer)

**Cut-line:** submitted with working demo video.

## Drop order (if behind)
1. Fix suggestion
2. Replay retry loop
3. YOLO UI detection
4. Local coder model (use Fireworks API instead)

**Never drop:** cost counter + MI300X justification.

## Team split (2 people)
- **Person A (infra/ML):** MI300X, VLM, coder, ROCm
- **Person B (product):** ingest, OpenCV, UI, demo video, submission

20-min sync each morning. That's it.
