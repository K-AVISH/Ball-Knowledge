"""Pipeline check tests: synthetic videos, a stand-in detector and the real training,
prediction, steady vote and history code. No webcam, MediaPipe model or real clips."""
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_pipeline as cp  # noqa: E402
import config  # noqa: E402
import data_collector as dc  # noqa: E402
import import_videos as iv  # noqa: E402
import predictor as pr  # noqa: E402
import train_model as tm  # noqa: E402
from vision import Detection, HandDetection  # noqa: E402

FPS = 30
# Frame brightness the stand-in detector reads as each gesture; 0 is an empty frame.
BRIGHTNESS = {"peace": 220, "fist": 120}
SHAPES = {label: np.random.default_rng(10 + i).uniform(0.2, 0.8, size=(21, 3)).astype(np.float32)
          for i, label in enumerate(sorted(BRIGHTNESS))}


class FakeDetector:
    """The gesture whose brightness is closest to the frame's, with a little jitter."""

    def __init__(self):
        self.rng = np.random.default_rng(0)

    def detect(self, frame):
        level = frame.mean()
        if level < 60:
            return Detection()
        label = min(BRIGHTNESS, key=lambda g: abs(BRIGHTNESS[g] - level))
        lm = SHAPES[label] + self.rng.normal(scale=0.01, size=(21, 3)).astype(np.float32)
        return Detection(hands=[HandDetection("Right", 0.9, lm)])

    def close(self):
        pass


def video(path, segments, seed=0):
    """segments: [(gesture or None, frames)]. `seed` makes the file's bytes unique."""
    path.parent.mkdir(parents=True, exist_ok=True)
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), FPS, (160, 120))
    assert out.isOpened()
    first = True
    for gesture, n in segments:
        for _ in range(n):
            frame = np.full((120, 160, 3), BRIGHTNESS.get(gesture, 0), np.uint8)
            if first:
                frame[0, 0] = seed * 37 % 256
                first = False
            out.write(frame)
    out.release()
    return path


@pytest.fixture
def setup(tmp_path):
    """Three imported recordings per gesture in a scratch dataset."""
    store = dc.DatasetStore(tmp_path / "s.csv", tmp_path / "s.json", "hands")
    sources = []
    for i, gesture in enumerate(sorted(BRIGHTNESS)):
        for k in range(3):
            path = video(tmp_path / gesture / f"clip{k}.avi", [(None, 10), (gesture, 40), (None, 10)],
                         seed=i * 10 + k)
            sources.append(iv.VideoSource(path, gesture))
    outcomes = iv.import_videos(sources, store, detector_factory=FakeDetector)
    assert all(o.status == iv.IMPORTED for o in outcomes)
    return tmp_path, store, sources


def saved_model(store):
    """A model trained on everything in `store`, as the dashboard would load it."""
    df = tm.validate_dataset(store.load(), store.feature_length)[0].reset_index(drop=True)
    labels = sorted(df["label"].unique())
    X, y = tm._xy(df, labels)
    return pr.Predictor(tm.make_model(0.01).fit(X, y), labels, "hands")


def test_dataset_clips_are_checked_with_a_model_that_never_saw_them(setup, monkeypatch):
    _, store, sources = setup
    total = store.row_count()
    fitted_rows = []
    real_fit = tm.GradientDescentClassifier.fit

    def spy_fit(self, X, y):
        fitted_rows.append(len(X))
        return real_fit(self, X, y)

    monkeypatch.setattr(tm.GradientDescentClassifier, "fit", spy_fit)
    models = cp.ModelSource(store, saved_loader=lambda: pytest.fail("the saved model must not be used"),
                            l2=0.01)
    results = cp.check_clips(sources, models, detector_factory=FakeDetector)

    df = store.load()
    held_out_rows = [int((df["session_id"] == iv.session_id_for(iv.file_digest(s.path))).sum())
                     for s in sources]
    assert fitted_rows == [total - n for n in held_out_rows]          # one model per clip, without it
    for r, src in zip(results, sources):
        assert not r.error and r.model == "a model trained without this clip"
        assert r.frames == 60 and r.hand_frames == 40 and r.span == 40
        assert r.shown[cp.WRONG] == 0
        assert r.share(cp.RIGHT) > 0.9                               # all but the first 3 frames
        assert r.first_right_s == pytest.approx(3 / FPS)            # steady on the 4th hand frame
        assert [label for _, label in r.detections] == [src.label]


