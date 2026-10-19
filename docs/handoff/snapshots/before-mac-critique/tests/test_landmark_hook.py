"""Stage 2 tests: landmark hook, drawing and feature output using a stand-in
detector. No webcam, MediaPipe model or network needed."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import features  # noqa: E402
import vision  # noqa: E402
from vision import Detection, FrameProcessor, HandDetection, LandmarkHook  # noqa: E402


def hand_points(seed=0):
    return np.random.default_rng(seed).uniform(0.2, 0.8, size=(21, 3)).astype(np.float32)


class FakeDetector:
    def __init__(self, detection):
        self.detection = detection
        self.closed = False

    def detect(self, frame):
        return self.detection

    def close(self):
        self.closed = True


def blank():
    return np.zeros((480, 640, 3), dtype=np.uint8)


def test_no_hand_gives_no_features():
    hook = LandmarkHook(detector_factory=lambda: FakeDetector(Detection()))
    frame, info = hook(blank())
    assert info["hand_detected"] is False and info["num_hands"] == 0
    assert info["features"] is None
    assert not frame.any()                      # nothing drawn


def test_one_hand_gives_features_and_draws():
    det = Detection(hands=[HandDetection("Right", 0.9, hand_points())])
    hook = LandmarkHook(detector_factory=lambda: FakeDetector(det))
    frame, info = hook(blank())
    assert info["hand_detected"] and info["num_hands"] == 1
    assert info["features"].shape == (features.feature_length("hands"),)
    assert frame.any()                          # landmarks were drawn


def test_toggle_landmarks_off_draws_nothing_but_still_detects():
    det = Detection(hands=[HandDetection("Left", 0.8, hand_points())])
    hook = LandmarkHook(detector_factory=lambda: FakeDetector(det))
    hook.show_landmarks = False
    frame, info = hook(blank())
    assert not frame.any()
    assert info["features"] is not None


def test_two_hands_fill_both_slots():
    det = Detection(hands=[HandDetection("Right", 0.9, hand_points(1)),
                           HandDetection("Left", 0.9, hand_points(2))])
    _, info = LandmarkHook(detector_factory=lambda: FakeDetector(det))(blank())
    v = info["features"]
    assert info["num_hands"] == 2
    assert v[:63].any() and v[63:126].any()


def test_duplicate_labels_keep_most_confident():
    weak, strong = hand_points(3), hand_points(4)
    det = Detection(hands=[HandDetection("Right", 0.5, weak),
                           HandDetection("Right", 0.95, strong)])
    _, info = LandmarkHook(detector_factory=lambda: FakeDetector(det))(blank())
    assert np.allclose(info["features"][:63],
                       features.normalize_hand(features.correct_aspect(strong, 640, 480)))


def test_same_hand_gives_same_features_in_any_frame_shape():
    # One hand in pixels, seen by a 4:3 webcam and by a 3:2 video. MediaPipe would report
    # it as fractions of each frame's width and height, so the raw numbers differ.
    px = np.random.default_rng(7).uniform(100, 400, size=(21, 3)).astype(np.float32)
    vectors = []
    for w, h in ((640, 480), (1620, 1080), (720, 480)):
        lm = np.stack([px[:, 0] / w, px[:, 1] / h, px[:, 2] / w], axis=1)
        det = Detection(hands=[HandDetection("Right", 0.9, lm)])
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        _, info = LandmarkHook(detector_factory=lambda: FakeDetector(det))(frame)
        vectors.append(info["features"])
    assert np.allclose(vectors[0], vectors[1], atol=1e-5)
    assert np.allclose(vectors[0], vectors[2], atol=1e-5)


def test_degenerate_landmarks_are_treated_as_no_features():
    flat = np.zeros((21, 3), dtype=np.float32)
    det = Detection(hands=[HandDetection("Right", 0.9, flat)])
    _, info = LandmarkHook(detector_factory=lambda: FakeDetector(det))(blank())
    assert info["features"] is None


def test_pose_mode_requires_pose():
    det = Detection(hands=[HandDetection("Right", 0.9, hand_points())])
    hook = LandmarkHook(detector_factory=lambda: FakeDetector(det), mode="hands+pose")
    _, info = hook(blank())
    assert info["features"] is None
    pose = np.random.default_rng(5).uniform(0, 1, size=(33, 3)).astype(np.float32)
    det.pose = pose
    _, info = hook(blank())
    assert info["pose_detected"] and info["features"].shape == (225,)


def test_missing_model_is_reported_not_raised(tmp_path, monkeypatch):
    pytest.importorskip("mediapipe")
    monkeypatch.setattr(vision, "HAND_MODEL_PATH", tmp_path / "nope.task")
    proc = FrameProcessor(frame_hook=LandmarkHook())
    out = proc.process(blank())                 # must not raise
    assert out.shape == (480, 640, 3)
    assert "download_models.py" in proc.get_stats().error
    proc.process(blank())                       # second frame: same clear error
    assert "download_models.py" in proc.get_stats().error


def test_processor_exposes_latest_features_and_resets():
    det = Detection(hands=[HandDetection("Right", 0.9, hand_points())])
    proc = FrameProcessor(frame_hook=LandmarkHook(detector_factory=lambda: FakeDetector(det)))
    proc.process(blank())
    s = proc.get_stats()
    assert s.hand_detected and s.num_hands == 1
    assert proc.get_latest_features().shape == (126,)
    proc.reset()
    assert proc.get_latest_features() is None


def test_close_closes_detector():
    fake = FakeDetector(Detection())
    hook = LandmarkHook(detector_factory=lambda: fake)
    hook(blank())
    hook.close()
    assert fake.closed
