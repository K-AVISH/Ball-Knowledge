"""Live gesture recognition: load the trained classifier once and classify frames.

Two pieces, neither of which touches the UI:

* `Predictor`       loads models/gesture_model.joblib and models/label_mapping.json,
                    checks that they match each other and the current feature mode,
                    and turns one feature vector into a `Prediction`.
* `LiveRecognizer`  runs a Predictor on its own worker thread. The video thread hands
                    it the newest feature vector with `offer()`, which never waits for
                    the model. A slow model lowers the prediction rate, not the video
                    frame rate. Frames that arrive while the model is busy are skipped
                    and only the newest one is classified.

The feature vector is the one `vision.LandmarkHook` builds with
`features.build_feature_vector`, the same call the data collector used to make the
training samples, so training and prediction see the same input.

Confidence is the classifier's own probability estimate. It is not calibrated: a
score of 0.8 does not mean the prediction is right 80% of the time. The confidence
cutoff table on the Model performance page shows how often predictions above each
cutoff were right on the held-out test recordings.

Smoothing across frames (a voting window) is Stage 7. Each Prediction here describes
one frame.
"""
from __future__ import annotations

import json
import threading
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple

import numpy as np

import config
import features

NO_HAND, UNRECOGNISED, RECOGNISED, ERROR = "no_hand", "unrecognised", "recognised", "error"


class PredictorError(RuntimeError):
    """The saved model cannot be used. The message says what to do."""


class NotTrainedError(PredictorError):
    """No model has been trained yet."""


@dataclass(frozen=True)
class Prediction:
    """The classifier's answer for one frame."""

    status: str                                   # NO_HAND, UNRECOGNISED, RECOGNISED or ERROR
    label: Optional[str] = None                   # the accepted gesture; None unless RECOGNISED
    confidence: Optional[float] = None            # highest class probability; None without a hand
    top: Tuple[Tuple[str, float], ...] = ()       # (gesture, probability), highest first
    threshold: float = config.DEFAULT_CONFIDENCE_THRESHOLD
    inference_ms: Optional[float] = None          # time spent in the classifier
    at: float = 0.0                               # time.time() when the frame was classified
    error: Optional[str] = None


def is_fresh(prediction: Optional[Prediction], max_age_s: float = 2.0) -> bool:
    """True if the prediction describes a frame from the last `max_age_s` seconds."""
    return prediction is not None and (time.time() - prediction.at) < max_age_s


def _read_json(path: Path, what: str):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise PredictorError(f"Cannot read {path.name} ({what}): {exc}. Train the model again.") from exc


def _parse_label_mapping(raw, path: Path) -> list:
    """{"0": "fist", "1": "open_palm"} -> ["fist", "open_palm"]."""
    if not isinstance(raw, dict) or not raw:
        raise PredictorError(f"{path.name} is not a label mapping. Train the model again.")
    try:
        indexed = {int(k): v for k, v in raw.items()}
    except (TypeError, ValueError):
        raise PredictorError(f"{path.name} has keys that are not class numbers. Train the model again.")
    if sorted(indexed) != list(range(len(indexed))) or not all(
            isinstance(v, str) and v for v in indexed.values()):
        raise PredictorError(f"{path.name} is incomplete or has empty gesture names. Train the model again.")
    labels = [indexed[i] for i in range(len(indexed))]
    if len(set(labels)) != len(labels):
        raise PredictorError(f"{path.name} lists the same gesture twice. Train the model again.")
    return labels


