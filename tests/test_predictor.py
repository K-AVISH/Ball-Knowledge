"""Stage 5 tests for predictor.py.

The model here is trained by train_model.train() on SYNTHETIC data, so these tests
check the code: loading, file checks, the confidence threshold, top predictions, the
worker thread and the hand-over from the video thread. They say nothing about how
well a model trained on real gesture recordings will recognise anything.
"""
import json
import shutil
import sys
import threading
import time
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
import data_collector as dc  # noqa: E402
import features  # noqa: E402
import predictor as pr  # noqa: E402
import train_model as tm  # noqa: E402
from vision import Detection, FrameProcessor, HandDetection, LandmarkHook  # noqa: E402

N = features.feature_length("hands")
LABELS = ["fist", "open_palm", "peace"]


def hand(seed):
    return np.random.default_rng(seed).uniform(0.2, 0.8, size=(21, 3)).astype(np.float32)


# Each synthetic gesture is a fixed right-hand shape plus small jitter per sample, built
# through features.build_feature_vector exactly as the collector does.
SHAPES = {label: hand(10 + i) for i, label in enumerate(LABELS)}


def vector_for(label, rng=None, jitter=0.0):
    pts = SHAPES[label]
    if rng is not None:
        pts = pts + rng.normal(scale=jitter, size=pts.shape).astype(np.float32)
    return features.build_feature_vector(pts, None, None, "hands")


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    """Train once with the real pipeline. Returns the folder holding the saved files."""
    root = tmp_path_factory.mktemp("trained")
    store = dc.DatasetStore(root / "s.csv", root / "s.json", "hands")
    rng = np.random.default_rng(0)
    for label in LABELS:
        for s in range(4):
            r = dc.RecordingResult(f"{label}-{s}", label, "", "2026-01-01T00:00:00")
            r.samples = [vector_for(label, rng, 0.01) for _ in range(25)]
            store.append(r)
    tm.train(store, model_path=root / "model.joblib", labels_path=root / "labels.json",
             report_path=root / "report.json")
    return root


def paths(root):
    return dict(model_path=root / "model.joblib", labels_path=root / "labels.json",
                report_path=root / "report.json")


def copy_of(trained, tmp_path):
    for name in ("model.joblib", "labels.json", "report.json"):
        shutil.copy(trained / name, tmp_path / name)
    return tmp_path


# --- loading -------------------------------------------------------------------

def test_loads_saved_model_and_labels(trained):
    p = pr.Predictor.load(**paths(trained))
    assert p.labels == LABELS
    assert p.feature_length == N
    assert p.trained_at
    assert p.warnings == []


def test_missing_model_is_not_trained(tmp_path):
    with pytest.raises(pr.NotTrainedError, match="Model performance"):
        pr.Predictor.load(**paths(tmp_path))


def test_missing_label_mapping_is_a_clear_error(trained, tmp_path):
    root = copy_of(trained, tmp_path)
    (root / "labels.json").unlink()
    with pytest.raises(pr.PredictorError, match="labels.json is missing") as info:
        pr.Predictor.load(**paths(root))
    assert not isinstance(info.value, pr.NotTrainedError)


@pytest.mark.parametrize("content, message", [
    ("not json", "Cannot read labels.json"),
    ("[]", "not a label mapping"),
    ('{"a": "fist"}', "not class numbers"),
    ('{"0": "fist", "2": "peace"}', "incomplete"),
    ('{"0": "fist", "1": "fist"}', "same gesture twice"),
])
def test_bad_label_mapping_is_rejected(trained, tmp_path, content, message):
    root = copy_of(trained, tmp_path)
    (root / "labels.json").write_text(content)
    with pytest.raises(pr.PredictorError, match=message):
        pr.Predictor.load(**paths(root))