def test_a_new_clip_uses_the_saved_model_and_wrong_results_are_counted(setup):
    tmp_path, store, _ = setup
    model = saved_model(store)
    clip = video(tmp_path / "new" / "clip.avi", [(None, 5), ("fist", 20), ("peace", 20)], seed=99)
    # The clip is labelled peace, so its fist half shows the wrong gesture.
    results = cp.check_clips([iv.VideoSource(clip, "peace")], cp.ModelSource(store, lambda: model, 0.01),
                             detector_factory=FakeDetector)
    r = results[0]
    assert r.model == "the saved model" and not r.error
    assert r.shown[cp.WRONG] == 20 and r.shown[cp.RIGHT] == 17      # peace takes 3 frames to win
    assert [label for _, label in r.detections] == ["fist", "peace"]
    assert r.first_right_s == pytest.approx(23 / FPS)
    summary = cp.format_summary(results)
    assert "A wrong gesture was shown in 1 of 1 clips" in summary and "for 20 frames" in summary


def test_identical_copies_and_unknown_gestures_are_reported_not_checked(setup):
    tmp_path, store, sources = setup
    copy = tmp_path / "copy.avi"
    copy.write_bytes(sources[0].path.read_bytes())
    unknown = video(tmp_path / "wave" / "clip.avi", [("peace", 10)], seed=77)
    models = cp.ModelSource(store, lambda: saved_model(store), 0.01)
    results = cp.check_clips([sources[0], iv.VideoSource(copy, sources[0].label),
                              iv.VideoSource(unknown, "wave")], models, detector_factory=FakeDetector)
    assert not results[0].error
    assert "identical to clip0.avi" in results[1].error
    assert "does not know the gesture wave" in results[2].error
    assert "2 clip(s) could not be checked" in cp.format_summary(results)


def test_a_clip_filed_under_another_gesture_is_reported(setup):
    _, store, sources = setup
    models = cp.ModelSource(store, l2=0.01)
    r = cp.check_clips([iv.VideoSource(sources[0].path, "peace")], models, detector_factory=FakeDetector)[0]
    assert f"in the dataset as {sources[0].label}, not peace" in r.error


def test_the_only_recording_of_a_gesture_cannot_be_held_out(tmp_path):
    store = dc.DatasetStore(tmp_path / "s.csv", tmp_path / "s.json", "hands")
    sources = [iv.VideoSource(video(tmp_path / "a.avi", [("fist", 30)], seed=1), "fist"),
               iv.VideoSource(video(tmp_path / "b.avi", [("peace", 30)], seed=2), "peace"),
               iv.VideoSource(video(tmp_path / "c.avi", [("peace", 30)], seed=3), "peace")]
    iv.import_videos(sources, store, detector_factory=FakeDetector)
    r = cp.check_clips(sources[:1], cp.ModelSource(store, l2=0.01), detector_factory=FakeDetector)[0]
    assert "only recording of fist" in r.error


def test_dataset_clips_need_a_trained_model_for_its_settings(setup, monkeypatch):
    _, store, sources = setup
    monkeypatch.setattr(tm, "load_report", lambda: None)
    r = cp.check_clips(sources[:1], cp.ModelSource(store), detector_factory=FakeDetector)[0]
    assert "Train the model first" in r.error


def test_an_unreadable_report_is_a_clear_error_not_a_traceback(setup, monkeypatch):
    _, store, sources = setup

    def unreadable():
        raise tm.TrainingError("Cannot read training_report.json: Expecting value")
    monkeypatch.setattr(tm, "load_report", unreadable)
    r = cp.check_clips(sources[:1], cp.ModelSource(store), detector_factory=FakeDetector)[0]
    assert "Cannot read training_report.json" in r.error


@pytest.mark.parametrize("steady, status, expected, state", [
    (None, pr.NO_HAND, "peace", cp.NO_HAND),
    (None, pr.UNRECOGNISED, "peace", cp.UNSURE),
    (None, pr.RECOGNISED, "peace", cp.UNSURE),            # recognised, not yet steady
    ("peace", pr.RECOGNISED, "peace", cp.RIGHT),
    ("fist", pr.RECOGNISED, "peace", cp.WRONG),
    (config.NONE_LABEL, pr.RECOGNISED, "peace", cp.NO_GESTURE),
    (config.NONE_LABEL, pr.RECOGNISED, config.NONE_LABEL, cp.RIGHT),
    ("peace", pr.RECOGNISED, config.NONE_LABEL, cp.WRONG),   # a meme for a hand doing nothing
])
def test_dashboard_state(steady, status, expected, state):
    s = pr.Steady(steady, 0.9, 4, 7) if steady else None
    assert cp.dashboard_state(s, pr.Prediction(status), expected) == state
