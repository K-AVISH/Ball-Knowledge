"""Shared UI pieces: styling, small HTML helpers, the per-session vision objects
and the camera widget used by every page that shows the webcam."""
from __future__ import annotations

import base64
import functools
import html
import time
from pathlib import Path
from typing import Dict, Optional

import av
import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer

import config
import dataset_manager as dm
import predictor as pr
from vision import FrameProcessor, LandmarkHook, VisionStats, camera_is_live

# Flat surfaces, one accent colour, small corners, static layout.
CSS = """
<style>
:root {
  --bg:#0b0f0d; --surface:#111815; --surface2:#151d19; --border:#212c26;
  --text:#e6ece8; --muted:#8c9b93; --accent:#2fbf71; --warn:#e0b04a; --bad:#e5645f;
}
.stApp { background: var(--bg); }
header[data-testid="stHeader"] { background: var(--bg); border-bottom: 1px solid var(--border); }
/* the top navigation lives inside stToolbar, so hide only its Deploy button and menu */
[data-testid="stToolbarActions"], [data-testid="stMainMenu"], [data-testid="stAppDeployButton"],
[data-testid="stDecoration"], #MainMenu, footer, .stDeployButton { display: none !important; }
[data-testid="stTopNavLink"], [data-testid="stTopNavSection"] { border-radius: 6px; font-weight: 600; }
.block-container { padding-top: 5rem; max-width: 1280px; }

/* page header (scoped under .stApp so Streamlit's heading and paragraph styles do not win) */
.stApp .brand { font-size: .78rem; letter-spacing: .08em; text-transform: uppercase;
         color: var(--muted); margin: 0 0 .3rem 0; }
.stApp .page-title { font-size: 1.75rem; font-weight: 650; margin: 0; padding: 0; color: var(--text);
              line-height: 1.25; }
.stApp .page-desc { color: var(--muted); margin: .35rem 0 1.5rem 0; max-width: 80ch; }

/* cards: HTML cards (.card) and bordered panels (ui.panel). A keyed container gets the
   class st-key-<key>, which is how Streamlit lets a page style one container. */
.card, .stApp [class*="st-key-panel-"] {
  background: var(--surface) !important; border: 1px solid var(--border) !important;
  border-radius: 8px !important; }
.card { padding: 1rem 1.2rem; margin-bottom: 1rem; }
.stApp [class*="st-key-panel-"] { padding: 1rem 1.2rem !important; }
.stApp .card h2, .stApp h2.ctitle { margin: 0 0 .7rem 0; padding: 0; font-size: .74rem; text-transform: uppercase;
  letter-spacing: .1em; color: var(--muted); font-weight: 650; line-height: 1.4; }
/* section titles are real h2 headings; hide the link icon Streamlit adds to headings */
[data-testid="stHeaderActionElements"] { display: none !important; }
/* Streamlit pulls each text block up by 1rem to cancel a paragraph's bottom margin. Text
   that ends a block with a smaller margin gets that 1rem back, so it never touches a border. */
.stApp [data-testid="stMarkdownContainer"] > :is(p.hint, p.cm-axis, .empty, ul.tips):last-child {
  margin-bottom: 1rem; }
/* columns stacked on a phone: the same 1rem gap as between panels, not the 4rem column gap */
.stApp [data-testid="stHorizontalBlock"] { row-gap: 1rem; }

/* status tags (labels, not buttons) */
.tag { display: inline-block; padding: .15rem .55rem; border-radius: 4px; font-size: .78rem;
       font-weight: 600; border: 1px solid var(--border); margin: 0 .4rem .3rem 0; }
.tag.ok   { color: var(--accent); border-color: rgba(47,191,113,.45); background: rgba(47,191,113,.08); }
.tag.warn { color: var(--warn);   border-color: rgba(224,176,74,.4);  background: rgba(224,176,74,.08); }
.tag.bad  { color: var(--bad);    border-color: rgba(229,100,95,.4);  background: rgba(229,100,95,.08); }
.tag.off  { color: var(--muted);  background: var(--surface2); }
.stApp .hint { color: var(--muted); font-size: .88rem; margin: .4rem 0 0 0; }
.stApp .tbl .tag { margin: 0; white-space: nowrap; }

/* notices: st.warning, st.error, st.success and ui.notice share one flat look in the site's own
   colours, tinted like the tags. Streamlit's defaults (olive yellow, blue) are outside the palette.
   The text stays --text, so it reads at full contrast whatever the tint. */
.stApp [data-testid="stAlertContainer"], .notice {
  background: var(--surface) !important; color: var(--text) !important;
  border: 1px solid rgba(140,155,147,.45); border-radius: 8px !important; }
.stApp [data-testid^="stAlertContent"], .stApp [data-testid^="stAlertContent"] * { color: var(--text) !important; }
.stApp [data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]), .notice.warn {
  background: rgba(224,176,74,.08) !important; border-color: rgba(224,176,74,.5); }
.stApp [data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]), .notice.bad {
  background: rgba(229,100,95,.08) !important; border-color: rgba(229,100,95,.5); }
.stApp [data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]), .notice.ok {
  background: rgba(47,191,113,.08) !important; border-color: rgba(47,191,113,.5); }
.notice { padding: .85rem 1rem; margin-bottom: 1rem; line-height: 1.5; }
.stApp .notice a, .stApp [data-testid^="stAlertContent"] a { color: var(--accent) !important; text-decoration: underline; }

/* stat tiles. Each tile spans three rows of the grid (label, value, note) through subgrid,
   so when one label wraps to two lines every value in that row still starts at the same height. */
.tiles { display: grid; grid-template-columns: repeat(2, 1fr); gap: .7rem; margin-bottom: 1rem; }
.tiles.four { grid-template-columns: repeat(4, 1fr); }
.tiles.three { grid-template-columns: repeat(3, 1fr); margin-bottom: 0; }
@media (max-width: 720px) { .tiles.four, .tiles.three { grid-template-columns: repeat(2, 1fr); } }
.card .tile { background: var(--surface2); }
.tile { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: .8rem 1rem;
        display: grid; grid-row: span 3; grid-template-rows: subgrid; row-gap: 0; align-content: start; }
.tile.wide { grid-column: 1 / -1; }
.tile .k { font-size: .7rem; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); font-weight: 650; }
.tile .v { font-size: 1.5rem; font-weight: 650; margin-top: .15rem; color: var(--text);
           font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.tile.worded .v { font-size: 1.15rem; line-height: 1.3; margin-top: .3rem; }
.tile .note { color: var(--muted); font-size: .8rem; font-variant-numeric: tabular-nums; }
.tile .v small { font-size: .8rem; color: var(--muted); font-weight: 500; margin-left: .2rem; }

/* the meme panel's meter and title, and empty states */
.big { font-size: 1.5rem; font-weight: 650; line-height: 1.2; margin: .2rem 0 0 0; overflow-wrap: anywhere; }
.conf { position: relative; height: 8px; border-radius: 2px; background: #1b2620; margin: .7rem 0 .3rem 0; }
.conf .fill { height: 100%; border-radius: 2px; background: var(--accent); }
.conf .fill.warn { background: var(--warn); }
.conf .mark { position: absolute; top: -3px; width: 2px; height: 14px; background: var(--text); }
.conf-row { display: flex; justify-content: space-between; gap: .8rem; font-size: .82rem;
            color: var(--muted); font-variant-numeric: tabular-nums; }
.conf-row b { color: var(--text); }
.empty { border: 1px dashed #2b3a33; border-radius: 8px; padding: 1.4rem 1rem; text-align: center;
         color: var(--muted); }
.empty b { display: block; color: var(--text); margin-bottom: .2rem; }

/* collector */
.count { font-size: 3rem; font-weight: 700; color: var(--accent); text-align: center; line-height: 1; }
.rec-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; background: var(--bad);
           margin-right: .5rem; }
.cls { display: flex; align-items: center; justify-content: space-between; gap: .8rem;
       padding: .65rem .8rem; border: 1px solid var(--border); border-radius: 8px; margin-bottom: .5rem;
       background: var(--surface2); }
.cls .n { font-weight: 650; }
.cls .m { color: var(--muted); font-size: .82rem; }
.cls .meter { height: 4px; border-radius: 2px; background: #1b2620; margin-top: .45rem; overflow: hidden; }
.cls .meter > div { height: 100%; background: var(--accent); }
.cls .meter.warn > div { background: var(--warn); }
.cls .meter.bad > div { background: var(--bad); }
.tips { margin: .2rem 0 0 0; padding-left: 1.1rem; color: var(--muted); font-size: .88rem; }
.tips li { margin: .2rem 0; }

/* tables: wide ones scroll inside their own labelled region, never the page */
.tbl-wrap { overflow-x: auto; max-width: 100%; }
.stApp .card a, .stApp .hint a { color: var(--accent); text-decoration: underline; }
.tbl-wrap:focus-visible, .stApp a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
/* Tab also stops on the scrolling page area; show that stop like every other one */
.stApp [data-testid="stMain"]:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
/* checkboxes: Streamlit keeps the real input in a 1px clipped box, so its focus ring never
   shows; ring the visible box while the input has keyboard focus */
.stApp [data-testid="stCheckbox"] label:has(input:focus-visible) > div:first-of-type {
  outline: 2px solid var(--accent); outline-offset: 2px; }
/* narrow windows: the page links sit in a menu that Streamlit only slides off screen when
   closed, so Tab stopped on them out of view; hidden, they leave the tab order. The * also
   covers the menu's close button, which Streamlit marks visible on phones. */
.stApp [data-testid="stSidebar"][aria-expanded="false"],
.stApp [data-testid="stSidebar"][aria-expanded="false"] * { visibility: hidden; }
.tbl caption, .cm caption { caption-side: top; text-align: left; color: var(--muted); font-size: .8rem;
  padding: 0 0 .4rem 0; }
.tbl { width: 100%; border-collapse: collapse; font-size: .88rem; }
.tbl th, .tbl td, .cm th, .cm td { border: none; }
.tbl th { text-align: left; color: var(--muted); font-size: .72rem; letter-spacing: .08em;
          text-transform: uppercase; font-weight: 650; padding: .45rem .6rem;
          border-bottom: 1px solid var(--border); }
.tbl td { padding: .5rem .6rem; border-bottom: 1px solid var(--border); color: var(--text); }
.tbl .num { text-align: right; font-variant-numeric: tabular-nums; }
.tbl tr:last-child td, .tbl tr:last-child th { border-bottom: none; }
.cm { border-collapse: separate; border-spacing: 3px; width: 100%; font-size: .85rem; }
.cm th { color: var(--muted); font-weight: 600; padding: .3rem .4rem; font-size: .75rem; }
.cm th.row { text-align: right; white-space: nowrap; }
.cm td { text-align: center; padding: .55rem .3rem; border-radius: 4px; background: var(--surface2);
         font-variant-numeric: tabular-nums; color: var(--text); }
.stApp .cm-axis { color: var(--muted); font-size: .78rem; margin: .5rem 0 0 0; }
.tbl th[scope="row"] { font-size: .88rem; letter-spacing: 0; text-transform: none; color: var(--text);
  font-weight: 500; border-bottom: 1px solid var(--border); padding: .5rem .6rem; }
/* phones: tables tighten so more of them fit without scrolling, and a status tag in a table
   becomes its coloured word alone (the word carries the meaning, the colour repeats it) */
@media (max-width: 480px) {
  .stApp .tbl th, .stApp .tbl td { padding: .45rem .35rem; }
  .stApp .tbl thead th { letter-spacing: .02em; }
  .stApp .tbl .tag { padding: 0; border: none; background: none; }
  .stApp .cm { border-spacing: 2px; }
  .stApp .cm th { padding: .3rem .25rem; }
}
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

/* meme panel: the meme, or a message in its place, always in one 4:3 frame, so the panel
   keeps its size from state to state and nothing below it moves */
.meme-frame { aspect-ratio: 4/3; width: 100%; box-sizing: border-box; border-radius: 6px;
  background: var(--surface2); display: flex; align-items: center; justify-content: center;
  overflow: hidden; }
.meme-frame .meme-img { display: block; width: 100%; height: 100%; object-fit: contain; }
.meme-frame.msg { border: 1px dashed #2b3a33; padding: 1rem; text-align: center; color: var(--muted);
  font-size: .9rem; line-height: 1.5; }
.meme-frame.msg.warn { border: 1px solid rgba(224,176,74,.5); }
.meme-frame.msg.bad { border: 1px solid rgba(229,100,95,.5); }
.frame-msg { max-width: 36ch; }
.frame-msg b { display: block; color: var(--text); font-size: 1.15rem; font-weight: 650; margin-bottom: .3rem; }
.stApp .frame-msg a { color: var(--accent); text-decoration: underline; }
.owner { margin-top: .8rem; }
.meme-desc { color: var(--text); margin: .5rem 0 0 0; line-height: 1.5; }
/* a meme as a small picture: Latest meme tile and Recent detections */
.thumb { display: block; width: 52px; height: 39px; object-fit: contain; border-radius: 4px;
  background: var(--surface2); }
.tile .thumb { width: 64px; height: 48px; margin-top: .3rem; }

/* legal pages */
.legal { max-width: 70ch; }
.legal h2 { font-size: 1.1rem; margin: 1.6rem 0 .4rem 0; }
.legal p, .legal li { color: #c9d3cd; line-height: 1.6; }

/* controls: small radius, no pills */
.stButton button { border-radius: 6px !important; font-weight: 600 !important; }
/* green buttons (Start recording, Train model, Save meme): dark text, 8.1:1. Streamlit's
   white text on this green is 2.4:1. A disabled one has no green fill, so it keeps
   Streamlit's faded light text; dark text there would be invisible on the dark page. */
.stApp [data-testid^="stBaseButton-primary"]:not(:disabled),
.stApp [data-testid^="stBaseButton-primary"]:not(:disabled) * {
  color: var(--bg) !important; }
/* Streamlit darkens them on hover to #20834d, where dark text is 4.1:1; lighten instead (9.1:1) */
.stApp [data-testid^="stBaseButton-primary"]:is(:hover, :active):not(:disabled) {
  background: #45c983 !important; border-color: #45c983 !important; }
[data-testid="stProgress"] > div, [data-testid="stProgress"] div[role="progressbar"],
[data-testid="stProgress"] div[role="progressbar"] > div { border-radius: 2px !important; }
iframe { border-radius: 6px; }
/* phones (the columns stack): the dashboard's camera at 60% of the width, centred, so more of the
   meme below it is in the first screen; its 4:3 frame shrinks with it (proposal PR-5, option C).
   The collector's camera keeps the full width. */
@media (max-width: 640px) {
  .stApp [class*="st-key-dashboard-camera"] iframe {
    width: 60% !important; display: block; margin: 0 auto; }
}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def page_header(title: str, description: str) -> None:
    st.markdown(
        f'<p class="brand">{config.APP_TITLE}</p>'
        f'<h1 class="page-title">{title}</h1>'
        f'<p class="page-desc">{description}</p>',
        unsafe_allow_html=True,
    )


def tag(text: str, kind: str) -> str:
    return f'<span class="tag {kind}">{text}</span>'


class Html(str):
    """A table cell that is already HTML built from escaped parts (a tag, say), so
    html_table puts it in as it is. Every other cell is escaped."""


def notice(body: str, kind: str = "info") -> None:
    """A notice in the same look as st.warning and friends, for text that needs an in-app link
    (Streamlit's own notices open links in a new tab). `body` is HTML: escape data in it.
    `kind` is info, ok, warn or bad."""
    st.markdown(f'<div class="notice {kind}">{body}</div>', unsafe_allow_html=True)


def tile(label: str, value: str, unit: str = "", wide: bool = False, note: str = "") -> str:
    """A stat tile. `wide` spans the whole row. `note` is a second line under the value,
    for a word value with a detail (a gesture name and its time), so the two never wrap together."""
    small = f"<small>{unit}</small>" if unit else ""
    sub = f'<div class="note">{note}</div>' if note else ""
    return (f'<div class="tile{" wide" if wide else ""}{" worded" if note else ""}"><div class="k">{label}</div>'
            f'<div class="v">{value}{small}</div>{sub}</div>')


def esc(value) -> str:
    """HTML-escape anything that came from data (gesture names, file contents)."""
    return html.escape(str(value))


def link(page: str, text: str) -> str:
    """A link to another page of this app, opened in the same tab."""
    return f'<a href="/{page}" target="_self">{esc(text)}</a>'


def pct(value: Optional[float]) -> str:
    """0.843 -> '84%'. A missing value is 'n/a', never a made-up number."""
    return "n/a" if value is None else f"{value:.0%}"


def score_pct(value: Optional[float]) -> str:
    """A model score as a percentage. The model never outputs exactly 0 or 1, so a score
    that rounds to 100% or 0% is shown as 'over 99%' or 'under 1%' instead."""
    text = pct(value)
    if text == "100%" and value < 1:
        return "over 99%"
    if text == "0%" and value > 0:
        return "under 1%"
    return text


def panel(key: str):
    """A bordered panel that looks like the HTML cards. Use it instead of
    st.container(border=True), which Streamlit draws with its own outline."""
    return st.container(border=True, key=f"panel-{key}")


def card_title(text: str) -> None:
    """Section title inside a bordered container, as a real h2 for screen readers."""
    st.markdown(f'<h2 class="ctitle">{esc(text)}</h2>', unsafe_allow_html=True)


def _scroll_region(table: str, label: str) -> str:
    """Wide tables scroll inside this box (keyboard focusable), not the whole page."""
    return f'<div class="tbl-wrap" role="region" aria-label="{esc(label)}" tabindex="0">{table}</div>'


def html_table(headers: "list[str]", rows: "list[list]", numeric_from: int = 1,
               caption: str = "") -> str:
    """A flat table. The first column names each row; columns from index `numeric_from`
    onward are right-aligned numbers. `caption` describes the table for screen readers."""
    head = "".join(f'<th scope="col" class="{"num" if i >= numeric_from else ""}">{esc(h)}</th>'
                   for i, h in enumerate(headers))
    def cell(c) -> str:
        return c if isinstance(c, Html) else esc(c)

    body = "".join(
        "<tr>" + "".join(
            (f'<th scope="row">{cell(c)}</th>' if i == 0 else
             f'<td class="{"num" if i >= numeric_from else ""}">{cell(c)}</td>')
            for i, c in enumerate(row)) + "</tr>"
        for row in rows)
    cap = f"<caption>{esc(caption)}</caption>" if caption else ""
    return _scroll_region(f'<table class="tbl">{cap}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>',
                          caption or "Table")


def confusion_table(labels: "list[str]", matrix: "list[list[int]]") -> str:
    """Confusion matrix as an HTML heatmap. Rows are the true gesture, columns the prediction.
    Shading shows each cell's share of its row: green on the diagonal, red for mistakes.
    The numbers are always printed, so the colour is never the only signal."""
    head = '<th scope="col"><span class="sr">True gesture</span></th>' + "".join(
        f'<th scope="col">{esc(l)}</th>' for l in labels)
    rows = []
    for i, (label, row) in enumerate(zip(labels, matrix)):
        total = sum(row) or 1
        cells = []
        for j, count in enumerate(row):
            share = count / total
            if count == 0:
                cells.append("<td>0</td>")
                continue
            rgb = "47,191,113" if i == j else "229,100,95"
            # capped at 0.55 so the white number keeps a contrast of at least 4.5:1 (WCAG AA)
            cells.append(f'<td style="background:rgba({rgb},{0.12 + 0.43 * share:.2f})">{count}</td>')
        rows.append(f'<tr><th scope="row" class="row">{esc(label)}</th>{"".join(cells)}</tr>')
    caption = "Confusion matrix on held-out recordings. Rows: true gesture. Columns: what the model predicted."
    table = (f'<table class="cm"><caption>{caption}</caption><thead><tr>{head}</tr></thead>'
             f'<tbody>{"".join(rows)}</tbody></table>')
    return (_scroll_region(table, "Confusion matrix")
            + '<p class="cm-axis">Green cells on the diagonal are correct predictions. Red cells are '
              "mistakes. Darker means a larger share of that gesture's held-out samples.</p>")


def get_vision() -> "tuple[FrameProcessor, LandmarkHook]":
    """One processor and landmark hook per browser session, shared by all pages.
    The video thread writes to them; the UI only reads."""
    if "processor" not in st.session_state:
        st.session_state.landmark_hook = LandmarkHook()
        st.session_state.processor = FrameProcessor(frame_hook=st.session_state.landmark_hook)
    return st.session_state.processor, st.session_state.landmark_hook


RECORDING_STOPPED = "The recording was stopped when you left the page. Nothing was saved."


def leave_collector() -> bool:
    """Every page but the Data collector cancels a recording still going there (owner's
    answer to Q2, 18 October), so a recording only ends on the collector, or is dropped.
    Returns True when one was dropped; the collector then says so when you come back.

    A collector message stays until your next action there (proposal PR-12). Opening another
    page is one, so a message the collector has already shown goes now."""
    if st.session_state.get("collector_msg_seen"):
        st.session_state.pop("collector_msg", None)
        st.session_state.pop("collector_msg_seen", None)
    recorder = st.session_state.get("recorder")
    dropped = recorder is not None and recorder.cancel_unfinished()
    if dropped:
        st.session_state.collector_msg = ("warn", RECORDING_STOPPED)
        st.session_state.collector_msg_seen = False
    return dropped


def get_recognizer() -> pr.LiveRecognizer:
    """One live recogniser per browser session. Its worker thread runs the model."""
    if "recognizer" not in st.session_state:
        st.session_state.recognizer = pr.LiveRecognizer()
    return st.session_state.recognizer


# ---------------------------------------------------------------------------
# Trained model: loaded once per version, shared by every session
# ---------------------------------------------------------------------------

def _mtime(path: Path) -> Optional[int]:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return None


@st.cache_resource(max_entries=2, show_spinner=False)
def _cached_predictor(model_path: str, labels_path: str, report_path: str, versions: tuple,
                      feature_mode: str, threshold: float, top_k: int) -> pr.Predictor:
    # `versions` holds the files' modification times, so retraining loads the new model
    # once and every other rerun reuses the loaded one. Failed loads are not cached.
    return pr.Predictor.load(Path(model_path), Path(labels_path), Path(report_path),
                             feature_mode, threshold, top_k)


def load_predictor() -> "tuple[Optional[pr.Predictor], Optional[pr.PredictorError]]":
    """(predictor, None) when the saved model is usable, otherwise (None, the reason).

    A training run renames its three files one after another, so a load in between can see
    a new model beside the old report and is refused. When the files changed while loading,
    the load is tried again (a few times at most) instead of reporting a broken model."""
    files = (config.MODEL_PATH, config.LABELS_PATH, config.REPORT_PATH)
    versions = tuple(_mtime(p) for p in files)
    for _ in range(3):
        try:
            return _cached_predictor(*(str(p) for p in files), versions,
                                     config.FEATURE_MODE, config.DEFAULT_CONFIDENCE_THRESHOLD,
                                     config.TOP_PREDICTIONS), None
        except pr.PredictorError as exc:
            problem = exc
        now = tuple(_mtime(p) for p in files)
        if now == versions:                 # nothing changed while loading: the problem is real
            break
        versions = now
    return None, problem


def model_state(problem: Optional[pr.PredictorError], stale: "list[str]") -> "tuple[str, str]":
    """(short label, tag kind) for the model: not trained, cannot load, retrain needed, loaded."""
    if isinstance(problem, pr.NotTrainedError):
        return "Not trained", "off"
    if problem is not None:
        return "Cannot load", "bad"
    if stale:
        return "Retrain needed", "warn"
    return "Loaded", "ok"


def confidence_bar(confidence: Optional[float], threshold: float, accepted: bool) -> str:
    """A flat bar for the confidence with a marker at the threshold, plus both numbers.
    With no confidence (no gesture being judged) the bar is empty and says n/a."""
    fill = 0 if confidence is None else max(0, min(100, round(confidence * 100)))
    mark = max(0, min(99, round(threshold * 100)))
    note = ("The model's own estimate, not a calibrated probability. A meme shows only above "
            f"the {pct(threshold)} threshold.")
    return (f'<div class="conf" role="img" title="{note}" aria-label="Confidence '
            f'{score_pct(confidence)}, threshold {pct(threshold)}"><div class="fill '
            f'{"" if accepted else "warn"}" style="width:{fill}%"></div>'
            f'<div class="mark" style="left:{mark}%"></div></div>'
            f'<div class="conf-row"><span>Confidence <b>{score_pct(confidence)}</b></span>'
            f'<span>Threshold {pct(threshold)}</span></div>')


def stale_notice(stale: "list[str]") -> str:
    """HTML for the dashboard notice when the data changed after training (for ui.notice)."""
    return (" ".join(esc(s) for s in stale)
            + f" Train model is on the {link('performance', 'Model performance')} page.")


# ---------------------------------------------------------------------------
# The meme panel: the meme, or a message in its place, and the confidence meter
# ---------------------------------------------------------------------------

_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
         ".gif": "image/gif"}


def _encode(img, longest: int) -> str:
    """A PIL image shrunk to `longest` pixels on its longest side, as a data URI."""
    import io
    img = img.copy()
    img.thumbnail((longest, longest))
    out = io.BytesIO()
    if img.mode in ("RGBA", "LA", "P"):
        img.save(out, format="PNG", optimize=True)
        mime = "image/png"
    else:
        img.convert("RGB").save(out, format="JPEG", quality=85)
        mime = "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(out.getvalue()).decode('ascii')}"


@functools.lru_cache(maxsize=16)
def _data_uri(path: str, mtime_ns: int) -> str:
    """The image as a data URI, keyed by modification time so a replaced image is read again.
    The meme panel is sent to the browser on every refresh, so an image that is large in
    bytes or pixels is shrunk (MEME_DISPLAY_MAX_PX) for display. The file is not changed.
    GIFs are sent as they are, so a moving GIF keeps all its frames."""
    raw = Path(path).read_bytes()
    suffix = Path(path).suffix.lower()
    if suffix != ".gif":
        try:
            from PIL import Image
            import io
            with Image.open(io.BytesIO(raw)) as img:
                if (max(img.size) > config.MEME_DISPLAY_MAX_PX
                        or len(raw) > config.MEME_DISPLAY_MAX_KB * 1024):
                    return _encode(img, config.MEME_DISPLAY_MAX_PX)
        except Exception:            # unreadable here: image_problem() has already vetted it
            pass
    return f"data:{_MIME[suffix]};base64,{base64.b64encode(raw).decode('ascii')}"


@functools.lru_cache(maxsize=32)
def _thumb_uri(path: str, mtime_ns: int) -> Optional[str]:
    """A small still of the image (a GIF's first frame) for the stats and history panels,
    which list up to 11 at once and refresh twice a second."""
    try:
        from PIL import Image
        with Image.open(path) as img:
            return _encode(img, 120)
    except Exception:
        return None


def meme_thumb(label: str, records: Optional[Dict[str, dm.MemeRecord]],
               library: Optional[dm.MemeLibrary]) -> str:
    """A gesture shown by a small picture of its meme. A gesture without a usable image
    (or with no library to look in) is shown by its name instead, since nothing else
    can say which one it was."""
    record = (records or {}).get(label)
    if library is not None and record is not None and library.image_problem(record) is None:
        path = library.image_file(record)
        try:
            uri = _thumb_uri(str(path), path.stat().st_mtime_ns)
        except OSError:                      # removed or replaced since it was checked
            uri = None
        if uri:
            return f'<img class="thumb" src="{uri}" alt="{meme_alt(record)}">'
    return esc(dm.display_name(label, records))


def meme_alt(record: dm.MemeRecord) -> str:
    """Escaped screen-reader text for a meme picture: the owner's meme title alone (the panel
    and the table column are already headed "Meme"), or just "Meme" when none is set. Never the
    gesture's name, which the dashboard does not show (owner's rule, 17 October; alt text
    decided 18 October, OD-5 and Q3)."""
    return esc(record.meme_title or "Meme")


def _frame(title: str, text: str = "", kind: str = "") -> str:
    """A message in the meme's place, in the same 4:3 frame, so the panel keeps its size."""
    return (f'<div class="meme-frame msg {kind}"><div class="frame-msg"><b>{title}</b>'
            f'{text}</div></div>')


