"""Train, validate, evaluate and save the gesture classifier.

    python train_model.py              # train on data/samples.csv
    python train_model.py --seed 7     # a different (still repeatable) split

What it does, in order:

1. Loads data/samples.csv and validates it (bad rows are dropped and counted).
2. Splits by whole recording session into train, validation and test sets, so
   frames from one recording never appear on both sides of a split.
3. Trains a few baseline classifiers on the training set and picks one by its
   validation score. The test set plays no part in that choice.
4. Evaluates the chosen model once on the test set: accuracy, precision,
   recall, F1, a confusion matrix and the gestures it mixes up.
5. Saves the model, the label mapping and a JSON report to models/.

Every number in the report is measured on your own recordings. Nothing is
estimated or invented. Saving is all-or-nothing: if training fails, the previous
model and report are left untouched.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import config
import data_collector as dc
import features

META = dc.META_COLUMNS


class TrainingError(RuntimeError):
    """Training cannot proceed. The message says what to fix."""


# ---------------------------------------------------------------------------
# 1. Validation
# ---------------------------------------------------------------------------

def validate_dataset(df: pd.DataFrame, feature_length: int) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Drop malformed rows. Returns (clean frame, {reason: rows dropped})."""
    feat_cols = [c for c in df.columns if c not in META]
    if len(feat_cols) != feature_length:
        raise TrainingError(
            f"The dataset has {len(feat_cols)} feature columns but {feature_length} are expected."
        )
    work = df.copy()
    dropped: Dict[str, int] = {}

    def drop(mask: pd.Series, reason: str) -> None:
        nonlocal work
        n = int(mask.sum())
        if n:
            dropped[reason] = dropped.get(reason, 0) + n
            work = work[~mask]

    for col in ("label", "session_id"):
        work[col] = work[col].astype("string").str.strip()
    drop(work["label"].isna() | (work["label"] == ""), "missing gesture label")
    drop(work["session_id"].isna() | (work["session_id"] == ""), "missing recording id")

    numeric = work[feat_cols].apply(pd.to_numeric, errors="coerce")
    values = numeric.to_numpy(dtype=np.float64)
    drop(pd.Series(~np.isfinite(values).all(axis=1), index=work.index),
         "non-numeric, missing or infinite feature values")
    work[feat_cols] = numeric.loc[work.index]
    values = work[feat_cols].to_numpy(dtype=np.float64)
    drop(pd.Series(~values.any(axis=1), index=work.index), "all-zero feature vector")

    # A recording belongs to exactly one gesture. A reused id means the file is corrupted.
    labels_per_session = work.groupby("session_id")["label"].nunique()
    clashing = labels_per_session[labels_per_session > 1].index
    drop(work["session_id"].isin(clashing), "recording id used by more than one gesture")

    work = work.copy()
    work[feat_cols] = work[feat_cols].astype(np.float32)
    work["label"] = work["label"].astype(str)
    work["session_id"] = work["session_id"].astype(str)
    return work, dropped


# ---------------------------------------------------------------------------
# 2. Splitting by session
# ---------------------------------------------------------------------------

