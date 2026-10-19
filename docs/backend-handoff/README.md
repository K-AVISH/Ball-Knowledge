# Backend handoff: Ball Knowledge Vision AI

Written 17 October 2026 for the backend developer taking over the Python side of the project.
Start here, then read the other files in this folder.

| File | What it covers |
|---|---|
| `README.md` (this file) | What the project is, current state, setup, how to verify, open work |
| `ARCHITECTURE.md` | The live pipeline, threads, and every backend module with its public API |
| `DATA_CONTRACTS.md` | Every file the backend reads or writes, its schema and its invariants |
| `Implementation Stratergist/Implementation STRATEGIST_HANDOFF from the Backend.md` | One-page summary of the 17 October backend pass for the implementation strategist: changes, interfaces, conflicts, open work. Not in this folder: it moved on 17 October to `Implementation Stratergist/` in the project root (the folder name is spelled that way on disk) |

## Context files to read (in this order)

| File | Why |
|---|---|
| `docs/backend-handoff/*` | This handoff |
| `Context.md` | The original product spec: objective, pipeline, model requirements, acceptance criteria |
| `Instructions.md` | The 8 build stages the project was built in (the owner refers to stages by these numbers) |
| `README.md` (project root) | User-facing setup, data collection, training, testing and troubleshooting |
| `config.py` | Every path, threshold and tunable. No other module hardcodes these |
| `requirements.txt` | Dependencies, with notes on the OpenCV and streamlit-webrtc pins |
| `LAUNCH_CHECKLIST.md` | What must be done before anything goes public |
| `docs/implementation-plan/README.md` | The joined plan for all three departments: verified state, conflicts, roadmap, owner decisions, risks |
| `docs/ui-critique-log.md` | History of UI decisions, only if you touch `ui.py` or `views/` |

The older critique files from 14 October (including the previous UI-focused handoff) are in
`to be deleted/`. They describe the dashboard before 17 October; do not work from them.

If you received `backend-handoff-2026-10-17.zip`: it holds the code, tests, the files above,
the training data (`data/`), the trained model and the meme images. It leaves out the MediaPipe
models (run `python download_models.py --pose`) and the raw gesture videos, which show people's
faces. Without the videos, `check_pipeline.py` and `import_videos.py` cannot be run on the real
clips; ask the owner if you need them. The test suite passes from the unzipped folder.

## 1. What the project is

A local web app. You show a hand gesture to your webcam, a classifier trained on your own
recordings recognises it, and the dashboard shows the matching meme with a "Ball Knowledge"
rating and description.

There is no separate server or database. Streamlit is both the web server and the UI, and all
state lives in files under the project folder. "Backend" here means the Python modules that do
the vision, data, training and prediction work. They do not import Streamlit, so they can be
moved behind a different web layer without rewriting them.

| Layer | Files |
|---|---|
| Backend (your area) | `vision.py`, `features.py`, `gd_model.py`, `train_model.py`, `predictor.py`, `data_collector.py`, `dataset_manager.py`, `import_videos.py`, `check_pipeline.py`, `download_models.py`, `storage.py`, `config.py` |
| UI (Streamlit) | `app.py`, `ui.py`, `views/*.py`, `.streamlit/config.toml` |
| Data | `data/`, `models/`, `assets/memes/` |
| Tests | `tests/` (pytest, no webcam needed) |

## 2. Current state (verified 17 October 2026)

- All 8 build stages are done. The owner checked the site and webcam on 14 October and, with the
  17 October model, on 18 October; both times they reported it works.
- A backend refinement pass followed on 17 October (section 7): safe saving with locks,
  background training, checks that catch a mismatched model or a changed dataset, and a
  camera-start fix. It changed no model maths.
- Later on 17 October an ML session changed the training recipe: each training sample also
  gets 4 slightly turned and jittered copies (`GD_AUGMENT_*` in `config.py`,
  `features.augment_hands`), and a sixth penalty, 0.003, is tried. It retrained the live model
  at 13:47. Details and its own measurements: `docs/ml-handoff/`. The previous model is in
  `docs/handoff/snapshots/before-augmentation/`.
- `python -m pytest -q`: **413 passed** (17 October, after both passes; 337 before them; about
  70 s, longer than before because training tests now augment). Python 3.14.7, project `.venv`.
