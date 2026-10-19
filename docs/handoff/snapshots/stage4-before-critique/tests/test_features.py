"""Stage 2 tests: landmark normalisation (no MediaPipe or webcam needed)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import features as F  # noqa: E402


def fake_hand(seed=0):
    rng = np.random.default_rng(seed)
    return rng.uniform(0.2, 0.8, size=(21, 3)).astype(np.float32)


def test_hand_vector_length_and_wrist_at_origin():
    v = F.normalize_hand(fake_hand())
    assert v.shape == (63,)
    assert np.allclose(v[:3], 0)               # wrist is landmark 0


def test_hand_translation_invariant():
    h = fake_hand()
    shifted = h + np.array([0.3, -0.1, 0.0], dtype=np.float32)
    assert np.allclose(F.normalize_hand(h), F.normalize_hand(shifted), atol=1e-5)


def test_hand_scale_invariant():
    h = fake_hand()
    assert np.allclose(F.normalize_hand(h), F.normalize_hand(h * 0.5), atol=1e-5)


def test_mirror_flips_x_only():
    h = fake_hand()
    a = F.normalize_hand(h).reshape(21, 3)
    b = F.normalize_hand(h, mirror=True).reshape(21, 3)
    assert np.allclose(a[:, 0], -b[:, 0]) and np.allclose(a[:, 1:], b[:, 1:])


@pytest.mark.parametrize("bad", [np.zeros((20, 3)), np.zeros((21, 2)), np.zeros((21, 3))])
def test_malformed_or_degenerate_hand_raises(bad):
    with pytest.raises(ValueError):
        F.normalize_hand(bad)


def test_nan_hand_raises():
    h = fake_hand()
    h[3, 1] = np.nan
    with pytest.raises(ValueError):
        F.normalize_hand(h)


def test_no_hand_returns_none():
    assert F.build_feature_vector() is None


def test_one_hand_vs_other_hand_differ_and_fixed_length():
    h = fake_hand()
    right_only = F.build_feature_vector(right_hand=h, mode="hands")
    left_only = F.build_feature_vector(left_hand=h, mode="hands")
    assert right_only.shape == left_only.shape == (F.feature_length("hands"),) == (126,)
    assert np.allclose(right_only[63:], 0) and np.allclose(left_only[:63], 0)


def test_pose_mode_needs_pose_and_adds_features():
    h = fake_hand()
    assert F.build_feature_vector(right_hand=h, mode="hands+pose") is None
    pose = np.random.default_rng(1).uniform(0, 1, size=(33, 3)).astype(np.float32)
    v = F.build_feature_vector(right_hand=h, pose=pose, mode="hands+pose")
    assert v.shape == (F.feature_length("hands+pose"),) == (225,)


def test_pose_invariance_and_degenerate():
    pose = np.random.default_rng(2).uniform(0, 1, size=(33, 3)).astype(np.float32)
    assert np.allclose(F.normalize_pose(pose), F.normalize_pose(pose * 2 + 0.1), atol=1e-4)
    flat = np.zeros((33, 3), np.float32)
    with pytest.raises(ValueError):
        F.normalize_pose(flat)


def test_unknown_mode_raises():
    with pytest.raises(ValueError):
        F.feature_length("hands+feet")
