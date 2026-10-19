"""Model performance page: train the classifier and inspect how well it did.

Every number comes from training_report.json, which train_model.py writes after
measuring the model on recordings it never saw. Nothing is estimated here.
"""
from __future__ import annotations

import streamlit as st

import config
import data_collector as dc
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
    dataset_rows = len(dc.DatasetStore().load())
except dc.DatasetError:
    dataset_rows = None

# ------------------------------------------------------------------ training control
with st.container(border=True):
    st.markdown('<div class="ctitle">Train</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hint" style="margin-top:0">Training uses every recording in data/samples.csv. '
        "Each gesture needs at least "
        f"{config.MIN_SESSIONS_FOR_TRAINING} separate recordings. A successful run replaces the "
        "current model. A failed run leaves it unchanged. The same thing runs from the terminal "
        "with <code>python train_model.py</code>.</p>",
        unsafe_allow_html=True,
    )
    if st.button("Train model", type="primary"):
        with st.spinner("Training. This usually takes a few seconds."):
            try:
                result = tm.train()
                notify("ok", f"Trained a {result['model_name']} model. Test accuracy "
                             f"{result['test']['accuracy']:.1%} on {result['test']['samples']} unseen samples.")
            except tm.TrainingError as exc:
                notify("bad", str(exc))
        st.rerun()

if report is None:
    st.markdown(
        '<div class="empty"><b>No trained model yet</b>Record at least two gestures on the Data '
        "collector page, then press Train model.</div>",
        unsafe_allow_html=True,
    )
    st.stop()

test = report["test"]
labels = test["labels"]

# ------------------------------------------------------------------ status
stale = []
if dataset_rows is not None and dataset_rows != report["dataset"]["rows_loaded"]:
    stale.append("The dataset has changed since this model was trained. Train again to include the changes.")
if report["feature_mode"] != config.FEATURE_MODE:
    stale.append(f"This model used '{report['feature_mode']}' features but the app is set to "
                 f"'{config.FEATURE_MODE}'. Train again before using it.")
for text in stale:
    st.warning(text)

st.markdown(
    tag(f"Trained {esc(report['trained_at'].replace('T', ' '))}", "off")
    + tag(esc(report["model_name"].replace("_", " ")), "off")
    + tag(f"{esc(report['feature_mode'])} features", "off"),
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="tiles" style="grid-template-columns:repeat(4,1fr)">'
    + tile("Test accuracy", f"{test['accuracy']:.1%}")
    + tile("Macro F1", f"{test['macro_f1']:.3f}")
    + tile("Test samples", str(test["samples"]))
    + tile("Gestures", str(len(labels)))
    + "</div>",
    unsafe_allow_html=True,
)

for text in report["warnings"]:
    st.warning(text)

left, right = st.columns([3, 2], gap="large")

with left:
    with st.container(border=True):
        st.markdown('<div class="ctitle">Per gesture (test set)</div>', unsafe_allow_html=True)
        st.markdown(html_table(
            ["Gesture", "Precision", "Recall", "F1", "Test samples"],
            [[l, f"{m['precision']:.3f}", f"{m['recall']:.3f}", f"{m['f1']:.3f}", m["support"]]
             for l, m in test["per_class"].items()]), unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="ctitle">Confusion matrix (test set)</div>', unsafe_allow_html=True)
        st.markdown(confusion_table(labels, test["confusion_matrix"]), unsafe_allow_html=True)

with right:
    with st.container(border=True):
        st.markdown('<div class="ctitle">Gestures it mixes up</div>', unsafe_allow_html=True)
        if test["top_confusions"]:
            st.markdown(html_table(
                ["True gesture", "Predicted as", "Times"],
                [[c["true"], c["predicted"], f"{c['count']} ({c['share_of_true']:.0%})"]
                 for c in test["top_confusions"]], numeric_from=2), unsafe_allow_html=True)
        else:
            st.markdown('<p class="hint">No mistakes on the test set.</p>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="ctitle">Confidence cutoff</div>', unsafe_allow_html=True)
        st.markdown(html_table(
            ["Cutoff", "Accepted", "Correct"],
            [[f"{t['threshold']:.0%}", f"{t['coverage']:.0%}",
              "n/a" if t["accuracy"] is None else f"{t['accuracy']:.1%}"] for t in test["thresholds"]]),
            unsafe_allow_html=True)
        st.markdown('<p class="hint">Predictions below the cutoff are rejected as uncertain. '
                    "Accepted is the share of test predictions kept. Correct is how many of those were right.</p>",
                    unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="ctitle">How the data was split</div>', unsafe_allow_html=True)
        split = report["split"]
        st.markdown(html_table(
            ["Set", "Recordings", "Samples"],
            [[name, split[key]["sessions"], split[key]["samples"]]
             for name, key in (("Training", "train"), ("Validation", "val"), ("Test", "test"))]),
            unsafe_allow_html=True)
        st.markdown('<p class="hint">Whole recordings are held out, so no frames from one recording '
                    "appear in two sets.</p>", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<div class="ctitle">Models compared on the validation set</div>', unsafe_allow_html=True)
    st.markdown(html_table(
        ["Model", "Validation accuracy", "Validation macro F1", "Chosen"],
        [[c["name"].replace("_", " "), f"{c['val_accuracy']:.3f}", f"{c['val_macro_f1']:.3f}",
          "Yes" if c["name"] == report["selected"] else ""] for c in report["candidates"]]),
        unsafe_allow_html=True)
    dropped = report["dataset"]["dropped"]
    if dropped:
        st.markdown('<p class="hint">Rows dropped as invalid: '
                    + esc(", ".join(f"{n} ({r})" for r, n in dropped.items())) + ".</p>",
                    unsafe_allow_html=True)
