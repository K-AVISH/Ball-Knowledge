# Handoff: Ball Knowledge Vision AI (Stage 8 of 8)

For the next session, or for you picking this up later. Read `01_PROJECT_CONTEXT.md` first.

## Update, 14 October 2026: Stage 8, testing without a webcam

Everything that can run without your webcam was tested end to end. The webcam run is the part left (README, Test the whole pipeline, With your webcam).

**New: `check_pipeline.py`.** Plays clips through the exact live path (mirror, MediaPipe, features, model, steady vote, recent detections) and reports what the dashboard would show. A clip already in the dataset is classified by a model trained without it. `predictor.LiveRecognizer.classify()` was added for this: it runs the same vote and history code on the calling thread, in the video's own time. Tests: `tests/test_check_pipeline.py` and 3 new tests in `tests/test_predictor.py`.

**Held-out replay of all 16 recordings** (`python check_pipeline.py "First meme" "Second meme" "Meme 3" "Meme 4" None`; the identical copy in First meme is checked once). Shares of the frames from the first to the last frame with a hand:

| Gesture | Clips | Right | Wrong | No gesture | Unsure | No hand | First right, median |
|---|---|---|---|---|---|---|---|
| first_meme | 2 | 75% | 0% | 5% | 19% | 0% | 0.38 s |
| meme_3 | 3 | 87% | 0% | 2% | 12% | 0% | 0.20 s |
| meme_4 | 4 | 59% | 0% | 0% | 7% | 33% | 0.10 s |
| none | 4 | 78% (No gesture) | 0% | | 21% | 1% | |
| second_meme | 3 | 85% | 0% | 2% | 13% | 0% | 0.13 s |

No clip showed a wrong gesture. The "no hand" share for meme_4 is real: frames from those gaps show no hand in the picture (the person lowered it between attempts).

**Browser run on a scratch copy of the data** (port 8503, `BALLKNOWLEDGE_DATA_DIR` and `BALLKNOWLEDGE_MODEL_DIR` pointed at the scratchpad, so `data/` and `models/` were not touched). Four clips were removed from the scratch dataset first.

1. Data collector: a removed meme_3 clip was played into the stand-in camera and recorded (countdown, progress, single Start/Stop toggle, "Saved 40 samples for meme_3", dataset table updated). Each browser sample was much closer to the imported samples of the same clip (median distance 0.15) than to other meme_3 recordings (0.50) or other gestures (1.18). A model that never saw the clip labelled 36 of 40 as meme_3, 3 unrecognised, 1 none. So the live camera path and `import_videos.py` produce matching numbers.
2. Model performance: Train model worked from the page (13 recordings, held-out 74.6% on this reduced set, l2 0.3).
3. Live dashboard with the three removed clips: none showed No gesture or Unrecognised and never a meme; second_meme showed its meme whenever the hand was steady; meme_4 mostly stayed Unrecognised. Offline, the same scratch model scores that clip 0.67 to 0.69 on average, right at the 70% cutoff. Each compression step lowers the share shown a little (54% at full quality, 33% to 44% after JPEG and VP8). The full model does much better on it (94% right in the replay above).
4. Stop camera cleared every panel and kept the session history. Undo last recording made the dashboard say "Retrain needed (347 samples then, 307 now)".

**Fixed**

- The hand tag under the video refreshed every 1 s and the Recognition panel every 0.5 s, so they contradicted each other in 12% of snapshots (for example "No hand" next to a recognised gesture). Both now refresh every 0.5 s (`REFRESH_S` in `views/dashboard.py`): 4% of snapshots, and those are the intended hold of a steady gesture for a few frames after the hand leaves.
- `requirements.txt` listed `opencv-python-headless`, but mediapipe depends on `opencv-contrib-python`, so every install had two OpenCV packages writing to the same `cv2` folder. It now lists `opencv-contrib-python` only. Checked in a new scratch venv: install succeeded, 284 tests passed, the clip check gave identical numbers and the app ran with the stand-in camera. Your existing `.venv` still has both and works; leave it, or recreate it with the commands in section 2.

**Found, not changed**

- meme_4 depends on who does it. With one of the two `11.48 AM` clips removed from training, the other (`11.48 AM #2`, the second person) was read as none on all its samples. With both in the dataset it is fine. Give each gesture at least two recordings per person, or more people.
- The browser's WebRTC stream starts at a lower resolution (480x320 seen) and rises to full size within a few seconds. This is normal WebRTC behaviour.
- The server log has a macOS warning that a class is defined twice (PyAV and OpenCV each bundle the same video library). It appears with either OpenCV package and caused no errors in any run.
- Opening a page URL directly (for example `/collector`) logs two 404s for `/collector/_stcore/health` in the browser console. That is Streamlit probing; the page loads normally.

