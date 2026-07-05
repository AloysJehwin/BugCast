# Cursor templates

Drop small (~24–32 px) PNGs of cursor sprites here. Each PNG becomes a template
used by `cursor_tracker.py`. Naming is free-form (`arrow_mac.png`,
`pointer_windows.png`, `ibeam.png`, etc.) — the file stem is reported back as
`template` on each hit.

## What to include (Day 1 minimum)

- `arrow_default.png` — the standard OS arrow cursor
- `pointer_hand.png` — the "clickable" pointing-hand cursor
- `ibeam.png` — the text-input I-beam

## How to grab them

The cleanest way is to screenshot your own OS cursor at 2× zoom, crop tight,
and save as PNG with transparent background. On macOS:

```bash
screencapture -i -x cursor.png
```

Then crop in Preview. Aim for 24×24 or 32×32.

## Gitignored?

No — these are tiny (<5 KB) and load-bearing, commit them.