- Trained model: softmax regression by gradient descent, 5 classes (`first_meme`, `meme_3`,
  `meme_4`, `second_meme`, `none`), 380 samples from 16 recordings, penalty l2 0.003, with
  augmentation. Held-out accuracy 97.1%, macro F1 0.972, cost 0.0747 (from
  `models/training_report.json`, trained 17 October 13:47). Every number is measured
  leave-one-recording-out; none are estimates. This is the first saved model whose report
  carries the dataset fingerprint and model checksum from section 7, and both match.
- Replaying all 16 clips through the live path (`check_pipeline.py`) showed a wrong gesture in 0 of 16 clips
  (14 October; on 17 October before the recipe change; and, per the ML session's run in
  `docs/ml-handoff/RESULTS_AND_DATA.md`, after it).
- All four memes have images, but their titles, ratings and descriptions are empty. **The owner
  writes those. Never fill them in yourself.**

## 3. Setup and run (macOS, Apple Silicon)

The machine has Python 3.14 (python.org) and 3.9. Use 3.14.

```bash
cd "/Users/kavishseema/Desktop/Passion Project"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python download_models.py --pose
streamlit run app.py
```

Open http://localhost:8501 in Chrome. Notes:

- The app listens on this computer only (`server.address = "localhost"` in
  `.streamlit/config.toml`). Without it, anyone on the same network could open it, and no
  page has a sign-in. Hosting would need a sign-in first (CONFLICTS N12).
- MediaPipe 1.1.0 ships no models and has no `mp.solutions`. `download_models.py` fetches the
  `.task` files into `models/mediapipe/` (it uses `certifi` for SSL). They are already present on this Mac.
- Streamlit does not reliably reload imported modules. Restart it after editing any backend file.
- The owner usually keeps their own Streamlit on port 8501. Test on another port:
  `streamlit run app.py --server.port 8502`.
- Install only `opencv-contrib-python`. A second OpenCV package overwrites the same `cv2` folder.
  Since 18 October `requirements.txt` pins every direct dependency to the tested version, and
  the project `.venv` has a single OpenCV again.

## 4. How to verify a change

```bash
source .venv/bin/activate
python -m pytest -q
python check_pipeline.py "First meme" "Second meme" "Meme 3" "Meme 4" None
python train_model.py
```

- The test suite trains on synthetic data, so it checks code, not recognition quality.
- `check_pipeline.py` replays the owner's real clips through the exact live code path. Each
  clip already in the dataset is classified by a model trained without it. The line that
  matters is "A wrong gesture was shown in N clips"; it must stay at 0.
- **Do not train, import or record against the real `data/` and `models/` while experimenting.**
  Point the app at scratch copies instead:

```bash
export BALLKNOWLEDGE_DATA_DIR=/tmp/bk-scratch/data
export BALLKNOWLEDGE_MODEL_DIR=/tmp/bk-scratch/models
```

  `assets/memes/` has no override, so test meme saving on a copy of the whole project folder.

The raw gesture videos (`First meme/`, `Second meme/`, `Meme 3/`, `Meme 4/`, `None/`) show the
owner and a friend. They are training input only; the app never stores video or images of
people, only landmark numbers. Keep it that way.

## 5. Rules you must keep

1. **One feature path.** Collection, video import, training and live prediction all build
   features with `features.build_feature_vector` through `vision.LandmarkHook`. Never add a
   second way of computing features, or training and prediction will drift apart.
2. **Split by recording, never by frame.** Neighbouring frames are near-duplicates. Training
   holds out whole recordings (`session_id`). A random row split would report fake accuracy.
3. **Honest numbers.** No invented accuracy, no "estimated" metrics in the UI or reports.
   `Context.md` section 11 requires this.
4. **Uncertain means no meme.** Below the confidence threshold, or before the steady vote
   passes, the dashboard shows "Unrecognised" or "Hold it steady", never a guess. `none` has no meme.
5. **Save through `storage.py`.** Every file write goes to a temporary file that is flushed
   and renamed into place (`storage.atomic_write_bytes`, `replace_together`), including
   saving a recording, which used to append in place. Every read-modify-write holds
   `storage.locked(path)`, which works across tabs (threads) and across the app and a
   terminal script (processes). Reads take no lock. Keep both for any new file.