def _meme_view(label: str, records: Optional[Dict[str, dm.MemeRecord]], load_error: Optional[str],
               library: dm.MemeLibrary, on_page: str) -> "tuple[str, str]":
    """(frame, text under it) for one gesture's meme. The frame holds the image, or says why
    there is none. Under it go only the texts the owner has written; nothing names the gesture.
    The two problems that need fixing (no meme set, image missing) do name it, since the
    owner has to know which gesture to fix."""
    if load_error:
        return _frame("Memes cannot be shown",
                      f"{esc(load_error)} Fix assets/memes/memes.json by hand. The Memes page "
                      "cannot edit it until it can be read.", "bad"), ""
    record = (records or {}).get(label)
    if record is None:
        return _frame("No meme set",
                      f"{esc(dm.display_name(label, records))} has no meme yet. Add one {on_page}, "
                      f"or with <code>python dataset_manager.py {esc(label)} --image &lt;file&gt;</code>.",
                      "warn"), ""
    problem = library.image_problem(record)
    if not problem:
        path = library.image_file(record)
        try:
            uri = _data_uri(str(path), path.stat().st_mtime_ns)
        except OSError:                      # removed or replaced since it was checked
            problem = library.image_problem(record) or f"The image file {path.name} cannot be read."
    if problem:
        return _frame("Image missing", f"{esc(problem)} Choose the image again {on_page}.", "bad"), ""

    frame = (f'<div class="meme-frame"><img class="meme-img" src="{uri}" '
             f'alt="{meme_alt(record)}"></div>')
    owner = ""
    if record.meme_title:
        owner += f'<div class="big">{esc(record.meme_title)}</div>'
    if record.ball_knowledge_level:
        owner += f'<div>{tag("Ball Knowledge: " + esc(record.ball_knowledge_level), "ok")}</div>'
    if record.description:
        owner += f'<p class="meme-desc">{esc(record.description)}</p>'
    return frame, (f'<div class="owner">{owner}</div>' if owner else "")