class Predictor:
    """A loaded classifier plus its label mapping. Thread-safe for `predict`."""

    def __init__(self, model, labels: Sequence[str], feature_mode: str = config.FEATURE_MODE,
                 threshold: float = config.DEFAULT_CONFIDENCE_THRESHOLD,
                 top_k: int = config.TOP_PREDICTIONS, trained_at: Optional[str] = None,
                 warnings_: Sequence[str] = ()) -> None:
        if not 0 < threshold <= 1:
            raise ValueError(f"The confidence threshold must be above 0 and at most 1, got {threshold}.")
        if top_k < 1:
            raise ValueError("top_k must be at least 1.")
        for attr in ("predict_proba", "classes_"):
            if not hasattr(model, attr):
                raise PredictorError("The saved model is not a trained classifier. Train the model again.")
        self.model = model
        self.labels = list(labels)
        self.feature_mode = feature_mode
        self.feature_length = features.feature_length(feature_mode)
        self.threshold = float(threshold)
        self.top_k = int(top_k)
        self.trained_at = trained_at
        self.warnings = list(warnings_)

        n_in = getattr(model, "n_features_in_", None)
        if n_in is not None and n_in != self.feature_length:
            raise PredictorError(
                f"The model expects {n_in} features but '{feature_mode}' mode produces "
                f"{self.feature_length}. Train the model again with the current setting.")
        try:
            self._class_names = [self.labels[int(c)] for c in model.classes_]
        except (IndexError, TypeError, ValueError):
            raise PredictorError(
                "The model and label_mapping.json do not match. Train the model again "
                "so both are written together.")

        # A random forest with n_jobs=-1 starts a thread pool for every call. For one
        # frame that costs more than it saves (measured: about 26 ms per frame against
        # 10 ms single-threaded for the 300-tree forest).
        if "n_jobs" in model.get_params(deep=False):
            model.set_params(n_jobs=1)

    @classmethod
    def load(cls, model_path: Optional[Path] = None, labels_path: Optional[Path] = None,
             report_path: Optional[Path] = None, feature_mode: str = config.FEATURE_MODE,
             threshold: float = config.DEFAULT_CONFIDENCE_THRESHOLD,
             top_k: int = config.TOP_PREDICTIONS) -> "Predictor":
        """Load the saved model, label mapping and (if present) training report.

        Raises NotTrainedError when there is no model yet, and PredictorError when the
        files are unreadable, do not match each other, or were made for another
        feature mode.
        """
        import joblib

        model_path = Path(model_path or config.MODEL_PATH)
        labels_path = Path(labels_path or config.LABELS_PATH)
        report_path = Path(report_path or config.REPORT_PATH)

        if not model_path.exists():
            raise NotTrainedError(
                "No trained model yet. Record at least 2 gestures on the Data collector page, "
                "then train a model on the Model performance page.")
        if not labels_path.exists():
            raise PredictorError(
                f"{labels_path.name} is missing, so predictions cannot be named. "
                "Train the model again to recreate it.")
        labels = _parse_label_mapping(_read_json(labels_path, "label mapping"), labels_path)

        notes = []
        trained_at = None
        if report_path.exists():
            report = _read_json(report_path, "training report")
            trained_at = report.get("trained_at")
            trained_mode = report.get("feature_mode")
            if trained_mode and trained_mode != feature_mode:
                raise PredictorError(
                    f"The model was trained on '{trained_mode}' features but the app is set to "
                    f"'{feature_mode}'. Train the model again, or set FEATURE_MODE in config.py "
                    f"back to '{trained_mode}'.")
            if report.get("labels") not in (None, labels):
                raise PredictorError(
                    "label_mapping.json and training_report.json list different gestures. "
                    "Train the model again.")
            import sklearn
            saved = report.get("sklearn_version")
            if saved and saved != sklearn.__version__:
                notes.append(
                    f"The model was saved with scikit-learn {saved} and is running on "
                    f"{sklearn.__version__}. Train again if predictions look wrong.")

        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                model = joblib.load(model_path)
        except Exception as exc:              # corrupted file, missing class, wrong format
            raise PredictorError(
                f"Cannot load {model_path.name}: {type(exc).__name__}: {exc}. "
                "Train the model again.") from exc
        version_warnings = [w for w in caught if w.category.__name__ == "InconsistentVersionWarning"]
        if version_warnings and not notes:   # no report to name the versions, so pass on sklearn's text
            notes.append(f"{version_warnings[0].message} Train again if predictions look wrong.")

        return cls(model, labels, feature_mode, threshold, top_k, trained_at, notes)

    def predict(self, vector: Optional[np.ndarray]) -> Prediction:
        """Classify one feature vector. `None` (no hand in the frame) gives NO_HAND."""
        now = time.time()
        if vector is None:
            return Prediction(NO_HAND, threshold=self.threshold, at=now)
        x = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        if x.shape[1] != self.feature_length:
            raise PredictorError(
                f"Got a feature vector of length {x.shape[1]}, expected {self.feature_length}.")
        if not np.isfinite(x).all():
            raise PredictorError("The feature vector contains NaN or infinity.")

        start = time.perf_counter()
        proba = np.asarray(self.model.predict_proba(x)[0], dtype=float)
        elapsed_ms = (time.perf_counter() - start) * 1000

        order = np.argsort(-proba, kind="stable")[: self.top_k]     # ties keep class order
        top = tuple((self._class_names[i], float(proba[i])) for i in order)
        best_label, best_p = top[0]
        if best_p >= self.threshold:
            return Prediction(RECOGNISED, best_label, best_p, top, self.threshold, elapsed_ms, now)
        return Prediction(UNRECOGNISED, None, best_p, top, self.threshold, elapsed_ms, now)


