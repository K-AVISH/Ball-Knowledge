"""What the pages say about gestures and recordings: one display name per gesture on
every panel, readiness hints that name every shortfall, and recordings named by when
they were made. Data here is hand-made; nothing is measured."""
import sys
import time
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
import data_collector as dc  # noqa: E402
import dataset_manager as dm  # noqa: E402
import features  # noqa: E402
import predictor as pr  # noqa: E402
import ui  # noqa: E402

RECORDS = {
    "meme_3": dm.MemeRecord("meme_3", gesture_name="Meme 3"),
    "meme_4": dm.MemeRecord("meme_4", gesture_name="", ball_knowledge_level="7/10", description="x"),
}


# --- names ------------------------------------------------------------------------

@pytest.mark.parametrize("label, expected", [
    ("meme_3", "Meme 3"),          # gesture_name set
    ("meme_4", "meme_4"),          # record without a name falls back to the id
    ("wave", "wave"),              # no record at all
    ("none", "No gesture"),        # the no-gesture class reads as the recognition panel says it
    (None, ""),
])
def test_display_name(label, expected):
    assert dm.display_name(label, RECORDS) == expected


def test_display_name_without_records_is_the_id():
    assert dm.display_name("meme_3", None) == "meme_3"


def test_recognition_panel_uses_the_same_name_as_the_meme_panel():
    steady = pr.Steady("meme_3", 0.9, 6, 7)
    prediction = pr.Prediction(pr.RECOGNISED, "meme_3", 0.92,
                               (("meme_3", 0.92), ("none", 0.05)), at=time.time())
    html = ui.recognition_card(None, prediction, True, True, [], steady, RECORDS)
    assert ">Meme 3<" in html and ">meme_3<" not in html


def test_checking_state_names_the_gesture_by_its_display_name():
    prediction = pr.Prediction(pr.RECOGNISED, "meme_3", 0.92, (("meme_3", 0.92),), at=time.time())
    html = ui.recognition_card(None, prediction, True, True, [], None, RECORDS)
    assert "Latest frame: Meme 3." in html


def test_history_uses_display_names():
    entries = (pr.HistoryEntry(time.time(), "meme_3", 0.95),)
    assert ">Meme 3<" in ui.history_card(entries, 1, True, RECORDS)


def test_unfinished_lists_memes_without_rating_or_description():
    labels = ["meme_3", "meme_4", "none", "wave"]
    assert dm.unfinished(RECORDS, labels) == ["meme_3"]


# --- readiness hints ------------------------------------------------------------------

def test_a_gesture_short_of_samples_and_recordings_names_both():
    kind, hint = dc.class_status(58, 2)
    assert kind == "bad"
    assert f"{config.TARGET_MIN_PER_CLASS - 58} more samples" in hint
    assert "1 more separate recording" in hint and "recordings" not in hint


def test_short_of_samples_only_does_not_mention_recordings():
    kind, hint = dc.class_status(10, config.MIN_SESSIONS_PER_CLASS)
    assert kind == "bad" and "recording" not in hint


def test_recording_hint_is_plural_when_needed():
    _, hint = dc.class_status(config.TARGET_MIN_PER_CLASS, 0)
    assert hint == f"Record {config.MIN_SESSIONS_PER_CLASS} more separate recordings"


# --- recordings named by time -------------------------------------------------------------

def test_session_times_give_each_recording_its_first_timestamp(tmp_path):
    store = dc.DatasetStore(tmp_path / "samples.csv", tmp_path / "meta.json", "hands")
    n = features.feature_length("hands")
    for sid, stamp in (("aaa111", "2026-10-13T09:55:01"), ("bbb222", "2026-10-14T11:39:24")):
        r = dc.RecordingResult(sid, "meme_3", "", stamp)
        r.samples = [np.zeros(n, dtype=np.float32) for _ in range(3)]
        store.append(r)
    assert store.session_times() == {"aaa111": "2026-10-13T09:55:01",
                                     "bbb222": "2026-10-14T11:39:24"}


def test_session_times_of_an_empty_dataset(tmp_path):
    store = dc.DatasetStore(tmp_path / "samples.csv", tmp_path / "meta.json", "hands")
    assert store.session_times() == {}


# --- saving from the Memes page ---------------------------------------------------------

def _png_bytes(colour=(20, 120, 60)):
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (30, 20), colour).save(buf, format="PNG")
    return buf.getvalue()


