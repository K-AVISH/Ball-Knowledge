"""Stage 1 tests: frame processing works without any webcam."""
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import vision  # noqa: E402
from vision import FrameProcessor, camera_is_live  # noqa: E402


def fake_frame(h=480, w=640):
    f = np.zeros((h, w, 3), dtype=np.uint8)
    f[:, :10] = 255  # white strip on the left so we can check mirroring
    return f


def test_process_mirrors_and_keeps_shape():
    p = FrameProcessor()
    out = p.process(fake_frame())
    assert out.shape == (480, 640, 3)
    assert out[0, -1].tolist() == [255, 255, 255]  # strip moved to the right
    assert out[0, 0].tolist() == [0, 0, 0]


def test_stats_update_and_camera_live():
    p = FrameProcessor()
    for _ in range(5):
        p.process(fake_frame())
    s = p.get_stats()
    assert s.frames_processed == 5
    assert (s.frame_width, s.frame_height) == (640, 480)
    assert s.fps > 0
    assert camera_is_live(s)


def test_fps_matches_frame_rate_when_frames_arrive_unevenly(monkeypatch):
    # 15 frames per second on average, but arriving in uneven pairs (10 ms then 123 ms
    # apart), as WebRTC often delivers them. Averaging 1/gap would report about 54.
    gaps = [0.010, 2 / 15 - 0.010] * 60
    ticks = [0.0]
    for gap in gaps:
        ticks.append(ticks[-1] + gap)
    calls = iter(t for t in ticks for _ in range(2))      # process() reads the clock twice
    monkeypatch.setattr(vision, "time", SimpleNamespace(perf_counter=lambda: next(calls),
                                                        time=lambda: 0.0))
    p = FrameProcessor()
    for _ in ticks:
        p.process(fake_frame())
    assert abs(p.get_stats().fps - 15) < 1


def test_stale_camera_is_not_live():
    p = FrameProcessor()
    p.process(fake_frame())
    s = p.get_stats()
    s.last_frame_time -= 10
    assert not camera_is_live(s)


def test_reset_clears_stats():
    p = FrameProcessor()
    p.process(fake_frame())
    p.reset()
    s = p.get_stats()
    assert s.frames_processed == 0
    assert not camera_is_live(s)


def test_hook_error_is_reported_not_raised():
    def bad_hook(frame):
        raise RuntimeError("boom")

    p = FrameProcessor(frame_hook=bad_hook)
    out = p.process(fake_frame())
    assert out.shape == (480, 640, 3)
    assert "boom" in p.get_stats().error


def test_hook_info_sets_hand_detected():
    p = FrameProcessor(frame_hook=lambda f: (f, {"hand_detected": True}))
    p.process(fake_frame())
    assert p.get_stats().hand_detected
