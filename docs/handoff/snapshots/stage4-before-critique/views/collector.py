"""Data collector page: record labelled gesture samples from the webcam.

Workflow: pick or name a gesture, press Start camera, press Start recording and
hold the gesture. Samples (hand landmark feature vectors, never video) are
appended to data/samples.csv together with the gesture label and a
recording session id.
"""
from __future__ import annotations

import streamlit as st

import config
import data_collector as dc
import ui
from ui import camera_state, hand_tag, tag

CAMERA_KEY = "collector-camera"

processor, landmark_hook = ui.get_vision()

if "recorder" not in st.session_state:
    st.session_state.recorder = dc.Recorder()
recorder: dc.Recorder = st.session_state.recorder
processor.recorder = recorder
landmark_hook.show_landmarks = True          # you need to see the skeleton while recording

store = dc.DatasetStore()
NEW_OPTION = "New gesture..."

ui.page_header(
    "Data collector",
    "Record labelled hand landmark samples for each gesture you want the model to learn. "
    "Samples are saved to data/samples.csv. No images or video are stored.",
)


def notify(kind: str, text: str) -> None:
    st.session_state.collector_msg = (kind, text)


def load_summary():
    """Summary table, or None (after showing the error) if the dataset is unreadable."""
    try:
        return store.summary()
    except dc.DatasetError as exc:
        st.error(f"Dataset problem: {exc}")
        return None


summary = load_summary()
existing = summary["label"].tolist() if summary is not None else []
status = recorder.status()
busy = status.state in (dc.COUNTDOWN, dc.RECORDING)

left, right = st.columns([3, 2], gap="large")

# ------------------------------------------------------------------ camera and progress
with left:
    with st.container(border=True):
        st.markdown('<div class="ctitle">Camera</div>', unsafe_allow_html=True)
        ctx = ui.camera_widget(CAMERA_KEY, processor)

        @st.fragment(run_every=0.5)
        def recording_panel() -> None:
            """Camera status, countdown and progress, and saving a finished recording."""
            playing = bool(ctx.state.playing)
            stats = processor.get_stats()
            s = recorder.status()

            if not playing and s.state in (dc.COUNTDOWN, dc.RECORDING):
                recorder.stop()                  # camera stopped mid-recording: keep what we have
                s = recorder.status()

            if s.state == dc.FINISHED:
                result = recorder.pop_finished()
                try:
                    n = store.append(result)
                    if n:
                        notify("ok", f"Saved {n} samples for {result.label}.")
                    else:
                        notify("warn", "Nothing was saved because no hand was detected during the recording.")
                except dc.DatasetError as exc:
                    notify("bad", f"Could not save: {exc}")
                st.rerun()                       # refresh the gesture list and controls

            cam, hint, live = camera_state(stats, playing)
            st.markdown(f"{cam}{hand_tag(stats, live)}", unsafe_allow_html=True)

            if s.state == dc.COUNTDOWN:
                st.markdown(
                    f'<div class="count">{int(s.countdown_left) + 1}</div>'
                    '<p class="hint" style="text-align:center">Get your hand in view and make the '
                    f"{s.label} gesture.</p>", unsafe_allow_html=True)
            elif s.state == dc.RECORDING:
                st.markdown(
                    f'<p><span class="rec-dot"></span><b>Recording {s.label}</b>: '
                    f"{s.collected} of {s.target} samples</p>", unsafe_allow_html=True)
                st.progress(min(1.0, s.collected / s.target))
                if not stats.hand_detected:
                    st.markdown('<p class="hint">No hand in view, so sampling is paused. '
                                f"{s.skipped_no_hand} empty frames skipped.</p>", unsafe_allow_html=True)
                else:
                    st.markdown('<p class="hint">Slowly move and rotate your hand a little. '
                                "Variety makes the model more robust.</p>", unsafe_allow_html=True)
            else:
                st.markdown(f'<p class="hint">{hint}</p>', unsafe_allow_html=True)

        recording_panel()

    if ctx.state.playing is False and not busy:
        processor.reset()

    with st.container(border=True):
        st.markdown('<div class="ctitle">Tips for good data</div>', unsafe_allow_html=True)
        st.markdown(
            '<ul class="tips">'
            "<li>Record each gesture in <b>at least 3 separate sessions</b>. The model is tested on "
            "a session it has never seen.</li>"
            "<li>Change things between sessions: lighting, distance, background, hand angle, which hand.</li>"
            "<li>Ask friends to record too and enter their name. More people means better recognition.</li>"
            "<li>Use clearly different gestures, and add a relaxed hand class (for example "
            "<code>none</code>) so the model learns what not to match.</li>"
            "</ul>", unsafe_allow_html=True)

