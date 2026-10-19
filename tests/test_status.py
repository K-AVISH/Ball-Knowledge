"""Status logic shown on the dashboard and performance pages: model state, staleness
and every state of the dashboard's meme panel. Predictions here are hand-made, so these
tests check what is shown for each state, not how accurate any model is."""
import os
import sys
import time
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
import dataset_manager as dm  # noqa: E402
import predictor as pr  # noqa: E402
import train_model as tm  # noqa: E402
import ui  # noqa: E402
from vision import VisionStats  # noqa: E402

TOP = (("peace_sign", 0.84), ("open_palm", 0.11), ("fist", 0.05))
LOW = (("peace_sign", 0.52), ("open_palm", 0.31), ("fist", 0.17))


def fresh(status, **kw):
    return pr.Prediction(status, at=time.time(), **kw)


LIB = None          # a meme library with an image for each gesture, set up once below


@pytest.fixture(scope="module", autouse=True)
def memes(tmp_path_factory):
    global LIB
    root = tmp_path_factory.mktemp("memes")
    Image.new("RGB", (40, 30), (20, 120, 60)).save(root / "a.png")
    LIB = dm.MemeLibrary(root / "project")
    for gid, name in (("peace_sign", "Peace sign"), ("fist", "Fist"), ("open_palm", "Open palm")):
        LIB.update(gid, image=root / "a.png", gesture_name=name)
    return LIB


def card(problem=None, prediction=None, playing=True, live=True, steady=None, camera_error=None):
    return ui.result_card(problem, prediction, playing, live, steady, LIB.load(), None, LIB,
                          camera_error=camera_error)


STEADY = pr.Steady("peace_sign", 0.84, 5, 7)


# --- staleness -----------------------------------------------------------------

REPORT = {"dataset": {"rows_loaded": 480}, "feature_mode": "hands"}


def test_current_model_is_not_stale():
    assert tm.staleness(REPORT, 480, "hands") == []


def test_changed_dataset_is_stale_and_says_by_how_much():
    reasons = tm.staleness(REPORT, 580, "hands")
    assert len(reasons) == 1 and "480 samples then, 580 now" in reasons[0]


def test_feature_mode_change_is_stale():
    assert "hands+pose" in tm.staleness(REPORT, 480, "hands+pose")[0]


def test_unreadable_dataset_is_not_called_stale():
    assert tm.staleness(REPORT, None, "hands") == []


SIGNED = {"dataset": {"rows_loaded": 480, "fingerprint": "a" * 64}, "feature_mode": "hands"}


def test_a_replaced_recording_of_the_same_length_is_stale():
    reasons = tm.staleness(SIGNED, 480, "hands", dataset_fingerprint="b" * 64)
    assert len(reasons) == 1
    assert "still has 480 samples, but recordings were replaced or edited" in reasons[0]
    assert reasons[0].endswith("Train again to include the changes.")   # the hint the panels extend


def test_same_fingerprint_is_current_and_a_row_change_is_reported_once():
    assert tm.staleness(SIGNED, 480, "hands", dataset_fingerprint="a" * 64) == []
    reasons = tm.staleness(SIGNED, 500, "hands", dataset_fingerprint="b" * 64)
    assert len(reasons) == 1 and "480 samples then, 500 now" in reasons[0]


def test_reports_without_a_fingerprint_are_checked_by_rows_only():
    assert tm.staleness(REPORT, 480, "hands", dataset_fingerprint="b" * 64) == []


def trained_with_todays_settings():
    aug = tm.augmentation_settings(tm.make_model(config.GD_L2_OPTIONS[0]))
    return {**SIGNED, "cost": {"augmentation": aug,
                               "l2_options": [{"l2": v} for v in config.GD_L2_OPTIONS]}}


def test_changed_training_settings_ask_for_retraining(monkeypatch):
    report = trained_with_todays_settings()
    assert tm.staleness(report, 480, "hands", dataset_fingerprint="a" * 64) == []
    monkeypatch.setattr(config, "GD_AUGMENT_COPIES", 0)            # the ML rollback advice
    reasons = tm.staleness(report, 480, "hands", dataset_fingerprint="a" * 64)
    assert len(reasons) == 1 and reasons[0].startswith("The training settings in config.py (augmentation)")
    monkeypatch.setattr(config, "GD_L2_OPTIONS", (1.0, 0.1))
    assert "(augmentation and the l2 options)" in tm.staleness(report, 480, "hands")[0]


