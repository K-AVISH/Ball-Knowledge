# Ball Knowledge Vision AI: project context (all 8 stages built)

Snapshot: 14 October 2026, after Stage 8 and six critique rounds on the finished app. Sources of truth, in order: the code, `README.md`, then the original brief in `Context.md` and `Instructions.md`, then `LAUNCH_CHECKLIST.md`. Where this file and the brief disagree, the conflict is listed in section 7.

**About the structure.** These four files (context, build and critique prompt, checklist, handoff) copy the structure of four uploaded handoff files that were about a different project (Prognos, an EV fault-detection dashboard). Only the structure was reused. None of their content applies here.

## 1. What the project is

A local webcam dashboard. You show a hand gesture; a classifier trained on your own recordings recognises it; the dashboard shows the matching meme with its Ball Knowledge rating and description. Everything runs on your Mac: no paid APIs, no cloud services, no accounts.

You are the developer and the only user. You record or import the samples, train the model, and set the memes.

## 2. Status by stage

"Verified" says what was actually run. "Stand-in camera" means real clips or real recorded samples fed through the real code with the webcam simulated.

| Stage | Scope | Main files | Tests | Verified |
|---|---|---|---|---|
| 1 | Dashboard and webcam | `app.py`, `ui.py`, `views/dashboard.py` | `test_style_rules.py` | Browser run with a stand-in camera (13 and 14 October). Not on your webcam |
| 2 | Hand landmarks | `vision.py`, `features.py`, `download_models.py` | `test_vision.py`, `test_landmark_hook.py`, `test_features.py` | MediaPipe on all 16 real clips (`import_videos.py`, `check_pipeline.py`) |
| 3 | Data collection | `views/collector.py`, `data_collector.py`, `import_videos.py` | `test_data_collector.py`, `test_import_videos.py` | 16 real clips imported (380 samples). One clip recorded through the Data collector page in the browser matched its imported samples (median distance 0.15, against 0.50 to other recordings) |
| 4 | Training and evaluation | `train_model.py`, `gd_model.py`, `views/performance.py` | `test_train_model.py`, `test_gd_model.py`, `test_status.py` | Trained on the real data: 97.4% held-out accuracy, macro F1 0.973. Reproduced exactly on a second machine on 14 October |
| 5 | Live recognition | `predictor.py` (`Predictor`, `LiveRecognizer`) | `test_predictor.py` | Stand-in camera with the real clips |
| 6 | Memes | `dataset_manager.py`, `views/memes.py`, `assets/memes/` | `test_memes.py`, `test_display.py` | Meme panel with a stand-in camera. The Memes page (added 14 October) has not run in real Streamlit |
| 7 | Smoothing, history, statistics | `predictor.py` (`steady`, `DetectionLog`), `views/dashboard.py` | `test_predictor.py`, `test_status.py` | Stand-in camera with the real clips |
| 8 | End-to-end testing | `check_pipeline.py` | `test_check_pipeline.py` | All 16 clips replayed, each by a model that never saw it: no wrong gesture shown in any clip. Your webcam run is still to do |

Tests: 284 passed on the Mac before the critique rounds. The rounds took the suite from 284 to 312 test cases (24 in the new `tests/test_display.py`, the rest from the style tests now also checking the new page and the critique log); in the review environment 307 passed and 5 could not run there (4 Streamlit AppTest tests, 1 `capsys` test).

## 3. How recognition must behave

From `Context.md` section 3 and `Instructions.md` sections 2 and 6. These are built; keep them true.

1. No hand in view means no prediction: "No hand detected".
2. A score below `DEFAULT_CONFIDENCE_THRESHOLD` (0.70) is "Unrecognised", never a guess.
3. A gesture becomes the result only after winning `MIN_STABLE_FRAMES` (4) of the last `SMOOTHING_WINDOW` (7) classified frames. Until then the panel says "Checking".
4. The `none` class (a hand, but no gesture) shows "No gesture" and never a meme.
5. A meme is shown only for the steady result, and only if its image is readable. Never a random or fallback meme.
6. The rating and description come from `assets/memes/memes.json`, written by you. The model does not produce them, and the panel says so.
7. Recent detections add one row per change of steady gesture, or the same gesture after a 2 second gap. Memory only, never saved.
8. Camera loss, missing or mismatched model files, an unreadable `memes.json` and missing images each show a visible message.
9. Confidence is the model's own estimate, not a calibrated probability. The cutoff table on the Model performance page is the evidence for the threshold.

