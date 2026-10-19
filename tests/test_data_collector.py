"""Stage 3 tests: label cleaning, recorder state machine, CSV dataset store.
No webcam or MediaPipe needed."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
import data_collector as dc  # noqa: E402
import features  # noqa: E402
from vision import Detection, FrameProcessor, HandDetection, LandmarkHook  # noqa: E402

N = features.feature_length("hands")


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def vec(seed=0):
    return np.random.default_rng(seed).normal(size=N).astype(np.float32)


@pytest.fixture
def store(tmp_path):
    return dc.DatasetStore(tmp_path / "samples.csv", tmp_path / "meta.json", "hands")


def finished(label="four_gesture", n=5, person="kavish", session=None):
    r = dc.RecordingResult(session or "s" + label[:3] + str(n), label, person, "2026-01-01T00:00:00")
    r.samples = [vec(i) for i in range(n)]
    return r


# --- labels -----------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("four_gesture", "four_gesture"), ("  Four Gesture! ", "four_gesture"),
    ("Thumbs-Up", "thumbs_up"), ("7 up", "g_7_up"), ("ÉCOLE", "cole"),
])
def test_slugify(raw, expected):
    assert dc.slugify_label(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "!!!"])
def test_slugify_rejects_empty(raw):
    with pytest.raises(ValueError):
        dc.slugify_label(raw)


@pytest.mark.parametrize("raw", ["жест", "手势", "!!!"])
def test_names_in_other_scripts_are_refused_with_a_true_message(raw):
    """Owner decision Q5 (code review R2-3): ids keep only a to z and 0 to 9, so "жест" was
    refused with "using letters or numbers", although it is letters."""
    with pytest.raises(ValueError) as err:
        dc.slugify_label(raw)
    assert str(err.value) == "Enter a gesture name using the letters a to z or numbers."


def _summary(recordings):
    import pandas as pd
    return pd.DataFrame({"label": [f"g{i}" for i in range(len(recordings))],
                         "samples": [50] * len(recordings), "recordings": recordings})


@pytest.mark.parametrize("recordings, ready", [
    ([], False), ([5], False),                       # training needs 2 gestures
    ([2, 1], False),                                 # and 2 recordings of each
    ([2, 2], True), ([3, 2, 4], True),
])
def test_ready_to_train_matches_what_training_asks_for(recordings, ready):
    """Proposal PR-7: the collector points to training once the data meets its minimum
    (config.MIN_SESSIONS_FOR_TRAINING recordings of each of at least 2 gestures)."""
    assert dc.ready_to_train(_summary(recordings)) is ready
    assert dc.ready_to_train(None) is False


def test_slugify_truncates():
    assert len(dc.slugify_label("a" * 100)) <= 40


# --- recorder ---------------------------------------------------------------

def make_recorder(rate=10):
    clock = Clock()
    return dc.Recorder(rate_hz=rate, clock=clock), clock


def test_countdown_then_records_until_target():
    rec, clock = make_recorder()
    rec.start("Four Gesture", target=3, person="me", countdown_s=3)
    assert rec.status().state == dc.COUNTDOWN
    rec.offer(vec())                                  # ignored during countdown
    assert rec.status().collected == 0
    clock.advance(3.1)
    for i in range(10):
        rec.offer(vec(i))
        clock.advance(0.11)
    assert rec.status().state == dc.FINISHED
    result = rec.pop_finished()
    assert result.label == "four_gesture" and len(result.samples) == 3
    assert rec.pop_finished() is None                 # only once
    assert rec.status().state == dc.IDLE


def test_rate_limit_skips_near_duplicate_frames():
    rec, clock = make_recorder(rate=10)
    rec.start("a", target=100, countdown_s=0)
    for _ in range(30):                               # 30 frames in 0.3 s (100 fps)
        rec.offer(vec())
        clock.advance(0.01)
    assert rec.status().collected <= 4


def test_frame_exactly_one_interval_later_is_kept():
    # 30 fps at 10 Hz: every third frame. 3/30 is not exactly 0.1 in floating point.
    rec, clock = make_recorder(rate=10)
    rec.start("a", target=100, countdown_s=0)
    for i in range(90):
        clock.t = 100.0 + i / 30
        rec.offer(vec())
    assert rec.status().collected == 30


def test_no_hand_frames_are_counted_not_stored():
    rec, clock = make_recorder()
    rec.start("a", target=5, countdown_s=0)
    for _ in range(3):
        rec.offer(None)
        clock.advance(0.2)
    s = rec.status()
    assert s.collected == 0 and s.skipped_no_hand == 3


def test_stop_early_keeps_samples_and_cancel_discards():
    rec, clock = make_recorder()
    rec.start("a", target=50, countdown_s=0)
    for i in range(3):
        rec.offer(vec(i))
        clock.advance(0.2)
    rec.stop()
    assert len(rec.pop_finished().samples) == 3
    rec.start("a", target=50, countdown_s=0)
    rec.offer(vec())
    rec.cancel()
    assert rec.status().state == dc.IDLE and rec.pop_finished() is None


def test_leaving_the_collector_drops_only_a_recording_still_going():
    """Owner decision Q2 (A): another page cancels a recording in its countdown or while it
    records. A finished one waiting to be saved is kept, so it is saved on the collector."""
    rec, clock = make_recorder()
    assert rec.cancel_unfinished() is False                       # nothing to drop
    rec.start("a", target=50, countdown_s=3)
    assert rec.cancel_unfinished() is True and rec.status().state == dc.IDLE
    rec.start("a", target=50, countdown_s=0)
    rec.offer(vec())
    assert rec.cancel_unfinished() is True and rec.pop_finished() is None
    rec.start("a", target=1, countdown_s=0)
    rec.offer(vec())                                              # reaches its target
    assert rec.cancel_unfinished() is False
    assert len(rec.pop_finished().samples) == 1


def test_cannot_start_twice_or_with_bad_args():
    rec, _ = make_recorder()
    rec.start("a", target=5, countdown_s=0)
    with pytest.raises(RuntimeError):
        rec.start("b", target=5, countdown_s=0)
    rec.cancel()
    with pytest.raises(ValueError):
        rec.start("a", target=0)
    with pytest.raises(ValueError):
        rec.start("!!!", target=5)


def test_offered_vector_is_copied():
    rec, clock = make_recorder()
    rec.start("a", target=1, countdown_s=0)
    v = vec()
    rec.offer(v)
    v[:] = 0
    assert rec.pop_finished().samples[0].any()


def test_processor_feeds_recorder_only_when_hook_succeeds():
    rec, clock = make_recorder()
    rec.start("a", target=2, countdown_s=0)
    hand = np.random.default_rng(0).uniform(0.2, 0.8, (21, 3)).astype(np.float32)

    class Det:
        def detect(self, frame):
            return Detection(hands=[HandDetection("Right", 0.9, hand)])

    proc = FrameProcessor(frame_hook=LandmarkHook(detector_factory=Det))
    proc.recorder = rec
    frame = np.zeros((480, 640, 3), np.uint8)
    proc.process(frame)
    assert rec.status().collected == 1

    def broken():
        raise RuntimeError("no model")

    bad = FrameProcessor(frame_hook=LandmarkHook(detector_factory=broken))
    bad.recorder = rec
    bad.process(frame)
    assert rec.status().skipped_no_hand == 0          # errors are not "no hand"


# --- dataset store ----------------------------------------------------------

def test_empty_store_is_fine(store):
    assert store.load().empty
    assert store.labels() == [] and store.summary().empty
    assert store.last_session() is None


def test_append_load_roundtrip_and_summary(store):
    assert store.append(finished("four_gesture", 5, "a", "s1")) == 5
    store.append(finished("four_gesture", 4, "b", "s2"))
    store.append(finished("fist", 3, "a", "s3"))
    df = store.load()
    assert len(df) == 12 and list(df.columns) == store.columns
    assert np.allclose(df.iloc[0][store.columns[4:]].astype(float).values, vec(0), atol=1e-4)
    summ = store.summary().set_index("label")
    assert summ.loc["four_gesture", "samples"] == 9
    assert summ.loc["four_gesture", "recordings"] == 2
    assert summ.loc["four_gesture", "people"] == 2
    assert summ.loc["fist", "recordings"] == 1
    assert store.labels() == ["fist", "four_gesture"]
    assert json.loads(store.meta_path.read_text())["feature_length"] == N


def test_empty_recording_writes_nothing(store):
    assert store.append(dc.RecordingResult("s", "a", "", "t")) == 0
    assert not store.csv_path.exists()


def test_wrong_length_and_nan_rejected(store):
    bad = finished()
    bad.samples = [np.zeros(10, np.float32)]
    with pytest.raises(dc.DatasetError):
        store.append(bad)
    nan = finished()
    nan.samples[0][3] = np.nan
    with pytest.raises(dc.DatasetError):
        store.append(nan)
    assert not store.csv_path.exists()


def test_mode_mismatch_is_reported(store, tmp_path):
    store.append(finished())
    other = dc.DatasetStore(store.csv_path, store.meta_path, "hands+pose")
    with pytest.raises(dc.DatasetError, match="feature mode"):
        other.load()


def test_corrupt_csv_is_reported_and_never_extended(store):
    store.append(finished())
    store.csv_path.write_text("session_id,label\n1,2,3,4,5\n\x00\x00")
    with pytest.raises(dc.DatasetError):
        store.load()
    with pytest.raises(dc.DatasetError):
        store.append(finished())


def test_delete_session_and_label(store):
    store.append(finished("a_g", 3, session="s1"))
    store.append(finished("a_g", 2, session="s2"))
    store.append(finished("b_g", 4, session="s3"))
    assert store.last_session() == {"session_id": "s3", "label": "b_g", "samples": 4}
    assert store.delete_session("s3") == 4
    assert store.last_session()["session_id"] == "s2"
    assert store.delete_label("a_g") == 5
    assert store.load().empty
    assert store.delete_label("nope") == 0


# --- safe saving ------------------------------------------------------------------

def test_a_failed_save_keeps_every_earlier_recording(store, monkeypatch):
    import storage
    store.append(finished("a_g", 3, session="s1"))
    before = store.csv_path.read_bytes()

    def disk_full(*_a):
        raise OSError("No space left on device")
    monkeypatch.setattr(storage, "atomic_write_bytes", disk_full)
    with pytest.raises(OSError):
        store.append(finished("a_g", 4, session="s2"))
    assert store.csv_path.read_bytes() == before         # not half a row, not a lost file
    assert store.row_count() == 3


def test_recordings_saved_at_the_same_time_are_all_kept(store):
    """Two tabs (threads) saving at once used to be able to overwrite each other."""
    import threading
    threads = [threading.Thread(target=store.append, args=(finished("a_g", 5, session=f"s{i}"),))
               for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    df = store.load()
    assert len(df) == 40 and sorted(df["session_id"].unique()) == [f"s{i}" for i in range(8)]


def test_deleting_while_another_tab_saves_loses_nothing_else(store):
    import threading
    store.append(finished("a_g", 3, session="old"))
    adds = [threading.Thread(target=store.append, args=(finished("b_g", 2, session=f"n{i}"),))
            for i in range(5)]
    delete = threading.Thread(target=store.delete_session, args=("old",))
    for t in adds + [delete]:
        t.start()
    for t in adds + [delete]:
        t.join()
    assert sorted(store.load()["session_id"].unique()) == [f"n{i}" for i in range(5)]


def test_appending_after_a_file_without_a_final_newline(store):
    store.append(finished("a_g", 2, session="s1"))
    store.csv_path.write_bytes(store.csv_path.read_bytes().rstrip(b"\n"))
    store.append(finished("a_g", 3, session="s2"))
    assert store.row_count() == 5


def test_reading_is_cached_until_the_file_changes(store, monkeypatch):
    store.append(finished("a_g", 3, session="s1"))
    store.load()
    calls = []
    real = dc.pd.read_csv
    monkeypatch.setattr(dc.pd, "read_csv", lambda *a, **k: calls.append(1) or real(*a, **k))
    for _ in range(5):
        store.load(), store.row_count(), store.summary(), store.fingerprint()
    assert calls == []                                  # unchanged file: parsed once, earlier
    store.append(finished("b_g", 2, session="s2"))
    assert store.row_count() == 5 and len(calls) == 2   # the corruption check, then one read


def test_each_load_is_a_copy_the_caller_may_change(store):
    store.append(finished("a_g", 3, session="s1"))
    first = store.load()
    first.loc[0, "label"] = "changed"
    first.drop(index=1, inplace=True)
    again = store.load()
    assert len(again) == 3 and set(again["label"]) == {"a_g"}


def test_fingerprint_follows_the_contents(store, tmp_path):
    assert store.fingerprint() == ""
    store.append(finished("a_g", 3, session="s1"))
    one = store.fingerprint()
    df, fp = store.load_with_fingerprint()
    assert fp == one and len(one) == 64 and len(df) == 3
    store.append(finished("a_g", 2, session="s2"))
    two = store.fingerprint()
    assert two != one
    store.delete_session("s2")
    assert store.fingerprint() == one                    # same rows, same bytes, same fingerprint
    store.delete_session("s1")
    store.append(finished("a_g", 3, session="s9"))       # same number of rows, other recording
    assert store.row_count() == 3 and store.fingerprint() != one


def test_names_that_pandas_reads_as_missing_are_kept_as_typed(store):
    """A gesture named "Null" or "NaN", or a person named "NA", used to read back as a missing
    value: the recording vanished from the gesture list, "Delete gesture data" could not
    remove it, training dropped it and the Memes page stopped with a TypeError."""
    store.append(finished(dc.slugify_label("NaN"), 3, "NA", session="s1"))
    store.append(finished(dc.slugify_label("Null"), 2, "None", session="s2"))
    store.append(finished("wave", 2, "", session="s3"))
    df = store.load()
    assert store.labels() == ["nan", "null", "wave"]
    assert df["person"].tolist() == ["NA"] * 3 + ["None"] * 2 + ["", ""]
    assert store.summary()["label"].tolist() == ["nan", "null", "wave"]
    assert store.delete_label("null") == 2 and store.labels() == ["nan", "wave"]


def test_a_meta_file_that_is_not_json_text_is_a_dataset_error(store):
    store.append(finished())
    for content in (b"\xff\xfe\x00 not text", b"[]"):
        store.meta_path.write_bytes(content)
        with pytest.raises(dc.DatasetError, match="Cannot read"):
            store.load()


def test_class_status_levels():
    assert dc.class_status(10, 1)[0] == "bad"
    assert dc.class_status(config.TARGET_MIN_PER_CLASS, 1)[0] == "warn"
    assert dc.class_status(config.TARGET_MIN_PER_CLASS, config.MIN_SESSIONS_PER_CLASS)[0] == "ok"
    assert "Great" in dc.class_status(config.TARGET_GOOD_PER_CLASS, 5)[1]