def test_an_empty_l2_list_is_reported_not_a_crash(monkeypatch):
    """The check used to build a model with GD_L2_OPTIONS[0], an IndexError on both pages."""
    report = trained_with_todays_settings()
    monkeypatch.setattr(config, "GD_L2_OPTIONS", ())
    reasons = tm.staleness(report, 480, "hands", dataset_fingerprint="a" * 64)
    assert len(reasons) == 1 and "(the l2 options)" in reasons[0]


def test_reports_without_settings_are_not_called_stale_for_them(monkeypatch):
    monkeypatch.setattr(config, "GD_AUGMENT_COPIES", 0)
    assert tm.staleness({**SIGNED, "cost": {}}, 480, "hands", dataset_fingerprint="a" * 64) == []


# --- model state -----------------------------------------------------------------

@pytest.mark.parametrize("problem, stale, expected", [
    (pr.NotTrainedError("x"), [], ("Not trained", "off")),
    (pr.PredictorError("x"), [], ("Cannot load", "bad")),
    (None, ["changed"], ("Retrain needed", "warn")),
    (None, [], ("Loaded", "ok")),
])
def test_model_state(problem, stale, expected):
    assert ui.model_state(problem, stale) == expected


def test_pct_never_invents_a_number():
    assert ui.pct(None) == "n/a"
    assert ui.pct(0.843) == "84%"


def test_model_scores_never_round_to_certainty():
    assert ui.score_pct(0.9996) == "over 99%"
    assert ui.score_pct(0.0004) == "under 1%"
    assert ui.score_pct(0.843) == "84%"
    assert ui.score_pct(None) == "n/a"
    html = card(prediction=fresh(pr.RECOGNISED, label="peace_sign", confidence=0.9996,
                                 top=(("peace_sign", 0.9996), ("open_palm", 0.0004))))
    assert "Confidence <b>over 99%</b>" in html
    assert ">100%<" not in html                            # visible text, not the bar width


# --- meme panel states -------------------------------------------------------------

STATES = {
    "not trained": dict(problem=pr.NotTrainedError("x")),
    "cannot load": dict(problem=pr.PredictorError("Cannot load model.joblib")),
    "camera off": dict(playing=False, live=False),
    "connecting": dict(playing=True, live=False),
    "starting": dict(prediction=None),
    "no hand": dict(prediction="no_hand"),
    "unrecognised": dict(prediction="unrecognised"),
    "checking": dict(prediction="recognised"),
    "recognised": dict(prediction="recognised", steady=STEADY),
    "no gesture": dict(prediction="no_hand", steady=pr.Steady(config.NONE_LABEL, 0.9, 4, 7)),
    "error": dict(prediction="error"),
    "camera problem": dict(prediction=None, camera_error="ModelMissingError: Hand model not found at "
                                                         "/x/hand_landmarker.task. Run: python download_models.py"),
}


def build(name):
    kw = dict(STATES[name])
    p = kw.get("prediction")
    if p == "no_hand":
        kw["prediction"] = fresh(pr.NO_HAND)
    elif p == "unrecognised":
        kw["prediction"] = fresh(pr.UNRECOGNISED, confidence=0.52, top=LOW, threshold=0.7)
    elif p == "recognised":
        kw["prediction"] = fresh(pr.RECOGNISED, label="peace_sign", confidence=0.84, top=TOP, threshold=0.7)
    elif p == "error":
        kw["prediction"] = fresh(pr.ERROR, error="ValueError: bad frame")
    return card(**kw)


# What stands in the meme's place in each state. Recognised shows the meme itself.
HEADLINES = {
    "not trained": "No trained model", "cannot load": "Model cannot be used",
    "camera off": "Camera off", "connecting": "Waiting for video",
    "starting": "Starting", "no hand": "No hand in view",
    "unrecognised": "Unrecognised", "checking": "Hold it steady",
    "no gesture": "No gesture", "error": "Prediction failed",
    "camera problem": "Camera problem",
}


