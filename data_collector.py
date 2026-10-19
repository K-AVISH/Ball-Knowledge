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

import io
import json
import os
import re
import threading
import time
import uuid
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, List, NamedTuple, Optional

import numpy as np
import pandas as pd

import config
import features
import storage

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
        raise ValueError("Enter a gesture name using the letters a to z or numbers.")
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

    def cancel_unfinished(self) -> bool:
        """Drop a recording still in its countdown or recording. Returns True if one was
        dropped. A finished recording waiting to be saved is kept."""
        with self._lock:
            if self._state not in (COUNTDOWN, RECORDING):
                return False
            self._reset()
            return True

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
            # The tolerance stops float rounding from skipping a frame that is exactly one
            # interval later (e.g. every third frame of a 30 fps video at 10 Hz).
            if now - self._last_sample_at < self._min_interval - 1e-9:
                return
            self._last_sample_at = now
            self._result.samples.append(np.asarray(feature_vector, dtype=np.float32).copy())
            if len(self._result.samples) >= self._target:
                self._state = FINISHED


# ---------------------------------------------------------------------------
# Dataset on disk
# ---------------------------------------------------------------------------

class _Snapshot(NamedTuple):
    key: tuple                 # (inode, modification time, size) of the file that was read
    frame: pd.DataFrame
    fingerprint: str


# Parsed copies of recently read sample files. Every page asks for the dataset on every
# rerun; while the file is unchanged it is parsed once, not once per question. The file
# is only ever replaced whole (storage.atomic_write_bytes), so a new version always has a
# new inode or modification time and is read again.
_SNAPSHOTS: "OrderedDict[str, _Snapshot]" = OrderedDict()
_SNAPSHOTS_LOCK = threading.Lock()
_SNAPSHOTS_KEPT = 8


def _file_key(st: os.stat_result) -> tuple:
    return st.st_ino, st.st_mtime_ns, st.st_size


