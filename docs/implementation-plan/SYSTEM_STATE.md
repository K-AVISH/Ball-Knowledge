# System state: Ball Knowledge Vision AI

One verified picture of the system, joined from the Backend, Frontend and AI/ML handoffs and
checked against the code. Written by the implementation strategist.

## 0. Snapshot

| Item | Value | How it was checked |
|---|---|---|
| Snapshot time | 17 October 2026, 16:29 to 16:37 IST | `date` at the start and end of the checks |
| Other sessions | None running: no Streamlit server, training, import or replay process | `ps` and `lsof` on ports 8500 to 8599 at 16:36 |
| Code changes during the snapshot | None. The newest code file is `config.py` (13:43). Only `.DS_Store` files and one handoff in `Implementation Stratergist/` changed after 14:31 | `find -newermt "2026-10-17 14:31"` |
| Code baseline | The live folder's code, tests, data, model and memes are byte-for-byte the same as `frontend-handoff-2026-10-17.zip` (made 14:30). Only some docs differ | `diff -rq` of the unzipped archive against the folder |
| Test result | **413 passed in 71.96 s** (16:30:57 to 16:32:13) | `.venv/bin/python -m pytest -q` |
| Python and key packages | Python 3.14.7; streamlit 1.65.0; streamlit-webrtc 0.78.1; mediapipe 1.1.0; scikit-learn 1.9.1; numpy 2.5.4; pandas 3.0.6; joblib 1.6.0; pytest 9.1.1; opencv-contrib-python 5.0.0.93 **and** opencv-python-headless 5.0.0.93 (see CONFLICTS N4) | `pip list` in `.venv` |

Nothing in `data/`, `models/` or `assets/memes/` was changed. Training and the clip replay ran on
scratch copies in this session's scratchpad folder (`BALLKNOWLEDGE_DATA_DIR`, `BALLKNOWLEDGE_MODEL_DIR`).

## 1. End-to-end flow, camera to meme

Departments: **B** Backend, **F** Frontend, **M** AI/ML, **O** Owner. Sources: `docs/backend-handoff/ARCHITECTURE.md`
section 1, `docs/ml-handoff/ARCHITECTURE.md` section 1, `docs/frontend-handoff/ARCHITECTURE.md`
sections 2 and 3, and the code named in each row (read by the strategist).

| Step | What happens | Module | Owner |
|---|---|---|---|
| 1 | The browser sends webcam frames over WebRTC. One Start camera / Stop camera button. No STUN or TURN server (`iceServers: []`), so it only works on the same machine | `ui.camera_widget` (streamlit-webrtc 0.78.1) | F |
| 2 | Each frame is mirrored, timed (FPS, latency) and handed to the landmark hook. Errors go into the stats, never raised | `vision.FrameProcessor.process` | B |
| 3 | MediaPipe hand landmarker (Google, pretrained) finds up to 2 hands, 21 points each. A failed start retries every 2 s | `vision.LandmarkHook`, `vision.MediaPipeDetector`, `models/mediapipe/*.task` | B |
| 4 | Landmarks become one 126-number vector: wrist at origin, scaled by hand size, aspect corrected, left hand mirrored, missing hand = zeros, no hand = `None` | `features.correct_aspect`, `features.build_feature_vector` | M (definition), B (call site) |
| 5a | Data collector page: at most 10 vectors per second are recorded and saved as one recording | `data_collector.Recorder`, `DatasetStore.append`, `storage` atomic write and lock, `data/samples.csv` | B (store), F (`views/collector.py`) |
| 5b | Live dashboard: the newest vector goes to a worker thread; older ones are skipped | `predictor.LiveRecognizer.offer` | B |
| 6 | The model gives 5 probabilities. Top score at or above 0.70 is RECOGNISED, below is UNRECOGNISED | `predictor.Predictor.predict`, `gd_model.GradientDescentClassifier.predict_proba` | M (model and rule), B (threading) |
| 7 | Steady vote: a label must be recognised in 4 of the last 7 classified frames. Steady changes go to the in-memory recent detections log (repeat gap 2 s, `none` never logged) | `LiveRecognizer.steady`, `predictor.DetectionLog` | M (rule), B (code) |
| 8 | The page polls every 0.5 s (fragments) and reads `latest()`, `steady()`, `history()` | `views/dashboard.py` (`camera_status`, `live_panels`, `session_panels`) | F |
| 9 | The steady label is looked up in `memes.json`; the image is shrunk to 900 px / 250 KB and sent as a data URI. Every other state shows a message in the same 4:3 frame. Steady `none` shows "No gesture", never a meme | `ui.result_card`, `ui._meme_view`, `dataset_manager.MemeLibrary` | F (panel), B (library), O (content) |
| Offline | `train_model.py` or the Train model button: validate, leave-one-recording-out for 6 penalties x 16 recordings, pick l2 by lowest held-out cost, refit, save 3 files together | `train_model.train`, `TrainingJob`, `save_artifacts` | M (recipe, evaluation), B (job, locks, saving) |
| Offline | `import_videos.py` turns clips into samples through steps 2 to 5a; `check_pipeline.py` replays clips through steps 2 to 7 | same modules | B, M |

