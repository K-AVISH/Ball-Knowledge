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
.stApp .page-desc { color: var(--muted); margin: .35rem 0 1.5rem 0; max-width: 64ch; }

/* cards */
.card, [data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--surface) !important; border: 1px solid var(--border) !important;
  border-radius: 8px !important; }
.card { padding: 1rem 1.2rem; margin-bottom: 1rem; }
.stApp .card h2, .stApp h2.ctitle { margin: 0 0 .7rem 0; padding: 0; font-size: .74rem; text-transform: uppercase;
  letter-spacing: .1em; color: var(--muted); font-weight: 650; line-height: 1.4; }
/* section titles are real h2 headings; hide the link icon Streamlit adds to headings */
[data-testid="stHeaderActionElements"] { display: none !important; }
[data-testid="stVerticalBlockBorderWrapper"] > div { padding-bottom: .3rem; }

/* status tags (labels, not buttons) */
.tag { display: inline-block; padding: .15rem .55rem; border-radius: 4px; font-size: .78rem;
       font-weight: 600; border: 1px solid var(--border); margin: 0 .4rem .3rem 0; }
.tag.ok   { color: var(--accent); border-color: rgba(47,191,113,.45); background: rgba(47,191,113,.08); }
.tag.warn { color: var(--warn);   border-color: rgba(224,176,74,.4);  background: rgba(224,176,74,.08); }
.tag.bad  { color: var(--bad);    border-color: rgba(229,100,95,.4);  background: rgba(229,100,95,.08); }
.tag.off  { color: var(--muted);  background: var(--surface2); }
.stApp .hint { color: var(--muted); font-size: .88rem; margin: .4rem 0 0 0; }

