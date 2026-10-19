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

pages = [
    st.Page("views/dashboard.py", title="Live dashboard", default=True),
    st.Page("views/collector.py", title="Data collector"),
    st.Page("views/performance.py", title="Model performance"),
    st.Page("views/privacy.py", title="Privacy policy"),
    st.Page("views/terms.py", title="Terms and conditions"),
]
st.navigation(pages, position="top").run()
