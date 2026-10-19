"""Shared UI pieces: styling, small HTML helpers, the per-session vision objects
and the camera widget used by every page that shows the webcam."""
from __future__ import annotations

import html

import av
import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer

import config
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

/* page header */
.brand { font-size: .78rem; letter-spacing: .08em; text-transform: uppercase;
         color: var(--muted); margin: 0 0 .3rem 0; }
.page-title { font-size: 1.75rem; font-weight: 650; margin: 0; color: var(--text); }
.page-desc { color: var(--muted); margin: .35rem 0 1.5rem 0; max-width: 64ch; }

/* cards */
.card, [data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--surface) !important; border: 1px solid var(--border) !important;
  border-radius: 8px !important; }
.card { padding: 1rem 1.2rem; margin-bottom: 1rem; }
.card h3, .ctitle { margin: 0 0 .7rem 0; font-size: .74rem; text-transform: uppercase;
  letter-spacing: .1em; color: var(--muted); font-weight: 650; }
[data-testid="stVerticalBlockBorderWrapper"] > div { padding-bottom: .3rem; }

/* status tags (labels, not buttons) */
.tag { display: inline-block; padding: .15rem .55rem; border-radius: 4px; font-size: .78rem;
       font-weight: 600; border: 1px solid var(--border); margin: 0 .4rem .3rem 0; }
.tag.ok   { color: var(--accent); border-color: rgba(47,191,113,.45); background: rgba(47,191,113,.08); }
.tag.warn { color: var(--warn);   border-color: rgba(224,176,74,.4);  background: rgba(224,176,74,.08); }
.tag.bad  { color: var(--bad);    border-color: rgba(229,100,95,.4);  background: rgba(229,100,95,.08); }
.tag.off  { color: var(--muted);  background: var(--surface2); }
.hint { color: var(--muted); font-size: .88rem; margin: .4rem 0 0 0; }

/* stat tiles */
.tiles { display: grid; grid-template-columns: repeat(2, 1fr); gap: .7rem; margin-bottom: 1rem; }
.tile { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: .8rem 1rem; }
.tile .k { font-size: .7rem; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); font-weight: 650; }
.tile .v { font-size: 1.5rem; font-weight: 650; margin-top: .15rem; color: var(--text);
           font-variant-numeric: tabular-nums; }
.tile .v small { font-size: .8rem; color: var(--muted); font-weight: 500; margin-left: .2rem; }

/* recognition and empty states */
.big { font-size: 1.5rem; font-weight: 650; line-height: 1.2; }
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

/* tables */
.tbl { width: 100%; border-collapse: collapse; font-size: .88rem; }
.tbl th { text-align: left; color: var(--muted); font-size: .72rem; letter-spacing: .08em;
          text-transform: uppercase; font-weight: 650; padding: .45rem .6rem;
          border-bottom: 1px solid var(--border); }
.tbl td { padding: .5rem .6rem; border-bottom: 1px solid var(--border); color: var(--text); }
.tbl .num { text-align: right; font-variant-numeric: tabular-nums; }
.tbl tr:last-child td { border-bottom: none; }
.cm { border-collapse: separate; border-spacing: 3px; width: 100%; font-size: .85rem; }
.cm th { color: var(--muted); font-weight: 600; padding: .3rem .4rem; font-size: .75rem; }
.cm th.row { text-align: right; white-space: nowrap; }
.cm td { text-align: center; padding: .55rem .3rem; border-radius: 4px; background: var(--surface2);
         font-variant-numeric: tabular-nums; color: var(--text); }
.cm-axis { color: var(--muted); font-size: .78rem; margin: .5rem 0 0 0; }

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


def tile(label: str, value: str, unit: str = "") -> str:
    small = f"<small>{unit}</small>" if unit else ""
    return (f'<div class="tile"><div class="k">{label}</div>'
            f'<div class="v">{value}{small}</div></div>')


def esc(value) -> str:
    """HTML-escape anything that came from data (gesture names, file contents)."""
    return html.escape(str(value))


def html_table(headers: "list[str]", rows: "list[list]", numeric_from: int = 1) -> str:
    """A flat table. Columns from index `numeric_from` onward are right-aligned numbers."""
    head = "".join(f'<th class="{"num" if i >= numeric_from else ""}">{esc(h)}</th>'
                   for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(f'<td class="{"num" if i >= numeric_from else ""}">{esc(c)}</td>'
                         for i, c in enumerate(row)) + "</tr>"
        for row in rows)
    return f'<table class="tbl"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def confusion_table(labels: "list[str]", matrix: "list[list[int]]") -> str:
    """Confusion matrix as an HTML heatmap. Rows are the true gesture, columns the prediction.
    Shading shows each cell's share of its row: green on the diagonal, red for mistakes."""
    head = "<th></th>" + "".join(f"<th>{esc(l)}</th>" for l in labels)
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
            cells.append(f'<td style="background:rgba({rgb},{0.15 + 0.6 * share:.2f})">{count}</td>')
        rows.append(f'<tr><th class="row">{esc(label)}</th>{"".join(cells)}</tr>')
    return (f'<table class="cm"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>'
            '<p class="cm-axis">Rows: true gesture. Columns: what the model predicted.</p>')


def get_vision() -> "tuple[FrameProcessor, LandmarkHook]":
    """One processor and landmark hook per browser session, shared by all pages.
    The video thread writes to them; the UI only reads."""
    if "processor" not in st.session_state:
        st.session_state.landmark_hook = LandmarkHook()
        st.session_state.processor = FrameProcessor(frame_hook=st.session_state.landmark_hook)
    return st.session_state.processor, st.session_state.landmark_hook


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