NO_GESTURE = "The hand in view is not one of your gestures."


def result_card(problem: Optional[pr.PredictorError], prediction: Optional[pr.Prediction],
                playing: bool, live: bool, steady: Optional[pr.Steady],
                records: Optional[Dict[str, dm.MemeRecord]], load_error: Optional[str],
                library: dm.MemeLibrary, camera_error: Optional[str] = None,
                can_train: bool = False) -> str:
    """The dashboard's panel beside the camera: the meme for the gesture being held, with the
    confidence meter under it. No gesture names: the meme is the result.

    A meme shows only for a steady gesture (LiveRecognizer.steady: recognised in
    MIN_STABLE_FRAMES of the last SMOOTHING_WINDOW frames), so one frame neither shows a meme
    nor hides one that is being held. Every other state puts its own short message in the
    meme's place, and the meter shows the score being judged or n/a. `camera_error` is the
    frame error from the camera stats: such frames never reach the model. `can_train` says the
    recorded data is ready for training (data_collector.ready_to_train)."""
    threshold = (prediction.threshold if prediction is not None
                 else config.DEFAULT_CONFIDENCE_THRESHOLD)
    confidence, accepted, under = None, False, ""
    if isinstance(problem, pr.NotTrainedError) and can_train:     # gestures recorded (PR-4)
        frame = _frame("No trained model",
                       f"Train a model on the {link('performance', 'Model performance')} page.")
    elif isinstance(problem, pr.NotTrainedError):
        frame = _frame("No trained model",
                       f"Record your gestures on the {link('collector', 'Data collector')} page, "
                       f"then train on the {link('performance', 'Model performance')} page.")
    elif problem is not None:
        frame = _frame("Model cannot be used",
                       f"{esc(problem)} Training runs on the {link('performance', 'Model performance')} "
                       "page.", "bad")
    elif not live and not playing:
        frame = _frame("Camera off", "Press Start camera. The meme for the gesture you show "
                                     "appears here.")
    elif not live:
        frame = _frame("Waiting for video", "If your browser asks for camera access, choose Allow.")
    elif camera_error:                      # the camera panel's hint says why (owner, Q1)
        frame = _frame("Camera problem", "The camera's frames cannot be processed, so no meme can "
                                         "be shown. The message under the video says why.", "bad")
    elif not pr.is_fresh(prediction):
        frame = _frame("Starting", "The model is classifying the first frames.")
    elif prediction.status == pr.ERROR:
        frame = _frame("Prediction failed", esc(prediction.error), "bad")
    elif steady is not None and steady.label == config.NONE_LABEL:
        frame = _frame("No gesture", NO_GESTURE)
    elif steady is not None:
        frame, under = _meme_view(steady.label, records, load_error, library,
                                  f"on the {link('memes', 'Memes')} page")
        confidence, accepted = steady.confidence, True
    elif prediction.status == pr.NO_HAND:
        frame = _frame("No hand in view", "Show one of your gestures to the camera.")
    elif prediction.status == pr.UNRECOGNISED:
        frame = _frame("Unrecognised", f"The best score is below the {pct(threshold)} threshold, "
                                       "so no meme is shown.", "warn")
        confidence = prediction.confidence
    elif prediction.label == config.NONE_LABEL:
        # a relaxed hand in this frame: no meme is at stake, so no vote is needed (PR-2)
        frame = _frame("No gesture", NO_GESTURE)
    else:                                   # recognised in this frame, not yet steady
        frame = _frame("Hold it steady", f"The meme appears once the gesture is recognised in "
                                         f"{config.MIN_STABLE_FRAMES} of the last "
                                         f"{config.SMOOTHING_WINDOW} frames.")
        confidence, accepted = prediction.confidence, True
    return (f'<div class="card"><h2>Meme</h2>{frame}'
            f'{confidence_bar(confidence, threshold, accepted)}{under}</div>')


