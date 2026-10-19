"""The pages as Streamlit runs them (AppTest), on a small synthetic project in a temporary
folder: samples, a model trained on them and a memes.json with gesture names. The camera
widget needs a browser, so the collector page runs with a stand-in that reports the camera
as off. These tests check what the pages say, not how well any model recognises gestures."""
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
import data_collector as dc  # noqa: E402
import dataset_manager as dm  # noqa: E402
import features  # noqa: E402
import train_model as tm  # noqa: E402
import ui  # noqa: E402

N = features.feature_length("hands")
NAMES = {"first_meme": "First meme", "second_meme": "Second meme"}


def _picture(path):
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (40, 30), (20, 120, 60)).save(path)
    return path


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    """first_meme has 2 recordings (so training warns about it), the others 3."""
    root = tmp_path_factory.mktemp("project")
    store = dc.DatasetStore(root / "samples.csv", root / "meta.json", "hands")
    rng = np.random.default_rng(0)
    for label, sessions in (("first_meme", 2), ("second_meme", 3), (config.NONE_LABEL, 3)):
        centre = rng.normal(size=N) * 3
        for s in range(sessions):
            r = dc.RecordingResult(f"{label}-{s}", label, "", f"2026-10-14T11:3{s}:00")
            r.samples = [(centre + rng.normal(size=N) * 0.5).astype(np.float32) for _ in range(12)]
            store.append(r)
    paths = dict(model_path=root / "m" / "model.joblib", labels_path=root / "m" / "labels.json",
                 report_path=root / "m" / "report.json")
    report = tm.train(store=store, **paths)
    lib = dm.MemeLibrary(root / "app")
    for gid, name in NAMES.items():
        lib.update(gid, image=_picture(root / f"{gid}.png"), gesture_name=name)
    return SimpleNamespace(root=root, store=store, report=report, lib=lib, **paths)


@pytest.fixture
def run(project, monkeypatch):
    """run('performance.py') -> the AppTest after one run, on the synthetic project."""
    from streamlit.testing.v1 import AppTest
    monkeypatch.setattr(dc, "DatasetStore", lambda *a, **k: project.store)
    monkeypatch.setattr(dm, "MemeLibrary", lambda *a, **k: project.lib)
    monkeypatch.setattr(config, "REPORT_PATH", project.report_path)
    monkeypatch.setattr(config, "MODEL_PATH", project.model_path)
    monkeypatch.setattr(config, "LABELS_PATH", project.labels_path)
    camera_off = SimpleNamespace(state=SimpleNamespace(playing=False))
    monkeypatch.setattr(ui, "camera_widget", lambda key, processor: camera_off)

    def go(page):
        at = AppTest.from_file(str(ROOT / "views" / page), default_timeout=60)
        at.run()
        assert not at.exception, at.exception
        return at
    return go


def page_text(at):
    return " ".join([m.value for m in at.markdown] + [w.value for w in at.warning]
                    + [c.value for c in at.caption])


# --- one name per gesture on every page ---------------------------------------------------

def test_collector_lists_each_gesture_by_its_name_and_id(run):
    at = run("collector.py")
    text = page_text(at)
    assert '<div class="n">First meme <span class="m">first_meme</span></div>' in text
    assert '<div class="n">No gesture <span class="m">none</span></div>' in text
    assert at.selectbox[0].options[:3] == ["First meme (first_meme)", "No gesture (none)",
                                           "Second meme (second_meme)"]


def test_performance_cautions_name_gestures_as_the_tables_do(run):
    warnings = " ".join(w.value for w in run("performance.py").warning)
    assert "Fewer than 3 recordings for: First meme." in warnings
    assert "first_meme" not in warnings


def test_cautions_without_names_are_the_saved_ones(project):
    assert tm.make_warnings(project.report) == project.report["warnings"]


# --- the Memes page states what it enforces ---------------------------------------------

def test_upload_box_states_the_same_limit_that_saving_enforces():
    settings = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text())
    assert settings["server"]["maxUploadSize"] == config.MEME_MAX_UPLOAD_MB


def test_the_app_listens_on_this_computer_only():
    """Without server.address Streamlit also listens on the local network ("Network URL"), and
    no page has a sign-in: anyone on the same Wi-Fi could delete gesture data, retrain the model
    or replace memes. The camera only works on localhost anyway."""
    settings = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text())
    assert settings["server"]["address"] == "localhost"