def test_save_edit_writes_text_and_copies_the_upload(tmp_path):
    lib = dm.MemeLibrary(tmp_path / "project")
    rec = dm.save_edit(lib, "meme_3", gesture_name="Meme 3", meme_title="Absolute cinema",
                       ball_knowledge_level="9/10", description="Both hands up.",
                       upload_name="cinema.png", upload_bytes=_png_bytes())
    assert rec.image_path == "assets/memes/meme_3.png"
    assert lib.image_problem(rec) is None
    saved = lib.load()["meme_3"]
    assert (saved.meme_title, saved.ball_knowledge_level, saved.description) == (
        "Absolute cinema", "9/10", "Both hands up.")
    assert dm.unfinished(lib.load(), ["meme_3"]) == []


def test_save_edit_without_upload_keeps_the_image_and_can_clear_text(tmp_path):
    lib = dm.MemeLibrary(tmp_path / "project")
    dm.save_edit(lib, "meme_3", gesture_name="Meme 3", meme_title="t", ball_knowledge_level="9/10",
                 description="d", upload_name="a.png", upload_bytes=_png_bytes())
    rec = dm.save_edit(lib, "meme_3", gesture_name="Meme 3", meme_title="", ball_knowledge_level="",
                       description="")
    assert rec.image_path == "assets/memes/meme_3.png" and rec.meme_title == ""
    assert dm.unfinished(lib.load(), ["meme_3"]) == ["meme_3"]


def test_a_bad_upload_saves_nothing_and_names_the_users_file(tmp_path):
    lib = dm.MemeLibrary(tmp_path / "project")
    with pytest.raises(dm.MemeError) as err:
        dm.save_edit(lib, "meme_3", gesture_name="Meme 3", meme_title="t", ball_knowledge_level="9/10",
                     description="d", upload_name="holiday.png", upload_bytes=b"not an image")
    assert "holiday.png" in str(err.value)
    assert lib.load() == {}


def test_text_over_the_limit_saves_nothing(tmp_path):
    lib = dm.MemeLibrary(tmp_path / "project")
    with pytest.raises(dm.MemeError):
        dm.save_edit(lib, "meme_3", gesture_name="x", meme_title="t",
                     ball_knowledge_level="9" * (dm.MAX_TEXT["ball_knowledge_level"] + 1),
                     description="")
    assert lib.load() == {}


def test_memes_page_is_in_the_navigation():
    app = (Path(__file__).resolve().parents[1] / "app.py").read_text()
    assert 'st.Page("views/memes.py"' in app


# --- contrast ---------------------------------------------------------------------------

def _luminance(rgb):
    def f(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def test_confusion_matrix_numbers_keep_aa_contrast_on_the_darkest_cells():
    import re
    html = ui.confusion_table(["a", "b"], [[10, 0], [5, 5]])
    alphas = [float(a) for a in re.findall(r"rgba\(\d+,\d+,\d+,([0-9.]+)\)", html)]
    assert max(alphas) <= 0.55
    surface2, text = (0x15, 0x1d, 0x19), (0xe6, 0xec, 0xe8)
    for colour in ((47, 191, 113), (229, 100, 95)):
        cell = tuple(round(c * max(alphas) + s * (1 - max(alphas))) for c, s in zip(colour, surface2))
        hi, lo = sorted([_luminance(text), _luminance(cell)], reverse=True)
        assert (hi + 0.05) / (lo + 0.05) >= 4.5


# --- meme image size on the dashboard ----------------------------------------------------

def test_large_meme_images_are_shrunk_for_display_but_not_on_disk(tmp_path):
    from PIL import Image
    path = tmp_path / "big.png"
    Image.effect_noise((2400, 1600), 60).convert("RGB").save(path)
    before = path.read_bytes()
    uri = ui._data_uri(str(path), path.stat().st_mtime_ns)
    assert uri.startswith("data:image/jpeg;base64,")
    assert len(uri) < len(before)
    assert path.read_bytes() == before


def test_small_meme_images_are_sent_unchanged(tmp_path):
    import base64
    from PIL import Image
    path = tmp_path / "small.png"
    Image.new("RGB", (200, 150), (10, 90, 40)).save(path)
    uri = ui._data_uri(str(path), path.stat().st_mtime_ns)
    assert uri == "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def test_oversized_uploads_are_refused_before_anything_is_written(tmp_path):
    lib = dm.MemeLibrary(tmp_path / "project")
    big = b"0" * (config.MEME_MAX_UPLOAD_MB * 1024 * 1024 + 1)
    with pytest.raises(dm.MemeError, match="larger than"):
        dm.save_edit(lib, "meme_3", gesture_name="", meme_title="", ball_knowledge_level="",
                     description="", upload_name="huge.png", upload_bytes=big)
    assert lib.load() == {}
