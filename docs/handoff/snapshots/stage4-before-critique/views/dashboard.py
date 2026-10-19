"""Live dashboard page: camera, landmarks, recognition, meme result and stats.

The recognition, meme and history panels show plain empty states until a model
is trained and connected.
"""
from __future__ import annotations

import streamlit as st

import train_model
import ui
from ui import camera_state, hand_tag, tile

CAMERA_KEY = "dashboard-camera"

processor, landmark_hook = ui.get_vision()
processor.recorder = None            # not recording on this page
_rec = st.session_state.get("recorder")
if _rec is not None:
    _rec.cancel()                    # leaving the collector page abandons any recording

try:
    model_report = train_model.load_report()
except train_model.TrainingError:
    model_report = None
n_classes = len(model_report["labels"]) if model_report else None

ui.page_header(
    "Live dashboard",
    "Webcam preview with hand landmark detection. Gesture recognition and meme results "
    "appear here once a model has been trained on your own samples.",
)

left, right = st.columns([3, 2], gap="large")

with left:
    with st.container(border=True):
        st.markdown('<div class="ctitle">Camera</div>', unsafe_allow_html=True)
        ctx = ui.camera_widget(CAMERA_KEY, processor)

        landmark_hook.show_landmarks = st.checkbox(
            "Show landmarks overlay", value=landmark_hook.show_landmarks,
            help="Draw the detected hand skeleton on the video.",
        )

        @st.fragment(run_every=1.0)
        def camera_status() -> None:
            playing = bool(ctx.state.playing)
            stats = processor.get_stats()
            cam, hint, live = camera_state(stats, playing)
            st.markdown(f'{cam}{hand_tag(stats, live)}<p class="hint">{hint}</p>',
                        unsafe_allow_html=True)

        camera_status()

    if ctx.state.playing is False:
        processor.reset()  # clear stale stats; the browser releases the camera when it stops


with right:
    @st.fragment(run_every=1.0)
    def live_panels() -> None:
        """Refreshes once per second without re-running the whole page."""
        stats = processor.get_stats()
        _, _, live = camera_state(stats, bool(ctx.state.playing))

        st.markdown(
            '<div class="tiles">'
            + tile("Frames per second", f"{stats.fps:.0f}" if live else "n/a")
            + tile("Latency", f"{stats.latency_ms:.1f}" if live else "n/a", "ms" if live else "")
            + tile("Gesture classes", str(n_classes) if n_classes else "n/a")
            + tile("Model", "Trained" if model_report else "Not trained")
            + "</div>",
            unsafe_allow_html=True,
        )
        if model_report:
            recognition = (
                '<div class="big">Model trained</div>'
                f'<p class="hint">{n_classes} gestures. Live recognition is not connected to the '
                "camera yet, so no prediction is shown. See Model performance for test results.</p>")
        else:
            recognition = (
                '<div class="big">No trained model</div>'
                '<p class="hint">Record samples on the Data collector page, then train a model on '
                "the Model performance page. The predicted gesture and its confidence will be shown here.</p>")
        st.markdown(f'<div class="card"><h3>Recognition</h3>{recognition}</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card"><h3>Meme result</h3>'
            '<div class="empty"><b>No result yet</b>The meme, its Ball Knowledge rating and '
            "description for a recognised gesture will appear here.</div></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="card"><h3>Recent detections</h3>'
            '<div class="empty"><b>Nothing detected</b>Each recognised gesture is listed here '
            "with its confidence and time.</div></div>",
            unsafe_allow_html=True,
        )

    live_panels()