def meme_card(label: str, records: Optional[Dict[str, dm.MemeRecord]],
              load_error: Optional[str], library: dm.MemeLibrary, preview: bool = False) -> str:
    """One gesture's meme as the dashboard shows it, without the meter: the Memes page
    preview. `preview` says "in the form on this page" instead of linking to that page."""
    on_page = "in the form on this page" if preview else f"on the {link('memes', 'Memes')} page"
    frame, under = _meme_view(label, records, load_error, library, on_page)
    return f'<div class="card"><h2>Meme</h2>{frame}{under}</div>'


# ---------------------------------------------------------------------------
# Recent detections and session statistics
# ---------------------------------------------------------------------------

def clock(at: float) -> str:
    """time.time() -> '14:05:09' in local time."""
    return time.strftime("%H:%M:%S", time.localtime(at))


def history_card(entries: "tuple[pr.HistoryEntry, ...]", total: int, model_ready: bool,
                 records: Optional[Dict[str, dm.MemeRecord]] = None,
                 library: Optional[dm.MemeLibrary] = None) -> str:
    """HTML for the recent detections panel, newest first. Entries come from
    predictor.DetectionLog, which adds one per change of steady gesture, not per frame.
    With `library`, each detection is shown by a small picture of its meme (meme_thumb)."""
    def card(body: str) -> str:
        return f'<div class="card"><h2>Recent detections</h2>{body}</div>'

    if not entries:
        text = ("Each meme you bring up is listed here with its time and confidence."
                if model_ready else "Recognition starts once a model is trained.")
        return card(f'<div class="empty"><b>Nothing detected yet</b>{text}</div>')
    shown = (f"Newest first, {len(entries)} of {total} this session."
             if total > len(entries) else "Newest first.")
    rows = [[clock(e.at), Html(meme_thumb(e.label, records, library)), score_pct(e.confidence)]
            for e in entries]
    return card(html_table(["Time", "Meme", "Confidence"], rows, numeric_from=2,
                           caption=shown)
                + '<p class="hint">A meme is added when it comes up, and again only after '
                f"another one or a pause of over {config.HISTORY_REPEAT_GAP_S:g} seconds. "
                "Confidence is the average over the frames that confirmed it. Kept for this "
                "browser session only, never saved.</p>")