@pytest.mark.parametrize("name", [n for n in STATES if n != "recognised"])
def test_each_state_has_its_own_message_and_no_meme(name):
    html = build(name)
    assert f"<b>{HEADLINES[name]}</b>" in html and "<img" not in html
    assert not any(f"<b>{h}</b>" in html for n, h in HEADLINES.items() if n != name)


def test_states_are_all_different():
    assert len({build(n) for n in STATES}) == len(STATES)


@pytest.mark.parametrize("name", list(STATES))
def test_no_state_names_a_gesture(name):
    html = build(name)                   # alt text included: screen readers hear it
    for word in ("Peace sign", "peace_sign", "Open palm", "open_palm", "Fist", "fist"):
        assert word not in html


def test_alt_text_is_the_meme_title_or_just_meme(tmp_path):
    Image.new("RGB", (40, 30), (20, 120, 60)).save(tmp_path / "a.png")
    lib = dm.MemeLibrary(tmp_path / "project")
    lib.update("peace_sign", image=tmp_path / "a.png", gesture_name="Peace sign")
    untitled = ui.result_card(None, fresh(pr.RECOGNISED, label="peace_sign", confidence=0.84, top=TOP,
                                          threshold=0.7), True, True, STEADY, lib.load(), None, lib)
    assert 'alt="Meme"' in untitled and "Peace sign" not in untitled
    lib.update("peace_sign", meme_title="Peace Out")
    records = lib.load()
    # the title alone (owner decision Q3, option B): the panel is already headed "Meme"
    assert 'alt="Peace Out"' in ui.meme_thumb("peace_sign", records, lib)
    assert ui.meme_alt(records["peace_sign"]) == "Peace Out"


def test_no_hand_tag_once_the_camera_is_off():
    """Stop camera: the camera tag says Camera off at once, but the frame stats are cleared only
    when the page runs again. The hand tag used to say "2 hands detected" beside "Camera off"
    in that moment (about 640 ms in the browser)."""
    stats = VisionStats(hand_detected=True, num_hands=2)
    assert ui.hand_tag(stats, live=False) == ""
    assert "2 hands detected" in ui.hand_tag(stats, live=True)
    assert "No hand" in ui.hand_tag(VisionStats(), live=True)


def test_missing_hand_model_hint_names_no_python_error_and_ends_its_sentence():
    """The hint showed the frame error as stored, "ModelMissingError: ... Run: python
    download_models.py The camera picks ...": a Python error name and two sentences run together."""
    stats = VisionStats(error="ModelMissingError: Hand model not found at /x/hand_landmarker.task. "
                              "Run: python download_models.py")
    _, hint, _ = ui.camera_state(stats, playing=True)
    assert "Error" not in hint
    assert hint == ("Hand model not found at /x/hand_landmarker.task. Run: python download_models.py. "
                    "The camera picks the model up by itself within a few seconds.")


def test_missing_hand_model_hint_says_the_camera_recovers_by_itself():
    stats = VisionStats(error="Hand model not found. Run: python download_models.py")
    _, hint, _ = ui.camera_state(stats, playing=True)
    assert "picks the model up by itself" in hint and "restart" not in hint


@pytest.mark.parametrize("error", [
    "error: (-215:Assertion failed) size.width>0 && size.height>0 <cv::Mat>",
    "ModelMissingError: Hand model not found at /a<b>/hand_landmarker.task. Run: python download_models.py",
])
def test_frame_errors_are_escaped_in_the_camera_hint(error):
    """Both pages put the hint into HTML; error text is data and must be escaped."""
    _, hint, _ = ui.camera_state(VisionStats(error=error), playing=True)
    assert "<" not in hint and ">" not in hint and "&lt;" in hint


# --- loading the model while a training run saves it -------------------------------

@pytest.fixture
def model_files(tmp_path, monkeypatch):
    files = {key: tmp_path / key.lower() for key in ("MODEL_PATH", "LABELS_PATH", "REPORT_PATH")}
    for key, path in files.items():
        path.write_text("x")
        monkeypatch.setattr(config, key, path)
    return files