## 2. Interfaces between departments

"Producer" writes or defines it, "consumer" reads it. "Breaks" is what fails if one side changes alone.

| # | Interface | What crosses | Producer | Consumer | Breaks if one side changes |
|---|---|---|---|---|---|
| I1 | Feature vector | 126 floats: `f000-f062` right hand, `f063-f125` left hand mirrored; 225 in `hands+pose` mode | `features.py` (M) via `vision.LandmarkHook` (B) | `data_collector` (B), `gd_model`/`train_model` (M), `predictor` (B/M) | Any change to length or meaning makes `samples.csv` unusable; `dataset_meta.json` blocks mixing, and `Predictor` refuses a model whose `n_features_in_` differs. All samples must be re-extracted from video |
| I2 | `data/samples.csv` | `session_id` (12 chars), `label`, `person`, `timestamp`, `f000...` at `%.6g` | `DatasetStore` (B), Data collector page (F), `import_videos.py` (B) | `train_model` (M), `check_pipeline` (M/B), pages | Column rename breaks training and staleness. `session_id` is the unit of the held-out split (owner rule 2) |
| I3 | `data/dataset_meta.json` | `feature_mode`, `feature_length` | `DatasetStore` (B) | `DatasetStore` on every load | Mismatch with `config.FEATURE_MODE` makes `DatasetStore` refuse the data |
| I4 | Model files | `gesture_model.joblib` (pickled `GradientDescentClassifier`), `label_mapping.json` (index to id), `training_report.json` | `train_model.save_artifacts` (B writes, M content) | `Predictor.load` (B), Model performance page (F), `check_pipeline` (reads `cost.l2`) | Written as one set (report renamed last). `Predictor.load` refuses: labels that differ from the report, wrong feature mode or length, and a model whose SHA-256 differs from `artifacts.model_sha256` |
| I5 | Report fields read by the page | `trained_at`, `model_name`, `feature_mode`, `test.{accuracy, cost, macro_f1, per_class, labels, confusion_matrix, top_confusions, thresholds}`, `evaluation.{recordings, per_recording}`, `cost.{history, training_cost, steps, slope_at_end, converged, l2, l2_options}`, `dataset.dropped`, `warnings` | `train_model` (M/B) | `views/performance.py` (F) indexes these keys directly | Renaming or removing a key crashes the page (no fallback except a missing `cost`, which shows "older version" and hides the results) |
| I6 | Report protection fields | `dataset.fingerprint` (SHA-256 of `samples.csv`), `artifacts.model_sha256`, `cost.augmentation` | `train_model` (B, M) | `Predictor.load`, `staleness()` | Optional when reading: older reports fall back to row counts and "no augmentation" |
| I7 | `assets/memes/memes.json` | id to `gesture_name`, `meme_title`, `image_path` (inside `assets/memes/`), `ball_knowledge_level`, `description`; limits 60/80/40/400 chars; images 10 MB | `MemeLibrary.update` via Memes page (F) and CLI (B); content by O | `ui._meme_view`, `ui.meme_thumb`, `dm.display_name` (every page) | Unreadable file: dashboard shows "Memes cannot be shown". `MEME_MAX_UPLOAD_MB` must equal `server.maxUploadSize` (tested). `none` has no record |
| I8 | `Predictor` API | `Predictor.load(...)` raising `NotTrainedError` / `PredictorError`; `.labels`, `.warnings`, `.threshold`; `predict(vector) -> Prediction(status, label, confidence, top, threshold, inference_ms, at, error)` | `predictor.py` (B) | `ui.load_predictor` (F), cached by the three files' modification times | Status names `NO_HAND`, `UNRECOGNISED`, `RECOGNISED`, `ERROR` drive every state in `ui.result_card` |
| I9 | `LiveRecognizer` API | `offer(vector)`, `latest()`, `steady() -> Steady(label, confidence, votes, frames)`, `history() -> (entries, total)`, `use(predictor)`, `reset()`, `classify(vector, at)` | `predictor.py` (B, rule from M) | `views/dashboard.py`, `ui.history_card` (F); `check_pipeline.py` | A generation counter drops results from an older model after `use()` or `reset()`; keep it if threading changes |
| I10 | Training job progress | `train_model.training_job()`, `TrainingJob.start(**kw) -> bool`, `status()` with `run, running, done, total, started_at, finished_at, report, error`; total = l2 options x recordings + 1 = **97** today | `train_model.py` (B) | `views/performance.py` (F) progress bar and the one-time result message | Renaming a field breaks the progress bar. A run started in the terminal is not visible to the page (one job per process) |
| I11 | Staleness | `staleness(report, rows, feature_mode, dataset_fingerprint=)` returns sentences ending "Train again to include the changes." | `train_model.py` (B) | dashboard `ui.stale_notice` and performance page `st.warning` (F) | The pages show the sentences as they are. It checks rows, fingerprint and feature mode only, not training settings (CONFLICTS N10) |
| I12 | `DatasetStore` | `load()`, `load_with_fingerprint()`, `fingerprint()`, `row_count()`, `session_times()`, `summary()`, `append`, `delete_session`, `delete_label` | `data_collector.py` (B) | collector, dashboard, performance pages (F); `train()` | Reads are cached by inode, mtime and size; callers get copies |
| I13 | Safe file writes | `storage.atomic_write_bytes/_text`, `replace_together`, `locked(path, timeout)` raising `StorageBusyError` | `storage.py` (B) | every writer | Any new file writer must use them, or a crash or a second tab can corrupt or lose data |
| I14 | Lock files | `data/.samples.csv.lock` (waits 10 s), `assets/memes/.memes.json.lock` (waits 10 s), `models/.gesture_model.joblib.lock` (held for a whole training run, a second run fails at once) | `storage.locked` (B) | OS only | Harmless to delete while nothing runs. Present today: only the model lock (empty, from the ML session's 13:46 run) |
| I15 | Environment overrides | `BALLKNOWLEDGE_DATA_DIR`, `BALLKNOWLEDGE_MODEL_DIR`. No override for `assets/memes/` or `models/mediapipe/` | `config.py` (B) | every department's testing; `tests/conftest.py` fails a run that changes the real folders | Testing the Memes page safely needs a copy of the whole project folder |
| I16 | Live decision settings | `DEFAULT_CONFIDENCE_THRESHOLD = 0.70`, `SMOOTHING_WINDOW = 7`, `MIN_STABLE_FRAMES = 4`, `HISTORY_REPEAT_GAP_S = 2.0`, `NONE_LABEL = "none"` | `config.py` (M decides, O approves) | `predictor` (B), `ui.result_card` and the performance cutoff table (F) | A change alters how often memes appear; must be re-checked with `check_pipeline.py` and the cutoff table |
| I17 | Training warnings with names | `report["warnings"]` (ids) and `make_warnings(report, name)` | `train_model` (M/B) | performance page (F) | Names come from `memes.json`; the dashboard never shows these |

## 3. Measured numbers today

Every number below was measured, not estimated. "Strategist" means re-measured in this session.

### 3.1 Model

Source: `models/training_report.json` (trained `2026-10-17T13:47:21`), read at 16:30.

| Measure (leave one recording out) | Value |
|---|---|
| Held-out accuracy | 0.9711 (369 of 380 right, 11 wrong) |
| Held-out balanced cross-entropy | 0.0747 |
| Macro F1 / weighted F1 | 0.9722 / 0.9711 |
| Mean confidence when right / when wrong | 0.9537 / 0.6827 |
| Cutoff 0.5 / 0.6 / 0.7 / 0.8 / 0.9: share accepted | 99.7% / 98.2% / 95.8% / 91.6% / 82.4% |
| Same cutoffs: accuracy of accepted | 97.4% / 98.4% / 98.6% / 99.1% / 100% |
| Chosen l2 (of 1.0, 0.3, 0.1, 0.03, 0.01, 0.003) | 0.003, the smallest in the grid |
| Steps to the minimum; final training cost | 2,658; 0.048664 (over the augmented rows) |
| Training accuracy (not a quality measure) | 1.0 |
| Augmentation | 4 copies per sample, 15 degrees, noise 0.01, seed 0 |
| scikit-learn version saved | 1.9.1 (same as installed) |
| Per class F1 | first_meme 0.958, meme_3 1.000, meme_4 0.984, none 0.953, second_meme 0.966 |
| Main errors | `none` read as a gesture 7 of 11 (4 as first_meme, 2 as second_meme, 1 as meme_4); meme_4 read as none 3 |

### 3.2 Checks re-run by the strategist

| Check | Result | Command |
|---|---|---|
| Report matches the data and model | `dataset.fingerprint` = SHA-256 of `data/samples.csv` (`d4e05a87...`); `artifacts.model_sha256` = SHA-256 of `gesture_model.joblib` (`1e5813fc...`) | `shasum -a 256` |
| Retrain on a scratch copy | **34.78 s** wall time. The new model file has the **same SHA-256** as the live one, and the report differs only in `trained_at`. Training is deterministic, and the live model is exactly what today's code, data and settings produce | `BALLKNOWLEDGE_DATA_DIR=... BALLKNOWLEDGE_MODEL_DIR=... python train_model.py` (16:33:40 to 16:34:15) |
| Clip replay through the live path | **A wrong gesture was shown in 0 of 16 clips.** Right / unsure / no hand: first_meme 87% / 8% / 0%, meme_3 89% / 10% / 0%, meme_4 60% / 7% / 33%, none 86% (No gesture) / 13% / 1%, second_meme 87% / 12% / 0%. The 17th clip is the known byte copy of a first_meme clip and is skipped. Matches `docs/ml-handoff/RESULTS_AND_DATA.md` section 3 exactly | `python check_pipeline.py "First meme" "Second meme" "Meme 3" "Meme 4" None` on scratch copies (16:34:33 to 16:35:17) |
| Integration of the three departments' 17 October edits | Every change each handoff lists is present in the code (see section 5) | `grep` per change; `diff -rq` against the three zips |

### 3.3 Data

Source: `data/samples.csv` (modified 14 October 11:55), read with pandas at 16:31.

| Gesture | Samples | Recordings | Samples per recording |
|---|---|---|---|
| first_meme | 58 | 2 | 34, 24 |
| meme_3 | 48 | 3 | 13, 18, 17 |
| meme_4 | 127 | 4 | 34, 21, 39, 33 |
| none | 119 | 4 | 25, 27, 30, 37 |
| second_meme | 28 | 3 | 10, 10, 8 |
| **Total** | **380** | **16** | |

- Sample dates: 13 and 14 October 2026 only.
- The `person` column is empty in all 380 rows (report: `"people": 0`). "About 2 people" (ML handoff) and "mostly one person" (strategist prompt) come from the sessions' notes and cannot be checked from the data.
- Targets in `config.py`: 100 to 300 samples (`TARGET_MIN_PER_CLASS`, `TARGET_GOOD_PER_CLASS`) and 3 recordings (`MIN_SESSIONS_PER_CLASS`) per gesture. Three gestures are under 100 samples; first_meme is under 3 recordings.

### 3.4 Memes

Source: `assets/memes/memes.json` (modified 14 October 11:55). Four records (first_meme, meme_3, meme_4,
second_meme), each with an image file present. Every `meme_title`, `ball_knowledge_level` and
`description` is empty. `none` has no record, by design.

### 3.5 Not verified by the strategist

| Claim | Why not verified |
|---|---|
| The owner's webcam works with the 17 October model | No webcam in this session. The frontend reports the owner ran README step 3 on 17 October, but not at what time; the model changed at 13:47 (CONFLICTS N6) |
| The UI in a browser after the 17 October changes | Not opened in this session; the frontend's check (CHANGES section 5) used a stand-in camera. Tests cover the HTML |
| Safari, screen readers | Never tested by any department |
| `requirements.txt` floors (`streamlit>=1.40`, `mediapipe>=0.10.14`) actually work | Only the installed versions were tested |

## 4. Acceptance criteria (`Context.md` section 10)

| # | Criterion | State | Evidence |
|---|---|---|---|
| 1 | Launches locally, camera with permission | Met, by the owner's report | Owner, 14 October (all handoffs); not re-checked with the 17 October model |
| 2 | Recognises gestures with a trained classifier | Met | Report and retrain above |
| 3 | Shows the correct image for a recognised gesture | Met on clips | Replay: 0 wrong memes in 16 clips; `tests/test_status.py` |
| 4 | Rating and description match the metadata | Met in code, no content yet | `ui._meme_view` shows them when set; all empty today; README steps 7 to 9 passed on a scratch copy on 14 October (`New files fopr critiquing/03_...` section M) |
| 5 | Rejects uncertain predictions | Met | Threshold plus 4-of-7 vote; replay "unsure" shares; tests |
| 6 | A new gesture can be added | Met in code | Collector, training and Memes page; AppTest runs in `tests/test_pages.py` |
| 7 | Dashboard updates during live use | Met with a stand-in camera | Frontend CHANGES section 5 |
| 8 | Training metrics and held-out test | Met | Model performance page, report |
| 9 | Camera errors, missing images and models handled | Met | `ui.result_card` states; `tests/test_status.py`, `tests/test_predictor.py` |
| 10 | README explains install, collection, training, running | Met, with small stale lines | CONFLICTS N18 |

## 5. Integration check (prompt conflict 6)

Three sessions edited `ui.py`, `views/dashboard.py` and `views/performance.py` on 17 October without
git. The suite passing is necessary, not sufficient, so each listed change was looked for in the code:

| Department | Change (from its handoff) | Found in code |
|---|---|---|
| Backend | Atomic writes and locks for samples, memes, training | `data_collector.py` (5 uses), `dataset_manager.py` (3), `train_model.py` (2) |
| Backend | Model checksum written and checked | `train_model.py` and `predictor.py` (`model_sha256`) |
| Backend | Dataset fingerprint passed to staleness on both pages | `views/dashboard.py` (3 lines), `views/performance.py` |
| Backend | Background `TrainingJob` with progress | `train_model.py` (`class TrainingJob`, `training_job`); `views/performance.py` progress fragment |
| Backend | Detector retry every 2 s, serialised calls | `vision.py` (`retry_s`, lock) |
| Backend | Parsed CSV cache | `data_collector.py` (`_snapshot`) |
| Backend | Disabled green button CSS | `ui.py` (`:disabled` selectors) |
| Backend | Test guard on real folders | `tests/conftest.py` |
| Frontend | One Meme panel, thumbnails, notices, stale notice | `ui.py` (`result_card`, `meme_thumb`, `notice`, `stale_notice`, `Html`, `_thumb_uri`); removed functions absent |
| Frontend | Subgrid tiles, `:has()` notices, camera button without shadow | `ui.py` |
| Frontend | Per-page tab title | `app.py` (`page_title`) |
| Frontend | Memes preview mode, model tag "softmax regression" | `views/memes.py`, `views/performance.py` |
| ML | Augmentation and the 0.003 option | `features.augment_hands`, `gd_model.py` params and `__setstate__`, `config.GD_AUGMENT_*`, `train_model.make_model` |
| ML | Clip replay uses the same recipe | `check_pipeline.ModelSource` calls `tm.make_model(l2)` with the saved report's l2 |

Result: nothing listed was lost. Limits: this checks that each department's listed changes exist,
not that unlisted edits were kept. The full suite, the bit-identical retrain and the clip replay
cover behaviour; the browser look was not re-checked by the strategist.