_NOTHING = object()          # marks an empty mailbox (None means "frame without a hand")


class LiveRecognizer:
    """Classifies the newest frame on a worker thread.

    The video thread calls `offer()` for every frame; the UI thread reads `latest()`.
    The worker thread stops by itself after `idle_exit_s` seconds without frames (for
    example after the camera is stopped) and starts again on the next `offer()`.
    """

    def __init__(self, predictor: Optional[Predictor] = None, idle_exit_s: float = 5.0) -> None:
        self._cond = threading.Condition()
        self._predictor = predictor
        self._pending = _NOTHING
        self._latest: Optional[Prediction] = None
        self._thread: Optional[threading.Thread] = None
        self._generation = 0           # bumped on reset or model change; stale results are dropped
        self._idle_exit_s = idle_exit_s
        self.frames_skipped = 0        # frames replaced before the worker reached them

    # --- UI thread ---------------------------------------------------------------
    @property
    def predictor(self) -> Optional[Predictor]:
        with self._cond:
            return self._predictor

    def use(self, predictor: Optional[Predictor]) -> None:
        """Switch model (for example after retraining). Clears the previous result."""
        with self._cond:
            if predictor is self._predictor:
                return
            self._predictor = predictor
            self._clear()

    def reset(self) -> None:
        """Forget the last result, for example when the camera stops."""
        with self._cond:
            self._clear()

    def latest(self) -> Optional[Prediction]:
        with self._cond:
            return self._latest

    def is_running(self) -> bool:
        with self._cond:
            return self._thread is not None

    def _clear(self) -> None:
        self._pending = _NOTHING
        self._latest = None
        self._generation += 1

    # --- video thread ------------------------------------------------------------
    def offer(self, vector: Optional[np.ndarray]) -> None:
        """Hand over the newest feature vector. Returns at once; never runs the model."""
        with self._cond:
            if self._predictor is None:
                return
            if self._pending is not _NOTHING:
                self.frames_skipped += 1
            self._pending = None if vector is None else np.array(vector, dtype=np.float32)
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, name="gesture-recognizer",
                                                daemon=True)
                self._thread.start()
            self._cond.notify()

    # --- worker thread -----------------------------------------------------------
    def _run(self) -> None:
        while True:
            with self._cond:
                idle_since = time.monotonic()
                while self._pending is _NOTHING:
                    remaining = self._idle_exit_s - (time.monotonic() - idle_since)
                    if remaining <= 0:
                        self._thread = None          # offer() starts a new worker when frames return
                        return
                    self._cond.wait(remaining)
                vector, self._pending = self._pending, _NOTHING
                predictor, generation = self._predictor, self._generation
            if predictor is None:
                continue
            try:
                result = predictor.predict(vector)
            except Exception as exc:                 # keep the worker alive, surface the message
                result = Prediction(ERROR, threshold=predictor.threshold, at=time.time(),
                                    error=f"{type(exc).__name__}: {exc}")
            with self._cond:
                if generation == self._generation:   # ignore results for a model that was swapped out
                    self._latest = result
