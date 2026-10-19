"""Memes page: set the image, title, Ball Knowledge rating and description for each gesture.

Everything here is written to assets/memes/memes.json through dataset_manager, the same
code as `python dataset_manager.py`. The model only recognises the gesture; the rating
and description are the user's own and are never generated.
"""
from __future__ import annotations

import streamlit as st

import config
import data_collector as dc
import dataset_manager as dm
import train_model
import ui

ui.page_header(
    "Memes",
    "Choose the meme, title, Ball Knowledge rating and description shown for each gesture. "
    "The model only recognises the gesture. Everything on this page is yours to set.",
)

msg = st.session_state.pop("memes_msg", None)
if msg:
    {"ok": st.success, "bad": st.error}[msg[0]](msg[1])

library = dm.MemeLibrary()
try:
    records = library.load()
except dm.MemeError as exc:
    st.error(f"{exc} Fix assets/memes/memes.json by hand before editing here, so nothing in it "
             "is overwritten.")
    st.stop()

# Every gesture the app knows about: trained, recorded, or already in memes.json.
known = set(records)
try:
    report = train_model.load_report()
except train_model.TrainingError:
    report = None
if report:
    known.update(report.get("labels", []))
try:
    known.update(dc.DatasetStore().labels())
except dc.DatasetError:
    pass
gestures = sorted(g for g in known if g != config.NONE_LABEL)

if not gestures:
    st.markdown('<div class="empty"><b>No gestures yet</b>Record a gesture on the '
                f'{ui.link("collector", "Data collector")} page first. Its meme is set here.</div>',
                unsafe_allow_html=True)
    st.stop()


def state(record, check) -> str:
    return "Set" if record is not None and check(record) else "Not set"


left, right = st.columns([3, 2], gap="large")

with left:
    with st.container(border=True):
        ui.card_title("Your memes")
        rows = []
        for g in gestures:
            r = records.get(g)
            image = ("Missing" if r is None or library.image_problem(r) else "Set")
            rows.append([dm.display_name(g, records), image,
                         state(r, lambda x: x.ball_knowledge_level),
                         state(r, lambda x: x.description)])
        st.markdown(ui.html_table(["Gesture", "Image", "Rating", "Description"], rows,
                                  numeric_from=4,
                                  caption="What is set for each gesture's meme."),
                    unsafe_allow_html=True)
        st.markdown(f'<p class="hint">The {config.NONE_LABEL} gesture means a hand with no '
                    "gesture, so it never shows a meme and is not listed.</p>",
                    unsafe_allow_html=True)

    with st.container(border=True):
        ui.card_title("Edit a meme")
        gid = st.selectbox("Gesture", gestures, format_func=lambda g: dm.display_name(g, records))
        current = records.get(gid, dm.MemeRecord(gid))
        # One form and one set of widget keys per gesture, so text typed for one gesture and
        # not saved never appears in another gesture's form.
        with st.form(key=f"meme-form-{gid}", border=False):
            name = st.text_input("Gesture name", value=current.gesture_name, key=f"meme-name-{gid}",
                                 max_chars=dm.MAX_TEXT["gesture_name"],
                                 help=f"Shown on every panel instead of the id {gid}.")
            title = st.text_input("Meme title", value=current.meme_title, key=f"meme-title-{gid}",
                                  max_chars=dm.MAX_TEXT["meme_title"])
            rating = st.text_input("Ball Knowledge rating", value=current.ball_knowledge_level,
                                   key=f"meme-rating-{gid}",
                                   max_chars=dm.MAX_TEXT["ball_knowledge_level"],
                                   placeholder="for example 8/10",
                                   help="Shown exactly as you type it.")
            description = st.text_area("Description", value=current.description, key=f"meme-desc-{gid}",
                                       max_chars=dm.MAX_TEXT["description"], height=110,
                                       help="Shown as one paragraph. Line breaks are joined.")
            upload = st.file_uploader(
                "Meme image" if not current.image_path else "Replace the image",
                type=[s.lstrip(".") for s in config.MEME_IMAGE_SUFFIXES], key=f"meme-image-{gid}",
                help=f"Up to {config.MEME_MAX_UPLOAD_MB} MB. Copied into assets/memes/ on this computer. "
                     "Leave empty to keep the current image.")
            saved = st.form_submit_button("Save meme", type="primary")
        if saved:
            try:
                dm.save_edit(library, gid, gesture_name=name, meme_title=title,
                             ball_knowledge_level=rating, description=description,
                             upload_name=upload.name if upload else None,
                             upload_bytes=upload.getvalue() if upload else None)
                st.session_state.memes_msg = (
                    "ok", f"Saved the meme for {dm.display_name(gid, library.load())}. The Live "
                          "dashboard shows it the next time this gesture is recognised.")
            except (dm.MemeError, ValueError, OSError) as exc:
                st.session_state.memes_msg = ("bad", f"Nothing was saved: {exc}")
            st.rerun()

with right:
    # The real Meme result panel from the dashboard, for the gesture being edited.
    st.markdown('<p class="hint" style="margin:0 0 .5rem 0">Preview: the Meme result panel when '
                f"{ui.esc(dm.display_name(gid, records))} is recognised. Save to update it.</p>",
                unsafe_allow_html=True)
    st.markdown(ui.meme_card(gid, records, None, library), unsafe_allow_html=True)
