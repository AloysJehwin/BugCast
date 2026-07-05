"""Real PaddleOCR smoke test. Skipped in environments without paddle installed
(CI, dev laptops without the ~700MB model download).
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

paddleocr = pytest.importorskip("paddleocr", reason="paddleocr not installed")

from ml.ocr.paddle import ocr_frame, ocr_text_set  # noqa: E402


@pytest.fixture(scope="module")
def synthetic_ui(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Render a fake login-screen bug: title, submit button, red error."""
    p = tmp_path_factory.mktemp("ocr") / "screen.png"
    img = np.full((280, 640, 3), 255, dtype=np.uint8)
    cv2.putText(img, "Sign in to your account", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (30, 30, 30), 2)
    cv2.putText(img, "Submit", (60, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 30, 30), 2)
    cv2.putText(img, "500 Server Error", (60, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 200), 2)
    cv2.imwrite(str(p), img)
    return p


class TestPaddleOcrReal:
    def test_extracts_expected_tokens(self, synthetic_ui: Path) -> None:
        tokens = ocr_frame(synthetic_ui)
        assert len(tokens) >= 3, f"expected at least 3 tokens, got {tokens}"
        joined = " ".join(t["text"].lower() for t in tokens)
        assert "sign in" in joined
        assert "submit" in joined
        assert "500" in joined

    def test_all_tokens_have_shape(self, synthetic_ui: Path) -> None:
        for tok in ocr_frame(synthetic_ui):
            assert set(tok.keys()) == {"text", "bbox", "conf"}
            assert len(tok["bbox"]) == 4
            assert tok["conf"] > 0.5

    def test_text_set_lowercases_and_dedupes(self, synthetic_ui: Path) -> None:
        tokens = ocr_text_set(synthetic_ui)
        assert all(t == t.lower() for t in tokens)
        assert len(tokens) >= 3

    def test_high_confidence_on_synthetic_input(self, synthetic_ui: Path) -> None:
        # Synthetic images should give near-perfect confidence.
        tokens = ocr_frame(synthetic_ui)
        assert all(t["conf"] > 0.9 for t in tokens), tokens
