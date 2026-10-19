"""Landmark → feature-vector preprocessing (pure NumPy, no MediaPipe import).

Raw landmarks depend on where your hand is in the frame, how close it is to
the camera and the shape of the frame. These functions remove all three so the
classifier only sees hand *shape*:

* all modes: `correct_aspect` puts x and y on the same scale, so a 4:3 webcam
  and a 3:2 video describe the same hand with the same numbers.
* hands: translate so the wrist is the origin, then divide by the hand's size
  (the largest distance from the wrist to any landmark).
* pose: translate to the hip centre, divide by shoulder width.

The same function is used for data collection (Stage 3), training (Stage 4) and
live inference (Stage 5). That is what keeps training and prediction consistent.

`augment_hands` makes extra training rows from saved vectors (slightly turned and
jittered hands). It works on the numbers only, at training time; nothing is saved.
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


def correct_aspect(landmarks: np.ndarray, width: int, height: int) -> np.ndarray:
    """Rescale MediaPipe landmarks of shape (n, 3) so x, y and z share one unit.

    MediaPipe gives x as a fraction of the frame width and y as a fraction of its
    height (z uses the same scale as x). Without this, a hand looks wider in a wide
    frame than in a narrow one. Multiplying x and z by width / height expresses all
    three in frame heights.
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"Frame size must be positive, got {width}x{height}")
    lm = np.array(landmarks, dtype=np.float32)
    lm[:, 0] *= width / height
    lm[:, 2] *= width / height
    return lm


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
    classify (no hand, or no pose in pose mode). Callers must show the
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


def augment_hands(X: np.ndarray, copies: int, rotation_deg: float, noise: float,
                  seed: int = 0) -> np.ndarray:
    """Extra training rows made from feature vectors: `copies` new rows per row.

    In each copy every visible hand is turned about its wrist, in the image plane, by a
    random angle within +-`rotation_deg` (a tilted head or camera), and every landmark
    moves by random noise with a spread of `noise` hand sizes (landmark jitter). The hand
    is then normalised again exactly as `normalize_hand` does, so a copy looks like a
    vector the camera could have produced. Missing hands stay zero, and pose columns
    ('hands+pose' mode) are copied unchanged.

    Rows come in blocks: rows [c * n, (c + 1) * n) are copy c of X, in X's order, so the
    labels are `np.tile(y, copies)`. The same seed gives the same rows.
    """
    X = np.asarray(X, dtype=np.float64)
    if X.ndim != 2 or X.shape[1] < 2 * HAND_FEATURES:
        raise ValueError(f"Expected rows of at least {2 * HAND_FEATURES} features (two hand slots).")
    if copies < 0 or rotation_deg < 0 or noise < 0:
        raise ValueError("copies, rotation_deg and noise must not be negative.")
    rng = np.random.default_rng(seed)
    out = np.tile(X, (copies, 1))
    for slot in (0, HAND_FEATURES):
        hands = out[:, slot:slot + HAND_FEATURES].reshape(-1, HAND_LANDMARKS, 3)
        present = np.abs(hands).sum(axis=(1, 2)) > 0
        angle = np.deg2rad(rng.uniform(-rotation_deg, rotation_deg, len(hands)))
        cos, sin = np.cos(angle)[:, None], np.sin(angle)[:, None]
        x, y = hands[:, :, 0].copy(), hands[:, :, 1].copy()
        hands[:, :, 0] = cos * x - sin * y
        hands[:, :, 1] = sin * x + cos * y
        hands += rng.normal(0.0, noise, hands.shape)
        hands -= hands[:, :1]                                   # wrist back to the origin
        scale = np.linalg.norm(hands[:, :, :2], axis=2).max(axis=1)
        hands /= np.where(scale > 1e-6, scale, 1.0)[:, None, None]
        hands[~present] = 0.0
        out[:, slot:slot + HAND_FEATURES] = hands.reshape(len(hands), -1)
    return out
