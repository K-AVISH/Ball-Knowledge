"""Model performance page: train the classifier and inspect how well it did.

Every number comes from training_report.json, which train_model.py writes after
testing each recording with a model that never saw it. Nothing is estimated here.
"""
from __future__ import annotations

import streamlit as st

import config
import data_collector as dc
import dataset_manager as dm
import train_model as tm
import ui
from ui import confusion_table, esc, html_table, tag, tile

ui.page_header(
    "Model performance",
    "Results from the last training run, measured on recordings the model did not see while "
    "it was learning.",
)


def notify(kind: str, text: str) -> None:
    st.session_state.perf_msg = (kind, text)


msg = st.session_state.pop("perf_msg", None)
if msg:
    {"ok": st.success, "warn": st.warning, "bad": st.error}[msg[0]](msg[1])

try:
    report = tm.load_report()
except tm.TrainingError as exc:
    st.error(str(exc))
    report = None

try:
    _store = dc.DatasetStore()
    dataset_rows, recorded = _store.row_count(), _store.session_times()
except dc.DatasetError:
    dataset_rows, recorded = None, {}


try:
    _memes = dm.MemeLibrary().load()
except dm.MemeError:
    _memes = {}


def name(label: str) -> str:
    """The gesture's name as the dashboard shows it (set on the Memes page)."""
    return dm.display_name(label, _memes)


def recording_name(session_id: str) -> str:
    """'13 Oct 09:55 (191fce)': when the recording started, plus the start of its id.
    A recording deleted since training shows its id only."""
    when = recorded.get(session_id)
    if not when:
        return session_id
    try:
        from datetime import datetime
        stamp = datetime.fromisoformat(when).strftime("%d %b %H:%M")
    except ValueError:
        stamp = when
    return f"{stamp} ({session_id[:6]})"

# ------------------------------------------------------------------ training control
with st.container(border=True):
    ui.card_title("Train")
    st.markdown(
        '<p class="hint" style="margin-top:0">Trains softmax regression on every recording in '
        "data/samples.csv, step by step downhill on its cost. Each gesture needs at least "
        f"{config.MIN_SESSIONS_FOR_TRAINING} separate recordings; {config.MIN_SESSIONS_PER_CLASS} or more "
        "give steadier numbers. A successful run replaces the current model. A failed run leaves it "
        "unchanged. The same thing runs from the terminal with <code>python train_model.py</code>.</p>",
        unsafe_allow_html=True,
    )
    if st.button("Train model", type="primary"):
        with st.spinner("Training. This usually takes a few seconds."):
            try:
                result = tm.train()
                notify("ok", f"Trained in {result['cost']['steps']} steps. Held-out "
                             f"accuracy {result['test']['accuracy']:.1%} on {result['test']['samples']} samples "
                             f"from {result['evaluation']['recordings']} recordings. "
                             "The Live dashboard uses the new model the next time it loads.")
            except tm.TrainingError as exc:
                notify("bad", str(exc))
        st.rerun()

if report is not None and "cost" not in report:
    st.warning("This report comes from an older version of the trainer. Press Train model to "
               "replace it.")
    report = None

if report is None:
    st.markdown(
        '<div class="empty"><b>No trained model yet</b>Record at least two gestures on the Data '
        "collector page, then press Train model.</div>",
        unsafe_allow_html=True,
    )
    st.stop()

test = report["test"]
labels = test["labels"]
cost = report["cost"]

# ------------------------------------------------------------------ status
for text in tm.staleness(report, dataset_rows):
    st.warning(text)

st.markdown(
    tag(f"Trained {esc(report['trained_at'].replace('T', ' '))}", "off")
    + tag(esc(report["model_name"].replace("_", " ")), "off")
    + tag(f"{esc(report['feature_mode'])} features", "off"),
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="tiles four">'
    + tile("Held-out accuracy", f"{test['accuracy']:.1%}")
    + tile("Held-out cost", f"{test['cost']:.4f}")
    + tile("Macro F1", f"{test['macro_f1']:.3f}")
    + tile("Recordings tested", str(report["evaluation"]["recordings"]))
    + "</div>",
    unsafe_allow_html=True,
)

for text in report["warnings"]:
    st.warning(text)

left, right = st.columns([3, 2], gap="large")

with left:
    with st.container(border=True):
        ui.card_title("Per gesture (held-out recordings)")
        st.markdown(html_table(
            ["Gesture", "Precision", "Recall", "F1", "Samples"],
            [[name(l), f"{m['precision']:.3f}", f"{m['recall']:.3f}", f"{m['f1']:.3f}", m["support"]]
             for l, m in test["per_class"].items()],
            caption="Precision, recall and F1 for each gesture, from recordings the model did not learn from."),
            unsafe_allow_html=True)

    with st.container(border=True):
        ui.card_title("Confusion matrix (held-out recordings)")
        st.markdown(confusion_table([name(l) for l in labels], test["confusion_matrix"]),
                    unsafe_allow_html=True)