/* stat tiles */
.tiles { display: grid; grid-template-columns: repeat(2, 1fr); gap: .7rem; margin-bottom: 1rem; }
.tiles.four { grid-template-columns: repeat(4, 1fr); }
.tiles.three { grid-template-columns: repeat(3, 1fr); margin-bottom: 0; }
@media (max-width: 720px) { .tiles.four, .tiles.three { grid-template-columns: repeat(2, 1fr); } }
.card .tile { background: var(--surface2); }
.tile { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: .8rem 1rem; }
.tile.wide { grid-column: 1 / -1; }
.tile .k { font-size: .7rem; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); font-weight: 650; }
.tile .v { font-size: 1.5rem; font-weight: 650; margin-top: .15rem; color: var(--text);
           font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.tile.worded .v { font-size: 1.15rem; line-height: 1.3; margin-top: .3rem; }
.tile .note { color: var(--muted); font-size: .8rem; font-variant-numeric: tabular-nums; }
.tile .v small { font-size: .8rem; color: var(--muted); font-weight: 500; margin-left: .2rem; }

/* recognition and empty states */
.big { font-size: 1.5rem; font-weight: 650; line-height: 1.2; margin: .2rem 0 0 0; overflow-wrap: anywhere; }
.big.ok { color: var(--accent); }
.conf { position: relative; height: 8px; border-radius: 2px; background: #1b2620; margin: .7rem 0 .3rem 0; }
.conf .fill { height: 100%; border-radius: 2px; background: var(--accent); }
.conf .fill.warn { background: var(--warn); }
.conf .mark { position: absolute; top: -3px; width: 2px; height: 14px; background: var(--text); }
.conf-row { display: flex; justify-content: space-between; gap: .8rem; font-size: .82rem;
            color: var(--muted); font-variant-numeric: tabular-nums; }
.conf-row b { color: var(--text); }
.gap { height: .9rem; }
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
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

/* meme result */
.meme-img { display: block; width: 100%; max-height: 340px; object-fit: contain; border-radius: 6px;
  background: var(--surface2); margin: 0 0 .8rem 0; }
.meme-desc { color: var(--text); margin: .5rem 0 0 0; line-height: 1.5; }

/* legal pages */
.legal { max-width: 70ch; }
.legal h2 { font-size: 1.1rem; margin: 1.6rem 0 .4rem 0; }
.legal p, .legal li { color: #c9d3cd; line-height: 1.6; }

/* controls: small radius, no pills */
.stButton button { border-radius: 6px !important; font-weight: 600 !important; }
[data-testid="stProgress"] > div, [data-testid="stProgress"] div[role="progressbar"],
[data-testid="stProgress"] div[role="progressbar"] > div { border-radius: 2px !important; }
iframe { border-radius: 6px; }
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
    body = "".join(
        "<tr>" + "".join(
            (f'<th scope="row">{esc(c)}</th>' if i == 0 else
             f'<td class="{"num" if i >= numeric_from else ""}">{esc(c)}</td>')
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
    """(predictor, None) when the saved model is usable, otherwise (None, the reason)."""
    files = (config.MODEL_PATH, config.LABELS_PATH, config.REPORT_PATH)
    try:
        return _cached_predictor(*(str(p) for p in files), tuple(_mtime(p) for p in files),
                                 config.FEATURE_MODE, config.DEFAULT_CONFIDENCE_THRESHOLD,
                                 config.TOP_PREDICTIONS), None
    except pr.PredictorError as exc:
        return None, exc


def model_state(problem: Optional[pr.PredictorError], stale: "list[str]") -> "tuple[str, str]":
    """(short label, tag kind) for the model: not trained, cannot load, retrain needed, loaded."""
    if isinstance(problem, pr.NotTrainedError):
        return "Not trained", "off"
    if problem is not None:
        return "Cannot load", "bad"
    if stale:
        return "Retrain needed", "warn"
    return "Loaded", "ok"


def confidence_bar(confidence: float, threshold: float, accepted: bool) -> str:
    """A flat bar for the confidence with a marker at the threshold, plus both numbers."""
    fill = max(0, min(100, round(confidence * 100)))
    mark = max(0, min(99, round(threshold * 100)))
    return (f'<div class="conf" role="img" aria-label="Confidence {score_pct(confidence)}, '
            f'threshold {pct(threshold)}"><div class="fill {"" if accepted else "warn"}" '
            f'style="width:{fill}%"></div><div class="mark" style="left:{mark}%"></div></div>'
            f'<div class="conf-row"><span>Confidence <b>{score_pct(confidence)}</b></span>'
            f'<span>Threshold {pct(threshold)}</span></div>')


def recognition_card(problem: Optional[pr.PredictorError], prediction: Optional[pr.Prediction],
                     playing: bool, live: bool, stale: "list[str]",
                     steady: Optional[pr.Steady] = None,
                     records: Optional[Dict[str, dm.MemeRecord]] = None) -> str:
    """HTML for the recognition panel. Each state has its own tag and wording. A gesture
    name only appears as the result once it is steady (LiveRecognizer.steady), so a
    single frame neither shows a gesture nor hides one that is being held. `records`
    (memes.json) supplies the gesture names, so this panel and the meme panel agree."""
    def name(label: Optional[str]) -> str:
        return esc(dm.display_name(label, records))

    tags, model_tags = [], []
    model_label, model_kind = model_state(problem, stale)
    if model_kind in ("bad", "warn"):
        model_tags.append(tag(model_label, model_kind))     # e.g. Retrain needed, after the result
    detail, scores_title, recognised = "", "", False
    if isinstance(problem, pr.NotTrainedError):
        model_tags = [tag("Not trained", "off")]
        headline = "No trained model"
        hint = (f"Record at least 2 gestures on the {link('collector', 'Data collector')} page, "
                f"then train a model on the {link('performance', 'Model performance')} page. "
                "Recognition starts here once a model exists.")
    elif problem is not None:
        headline = "Model cannot be used"
        hint = f"{esc(problem)} Training runs on the {link('performance', 'Model performance')} page."
    elif not live and not playing:
        tags.append(tag("Camera off", "off"))
        headline = "Waiting for the camera"
        hint = "Press Start camera. Gestures are recognised while the camera is on."
    elif not live:
        tags.append(tag("Connecting", "off"))
        headline = "Waiting for video"
        hint = "Recognition starts as soon as video arrives. If your browser asks for camera access, choose Allow."
    elif not pr.is_fresh(prediction):
        tags.append(tag("Starting", "off"))
        headline = "Waiting for the first prediction"
        hint = "The model is classifying the first frames."
    elif prediction.status == pr.ERROR:
        tags.append(tag("Prediction error", "bad"))
        headline = "Prediction failed"
        hint = esc(prediction.error)
    elif steady is not None and steady.label == config.NONE_LABEL:
        tags.append(tag("No gesture", "off"))
        headline = "No gesture"
        hint = "The model sees a hand but none of your gestures."
    elif steady is not None:
        tags.append(tag("Recognised", "ok"))
        headline, recognised = name(steady.label), True
        hint = (f"Recognised in {steady.votes} of the last {steady.frames} frames. Confidence is "
                "the average over those frames, the model's own estimate, not a calibrated "
                "probability.")
        detail = confidence_bar(steady.confidence, prediction.threshold, True)
        scores_title = "Scores in the latest frame"
    elif prediction.status == pr.NO_HAND:
        tags.append(tag("No hand", "off"))
        headline = "No hand detected"
        hint = "Show one of your trained gestures to the camera."
    elif prediction.status == pr.UNRECOGNISED:
        tags.append(tag("Unrecognised", "warn"))
        headline = "Unrecognised"
        hint = (f"The highest score, {score_pct(prediction.confidence)}, is below the "
                f"{pct(prediction.threshold)} threshold, so no gesture is shown.")
        detail = confidence_bar(prediction.confidence, prediction.threshold, False)
        scores_title = "Scores in this frame, none high enough to count"
    else:                                   # recognised in this frame, not yet steady
        tags.append(tag("Checking", "off"))
        headline = "Checking"
        hint = (f"Latest frame: {name(prediction.label)}. It becomes the result once it is "
                f"recognised in {config.MIN_STABLE_FRAMES} of the last "
                f"{config.SMOOTHING_WINDOW} frames.")
        detail = confidence_bar(prediction.confidence, prediction.threshold, True)
        scores_title = "Scores in this frame"

    body = (f'<div>{"".join(tags + model_tags)}</div>'
            f'<div class="big{" ok" if recognised else ""}">{headline}</div>'
            f'{detail}<p class="hint">{hint}</p>')
    if scores_title and prediction.top:
        body += ('<div class="gap"></div>'
                 + html_table(["Gesture", "Score"],
                              [[dm.display_name(g, records), score_pct(p)] for g, p in prediction.top],
                              caption=f"{scores_title}."))
    if stale and problem is None:
        body += ('<p class="hint">' + " ".join(esc(s) for s in stale)
                 + f" Retrain on the {link('performance', 'Model performance')} page.</p>")
    return f'<div class="card"><h2>Recognition</h2>{body}</div>'


# ---------------------------------------------------------------------------
# Meme result
# ---------------------------------------------------------------------------

_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
         ".gif": "image/gif"}


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
                too_big = (max(img.size) > config.MEME_DISPLAY_MAX_PX
                           or len(raw) > config.MEME_DISPLAY_MAX_KB * 1024)
                if too_big:
                    img = img.copy()
                    img.thumbnail((config.MEME_DISPLAY_MAX_PX, config.MEME_DISPLAY_MAX_PX))
                    out = io.BytesIO()
                    if img.mode in ("RGBA", "LA", "P"):
                        img.save(out, format="PNG", optimize=True)
                        mime = "image/png"
                    else:
                        img.convert("RGB").save(out, format="JPEG", quality=85)
                        mime = "image/jpeg"
                    return f"data:{mime};base64,{base64.b64encode(out.getvalue()).decode('ascii')}"
        except Exception:            # unreadable here: image_problem() has already vetted it
            pass
    return f"data:{_MIME[suffix]};base64,{base64.b64encode(raw).decode('ascii')}"


def meme_card(label: Optional[str], records: Optional[Dict[str, dm.MemeRecord]],
              load_error: Optional[str], library: dm.MemeLibrary) -> str:
    """HTML for the meme panel. `label` is the steady gesture (LiveRecognizer.stable) or
    None. A meme is only shown for a steady gesture with a readable image."""
    def card(body: str) -> str:
        return f'<div class="card"><h2>Meme result</h2>{body}</div>'

    def empty(title: str, text: str) -> str:
        return card(f'<div class="empty"><b>{title}</b>{text}</div>')

    if load_error:
        return card(f'<div>{tag("Meme list unreadable", "bad")}</div>'
                    f'<div class="big">Memes cannot be shown</div><p class="hint">{esc(load_error)} '
                    "Fix assets/memes/memes.json by hand. The Memes page cannot edit it until it "
                    "can be read.</p>")
    if label is None:
        return empty("No meme yet",
                     f"A meme appears when a trained gesture is recognised in at least "
                     f"{config.MIN_STABLE_FRAMES} of the last {config.SMOOTHING_WINDOW} frames.")
    if label == config.NONE_LABEL:
        return empty("No gesture", "The model sees a hand but no gesture, so no meme is shown.")
    record = (records or {}).get(label)
    if record is None:
        return card(f'<div>{tag("No meme set", "warn")}</div><div class="big">{esc(label)}</div>'
                    f'<p class="hint">This gesture has no meme yet. Add one on the '
                    f"{link('memes', 'Memes')} page, or with "
                    f"<code>python dataset_manager.py {esc(label)} --image &lt;file&gt;</code>.</p>")
    problem = library.image_problem(record)
    if problem:
        return card(f'<div>{tag("Image missing", "bad")}</div><div class="big">{esc(record.title)}</div>'
                    f'<p class="hint">{esc(problem)} Choose the image again on the '
                    f"{link('memes', 'Memes')} page.</p>")

    path = library.image_file(record)
    uri = _data_uri(str(path), path.stat().st_mtime_ns)
    rating = (f"Ball Knowledge: {esc(record.ball_knowledge_level)}" if record.ball_knowledge_level
              else "Ball Knowledge rating not set")
    description = (f'<p class="meme-desc">{esc(record.description)}</p>' if record.description
                   else '<p class="hint">No description set.</p>')
    return card(
        f'<img class="meme-img" src="{uri}" alt="{esc("Meme: " + record.title)}">'
        f'<div>{tag(esc(record.gesture_name or label), "ok")}'
        f'{tag(rating, "off" if not record.ball_knowledge_level else "ok")}</div>'
        f'<div class="big">{esc(record.title)}</div>{description}'
        f'<p class="hint">The rating and description are yours, set on the {link("memes", "Memes")} '
        "page. The model only recognises the gesture.</p>")


# ---------------------------------------------------------------------------
# Recent detections and session statistics
# ---------------------------------------------------------------------------

def clock(at: float) -> str:
    """time.time() -> '14:05:09' in local time."""
    return time.strftime("%H:%M:%S", time.localtime(at))


def history_card(entries: "tuple[pr.HistoryEntry, ...]", total: int, model_ready: bool,
                 records: Optional[Dict[str, dm.MemeRecord]] = None) -> str:
    """HTML for the recent detections panel, newest first. Entries come from
    predictor.DetectionLog, which adds one per change of steady gesture, not per frame."""
    def card(body: str) -> str:
        return f'<div class="card"><h2>Recent detections</h2>{body}</div>'

    if not entries:
        text = ("Each gesture you show is listed here with its time and confidence."
                if model_ready else "Recognition starts once a model is trained.")
        return card(f'<div class="empty"><b>Nothing detected yet</b>{text}</div>')
    shown = (f"Newest first, {len(entries)} of {total} this session."
             if total > len(entries) else "Newest first.")
    rows = [[clock(e.at), dm.display_name(e.label, records), score_pct(e.confidence)] for e in entries]
    return card(html_table(["Time", "Gesture", "Confidence"], rows, numeric_from=2,
                           caption=shown)
                + '<p class="hint">A gesture is added when it becomes the result, and again only '
                f"after another gesture or a pause of over {config.HISTORY_REPEAT_GAP_S:g} seconds. "
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
    "button.MuiButton-text{display:none !important}"          # the Select Device button
    "button{text-transform:none !important;letter-spacing:0 !important;"
    "border-radius:6px !important;font-weight:600 !important}"
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
        # Browser and server are on the same machine, so no STUN server is needed.
        # Without these, the library asks Google's STUN server and the camera fails offline.
        frontend_rtc_configuration={"iceServers": []},
        server_rtc_configuration={"iceServers": []},
    )
    st.html(_IFRAME_SCRIPT, unsafe_allow_javascript=True)
    return ctx


def camera_state(stats: VisionStats, playing: bool) -> "tuple[str, str, bool]":
    """Returns (status tag html, hint text, is_live)."""
    live = playing and camera_is_live(stats)
    if stats.error and "download_models.py" in stats.error:
        return (tag("Hand model missing", "bad"),
                f"{stats.error} Then stop and restart the camera.", live)
    if stats.error:
        return tag("Processing error", "bad"), f"Frame processing error: {stats.error}", live
    if live:
        return (tag("Camera connected", "ok"),
                f"Receiving {stats.frame_width}x{stats.frame_height} video.", True)
    if playing:
        return (tag("Connecting", "warn"),
                "Waiting for video. If your browser asks for camera access, choose Allow.", False)
    return tag("Camera off", "off"), "Press Start camera and allow access in your browser.", False


def hand_tag(stats: VisionStats, live: bool) -> str:
    if stats.hand_detected:
        n = stats.num_hands
        return tag(f"{n} hand{'s' if n != 1 else ''} detected", "ok")
    if live and not stats.error:
        return tag("No hand", "off")
    return ""