# ---------------------------------------------------------------------------
# Camera: one toggle button
# ---------------------------------------------------------------------------
# streamlit-webrtc draws its own control inside an iframe. Its Start/Stop button is
# already a single toggle (the same button says "Start camera", then "Stop camera"),
# but it also draws a "Select Device" button and, while streaming, extra camera
# on/off and mute controls. `media_toggle_controls=False` removes the extras, and
# the small script below hides "Select Device" by styling the same-origin iframe.
#
# An earlier version drove the stream from our own button through
# `desired_playing_state`. That made the component retry getUserMedia hundreds of
# times per second whenever the camera was denied or busy, so it was dropped.

_IFRAME_CSS = (
    "html,body{background:transparent !important}"            # the panel's colour shows through
    "button.MuiButton-text{display:none !important}"          # the Select Device button
    # flat like the page's own buttons: no raised shadow, no ripple on click, dark text
    "button{text-transform:none !important;letter-spacing:0 !important;"
    "border-radius:6px !important;font-weight:600 !important;box-shadow:none !important}"
    "button.MuiButton-contained{color:#0b0f0d !important}"
    "button.MuiButton-contained:is(:hover,:active):not(:disabled){background:#45c983 !important}"
    ".MuiTouchRipple-root{display:none !important}"
    "button:focus-visible{outline:2px solid #2fbf71 !important;outline-offset:2px}"   # keyboard focus
    # With the camera off or connecting, the video area is a 4:3 frame (the shape the camera is
    # asked for), so the panel keeps its size and the page does not jump when video starts.
    ".MuiPaper-root:not(.MuiAlert-root){aspect-ratio:4/3;width:100%;box-sizing:border-box;background:#151d19 !important;"
    "border:1px dashed #2b3a33;border-radius:6px !important;color:#8c9b93 !important}"
    "video{display:block;border-radius:6px;background:#151d19}"
    # the library's own error (camera access denied, camera busy) in the look of the page's notices
    ".MuiAlert-root{background:rgba(229,100,95,.08) !important;border:1px solid rgba(229,100,95,.5);"
    "border-radius:8px !important;color:#e6ece8 !important}"
    ".MuiAlert-icon{color:#e5645f !important}"
)