class DatasetStore:
    """Reads and writes `data/samples.csv`. Safe to construct on an empty project.

    Writes replace the whole file in one step under a lock (see storage.py), so a crash
    never leaves half a row, and two tabs or a tab and a terminal script never overwrite
    each other's recordings. Reads take no lock.
    """

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
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DatasetError(f"Cannot read {self.meta_path}: {exc}") from exc
        if not isinstance(meta, dict):
            raise DatasetError(f"Cannot read {self.meta_path}: it does not describe a dataset.")
        if meta.get("feature_mode") != self.feature_mode:
            raise DatasetError(
                f"The dataset was collected with feature mode '{meta.get('feature_mode')}' but "
                f"config.FEATURE_MODE is '{self.feature_mode}'. Change the setting back, or move "
                f"{self.csv_path.name} and {self.meta_path.name} aside to start a new dataset."
            )

    def _write_meta(self) -> None:
        text = json.dumps({"feature_mode": self.feature_mode, "feature_length": self.feature_length},
                          indent=2)
        try:
            if self.meta_path.read_text() == text:
                return
        except OSError:
            pass
        storage.atomic_write_text(self.meta_path, text)

    def _locked(self):
        return storage.locked(self.csv_path, what=self.csv_path.name)

    def _atomic_write(self, df: pd.DataFrame) -> None:
        storage.atomic_write_text(self.csv_path, df.to_csv(index=False, float_format="%.6g"))

    def _parse(self, data: bytes) -> pd.DataFrame:
        # keep_default_na=False: text stays as written. Otherwise a gesture named "null" or
        # "nan", or a person named "NA", would read back as a missing value. Nothing is
        # ever saved as NaN (append refuses it), so an empty cell is just empty text.
        try:
            df = pd.read_csv(io.BytesIO(data), dtype={"session_id": str, "label": str, "person": str},
                             keep_default_na=False)
        except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
            raise DatasetError(f"{self.csv_path} is corrupted: {exc}") from exc
        missing = [c for c in self.columns if c not in df.columns]
        if missing:
            raise DatasetError(f"{self.csv_path} is missing columns, e.g. {missing[:3]}.")
        df["person"] = df["person"].fillna("")
        return df[self.columns]

    def _snapshot(self) -> Optional[_Snapshot]:
        """The parsed file and its fingerprint, or None if nothing is collected yet."""
        try:
            key = _file_key(os.stat(self.csv_path))
        except FileNotFoundError:
            return None
        self._check_meta()
        cache_key = f"{self.csv_path.resolve()}|{self.feature_mode}"
        with _SNAPSHOTS_LOCK:
            cached = _SNAPSHOTS.get(cache_key)
            if cached is not None and cached.key == key:
                _SNAPSHOTS.move_to_end(cache_key)
                return cached
        try:
            with open(self.csv_path, "rb") as fh:      # key and bytes from the same file
                key = _file_key(os.fstat(fh.fileno()))
                data = fh.read()
        except FileNotFoundError:
            return None
        snap = _Snapshot(key, self._parse(data), storage.sha256_bytes(data))
        with _SNAPSHOTS_LOCK:
            _SNAPSHOTS[cache_key] = snap
            _SNAPSHOTS.move_to_end(cache_key)
            while len(_SNAPSHOTS) > _SNAPSHOTS_KEPT:
                _SNAPSHOTS.popitem(last=False)
        return snap

    # --- reading -----------------------------------------------------------------
    def load(self) -> pd.DataFrame:
        """All samples (empty frame if nothing collected yet). The caller gets its own copy."""
        return self.load_with_fingerprint()[0]

    def load_with_fingerprint(self) -> "tuple[pd.DataFrame, str]":
        """(all samples, fingerprint of the file they were read from), from one read.
        The fingerprint is empty when nothing is collected yet."""
        snap = self._snapshot()
        if snap is None:
            return pd.DataFrame(columns=self.columns), ""
        return snap.frame.copy(), snap.fingerprint

    def fingerprint(self) -> str:
        """SHA-256 of samples.csv, or "" when it does not exist. Any change to the samples
        (a recording added, deleted or replaced) changes it."""
        snap = self._snapshot()
        return snap.fingerprint if snap is not None else ""

    def row_count(self) -> int:
        """Number of saved samples. Raises DatasetError like `load()`."""
        snap = self._snapshot()
        return len(snap.frame) if snap is not None else 0

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

    def session_times(self) -> "dict[str, str]":
        """When each recording started: session id -> its earliest timestamp (ISO text)."""
        df = self.load()
        if df.empty:
            return {}
        first = df.groupby("session_id")["timestamp"].min()
        return {str(k): str(v) for k, v in first.items()}

    # --- writing -----------------------------------------------------------------
    def append(self, result: RecordingResult) -> int:
        """Save a finished recording. Returns the number of rows written.

        The file is replaced whole, with the new rows after the existing ones, so a
        crash or a full disk leaves the previous file intact rather than half a row.
        """
        if not result.samples:
            return 0
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
        with self._guard():
            self._check_meta()
            try:
                existing = self.csv_path.read_bytes()
            except FileNotFoundError:
                existing = None
            if existing is not None:
                self._parse(existing)            # a corrupted file must not be silently extended
                if existing and not existing.endswith(b"\n"):
                    existing += b"\n"
            new = df.to_csv(header=existing is None, index=False, float_format="%.6g").encode()
            self._write_meta()
            storage.atomic_write_bytes(self.csv_path, (existing or b"") + new)
        return len(df)

    @contextmanager
    def _guard(self):
        """The write lock, with a busy lock reported like any other dataset problem."""
        try:
            with self._locked():
                yield
        except storage.StorageBusyError as exc:
            raise DatasetError(str(exc)) from exc

    def last_session(self) -> Optional[dict]:
        """The most recently saved recording: {'session_id','label','samples'} or None."""
        df = self.load()
        if df.empty:
            return None
        last = df.iloc[-1]["session_id"]               # rows are appended in order
        part = df[df["session_id"] == last]
        return {"session_id": last, "label": part.iloc[0]["label"], "samples": len(part)}

    def delete_session(self, session_id: str) -> int:
        return self._delete_where("session_id", session_id)

    def delete_label(self, label: str) -> int:
        return self._delete_where("label", label)

    def _delete_where(self, column: str, value: str) -> int:
        """Remove every row whose `column` equals `value`. Returns the number removed."""
        with self._guard():
            df = self.load()                     # read under the lock: nothing is lost in between
            keep = df[df[column] != value]
            removed = len(df) - len(keep)
            if removed:
                self._atomic_write(keep)
        return removed


def ready_to_train(summary: Optional[pd.DataFrame],
                   min_sessions: int = config.MIN_SESSIONS_FOR_TRAINING) -> bool:
    """True when the recorded data meets training's minimum: at least 2 gestures, each with
    `min_sessions` separate recordings (what train_model.check_recordings asks for). Rows are
    not validated here, so training can still refuse a damaged file, and then says why."""
    if summary is None or len(summary) < 2:
        return False
    return bool((summary["recordings"] >= min_sessions).all())


def class_status(samples: int, recordings: int) -> "tuple[str, str]":
    """('ok'|'warn'|'bad', hint) describing how ready a gesture's data is."""
    short_recordings = max(0, config.MIN_SESSIONS_PER_CLASS - recordings)
    more_recordings = (f"{short_recordings} more separate recording"
                       f"{'s' if short_recordings != 1 else ''}")
    if samples < config.TARGET_MIN_PER_CLASS:
        hint = f"Needs {config.TARGET_MIN_PER_CLASS - samples} more samples"
        if short_recordings:                 # both shortfalls matter, so name both
            hint += f" and {more_recordings}"
        return "bad", hint
    if short_recordings:
        return "warn", f"Record {more_recordings}"
    if samples < config.TARGET_GOOD_PER_CLASS:
        return "ok", "Ready, more variety will help"
    return "ok", "Great coverage"
