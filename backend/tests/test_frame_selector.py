from __future__ import annotations

from pathlib import Path

from app.pipeline.frame_scorer import FrameSignals
from app.pipeline.frame_selector import select_key_frames


def _sig(name: str, t: float, score: float) -> FrameSignals:
    return FrameSignals(frame=name, timestamp_s=t, score=score)


def _dummy_frame_paths(names: list[str]) -> list[Path]:
    return [Path(n) for n in names]


class TestSelectKeyFrames:
    def test_empty_input(self) -> None:
        assert select_key_frames([], []) == []

    def test_first_and_last_always_kept(self) -> None:
        signals = [
            _sig("a.png", 0.0, 0.05),
            _sig("b.png", 1.0, 0.9),  # spike
            _sig("c.png", 2.0, 0.06),
            _sig("d.png", 3.0, 0.04),
        ]
        selected = select_key_frames(signals, _dummy_frame_paths(["a.png", "b.png", "c.png", "d.png"]), max_key_frames=3)
        names = [s.frame for s in selected]
        assert "a.png" in names
        assert "d.png" in names

    def test_cap_respected(self) -> None:
        signals = [_sig(f"f{i}.png", float(i), 0.4 + 0.01 * i) for i in range(20)]
        selected = select_key_frames(signals, _dummy_frame_paths([s.frame for s in signals]), max_key_frames=5)
        assert len(selected) == 5

    def test_min_gap_enforced(self) -> None:
        # Two high-scoring frames only 0.05s apart — the selector should not keep both
        # unless spike-neighbour logic explicitly does. Use flat scores to isolate spacing.
        signals = [
            _sig("a.png", 0.0, 0.1),
            _sig("b.png", 0.05, 0.5),
            _sig("c.png", 0.10, 0.5),
            _sig("d.png", 2.0, 0.1),
        ]
        selected = select_key_frames(
            signals,
            _dummy_frame_paths(["a.png", "b.png", "c.png", "d.png"]),
            max_key_frames=5,
            min_gap_s=0.2,
        )
        # a and d are first/last, always kept. Between b and c only one may enter
        # via the score-fill path (they're not spikes with such flat scores).
        middle = [s.frame for s in selected if s.frame not in ("a.png", "d.png")]
        assert len(middle) <= 1

    def test_spike_keeps_neighbour(self) -> None:
        # A big spike at index 2 — the selector should also keep index 1 for context.
        signals = [
            _sig("a.png", 0.0, 0.05),
            _sig("b.png", 1.0, 0.10),
            _sig("c.png", 2.0, 0.95),  # spike
            _sig("d.png", 3.0, 0.10),
            _sig("e.png", 4.0, 0.05),
        ]
        selected = select_key_frames(
            signals,
            _dummy_frame_paths([s.frame for s in signals]),
            max_key_frames=5,
        )
        names = {s.frame for s in selected}
        assert "c.png" in names  # the spike itself
        assert "b.png" in names  # the "before" neighbour

    def test_returns_time_sorted(self) -> None:
        signals = [
            _sig("z.png", 3.0, 0.1),
            _sig("a.png", 0.0, 0.1),
            _sig("m.png", 1.5, 0.9),
        ]
        selected = select_key_frames(
            signals,
            _dummy_frame_paths([s.frame for s in signals]),
            max_key_frames=5,
        )
        timestamps = [s.timestamp_s for s in selected]
        assert timestamps == sorted(timestamps)

    def test_single_frame(self) -> None:
        signals = [_sig("only.png", 0.0, 0.5)]
        selected = select_key_frames(signals, _dummy_frame_paths(["only.png"]), max_key_frames=5)
        assert len(selected) == 1
        assert selected[0].frame == "only.png"