_IFRAME_SCRIPT = """
<script>
(function () {
  if (window.__bkCameraStyle) return;
  window.__bkCameraStyle = true;
  var CSS = %s;
  function patch(frame) {
    try {
      var doc = frame.contentDocument;
      if (!doc || !doc.head || doc.getElementById('bk-camera-style')) return;
      var el = doc.createElement('style');
      el.id = 'bk-camera-style';
      el.textContent = CSS;
      doc.head.appendChild(el);
    } catch (e) { /* cross-origin or not ready: the default buttons simply stay visible */ }
  }
  function scan() {
    document.querySelectorAll('iframe[title*="webrtc_streamer"]').forEach(function (f) {
      patch(f);
      if (!f.dataset.bkBound) {
        f.dataset.bkBound = '1';
        f.addEventListener('load', function () { patch(f); });
      }
    });
  }
  scan();
  new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });
})();
</script>
""" % __import__("json").dumps(_IFRAME_CSS)


def _ice_servers() -> list:
    """STUN/TURN servers for the camera connection, from ice_servers in Streamlit secrets.

    On localhost browser and server are on the same machine, so none are needed (and without
    secrets the list stays empty, so the camera also works offline). A hosted copy needs a TURN
    server: see .streamlit/secrets.toml.example."""
    try:
        return [dict(server) for server in st.secrets.get("ice_servers", [])]
    except Exception:                # no secrets file at all
        return []


