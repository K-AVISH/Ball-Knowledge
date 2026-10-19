"""Stage 4 tests for train_model.py.

All data here is synthetic, so these tests check the CODE (validation, leak-free
splitting, evaluation maths, saving). They say nothing about how accurate a model
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


# --- splitting --------------------------------------------------------------

def test_split_never_shares_a_recording_and_covers_every_gesture(tmp_path):
    df = make_store(tmp_path, {"a": 6, "b": 5, "c": 3}, per_session=10).load()
    train, val, test = tm.split_by_session(df, seed=1)
    ids = [set(x["session_id"]) for x in (train, val, test)]
    assert not (ids[0] & ids[1]) and not (ids[0] & ids[2]) and not (ids[1] & ids[2])
    assert len(train) + len(val) + len(test) == len(df)
    for part in (train, val, test):
        assert set(part["label"]) == {"a", "b", "c"}


def test_split_is_repeatable_and_seed_dependent(tmp_path):
    df = make_store(tmp_path, {"a": 8, "b": 8}, per_session=5).load()
    a1 = [set(x["session_id"]) for x in tm.split_by_session(df, seed=3)]
    a2 = [set(x["session_id"]) for x in tm.split_by_session(df, seed=3)]
    b = [set(x["session_id"]) for x in tm.split_by_session(df, seed=4)]
    assert a1 == a2
    assert a1 != b


def test_three_recordings_split_one_one_one(tmp_path):
    df = make_store(tmp_path, {"a": 3, "b": 3}, per_session=5).load()
    train, val, test = tm.split_by_session(df)
    for part in (train, val, test):
        assert part.groupby("label")["session_id"].nunique().tolist() == [1, 1]


def test_too_few_recordings_names_the_gestures(tmp_path):
    df = make_store(tmp_path, {"a": 3, "b": 2, "c": 1}, per_session=5).load()
    with pytest.raises(tm.TrainingError) as err:
        tm.split_by_session(df)
    assert "b has 2" in str(err.value) and "c has 1" in str(err.value) and "a has" not in str(err.value)


def test_leak_check_catches_a_shared_recording(tmp_path):
    df = make_store(tmp_path, {"a": 3, "b": 3}, per_session=4).load()
    with pytest.raises(tm.TrainingError, match="both"):
        tm.assert_no_leakage(df, df.iloc[:3], df.iloc[3:6])


def test_session_split_stops_a_model_cheating_on_recording_identity(tmp_path):
    """Features identify the RECORDING, labels are random per recording, so there is nothing
    real to learn. A leak-free split must score near chance. A naive frame-level split on the
    same data scores high, which is exactly the leak this project avoids."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split

    rng = np.random.default_rng(0)
    rows = []
    n_sessions = 30
    for s in range(n_sessions):
        offset = rng.normal(size=N) * 5.0
        label = ["a", "b", "c"][s % 3] if s < 3 else rng.choice(["a", "b", "c"])
        for _ in range(30):
            rows.append([f"s{s}", label, "x", "t", *(offset + rng.normal(size=N) * 0.1)])
    df = pd.DataFrame(rows, columns=dc.META_COLUMNS + [f"f{i:03d}" for i in range(N)])

    train, val, test = tm.split_by_session(df, seed=0)
    X_tr, y_tr = tm._xy(train, ["a", "b", "c"])
    X_te, y_te = tm._xy(test, ["a", "b", "c"])
    honest = RandomForestClassifier(100, random_state=0).fit(X_tr, y_tr).score(X_te, y_te)

    X, y = tm._xy(df, ["a", "b", "c"])
    Xa, Xb, ya, yb = train_test_split(X, y, test_size=0.3, random_state=0)
    leaky = RandomForestClassifier(100, random_state=0).fit(Xa, ya).score(Xb, yb)

    assert leaky > 0.9
    assert honest < 0.7


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

    store = make_store(tmp_path, {"fist": 4, "four_gesture": 4, "peace": 4}, per_session=30)
    paths = out_paths(tmp_path)
    report = tm.train(store=store, seed=5, **paths)

    assert report["labels"] == ["fist", "four_gesture", "peace"]
    assert report["test"]["accuracy"] > 0.9               # well-separated synthetic classes
    assert report["selected"] in {c["name"] for c in report["candidates"]}
    assert sum(sum(r) for r in report["test"]["confusion_matrix"]) == report["test"]["samples"]
    assert sum(m["support"] for m in report["test"]["per_class"].values()) == report["test"]["samples"]
    total = sum(report["split"][k]["samples"] for k in ("train", "val", "test"))
    assert total == report["dataset"]["rows_used"] == 360

    model = joblib.load(paths["model_path"])
    mapping = json.loads(paths["labels_path"].read_text())
    assert mapping == {"0": "fist", "1": "four_gesture", "2": "peace"}
    X = store.load()[store.columns[4:]].to_numpy(dtype=np.float32)[:5]
    assert model.predict_proba(X).shape == (5, 3)
    assert json.loads(paths["report_path"].read_text())["test"]["accuracy"] == report["test"]["accuracy"]
    assert tm.load_report(paths["report_path"])["model_name"] == report["model_name"]
    assert "Training report" in tm.format_report(report)


def test_training_is_repeatable(tmp_path):
    store = make_store(tmp_path, {"a": 4, "b": 4}, per_session=20)
    r1 = tm.train(store=store, seed=9, **out_paths(tmp_path))
    r2 = tm.train(store=store, seed=9, **out_paths(tmp_path))
    assert r1["test"] == r2["test"] and r1["split"] == r2["split"]


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
    store = make_store(tmp_path, {"a": 3, "b": 3}, per_session=10)
    report = tm.train(store=store, **out_paths(tmp_path))
    text = " ".join(report["warnings"])
    assert "only one recording" in text                  # one test recording per gesture
    assert "Perfect test accuracy" in text               # separable synthetic data scores 100%
    assert "Very few test samples" in text               # 10 test samples per gesture


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
