"""Train, test and save the gesture classifier.

    python train_model.py

The model is softmax regression trained by gradient descent (see gd_model.py). What
this script does, in order:

1. Loads data/samples.csv and validates it (bad rows are dropped and counted).
2. Tests by recording. Each recording in turn is held out, a model is trained on all
   the other recordings, and that model predicts the held-out one. Every prediction
   is therefore made by a model that never saw that recording, not even a
   neighbouring frame of it.
3. Repeats step 2 for a few regularisation strengths (config.GD_L2_OPTIONS) and keeps
   the one with the lowest cost on the held-out recordings.
4. Trains the final model on every recording with that strength. Gradient descent runs
   until the gradient is practically zero, which means the cost is at its minimum.
5. Saves the model, the label mapping and a JSON report to models/.

Every number in the report is measured on your own recordings. Nothing is estimated or
invented. Training is deterministic: the same data gives the same model and report.
Saving is all-or-nothing: if training fails, the previous model and report are left
untouched.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

import config
import data_collector as dc
import features
from gd_model import GradientDescentClassifier

META = dc.META_COLUMNS
MODEL_NAME = "softmax_regression_gradient_descent"
COST_FUNCTION = "average cross-entropy (each gesture weighted equally) + l2 / 2 x sum of squared weights"


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
# 2. Testing by recording
# ---------------------------------------------------------------------------

def check_recordings(df: pd.DataFrame, min_sessions: int = config.MIN_SESSIONS_FOR_TRAINING) -> None:
    """Every gesture needs `min_sessions` recordings: one to hold out, the rest to learn from."""
    counts = df.groupby("label")["session_id"].nunique()
    short = {l: int(n) for l, n in counts.items() if n < min_sessions}
    if short:
        detail = ", ".join(f"{l} has {n}" for l, n in sorted(short.items()))
        raise TrainingError(
            f"Each gesture needs at least {min_sessions} separate recordings, so that each one "
            f"can be tested by a model that learned the gesture from another. {detail}. "
            "Record more sessions on the Data collector page or import more videos.")


def make_model(l2: float) -> GradientDescentClassifier:
    return GradientDescentClassifier(l2=l2, max_iter=config.GD_MAX_STEPS, tol=config.GD_TOLERANCE)


def _xy(df: pd.DataFrame, labels: List[str]) -> Tuple[np.ndarray, np.ndarray]:
    feat_cols = [c for c in df.columns if c not in META]
    index = {l: i for i, l in enumerate(labels)}
    return df[feat_cols].to_numpy(dtype=np.float32), df["label"].map(index).to_numpy(dtype=int)


def _proba_by_label(model, X: np.ndarray, n_labels: int) -> np.ndarray:
    """predict_proba with one column per label index, whatever classes the model saw."""
    out = np.zeros((len(X), n_labels))
    out[:, np.asarray(model.classes_, dtype=int)] = model.predict_proba(X)
    return out


def held_out_probabilities(df: pd.DataFrame, labels: List[str], l2: float,
                           make: Callable[[float], object] = make_model) -> np.ndarray:
    """Probabilities for every row, each from a model that never saw that row's recording."""
    X, y = _xy(df, labels)
    sessions = df["session_id"].to_numpy()
    proba = np.zeros((len(df), len(labels)))
    for session in sorted(set(sessions)):
        held_out = sessions == session
        if session in set(sessions[~held_out]):
            raise TrainingError(f"Internal error: recording {session} is on both sides of a test.")
        if len(set(y[~held_out])) < len(labels):
            raise TrainingError(f"Internal error: holding out {session} removes a gesture from training.")
        model = make(l2).fit(X[~held_out], y[~held_out])
        proba[held_out] = _proba_by_label(model, X[held_out], len(labels))
    return proba


def balanced_cost(proba: np.ndarray, y: np.ndarray, n_labels: int) -> float:
    """Average cross-entropy with each gesture counting equally: the data part of the
    training cost, measured on predictions for recordings the model did not see."""
    counts = np.bincount(y, minlength=n_labels)
    weights = 1.0 / (n_labels * counts[y])
    p_true = np.clip(proba[np.arange(len(y)), y], 1e-15, 1.0)
    return float(-(weights * np.log(p_true)).sum() / weights.sum())