def test_a_load_that_overlaps_a_training_save_is_tried_again(model_files, monkeypatch):
    """A run renames its three files one by one; a load in between sees a new model beside
    the old report and is refused. The dashboard used to keep showing "Model cannot be used"
    until the whole page ran again."""
    calls = []

    def load(*_args):
        calls.append(1)
        if len(calls) == 1:                        # the trainer's renames land meanwhile
            os.utime(model_files["MODEL_PATH"], ns=(10**18, 10**18))
            raise pr.PredictorError("not the model that the report was saved with")
        return "the new model"
    monkeypatch.setattr(pr.Predictor, "load", load)
    assert ui.load_predictor() == ("the new model", None) and len(calls) == 2


def test_a_model_that_stays_unusable_is_reported_without_retrying(model_files, monkeypatch):
    calls = []

    def load(*_args):
        calls.append(1)
        raise pr.PredictorError("Cannot load model: truncated")
    monkeypatch.setattr(pr.Predictor, "load", load)
    model, problem = ui.load_predictor()
    assert model is None and "truncated" in str(problem) and len(calls) == 1


def test_recognised_shows_the_meme_with_the_meter_only():
    html = build("recognised")
    assert '<div class="meme-frame"><img class="meme-img" src="data:image/png;base64,' in html
    assert "Confidence <b>84%</b>" in html and "Threshold 70%" in html
    assert 'class="fill "' in html                       # green, above the threshold
    assert "<h2>Meme</h2>" in html and "<table" not in html and 'class="tag' not in html
    assert "not a calibrated probability" in html        # in the meter's tooltip


def test_unrecognised_never_shows_a_meme():
    html = build("unrecognised")
    assert "<img" not in html and "below the 70% threshold" in html
    assert "Confidence <b>52%</b>" in html and 'class="fill warn"' in html


def test_the_meter_says_n_a_when_nothing_is_being_judged():
    for name in ("camera off", "no hand", "no gesture", "not trained"):
        html = build(name)
        assert "Confidence <b>n/a</b>" in html and 'style="width:0%"' in html


def test_a_single_frame_is_not_presented_as_the_result():
    html = build("checking")
    assert "<b>Hold it steady</b>" in html and "<img" not in html
    assert f"{config.MIN_STABLE_FRAMES} of the last {config.SMOOTHING_WINDOW} frames" in html


def test_no_trained_model_says_train_first_when_the_data_is_ready():
    """Proposal PR-4 (B): with gestures already recorded, "Record your gestures ..." was not the
    next step. The new-project text stays while the data is not ready."""
    ready = ui.result_card(pr.NotTrainedError("x"), None, True, True, None, LIB.load(), None, LIB,
                           can_train=True)
    assert "<b>No trained model</b>" in ready and "Record your gestures" not in ready
    assert ('Train a model on the <a href="/performance" target="_self">Model performance</a> '
            "page.") in ready
    assert "Record your gestures on the" in build("not trained")


def test_a_relaxed_hand_says_no_gesture_at_once():
    """Proposal PR-2 (B). A frame recognised as `none` showed "Hold it steady. The meme appears
    once ..." with a green meter, although no meme ever appears for a relaxed hand. No vote is
    needed when no meme is at stake, so it is the steady No gesture state at once."""
    frame = fresh(pr.RECOGNISED, label=config.NONE_LABEL, confidence=0.91,
                  top=((config.NONE_LABEL, 0.91), ("peace_sign", 0.09)), threshold=0.7)
    html = card(prediction=frame)
    assert html == build("no gesture")
    assert "Hold it steady" not in html and "The meme appears" not in html
    assert "Confidence <b>n/a</b>" in html


def test_a_held_meme_stays_through_one_relaxed_frame():
    """The vote still decides when a meme goes: one `none` frame does not hide a held meme."""
    frame = fresh(pr.RECOGNISED, label=config.NONE_LABEL, confidence=0.9, top=TOP)
    assert '<img class="meme-img"' in card(prediction=frame, steady=STEADY)


def test_a_held_gesture_survives_a_frame_without_a_hand():
    html = card(prediction=fresh(pr.NO_HAND), steady=STEADY)
    assert '<img class="meme-img"' in html and "No hand in view" not in html


def test_steady_result_is_hidden_when_the_camera_is_off_or_errors():
    assert "<img" not in card(prediction=fresh(pr.NO_HAND), steady=STEADY, playing=False, live=False)
    assert "Prediction failed" in card(prediction=fresh(pr.ERROR, error="x"), steady=STEADY)