## 4. Data and privacy rules

- `data/samples.csv`: one row per frame. Columns `session_id`, `label`, `person`, `timestamp`, then features `f000` onward (126 in `hands` mode).
- Only landmark numbers are stored. No frames, images or video from the camera or from imported clips.
- Meme images you choose are copied into `assets/memes/` on your Mac and go nowhere else.
- `data/dataset_meta.json` records the feature mode. Mixing modes is an error.
- Evaluation holds out whole recordings (leave one recording out), so no frame of a recording trains the model that tests it.
- A gesture needs 2 recordings to train and 3 for steadier numbers. Aim for 100 to 300 samples per gesture.
- The saved model is marked stale when the dataset's row count or the feature mode changes.
- The camera connection uses no STUN or TURN server (`ui.py` sets an empty list). The privacy page says so, corrected on 14 October.

## 5. Current data and model

| Gesture | Name shown | Recordings | Samples | Held-out F1 |
|---|---|---|---|---|
| first_meme | First meme | 2 | 58 | 0.949 |
| meme_3 | Meme 3 | 3 | 48 | 1.000 |
| meme_4 | Meme 4 | 4 | 127 | 0.988 |
| none | No gesture | 4 | 119 | 0.961 |
| second_meme | Second meme | 3 | 28 | 0.966 |

Model: softmax regression by gradient descent, l2 0.01, trained 14 October 2026 11:55. Held-out accuracy 97.4%, cost 0.1056. At the 70% cutoff 92% of predictions are accepted and 98.6% of those are right. Main mistakes: `none` read as first_meme (4) or second_meme (2). All clips were filmed in one room on one day, so treat these as a rough guide.

Meme titles, ratings and descriptions are empty for all four gestures.

## 6. Pages

| Page | What it shows |
|---|---|
| Live dashboard | Camera with status and hand tags; Recognition (steady gesture, confidence bar against the threshold, top scores); Meme result; below them Live statistics (latest gesture, recognised this session, gesture classes, FPS, latency, model) and Recent detections |
| Data collector | Camera, record a gesture (one Start/Stop recording button), dataset status per gesture with a legend, undo and delete |
| Model performance | Train button, held-out accuracy, cost, macro F1, per-gesture table, confusion matrix, mix-ups, confidence cutoffs, each recording held out (named by when it started), cost function details |
| Memes | What is set per gesture, a form for name, title, rating, description and image, and a live preview of the dashboard's meme panel |
| Privacy policy, Terms | Legal pages; warn until your name and contact email are set in `config.py` |

A gesture's name from the Memes page is used on every page.

## 7. Conflicts and assumptions

1. **Dashboard technology.** `Instructions.md` says "Figma for the web dashboard"; `Context.md` says Streamlit, and the app is Streamlit. Still undecided by you; assumed Streamlit.
2. **Per-gesture threshold.** `Context.md` lists a `confidence_threshold` per metadata record. The app uses one global threshold. Not built.
3. **Optional pages.** `Context.md` lists a Dataset Manager page and a Prediction History page as optional. The Memes page covers the meme part of the Dataset Manager. Prediction History is not built (recent detections are on the dashboard).
4. **Classifier.** The brief suggests a Random Forest baseline. The project switched to softmax regression by gradient descent on 13 October; gradient boosting and forests were measured and had a higher held-out cost.
5. **Video upload.** Decided 13 October: `import_videos.py` turns local video files into samples through the live pipeline.

## 8. Stack

Python 3 on macOS. Streamlit (dark theme in `.streamlit/config.toml`), streamlit-webrtc 0.78.1, opencv-contrib-python (the OpenCV that MediaPipe needs; only one OpenCV package), MediaPipe, NumPy, pandas, scikit-learn, joblib, Pillow (installed with Streamlit), pytest.

Design rules enforced by `tests/test_style_rules.py`: no emoji, no em dashes, no gradients, no animation, no pill shapes, no purple, no "made with" badges, a real favicon, legal pages in the navigation, corner radii of 2, 4, 6 or 8 pixels or 50%, one camera button and one record button.
