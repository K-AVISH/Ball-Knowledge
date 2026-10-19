"""Live dashboard page: the camera, and beside it the meme for the gesture being shown with
the confidence meter under it. Session statistics and recent detections follow below.

The trained model is loaded once (ui.load_predictor) and runs on its own worker
thread (predictor.LiveRecognizer), fed by the video thread. This page only reads the
results. A meme shows once a gesture holds steady across several frames; it comes from
assets/memes/memes.json (dataset_manager.py). Gestures are shown by their memes, never
by name. Recent detections and the session count come from the recogniser's in-memory log.
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
# The camera status and the meme panel refresh together, so the hand tag under the
# video never contradicts the meme panel for longer than one refresh.
REFRESH_S = 0.5

processor, landmark_hook = ui.get_vision()
recognizer = ui.get_recognizer()
processor.recorder = None            # not recording here; app.py cancels any recording

model, model_problem = ui.load_predictor()
recognizer.use(model)                # a retrained model replaces the old one here
processor.recognizer = recognizer if model is not None else None

try:
    model_report = train_model.load_report()
except train_model.TrainingError:
    model_report = None
try:
    _store = dc.DatasetStore()
    dataset_rows, dataset_fingerprint = _store.row_count(), _store.fingerprint()
    can_train = dc.ready_to_train(_store.summary())      # "No trained model" says what is next
except dc.DatasetError:
    dataset_rows, dataset_fingerprint, can_train = None, None, False
stale = (train_model.staleness(model_report, dataset_rows, dataset_fingerprint=dataset_fingerprint)
         if model_report else [])

if model is not None:
    n_classes = len(model.labels)
elif model_report:
    n_classes = len(model_report["labels"])
else:
    n_classes = None

ui.page_header(
    "Live dashboard",
    "Show one of your gestures to the camera. Its meme appears beside the video with the "
    "model's confidence. When the model is not confident enough, no meme is shown.",
)

for note in (model.warnings if model is not None else []):
    st.warning(note)
if stale and model is not None:
    ui.notice(ui.stale_notice(stale), "warn")      # the data changed after training

meme_library = dm.MemeLibrary()
if model is not None:
    try:
        _records = meme_library.load()
        without = meme_library.missing_for(model.labels)
    except dm.MemeError:
        _records, without = {}, []                     # the meme panel shows the reason
    # A gesture with no image would show nothing, so the owner is told which one. Names on this
    # page: this notice, the Meme panel's fix-this messages and, for such a gesture, Recent
    # detections (owner, 18 October). ui.notice, so the link opens the Memes page in this tab.
    if without:
        ui.notice("No usable meme image yet for: "
                  + ui.esc(", ".join(dm.display_name(l, _records) for l in without))
                  + f". Add one on the {ui.link('memes', 'Memes')} page.")

left, right = st.columns([3, 2], gap="large")

with left:
    with ui.panel("camera"):
        ui.card_title("Camera")
        ctx = ui.camera_widget(CAMERA_KEY, processor)

        # The key keeps this one checkbox while its default changes; without it Streamlit saw
        # a new checkbox after each click, and every second click was lost. Its explanation is
        # a hint, not help=: Streamlit puts the help icon inside the checkbox's label, so a click
        # on the icon also flipped the box (proposal PR-10).
        landmark_hook.show_landmarks = st.checkbox(
            "Show landmarks overlay", value=landmark_hook.show_landmarks, key="show_landmarks",
        )
        st.markdown('<p class="hint">Draw the detected hand skeleton on the video.</p>',
                    unsafe_allow_html=True)

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
        """The meme and its confidence meter. Refreshes twice per second without re-running
        the whole page."""
        playing = bool(ctx.state.playing)
        stats = processor.get_stats()
        _, _, live = camera_state(stats, playing)
        prediction = recognizer.latest()
        steady = recognizer.steady() if (model is not None and live and pr.is_fresh(prediction)) else None
        try:
            memes, memes_error = meme_library.load(), None
        except dm.MemeError as exc:
            memes, memes_error = None, str(exc)

        st.markdown(ui.result_card(model_problem, prediction, playing, live, steady, memes,
                                   memes_error, meme_library, camera_error=stats.error,
                                   can_train=can_train),
                    unsafe_allow_html=True)

    live_panels()


@st.fragment(run_every=REFRESH_S)
def session_panels() -> None:
    """Live statistics and recent detections, below the camera and the result panels."""
    playing = bool(ctx.state.playing)
    stats = processor.get_stats()
    _, _, live = camera_state(stats, playing)
    history, total = recognizer.history()
    try:
        memes = meme_library.load()
    except dm.MemeError:
        memes = None                         # the meme panel above shows the reason
    model_label, _ = ui.model_state(model_problem, stale)
    latest = history[0] if history else None
    stats_col, history_col = st.columns([3, 2], gap="large")     # lines up with the row above
    with stats_col:
        st.markdown(
            '<div class="card"><h2>Live statistics</h2><div class="tiles three">'
            + (tile("Latest meme", ui.meme_thumb(latest.label, memes, meme_library),
                    note=f"at {ui.clock(latest.at)}") if latest else tile("Latest meme", "n/a"))
            + tile("Recognised this session", str(total) if model is not None else "n/a")
            + tile("Gesture classes", str(n_classes) if n_classes else "n/a")
            + tile("Frames per second", f"{stats.fps:.0f}" if live else "n/a")
            + tile("Latency", f"{stats.latency_ms:.1f}" if live else "n/a", "ms" if live else "")
            + tile("Model", model_label)
            + "</div></div>",
            unsafe_allow_html=True,
        )
    with history_col:
        st.markdown(ui.history_card(history, total, model is not None, memes, meme_library),
                    unsafe_allow_html=True)


session_panels()