**Tests:** 284 passed (`python -m pytest -q`), also in two fresh venvs.

**Still open:** your webcam run (README table), a third first_meme recording, more second_meme samples, recordings made with the webcam on the Data collector page, and meme titles, ratings and descriptions.

## Update, 14 October 2026: Meme 3, Meme 4 and none

- Imported 11 new clips with `python import_videos.py "Meme 3" "Meme 4" "None"`: meme_3 (both open hands raised, 3 recordings, 48 samples), meme_4 (one hand over the eyes, 4 recordings, 127 samples) and none (random hand shapes and movement, 4 recordings, 119 samples). Every clip was distinct; none were skipped.
- The folder images became the memes: `assets/memes/meme_3.jpg` and `assets/memes/meme_4.jpeg`. Titles, ratings and descriptions are still empty for you to set.
- Retrained: 380 samples, 16 recordings, 5 gestures. Held-out accuracy 97.4%, macro F1 0.973, cost 0.1056 at l2 0.01. Mistakes: none read as first_meme 4 times and as second_meme 2 times, plus 3 single errors. At the 70% cutoff 92% of predictions are accepted and 98.6% of those are right.
- l2 0.01 is the smallest option in `GD_L2_OPTIONS`. Smaller values (0.003 to 0.0003) were tried in a scratch folder: held-out cost falls to 0.0658 but accuracy stays at 97.4%, and the model becomes so confident that at the 90% cutoff wrong answers still get through (98.9% correct, against 100% at l2 0.01). The options were left unchanged.
- Checked in the browser with the stand-in camera: meme_3 and meme_4 are recognised at over 99% and their memes show; the none clip shows No gesture, no meme, and adds nothing to Recent detections. These clips are training data, so this checks the wiring, not accuracy. Tests: 266 passed.
- The previous data, model and memes.json are saved in `docs/handoff/snapshots/before-meme3-meme4-none/`.
- Still open: a third first_meme recording, more samples for second_meme, first_meme and meme_3, clips from a different room or lighting, and a real webcam run (Stage 8).

## Update, 13 October 2026: Stage 7

- The Recognition panel now shows the steady gesture (4 of the last 7 frames), the same one the meme panel uses, with a Checking state while a gesture is being confirmed and a No gesture state for `none`.
- Recent detections: time, gesture and confidence, newest first. One entry per change of steady gesture, or the same gesture after a pause over `HISTORY_REPEAT_GAP_S` (2 s). Kept in memory for the browser session only; the privacy page says so.
- New tiles: Latest gesture (with time) and Recognised this session.
- Checked in the browser with the stand-in camera at desktop width and 390px. Tests: 266 passed.
- Still open: Stage 8 (a real webcam run end to end), plus the data items listed below.

## Update, 13 October 2026: Stage 5 check

Stages 5 and 6 are built (see `README.md`). Sections 1 to 7 below describe the earlier Stage 4 session; section 6's open items 1, 2 and 4 are done.

- Live recognition was run in the browser with a stand-in camera playing frames from the real clips. Every state behaved as specified. This checks the wiring, not accuracy, because those clips are the training data.
- Fixed: the FPS tile overstated the frame rate when frames arrive unevenly (24 shown for a 15 fps stream). `vision.py` now averages the gaps between frames. Test: `tests/test_vision.py`.
- Changed: model scores that round to 100% or 0% now read "over 99%" or "under 1%" (`ui.score_pct`).
- Tests: 250 passed.
- Still open: a real webcam run, a `none` gesture, a third distinct `first_meme` recording, clips for `Meme 3` and `Meme 4` (each folder holds only an image so far), and meme titles, ratings and descriptions.

## 1. What changed in this session

Six critique-and-improve rounds on the Stage 4 site. Full evidence and scores are in `docs/ui-critique-log.md`. Summary:

| Round | Change |
|---|---|
| 1 | Shared staleness check; dashboard "Retrain needed"; test-set line on the performance page; collector captions and legend; pluralisation |
| 2 | Camera status above the video; right column in brief order; larger meme slot |
| 3 | Halfway-line mark in the header; Live statistics as a card |
| 4 | Heading order; table captions and scope; confusion-matrix legend; focus outline; status region |
| 5 | Scrollable table regions; responsive tiles; zero overflow at 390px in the stand-in render |
| 6 | Progress strip on the dashboard; readiness line on the performance page; header mark spacing fix |

