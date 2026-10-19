"""Stage 4 tests for train_model.py.

All data here is synthetic, so these tests check the CODE (validation, leak-free
testing by recording, evaluation maths, saving). They say nothing about how accurate a model
trained on real gesture recordings will be.
"""
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
import train_model as tm  # noqa: E402

N = features.feature_length("hands")


def make_store(tmp_path, spec, per_session=40, seed=0, separable=True, name="d"):
    """spec: {label: n_sessions}. Class means differ when `separable`; every session also
    gets its own offset, like different lighting or hand position."""
    store = dc.DatasetStore(tmp_path / f"{name}.csv", tmp_path / f"{name}.json", "hands")
    rng = np.random.default_rng(seed)
    centres = {l: rng.normal(size=N) * (3.0 if separable else 0.0) for l in spec}
    for label, n_sessions in spec.items():
        for s in range(n_sessions):
            offset = rng.normal(size=N) * 0.3
            r = dc.RecordingResult(f"{label}-{s}", label, f"person{s % 2}", "2026-01-01T00:00:00")
            r.samples = [(centres[label] + offset + rng.normal(size=N) * 0.5).astype(np.float32)
                         for _ in range(per_session)]
            store.append(r)
    return store


def out_paths(tmp_path):
    return dict(model_path=tmp_path / "m" / "model.joblib", labels_path=tmp_path / "m" / "labels.json",
                report_path=tmp_path / "m" / "report.json")


# --- validation ------------------------------------------------------------

def test_validation_drops_each_kind_of_bad_row_and_counts_them(tmp_path):
    store = make_store(tmp_path, {"a": 3, "b": 3}, per_session=5)
    df = store.load()
    cols = store.columns[4:]
    df.loc[0, cols[3]] = np.nan                    # missing value
    df.loc[1, cols[5]] = np.inf                    # infinite
    df.loc[2, "label"] = ""                        # blank label
    df.loc[3, cols] = 0.0                          # all zero
    df[cols[0]] = df[cols[0]].astype(object)
    df.loc[4, cols[0]] = "oops"                    # not a number
    clean, dropped = tm.validate_dataset(df, N)
    assert len(clean) == len(df) - 5
    assert dropped["missing gesture label"] == 1
    assert dropped["all-zero feature vector"] == 1
    assert dropped["non-numeric, missing or infinite feature values"] == 3
    assert clean[cols].notna().all().all() and np.isfinite(clean[cols].to_numpy()).all()


def test_validation_drops_session_ids_shared_by_two_gestures(tmp_path):
    df = make_store(tmp_path, {"a": 3, "b": 3}, per_session=4).load()
    df.loc[df["label"] == "b", "session_id"] = df.loc[df["label"] == "b", "session_id"].replace(
        {"b-0": "a-0"})
    clean, dropped = tm.validate_dataset(df, N)
    assert "a-0" not in set(clean["session_id"])
    assert dropped["recording id used by more than one gesture"] == 8


def test_validation_rejects_wrong_feature_count(tmp_path):
    df = make_store(tmp_path, {"a": 3}, per_session=3).load().iloc[:, :-5]
    with pytest.raises(tm.TrainingError, match="feature columns"):
        tm.validate_dataset(df, N)


# --- testing by recording -------------------------------------------------

def test_too_few_recordings_names_the_gestures(tmp_path):
    df = make_store(tmp_path, {"a": 3, "b": 2, "c": 1}, per_session=5).load()
    with pytest.raises(tm.TrainingError) as err:
        tm.check_recordings(df, min_sessions=2)
    assert "c has 1" in str(err.value) and "b has" not in str(err.value) and "a has" not in str(err.value)
    tm.check_recordings(df[df["label"] != "c"], min_sessions=2)          # 2 recordings are enough


