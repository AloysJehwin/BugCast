# Demo Video Script (≤ 2 min)

## 0:00–0:15 — The problem
> "Every dev knows this pain: a user sends a Loom video of a bug. You watch 90 seconds of them clicking around, still not sure what broke, and you can't reproduce it."

Show: a real Loom-style bug report video.

## 0:15–0:45 — The magic
> "BugCast turns that video into a runnable Playwright test. Drag it in..."

Show: drag-drop upload. Live progress steps light up:
- Frames extracted (60 → 8)
- OCR done
- Events inferred (5 clicks, 1 error modal)
- VLM reasoning on MI300X (2.3s)
- Script generated

## 0:45–1:15 — The proof
> "Here's the generated script. Let's run it."

Show: split screen. Original video plays on the left. Generated Playwright script runs headless on the right. They complete the same flow. The bug reproduces. Green checkmark.

## 1:15–1:45 — The MI300X story
> "Every frame stayed on our infra. We ran a 72-billion-parameter vision model locally on a single AMD MI300X — 192 GB of HBM3 makes that possible without sharding. Look at the counter:"

Show: prominent counter.
- BugCast cost: **$0.03**
- GPT-4o pipeline cost: **$2.14**
- **~70× cheaper**

## 1:45–2:00 — The ask
> "BugCast. Every bug report becomes a runnable test. Try it at bugcast.dev."

Show: URL + QR code.

## Recording notes
- Record at 1920×1080, 30fps.
- No talking-head. Voiceover only.
- Text on screen for every key claim (judges may watch muted).
- End card holds 3 seconds so it's screenshottable.