6. **Changing `FEATURE_MODE` changes the vector length** (126 for `hands`, 225 for
   `hands+pose`). The existing `data/samples.csv` is then unusable and must be re-collected.
   `DatasetStore` refuses mismatched data through `data/dataset_meta.json`.
7. **UI text rules** (enforced by `tests/test_style_rules.py`): no emoji, no em dashes, no
   gradients, no pills, no purple, no fake metrics, and the word "gradient" may not appear in
   `views/`, `ui.py` or `app.py`. Backend modules may say "gradient descent".

## 6. Open work and decisions

Owner tasks (not yours): meme titles, ratings and descriptions; more recordings (a third
`first_meme` recording, clips in other rooms and lighting, more people for `meme_4`, which
depends on who performs it).

Backend work, roughly in priority order:

| # | Item | Notes |
|---|---|---|
| 1 | ~~Training blocks the page~~ | **Done 17 October.** Train model starts `train_model.TrainingJob` on a background thread with a progress bar. See section 7. |
| 2 | Single-machine file storage | **Locking added 17 October**, so tabs and terminal scripts on one machine no longer lose each other's writes. Still files on one disk: a hosted, multi-user site needs per-user data and a real database. |
| 3 | Per-gesture confidence threshold | `Context.md` lists `confidence_threshold` per meme record. Today one global `DEFAULT_CONFIDENCE_THRESHOLD` (0.70) is used. Owner decision pending. |
| 4 | Prediction history persistence | Recent detections are memory-only per browser session by design, and the privacy page says so. Persisting them requires a privacy page update first. |
| 5 | Hosting | Needs HTTPS (browsers only allow cameras on HTTPS or localhost), a TURN server for WebRTC over the internet, per-user data separation, and the operator details in `config.py` plus a legal review. See `LAUNCH_CHECKLIST.md`. `Context.md` says not to deploy until local use is reliable. |
| 6 | Accessibility | Results are not announced to screen readers. Safari is untested. |
| 7 | Training time | About 34 s since the recipe change (97 models: 6 penalties x 16 held-out recordings, plus the final one, each learning from 5 times the rows). It was 6 to 7 s before. It grows with samples x recordings. The page stays usable (background job), but this is now past the point where worker processes pay off; see the options in section 7. |

Ask the owner before changing the model type, the feature layout, the privacy behaviour, or anything user-visible.

## 7. Refinement pass, 17 October 2026

What was wrong, what changed, and how it was checked. This pass did not touch the model maths
(`gd_model.py`, `features.py`) or settings (`config.py`); the ML session's recipe change came
afterwards, so the training figures in this section describe the recipe before it.

