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
import dataset_manager as dm
import ui
from ui import camera_state, hand_tag, tag

CAMERA_KEY = "collector-camera"

processor, landmark_hook = ui.get_vision()

if "recorder" not in st.session_state:
    st.session_state.recorder = dc.Recorder()
recorder: dc.Recorder = st.session_state.recorder
processor.recorder = recorder
processor.recognizer = None                  # no live recognition while collecting samples
landmark_hook.show_landmarks = True          # you need to see the skeleton while recording

store = dc.DatasetStore()
NEW_OPTION = "New gesture..."

try:
    memes = dm.MemeLibrary().load()
except dm.MemeError:
    memes = {}                               # the dashboard and the Memes page say why


def name(label: str) -> str:
    """The gesture's name from the Memes page, the same as every other page shows."""
    return dm.display_name(label, memes)


def name_and_id(label: str) -> str:
    """'First meme (first_meme)': the name, plus the id the samples are saved under."""
    shown = name(label)
    return shown if shown == label else f"{shown} ({label})"

ui.page_header(
    "Data collector",
    "Record labelled hand landmark samples for each gesture you want the model to learn. "
    "Samples are saved to data/samples.csv. No images or video are stored.",
)


def notify(kind: str, text: str) -> None:
    st.session_state.collector_msg = (kind, text)
    st.session_state.collector_msg_seen = False


