"""Landmark → feature-vector preprocessing (pure NumPy, no MediaPipe import).

Raw landmarks depend on where your hand is in the frame and how close it is to
the camera. These functions remove both so the classifier only sees hand *shape*:

* hands: translate so the wrist is the origin, then divide by the hand's size
  (the largest distance from the wrist to any landmark).
* pose: translate to the hip centre, divide by shoulder width.

The same function is used for data collection (Stage 3), training (Stage 4) and
live inference (Stage 5) — that is what keeps training and prediction consistent.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

import config

HAND_LANDMARKS = 21
POSE_LANDMARKS = 33
# MediaPipe pose indices
L_SHOULDER, R_SHOULDER, L_HIP, R_HIP = 11, 12, 23, 24

HAND_FEATURES = HAND_LANDMARKS * 3          # x, y, z per landmark
POSE_FEATURES = POSE_LANDMARKS * 3


def feature_length(mode: str = config.FEATURE_MODE) -> int:
    """Length of the vector produced by `build_feature_vector` for a mode."""
    _check_mode(mode)
    n = 2 * HAND_FEATURES                    # slot for each hand
    return n + POSE_FEATURES if mode == "hands+pose" else n


def _check_mode(mode: str) -> None:
    if mode not in ("hands", "hands+pose"):
        raise ValueError(f"Unknown feature mode {mode!r}; use 'hands' or 'hands+pose'.")


def normalize_hand(landmarks: np.ndarray, mirror: bool = False) -> np.ndarray:
    """Normalise one hand of shape (21, 3) → flat vector of length 63.

    `mirror=True` flips x so a left hand looks like a right hand.
    Raises ValueError for malformed or degenerate input.
    """
    lm = np.asarray(landmarks, dtype=np.float32)
    if lm.shape != (HAND_LANDMARKS, 3):
        raise ValueError(f"Expected hand landmarks of shape (21, 3), got {lm.shape}")
    if not np.isfinite(lm).all():
        raise ValueError("Hand landmarks contain NaN or infinity")
    lm = lm - lm[0]                          # wrist (landmark 0) becomes origin
    if mirror:
        lm[:, 0] = -lm[:, 0]
    scale = float(np.linalg.norm(lm[:, :2], axis=1).max())
    if scale < 1e-6:
        raise ValueError("Degenerate hand: all landmarks at the same point")
    return (lm / scale).reshape(-1)


def normalize_pose(landmarks: np.ndarray) -> np.ndarray:
    """Normalise body pose of shape (33, 3) → flat vector of length 99."""
    lm = np.asarray(landmarks, dtype=np.float32)
    if lm.shape != (POSE_LANDMARKS, 3):
        raise ValueError(f"Expected pose landmarks of shape (33, 3), got {lm.shape}")
    if not np.isfinite(lm).all():
        raise ValueError("Pose landmarks contain NaN or infinity")
    centre = (lm[L_HIP] + lm[R_HIP]) / 2
    scale = float(np.linalg.norm((lm[L_SHOULDER] - lm[R_SHOULDER])[:2]))
    if scale < 1e-6:
        raise ValueError("Degenerate pose: shoulders at the same point")
    return ((lm - centre) / scale).reshape(-1)


def build_feature_vector(
    right_hand: Optional[np.ndarray] = None,
    left_hand: Optional[np.ndarray] = None,
    pose: Optional[np.ndarray] = None,
    mode: str = config.FEATURE_MODE,
) -> Optional[np.ndarray]:
    """Combine detections into one fixed-length feature vector.

    Layout: [right hand 63][left hand 63] (+ [pose 99] in 'hands+pose' mode).
    A missing hand is zero-filled, so "one hand shown" and "two hands shown"
    are different, learnable patterns. Returns None when there is nothing to
    classify (no hand, or no pose in pose mode) — callers must show the
    "no hand" state instead of guessing.
    """
    _check_mode(mode)
    if right_hand is None and left_hand is None:
        return None
    parts = [
        normalize_hand(right_hand) if right_hand is not None else np.zeros(HAND_FEATURES, np.float32),
        # left hand is mirrored so it shares the same shape space as the right hand
        normalize_hand(left_hand, mirror=True) if left_hand is not None else np.zeros(HAND_FEATURES, np.float32),
    ]
    if mode == "hands+pose":
        if pose is None:
            return None
        parts.append(normalize_pose(pose))
    return np.concatenate(parts).astype(np.float32)
