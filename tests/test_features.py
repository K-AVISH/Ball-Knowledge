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


# --- training-time augmentation ------------------------------------------------

def hand_rows(n=6, seed=0):
    """Feature vectors as the camera makes them: some with two hands, some with one."""
    rows = []
    for i in range(n):
        right = fake_hand(seed + i) if i % 3 != 2 else None
        left = fake_hand(seed + 100 + i) if i % 3 != 0 else None
        rows.append(F.build_feature_vector(right_hand=right, left_hand=left, mode="hands"))
    return np.array(rows)


def test_augmented_rows_come_in_blocks_and_are_normalised_hands():
    X = hand_rows()
    out = F.augment_hands(X, copies=3, rotation_deg=15, noise=0.01, seed=0)
    assert out.shape == (3 * len(X), X.shape[1])
    for row, source in zip(out, np.tile(X, (3, 1))):
        for slot in (slice(0, 63), slice(63, 126)):
            hand, original = row[slot].reshape(21, 3), source[slot]
            if not original.any():
                assert not hand.any()                  # a missing hand stays missing
                continue
            assert np.allclose(hand[0], 0)              # wrist at the origin
            assert np.linalg.norm(hand[:, :2], axis=1).max() == pytest.approx(1.0)
            assert not np.allclose(hand.reshape(-1), original)   # it did change


def test_augmentation_without_noise_turns_the_hand_rigidly():
    X = hand_rows()
    out = F.augment_hands(X, copies=1, rotation_deg=30, noise=0.0, seed=3)
    for row, source in zip(out, X):
        a, b = row[:63].reshape(21, 3), source[:63].reshape(21, 3)
        if not source[:63].any():
            continue
        dist = lambda h: np.linalg.norm(h[:, None] - h[None], axis=2)
        assert np.allclose(dist(a), dist(b), atol=1e-5)          # same shape
        assert np.allclose(a[:, 2], b[:, 2], atol=1e-6)          # turned in the image plane only
        angle = np.degrees(np.arctan2(a[1:, 1], a[1:, 0]) - np.arctan2(b[1:, 1], b[1:, 0]))
        assert np.all(np.abs((angle + 180) % 360 - 180) <= 30 + 1e-3)


def test_augmentation_is_repeatable_and_off_without_rotation_or_noise():
    X = hand_rows()
    a = F.augment_hands(X, 2, 15, 0.01, seed=7)
    assert np.array_equal(a, F.augment_hands(X, 2, 15, 0.01, seed=7))
    assert not np.array_equal(a, F.augment_hands(X, 2, 15, 0.01, seed=8))
    assert np.allclose(F.augment_hands(X, 2, 0, 0, seed=7), np.tile(X, (2, 1)), atol=1e-6)


def test_augmentation_leaves_pose_columns_alone():
    pose = np.random.default_rng(5).uniform(0, 1, size=(33, 3)).astype(np.float32)
    X = np.array([F.build_feature_vector(right_hand=fake_hand(i), pose=pose, mode="hands+pose")
                  for i in range(4)])
    out = F.augment_hands(X, copies=2, rotation_deg=15, noise=0.01)
    assert np.array_equal(out[:, 126:], np.tile(X[:, 126:], (2, 1)))


@pytest.mark.parametrize("X,kwargs", [
    (np.zeros((3, 10)), {}),
    (np.zeros((3, 126)), {"copies": -1}),
    (np.zeros((3, 126)), {"noise": -0.1}),
])
def test_augmentation_rejects_bad_input(X, kwargs):
    args = {"copies": 1, "rotation_deg": 10, "noise": 0.01, **kwargs}
    with pytest.raises(ValueError):
        F.augment_hands(X, **args)
