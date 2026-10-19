# Architecture

## 1. The live pipeline

```
Browser camera
  │  WebRTC (streamlit-webrtc, ui.camera_widget)
  ▼
vision.FrameProcessor.process(frame)              video thread, one per browser session
  │  mirrors the frame
  ├─ vision.LandmarkHook(frame)
  │    ├─ MediaPipeDetector.detect()              hands (and pose in "hands+pose" mode)
  │    ├─ draw_landmarks()                        skeleton overlay
  │    ├─ features.correct_aspect()               same numbers for 4:3, 3:2, 16:9 frames
  │    └─ features.build_feature_vector()         126 floats, or None when no hand
  │
  ├─ recorder.offer(vector)                       Data collector page only
  │    └─ data_collector.Recorder  ──►  DatasetStore.append()  ──►  data/samples.csv
  │
  └─ recognizer.offer(vector)                     Live dashboard only; returns at once
       └─ predictor.LiveRecognizer                worker thread "gesture-recognizer"
            ├─ Predictor.predict(vector)          softmax probabilities, threshold
            ├─ steady vote                        MIN_STABLE_FRAMES of last SMOOTHING_WINDOW
            └─ DetectionLog                       recent detections, memory only

Streamlit page (main thread, reruns every 0.5 s)
  reads FrameProcessor.get_stats(), LiveRecognizer.latest()/steady()/history()
  looks up the steady label in dataset_manager.MemeLibrary  ──►  meme panel
```

Offline paths reuse the same code:

```
import_videos.py   video file ─► FrameProcessor + LandmarkHook ─► Recorder ─► samples.csv
check_pipeline.py  video file ─► FrameProcessor + LandmarkHook ─► LiveRecognizer.classify ─► report
train_model.py     samples.csv ─► validate ─► leave-one-recording-out ─► pick l2 ─► fit ─► models/
```

## 2. Threads and ownership

| Thread | Owns | Talks to others through |
|---|---|---|
| WebRTC video thread | `FrameProcessor.process`, `LandmarkHook`, MediaPipe detector | `FrameProcessor` stats under a lock; `offer()` on recorder and recognizer |
| `gesture-recognizer` worker | Running the model | `threading.Condition` in `LiveRecognizer`. Only the newest frame is kept; frames that arrive while the model is busy are skipped. The worker exits after 5 s with no frames and restarts on the next `offer()` |
| `model-training` worker | One `train()` run started by the Train model button (`train_model.TrainingJob`) | `TrainingJob.status()` returns a frozen copy under a lock; the page polls it every 0.5 s while a run is going |
| Streamlit script thread | Page rendering, meme edits, starting training | Reads copies of state; never touches frames |

Per browser session (`st.session_state`): one `FrameProcessor`, one `LandmarkHook`, one
`LiveRecognizer`, one `Recorder`. Shared across sessions (`st.cache_resource` in
`ui.load_predictor`): the loaded `Predictor`, keyed on the model files' modification times, so
retraining is picked up without a restart. A load that overlaps a training run's renames can see
a new model beside the old report; `load_predictor` then tries again while the files keep changing
(three tries at most), instead of reporting a broken model.

The pages set `FrameProcessor.recorder` and `.recognizer` from their own thread; `process()`
reads each once per frame, so one set to `None` mid-frame is never called.