def dismiss() -> None:
    """The callback of every control on this page. A message stays until your next action
    here: the camera reruns the page when it starts, and that rerun used to clear it."""
    st.session_state.pop("collector_msg", None)


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
    with ui.panel("camera"):
        ui.card_title("Camera")
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
                        notify("ok", f"Saved {n} samples for {name(result.label)}.")
                    else:
                        notify("warn", "Nothing was saved because no hand was detected during the recording.")
                except (dc.DatasetError, OSError) as exc:        # OSError: for example a full disk
                    notify("bad", f"Could not save: {exc}")
                st.rerun()                       # refresh the gesture list and controls

            cam, hint, live = camera_state(stats, playing)
            st.markdown(f"{cam}{hand_tag(stats, live)}", unsafe_allow_html=True)

            if s.state == dc.COUNTDOWN:
                st.markdown(
                    f'<div class="count">{int(s.countdown_left) + 1}</div>'
                    '<p class="hint" style="text-align:center">Get your hand in view and make the '
                    f"{ui.esc(name(s.label))} gesture.</p>", unsafe_allow_html=True)
            elif s.state == dc.RECORDING:
                st.markdown(
                    f'<p><span class="rec-dot"></span><b>Recording {ui.esc(name(s.label))}</b>: '
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

    with ui.panel("tips"):
        ui.card_title("Tips for good data")
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
    # The message has a slot in every run, so the panels below never move. When they moved
    # (Undo ends one run early with no message, then shows one), the browser kept a faded
    # copy of Your dataset with the old numbers.
    msg_slot = st.empty()
    msg = st.session_state.get("collector_msg")
    if msg:
        {"ok": msg_slot.success, "warn": msg_slot.warning, "bad": msg_slot.error}[msg[0]](msg[1])
        st.session_state.collector_msg_seen = True       # another page clears it (ui.leave_collector)

    with ui.panel("record"):
        ui.card_title("Record a gesture")

        choice = st.selectbox("Gesture", existing + [NEW_OPTION], disabled=busy, on_change=dismiss,
                              format_func=lambda g: g if g == NEW_OPTION else name_and_id(g))
        label, label_error = None, None
        if choice == NEW_OPTION:
            raw = st.text_input("New gesture name", placeholder="e.g. four_gesture", disabled=busy,
                                on_change=dismiss)
            if raw.strip():
                try:
                    label = dc.slugify_label(raw)
                    st.caption(f"Saved as `{label}`")
                except ValueError as exc:
                    label_error = str(exc)
        else:
            label = choice

        person = st.text_input("Recorded by (optional)", key="person", disabled=busy,
                               placeholder="your name", on_change=dismiss)
        target = st.slider("Samples in this recording", 20, config.COLLECT_TARGET_MAX,
                           config.COLLECT_TARGET_DEFAULT, step=10, disabled=busy, on_change=dismiss,
                           help=f"Saved at about {config.COLLECT_RATE_HZ} samples per second.")

        if label_error:
            st.error(label_error)

        # One button for both actions: it starts a recording, then stops it.
        if busy:
            if st.button("Stop recording", key="record-toggle", use_container_width=True,
                         on_click=dismiss):
                recorder.stop()                  # the panel saves what was collected
                st.rerun()
        elif st.button("Start recording", key="record-toggle", type="primary",
                       use_container_width=True, disabled=label is None, on_click=dismiss):
            stats = processor.get_stats()
            if not ctx.state.playing:
                notify("warn", "Start the camera first: press Start camera under the video.")
            elif stats.error:
                notify("bad", stats.error)
            else:
                recorder.start(label, target, person)
            st.rerun()
        if not busy and choice == NEW_OPTION and not raw.strip():
            # the button is disabled until there is a name; say so (proposal PR-8)
            st.markdown('<p class="hint">Type a gesture name to start.</p>', unsafe_allow_html=True)

    with ui.panel("dataset"):
        ui.card_title("Your dataset")
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
                    f'<div class="cls"><div style="flex:1"><div class="n">{ui.esc(name(row.label))}'
                    + (f' <span class="m">{ui.esc(row.label)}</span>' if name(row.label) != row.label else "")
                    + '</div>'
                    f'<div class="m">{row.samples} samples, {row.recordings} recording'
                    f'{"s" if row.recordings != 1 else ""}. {hint}.</div>'
                    f'<div class="meter {kind}"><div style="width:{pct}%"></div></div></div>'
                    f'{tag(label_text, kind)}</div>',
                    unsafe_allow_html=True)
            st.markdown(f'<p class="hint">Bars fill toward {config.TARGET_GOOD_PER_CLASS} samples, the '
                        f"suggested amount. Ready needs {config.TARGET_MIN_PER_CLASS} samples from "
                        f"{config.MIN_SESSIONS_PER_CLASS} separate recordings.</p>",
                        unsafe_allow_html=True)
            # One slot in every run for what comes next, so nothing below it moves (proposal PR-7)
            next_step = st.empty()
            if len(summary) < 2:
                next_step.markdown('<p class="hint">Add at least 2 gestures before training.</p>',
                                   unsafe_allow_html=True)
            elif dc.ready_to_train(summary):
                # Not "Ready": the gesture tags above use that word for more samples (PR-14)
                next_step.markdown('<p class="hint">You can train now: Train model is on the '
                                   f"{ui.link('performance', 'Model performance')} page.</p>",
                                   unsafe_allow_html=True)

            with st.expander("Manage data"):
                try:
                    last = store.last_session()
                except dc.DatasetError:
                    last = None
                if last and st.button(
                    f"Undo last recording ({last['samples']} samples of {name(last['label'])})",
                    disabled=busy, use_container_width=True, on_click=dismiss,
                ):
                    try:
                        removed = store.delete_session(last["session_id"])
                        notify("ok", f"Removed the last recording ({removed} samples).")
                    except (dc.DatasetError, OSError) as exc:     # another tab saving, a full disk
                        notify("bad", f"Nothing was deleted: {exc}")
                    st.rerun()

                victim = st.selectbox("Delete all samples of a gesture", existing, disabled=busy,
                                      format_func=name_and_id, on_change=dismiss)
                sure = st.checkbox(f"Yes, permanently delete every {name(victim)} sample",
                                   on_change=dismiss)
                if st.button("Delete gesture data", disabled=busy or not sure, on_click=dismiss):
                    try:
                        removed = store.delete_label(victim)
                        notify("ok", f"Deleted {removed} samples of {name(victim)}.")
                    except (dc.DatasetError, OSError) as exc:
                        notify("bad", f"Nothing was deleted: {exc}")
                    st.rerun()

        st.markdown(f'<p class="hint">Stored in <code>data/{config.SAMPLES_CSV.name}</code>. '
                    "Only landmark numbers are saved, never images or video.</p>",
                    unsafe_allow_html=True)