# ------------------------------------------------------------------ controls and dataset
with right:
    msg = st.session_state.pop("collector_msg", None)
    if msg:
        {"ok": st.success, "warn": st.warning, "bad": st.error}[msg[0]](msg[1])

    with st.container(border=True):
        st.markdown('<div class="ctitle">Record a gesture</div>', unsafe_allow_html=True)

        choice = st.selectbox("Gesture", existing + [NEW_OPTION], disabled=busy)
        label, label_error = None, None
        if choice == NEW_OPTION:
            raw = st.text_input("New gesture name", placeholder="e.g. four_gesture", disabled=busy)
            if raw.strip():
                try:
                    label = dc.slugify_label(raw)
                    st.caption(f"Saved as `{label}`")
                except ValueError as exc:
                    label_error = str(exc)
        else:
            label = choice

        person = st.text_input("Recorded by (optional)", key="person", disabled=busy,
                               placeholder="your name")
        target = st.slider("Samples in this recording", 20, config.COLLECT_TARGET_MAX,
                           config.COLLECT_TARGET_DEFAULT, step=10, disabled=busy,
                           help=f"Saved at about {config.COLLECT_RATE_HZ} samples per second.")

        if label_error:
            st.error(label_error)

        # One button for both actions: it starts a recording, then stops it.
        if busy:
            if st.button("Stop recording", key="record-toggle", use_container_width=True):
                recorder.stop()                  # the panel saves what was collected
                st.rerun()
        elif st.button("Start recording", key="record-toggle", type="primary",
                       use_container_width=True, disabled=label is None):
            stats = processor.get_stats()
            if not ctx.state.playing:
                notify("warn", "Press Start camera above the video first.")
            elif stats.error:
                notify("bad", stats.error)
            else:
                recorder.start(label, target, person)
            st.rerun()

    with st.container(border=True):
        st.markdown('<div class="ctitle">Your dataset</div>', unsafe_allow_html=True)
        if summary is None:
            pass
        elif summary.empty:
            st.markdown('<div class="empty"><b>No samples yet</b>Record your first gesture above.</div>',
                        unsafe_allow_html=True)
        else:
            total = int(summary["samples"].sum())
            st.markdown(
                f'<p class="hint">{total} samples, {len(summary)} gesture'
                f'{"s" if len(summary) != 1 else ""}. Feature mode: <b>{config.FEATURE_MODE}</b>.</p>',
                unsafe_allow_html=True)
            for row in summary.itertuples():
                kind, hint = dc.class_status(row.samples, row.recordings)
                pct = min(100, round(100 * row.samples / config.TARGET_GOOD_PER_CLASS))
                label_text = {"ok": "Ready", "warn": "Needs sessions", "bad": "Needs samples"}[kind]
                st.markdown(
                    f'<div class="cls"><div style="flex:1"><div class="n">{row.label}</div>'
                    f'<div class="m">{row.samples} samples, {row.recordings} recording'
                    f'{"s" if row.recordings != 1 else ""}. {hint}.</div>'
                    f'<div class="meter {kind}"><div style="width:{pct}%"></div></div></div>'
                    f'{tag(label_text, kind)}</div>',
                    unsafe_allow_html=True)
            if len(summary) < 2:
                st.markdown('<p class="hint">Add at least 2 gestures before training.</p>',
                            unsafe_allow_html=True)

            with st.expander("Manage data"):
                try:
                    last = store.last_session()
                except dc.DatasetError:
                    last = None
                if last and st.button(
                    f"Undo last recording ({last['samples']} samples of {last['label']})",
                    disabled=busy, use_container_width=True,
                ):
                    removed = store.delete_session(last["session_id"])
                    notify("ok", f"Removed the last recording ({removed} samples).")
                    st.rerun()

                victim = st.selectbox("Delete all samples of a gesture", existing, disabled=busy)
                sure = st.checkbox(f"Yes, permanently delete every {victim} sample")
                if st.button("Delete gesture data", disabled=busy or not sure):
                    removed = store.delete_label(victim)
                    notify("ok", f"Deleted {removed} samples of {victim}.")
                    st.rerun()

        st.markdown(f'<p class="hint">Stored in <code>data/{config.SAMPLES_CSV.name}</code>. '
                    "Only landmark numbers are saved, never images or video.</p>",
                    unsafe_allow_html=True)
