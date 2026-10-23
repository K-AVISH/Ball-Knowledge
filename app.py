"""Ball Knowledge Vision AI: Streamlit entry point.

Run with:  streamlit run app.py

This file only sets up the page, the shared styling and the navigation; each
page lives in views/.
"""
import streamlit as st

import config
import ui

st.set_page_config(
    page_title=config.APP_TITLE,
    page_icon=str(config.FAVICON_PATH),
    layout="wide",
)
ui.inject_css()


@st.cache_resource(show_spinner=False)
def fetch_hand_model() -> None:
    """A fresh server (such as Streamlit Community Cloud) has no models/mediapipe/, which
    is not in git: download the hand model once. The camera picks it up by itself."""
    import download_models
    if not (config.MEDIAPIPE_MODELS_DIR / "hand_landmarker.task").exists():
        download_models.download("hand_landmarker.task", download_models.MODELS["hand_landmarker.task"])


fetch_hand_model()

collector = st.Page("views/collector.py", title="Data collector")
pages = [
    st.Page("views/dashboard.py", title="Live dashboard", default=True),
    collector,
    st.Page("views/performance.py", title="Model performance"),
    st.Page("views/memes.py", title="Memes"),
    st.Page("views/privacy.py", title="Privacy policy"),
    st.Page("views/terms.py", title="Terms and conditions"),
]
page = st.navigation(pages, position="top")
if page is not collector:
    ui.leave_collector()             # any other page cancels a recording in progress
# Each browser tab names its page first, so open tabs and history can be told apart.
st.set_page_config(page_title=f"{page.title} | {config.APP_TITLE}")
page.run()