def test_an_unreadable_image_is_explained_without_a_python_error_name(tmp_path):
    fake = tmp_path / "holiday.png"
    fake.write_text("not an image")
    problem = dm.image_file_problem(fake)
    assert problem.startswith("holiday.png cannot be read as an image.")
    assert "Error" not in problem and "JPG" in problem


def test_memes_page_shows_whether_each_title_is_set(run):
    text = page_text(run("memes.py"))
    assert '<th scope="col" class="">Title</th>' in text
    assert "No gesture (the none gesture)" in text


def test_meme_panel_shows_the_image_and_no_name_when_no_title_is_set(project):
    html = ui.meme_card("first_meme", project.lib.load(), None, project.lib)
    assert '<img class="meme-img"' in html and ">First meme<" not in html


# --- panels and spacing (seen in the browser; these keep the code that does it) -----------

def test_pages_draw_bordered_panels_through_ui_panel():
    for page in (ROOT / "views").glob("*.py"):
        assert "st.container(border=True)" not in page.read_text(), page.name
    assert '[class*="st-key-panel-"]' in ui.CSS
    assert "stVerticalBlockBorderWrapper" not in ui.CSS     # not in Streamlit 1.65, so it styled nothing


def test_ui_panel_keys_the_container_so_the_css_can_find_it(monkeypatch):
    calls = []
    monkeypatch.setattr(ui.st, "container", lambda **kw: calls.append(kw) or "panel")
    assert ui.panel("camera") == "panel"
    assert calls == [{"border": True, "key": "panel-camera"}]


def test_text_that_ends_a_block_gets_its_bottom_margin_back():
    assert ":is(p.hint, p.cm-axis, .empty, ul.tips):last-child" in ui.CSS


def test_both_dashboard_rows_use_the_same_column_split():
    src = (ROOT / "views" / "dashboard.py").read_text()
    assert src.count("st.columns([3, 2]") == 2


def test_the_camera_frame_lets_the_panel_colour_show():
    assert "html,body{background:transparent" in ui._IFRAME_CSS