def test_a_camera_problem_is_said_in_the_meme_panel_not_starting():
    """Owner decision Q1 (B), 18 October. Frames that fail before the model (the hand model
    missing, say) never reach it, so the panel used to say "Starting. The model is classifying
    the first frames." for as long as the camera panel said "Hand model missing"."""
    html = card(prediction=None, camera_error="ModelMissingError: Hand model not found.")
    assert "<b>Camera problem</b>" in html and 'class="meme-frame msg bad"' in html
    assert "under the video" in html
    assert "Starting" not in html and "classifying" not in html
    assert "ModelMissingError" not in html         # the reason is in the camera panel, once
    assert "Confidence <b>n/a</b>" in html


def test_a_camera_problem_hides_a_meme_that_was_steady():
    """No new frame reaches the model while frames fail, so the last result is not shown."""
    html = card(prediction=fresh(pr.RECOGNISED, label="peace_sign", confidence=0.9, top=TOP),
                steady=STEADY, camera_error="error: bad frame")
    assert "<img" not in html and "<b>Camera problem</b>" in html


def test_the_camera_being_off_comes_before_an_old_camera_problem():
    assert "<b>Camera off</b>" in card(playing=False, live=False, camera_error="x")
    assert "<b>Waiting for video</b>" in card(playing=True, live=False, camera_error="x")


def test_stale_prediction_is_not_shown():
    old = pr.Prediction(pr.RECOGNISED, label="peace_sign", confidence=0.9, top=TOP, at=time.time() - 10)
    html = card(prediction=old)
    assert "<img" not in html and "<b>Starting</b>" in html


def test_camera_off_hides_an_old_result():
    html = card(prediction=fresh(pr.RECOGNISED, label="peace_sign", confidence=0.9, top=TOP),
                playing=False, live=False)
    assert "<img" not in html and "<b>Camera off</b>" in html


def test_a_gesture_with_no_meme_is_named_so_it_can_be_fixed():
    html = card(prediction=fresh(pr.RECOGNISED, label="wave", confidence=0.9, top=TOP),
                steady=pr.Steady("wave", 0.9, 5, 7))
    assert "<b>No meme set</b>" in html and "wave has no meme yet" in html


def test_retrain_notice_names_the_change_and_where_to_train():
    html = ui.stale_notice(["The dataset has changed since this model was trained."])
    assert html.startswith("The dataset has changed since this model was trained. Train model is on the ")
    assert '<a href="/performance" target="_self">Model performance</a>' in html


def test_labels_and_errors_are_escaped():
    html = card(prediction=fresh(pr.ERROR, error="<script>x</script>"))
    assert "<script>" not in html
    html = card(prediction=fresh(pr.RECOGNISED, label="<i>x</i>", confidence=0.9, top=(("<i>x</i>", 0.9),)),
                steady=pr.Steady("<i>x</i>", 0.9, 5, 7))
    assert "<i>x</i>" not in html and "&lt;i&gt;x&lt;/i&gt;" in html


# --- recent detections -------------------------------------------------------------

def entry(label, confidence=0.9, at=None):
    return pr.HistoryEntry(at if at is not None else time.time(), label, confidence)


def test_history_lists_time_gesture_and_confidence_newest_first():
    at = time.mktime((2026, 10, 13, 14, 5, 9, 0, 0, -1))
    html = ui.history_card((entry("fist", 0.9996, at), entry("peace_sign", 0.81, at - 60)), 2, True)
    assert html.index("fist") < html.index("peace_sign")
    assert "14:05:09" in html and "over 99%" in html and "81%" in html
    assert "never saved" in html


def test_history_says_when_older_entries_are_not_shown():
    assert "3 of 25 this session" in ui.history_card((entry("a"), entry("b"), entry("c")), 25, True)


def test_empty_history_invents_nothing():
    html = ui.history_card((), 0, True)
    assert "Nothing detected yet" in html and "<table" not in html
    assert "once a model is trained" in ui.history_card((), 0, False)


def test_history_labels_are_escaped():
    assert "<b>x</b>" not in ui.history_card((entry("<b>x</b>"),), 1, True)