def test_every_row_is_predicted_by_a_model_that_never_saw_its_recording(tmp_path):
    df = make_store(tmp_path, {"a": 3, "b": 2}, per_session=6).load().reset_index(drop=True)
    seen = []

    class Spy:
        """Remembers which rows it was trained on; predicts uniform probabilities."""
        def __init__(self, l2):
            pass

        def fit(self, X, y):
            self.classes_ = np.unique(y)
            seen.append({tuple(row) for row in X})
            return self

        def predict_proba(self, X):
            for row in X:
                assert tuple(row) not in seen[-1]           # never trained on what it predicts
            return np.full((len(X), len(self.classes_)), 1 / len(self.classes_))

    proba = tm.held_out_probabilities(df, ["a", "b"], 0.1, make=Spy)
    assert len(seen) == 5                                    # one model per recording
    assert proba.shape == (len(df), 2) and np.allclose(proba.sum(axis=1), 1)


def test_testing_by_recording_stops_a_model_cheating_on_recording_identity(tmp_path):
    """Features identify the RECORDING, labels are random per recording, so there is nothing
    real to learn. Holding out whole recordings must score near chance. A naive frame-level
    split on the same data scores high, which is exactly the leak this project avoids."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split

    rng = np.random.default_rng(0)
    rows = []
    for s in range(30):
        offset = rng.normal(size=N) * 5.0
        label = ["a", "b", "c"][s % 3] if s < 3 else rng.choice(["a", "b", "c"])
        for _ in range(20):
            rows.append([f"s{s}", label, "x", "t", *(offset + rng.normal(size=N) * 0.1)])
    df = pd.DataFrame(rows, columns=dc.META_COLUMNS + [f"f{i:03d}" for i in range(N)])
    labels = ["a", "b", "c"]

    forest = lambda _l2: RandomForestClassifier(50, random_state=0)
    proba = tm.held_out_probabilities(df, labels, 0.1, make=forest)
    _, y = tm._xy(df, labels)
    honest = (proba.argmax(axis=1) == y).mean()

    X, y = tm._xy(df, labels)
    Xa, Xb, ya, yb = train_test_split(X, y, test_size=0.3, random_state=0)
    leaky = RandomForestClassifier(50, random_state=0).fit(Xa, ya).score(Xb, yb)

    assert leaky > 0.9
    assert honest < 0.7


def test_balanced_cost_counts_each_gesture_equally():
    # gesture 0 has 3 samples, gesture 1 has 1: each gesture contributes half of the cost
    proba = np.array([[.5, .5], [.5, .5], [.5, .5], [.1, .9]])
    y = np.array([0, 0, 0, 1])
    expected = 0.5 * -np.log(.5) + 0.5 * -np.log(.9)
    assert tm.balanced_cost(proba, y, 2) == pytest.approx(expected)


def test_per_recording_lists_the_worst_recording_first(tmp_path):
    df = pd.DataFrame({"session_id": ["r1", "r1", "r2", "r2"], "label": ["a", "a", "b", "b"],
                       "person": "", "timestamp": "", "f000": [1.0, 1.0, 2.0, 2.0]})
    proba = np.array([[.9, .1], [.8, .2], [.6, .4], [.3, .7]])     # r2 has one wrong of two
    rows = tm.per_recording(df, proba, ["a", "b"])
    assert [r["session_id"] for r in rows] == ["r2", "r1"]
    assert rows[0]["accuracy"] == 0.5 and rows[1]["accuracy"] == 1.0
    assert rows[1]["cost"] == round(float(-(np.log(.9) + np.log(.8)) / 2), 4)


# --- evaluation maths -------------------------------------------------------

class StubModel:
    classes_ = np.array([0, 1, 2])

    def __init__(self, proba):
        self.proba = np.asarray(proba, dtype=float)

    def predict_proba(self, X):
        return self.proba


def test_evaluate_matches_hand_computed_numbers():
    # truth:     0    0    1    1    2    2
    # predicted: 0    1    1    1    2    0
    proba = [[.9, .05, .05], [.2, .7, .1], [.1, .8, .1], [.1, .6, .3], [.1, .1, .8], [.5, .3, .2]]
    m = tm.evaluate(StubModel(proba), np.zeros((6, 1)), np.array([0, 0, 1, 1, 2, 2]), ["a", "b", "c"])
    assert m["accuracy"] == round(4 / 6, 4)
    assert m["confusion_matrix"] == [[1, 1, 0], [0, 2, 0], [1, 0, 1]]
    assert m["per_class"]["b"]["precision"] == round(2 / 3, 4)
    assert m["per_class"]["b"]["recall"] == 1.0
    assert m["per_class"]["a"]["recall"] == 0.5
    assert m["per_class"]["c"]["support"] == 2
    assert m["top_confusions"][0] == {"true": "a", "predicted": "b", "count": 1, "share_of_true": 0.5}
    # cutoff 0.8: confident predictions are rows 0, 2, 4 (all correct)
    at80 = [t for t in m["thresholds"] if t["threshold"] == 0.8][0]
    assert at80["coverage"] == 0.5 and at80["accuracy"] == 1.0
    assert m["mean_confidence_wrong"] == round((0.7 + 0.5) / 2, 4)
    # every gesture has 2 samples, so the balanced cost is the plain mean of -log p(true)
    assert m["cost"] == round(float(-np.log([.9, .2, .8, .6, .8, .2]).mean()), 4)


def test_threshold_with_nothing_accepted_has_no_accuracy():
    m = tm.evaluate(StubModel([[.4, .3, .3]]), np.zeros((1, 1)), np.array([0]), ["a", "b", "c"])
    assert [t for t in m["thresholds"] if t["threshold"] == 0.9][0]["accuracy"] is None


def test_top_confusions_orders_by_count():
    cm = np.array([[5, 3, 0], [1, 6, 0], [0, 2, 4]])
    out = tm.top_confusions(cm, ["a", "b", "c"], limit=2)
    assert [(c["true"], c["predicted"], c["count"]) for c in out] == [("a", "b", 3), ("c", "b", 2)]


# --- the whole pipeline -----------------------------------------------------

def test_train_end_to_end_saves_loadable_artifacts(tmp_path):
    import joblib
    from gd_model import GradientDescentClassifier

    store = make_store(tmp_path, {"fist": 4, "four_gesture": 4, "peace": 4}, per_session=30)
    paths = out_paths(tmp_path)
    report = tm.train(store=store, **paths)

    assert report["labels"] == ["fist", "four_gesture", "peace"]
    assert report["test"]["accuracy"] > 0.9               # well-separated synthetic classes
    assert report["test"]["samples"] == report["dataset"]["rows_used"] == 360   # every row held out once
    assert sum(sum(r) for r in report["test"]["confusion_matrix"]) == report["test"]["samples"]
    assert sum(m["support"] for m in report["test"]["per_class"].values()) == report["test"]["samples"]
    assert report["evaluation"]["recordings"] == 12
    assert sum(r["samples"] for r in report["evaluation"]["per_recording"]) == 360

    cost = report["cost"]
    assert cost["converged"] and cost["slope_at_end"] <= config.GD_TOLERANCE
    assert cost["l2"] == min(cost["l2_options"], key=lambda o: o["held_out_cost"])["l2"]
    assert cost["history"][0] == [0, round(float(np.log(3)), 8)]     # zero weights: all gestures equal
    costs = [c for _, c in cost["history"]]
    assert all(b <= a + 1e-12 for a, b in zip(costs, costs[1:]))       # never goes up
    assert costs[-1] == pytest.approx(cost["training_cost"], abs=1e-6)

    model = joblib.load(paths["model_path"])
    assert isinstance(model, GradientDescentClassifier) and model.l2 == cost["l2"]
    mapping = json.loads(paths["labels_path"].read_text())
    assert mapping == {"0": "fist", "1": "four_gesture", "2": "peace"}
    X = store.load()[store.columns[4:]].to_numpy(dtype=np.float32)[:5]
    assert model.predict_proba(X).shape == (5, 3)
    assert json.loads(paths["report_path"].read_text())["test"]["accuracy"] == report["test"]["accuracy"]
    assert tm.load_report(paths["report_path"])["model_name"] == report["model_name"]
    assert "Training report" in tm.format_report(report)


def test_training_is_repeatable(tmp_path):
    store = make_store(tmp_path, {"a": 4, "b": 4}, per_session=20)
    r1 = tm.train(store=store, **out_paths(tmp_path))
    r2 = tm.train(store=store, **out_paths(tmp_path))
    assert r1["test"] == r2["test"] and r1["cost"] == r2["cost"] and r1["evaluation"] == r2["evaluation"]


def test_two_recordings_per_gesture_are_enough(tmp_path):
    report = tm.train(store=make_store(tmp_path, {"a": 2, "b": 3}, per_session=20), **out_paths(tmp_path))
    assert report["evaluation"]["recordings"] == 5


def test_a_single_regularisation_option_is_used_as_given(tmp_path):
    store = make_store(tmp_path, {"a": 3, "b": 3}, per_session=20)
    report = tm.train(store=store, l2_options=(0.05,), **out_paths(tmp_path))
    assert report["cost"]["l2"] == 0.05
    assert not any("chosen from" in w for w in report["warnings"])


def test_failed_training_leaves_the_previous_model_untouched(tmp_path):
    good = make_store(tmp_path, {"a": 4, "b": 4}, per_session=20, name="good")
    bad = make_store(tmp_path, {"a": 4, "b": 1}, per_session=20, name="bad")
    paths = out_paths(tmp_path)
    tm.train(store=good, **paths)
    before = {k: p.read_bytes() for k, p in paths.items()}
    with pytest.raises(tm.TrainingError):
        tm.train(store=bad, **paths)
    assert {k: p.read_bytes() for k, p in paths.items()} == before
    assert not list((tmp_path / "m").glob("*.tmp"))


@pytest.mark.parametrize("spec,message", [
    ({}, "no samples"),
    ({"only": 4}, "at least 2 different gestures"),
])
def test_clear_errors_for_unusable_data(tmp_path, spec, message):
    store = make_store(tmp_path, spec, per_session=10) if spec else dc.DatasetStore(
        tmp_path / "e.csv", tmp_path / "e.json", "hands")
    with pytest.raises(tm.TrainingError, match=message):
        tm.train(store=store, **out_paths(tmp_path))


def test_feature_mode_mismatch_is_a_training_error(tmp_path):
    make_store(tmp_path, {"a": 3, "b": 3}, per_session=5)
    other = dc.DatasetStore(tmp_path / "d.csv", tmp_path / "d.json", "hands+pose")
    with pytest.raises(tm.TrainingError, match="feature mode"):
        tm.train(store=other, **out_paths(tmp_path))


def test_warnings_are_honest_about_thin_or_perfect_results(tmp_path):
    store = make_store(tmp_path, {"a": 2, "b": 3}, per_session=10)
    report = tm.train(store=store, **out_paths(tmp_path))
    text = " ".join(report["warnings"])
    assert "Fewer than 3 recordings for: a." in text     # b has 3, so only a is named
    assert "Perfect held-out accuracy" in text           # separable synthetic data scores 100%
    assert "Very few samples for: a" in text             # 20 samples of a
    assert "no 'none' gesture" in text
    assert "chosen from 5 options" in text


def test_a_none_gesture_removes_the_none_warning(tmp_path):
    store = make_store(tmp_path, {"none": 3, "b": 3}, per_session=10)
    report = tm.train(store=store, **out_paths(tmp_path))
    assert not any("'none' gesture" in w for w in report["warnings"])


def test_unfinished_descent_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GD_MAX_STEPS", 3)
    report = tm.train(store=make_store(tmp_path, {"a": 3, "b": 3}, per_session=10), **out_paths(tmp_path))
    assert not report["cost"]["converged"]
    assert any("before the cost reached its minimum" in w for w in report["warnings"])


def test_load_report_missing_and_corrupt(tmp_path):
    assert tm.load_report(tmp_path / "nope.json") is None
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    with pytest.raises(tm.TrainingError):
        tm.load_report(bad)


def test_cli_reports_errors_without_a_traceback(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "SAMPLES_CSV", tmp_path / "none.csv")
    monkeypatch.setattr(config, "DATASET_META", tmp_path / "none.json")
    monkeypatch.setattr(dc.DatasetStore, "__init__", lambda self, *a, **k: _empty_init(self, tmp_path))
    assert tm.main([]) == 1
    assert "Cannot train" in capsys.readouterr().err


def _empty_init(self, tmp_path):
    self.csv_path = tmp_path / "none.csv"
    self.meta_path = tmp_path / "none.json"
    self.feature_mode = "hands"
    self.feature_length = N
    self.columns = dc.META_COLUMNS + [f"f{i:03d}" for i in range(N)]