def per_recording(df: pd.DataFrame, proba: np.ndarray, labels: List[str]) -> List[dict]:
    """Accuracy and cost of each held-out recording, worst first."""
    _, y = _xy(df, labels)
    pred = proba.argmax(axis=1)
    rows = []
    for session, part in df.groupby("session_id", sort=True):
        idx = part.index.to_numpy()
        p_true = np.clip(proba[idx, y[idx]], 1e-15, 1.0)
        rows.append({"session_id": str(session), "label": str(part["label"].iloc[0]),
                     "samples": int(len(idx)),
                     "accuracy": round(float((pred[idx] == y[idx]).mean()), 4),
                     "cost": round(float(-np.log(p_true).mean()), 4)})
    rows.sort(key=lambda r: (r["accuracy"], -r["cost"], r["session_id"]))
    return rows


# ---------------------------------------------------------------------------
# 3. Evaluation maths
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


def evaluate_proba(proba: np.ndarray, y: np.ndarray, labels: List[str]) -> dict:
    """Accuracy, per-class precision/recall/F1, confusion matrix, cost and confidence cutoffs.
    `proba` has one column per label index."""
    from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

    idx = list(range(len(labels)))
    proba = np.asarray(proba, dtype=float)
    pred = proba.argmax(axis=1)
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
        "cost": round(balanced_cost(proba, y, len(labels)), 4),
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


def evaluate(model, X: np.ndarray, y: np.ndarray, labels: List[str]) -> dict:
    """`evaluate_proba` for a fitted model whose classes are label indices."""
    return evaluate_proba(_proba_by_label(model, X, len(labels)), y, labels)


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
    per_class = report["dataset"]["per_class"]
    few = sorted(l for l, d in per_class.items() if d["sessions"] < config.MIN_SESSIONS_PER_CLASS)
    if few:
        warns.append(
            f"Fewer than {config.MIN_SESSIONS_PER_CLASS} recordings for: {', '.join(few)}. When one of "
            "them is held out, the model learns that gesture from the remaining recording alone, so "
            "the held-out scores are a rough guide. Record more sessions.")
    small = [l for l, d in per_class.items() if d["samples"] < 30]
    if small:
        warns.append(f"Very few samples for: {', '.join(sorted(small))}. Scores for these are unreliable.")
    counts = [d["samples"] for d in per_class.values()]
    if counts and max(counts) > 3 * max(1, min(counts)):
        warns.append("The gestures have very unequal numbers of samples. Collect more for the smallest ones.")
    if test["accuracy"] >= 0.999:
        warns.append(
            "Perfect held-out accuracy on a few recordings usually means the conditions in them were "
            "similar, not that the model is perfect. Test it live in new lighting and with other people.")
    gap = report["train_accuracy"] - test["accuracy"]
    if gap > 0.15:
        warns.append(
            f"The model scores {report['train_accuracy']:.0%} on the recordings it learned from but "
            f"{test['accuracy']:.0%} on held-out ones. It is memorising conditions; record more varied sessions.")
    if report["dataset"].get("people") == 1:
        warns.append("All named recordings come from one person. Recognition for other people may be worse.")
    cost = report["cost"]
    if not cost["converged"]:
        warns.append(
            f"Gradient descent stopped after {cost['steps']} steps, before the cost reached its minimum "
            f"(slope {cost['slope_at_end']:.1e}). Raise GD_MAX_STEPS in config.py and train again.")
    if config.NONE_LABEL not in report["labels"]:
        warns.append(
            f"There is no '{config.NONE_LABEL}' gesture. The model always picks the closest of your "
            "gestures, so a hand doing something else can still be shown as one of them. Record "
            f"relaxed hands and random movements as a gesture named {config.NONE_LABEL}.")
    if len(cost["l2_options"]) > 1:
        warns.append(
            f"The regularisation strength was chosen from {len(cost['l2_options'])} options by the lowest "
            "cost on these same held-out recordings, so the held-out scores are slightly optimistic.")
    return warns


# ---------------------------------------------------------------------------
# 4. Saving and loading
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


