# BugCast — Architecture

## Core principle

The LLM is the last resort, not the first. Deterministic tools (ffmpeg, OpenCV, PaddleOCR, YOLO) filter and structure the video before any tokens are spent. The VLM only sees the ~5 frames that actually matter.

## Pipeline stages

```
1. INGEST         ffmpeg           mp4 → PNG frames @ 2fps
2. FRAME FILTER   two-pass scorer  pass 1 SSIM+pHash → pass 2 multi-signal score
3. UI EXTRACT     PaddleOCR 3.7    text + bboxes + confidences (PP-OCRv6 mobile)
4. EVENT INFER    OpenCV           cursor tracking, clicks, typing, error modals
5. VLM REASONING  Qwen2-VL-72B     intent + failure point (MI300X, ~5 frames)
6. SCRIPT GEN     Qwen2.5-Coder    Playwright .spec.ts from event log
7. REPLAY + DIFF  Playwright       headless run, screenshot diff vs original
8. FIX SUGGEST    coder model      code diff suggestion (optional)
```

## Token budget (target)

| Stage | Local tokens |
|---|---|
| Stages 1–4 (deterministic) | 0 |
| VLM reasoning (5 frames × ~1500 tok) | ~7,500 |
| Script generation | ~2,000 |
| Replay validation | ~500 |
| **Total per video** | **~10K local** |

Naive baseline (send 60 frames to GPT-4o): ~300K tokens → ~30× cheaper before infra. With local Qwen on MI300X the marginal cost is ~$0 → ~70× on the pitch.

## Frame scoring (stage 2 in detail)

Every frame is scored by a weighted sum of deterministic signals:

| Signal | Weight | Detects |
|---|---|---|
| SSIM distance | 0.15 | structural change |
| pHash Hamming | 0.10 | perceptual/theme change |
| OCR token Jaccard | **0.30** | new/removed text (the strongest signal) |
| UI edge delta | 0.15 | new buttons/modals |
| Cursor jump | 0.10 | user action location |
| HSV histogram χ² | 0.05 | broad scene shift |
| Error signal | 0.15 | red pixels + regex `error|failed|500…` |

**Two-pass:** SSIM+pHash on all frames first (cheap), then full scoring only on
survivors (OCR is the expensive step). Selection uses guardrails — always keep
first/last frame, keep neighbours of spike frames for context, enforce min
time-gap between kept frames. Not naive top-K.

Every per-frame score is written to `samples/outputs/<job>/scores.json` for
threshold tuning and for the UI timeline strip.

## Stack

- Python 3.11, FastAPI, Uvicorn
- OpenCV, PaddleOCR, YOLOv8, scikit-image (SSIM)
- vLLM with ROCm, Qwen2-VL-72B-Instruct, Qwen2.5-Coder-32B
- Fireworks AI API as fallback (`$50` credits)
- Playwright (TypeScript, headless Chromium)
- Next.js 14 (App Router), Tailwind
- Deployed on AMD Developer Cloud

## Data contracts

### Frame metadata (stage 3 output)
```json
{
  "frame_id": "0007",
  "timestamp_s": 3.5,
  "ocr": [{ "text": "Submit", "bbox": [x, y, w, h], "conf": 0.98 }],
  "ui_elements": [{ "type": "button", "bbox": [...], "label": "Submit" }]
}
```

### Event log (stage 4 output)
```json
[
  { "t": 1.2, "action": "click", "target": "Submit", "bbox": [...] },
  { "t": 2.4, "action": "type", "target": "email", "value": "***" },
  { "t": 3.1, "action": "error_modal", "text": "500 Internal Server Error" }
]
```

### VLM output (stage 5)
```json
{
  "intent": "complete checkout",
  "steps": ["fill email", "click continue", "submit payment"],
  "broke_at_step": 3,
  "symptom": "500 error on payment submit",
  "hypothesis": "backend timeout or bad state"
}
```

## The demo money shot

Split screen: original bug video (left), generated Playwright script running headless (right), live cost counter at bottom showing "$0.03 spent" vs greyed-out "GPT-4o cost: $2.14". Ends with a green checkmark and a one-line fix suggestion.

See `docs/DEMO_SCRIPT.md`.
