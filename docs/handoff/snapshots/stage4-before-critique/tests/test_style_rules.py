"""Guards for the site design and launch rules.

Rules: no emoji, no em dashes, no gradients, no animations, no pill shapes, no
purple, no "made with AI" badges, a real favicon, and privacy and terms pages in
the navigation. The camera control must stay a single button.
"""
import re
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402

UI_FILES = [ROOT / "ui.py", ROOT / "app.py", *sorted((ROOT / "views").glob("*.py")),
            ROOT / ".streamlit" / "config.toml"]
ALL_PY = [p for p in ROOT.rglob("*.py")
          if ".venv" not in p.parts and "tests" not in p.parts]

EMOJI = re.compile("[\U0001F000-\U0001FAFF←-⇿⌀-⏿■-◿"
                   "☀-➿⬀-⯿️‍]")
ALLOWED_RADII = {"2px", "4px", "6px", "8px", "50%"}


def text(path):
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", UI_FILES, ids=lambda p: p.name)
def test_no_emoji_or_em_dashes(path):
    src = text(path)
    assert not EMOJI.findall(src), f"emoji or decorative symbol in {path.name}"
    assert "—" not in src, f"em dash in {path.name}"


@pytest.mark.parametrize("path", UI_FILES, ids=lambda p: p.name)
def test_no_gradients_animation_or_purple(path):
    src = text(path).lower()
    for banned in ("gradient", "@keyframes", "animation", "999px", "purple", "violet",
                   "indigo", "magenta", "cursor:", "text-shadow", "box-shadow"):
        assert banned not in src, f"'{banned}' found in {path.name}"


def test_corner_radii_are_small():
    css = text(ROOT / "ui.py")
    radii = {v.strip().replace("!important", "").strip()
             for v in re.findall(r"border-radius:\s*([^;]+);", css)}
    assert radii, "expected some border-radius rules"
    assert radii <= ALLOWED_RADII, f"unexpected radii: {radii - ALLOWED_RADII}"
    assert 'baseRadius = "6px"' in text(ROOT / ".streamlit" / "config.toml")


def test_no_ai_attribution_badges_in_code():
    for path in ALL_PY + [ROOT / "README.md"]:
        src = text(path)
        for banned in ("Made with", "Generated with", "AI-generated", "Powered by"):
            assert banned not in src, f"'{banned}' in {path.name}"


def test_favicon_is_a_real_png_and_is_used():
    assert config.FAVICON_PATH.exists()
    data = config.FAVICON_PATH.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    assert width == height and width >= 128
    assert "page_icon=str(config.FAVICON_PATH)" in text(ROOT / "app.py")


def test_legal_pages_exist_and_are_in_navigation():
    app = text(ROOT / "app.py")
    for page in ("views/privacy.py", "views/terms.py"):
        assert page in app
        assert (ROOT / page).exists()
    for page in ("privacy.py", "terms.py"):
        body = text(ROOT / "views" / page)
        for banned in ("TODO", "Lorem", "[Your", "[Company"):
            assert banned not in body


def test_camera_is_one_toggle_button():
    ui = text(ROOT / "ui.py")
    # the component's own Start/Stop is one toggle; hide the rest of its controls
    assert "media_toggle_controls=False" in ui
    assert '"controls": False' in ui                           # no native video control bar
    assert '"start": "Start camera", "stop": "Stop camera"' in ui
    assert "button.MuiButton-text{display:none" in ui        # hides "Select Device"
    assert "unsafe_allow_javascript=True" in ui
    # driving the stream from our own button made the component retry in a tight loop
    # when the camera was denied, so desired_playing_state must not be passed
    assert "desired_playing_state=" not in ui.replace("`desired_playing_state`", "")
    for page in ("dashboard.py", "collector.py"):
        assert "webrtc_streamer" not in text(ROOT / "views" / page)


def test_recording_is_one_toggle_button():
    src = text(ROOT / "views" / "collector.py")
    assert src.count('key="record-toggle"') == 2     # same key, one visible at a time
    assert "if busy:" in src


def test_dashboard_shows_no_invented_numbers():
    src = text(ROOT / "views" / "dashboard.py")
    assert "0%" not in src
    assert '"n/a"' in src                      # no number is shown without a trained model


# ---- the legal pages render ---------------------------------------------------

def run_page(name, monkeypatch, **cfg):
    from streamlit.testing.v1 import AppTest
    for key, value in cfg.items():
        monkeypatch.setattr(config, key, value)
    at = AppTest.from_file(str(ROOT / "views" / name), default_timeout=30)
    at.run()
    return at


@pytest.mark.parametrize("page", ["privacy.py", "terms.py"])
def test_legal_pages_warn_until_operator_is_set(page, monkeypatch):
    at = run_page(page, monkeypatch, OPERATOR_NAME="", CONTACT_EMAIL="", GOVERNING_LAW="")
    assert not at.exception
    assert len(at.warning) == 1 and "Before launch" in at.warning[0].value


@pytest.mark.parametrize("page", ["privacy.py", "terms.py"])
def test_legal_pages_show_contact_once_set(page, monkeypatch):
    at = run_page(page, monkeypatch, OPERATOR_NAME="Example Ltd",
                  CONTACT_EMAIL="legal@example.com", GOVERNING_LAW="the laws of England and Wales")
    assert not at.exception
    assert not at.warning
    body = " ".join(m.value for m in at.markdown)
    assert "legal@example.com" in body
    if page == "terms.py":
        assert "the laws of England and Wales" in body