def _contrast(a, b):
    def lum(hex_colour):
        r, g, b = (int(hex_colour.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
        f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
    hi, lo = sorted([lum(a), lum(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_text_boxes_have_an_outline_that_stands_out_on_a_panel():
    # The panels and Streamlit's text boxes share the fill #111815, so the box is seen by
    # its outline. WCAG asks for 3:1 for the edge of a control.
    theme = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text())["theme"]
    assert theme["showWidgetBorder"] is True
    assert theme["secondaryBackgroundColor"] == "#111815" and "--surface:#111815" in ui.CSS
    assert _contrast(theme["borderColor"], "#111815") >= 3.0


# --- the result first ----------------------------------------------------------------------

def test_performance_cautions_share_one_box(run):
    warnings = run("performance.py").warning
    assert len(warnings) == 1
    assert warnings[0].value.startswith("Read these results with care:")
    assert "\n- Fewer than 3 recordings for: First meme." in warnings[0].value


def test_beside_the_camera_the_dashboard_shows_only_the_meme_panel():
    src = (ROOT / "views" / "dashboard.py").read_text()
    assert src.count("ui.result_card(") == 1
    for gone in ("recognition_card", "scores_card", "ui.meme_card(", "dm.unfinished"):
        assert gone not in src                  # no gesture names, no score table, no nagging
    assert not hasattr(ui, "recognition_card") and not hasattr(ui, "scores_card")


def test_the_stats_and_history_show_memes_by_picture():
    src = (ROOT / "views" / "dashboard.py").read_text()
    assert 'tile("Latest meme", ui.meme_thumb(latest.label, memes, meme_library)' in src
    assert "ui.history_card(history, total, model is not None, memes, meme_library)" in src
    assert ".meme-frame { aspect-ratio: 4/3;" in ui.CSS          # one frame size for every state


# --- contrast and keyboard focus (measured in the browser; these keep the fixes) ----------

def test_green_buttons_have_dark_text_that_passes_aa():
    assert '[data-testid^="stBaseButton-primary"]' in ui.CSS and "color: var(--bg) !important" in ui.CSS
    assert _contrast("#0b0f0d", "#2fbf71") >= 4.5          # --bg on --accent
    assert _contrast("#ffffff", "#2fbf71") < 4.5           # why: Streamlit's white text fails


def test_camera_button_shows_keyboard_focus():
    assert "button:focus-visible{outline:2px solid #2fbf71" in ui._IFRAME_CSS
    assert _contrast("#2fbf71", "#111815") >= 3.0          # the ring against the panel


def test_the_scrolling_page_area_shows_keyboard_focus():
    assert '[data-testid="stMain"]:focus-visible { outline: 2px solid var(--accent)' in ui.CSS


def test_checkboxes_show_keyboard_focus():
    """Streamlit keeps the real checkbox in a 1 px clipped box, so its own focus ring never
    shows (Show landmarks overlay, the delete confirmation). The visible box gets the ring."""
    assert ('[data-testid="stCheckbox"] label:has(input:focus-visible) > div:first-of-type {\n'
            "  outline: 2px solid var(--accent)") in ui.CSS
    assert _contrast("#2fbf71", "#111815") >= 3.0          # the ring against the panel


def test_the_closed_page_menu_takes_no_keyboard_focus():
    """In a narrow window (a phone, or 200% zoom) the page links move into a menu that
    Streamlit slides off screen when closed. Tab still stopped on its six links, out of view,
    and on phones on its close button too, which Streamlit marks visible itself."""
    assert ('.stApp [data-testid="stSidebar"][aria-expanded="false"],\n'
            '.stApp [data-testid="stSidebar"][aria-expanded="false"] * { visibility: hidden; }') in ui.CSS


def test_the_landmarks_overlay_box_changes_at_every_click(run):
    """Its default is the camera's current setting. Without a key, a new default made
    Streamlit see a new checkbox, so every second click was lost (seen in the browser)."""
    at = run("dashboard.py")

    def overlay():
        return next(c for c in at.checkbox if c.label == "Show landmarks overlay")
    assert overlay().value is True
    for want in (False, True, False, True):
        overlay().set_value(want).run()
        assert overlay().value is want
        assert at.session_state["landmark_hook"].show_landmarks is want


def test_the_dashboard_meme_panel_reports_a_camera_problem(run, monkeypatch):
    """Owner decision Q1 (B): while frames fail (here the hand model is missing), the Meme panel
    says Camera problem, as the camera panel beside it says Hand model missing."""
    import time
    from streamlit.testing.v1 import AppTest
    import vision
    camera_on = SimpleNamespace(state=SimpleNamespace(playing=True))
    monkeypatch.setattr(ui, "camera_widget", lambda key, processor: camera_on)
    hook = vision.LandmarkHook(detector_factory=lambda: None)
    processor = vision.FrameProcessor(frame_hook=hook)
    processor._stats.error = ("ModelMissingError: Hand model not found at /x/hand_landmarker.task. "
                              "Run: python download_models.py")
    processor._stats.last_frame_time = time.time() + 60    # still live when the page reads it
    at = AppTest.from_file(str(ROOT / "views" / "dashboard.py"), default_timeout=60)
    at.session_state["processor"], at.session_state["landmark_hook"] = processor, hook
    at.run()
    assert not at.exception, at.exception
    text = page_text(at)
    assert "Hand model missing" in text and "<b>Camera problem</b>" in text
    assert "<b>Starting</b>" not in text


def test_the_overlay_explains_itself_under_the_box_not_in_a_help_icon(run):
    """Proposal PR-10 (B). Streamlit puts a checkbox's help icon inside its label, so a click on
    the icon also turned the overlay on or off."""
    at = run("dashboard.py")
    box = next(c for c in at.checkbox if c.label == "Show landmarks overlay")
    assert not box.help
    assert '<p class="hint">Draw the detected hand skeleton on the video.</p>' in page_text(at)


def test_a_disabled_green_button_keeps_readable_text():
    """Train model is disabled while a run is going, and Start recording until a gesture is
    named. Disabled, the button has no green fill, so the dark text must not apply."""
    rule = ui.CSS.split("color: var(--bg) !important")[0].rsplit("*/", 1)[1]
    assert rule.count(':not(:disabled)') == 2


def test_green_buttons_keep_aa_contrast_when_hovered():
    assert ':is(:hover, :active):not(:disabled) {\n  background: #45c983 !important' in ui.CSS
    assert _contrast("#0b0f0d", "#45c983") >= 4.5


# --- controls recover and say what to do --------------------------------------------------

@pytest.fixture
def own_memes(project, monkeypatch, tmp_path):
    """A Memes library of its own, so saving in a test leaves the shared one unchanged."""
    lib = dm.MemeLibrary(tmp_path / "app")
    for gid, name in NAMES.items():
        lib.update(gid, image=_picture(tmp_path / f"{gid}.png"), gesture_name=name)
    monkeypatch.setattr(dm, "MemeLibrary", lambda *a, **k: lib)
    return lib


def test_saving_a_meme_starts_a_fresh_form_showing_what_was_saved(run, own_memes):
    at = run("memes.py")
    at.text_input(key="meme-title-first_meme-0").input("Title A")
    at.text_input(key="meme-rating-first_meme-0").input("8/10")
    at.text_area(key="meme-desc-first_meme-0").input("One line")
    next(b for b in at.button if b.label == "Save meme").click().run()
    assert not at.exception
    assert at.success[0].value.startswith("Saved the meme for First meme.")
    saved = own_memes.load()["first_meme"]
    assert (saved.meme_title, saved.ball_knowledge_level, saved.description) == ("Title A", "8/10", "One line")
    # a new form (and so an empty upload box), filled with the saved text
    assert at.text_input(key="meme-title-first_meme-1").value == "Title A"
    assert not [w for w in at.text_input if w.key == "meme-title-first_meme-0"]


def test_a_save_without_a_new_image_says_the_image_was_not_changed(run, own_memes):
    """Proposal PR-13 (B). A file over the size limit is refused by the upload box, which then
    gives the page no file; Save meme said "Saved the meme ..." and the error disappeared, while
    the image stayed the old one."""
    before = own_memes.image_file(own_memes.load()["first_meme"]).read_bytes()
    at = run("memes.py")
    at.text_input(key="meme-title-first_meme-0").input("Title A")
    next(b for b in at.button if b.label == "Save meme").click().run()
    assert at.success[0].value == ("Saved the meme for First meme. The Live dashboard shows it the "
                                   "next time this gesture is recognised. The image was not changed.")
    assert own_memes.image_file(own_memes.load()["first_meme"]).read_bytes() == before


def test_a_save_with_a_new_image_does_not_say_it_was_not_changed(run, own_memes):
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (30, 20), (200, 40, 40)).save(buf, format="PNG")
    at = run("memes.py")
    at.file_uploader(key="meme-image-first_meme-0").set_value(("new.png", buf.getvalue(), "image/png"))
    next(b for b in at.button if b.label == "Save meme").click().run()
    assert not at.exception, at.exception
    assert at.success[0].value.startswith("Saved the meme for First meme.")
    assert "The image was not changed" not in at.success[0].value
    assert own_memes.load()["first_meme"].image_path.endswith("first_meme.png")


@pytest.fixture
def own_model(project, run, monkeypatch, tmp_path):
    """A model folder of its own, so training in a test leaves the shared report unchanged."""
    import shutil
    paths = {}
    for key in ("model_path", "labels_path", "report_path"):
        target = tmp_path / "m" / getattr(project, key).name
        target.parent.mkdir(exist_ok=True)
        shutil.copy(getattr(project, key), target)
        monkeypatch.setattr(config, key.replace("_path", "").upper() + "_PATH", target)
        paths[key] = target
    return SimpleNamespace(**paths)


def test_train_model_runs_in_the_background_and_reports_once(run, own_model, monkeypatch):
    import threading
    release, real = threading.Event(), tm.train

    def held_until_released(**kwargs):           # the run stays going until the test says
        release.wait(30)
        return real(**kwargs)
    monkeypatch.setattr(tm, "train", held_until_released)
    before = own_model.report_path.read_bytes()
    try:
        at = run("performance.py")
        next(b for b in at.button if b.label == "Train model").click().run()
        assert not at.exception
        assert next(b for b in at.button if b.label == "Train model").disabled    # one run at a time
        assert "Training: " in " ".join(str(p.proto) for p in at.get("progress"))
        assert not at.success
    finally:
        release.set()
    status = tm.training_job(own_model.model_path).wait(60)
    assert status.error is None and not status.running
    at.run()
    assert not at.exception
    assert len(at.success) == 1 and at.success[0].value.startswith("Trained in ")
    assert "from 8 recordings" in at.success[0].value
    assert own_model.report_path.read_bytes() != before
    assert not next(b for b in at.button if b.label == "Train model").disabled
    at.run()
    assert not at.success                        # the result is said once


@pytest.fixture
def untrained(monkeypatch, tmp_path):
    """No model trained yet: the model files point into an empty folder."""
    for key in ("MODEL_PATH", "LABELS_PATH", "REPORT_PATH"):
        monkeypatch.setattr(config, key, tmp_path / "m" / key.lower())


def test_no_trained_model_says_train_first_when_the_data_is_ready(run, untrained):
    """Proposal PR-4 (B). With samples of every gesture recorded, both pages still said to
    record gestures first."""
    dash = page_text(run("dashboard.py"))
    assert "<b>No trained model</b>Train a model on the " in dash
    assert "Record your gestures" not in dash
    perf = page_text(run("performance.py"))
    assert "<b>No trained model yet</b>Press Train model.</div>" in perf


def test_no_trained_model_still_says_record_first_for_a_new_project(run, untrained, own_store):
    for label in ("second_meme", config.NONE_LABEL):
        own_store.delete_label(label)                      # one gesture left
    assert "Record your gestures on the " in page_text(run("dashboard.py"))
    assert "Record at least two gestures on the Data collector page" in page_text(run("performance.py"))


def test_performance_says_when_the_dashboard_cannot_load_the_model(run, own_model):
    """Proposal PR-3 (B). With the model file cut short, the dashboard said "Model cannot be
    used" while this page showed every result with no warning."""
    data = own_model.model_path.read_bytes()
    own_model.model_path.write_bytes(data[:1000])
    at = run("performance.py")
    first = at.warning[0].value
    assert first.startswith("Model cannot be used: the Live dashboard cannot load it. model.joblib ")
    assert first.endswith("The results below are from the training run that saved it.")
    assert "Train the model again." in first


def test_performance_has_no_such_warning_for_a_usable_model(run):
    assert not any(w.value.startswith("Model cannot be used") for w in run("performance.py").warning)


def test_a_recording_replaced_by_one_of_the_same_length_asks_for_retraining(run, project,
                                                                          monkeypatch, tmp_path):
    import shutil
    store = type(project.store)(tmp_path / "samples.csv", tmp_path / "meta.json", "hands")   # a copy
    shutil.copy(project.store.csv_path, store.csv_path)
    shutil.copy(project.store.meta_path, store.meta_path)
    store.delete_session("second_meme-0")
    r = dc.RecordingResult("second_meme-new", "second_meme", "", "2026-10-15T10:00:00")
    r.samples = [np.full(N, 0.5, np.float32)] * 12
    store.append(r)
    assert store.row_count() == project.report["dataset"]["rows_loaded"]
    monkeypatch.setattr(dc, "DatasetStore", lambda *a, **k: store)
    warnings = " ".join(w.value for w in run("performance.py").warning)
    assert "recordings were replaced or edited" in warnings


@pytest.fixture
def own_store(project, monkeypatch, tmp_path):
    """A copy of the samples, so changing them in a test leaves the shared ones unchanged."""
    import shutil
    store = type(project.store)(tmp_path / "samples.csv", tmp_path / "meta.json", "hands")
    shutil.copy(project.store.csv_path, store.csv_path)
    shutil.copy(project.store.meta_path, store.meta_path)
    monkeypatch.setattr(dc, "DatasetStore", lambda *a, **k: store)
    return store


def test_memes_page_lists_a_gesture_named_null(run, own_store):
    """Its samples used to read back with no label, and sorting the gestures stopped the page."""
    r = dc.RecordingResult("null-0", dc.slugify_label("Null"), "", "2026-10-18T10:00:00")
    r.samples = [np.full(N, 0.5, np.float32)] * 3
    own_store.append(r)
    at = run("memes.py")
    assert "null" in at.selectbox[0].options


@pytest.mark.parametrize("error", [
    dc.DatasetError("samples.csv is being changed by another tab or program. Wait a moment and try again."),
    OSError(28, "No space left on device"),
])
def test_a_busy_dataset_on_undo_or_delete_is_a_message_not_a_python_error(run, own_store, monkeypatch, error):
    def fails(*_args):
        raise error
    monkeypatch.setattr(own_store, "delete_session", fails)
    monkeypatch.setattr(own_store, "delete_label", fails)
    at = run("collector.py")
    next(b for b in at.button if b.label.startswith("Undo last recording")).click().run()
    assert not at.exception
    assert at.error[0].value == f"Nothing was deleted: {error}"
    at.checkbox[-1].check().run()
    next(b for b in at.button if b.label == "Delete gesture data").click().run()
    assert not at.exception
    assert at.error[0].value == f"Nothing was deleted: {error}"


def test_a_recording_that_cannot_be_written_is_a_message_not_a_python_error(run, own_store, monkeypatch):
    """A full disk while saving a finished recording used to stop the collector with OSError."""
    import storage
    from streamlit.testing.v1 import AppTest

    def disk_full(*_args):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(storage, "atomic_write_bytes", disk_full)
    rec = dc.Recorder()
    rec.start("wave", target=2, countdown_s=0)
    rec.offer(np.full(N, 0.5, np.float32))
    rec._last_sample_at = -1e9                            # the next frame counts too
    rec.offer(np.full(N, 0.4, np.float32))
    at = AppTest.from_file(str(ROOT / "views" / "collector.py"), default_timeout=60)
    at.session_state["recorder"] = rec                    # the finished recording waiting to be saved
    at.run()
    assert not at.exception
    assert at.error[0].value == "Could not save: [Errno 28] No space left on device"


def test_collector_escapes_a_gesture_id_from_the_files(run, project, own_store, monkeypatch, tmp_path):
    """Ids come from samples.csv; one edited by hand must not become HTML."""
    r = dc.RecordingResult("odd-0", "<i>odd</i>", "", "2026-10-18T10:00:00")
    r.samples = [np.full(N, 0.5, np.float32)] * 3
    own_store.append(r)
    lib = type(project.lib)(tmp_path / "app")        # dm.MemeLibrary is patched to the shared one
    lib.dir.mkdir(parents=True)
    lib.file.write_text('{"<i>odd</i>": {"gesture_name": "Odd"}}')
    monkeypatch.setattr(dm, "MemeLibrary", lambda *a, **k: lib)
    text = page_text(run("collector.py"))
    assert '<span class="m">&lt;i&gt;odd&lt;/i&gt;</span>' in text and "<i>odd</i>" not in text


TRAIN_NOW = ('<p class="hint">You can train now: Train model is on the '
             '<a href="/performance" target="_self">Model performance</a> page.</p>')


def test_the_collector_points_to_training_once_the_data_is_ready(run):
    """Proposal PR-7 (B): after two gestures with two recordings each, nothing on the collector
    said that training was possible, or where. Worded as the owner chose in PR-14 (B): "Ready"
    stays the gesture tag's word, which asks for more than training does."""
    text = page_text(run("collector.py"))
    assert TRAIN_NOW in text
    assert "Ready to train" not in text


def test_no_pointer_to_training_while_a_gesture_is_short_of_recordings(run, own_store):
    own_store.delete_session("first_meme-1")              # first_meme down to 1 recording
    text = page_text(run("collector.py"))
    assert "You can train now" not in text


TYPE_A_NAME = '<p class="hint">Type a gesture name to start.</p>'


def test_start_recording_says_why_it_is_disabled_until_a_name_is_typed(run):
    """Proposal PR-8 (B): with "New gesture..." chosen and no name, Start recording was disabled
    with no word on why."""
    at = run("collector.py")
    assert TYPE_A_NAME not in page_text(at)                       # a recorded gesture is chosen
    at.selectbox[0].set_value("New gesture...").run()
    assert at.button(key="record-toggle").disabled
    assert TYPE_A_NAME in page_text(at)
    at.text_input[0].input("Open palm").run()
    assert not at.button(key="record-toggle").disabled
    assert TYPE_A_NAME not in page_text(at)


def test_record_without_the_camera_says_where_the_camera_button_is(run):
    at = run("collector.py")
    at.button(key="record-toggle").click().run()
    assert at.warning[0].value == "Start the camera first: press Start camera under the video."


def _app_with_a_recording(label="wave"):
    """The whole app (app.py, with its navigation) and a recording going in this session."""
    from streamlit.testing.v1 import AppTest
    rec = dc.Recorder()
    rec.start(label, target=50, countdown_s=0)
    rec.offer(np.full(N, 0.5, np.float32))
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.session_state["recorder"] = rec
    return at, rec


@pytest.mark.parametrize("page", ["dashboard.py", "performance.py", "memes.py", "privacy.py",
                                  "terms.py"])
def test_every_other_page_cancels_a_recording_in_progress(run, page):
    """Owner decision Q2 (A), 18 October. Only the dashboard used to cancel; coming back from
    another page saved what had been recorded before you left, without you seeing it happen."""
    at, rec = _app_with_a_recording()
    at.switch_page(f"views/{page}").run()
    assert not at.exception, at.exception
    assert rec.status().state == dc.IDLE and rec.pop_finished() is None


def test_the_collector_itself_does_not_cancel_its_recording(run, own_store):
    at, rec = _app_with_a_recording("first_meme")
    before = own_store.row_count()
    at.switch_page("views/collector.py").run()            # camera off here: the recording ends
    assert not at.exception, at.exception
    assert own_store.row_count() == before + 1             # saved, not dropped


STOPPED = "The recording was stopped when you left the page. Nothing was saved."


def test_a_collector_message_stays_until_your_next_action(run):
    """Proposal PR-12 (B). Coming back to the collector, the camera component reruns the page
    as it mounts, and that rerun cleared the message: it showed for about 0.1 s."""
    at = run("collector.py")
    at.session_state["collector_msg"] = ("ok", "Saved 23 samples for First meme.")
    at.run()
    assert at.success[0].value == "Saved 23 samples for First meme."
    at.run()                                       # a rerun the user did not ask for
    assert at.success and at.success[0].value == "Saved 23 samples for First meme."
    at.slider[0].set_value(40).run()               # the user acts on the page
    assert not at.success


def test_leaving_mid_recording_says_it_was_stopped_and_nothing_saved(run, own_store):
    """Proposal PR-12 (B), after Q2 (A): the recording is dropped, and the collector says so."""
    at, rec = _app_with_a_recording()
    before = own_store.row_count()
    at.switch_page("views/memes.py").run()
    at.switch_page("views/privacy.py").run()              # a second page on the way back
    at.switch_page("views/collector.py").run()
    assert not at.exception, at.exception
    assert at.warning[0].value == STOPPED
    at.run()
    assert at.warning[0].value == STOPPED
    assert own_store.row_count() == before


def test_an_old_collector_message_is_gone_after_another_page(run):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.session_state["collector_msg"] = ("ok", "Saved 23 samples for First meme.")
    at.switch_page("views/collector.py").run()
    assert at.success[0].value == "Saved 23 samples for First meme."
    at.switch_page("views/memes.py").run()
    at.switch_page("views/collector.py").run()
    assert not at.exception, at.exception
    assert not at.success


def test_collector_panels_keep_their_place_when_a_message_comes_and_goes(run):
    """Undo ends its run early (st.rerun) with no message and then shows one. When the message
    pushed the panels down, the browser kept a faded copy of Your dataset with the old numbers."""
    at = run("collector.py")
    without = len(at.columns[1].children)
    at.session_state["collector_msg"] = ("ok", "Removed the last recording (20 samples).")
    at.run()
    assert at.success[0].value == "Removed the last recording (20 samples)."
    assert len(at.columns[1].children) == without


def test_retrain_hint_does_not_say_train_twice():
    stale = ["The dataset has changed since this model was trained (380 samples then, 400 now). "
             "Train again to include the changes."]
    html = ui.stale_notice(stale)
    assert "Train again to include the changes. Train model is on the " in html
    assert "Retrain on the" not in html
    src = (ROOT / "views" / "dashboard.py").read_text()
    assert 'ui.notice(ui.stale_notice(stale), "warn")' in src


def test_the_cutoff_table_never_rounds_a_share_up_to_all(run, project, monkeypatch, tmp_path):
    """At 50% the live report keeps 99.74% of held-out predictions; the table said "100%", as if
    none were rejected, beside a Correct column already written to one decimal."""
    import json
    report = json.loads(project.report_path.read_text())
    report["test"]["thresholds"][0].update(threshold=0.5, coverage=0.9974, accuracy=0.9736)
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report))
    monkeypatch.setattr(config, "REPORT_PATH", path)
    text = page_text(run("performance.py"))
    assert '<td class="num">99.7%</td><td class="num">97.4%</td>' in text
    assert '<td class="num">100%</td><td class="num">97.4%</td>' not in text


def test_performance_page_writes_every_time_the_same_way(run, project):
    from datetime import datetime
    text = page_text(run("performance.py"))
    trained = datetime.fromisoformat(project.report["trained_at"]).strftime("%d %b %H:%M")
    assert f"Trained {trained}</span>" in text
    assert "14 Oct 11:30 (first_)" in text                 # a recording, named by when it started


# --- frontend refinement, 17 October (seen in the browser; these keep the fixes) ----------

def test_camera_frame_keeps_its_size_and_is_flat():
    css = ui._IFRAME_CSS
    # camera off or connecting: a 4:3 frame, so the page does not jump when video starts
    assert ".MuiPaper-root:not(.MuiAlert-root){aspect-ratio:4/3" in css
    # the library's button had a raised shadow and a click ripple; the site's buttons have neither
    assert "box-shadow:none !important" in css and ".MuiTouchRipple-root{display:none" in css
    assert "button.MuiButton-contained:is(:hover,:active):not(:disabled){background:#45c983" in css


def test_on_a_phone_the_dashboard_camera_is_smaller():
    """Proposal PR-5 (C), a layout change the owner reserved, so it is a commit of its own. At
    390x844 the meme started at 827 px, 17 px into the first screen. When the columns stack, the
    dashboard's camera is 60% of the width (its 4:3 frame shrinks with it); the collector's camera,
    which you watch while recording, is unchanged."""
    assert ("@media (max-width: 640px) {\n"
            '  .stApp [class*="st-key-dashboard-camera"] iframe {\n'
            "    width: 60% !important; display: block; margin: 0 auto; }\n}") in ui.CSS
    assert "collector-camera" not in ui.CSS


def test_notices_are_drawn_in_the_site_colours():
    for kind in ("Warning", "Error", "Success"):
        assert f'[data-testid="stAlertContent{kind}"]' in ui.CSS
    assert '.stApp [data-testid="stAlertContainer"], .notice {' in ui.CSS
    # the notice text is --text on a faint tint of the page, so it keeps full contrast
    assert _contrast("#e6ece8", "#0b0f0d") >= 4.5


def test_notice_puts_its_html_in_one_box(monkeypatch):
    calls = []
    monkeypatch.setattr(ui.st, "markdown", lambda body, **kw: calls.append((body, kw)))
    ui.notice(f"Set them on the {ui.link('memes', 'Memes')} page.", "warn")
    body, kw = calls[0]
    assert body == ('<div class="notice warn">Set them on the '
                    '<a href="/memes" target="_self">Memes</a> page.</div>')
    assert kw == {"unsafe_allow_html": True}


def test_dashboard_notices_link_to_the_memes_page_in_this_tab():
    src = (ROOT / "views" / "dashboard.py").read_text()
    assert "st.info(" not in src                  # Streamlit's notices open links in a new tab
    assert src.count("ui.link('memes', 'Memes')") == 1


def test_stat_values_line_up_when_a_label_wraps():
    assert "grid-template-rows: subgrid" in ui.CSS and "grid-row: span 3" in ui.CSS


def test_html_table_escapes_every_cell_except_html_ones():
    table = ui.html_table(["Gesture", "Image"], [["<b>x</b>", ui.Html(ui.tag("Set", "ok"))]])
    assert "&lt;b&gt;x&lt;/b&gt;" in table
    assert '<span class="tag ok">Set</span>' in table


def test_memes_table_shows_each_state_as_a_tag(run):
    text = page_text(run("memes.py"))
    assert '<td class=""><span class="tag ok">Set</span></td>' in text           # images
    assert '<td class=""><span class="tag off">Not set</span></td>' in text      # titles


def test_memes_preview_does_not_send_you_to_the_page_you_are_on(run):
    text = page_text(run("memes.py"))
    assert "without the confidence meter that sits under it" in text
    assert 'href="/memes"' not in text


def test_the_model_is_named_without_the_word_the_site_avoids(run):
    text = page_text(run("performance.py"))
    assert '<span class="tag off">softmax regression</span>' in text
    assert "gradient" not in text.lower()


def test_each_browser_tab_names_its_page():
    src = (ROOT / "app.py").read_text()
    assert 'st.set_page_config(page_title=f"{page.title} | {config.APP_TITLE}")' in src
    assert src.index("st.navigation(") < src.index("page.title") < src.index("page.run()")