@pytest.mark.parametrize("name, content", [
    ("labels.json", b"\x80\x04\x95 a pickle, not text"),        # the model file copied over it
    ("report.json", b"\x80\x04\x95 a pickle, not text"),
    ("report.json", b"[1, 2]"),                                 # JSON, but not a report
])
def test_model_files_that_are_not_json_objects_are_a_clear_error(trained, tmp_path, name, content):
    root = copy_of(trained, tmp_path)
    (root / name).write_bytes(content)
    with pytest.raises(pr.PredictorError, match="Train the model again"):
        pr.Predictor.load(**paths(root))


def test_mapping_with_fewer_gestures_than_the_model_is_rejected(trained, tmp_path):
    root = copy_of(trained, tmp_path)
    (root / "labels.json").write_text(json.dumps({"0": "fist", "1": "open_palm"}))
    (root / "report.json").unlink()                 # leave only the model to compare with
    with pytest.raises(pr.PredictorError, match="do not match"):
        pr.Predictor.load(**paths(root))


def test_report_and_mapping_must_agree(trained, tmp_path):
    root = copy_of(trained, tmp_path)
    (root / "labels.json").write_text(json.dumps({"0": "a", "1": "b", "2": "c"}))
    with pytest.raises(pr.PredictorError, match="different gestures"):
        pr.Predictor.load(**paths(root))


def test_feature_mode_mismatch_is_rejected(trained):
    with pytest.raises(pr.PredictorError, match="'hands' features but the app is set to 'hands\\+pose'"):
        pr.Predictor.load(**paths(trained), feature_mode="hands+pose")


def test_feature_length_is_checked_without_a_report(trained, tmp_path):
    root = copy_of(trained, tmp_path)
    (root / "report.json").unlink()
    with pytest.raises(pr.PredictorError, match="expects 126 features"):
        pr.Predictor.load(**paths(root), feature_mode="hands+pose")


@pytest.mark.parametrize("with_report, message", [
    (True, "not the model that report.json was saved with"),   # caught by the checksum
    (False, "Cannot load model.joblib"),                       # no report: caught by unpickling
])
def test_corrupted_model_file_is_a_clear_error(trained, tmp_path, with_report, message):
    root = copy_of(trained, tmp_path)
    (root / "model.joblib").write_bytes(b"not a model")
    if not with_report:
        (root / "report.json").unlink()
    with pytest.raises(pr.PredictorError, match=message):
        pr.Predictor.load(**paths(root))