def camera_widget(key: str, processor: FrameProcessor):
    """Render the camera control and video; returns the WebRTC context."""

    def video_frame_callback(frame: av.VideoFrame) -> av.VideoFrame:
        """Runs on the WebRTC thread for every incoming frame."""
        img = processor.process(frame.to_ndarray(format="bgr24"))
        return av.VideoFrame.from_ndarray(img, format="bgr24")

    ctx = webrtc_streamer(
        key=key,
        mode=WebRtcMode.SENDRECV,
        video_frame_callback=video_frame_callback,
        media_stream_constraints={
            "video": {
                "width": {"ideal": config.CAMERA_WIDTH},
                "height": {"ideal": config.CAMERA_HEIGHT},
                "frameRate": {"ideal": config.CAMERA_IDEAL_FPS},
            },
            "audio": False,
        },
        async_processing=True,           # drop stale frames instead of lagging behind
        media_toggle_controls=False,     # no extra camera on/off and mute controls
        # no browser play/pause/volume bar over the video; autoplay needs it muted
        video_html_attrs={"autoPlay": True, "controls": False, "muted": True,
                          "playsInline": True, "style": {"width": "100%"}},
        translations={"start": "Start camera", "stop": "Stop camera"},
        frontend_rtc_configuration={"iceServers": _ice_servers()},
        server_rtc_configuration={"iceServers": _ice_servers()},
    )
    st.html(_IFRAME_SCRIPT, unsafe_allow_javascript=True)
    return ctx