Shared across sessions by module-level registries: `train_model.training_job()` (one
`TrainingJob` per model file, so two tabs pressing Train model start one run) and the
parsed-CSV cache in `data_collector` (keyed by the file's inode, modification time and size).

`LiveRecognizer` has a generation counter. `reset()` or `use(new_predictor)` bumps it, and any
result computed for an older generation is dropped. Keep that if you change the threading.

Files are shared by every thread and by terminal scripts. Writers hold `storage.locked(path)`
(thread lock plus `fcntl.flock`) and replace files whole; readers take no lock. `train()` holds
the model file's lock for the whole run with no waiting, so a second run fails at once.

`FrameProcessor.process` never raises. Errors go into `VisionStats.error` so the stream stays alive.

## 3. Backend modules

Line counts as of 17 October 2026, after the refinement pass. None of these import Streamlit.

### `config.py`
All paths and tunables. Env overrides: `BALLKNOWLEDGE_DATA_DIR`, `BALLKNOWLEDGE_MODEL_DIR`.
Key values: `FEATURE_MODE="hands"`, `MAX_HANDS=2`, `DETECTION_CONFIDENCE=0.6`,
`COLLECT_RATE_HZ=10`, `GD_L2_OPTIONS=(1.0, 0.3, 0.1, 0.03, 0.01, 0.003)`,
`GD_AUGMENT_COPIES=4`, `GD_AUGMENT_ROTATION_DEG=15.0`, `GD_AUGMENT_NOISE=0.01`, `GD_AUGMENT_SEED=0`,
`DEFAULT_CONFIDENCE_THRESHOLD=0.70`, `SMOOTHING_WINDOW=7`, `MIN_STABLE_FRAMES=4`,
`HISTORY_LENGTH=10`, `HISTORY_REPEAT_GAP_S=2.0`, `NONE_LABEL="none"`.

### `vision.py` (342 lines)
- `FrameProcessor(frame_hook)`: `process(frame) -> frame`, `get_stats() -> VisionStats`,
  `get_latest_features()`, `reset()`. Attributes `recorder` and `recognizer` are set by the pages.
- `VisionStats`: fps, latency_ms, frames_processed, frame size, last_frame_time, hand/pose flags, error.
- `camera_is_live(stats, max_age_s=2.0)`.
- `MediaPipeDetector(use_pose)`: `detect(frame_bgr) -> Detection`, `close()`. Raises
  `ModelMissingError` when `models/mediapipe/*.task` is missing.
- `LandmarkHook(detector_factory=None, mode)`: callable `(frame) -> (frame, info)` where
  `info = {hand_detected, num_hands, pose_detected, features}`. Keeps the most confident
  hand per side. `detector_factory` lets tests inject a fake detector. A failed detector start
  is retried every `retry_s` (2 s), so the camera recovers once the model is downloaded.
  `detect()` calls are serialised by a lock.

### `features.py` (162 lines)
Pure NumPy.
- `feature_length(mode)`: 126 for `hands`, 225 for `hands+pose`.
- `correct_aspect(landmarks, width, height)`.
- `normalize_hand(landmarks, mirror)`: wrist at origin, divided by the largest wrist-to-landmark distance.
- `normalize_pose(landmarks)`: hip centre at origin, divided by shoulder width.
- `build_feature_vector(right, left, pose, mode)`: `[right 63][left 63](+[pose 99])`. A missing
  hand is zeros, so one hand and two hands are different patterns. The left hand is mirrored
  into the right hand's shape space. Returns `None` when there is nothing to classify.
- `augment_hands(X, copies, rotation_deg, noise, seed)`: extra training rows with each hand
  slightly turned about its wrist and jittered. Used only inside `fit`; nothing is saved.

### `gd_model.py` (183 lines)
`GradientDescentClassifier(l2=0.01, max_iter=20000, tol=1e-6, class_weight="balanced",
augment_copies=0, augment_rotation_deg=15.0, augment_noise=0.01, random_state=0)`, a scikit-learn compatible
estimator (`fit`, `predict_proba`, `predict`, `classes_`, `n_features_in_`). Softmax
regression; cost is class-balanced cross-entropy plus `(l2/2)*||W||^2`. Convex, starts from
zeros, deterministic. Chosen with the owner on 13 October after gradient boosting lost on
held-out cost. Changing the model type is the owner's call. The augmentation parameters are
used only in `fit`; `train_model.make_model` sets them from config. `__setstate__` gives
pickles from before 17 October the new parameters (as off), so they still load.

### `train_model.py` (680 lines)
`python train_model.py`, or the Train model button.
- `validate_dataset(df, feature_length)`: drops and counts bad rows.
- `check_recordings(df, min_sessions=2)`: raises `TrainingError` if a gesture has too few recordings.
- `held_out_probabilities(df, labels, l2, on_fit=None)`: leave-one-recording-out predictions.
- `evaluate_proba(...)`: accuracy, cost, per-class precision/recall/F1, confusion matrix, cutoff table.
- `train(store=None, ..., progress=None)`: the whole run; picks l2 by lowest held-out cost, refits
  on all data, calls `save_artifacts`. Returns the report dict as saved. Holds the model file's
  lock for the whole run (a second run raises `TrainingError` at once). `progress(done, total)`
  counts models fitted: l2 options x recordings, plus 1 (97 with today's data).
- `make_model(l2)` (with the config augmentation), `augmentation_settings(model)`: recorded as
  `report["cost"]["augmentation"]`.
- `save_artifacts(...) -> report`: adds `artifacts.model_sha256`, writes all three files to
  temporary names, then renames them, the report last (`storage.replace_together`).
- `staleness(report, dataset_rows, feature_mode, dataset_fingerprint=None)`: also catches a
  changed dataset with the same row count when the report has `dataset.fingerprint`. Since
  18 October it also reports a change to the augmentation settings or `GD_L2_OPTIONS` in
  `config.py` when the report records them (`_changed_settings`).
- `TrainingJob(train_fn=None)`: `start(**train_kwargs) -> bool` (False while a run is going),
  `status() -> TrainingStatus` (run, running, done, total, started_at, finished_at, report,
  error), `wait(timeout)`. Catches every exception so a run never stays marked as going.
- `training_job(model_path=None)`: the shared job for a model file.
- `load_report()`, `make_warnings(report, name)`, `format_report(report)`.

### `predictor.py` (455 lines)
- `Predictor.load(model_path, labels_path, report_path, feature_mode, threshold, top_k)`. Raises
  `NotTrainedError` (no model) or `PredictorError` (unreadable, mismatched labels, wrong feature
  mode or length, or a model file whose SHA-256 differs from the report's
  `artifacts.model_sha256`). Loads exactly the bytes it hashed. Warns on a scikit-learn
  version mismatch.
- `Predictor.predict(vector) -> Prediction`. Thread-safe.
- `Prediction`: `status` (`NO_HAND`, `UNRECOGNISED`, `RECOGNISED`, `ERROR`), `label`,
  `confidence`, `top`, `threshold`, `inference_ms`, `at`, `error`.
- `LiveRecognizer(predictor, idle_exit_s=5.0, window, min_votes)`:
  video thread calls `offer(vector)`; UI reads `latest()`, `steady()`, `stable()`, `history()`;
  `use(predictor)` swaps models; `reset()` clears; `classify(vector, at)` runs synchronously
  (used by `check_pipeline.py` with video time).
- `Steady(label, confidence, votes, frames)`, `HistoryEntry(at, label, confidence)`,
  `DetectionLog` (skips repeats within `HISTORY_REPEAT_GAP_S`).

### `data_collector.py` (418 lines)
- `slugify_label(text)`: "First meme" becomes `first_meme`.
- `Recorder`: thread-safe state machine, countdown then recording then finished.
  `start(label, target, person)`, `stop()`, `cancel()`, `cancel_unfinished() -> bool` (drops a
  recording still counting down or recording; any page but the collector calls it through
  `ui.leave_collector()`), `offer(vector)`, `status()`, `pop_finished() -> RecordingResult`. Saves at most `COLLECT_RATE_HZ` per second and skips `None`.
- `DatasetStore(csv_path)`: `load()`, `load_with_fingerprint()`, `fingerprint()`, `row_count()`,
  `labels()`, `summary()`, `session_times()`, `append(result)`, `last_session()`,
  `delete_session(id)`, `delete_label(label)`. Raises `DatasetError` if `dataset_meta.json` does
  not match the current feature mode, or if the file stays locked by another writer for 10 s.
  Writes replace the whole file under the lock; reads are parsed once per file version and
  handed out as copies.
- `class_status(samples, recordings)`: the "too few / ok / good" label shown in the UI.
- `ready_to_train(summary)`: True when `summary()` meets training's minimum (2 or more gestures,
  each with `MIN_SESSIONS_FOR_TRAINING` recordings). The collector and the "No trained model"
  messages use it to point to Train model.

### `dataset_manager.py` (301 lines)
Meme metadata. Also a CLI (`python dataset_manager.py first_meme --rating "8/10"`).
- `MemeLibrary(root)`: `load() -> {id: MemeRecord}`, `image_file(record)`, `image_problem(record)`,
  `missing_for(labels)`, `update(gesture_id, image=None, **fields)`, `remove(gesture_id)`.
- `save_edit(library, gesture_id, *, gesture_name, meme_title, ...)`: what the Memes page calls.
- `display_name(label, records)`, `image_file_problem(path)`. (`unfinished` and `MemeRecord.title`
  were removed on the owner's answer to Q7: no page used them, and `title` fell back to the
  gesture's name.)
- `update` and `remove` hold the `memes.json` lock for their read-modify-write; images are
  copied with an atomic write, so the dashboard never shows half an image. A replaced image is
  deleted only after `memes.json` is saved; if that save fails, the previous image is put back.
  `remove` likewise saves `memes.json` before it deletes the image.
- `image_file_problem` checks the file's content, not just its name: only the JPEG, PNG, WebP
  and GIF images a browser can show are accepted.
- Raises `MemeError` with a user-readable message.

### `import_videos.py` (370 lines)
`python import_videos.py "Folder" ... [--label x] [--person name] [--rate 10] [--trim 0.25] [--dry-run]`.
One folder is one gesture, one file is one recording. The session id is the first 12 hex
characters of the file's SHA-256, so copies and re-imports are skipped. Frames are scaled to camera size and go through the live path.
Photo Booth filenames contain U+202F before "AM": pass them by glob, not typed by hand.

### `check_pipeline.py` (302 lines)
`python check_pipeline.py "Folder" ...` or `clip.mov --label meme_3`. `ModelSource` trains a
model without the clip's own recording when the clip is in the dataset. Reports per-clip shares
of right, wrong, no gesture, unsure and no hand.

### `storage.py` (195 lines)
Safe file writes, used by every module that saves something.
- `atomic_write_bytes(path, data)`, `atomic_write_text(path, text)`: unique temporary file in the
  same folder, flushed, renamed over the target. Keeps the old file's permissions; new files are 0600.
- `replace_together([(path, bytes), ...])`: writes every temporary file first, then renames in order.
- `locked(path, timeout=10.0, what="")`: exclusive, re-entrant within a thread, works across
  processes via `fcntl.flock` on `.<name>.lock` beside the file. Raises `StorageBusyError`.
- `sha256_bytes(data)`.

### `download_models.py` (70 lines)
Fetches `hand_landmarker.task` (7.8 MB) and, with `--pose`, `pose_landmarker_lite.task` (5.8 MB).

## 4. Where the UI touches the backend

| UI code | Backend call |
|---|---|
| `ui.get_vision()` | creates `LandmarkHook` and `FrameProcessor` per session |
| `ui.get_recognizer()` | creates `LiveRecognizer` per session |
| `ui.load_predictor()` | `Predictor.load()`, cached across sessions by file mtimes |
| `ui.camera_widget()` | `webrtc_streamer(...)` with `processor.process` as the frame callback |
| `views/dashboard.py` | sets `processor.recognizer`, reads stats, steady result, history, `MemeLibrary`, `staleness(..., dataset_fingerprint=)` |
| `views/collector.py` | sets `processor.recorder`, `DatasetStore` append, undo, delete |
| `views/performance.py` | `training_job().start()/status()`, `load_report()`, `staleness(..., dataset_fingerprint=)`, `make_warnings()` |
| `views/memes.py` | `dataset_manager.save_edit()`, `MemeLibrary` |

If you replace Streamlit with another web layer (for example FastAPI plus a JS frontend), the
backend modules above can stay as they are. What you rebuild is this table: the per-session
objects, the WebRTC frame callback, and the cached predictor.

## 5. Tests

`tests/` has 413 tests (pytest, about 70 s). Backend-relevant files: `test_storage.py`, `test_features.py`,
`test_vision.py`, `test_landmark_hook.py`, `test_gd_model.py`, `test_train_model.py`,
`test_predictor.py`, `test_data_collector.py`, `test_import_videos.py`, `test_check_pipeline.py`,
`test_memes.py`. Tests use scratch directories and fake detectors; they never touch the real
`data/` or `models/`, and `tests/conftest.py` fails the run if any test changes the real `data/`,
`models/` or `assets/memes/`. Add a test for any behaviour you change.
