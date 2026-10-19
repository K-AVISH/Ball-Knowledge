"""Capture and store labelled gesture samples.

Three pieces, none of which touch the UI:

* `slugify_label`  turns what you type into a safe gesture id (e.g. "four_gesture").
* `Recorder`       is a small state machine the video thread feeds with feature
                     vectors. Countdown → recording → finished. Thread-safe.
* `DatasetStore`   is the CSV file on disk (`data/samples.csv`). Every row has the
                     label, a recording-session id (so training can split by
                     session, not by neighbouring frames), who recorded it and
                     the feature vector.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

import numpy as np
import pandas as pd

import config
import features

META_COLUMNS = ["session_id", "label", "person", "timestamp"]
IDLE, COUNTDOWN, RECORDING, FINISHED = "idle", "countdown", "recording", "finished"


class DatasetError(RuntimeError):
    """The dataset on disk is unreadable or incompatible with the current settings."""


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------

def slugify_label(text: str, max_len: int = 40) -> str:
    """'Four Gesture!' -> 'four_gesture'. Raises ValueError if nothing usable is left."""
    slug = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")
    if not slug:
        raise ValueError("Enter a gesture name using letters or numbers.")
    if not slug[0].isalpha():
        slug = "g_" + slug                      # ids start with a letter
    return slug[:max_len].rstrip("_")


# ---------------------------------------------------------------------------
# Recorder
# ---------------------------------------------------------------------------

@dataclass
class RecordingResult:
    session_id: str
    label: str
    person: str
    timestamp: str
    samples: List[np.ndarray] = field(default_factory=list)
    skipped_no_hand: int = 0


@dataclass
class RecorderStatus:
    state: str = IDLE
    label: str = ""
    collected: int = 0
    target: int = 0
    countdown_left: float = 0.0
    skipped_no_hand: int = 0


class Recorder:
    """Feed it one feature vector per video frame with `offer()`.

    Frames without a hand (`features is None`) are counted but never stored, so
    the dataset only contains frames where a hand was actually found. Samples are
    spaced `1 / COLLECT_RATE_HZ` apart.
    """

    def __init__(self, rate_hz: float = config.COLLECT_RATE_HZ,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._lock = threading.Lock()
        self._clock = clock
        self._min_interval = 1.0 / rate_hz
        self._reset()

    def _reset(self) -> None:
        self._state = IDLE
        self._result: Optional[RecordingResult] = None
        self._target = 0
        self._record_from = 0.0
        self._last_sample_at = -1e9

    # --- control (called from the UI thread) ---------------------------------
    def start(self, label: str, target: int, person: str = "",
              countdown_s: float = config.COLLECT_COUNTDOWN_S) -> None:
        if target < 1:
            raise ValueError("Target must be at least 1 sample.")
        label = slugify_label(label)
        with self._lock:
            if self._state in (COUNTDOWN, RECORDING):
                raise RuntimeError("A recording is already in progress.")
            self._reset()
            self._result = RecordingResult(
                session_id=uuid.uuid4().hex[:12], label=label, person=person.strip(),
                timestamp=datetime.now().isoformat(timespec="seconds"),
            )
            self._target = target
            self._record_from = self._clock() + countdown_s
            self._state = COUNTDOWN if countdown_s > 0 else RECORDING

    def stop(self) -> None:
        """Finish early; keeps whatever was collected."""
        with self._lock:
            if self._state in (COUNTDOWN, RECORDING):
                self._state = FINISHED

    def cancel(self) -> None:
        with self._lock:
            self._reset()

    def pop_finished(self) -> Optional[RecordingResult]:
        """Return the finished recording exactly once, then go back to idle."""
        with self._lock:
            if self._state != FINISHED:
                return None
            result, self._result = self._result, None
            self._reset()
            return result

    def status(self) -> RecorderStatus:
        with self._lock:
            if self._result is None:
                return RecorderStatus()
            return RecorderStatus(
                state=self._state, label=self._result.label,
                collected=len(self._result.samples), target=self._target,
                countdown_left=max(0.0, self._record_from - self._clock())
                if self._state == COUNTDOWN else 0.0,
                skipped_no_hand=self._result.skipped_no_hand,
            )

    # --- video thread --------------------------------------------------------
    def offer(self, feature_vector: Optional[np.ndarray]) -> None:
        with self._lock:
            if self._state not in (COUNTDOWN, RECORDING):
                return
            now = self._clock()
            if self._state == COUNTDOWN:
                if now < self._record_from:
                    return
                self._state = RECORDING
            if feature_vector is None:
                self._result.skipped_no_hand += 1
                return
            if now - self._last_sample_at < self._min_interval:
                return
            self._last_sample_at = now
            self._result.samples.append(np.asarray(feature_vector, dtype=np.float32).copy())
            if len(self._result.samples) >= self._target:
                self._state = FINISHED


# ---------------------------------------------------------------------------
# Dataset on disk
# ---------------------------------------------------------------------------

class DatasetStore:
    """Reads and writes `data/samples.csv`. Safe to construct on an empty project."""

    def __init__(self, csv_path: Path = config.SAMPLES_CSV,
                 meta_path: Path = config.DATASET_META,
                 feature_mode: str = config.FEATURE_MODE) -> None:
        self.csv_path = Path(csv_path)
        self.meta_path = Path(meta_path)
        self.feature_mode = feature_mode
        self.feature_length = features.feature_length(feature_mode)
        self.columns = META_COLUMNS + [f"f{i:03d}" for i in range(self.feature_length)]

    # --- helpers ---------------------------------------------------------------
    def _check_meta(self) -> None:
        if not self.meta_path.exists():
            return
        try:
            meta = json.loads(self.meta_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise DatasetError(f"Cannot read {self.meta_path}: {exc}") from exc
        if meta.get("feature_mode") != self.feature_mode:
            raise DatasetError(
                f"The dataset was collected with feature mode '{meta.get('feature_mode')}' but "
                f"config.FEATURE_MODE is '{self.feature_mode}'. Change the setting back, or move "
                f"{self.csv_path.name} and {self.meta_path.name} aside to start a new dataset."
            )

    def _write_meta(self) -> None:
        self.meta_path.parent.mkdir(parents=True, exist_ok=True)
        self.meta_path.write_text(json.dumps(
            {"feature_mode": self.feature_mode, "feature_length": self.feature_length}, indent=2))

    def _atomic_write(self, df: pd.DataFrame) -> None:
        tmp = self.csv_path.with_suffix(".csv.tmp")
        df.to_csv(tmp, index=False, float_format="%.6g")
        os.replace(tmp, self.csv_path)

    # --- reading -----------------------------------------------------------------
    def load(self) -> pd.DataFrame:
        """All samples (empty frame if nothing collected yet)."""
        if not self.csv_path.exists():
            return pd.DataFrame(columns=self.columns)
        self._check_meta()
        try:
            df = pd.read_csv(self.csv_path, dtype={"session_id": str, "label": str, "person": str})
        except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
            raise DatasetError(f"{self.csv_path} is corrupted: {exc}") from exc
        missing = [c for c in self.columns if c not in df.columns]
        if missing:
            raise DatasetError(f"{self.csv_path} is missing columns, e.g. {missing[:3]}.")
        df["person"] = df["person"].fillna("")
        return df[self.columns]

    def row_count(self) -> int:
        """Number of saved samples. Raises DatasetError like `load()`."""
        return len(self.load())

    def labels(self) -> List[str]:
        df = self.load()
        return sorted(df["label"].unique().tolist())

    def summary(self) -> pd.DataFrame:
        """One row per gesture: samples, recordings, people."""
        df = self.load()
        if df.empty:
            return pd.DataFrame(columns=["label", "samples", "recordings", "people"])
        grouped = df.groupby("label")
        out = pd.DataFrame({
            "samples": grouped.size(),
            "recordings": grouped["session_id"].nunique(),
            "people": grouped["person"].apply(lambda s: len({p for p in s if p})),
        }).reset_index()
        return out.sort_values("label").reset_index(drop=True)

    # --- writing -----------------------------------------------------------------
    def append(self, result: RecordingResult) -> int:
        """Save a finished recording. Returns the number of rows written."""
        if not result.samples:
            return 0
        self._check_meta()
        rows = np.stack(result.samples)
        if rows.ndim != 2 or rows.shape[1] != self.feature_length:
            raise DatasetError(
                f"Feature vectors have length {rows.shape[-1]}, expected {self.feature_length} "
                f"for mode '{self.feature_mode}'."
            )
        if not np.isfinite(rows).all():
            raise DatasetError("Refusing to save samples containing NaN or infinity.")
        df = pd.DataFrame(rows, columns=self.columns[len(META_COLUMNS):])
        for i, col in enumerate(["session_id", "label", "person", "timestamp"]):
            df.insert(i, col, [result.session_id, result.label, result.person, result.timestamp][i])
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        exists = self.csv_path.exists()
        if exists:                               # a corrupted file must not be silently extended
            self.load()
        df.to_csv(self.csv_path, mode="a", header=not exists, index=False, float_format="%.6g")
        self._write_meta()
        return len(df)

    def last_session(self) -> Optional[dict]:
        """The most recently saved recording: {'session_id','label','samples'} or None."""
        df = self.load()
        if df.empty:
            return None
        last = df.iloc[-1]["session_id"]               # rows are appended in order
        part = df[df["session_id"] == last]
        return {"session_id": last, "label": part.iloc[0]["label"], "samples": len(part)}

    def delete_session(self, session_id: str) -> int:
        df = self.load()
        keep = df[df["session_id"] != session_id]
        removed = len(df) - len(keep)
        if removed:
            self._atomic_write(keep)
        return removed

    def delete_label(self, label: str) -> int:
        df = self.load()
        keep = df[df["label"] != label]
        removed = len(df) - len(keep)
        if removed:
            self._atomic_write(keep)
        return removed


def class_status(samples: int, recordings: int) -> "tuple[str, str]":
    """('ok'|'warn'|'bad', hint) describing how ready a gesture's data is."""
    if samples < config.TARGET_MIN_PER_CLASS:
        return "bad", f"Needs {config.TARGET_MIN_PER_CLASS - samples} more samples"
    if recordings < config.MIN_SESSIONS_PER_CLASS:
        return "warn", f"Record {config.MIN_SESSIONS_PER_CLASS - recordings} more separate recording(s)"
    if samples < config.TARGET_GOOD_PER_CLASS:
        return "ok", "Ready, more variety will help"
    return "ok", "Great coverage"
