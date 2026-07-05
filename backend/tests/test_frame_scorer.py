from __future__ import annotations

from pathlib import Path

import pytest

from app.pipeline.frame_scorer import (
    WEIGHTS,
    cheap_score,
    color_hist_chi2,
    cursor_jump_norm,
    error_signal,
    full_score,
    ocr_jaccard,
    phash_distance,
    ssim_distance,
    ui_edge_delta,
)


class TestSsim:
    def test_identical_frames_are_zero(self, blank_frame: Path, same_blank_frame: Path) -> None:
        assert ssim_distance(blank_frame, same_blank_frame) < 0.02

    def test_different_frames_are_positive(self, blank_frame: Path, frame_with_error: Path) -> None:
        assert ssim_distance(blank_frame, frame_with_error) > 0.1


class TestPhash:
    def test_identical_is_near_zero(self, blank_frame: Path, same_blank_frame: Path) -> None:
        assert phash_distance(blank_frame, same_blank_frame) < 0.1

    def test_different_is_larger(self, blank_frame: Path, frame_with_error: Path) -> None:
        assert phash_distance(blank_frame, frame_with_error) > 0.1


class TestOcrJaccard:
    def test_both_empty(self) -> None:
        assert ocr_jaccard(set(), set()) == 0.0

    def test_identical_tokens(self) -> None:
        assert ocr_jaccard({"submit", "cancel"}, {"submit", "cancel"}) == 0.0

    def test_completely_different(self) -> None:
        assert ocr_jaccard({"a"}, {"b"}) == 1.0

    def test_partial_overlap(self) -> None:
        # {a,b} vs {b,c} → intersection 1, union 3 → 1 - 1/3
        assert ocr_jaccard({"a", "b"}, {"b", "c"}) == pytest.approx(1 - 1 / 3)


class TestUiEdgeDelta:
    def test_identical(self, blank_frame: Path, same_blank_frame: Path) -> None:
        assert ui_edge_delta(blank_frame, same_blank_frame) < 0.05

    def test_new_button_appears(self, blank_frame: Path, frame_with_button: Path) -> None:
        assert ui_edge_delta(blank_frame, frame_with_button) > 0.001


class TestCursorJumpNorm:
    def test_none_returns_zero(self) -> None:
        assert cursor_jump_norm(None, (10, 10), (1000, 1000)) == 0.0
        assert cursor_jump_norm((10, 10), None, (1000, 1000)) == 0.0

    def test_zero_distance(self) -> None:
        assert cursor_jump_norm((100, 100), (100, 100), (1920, 1080)) == 0.0

    def test_diagonal_jump_normalized(self) -> None:
        v = cursor_jump_norm((0, 0), (1920, 1080), (1920, 1080))
        assert v == pytest.approx(1.0)

    def test_capped_at_one(self) -> None:
        v = cursor_jump_norm((0, 0), (10000, 10000), (100, 100))
        assert v == 1.0


class TestColorHistChi2:
    def test_identical(self, blank_frame: Path, same_blank_frame: Path) -> None:
        assert color_hist_chi2(blank_frame, same_blank_frame) < 0.05

    def test_error_frame_differs(self, blank_frame: Path, frame_with_error: Path) -> None:
        # The red bar is small (~7% of pixels), so chi2 is small too — just
        # assert it's meaningfully non-zero vs identical frames.
        identical = color_hist_chi2(blank_frame, blank_frame)
        different = color_hist_chi2(blank_frame, frame_with_error)
        assert different > identical * 5


class TestErrorSignal:
    def test_no_red_no_keyword(self, blank_frame: Path) -> None:
        assert error_signal(blank_frame, {"welcome"}) == 0.0

    def test_keyword_alone_scores(self, blank_frame: Path) -> None:
        # No red pixels but "500" hits the regex → keyword contribution.
        assert error_signal(blank_frame, {"500"}) > 0.5

    def test_red_pixels_score(self, frame_with_error: Path) -> None:
        assert error_signal(frame_with_error, set()) > 0.1

    def test_capped_at_one(self, frame_with_error: Path) -> None:
        assert error_signal(frame_with_error, {"error", "failed"}) <= 1.0


class TestWeights:
    def test_weights_sum_to_one(self) -> None:
        assert sum(WEIGHTS.values()) == pytest.approx(1.0)


class TestCheapScore:
    def test_identical_frames(self, blank_frame: Path, same_blank_frame: Path) -> None:
        assert cheap_score(blank_frame, same_blank_frame) < 0.05

    def test_different_frames(self, blank_frame: Path, frame_with_error: Path) -> None:
        assert cheap_score(blank_frame, frame_with_error) > 0.1


class TestFullScore:
    def test_produces_signals_in_range(self, blank_frame: Path, frame_with_error: Path) -> None:
        sig = full_score(
            prev_frame=blank_frame,
            curr_frame=frame_with_error,
            timestamp_s=1.0,
            prev_ocr=set(),
            curr_ocr={"500", "server", "error"},
            prev_cursor=None,
            curr_cursor=None,
            frame_size=(320, 180),
        )
        assert 0.0 <= sig.score <= 1.0
        assert sig.ocr_delta > 0
        assert sig.error_signal > 0
        assert sig.frame == frame_with_error.name

    def test_similar_frames_score_low(self, blank_frame: Path, same_blank_frame: Path) -> None:
        sig = full_score(
            prev_frame=blank_frame,
            curr_frame=same_blank_frame,
            timestamp_s=0.5,
            prev_ocr=set(),
            curr_ocr=set(),
            prev_cursor=None,
            curr_cursor=None,
            frame_size=(320, 180),
        )
        assert sig.score < 0.1
