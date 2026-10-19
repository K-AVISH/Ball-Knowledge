"""Live dashboard page: camera, landmarks, live recognition, meme result and stats.

The trained model is loaded once (ui.load_predictor) and runs on its own worker
thread (predictor.LiveRecognizer), fed by the video thread. This page only reads the
results. The recognition and meme panels show a gesture once it holds steady across
several frames; the meme comes from assets/memes/memes.json (dataset_manager.py).
Recent detections and the session count come from the recogniser's in-memory log.
"""
from __future__ import annotations

import streamlit as st

import data_collector as dc
import dataset_manager as dm
import predictor as pr
import train_model
import ui
from ui import camera_state, hand_tag, tile

CAMERA_KEY = "dashboard-camera"
# The camera status and the right-hand panels refresh together, so the hand tag under the
# video never contradicts the Recognition panel for longer than one refresh.
REFRESH_S = 0.5

processor, landmark_hook = ui.get_vision()
recognizer = ui.get_recognizer()
processor.recorder = None            # not recording on this page
_rec = st.session_state.get("recorder")
if _rec is not None:
    _rec.cancel()                    # leaving the collector page abandons any recording

model, model_problem = ui.load_predictor()
recognizer.use(model)                # a retrained model replaces the old one here
processor.recognizer = recognizer if model is not None else None

try:
    model_report = train_model.load_report()
except train_model.TrainingError:
    model_report = None
try:
    dataset_rows = dc.DatasetStore().row_count()
except dc.DatasetError:
    dataset_rows = None
stale = train_model.staleness(model_report, dataset_rows) if model_report else []

if model is not None:
    n_classes = len(model.labels)
elif model_report:
    n_classes = len(model_report["labels"])
else:
    n_classes = None

ui.page_header(
    "Live dashboard",
    "Show a gesture you have trained to the camera. The model classifies each frame and "
    "says Unrecognised when it is not confident enough, instead of guessing.",
)

for note in (model.warnings if model is not None else []):
    st.warning(note)

meme_library = dm.MemeLibrary()
if model is not None:
    try:
        without = meme_library.missing_for(model.labels)
    except dm.MemeError:
        without = []                     # the meme panel shows the reason
    if without:
        st.info("No usable meme yet for: " + ", ".join(without) + ". Add one with "
                "python dataset_manager.py <gesture> --image <file>.")

left, right = st.columns([3, 2], gap="large")

with left:
    with st.container(border=True):
        ui.card_title("Camera")
        ctx = ui.camera_widget(CAMERA_KEY, processor)

        landmark_hook.show_landmarks = st.checkbox(
            "Show landmarks overlay", value=landmark_hook.show_landmarks,
            help="Draw the detected hand skeleton on the video.",
        )

        @st.fragment(run_every=REFRESH_S)
        def camera_status() -> None:
            playing = bool(ctx.state.playing)
            stats = processor.get_stats()
            cam, hint, live = camera_state(stats, playing)
            st.markdown(f'{cam}{hand_tag(stats, live)}<p class="hint">{hint}</p>',
                        unsafe_allow_html=True)

        camera_status()

    if ctx.state.playing is False:
        processor.reset()  # clear stale stats; the browser releases the camera when it stops
        recognizer.reset()


with right:
    @st.fragment(run_every=REFRESH_S)
    def live_panels() -> None:
        """Refreshes twice per second without re-running the whole page."""
        playing = bool(ctx.state.playing)
        stats = processor.get_stats()
        _, _, live = camera_state(stats, playing)
        prediction = recognizer.latest()
        steady = recognizer.steady() if (model is not None and live and pr.is_fresh(prediction)) else None
        history, total = recognizer.history()

        st.markdown(ui.recognition_card(model_problem, prediction, playing, live, stale, steady),
                    unsafe_allow_html=True)
        try:
            memes, memes_error = meme_library.load(), None
        except dm.MemeError as exc:
            memes, memes_error = None, str(exc)
        st.markdown(ui.meme_card(steady.label if steady else None, memes, memes_error, meme_library),
                    unsafe_allow_html=True)
        model_label, _ = ui.model_state(model_problem, stale)
        latest = history[0] if history else None
        st.markdown(
            '<div class="tiles">'
            + tile("Latest gesture", ui.esc(latest.label) if latest else "n/a",
                   ui.clock(latest.at) if latest else "", wide=True)
            + tile("Recognised this session", str(total) if model is not None else "n/a")
            + tile("Gesture classes", str(n_classes) if n_classes else "n/a")
            + tile("Frames per second", f"{stats.fps:.0f}" if live else "n/a")
            + tile("Latency", f"{stats.latency_ms:.1f}" if live else "n/a", "ms" if live else "")
            + tile("Model", model_label, wide=True)
            + "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(ui.history_card(history, total, model is not None), unsafe_allow_html=True)

    live_panels()
