"""Stage 6: turn event log + VLM summary into a Playwright .spec.ts file."""
from __future__ import annotations

from typing import Any

STUB_SCRIPT = """import { test, expect } from '@playwright/test';

test('reproduce user-reported bug', async ({ page }) => {
  await page.goto('about:blank');
  // TODO: real steps generated from event log
  await expect(page).toHaveTitle(/.*/);
});
"""


async def generate_script(*, events: list[dict[str, Any]], vlm_summary: dict[str, Any]) -> str:
    # TODO(day3): call coder model, feed events + summary, return real spec.
    return STUB_SCRIPT