def staleness(report: dict, dataset_rows: Optional[int],
              feature_mode: str = config.FEATURE_MODE) -> List[str]:
    """Reasons the saved model is out of date. An empty list means it is current.

    `dataset_rows` is the number of rows in data/samples.csv now (None if it cannot be
    read). The check compares row counts, so adding one recording and deleting another
    of exactly the same length is not detected.
    """
    reasons = []
    if dataset_rows is not None and dataset_rows != report["dataset"]["rows_loaded"]:
        reasons.append(
            f"The dataset has changed since this model was trained ({report['dataset']['rows_loaded']} "
            f"samples then, {dataset_rows} now). Train again to include the changes.")
    if report.get("feature_mode") != feature_mode:
        reasons.append(
            f"This model used '{report.get('feature_mode')}' features but the app is set to "
            f"'{feature_mode}'. Train again before using it.")
    return reasons


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

def train(store: Optional[dc.DatasetStore] = None,
          min_sessions: int = config.MIN_SESSIONS_FOR_TRAINING,
          l2_options: Sequence[float] = config.GD_L2_OPTIONS,
          model_path: Path = None, labels_path: Path = None, report_path: Path = None,
          log: Callable[[str], None] = lambda _msg: None) -> dict:
    """Run the whole pipeline and return the report. Raises TrainingError on any problem."""
    import sklearn

    model_path = Path(model_path or config.MODEL_PATH)
    labels_path = Path(labels_path or config.LABELS_PATH)
    report_path = Path(report_path or config.REPORT_PATH)
    store = store or dc.DatasetStore()
    if not l2_options or min(l2_options) <= 0:
        raise TrainingError("GD_L2_OPTIONS must list at least one value above 0.")

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
    check_recordings(df, min_sessions)
    df = df.reset_index(drop=True)
    X, y = _xy(df, labels)
    recordings = int(df["session_id"].nunique())

    log(f"Testing by recording: {recordings} recordings, each held out once.")
    options, held_out = [], {}
    for l2 in sorted(set(l2_options), reverse=True):        # ties go to the smoother model
        proba = held_out_probabilities(df, labels, l2)
        held_out[l2] = proba
        cost = balanced_cost(proba, y, len(labels))
        accuracy = float((proba.argmax(axis=1) == y).mean())
        options.append({"l2": l2, "held_out_cost": round(cost, 4), "held_out_accuracy": round(accuracy, 4)})
        log(f"  l2 {l2:g}: held-out cost {cost:.4f}, held-out accuracy {accuracy:.1%}")
    best = min(options, key=lambda o: o["held_out_cost"])["l2"]
    log(f"Lowest held-out cost with l2 {best:g}. Training the final model on all {recordings} recordings...")

    model = make_model(best).fit(X, y)
    log(f"  gradient descent: {model.n_iter_} steps, cost {model.cost_:.5f}, gradient size {model.grad_norm_:.1e}"
        + ("" if model.converged_ else " (stopped before the minimum)"))

    report = {
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "sklearn_version": sklearn.__version__,
        "feature_mode": store.feature_mode,
        "feature_length": store.feature_length,
        "model_name": MODEL_NAME,
        "labels": labels,
        "dataset": {
            "rows_loaded": int(len(raw)),
            "rows_used": int(len(df)),
            "dropped": dropped,
            # named recorders only; 0 means nobody typed a name, so the number is unknown
            "people": int(df["person"].fillna("").replace("", np.nan).nunique()),
            "per_class": _describe(df)["per_class"],
        },
        "evaluation": {
            "method": "leave_one_recording_out",
            "recordings": recordings,
            "per_recording": per_recording(df, held_out[best], labels),
        },
        "cost": {
            "function": COST_FUNCTION,
            "l2": best,
            "l2_options": options,
            "held_out_cost": next(o["held_out_cost"] for o in options if o["l2"] == best),
            "training_cost": round(model.cost_, 6),
            "slope_at_end": model.grad_norm_,
            "tolerance": config.GD_TOLERANCE,
            "steps": model.n_iter_,
            "converged": model.converged_,
            "history": model.cost_history_,
        },
        "train_accuracy": evaluate(model, X, y, labels)["accuracy"],
        "test": evaluate_proba(held_out[best], y, labels),
    }
    report["warnings"] = make_warnings(report)

    save_artifacts(model, labels, report, model_path, labels_path, report_path)
    log(f"Saved {model_path.name}, {labels_path.name} and {report_path.name} to {model_path.parent}.")
    return report


