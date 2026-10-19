"""Status logic shown on the dashboard and performance pages: model state, staleness
and every state of the recognition panel. Predictions here are hand-made, so these
tests check what is shown for each state, not how accurate any model is."""
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
import predictor as pr  # noqa: E402
import train_model as tm  # noqa: E402
import ui  # noqa: E402

TOP = (("peace_sign", 0.84), ("open_palm", 0.11), ("fist", 0.05))
LOW = (("peace_sign", 0.52), ("open_palm", 0.31), ("fist", 0.17))


def fresh(status, **kw):
    return pr.Prediction(status, at=time.time(), **kw)


def card(problem=None, prediction=None, playing=True, live=True, stale=(), steady=None):
    return ui.recognition_card(problem, prediction, playing, live, list(stale), steady)


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
    assert "Confidence <b>over 99%</b>" in html and "under 1%" in html
    assert ">100%<" not in html and ">0%<" not in html     # visible text, not the bar width


# --- recognition panel states ------------------------------------------------------

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


HEADLINES = {
    "not trained": "No trained model", "cannot load": "Model cannot be used",
    "camera off": "Waiting for the camera", "connecting": "Waiting for video",
    "starting": "Waiting for the first prediction", "no hand": "No hand detected",
    "unrecognised": "Unrecognised", "checking": "Checking", "recognised": "peace_sign",
    "no gesture": "No gesture", "error": "Prediction failed",
}


@pytest.mark.parametrize("name", list(STATES))
def test_each_state_has_its_own_headline(name):
    html = build(name)
    assert f">{HEADLINES[name]}</div>" in html
    others = [h for n, h in HEADLINES.items() if n != name and h != "peace_sign"]
    assert not any(f">{h}</div>" in html for h in others)


def test_states_are_all_different():
    assert len({build(n) for n in STATES}) == len(STATES)


def test_unrecognised_never_presents_a_gesture_as_the_result():
    html = build("unrecognised")
    assert 'class="big">Unrecognised<' in html
    assert 'class="big ok"' not in html
    assert "none high enough to count" in html          # the scores are labelled as not results
    assert "below the 70% threshold" in html


def test_recognised_shows_label_confidence_threshold_and_calibration_note():
    html = build("recognised")
    assert 'class="big ok">peace_sign<' in html
    assert "Confidence <b>84%</b>" in html and "Threshold 70%" in html
    assert "Recognised in 5 of the last 7 frames" in html
    assert "not a calibrated probability" in html


def test_a_single_frame_is_not_presented_as_the_result():
    html = build("checking")
    assert 'class="big">Checking<' in html and 'class="big ok"' not in html
    assert "Latest frame: peace_sign" in html


def test_a_held_gesture_survives_a_frame_without_a_hand():
    html = card(prediction=fresh(pr.NO_HAND), steady=STEADY)
    assert 'class="big ok">peace_sign<' in html and "No hand detected" not in html


def test_steady_result_is_hidden_when_the_camera_is_off_or_errors():
    assert "peace_sign" not in card(prediction=fresh(pr.NO_HAND), steady=STEADY,
                                    playing=False, live=False)
    assert "Prediction failed" in card(prediction=fresh(pr.ERROR, error="x"), steady=STEADY)


def test_stale_prediction_is_not_shown():
    old = pr.Prediction(pr.RECOGNISED, label="peace_sign", confidence=0.9, top=TOP, at=time.time() - 10)
    html = card(prediction=old)
    assert "peace_sign" not in html and "Waiting for the first prediction" in html


def test_camera_off_hides_an_old_result():
    html = card(prediction=fresh(pr.RECOGNISED, label="peace_sign", confidence=0.9, top=TOP),
                playing=False, live=False)
    assert "peace_sign" not in html


def test_retrain_needed_is_shown_alongside_a_result():
    html = card(prediction=fresh(pr.RECOGNISED, label="fist", confidence=0.9, top=TOP),
                stale=["The dataset has changed since this model was trained."],
                steady=pr.Steady("fist", 0.9, 4, 7))
    assert "Retrain needed" in html and "dataset has changed" in html
    assert html.index("Recognised") < html.index("Retrain needed")     # result first


def test_labels_and_errors_are_escaped():
    html = card(prediction=fresh(pr.ERROR, error="<script>x</script>"))
    assert "<script>" not in html
    html = card(prediction=fresh(pr.RECOGNISED, label="<b>x</b>", confidence=0.9, top=(("<b>x</b>", 0.9),)))
    assert "<b>x</b>" not in html


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