with right:
    with st.container(border=True):
        ui.card_title("Gestures it mixes up")
        if test["top_confusions"]:
            st.markdown(html_table(
                ["True gesture", "Predicted as", "Times"],
                [[name(c["true"]), name(c["predicted"]), f"{c['count']} ({c['share_of_true']:.0%})"]
                 for c in test["top_confusions"]], numeric_from=2,
                caption="The most frequent wrong predictions on held-out recordings."), unsafe_allow_html=True)
        else:
            st.markdown('<p class="hint">No mistakes on the held-out recordings.</p>', unsafe_allow_html=True)

    with st.container(border=True):
        ui.card_title("Confidence cutoff")
        st.markdown(html_table(
            ["Cutoff", "Accepted", "Correct", "In use"],
            [[f"{t['threshold']:.0%}", f"{t['coverage']:.0%}",
              "n/a" if t["accuracy"] is None else f"{t['accuracy']:.1%}",
              "Yes" if abs(t["threshold"] - config.DEFAULT_CONFIDENCE_THRESHOLD) < 1e-9 else ""]
             for t in test["thresholds"]],
            caption="Share of held-out predictions kept at each confidence cutoff, and how many of those were right."),
            unsafe_allow_html=True)
        st.markdown('<p class="hint">Predictions below the cutoff are rejected as uncertain. '
                    "Accepted is the share of held-out predictions kept. Correct is how many of those were right. "
                    "Confidence is the model's own estimate, not a calibrated probability, so this table "
                    "is the evidence for choosing a cutoff. The live dashboard uses "
                    f"{config.DEFAULT_CONFIDENCE_THRESHOLD:.0%}, set by DEFAULT_CONFIDENCE_THRESHOLD in "
                    "config.py.</p>",
                    unsafe_allow_html=True)

    with st.container(border=True):
        ui.card_title("Each recording, held out")
        st.markdown(html_table(
            ["Recording", "Gesture", "Samples", "Correct", "Cost"],
            [[recording_name(r["session_id"]), name(r["label"]), r["samples"], f"{r['accuracy']:.0%}",
              f"{r['cost']:.3f}"]
             for r in report["evaluation"]["per_recording"]], numeric_from=2,
            caption="Each recording, named by when it started, predicted by a model trained on all "
                    "the others, worst first."),
            unsafe_allow_html=True)
        st.markdown('<p class="hint">Every recording is held out once. No frame of a recording is '
                    "ever used to train the model that tests it.</p>", unsafe_allow_html=True)

with st.container(border=True):
    ui.card_title("Cost function")
    st.markdown(
        '<p class="hint" style="margin-top:0">Training minimises one cost: the average cross-entropy, '
        "which is large when the model gives the true gesture a low probability, plus a penalty of "
        "l2 / 2 times the sum of the squared weights. Each gesture counts equally. The cost is convex, "
        "so it has a single lowest point. Each training step moves the weights downhill, in the "
        "direction that lowers the cost fastest, and training stops when the slope is practically "
        "zero. The l2 penalty is what makes a lowest point exist when gestures can be told apart "
        "perfectly.</p>",
        unsafe_allow_html=True)
    first_cost = cost["history"][0][1]
    st.markdown(html_table(
        ["Final model", "Value"],
        [["Cost at the start (all weights zero)", f"{first_cost:.4f}"],
         ["Cost at the end", f"{cost['training_cost']:.5f}"],
         ["Training steps", str(cost["steps"])],
         ["Slope at the end", f"{cost['slope_at_end']:.1e}"],
         ["Reached the minimum", "Yes" if cost["converged"]
          else f"No, stopped at {cost['steps']} steps"]],
        caption="The final model, trained on all recordings with the chosen penalty."), unsafe_allow_html=True)
    st.markdown(html_table(
        ["Penalty l2", "Held-out cost", "Held-out accuracy", "Used"],
        [[f"{o['l2']:g}", f"{o['held_out_cost']:.4f}", f"{o['held_out_accuracy']:.1%}",
          "Yes" if o["l2"] == cost["l2"] else ""] for o in cost["l2_options"]],
        caption="Each penalty tested on held-out recordings. The lowest held-out cost is used."),
        unsafe_allow_html=True)
    st.markdown('<p class="hint">A larger penalty gives a smoother, less confident model. The cost on '
                "held-out recordings decides, because a low cost on the training recordings alone "
                "can mean the model has memorised them.</p>", unsafe_allow_html=True)
    dropped = report["dataset"]["dropped"]
    if dropped:
        st.markdown('<p class="hint">Rows dropped as invalid: '
                    + esc(", ".join(f"{n} ({r})" for r, n in dropped.items())) + ".</p>",
                    unsafe_allow_html=True)