def format_report(report: dict) -> str:
    """Console summary of a training report."""
    t, c = report["test"], report["cost"]
    lines = [
        "", "Training report", "=" * 15,
        f"Trained {report['trained_at']}: softmax regression by gradient descent on "
        f"{report['dataset']['rows_used']} samples of {len(report['labels'])} gestures "
        f"({report['feature_mode']} features).",
        "",
        f"Cost function: {c['function']}.",
        "  l2        held-out cost   held-out accuracy",
    ]
    for o in c["l2_options"]:
        chosen = "   <- lowest cost, used" if o["l2"] == c["l2"] else ""
        lines.append(f"  {o['l2']:<10g}{o['held_out_cost']:>13.4f}{o['held_out_accuracy']:>20.1%}{chosen}")
    lines += [
        f"Final model: gradient descent took {c['steps']} steps from cost {c['history'][0][1]:.4f} "
        f"to {c['training_cost']:.5f}. Gradient size at the end {c['slope_at_end']:.1e} "
        + ("(below the tolerance, so this is the minimum)." if c["converged"]
           else "(stopped before the minimum)."),
        "",
        f"Held-out recordings (each of the {report['evaluation']['recordings']} recordings predicted by a "
        "model that never saw it):",
        f"  samples {t['samples']}   accuracy {t['accuracy']:.1%}   cost {t['cost']:.4f}   macro F1 {t['macro_f1']:.3f}   "
        f"macro precision {t['macro_precision']:.3f}   macro recall {t['macro_recall']:.3f}",
        f"  accuracy on the recordings it learned from {report['train_accuracy']:.1%}",
        "", f"  {'gesture':<20}{'precision':>10}{'recall':>9}{'F1':>8}{'samples':>9}",
    ]
    for label, m in t["per_class"].items():
        lines.append(f"  {label:<20}{m['precision']:>10.3f}{m['recall']:>9.3f}{m['f1']:>8.3f}{m['support']:>9}")
    lines += ["", f"  {'recording':<14}{'gesture':<20}{'samples':>8}{'correct':>9}{'cost':>8}"]
    for r in report["evaluation"]["per_recording"]:
        lines.append(f"  {r['session_id']:<14}{r['label']:<20}{r['samples']:>8}{r['accuracy']:>9.0%}{r['cost']:>8.3f}")
    lines += ["", "Confusion matrix (rows are the true gesture, columns the prediction):"]
    width = max(len(l) for l in t["labels"]) + 2
    lines.append(" " * width + "".join(f"{l:>{width}}" for l in t["labels"]))
    for label, row in zip(t["labels"], t["confusion_matrix"]):
        lines.append(f"{label:<{width}}" + "".join(f"{v:>{width}}" for v in row))
    if t["top_confusions"]:
        lines += ["", "Gestures the model mixes up:"]
        for m in t["top_confusions"]:
            lines.append(f"  {m['true']} predicted as {m['predicted']}: {m['count']} times ({m['share_of_true']:.0%} of {m['true']})")
    else:
        lines += ["", "No mistakes on the held-out recordings."]
    lines += ["", "Confidence cutoffs on the held-out recordings:"]
    for th in t["thresholds"]:
        acc = "n/a" if th["accuracy"] is None else f"{th['accuracy']:.1%}"
        lines.append(f"  at {th['threshold']:.0%}: {th['coverage']:.0%} of predictions accepted, {acc} of those correct")
    if report["warnings"]:
        lines += ["", "Cautions:"] + [f"  - {w}" for w in report["warnings"]]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--min-sessions", type=int, default=config.MIN_SESSIONS_FOR_TRAINING,
                        help="recordings required per gesture (at least 2)")
    args = parser.parse_args(argv)
    if args.min_sessions < 2:
        print("\nCannot train: --min-sessions must be at least 2.", file=sys.stderr)
        return 1
    try:
        report = train(min_sessions=args.min_sessions, log=print)
    except TrainingError as exc:
        print(f"\nCannot train: {exc}", file=sys.stderr)
        return 1
    print(format_report(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