def split_by_session(df: pd.DataFrame, seed: int = config.TRAIN_SEED,
                     min_sessions: int = config.MIN_SESSIONS_FOR_TRAINING
                     ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (train, validation, test) with disjoint recording sessions.

    Each gesture's sessions are shuffled (repeatably) and divided, so every
    gesture appears in all three sets. A gesture needs at least `min_sessions`
    recordings, otherwise no leak-free split is possible.
    """
    sessions_by_label = {
        label: sorted(part["session_id"].unique()) for label, part in df.groupby("label")
    }
    short = {l: len(s) for l, s in sessions_by_label.items() if len(s) < min_sessions}
    if short:
        detail = ", ".join(f"{l} has {n}" for l, n in sorted(short.items()))
        raise TrainingError(
            f"Each gesture needs at least {min_sessions} separate recordings so that some can be "
            f"held out for testing without leaking frames from the same recording. {detail}. "
            "Record more sessions on the Data collector page."
        )

    rng = np.random.default_rng(seed)
    assigned: Dict[str, str] = {}
    for label in sorted(sessions_by_label):
        sessions = sessions_by_label[label]
        order = [sessions[i] for i in rng.permutation(len(sessions))]
        n = len(order)
        n_test = max(1, round(n * config.TEST_SESSION_FRACTION))
        n_val = max(1, round(n * config.VAL_SESSION_FRACTION))
        if n - n_test - n_val < 1:
            raise TrainingError(f"Not enough recordings of {label} to split.")
        for s in order[:n_test]:
            assigned[s] = "test"
        for s in order[n_test:n_test + n_val]:
            assigned[s] = "val"
        for s in order[n_test + n_val:]:
            assigned[s] = "train"

    part = df["session_id"].map(assigned)
    train, val, test = (df[part == k].reset_index(drop=True) for k in ("train", "val", "test"))
    assert_no_leakage(train, val, test)
    return train, val, test


def assert_no_leakage(train: pd.DataFrame, val: pd.DataFrame, test: pd.DataFrame) -> None:
    sets = {k: set(v["session_id"]) for k, v in (("train", train), ("val", val), ("test", test))}
    for a, b in (("train", "val"), ("train", "test"), ("val", "test")):
        shared = sets[a] & sets[b]
        if shared:
            raise TrainingError(f"Internal error: recordings {sorted(shared)[:3]} are in both {a} and {b}.")


# ---------------------------------------------------------------------------
# 3. Models
# ---------------------------------------------------------------------------

def make_candidates(seed: int) -> Dict[str, Callable[[], object]]:
    """Baseline classifiers to compare on the validation set. Order is the tie-break."""
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC

    return {
        "random_forest": lambda: RandomForestClassifier(
            n_estimators=300, class_weight="balanced", n_jobs=-1, random_state=seed),
        "random_forest_smooth": lambda: RandomForestClassifier(
            n_estimators=300, min_samples_leaf=3, class_weight="balanced", n_jobs=-1,
            random_state=seed),
        # SVC has no probabilities of its own; calibration adds them (needed for confidence scores)
        "svm_rbf": lambda: make_pipeline(
            StandardScaler(),
            CalibratedClassifierCV(
                SVC(kernel="rbf", C=10, gamma="scale", class_weight="balanced"),
                method="sigmoid", cv=3, ensemble=False)),
    }


def _xy(df: pd.DataFrame, labels: List[str]) -> Tuple[np.ndarray, np.ndarray]:
    feat_cols = [c for c in df.columns if c not in META]
    index = {l: i for i, l in enumerate(labels)}
    return df[feat_cols].to_numpy(dtype=np.float32), df["label"].map(index).to_numpy(dtype=int)


# ---------------------------------------------------------------------------
# 4. Evaluation
# ---------------------------------------------------------------------------

def top_confusions(cm: np.ndarray, labels: List[str], limit: int = 5) -> List[dict]:
    """The most frequent wrong predictions, from a confusion matrix (rows = true)."""
    out = []
    for i in range(len(labels)):
        row_total = int(cm[i].sum())
        for j in range(len(labels)):
            if i != j and cm[i, j] > 0:
                out.append({"true": labels[i], "predicted": labels[j], "count": int(cm[i, j]),
                            "share_of_true": round(float(cm[i, j]) / row_total, 4)})
    out.sort(key=lambda d: (-d["count"], d["true"], d["predicted"]))
    return out[:limit]


def evaluate(model, X: np.ndarray, y: np.ndarray, labels: List[str]) -> dict:
    """Accuracy, per-class precision/recall/F1, confusion matrix and confidence cutoffs."""
    from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

    idx = list(range(len(labels)))
    proba = model.predict_proba(X)
    pred = np.asarray(model.classes_)[proba.argmax(axis=1)]
    conf = proba.max(axis=1)

    prec, rec, f1, support = precision_recall_fscore_support(
        y, pred, labels=idx, zero_division=0)
    macro = precision_recall_fscore_support(y, pred, labels=idx, average="macro", zero_division=0)
    weighted = precision_recall_fscore_support(y, pred, labels=idx, average="weighted", zero_division=0)
    cm = confusion_matrix(y, pred, labels=idx)

    correct = pred == y
    thresholds = []
    for t in config.CONFIDENCE_THRESHOLDS:
        accepted = conf >= t
        thresholds.append({
            "threshold": t,
            "coverage": round(float(accepted.mean()), 4),
            "accuracy": round(float(correct[accepted].mean()), 4) if accepted.any() else None,
        })

    return {
        "samples": int(len(y)),
        "accuracy": round(float(accuracy_score(y, pred)), 4),
        "macro_precision": round(float(macro[0]), 4),
        "macro_recall": round(float(macro[1]), 4),
        "macro_f1": round(float(macro[2]), 4),
        "weighted_f1": round(float(weighted[2]), 4),
        "per_class": {
            labels[i]: {"precision": round(float(prec[i]), 4), "recall": round(float(rec[i]), 4),
                        "f1": round(float(f1[i]), 4), "support": int(support[i])}
            for i in idx
        },
        "labels": labels,
        "confusion_matrix": cm.tolist(),
        "top_confusions": top_confusions(cm, labels),
        "mean_confidence_correct": round(float(conf[correct].mean()), 4) if correct.any() else None,
        "mean_confidence_wrong": round(float(conf[~correct].mean()), 4) if (~correct).any() else None,
        "thresholds": thresholds,
    }


def _describe(df: pd.DataFrame) -> dict:
    return {
        "samples": int(len(df)),
        "sessions": int(df["session_id"].nunique()),
        "per_class": {l: {"samples": int(len(p)), "sessions": int(p["session_id"].nunique())}
                      for l, p in df.groupby("label")},
    }


def make_warnings(report: dict) -> List[str]:
    """Plain-language cautions about how far the numbers can be trusted."""
    warns = []
    test = report["test"]
    per_class = report["split"]["test"]["per_class"]
    few_sessions = [l for l, d in per_class.items() if d["sessions"] < 2]
    if few_sessions:
        warns.append(
            "Each gesture is tested on only one recording, so the test scores are a rough guide. "
            "Record more sessions per gesture to get a steadier measurement.")
    small = [l for l, d in per_class.items() if d["samples"] < 30]
    if small:
        warns.append(f"Very few test samples for: {', '.join(sorted(small))}. Scores for these are unreliable.")
    counts = [d["samples"] for d in report["dataset"]["per_class"].values()]
    if counts and max(counts) > 3 * max(1, min(counts)):
        warns.append("The gestures have very unequal numbers of samples. Collect more for the smallest ones.")
    if test["accuracy"] >= 0.999:
        warns.append(
            "Perfect test accuracy on a few recordings usually means the conditions in them were "
            "similar, not that the model is perfect. Test it live in new lighting and with other people.")
    gap = report["train_accuracy"] - test["accuracy"]
    if gap > 0.15:
        warns.append(
            f"The model scores {report['train_accuracy']:.0%} on its training data but {test['accuracy']:.0%} "
            "on unseen recordings. It is memorising conditions; record more varied sessions.")
    people = report["dataset"].get("people")
    if people == 1:
        warns.append("All named recordings come from one person. Recognition for other people may be worse.")
    return warns


# ---------------------------------------------------------------------------
# 5. Saving and loading
# ---------------------------------------------------------------------------

def save_artifacts(model, labels: List[str], report: dict, model_path: Path,
                   labels_path: Path, report_path: Path) -> None:
    """Write all three files to temporary names, then rename them together."""
    import joblib

    targets = [model_path, labels_path, report_path]
    for p in targets:
        p.parent.mkdir(parents=True, exist_ok=True)
    tmp = {p: p.with_name(p.name + ".tmp") for p in targets}
    try:
        joblib.dump(model, tmp[model_path])
        tmp[labels_path].write_text(json.dumps({str(i): l for i, l in enumerate(labels)}, indent=2))
        tmp[report_path].write_text(json.dumps(report, indent=2))
        for p in targets:
            os.replace(tmp[p], p)
    finally:
        for p in tmp.values():
            p.unlink(missing_ok=True)


def load_report(path: Path = None) -> Optional[dict]:
    """The last training report, or None if no model has been trained yet."""
    path = Path(path or config.REPORT_PATH)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise TrainingError(f"Cannot read {path.name}: {exc}") from exc


# ---------------------------------------------------------------------------
# Putting it together
# ---------------------------------------------------------------------------

def train(store: Optional[dc.DatasetStore] = None, seed: int = config.TRAIN_SEED,
          min_sessions: int = config.MIN_SESSIONS_FOR_TRAINING,
          model_path: Path = None, labels_path: Path = None, report_path: Path = None,
          log: Callable[[str], None] = lambda _msg: None) -> dict:
    """Run the whole pipeline and return the report. Raises TrainingError on any problem."""
    import sklearn

    model_path = Path(model_path or config.MODEL_PATH)
    labels_path = Path(labels_path or config.LABELS_PATH)
    report_path = Path(report_path or config.REPORT_PATH)
    store = store or dc.DatasetStore()

    log("Loading and validating samples...")
    try:
        raw = store.load()
    except dc.DatasetError as exc:
        raise TrainingError(str(exc)) from exc
    if raw.empty:
        raise TrainingError("There are no samples yet. Record some on the Data collector page first.")
    df, dropped = validate_dataset(raw, store.feature_length)
    if dropped:
        log("Dropped rows: " + ", ".join(f"{n} ({r})" for r, n in dropped.items()))
    labels = sorted(df["label"].unique())
    if len(labels) < 2:
        raise TrainingError(
            f"Only one gesture ({labels[0] if labels else 'none'}) has valid samples. "
            "Record at least 2 different gestures.")

    train_df, val_df, test_df = split_by_session(df, seed, min_sessions)
    log(f"Split by recording: {len(train_df)} train, {len(val_df)} validation, {len(test_df)} test samples.")
    X_train, y_train = _xy(train_df, labels)
    X_val, y_val = _xy(val_df, labels)
    X_test, y_test = _xy(test_df, labels)

    candidates, fitted = [], {}
    warnings: List[str] = []
    for name, factory in make_candidates(seed).items():
        try:
            model = factory()
            model.fit(X_train, y_train)
            scores = evaluate(model, X_val, y_val, labels)
        except Exception as exc:                      # e.g. too few samples for SVM probabilities
            warnings.append(f"Model {name} was skipped: {type(exc).__name__}: {exc}")
            log(f"  {name}: skipped ({exc})")
            continue
        fitted[name] = model
        candidates.append({"name": name, "val_accuracy": scores["accuracy"],
                           "val_macro_f1": scores["macro_f1"]})
        log(f"  {name}: validation accuracy {scores['accuracy']:.3f}, macro F1 {scores['macro_f1']:.3f}")
    if not fitted:
        raise TrainingError("No model could be trained on this data. " + " ".join(warnings))

    best = max(candidates, key=lambda c: (c["val_macro_f1"], c["val_accuracy"]))["name"]  # first wins ties
    model = fitted[best]
    log(f"Selected {best} using validation data. Evaluating once on the held-out test set...")

    test = evaluate(model, X_test, y_test, labels)
    train_acc = evaluate(model, X_train, y_train, labels)["accuracy"]
    validation = evaluate(model, X_val, y_val, labels)

    report = {
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "seed": seed,
        "sklearn_version": sklearn.__version__,
        "feature_mode": store.feature_mode,
        "feature_length": store.feature_length,
        "model_name": best,
        "labels": labels,
        "dataset": {
            "rows_loaded": int(len(raw)),
            "rows_used": int(len(df)),
            "dropped": dropped,
            # named recorders only; 0 means nobody typed a name, so the number is unknown
            "people": int(df["person"].fillna("").replace("", np.nan).nunique()),
            "per_class": _describe(df)["per_class"],
        },
        "split": {"train": _describe(train_df), "val": _describe(val_df), "test": _describe(test_df)},
        "candidates": candidates,
        "selected": best,
        "train_accuracy": train_acc,
        "validation": {k: validation[k] for k in ("samples", "accuracy", "macro_f1")},
        "test": test,
    }
    report["warnings"] = warnings + make_warnings(report)

    save_artifacts(model, labels, report, model_path, labels_path, report_path)
    log(f"Saved {model_path.name}, {labels_path.name} and {report_path.name} to {model_path.parent}.")
    return report


def format_report(report: dict) -> str:
    """Console summary of a training report."""
    t = report["test"]
    lines = [
        "", "Training report", "=" * 15,
        f"Trained {report['trained_at']} with {report['model_name']} on {report['dataset']['rows_used']} samples "
        f"of {len(report['labels'])} gestures ({report['feature_mode']} features).",
        "", "Held-out test set (recordings the model never saw):",
        f"  samples {t['samples']}   accuracy {t['accuracy']:.1%}   macro F1 {t['macro_f1']:.3f}   "
        f"macro precision {t['macro_precision']:.3f}   macro recall {t['macro_recall']:.3f}",
        f"  training accuracy {report['train_accuracy']:.1%}   validation accuracy {report['validation']['accuracy']:.1%}",
        "", f"  {'gesture':<20}{'precision':>10}{'recall':>9}{'F1':>8}{'support':>9}",
    ]
    for label, m in t["per_class"].items():
        lines.append(f"  {label:<20}{m['precision']:>10.3f}{m['recall']:>9.3f}{m['f1']:>8.3f}{m['support']:>9}")
    lines += ["", "Confusion matrix (rows are the true gesture, columns the prediction):"]
    width = max(len(l) for l in t["labels"]) + 2
    col = width
    lines.append(" " * width + "".join(f"{l:>{col}}" for l in t["labels"]))
    for label, row in zip(t["labels"], t["confusion_matrix"]):
        lines.append(f"{label:<{width}}" + "".join(f"{v:>{col}}" for v in row))
    if t["top_confusions"]:
        lines += ["", "Gestures the model mixes up:"]
        for c in t["top_confusions"]:
            lines.append(f"  {c['true']} predicted as {c['predicted']}: {c['count']} times ({c['share_of_true']:.0%} of {c['true']})")
    else:
        lines += ["", "No mistakes on the test set."]
    lines += ["", "Confidence cutoffs on the test set:"]
    for th in t["thresholds"]:
        acc = "n/a" if th["accuracy"] is None else f"{th['accuracy']:.1%}"
        lines.append(f"  at {th['threshold']:.0%}: {th['coverage']:.0%} of predictions accepted, {acc} of those correct")
    if report["warnings"]:
        lines += ["", "Cautions:"] + [f"  - {w}" for w in report["warnings"]]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=config.TRAIN_SEED, help="random seed for the split and models")
    parser.add_argument("--min-sessions", type=int, default=config.MIN_SESSIONS_FOR_TRAINING,
                        help="recordings required per gesture")
    args = parser.parse_args(argv)
    try:
        report = train(seed=args.seed, min_sessions=args.min_sessions, log=print)
    except TrainingError as exc:
        print(f"\nCannot train: {exc}", file=sys.stderr)
        return 1
    print(format_report(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