Changed files: `ui.py`, `train_model.py`, `data_collector.py`, `views/dashboard.py`, `views/collector.py`, `views/performance.py`. New: `tests/test_status.py`, `docs/` (this folder, the critique log, and screenshots). `app.py`, `config.py`, `vision.py`, `features.py` and the legal pages are unchanged.

The original Stage 4 source is saved in `docs/handoff/snapshots/stage4-before-critique/`. `docs/handoff/changes-stage4-to-critiqued.diff` shows every change as a unified diff.

## 2. Run it on the Mac

These commands are from `README.md`. Run them in the project folder.

```bash
cd "/Users/kavishseema/Desktop/Passion Project"
rm -rf .venv                      # the existing .venv was built for another machine setup; recreate it
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python download_models.py --pose  # once, if the model files are missing
streamlit run app.py
```

Open http://localhost:8501 in Chrome, press Start camera and allow access.

## 3. Test it

```bash
source .venv/bin/activate
python -m pytest -q
```

Expect about 107 tests. In the review sandbox, 102 passed, 4 Streamlit AppTest tests were not run (they need Streamlit), and 1 `capsys` test was skipped. The Mac run is the first run of those 5.

## 4. Pages and components

| Page (file) | What it does |
|---|---|
| Live dashboard (`views/dashboard.py`) | Camera, progress strip, recognition placeholder, meme placeholder, live statistics, recent detections placeholder |
| Data collector (`views/collector.py`) | Camera, record a gesture, per-gesture status, manage data |
| Model performance (`views/performance.py`) | Readiness, train, test metrics, per-gesture table, confusion matrix, confusion pairs, cutoffs, split, validation comparison |
| Privacy policy, Terms (`views/privacy.py`, `views/terms.py`) | Legal pages; show a warning until operator details are set in `config.py` |

Shared helpers in `ui.py`: `inject_css`, `page_header` (with the halfway-line mark), `tag`, `tile`, `esc`, `html_table` (captions, scope, scroll region), `confusion_table` (captions, legend, scroll region), `camera_widget` (single start-stop control), `camera_state`, `hand_tag`.

## 5. Data contracts

**`data/samples.csv`.** One row per frame. Columns: `session_id`, `label`, `person`, `timestamp`, then feature columns `f000` to `f{n-1}`. `n` comes from `features.feature_length("hands")`. Written by `DatasetStore.append`. Validated by `DatasetStore.load`.

**`data/dataset_meta.json`.** Feature mode the samples were recorded with. A mismatch is an error.

**`models/training_report.json`.** Written by `train_model.train()`. Keys used by the UI: `trained_at`, `model_name`, `feature_mode`, `labels`, `dataset` (`rows_loaded`, `dropped`), `split` (`train`, `val`, `test`, each with `sessions` and `samples`), `candidates`, `selected`, `test` (`accuracy`, `macro_f1`, `samples`, `labels`, `per_class`, `confusion_matrix`, `top_confusions`, `thresholds`), `warnings`.

**`models/gesture_model.joblib`** and **`models/label_mapping.json`.** Written together. A failed run leaves the previous pair untouched.

**Shared check.** `train_model.staleness(report, dataset_rows, feature_mode)` returns a list of reasons the model is out of date. Empty means current.

## 6. Open items

See `03_REQUIREMENTS_AND_CHECKLIST.md`. The main ones:

1. Stage 5: live recognition (`predictor.py`, not yet written).
2. Stage 6: metadata file, meme images, meme panel.
3. Stage 7: smoothing in use, recent detections, total and latest gesture.
4. The video-upload decision (checklist section F).
5. A real camera and real recordings, then a real training run.

## 7. How to verify locally (manual steps, on the Mac)

1. Launch the app. Confirm each page loads with no red error box.
2. Camera: Start camera, allow access, check that "Camera connected" appears and landmarks draw when a hand is visible. Stop camera; check the status returns to "Camera off".
3. Recording: pick or name a gesture, Start camera first, Start recording, hold the gesture for 3 seconds of countdown, then check the sample count rises and the bar fills. Repeat in 3 separate recordings per gesture, in different light and distances.
4. Training: with at least 2 gestures and 3 recordings each, press Train model. Check the warning, the metrics and the confusion matrix. Remember these are measured on recordings the model did not learn from, and the warnings say how thin that evidence is.
5. Staleness: after training, record more samples. The dashboard should say "Retrain needed". Retrain, and it should return to "Trained".
6. Narrow window: resize the browser to a phone width. Check that tables scroll inside their own box and the page does not scroll sideways.