def test_model_from_another_run_is_refused(trained, tmp_path):
    """A save interrupted between renames can leave a new model beside the old report and
    labels. Same gestures, same shape, so only the checksum can tell."""
    root = copy_of(trained, tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    store = dc.DatasetStore(other / "s.csv", other / "s.json", "hands")
    rng = np.random.default_rng(7)
    for label in LABELS:
        for s in range(3):
            r = dc.RecordingResult(f"{label}-x{s}", label, "", "2026-01-01T00:00:00")
            r.samples = [vector_for(label, rng, 0.05) for _ in range(10)]
            store.append(r)
    tm.train(store, **paths(other))
    shutil.copy(other / "model.joblib", root / "model.joblib")
    with pytest.raises(pr.PredictorError, match="not the model that report.json was saved with"):
        pr.Predictor.load(**paths(root))


def test_report_records_the_checksum_of_the_saved_model(trained):
    import storage
    report = json.loads((trained / "report.json").read_text())
    assert report["artifacts"]["model_sha256"] == storage.sha256_bytes(
        (trained / "model.joblib").read_bytes())


def test_reports_from_before_checksums_still_load(trained, tmp_path):
    root = copy_of(trained, tmp_path)
    report = json.loads((root / "report.json").read_text())
    del report["artifacts"]
    (root / "report.json").write_text(json.dumps(report))
    assert pr.Predictor.load(**paths(root)).labels == LABELS


def test_older_scikit_learn_version_is_noted(trained, tmp_path):
    root = copy_of(trained, tmp_path)
    report = json.loads((root / "report.json").read_text())
    report["sklearn_version"] = "0.0.1"
    (root / "report.json").write_text(json.dumps(report))
    p = pr.Predictor.load(**paths(root))
    assert any("0.0.1" in w for w in p.warnings)


def test_bad_threshold_is_rejected(trained):
    for bad in (0, -0.1, 1.5):
        with pytest.raises(ValueError):
            pr.Predictor.load(**paths(trained), threshold=bad)


# --- predicting ----------------------------------------------------------------

def test_no_hand_gives_no_hand_without_running_the_model(trained):
    p = pr.Predictor.load(**paths(trained))
    out = p.predict(None)
    assert out.status == pr.NO_HAND
    assert out.label is None and out.confidence is None and out.top == ()


@pytest.mark.parametrize("label", LABELS)
def test_each_trained_shape_is_recognised(trained, label):
    p = pr.Predictor.load(**paths(trained))
    out = p.predict(vector_for(label))
    assert out.status == pr.RECOGNISED
    assert out.label == label
    assert out.confidence >= p.threshold
    assert out.top[0] == (label, out.confidence)
    assert out.inference_ms is not None and out.inference_ms >= 0


def test_below_threshold_is_unrecognised_and_names_no_gesture(trained):
    p = pr.Predictor.load(**paths(trained), threshold=1.0)
    out = p.predict(vector_for("fist"))
    if out.confidence < 1.0:
        assert out.status == pr.UNRECOGNISED
        assert out.label is None                    # never a guess
        assert out.top                              # scores are still available to inspect
    else:                                           # a forest can be unanimous; then it is accepted
        assert out.status == pr.RECOGNISED


def test_threshold_is_inclusive(trained):
    p = pr.Predictor.load(**paths(trained))
    conf = p.predict(vector_for("peace")).confidence
    at = pr.Predictor.load(**paths(trained), threshold=conf).predict(vector_for("peace"))
    above = pr.Predictor.load(**paths(trained), threshold=min(1.0, conf + 1e-6)).predict(vector_for("peace"))
    assert at.status == pr.RECOGNISED
    if conf + 1e-6 <= 1.0:
        assert above.status == pr.UNRECOGNISED


def test_top_predictions_are_sorted_and_limited(trained):
    p = pr.Predictor.load(**paths(trained), top_k=2)
    out = p.predict(vector_for("open_palm"))
    assert len(out.top) == 2
    scores = [s for _, s in out.top]
    assert scores == sorted(scores, reverse=True)
    assert {g for g, _ in out.top} <= set(LABELS)
    full = pr.Predictor.load(**paths(trained), top_k=10).predict(vector_for("open_palm"))
    assert len(full.top) == 3                       # never more than the trained gestures
    assert sum(s for _, s in full.top) == pytest.approx(1.0, abs=1e-6)


def test_wrong_vector_length_or_nan_raises(trained):
    p = pr.Predictor.load(**paths(trained))
    with pytest.raises(pr.PredictorError, match="length 10"):
        p.predict(np.zeros(10, np.float32))
    bad = vector_for("fist").copy()
    bad[0] = np.nan
    with pytest.raises(pr.PredictorError, match="NaN"):
        p.predict(bad)


def test_random_forest_is_switched_to_one_thread(trained):
    p = pr.Predictor.load(**paths(trained))
    params = p.model.get_params(deep=False)
    if "n_jobs" in params:
        assert params["n_jobs"] == 1


def test_a_model_with_worker_threads_is_switched_to_one():
    """The test above checks the saved model, which has had no n_jobs since 13 October, so its
    assertion never runs. Any estimator may replace make_model (ML handoff), so give Predictor
    one that has n_jobs."""
    from sklearn.ensemble import RandomForestClassifier
    X = np.array([vector_for(label) for label in LABELS])
    forest = RandomForestClassifier(n_estimators=3, n_jobs=-1, random_state=0).fit(X, [0, 1, 2])
    assert pr.Predictor(forest, LABELS).model.get_params()["n_jobs"] == 1


def test_is_fresh():
    assert not pr.is_fresh(None)
    assert pr.is_fresh(pr.Prediction(pr.NO_HAND, at=time.time()))
    assert not pr.is_fresh(pr.Prediction(pr.NO_HAND, at=time.time() - 5))


# --- the worker thread ---------------------------------------------------------

class SlowPredictor:
    """Stands in for a slow model and records which vectors it was given."""

    threshold = 0.7

    def __init__(self, delay=0.3):
        self.delay = delay
        self.seen = []
        self.started = threading.Event()

    def predict(self, vector):
        self.started.set()
        time.sleep(self.delay)
        self.seen.append(None if vector is None else float(vector[0]))
        return pr.Prediction(pr.RECOGNISED if vector is not None else pr.NO_HAND,
                             label="x" if vector is not None else None, at=time.time())


def wait_for(cond, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


def test_offer_never_waits_for_a_slow_model():
    slow = SlowPredictor(delay=0.5)
    rec = pr.LiveRecognizer(slow)
    rec.offer(np.ones(3, np.float32))
    assert slow.started.wait(2)
    start = time.perf_counter()
    for i in range(20):                              # the video thread keeps going
        rec.offer(np.full(3, i, np.float32))
    assert (time.perf_counter() - start) < 0.1


def test_only_the_newest_frame_is_classified():
    slow = SlowPredictor(delay=0.3)
    rec = pr.LiveRecognizer(slow)
    rec.offer(np.zeros(3, np.float32))
    assert slow.started.wait(2)
    for i in range(1, 6):
        rec.offer(np.full(3, i, np.float32))
    assert wait_for(lambda: len(slow.seen) == 2)
    assert slow.seen == [0.0, 5.0]                   # frames 1 to 4 were skipped
    assert rec.frames_skipped == 4
    assert rec.latest().status == pr.RECOGNISED


def test_no_hand_frames_reach_the_model_as_none():
    slow = SlowPredictor(delay=0)
    rec = pr.LiveRecognizer(slow)
    rec.offer(None)
    assert wait_for(lambda: rec.latest() is not None)
    assert rec.latest().status == pr.NO_HAND


def test_errors_are_reported_and_the_worker_survives():
    class Broken:
        threshold = 0.7
        calls = 0

        def predict(self, vector):
            Broken.calls += 1
            if Broken.calls == 1:
                raise ValueError("bad frame")
            return pr.Prediction(pr.NO_HAND, at=time.time())

    rec = pr.LiveRecognizer(Broken())
    rec.offer(np.ones(3, np.float32))
    assert wait_for(lambda: rec.latest() is not None)
    assert rec.latest().status == pr.ERROR and "bad frame" in rec.latest().error
    rec.offer(None)
    assert wait_for(lambda: rec.latest().status == pr.NO_HAND)


def test_without_a_model_offers_are_ignored():
    rec = pr.LiveRecognizer(None)
    rec.offer(np.ones(3, np.float32))
    assert not rec.is_running() and rec.latest() is None


def test_reset_and_model_switch_clear_the_result_and_drop_late_answers():
    slow = SlowPredictor(delay=0.3)
    rec = pr.LiveRecognizer(slow)
    rec.offer(np.ones(3, np.float32))
    assert slow.started.wait(2)
    rec.reset()                                      # camera stopped while the model was busy
    assert wait_for(lambda: len(slow.seen) == 1)
    time.sleep(0.05)
    assert rec.latest() is None                      # the late answer was dropped

    rec.offer(None)
    assert wait_for(lambda: rec.latest() is not None)
    other = SlowPredictor(delay=0)
    rec.use(other)
    assert rec.latest() is None and rec.predictor is other


def test_worker_stops_when_frames_stop_and_restarts():
    rec = pr.LiveRecognizer(SlowPredictor(delay=0), idle_exit_s=0.2)
    rec.offer(None)
    assert rec.is_running()
    assert wait_for(lambda: not rec.is_running(), timeout=2)
    rec.offer(None)
    assert rec.is_running()


# --- end to end: video thread -> features -> recogniser ---------------------------

class FakeDetector:
    def __init__(self, detection):
        self.detection = detection

    def detect(self, frame):
        return self.detection


def test_frames_flow_from_the_landmark_hook_to_a_prediction(trained):
    """The same LandmarkHook output that the collector saves is what gets classified."""
    det = Detection(hands=[HandDetection("Right", 0.9, SHAPES["peace"])])
    hook = LandmarkHook(detector_factory=lambda: FakeDetector(det))
    proc = FrameProcessor(frame_hook=hook)

    class Spy:
        def __init__(self):
            self.vectors = []

        def offer(self, v):
            self.vectors.append(v)

    proc.recorder = Spy()
    proc.recognizer = pr.LiveRecognizer(pr.Predictor.load(**paths(trained)))
    proc.process(np.zeros((480, 640, 3), np.uint8))

    # the hook rescales x for the 640x480 frame before building the vector
    expected = features.build_feature_vector(
        features.correct_aspect(SHAPES["peace"], 640, 480), None, None, "hands")
    assert np.array_equal(proc.recorder.vectors[0], expected)
    assert wait_for(lambda: proc.recognizer.latest() is not None)
    out = proc.recognizer.latest()
    assert out.status == pr.RECOGNISED and out.label == "peace"
    assert proc.get_stats().error is None

    det.hands = []                                   # hand leaves the frame
    proc.process(np.zeros((480, 640, 3), np.uint8))
    assert wait_for(lambda: proc.recognizer.latest().status == pr.NO_HAND)


# --- the steadiness vote used by the meme panel -------------------------------

class ScriptedPredictor:
    """Returns a scripted result per frame: a label (recognised), "?" (below the
    threshold) or None (no hand). Each result's `at` is its frame number."""

    threshold = 0.7

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def predict(self, vector):
        i, item = self.calls, self.script[self.calls]
        self.calls += 1
        if item is None:
            return pr.Prediction(pr.NO_HAND, at=i)
        if item == "?":
            return pr.Prediction(pr.UNRECOGNISED, confidence=0.5, at=i)
        label, confidence = item if isinstance(item, tuple) else (item, 0.9)
        return pr.Prediction(pr.RECOGNISED, label, confidence, at=i)


def run_script(script, **kw):
    """Feed one frame at a time and return stable() after each frame."""
    rec = pr.LiveRecognizer(ScriptedPredictor(script), **kw)
    out = []
    for i in range(len(script)):
        rec.offer(np.zeros(3, np.float32))
        assert wait_for(lambda: rec.latest() is not None and rec.latest().at == i)
        out.append(rec.stable())
    return rec, out


def test_a_gesture_is_steady_after_winning_4_of_7_frames():
    _, out = run_script(["peace"] * 5)
    assert out == [None, None, None, "peace", "peace"]


def test_no_hand_and_unsure_frames_vote_for_nothing():
    _, out = run_script(["peace", None, "peace", "?", "peace", "peace"])
    assert out == [None, None, None, None, None, "peace"]


def test_a_gesture_stops_being_steady_once_it_loses_the_window():
    _, out = run_script(["peace"] * 4 + [None] * 4)
    assert out[3:] == ["peace", "peace", "peace", "peace", None]   # 4 of 7, then 3 of 7


def test_a_new_gesture_takes_over_only_when_it_wins():
    _, out = run_script(["peace"] * 4 + ["fist"] * 4)
    # window after each frame: PPPP, PPPPF, PPPPFF, PPPPFFF (peace still 4 of 7), PPPFFFF
    assert out[3:] == ["peace", "peace", "peace", "peace", "fist"]


def test_reset_clears_the_vote():
    rec, out = run_script(["peace"] * 4)
    assert out[-1] == "peace"
    rec.reset()
    assert rec.stable() is None


def test_vote_settings_are_checked():
    with pytest.raises(ValueError):
        pr.LiveRecognizer(window=3, min_votes=4)


def test_steady_confidence_is_the_mean_of_the_frames_that_voted_for_it():
    rec, _ = run_script([("peace", 0.8), None, ("peace", 0.9), ("fist", 0.99), ("peace", 0.7),
                         ("peace", 1.0)])
    steady = rec.steady()
    assert (steady.label, steady.votes, steady.frames) == ("peace", 4, 6)
    assert steady.confidence == pytest.approx((0.8 + 0.9 + 0.7 + 1.0) / 4)


# --- recent detections ---------------------------------------------------------------

def steady(label, confidence=0.9):
    return pr.Steady(label, confidence, 4, 7)


def test_holding_a_gesture_is_one_detection():
    log = pr.DetectionLog(repeat_gap_s=2)
    for t in range(100):
        log.observe(steady("peace"), at=t * 0.05)
    assert [d.label for d in log.entries()] == ["peace"] and log.total == 1


def test_a_short_dropout_adds_nothing_but_a_long_pause_does():
    log = pr.DetectionLog(repeat_gap_s=2)
    log.observe(steady("peace"), at=0.0)
    log.observe(None, at=1.0)                    # hand gone for a moment
    log.observe(steady("peace"), at=1.5)
    assert log.total == 1
    log.observe(None, at=3.0)
    log.observe(steady("peace"), at=4.0)         # 2.5 s after it was last the result
    assert log.total == 2


def test_each_change_of_gesture_is_a_detection_newest_first():
    log = pr.DetectionLog(repeat_gap_s=2)
    for t, label in enumerate(["peace", "fist", "peace"]):
        log.observe(steady(label, 0.8 + t / 10), at=float(t))
    assert [(d.label, d.at) for d in log.entries()] == [("peace", 2.0), ("fist", 1.0), ("peace", 0.0)]
    assert log.entries()[0].confidence == pytest.approx(1.0)


def test_no_gesture_class_and_no_result_are_never_listed():
    log = pr.DetectionLog()
    log.observe(None, at=0.0)
    log.observe(steady(config.NONE_LABEL), at=1.0)
    assert log.entries() == () and log.total == 0


def test_history_keeps_the_newest_entries_and_counts_them_all():
    log = pr.DetectionLog(keep=3)
    for t in range(5):
        log.observe(steady(f"g{t}"), at=float(t))
    assert [d.label for d in log.entries()] == ["g4", "g3", "g2"] and log.total == 5


def test_recognizer_logs_once_per_steady_gesture_and_keeps_history_after_reset():
    rec, _ = run_script(["peace"] * 6 + ["fist"] * 8, log=pr.DetectionLog(repeat_gap_s=100))
    entries, total = rec.history()
    # fist wins the window (frames 3 to 9: 3 peace, 4 fist) at frame 9
    assert [(d.label, d.at) for d in entries] == [("fist", 9), ("peace", 3)] and total == 2
    rec.reset()                                  # the camera stopping does not clear the session
    assert rec.history()[1] == 2


# --- replaying a video on the calling thread (check_pipeline.py) ----------------------

def test_classify_gives_the_same_vote_and_history_as_the_worker():
    script = ["peace"] * 5 + [None, "?"] + ["fist"] * 6
    threaded, threaded_out = run_script(script, log=pr.DetectionLog(repeat_gap_s=100))
    rec = pr.LiveRecognizer(ScriptedPredictor(script), log=pr.DetectionLog(repeat_gap_s=100))
    out = []
    for _ in script:
        rec.classify(np.zeros(3, np.float32))
        out.append(rec.stable())
    assert out == threaded_out
    assert rec.history() == threaded.history()
    assert not rec.is_running()                      # no worker thread was started


def test_classify_uses_the_given_time_for_the_history():
    rec = pr.LiveRecognizer(ScriptedPredictor(["peace"] * 4 + [None] * 4 + ["peace"] * 4),
                            log=pr.DetectionLog(repeat_gap_s=2))
    for i in range(12):
        result = rec.classify(np.zeros(3, np.float32), at=i * 0.5)   # a video at 2 frames per second
        assert result.at == i * 0.5
    # peace steady at 1.5 s, gone from 3.5 s, steady again at 5.5 s: 2.5 s later, so listed twice
    assert [(d.label, d.at) for d in rec.history()[0]] == [("peace", 5.5), ("peace", 1.5)]


def test_classify_without_a_model_is_a_clear_error():
    with pytest.raises(pr.PredictorError, match="No model"):
        pr.LiveRecognizer().classify(None)
