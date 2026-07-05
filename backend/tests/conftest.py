"""Shared fixtures for BugCast tests.

We generate synthetic frames as PNGs in a tmp dir so tests are hermetic — no
real videos or model downloads needed for tier-1.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest


def _write(path: Path, img: np.ndarray) -> Path:
    cv2.imwrite(str(path), img)
    return path


def _blank(w: int = 320, h: int = 180, color: tuple[int, int, int] = (240, 240, 240)) -> np.ndarray:
    img = np.full((h, w, 3), color, dtype=np.uint8)
    return img


def _with_text(img: np.ndarray, text: str, org: tuple[int, int] = (20, 40)) -> np.ndarray:
    out = img.copy()
    cv2.putText(out, text, org, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 1, cv2.LINE_AA)
    return out


def _with_button(img: np.ndarray, xy: tuple[int, int], label: str = "Submit") -> np.ndarray:
    out = img.copy()
    x, y = xy
    cv2.rectangle(out, (x, y), (x + 90, y + 30), (100, 160, 100), -1)
    cv2.putText(out, label, (x + 8, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return out


def _with_red_error(img: np.ndarray) -> np.ndarray:
    out = img.copy()
    h, w = out.shape[:2]
    cv2.rectangle(out, (0, 0), (w, 40), (40, 40, 220), -1)  # red bar (BGR)
    cv2.putText(out, "500 Server Error", (10, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return out


@pytest.fixture
def frame_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def blank_frame(frame_dir: Path) -> Path:
    return _write(frame_dir / "f00.png", _blank())


@pytest.fixture
def same_blank_frame(frame_dir: Path) -> Path:
    return _write(frame_dir / "f00b.png", _blank())


@pytest.fixture
def frame_with_text(frame_dir: Path) -> Path:
    return _write(frame_dir / "f01.png", _with_text(_blank(), "Welcome"))


@pytest.fixture
def frame_with_button(frame_dir: Path) -> Path:
    return _write(frame_dir / "f02.png", _with_button(_blank(), (100, 90)))


@pytest.fixture
def frame_with_error(frame_dir: Path) -> Path:
    return _write(frame_dir / "f03.png", _with_red_error(_blank()))


@pytest.fixture
def flow_frames(frame_dir: Path) -> list[Path]:
    """A 4-frame 'user journey': blank → text → button → error."""
    frames = []
    frames.append(_write(frame_dir / "flow_00.png", _blank()))
    frames.append(_write(frame_dir / "flow_01.png", _with_text(_blank(), "Please log in")))
    frames.append(_write(frame_dir / "flow_02.png", _with_button(_with_text(_blank(), "Please log in"), (100, 90))))
    frames.append(_write(frame_dir / "flow_03.png", _with_red_error(_blank())))
    return frames
