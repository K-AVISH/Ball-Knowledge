# Ball Knowledge Vision AI: project context (Stage 8 of 8)

Snapshot: 12 October 2026, status table updated 14 October 2026. Source of truth: `Context.md`, `Instructions.md`, `README.md` and `LAUNCH_CHECKLIST.md` in the project root. If this file and those disagree, the conflict is logged in section 6.

**Note on the uploaded files.** The four uploads (frontend context, requirements checklist, critique prompt and handoff) describe Prognos, an EV fault-detection dashboard. They are not about this project. This folder reuses only their structure: context, checklist, build and critique prompt, and handoff. None of their content applies here.

## 1. What the project is

A local, webcam-driven dashboard. The user performs a gesture, a classifier trained on the user's own recordings recognises it, and the matching meme, its Ball Knowledge rating and a description appear. The build is local-first: no paid APIs and no cloud services.

The user is the developer and the only operator. They record the samples, train the model and add the memes.

## 2. Status by stage

| Stage | Scope | Code | Tests | Verified on real hardware or data |
|---|---|---|---|---|
| 1 | Dashboard and webcam | `app.py`, `ui.py`, `views/dashboard.py`, camera widget | Style and camera rule tests | No, needs a Mac camera |
| 2 | MediaPipe landmarks | `vision.py`, `download_models.py`; models in `models/mediapipe/` | `test_vision.py`, `test_landmark_hook.py` | No |
| 3 | Data collector | `views/collector.py`, `data_collector.py`, `features.py` | `test_data_collector.py`, `test_features.py` | No, `data/` has no samples yet |
| 4 | Training and evaluation | `train_model.py`, `gd_model.py`, `views/performance.py` | `test_train_model.py`, `test_gd_model.py`, `test_status.py` | Yes, on 16 real recordings (380 samples, 5 gestures including `none`), 14 October 2026. first_meme still has only 2 recordings |
| 5 | Live recognition | `predictor.py`, wired into `vision.py` and `views/dashboard.py` | `test_predictor.py`, `test_status.py` | Stand-in camera playing the real clips (13 October 2026). Not on a real webcam yet |
| 6 | Metadata manager and meme display | `dataset_manager.py`, `assets/memes/memes.json`, meme panel in `ui.py` | `test_memes.py` | Stand-in camera only (meme_3 and meme_4 checked 14 October 2026). Titles, ratings and descriptions not set yet |
| 7 | Smoothing, history and statistics | `predictor.py` (`steady`, `DetectionLog`), `ui.py` (recognition, history, tiles), `views/dashboard.py` | `test_predictor.py`, `test_status.py` | Stand-in camera playing the real clips (13 October 2026) |
| 8 | End-to-end testing | `check_pipeline.py`; browser run on a scratch dataset; fixes in `views/dashboard.py` and `requirements.txt` | `test_check_pipeline.py`, `test_predictor.py` | Clips and stand-in camera, 14 October 2026: no wrong gesture in 16 held-out clips. Your webcam run is still to do |

Optional pages in `Instructions.md` (Dataset Manager and Prediction History) are not built.

## 3. How recognition must behave

These rules come from `Context.md` section 3 and `Instructions.md` sections 2 and 6. They govern Stage 5 onwards.

1. No hand in view means no prediction. Show a clear "No hand detected" state.
2. A prediction below the configured confidence threshold (`DEFAULT_CONFIDENCE_THRESHOLD`, currently 0.70) is shown as "Unrecognised", never as a guess.
3. A gesture must win a voting window (`SMOOTHING_WINDOW` = 7 frames) and remain stable (`MIN_STABLE_FRAMES` = 4) before it changes the main result.
4. A meme is shown only for a recognised, stable gesture. Never show a random or unrelated meme.
5. The Ball Knowledge rating and description come from metadata. The vision model did not discover them. Say so in the UI.
6. Recent detections record meaningful changes in the result, not every frame.
7. Camera disconnection, missing models, invalid metadata and missing images are handled with visible messages, never silent failures.

## 4. Data and privacy rules

- `data/samples.csv` holds landmark feature numbers, one row per frame. Columns: `session_id`, `label`, `person`, `timestamp`, then the feature columns `f000` onward. The feature length comes from `features.feature_length(mode)`.
- Only landmark numbers are stored. No images or video. `LAUNCH_CHECKLIST.md` and the privacy page both say so, and the code matches.
- `data/dataset_meta.json` records the feature mode the samples were collected with. Mixing modes is an error.
- Training splits by whole recording, so frames from one recording never appear in two sets. The split is repeatable for a fixed seed (`TRAIN_SEED` = 42).
- Each gesture needs at least 3 separate recordings to train (`MIN_SESSIONS_FOR_TRAINING`). Aim for 100 to 300 samples per gesture.
- A saved model is marked stale when the dataset row count or the feature mode changes. The dashboard and the performance page both show this.

## 5. Dashboard information contract

Right-hand column order from the brief: current prediction, meme, live statistics, recent detections. Left column: camera, with its status and hand tags below the video.

| Area | Shown to the user | Status |
|---|---|---|
| Camera | Status (off, connecting, connected), hand detection, landmark overlay toggle, Start and Stop | Built |
| Recognition | Steady gesture, confidence, Unrecognised, Checking and No gesture states, top scores | Built (Stages 5 and 7) |
| Meme result | Image, title, gesture label, rating, description | Built (Stage 6) |
| Live statistics | FPS, latency, number of classes, model state. Also total recognised and latest gesture | Built |
| Recent detections | Time, label, confidence | Built (memory only, per browser session) |
| Model performance | Test metrics, per-gesture table, confusion matrix, confidence cutoffs, data split, validation comparison | Built, from `training_report.json` |

## 6. Conflicts and assumptions

1. **Dashboard technology.** `Instructions.md` says "Figma for the web dashboard". `Context.md` specifies Streamlit, and the build uses Streamlit. Assumption: Streamlit.
2. **Startup model loading.** `Instructions.md` asks for the saved model to load at startup. Resolved in Stage 5: the dashboard loads the model once (`ui.load_predictor`) and reloads it only when the files change.
3. **Per-gesture confidence threshold.** `Context.md` lists `confidence_threshold` in each metadata record. The current code has one global default. Per-gesture thresholds are a Stage 6 decision.
4. **Gesture count.** `Context.md` suggests 5 to 10 gestures. The app trains with 2 or more. Assumption: the suggestion, not a hard limit.
5. **Optional pages.** The dataset manager and prediction history pages are optional in `Context.md`. Not built.
6. **Video upload.** Resolved 13 October 2026: `import_videos.py` turns local video files into samples through the live pipeline (see `README.md`, Import recorded videos).

## 7. Stack and environment

- Python 3. The venv in the project folder was created on macOS with Python 3.14 and is not portable. Recreate it on the Mac with the commands in `04_HANDOFF.md`.
- Streamlit (dark theme set in `.streamlit/config.toml`), streamlit-webrtc 0.78.1, OpenCV (opencv-contrib-python, the one MediaPipe installs), MediaPipe, NumPy, pandas, scikit-learn, joblib, pytest.
- Design rules, enforced by `tests/test_style_rules.py`: no emoji, no em dashes, no gradients, no animation, no pill shapes, no purple, no "made with" badges, a real favicon, and privacy and terms pages in the navigation. Corner radii are limited to 2, 4, 6 and 8 pixels, or 50%.