| Problem found | Change | Where |
|---|---|---|
| Saving a recording appended to `samples.csv` in place, so a crash or full disk could leave half a row and make the whole dataset unreadable. `dataset_meta.json` was written in place too. | Every save replaces the whole file in one step (temporary file, flush, rename). | `storage.py`, `DatasetStore.append`, `_write_meta` |
| No locking: two tabs, or a tab and `import_videos.py`, could overwrite each other's recordings or meme edits, and two training runs shared the same `.tmp` names. | `storage.locked(path)`: a thread lock plus an OS file lock (`fcntl.flock`) on a hidden file beside the data. Recording saves, deletes and meme edits hold it; training holds one per model folder and a second run fails at once with a clear message. Temporary files now have unique names. | `storage.py`, `DatasetStore`, `MemeLibrary`, `train_model.train` |
| The three model files were renamed one by one. A save interrupted between renames could leave a new model next to the old labels, and with the same number of gestures it would load and show the wrong memes, with no error. | The report records the model file's SHA-256 (`artifacts.model_sha256`) and is renamed last. `Predictor.load` hashes the bytes it loads and refuses a mismatch, saying to train again. Reports without the field (such as the 14 October one, which was live during this pass) load as before. The model the ML session trained at 13:47 has the field, and it matches. | `train_model.save_artifacts`, `Predictor.load` |
| "Retrain needed" compared row counts only, so replacing a recording with one of the same length went unnoticed. | The report records `dataset.fingerprint` (SHA-256 of `samples.csv`); both pages pass `DatasetStore.fingerprint()` to `staleness()`. Old reports fall back to row counts. | `train_model.staleness`, `views/dashboard.py`, `views/performance.py` |
| After a failed detector start (hand model not downloaded yet), `LandmarkHook` kept the first error for the life of the browser tab. The on-screen hint said to stop and restart the camera, but only a page reload helped. | The hook tries again every 2 s, so the camera recovers by itself once the model is there. Detector calls are serialised, because one tab can briefly have two camera streams while switching pages and MediaPipe must not run twice at once. | `vision.LandmarkHook` |
| Train model ran inside the page's script run (item 1 above). | `TrainingJob` runs `train()` on a background thread, one run per model folder, shared by every tab. The page shows "Training: N of M models trained" from a real counter (`train(progress=...)`), disables the button while a run is going, and shows the same result message as before, once. | `train_model.TrainingJob`, `training_job()`, `views/performance.py` |
| Every page rerun parsed the whole CSV again (twice on Model performance). | Parsed samples are cached by the file's inode, modification time and size. Callers get a copy. | `DatasetStore._snapshot` |
| A disabled green button had dark text on no fill, so it could not be read (it showed once Train model could be disabled; Start recording already could be). | The dark-text rule now skips disabled buttons. | `ui.py` CSS |
| Nothing stopped a test from writing to the real project files. During this pass, one existing test that called the trainer with the real paths left an empty lock file in `models/`; it was deleted, and the model files were never touched. | That test now uses a scratch folder, and `tests/conftest.py` fails the run if any test changes `data/`, `models/` or `assets/memes/`. | `tests/conftest.py`, `tests/test_train_model.py` |

How it was checked (17 October):

- 40 new tests (`tests/test_storage.py` plus additions to the data collector, training,
  predictor, memes, landmark hook, status and page tests), including a lock held from
  a separate process, eight threads saving at once, a failed save keeping the old file,
  a model from another run being refused, and pressing Train model in AppTest.
  Full suite at the end of this pass: 388 passed (this also counts 10 page tests a frontend
  session added the same day).
- Retraining a scratch copy of the real data from the terminal gave exactly the
  14 October results: same held-out metrics, same cost curve, same 1927 steps (before the
  recipe change).
  The real model at the time, from 14 October and without a checksum, still loaded. The live
  model since the 13:47 retrain has `artifacts.model_sha256` and `dataset.fingerprint`, and both
  match (section 2).
- `check_pipeline.py` on all clips, with scratch data and model folders: a wrong gesture
  was shown in 0 of 16 clips, as on 14 October (the 17th file is the known identical copy).
- In the browser (Streamlit on port 8504, scratch folders): pressing Train model showed
  the progress bar counting to 81, a readable disabled button, then the result message;
  leaving for the dashboard mid-run and coming back still showed it, once.
- The real `data/`, `models/` and `assets/memes/` were not modified.

Training speed options, measured on the real 380 samples with the recipe before augmentation
(not adopted). With augmentation each fit learns from 5 times the rows, so worker processes
should now gain more than shown here, and their start-up cost matters less; measure again first.

| Option | Time, before augmentation | Why not adopted |
|---|---|---|
| Current single thread | 5.9 s for the 80 held-out fits | |
| Fewer NumPy operations per step | 5.7 s | About 3% faster; the two matrix products and the softmax already dominate each step |
| Warm start between penalties | 5.1 s | 11% fewer steps, but results move by up to 1e-4 in probability |
| Threads (2, 4, 8) | 7.2 s, 10.7 s, 13.1 s | Slower: the steps are too small to release Python's interpreter lock for long |
| Worker processes (4, 8) | 3.3 s, 3.0 s | About 2x, and more as data grows, but it adds process start-up inside Streamlit and new ways to fail. Worth doing if training passes about 30 s, which it now does (about 34 s). |

Measured after the recipe change: a full `python train_model.py` run (97 models) on a scratch copy
of the same 380 samples from 16 recordings took 34.78 s wall time (the implementation strategist,
17 October). None of the options above has been measured with augmentation yet; they are
re-measured after the next data round (`docs/implementation-plan/ROADMAP.md` item B7).