def camera_state(stats: VisionStats, playing: bool) -> "tuple[str, str, bool]":
    """Returns (status tag html, hint html, is_live). Error text in the hint is escaped."""
    live = playing and camera_is_live(stats)
    if stats.error and "download_models.py" in stats.error:
        # the message without the Python error name the frame error starts with, as one sentence
        detail = stats.error.removeprefix("ModelMissingError: ").rstrip(".")
        return (tag("Hand model missing", "bad"),
                f"{esc(detail)}. The camera picks the model up by itself within a few seconds.", live)
    if stats.error:
        return tag("Processing error", "bad"), f"Frame processing error: {esc(stats.error)}", live
    if live:
        return (tag("Camera connected", "ok"),
                f"Receiving {stats.frame_width}x{stats.frame_height} video.", True)
    if playing:
        return (tag("Connecting", "warn"),
                "Waiting for video. If your browser asks for camera access, choose Allow.", False)
    return tag("Camera off", "off"), "Press Start camera and allow access in your browser.", False


def hand_tag(stats: VisionStats, live: bool) -> str:
    """The hand tag beside the camera tag. Nothing unless frames are arriving: just after Stop
    camera the stats still describe the last frame until the page runs again."""
    if not live:
        return ""
    if stats.hand_detected:
        n = stats.num_hands
        return tag(f"{n} hand{'s' if n != 1 else ''} detected", "ok")
    if not stats.error:
        return tag("No hand", "off")
    return ""
