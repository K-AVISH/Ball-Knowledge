"""Webcam frame processing.

Stage 1: a thread-safe processor that receives frames from the browser camera
stream, annotates them, and publishes live stats (FPS, frame size, last frame
time). Landmark detection is plugged in during Stage 2 through the
`frame_hook` argument, so this file stays the single place that touches frames.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

import cv2
import numpy as np

import config
import features

# A hook takes a BGR frame and returns (annotated_frame, info_dict).
FrameHook = Callable[[np.ndarray], "tuple[np.ndarray, dict]"]


@dataclass
class VisionStats:
    """Snapshot of what the video thread is doing, read by the dashboard."""

    fps: float = 0.0
    latency_ms: float = 0.0
    frames_processed: int = 0
    frame_width: int = 0
    frame_height: int = 0
    last_frame_time: float = 0.0   # time.time() of the most recent frame
    hand_detected: bool = False
    num_hands: int = 0
    pose_detected: bool = False
    error: Optional[str] = None


class FrameProcessor:
    """Processes frames on the WebRTC thread and exposes stats to Streamlit.

    The dashboard (main Streamlit thread) only ever calls `get_stats()`, which
    returns a copy under a lock, so there are no data races.
    """

    def __init__(self, frame_hook: Optional[FrameHook] = None) -> None:
        self._lock = threading.Lock()
        self._stats = VisionStats()
        self._frame_hook = frame_hook
        self._last_tick: Optional[float] = None
        self._latest_features: Optional[np.ndarray] = None
        # Optional objects with `offer(features_or_None)`. Both receive the same feature
        # vector: the recorder (set by the data collector page) saves it as a training
        # sample, the recognizer (set by the dashboard) classifies it on its own thread.
        self.recorder = None
        self.recognizer = None

    def process(self, frame: np.ndarray) -> np.ndarray:
        """Annotate one BGR frame and update stats. Never raises."""
        start = time.perf_counter()
        info: dict = {}
        try:
            frame = np.ascontiguousarray(frame[:, ::-1])  # mirror: feels natural
            if self._frame_hook is not None:
                frame, info = self._frame_hook(frame)
            error = None
            if self.recorder is not None:
                self.recorder.offer(info.get("features"))
            if self.recognizer is not None:
                self.recognizer.offer(info.get("features"))    # returns at once
        except Exception as exc:  # keep the stream alive, surface the message
            error = f"{type(exc).__name__}: {exc}"

        now = time.perf_counter()
        with self._lock:
            s = self._stats
            if self._last_tick is not None:
                dt = now - self._last_tick
                if dt > 0:
                    inst = 1.0 / dt
                    s.fps = inst if s.fps == 0 else (
                        config.FPS_SMOOTHING * s.fps + (1 - config.FPS_SMOOTHING) * inst
                    )
            self._last_tick = now
            s.latency_ms = (now - start) * 1000
            s.frames_processed += 1
            s.frame_height, s.frame_width = frame.shape[:2]
            s.last_frame_time = time.time()
            s.hand_detected = bool(info.get("hand_detected", False))
            s.num_hands = int(info.get("num_hands", 0))
            s.pose_detected = bool(info.get("pose_detected", False))
            s.error = error
            self._latest_features = info.get("features")
        return frame

    def get_latest_features(self) -> Optional[np.ndarray]:
        """Most recent feature vector (None if no hand was visible)."""
        with self._lock:
            return None if self._latest_features is None else self._latest_features.copy()

    def get_stats(self) -> VisionStats:
        with self._lock:
            return VisionStats(**self._stats.__dict__)

    def reset(self) -> None:
        with self._lock:
            self._stats = VisionStats()
            self._last_tick = None
            self._latest_features = None


def camera_is_live(stats: VisionStats, max_age_s: float = 2.0) -> bool:
    """True if a frame arrived recently (detects a stalled/disconnected camera)."""
    return stats.last_frame_time > 0 and (time.time() - stats.last_frame_time) < max_age_s


# ---------------------------------------------------------------------------
# Landmark detection (Stage 2)
# ---------------------------------------------------------------------------

HAND_MODEL_PATH = config.MEDIAPIPE_MODELS_DIR / "hand_landmarker.task"
POSE_MODEL_PATH = config.MEDIAPIPE_MODELS_DIR / "pose_landmarker_lite.task"

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),            # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),            # index
    (5, 9), (9, 10), (10, 11), (11, 12),       # middle
    (9, 13), (13, 14), (14, 15), (15, 16),     # ring
    (13, 17), (17, 18), (18, 19), (19, 20),    # pinky
    (0, 17),                                    # palm edge
]
POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),   # shoulders and arms
    (11, 23), (12, 24), (23, 24),                        # torso
    (23, 25), (25, 27), (24, 26), (26, 28),              # legs
]

PITCH_GREEN_BGR = (138, 224, 20)
WHITE_BGR = (240, 240, 240)
HAND_COLORS_BGR = {"Right": PITCH_GREEN_BGR, "Left": (102, 209, 255)}


class ModelMissingError(RuntimeError):
    """Raised when a MediaPipe model file has not been downloaded yet."""


@dataclass
class HandDetection:
    label: str                 # "Right" or "Left" (as the user sees their own hand)
    score: float
    landmarks: np.ndarray      # (21, 3) normalised image coordinates


@dataclass
class Detection:
    hands: list = field(default_factory=list)          # list[HandDetection]
    pose: Optional[np.ndarray] = None                   # (33, 3) or None


class MediaPipeDetector:
    """Wraps MediaPipe's Tasks API hand (and optional pose) landmarkers.

    Created lazily on the video thread. Models are loaded from `models/mediapipe/`;
    run `python download_models.py` once to fetch them.
    """

    def __init__(self, use_pose: bool = False) -> None:
        import mediapipe as mp                                  # heavy import, keep local
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision

        if not HAND_MODEL_PATH.exists():
            raise ModelMissingError(
                f"Hand model not found at {HAND_MODEL_PATH}. "
                "Run: python download_models.py"
            )
        self._mp = mp
        self._last_ts_ms = 0
        self._hands = mp_vision.HandLandmarker.create_from_options(
            mp_vision.HandLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=str(HAND_MODEL_PATH)),
                running_mode=mp_vision.RunningMode.VIDEO,
                num_hands=config.MAX_HANDS,
                min_hand_detection_confidence=config.DETECTION_CONFIDENCE,
                min_hand_presence_confidence=config.DETECTION_CONFIDENCE,
                min_tracking_confidence=config.TRACKING_CONFIDENCE,
            )
        )
        self._pose = None
        if use_pose:
            if not POSE_MODEL_PATH.exists():
                raise ModelMissingError(
                    f"Pose model not found at {POSE_MODEL_PATH}. "
                    "Run: python download_models.py --pose"
                )
            self._pose = mp_vision.PoseLandmarker.create_from_options(
                mp_vision.PoseLandmarkerOptions(
                    base_options=mp_python.BaseOptions(model_asset_path=str(POSE_MODEL_PATH)),
                    running_mode=mp_vision.RunningMode.VIDEO,
                    min_pose_detection_confidence=config.DETECTION_CONFIDENCE,
                    min_pose_presence_confidence=config.DETECTION_CONFIDENCE,
                    min_tracking_confidence=config.TRACKING_CONFIDENCE,
                )
            )

    def detect(self, frame_bgr: np.ndarray) -> Detection:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        # VIDEO mode needs strictly increasing timestamps.
        ts = max(int(time.monotonic() * 1000), self._last_ts_ms + 1)
        self._last_ts_ms = ts

        detection = Detection()
        res = self._hands.detect_for_video(image, ts)
        for lms, handed in zip(res.hand_landmarks, res.handedness):
            arr = np.array([[p.x, p.y, p.z] for p in lms], dtype=np.float32)
            detection.hands.append(
                HandDetection(handed[0].category_name, float(handed[0].score), arr)
            )
        if self._pose is not None:
            pres = self._pose.detect_for_video(image, ts)
            if pres.pose_landmarks:
                detection.pose = np.array(
                    [[p.x, p.y, p.z] for p in pres.pose_landmarks[0]], dtype=np.float32
                )
        return detection

    def close(self) -> None:
        for model in (self._hands, self._pose):
            if model is not None:
                model.close()


def draw_landmarks(frame: np.ndarray, detection: Detection) -> None:
    """Draw hand skeletons (and pose, if present) onto `frame` in place."""
    h, w = frame.shape[:2]

    def pts(arr: np.ndarray) -> np.ndarray:
        return np.stack([arr[:, 0] * w, arr[:, 1] * h], axis=1).astype(int)

    if detection.pose is not None:
        p = pts(detection.pose)
        for a, b in POSE_CONNECTIONS:
            cv2.line(frame, tuple(p[a]), tuple(p[b]), (90, 90, 90), 2, cv2.LINE_AA)
    for hand in detection.hands:
        color = HAND_COLORS_BGR.get(hand.label, PITCH_GREEN_BGR)
        p = pts(hand.landmarks)
        for a, b in HAND_CONNECTIONS:
            cv2.line(frame, tuple(p[a]), tuple(p[b]), color, 2, cv2.LINE_AA)
        for x, y in p:
            cv2.circle(frame, (int(x), int(y)), 4, WHITE_BGR, -1, cv2.LINE_AA)
            cv2.circle(frame, (int(x), int(y)), 4, color, 1, cv2.LINE_AA)


class LandmarkHook:
    """Frame hook: detect landmarks, draw them, and emit a feature vector.

    Plug into `FrameProcessor(frame_hook=LandmarkHook())`. `show_landmarks` can
    be toggled from the dashboard at any time. Pass `detector_factory` to inject
    a stand-in detector (used by the tests, which have no webcam or model).
    """

    def __init__(self, detector_factory: Optional[Callable[[], object]] = None,
                 mode: str = config.FEATURE_MODE) -> None:
        self.mode = mode
        self.show_landmarks = config.SHOW_LANDMARKS_DEFAULT
        self._factory = detector_factory or (lambda: MediaPipeDetector(use_pose=(mode == "hands+pose")))
        self._detector = None
        self._init_error: Optional[Exception] = None

    def __call__(self, frame: np.ndarray) -> "tuple[np.ndarray, dict]":
        if self._detector is None:
            if self._init_error is not None:
                raise self._init_error          # cheap re-raise; processor shows the message
            try:
                self._detector = self._factory()
            except Exception as exc:
                self._init_error = exc
                raise

        detection: Detection = self._detector.detect(frame)
        if self.show_landmarks:
            draw_landmarks(frame, detection)

        right = left = None
        best = {"Right": -1.0, "Left": -1.0}
        for hand in detection.hands:            # keep the most confident hand per side
            if hand.label in best and hand.score > best[hand.label]:
                best[hand.label] = hand.score
                if hand.label == "Right":
                    right = hand.landmarks
                else:
                    left = hand.landmarks

        try:
            vector = features.build_feature_vector(right, left, detection.pose, self.mode)
        except ValueError:                      # degenerate landmarks: treat as no detection
            vector = None

        info = {
            "hand_detected": bool(detection.hands),
            "num_hands": len(detection.hands),
            "pose_detected": detection.pose is not None,
            "features": vector,
        }
        return frame, info

    def close(self) -> None:
        if self._detector is not None and hasattr(self._detector, "close"):
            self._detector.close()
