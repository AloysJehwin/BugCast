SCRIPT_GEN_PROMPT = """Convert this event log and VLM summary into a Playwright
TypeScript test that reproduces the failure. Rules:
- Use `test('reproduce user-reported bug', async ({ page }) => {...})`.
- Prefer `page.getByRole` and `page.getByText` — do not invent CSS selectors.
- After each action, add a short `await expect(...)` sanity check.
- End with an assertion that captures the observed failure (error modal text, missing element, etc.).
- Do NOT include comments explaining the code. Output only the .ts file contents."""
