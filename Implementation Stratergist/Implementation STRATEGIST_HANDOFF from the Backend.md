# Backend handoff for the implementation strategist

From the Backend session ("Backend Guy"), 17 October 2026, snapshot about 14:30.
This file is the short version for planning. The details are in the other files in this
folder: `README.md` (section 7 is the change log for this pass), `ARCHITECTURE.md` and
`DATA_CONTRACTS.md`. Every claim below names how it was checked. Treat it as a claim to check.

## 1. What the backend pass did (17 October)

The model maths and `config.py` were not changed by this pass. The ML session changed the
training recipe afterwards (see section 4).

| # | Problem found | What changed | Files | Checked by |
|---|---|---|---|---|
| 1 | Saving a recording appended to `samples.csv` in place. A crash or full disk could leave half a row and make the dataset unreadable. | Every save replaces the whole file in one step (temporary file, flush, rename). | `storage.py` (new), `data_collector.py` | `tests/test_data_collector.py::test_a_failed_save_keeps_every_earlier_recording` |
| 2 | No locking. Two tabs, or a tab and `import_videos.py`, could overwrite each other's recordings or meme edits. Two training runs shared temporary file names. | `storage.locked(path)`: thread lock plus OS file lock, so it holds across tabs and across the app and terminal scripts. Used for recordings, deletes, meme edits and training. | `storage.py`, `data_collector.py`, `dataset_manager.py`, `train_model.py` | `tests/test_storage.py` (incl. a lock held by a separate process), 8 threads saving at once, concurrent meme edits |
| 3 | The three model files were renamed one by one. An interrupted save could pair a new model with old gesture names and show wrong memes with no error. | The report stores the model file's SHA-256 (`artifacts.model_sha256`) and is renamed last. `Predictor.load` refuses a mismatch. Older reports without the field still load. | `train_model.py`, `predictor.py` | `tests/test_predictor.py::test_model_from_another_run_is_refused` |
| 4 | "Retrain needed" compared row counts only. Swapping a recording for one of the same length went unnoticed. | The report stores `dataset.fingerprint` (SHA-256 of `samples.csv`). Both pages pass the current fingerprint to `staleness()`. | `train_model.py`, `views/dashboard.py`, `views/performance.py` | `tests/test_status.py`, `tests/test_pages.py::test_a_recording_replaced_by_one_of_the_same_length_asks_for_retraining` |
| 5 | After a failed hand-model start, the camera kept the error until the page was reloaded, although the hint said restarting the camera was enough. | `LandmarkHook` retries every 2 s and serialises detector calls (one tab can briefly have two streams). | `vision.py` | `tests/test_landmark_hook.py` (fake clock, 3 threads) |
| 6 | Train model ran inside the page's script run and froze the page. | `TrainingJob` runs training on a background thread, one run per model folder, shared by all tabs. The page shows "Training: N of M models trained" from a real counter and the result message once. | `train_model.py`, `views/performance.py` | `tests/test_train_model.py`, `tests/test_pages.py::test_train_model_runs_in_the_background_and_reports_once`, browser check on port 8504 |
| 7 | Every page rerun parsed the whole CSV again. | Parsed samples cached by inode, modification time and size; callers get copies. | `data_collector.py` | `test_reading_is_cached_until_the_file_changes` |
| 8 | A disabled green button had dark text on no fill and could not be read. | One CSS selector in `ui.py` (the frontend's file) skips disabled buttons. Frontend Guy was told. | `ui.py` | `tests/test_pages.py::test_a_disabled_green_button_keeps_readable_text`, browser |
| 9 | Nothing stopped tests writing to the real project files. One existing test did leave an empty lock file in `models/` during this pass (deleted; the model was untouched). | That test uses scratch paths; `tests/conftest.py` fails the run if any test changes `data/`, `models/` or `assets/memes/`. | `tests/conftest.py`, `tests/test_train_model.py` | Whole suite |

Evidence at the end of the pass (before the ML change): a scratch retrain gave exactly the
14 October results (same metrics, cost curve and 1927 steps); `check_pipeline.py` showed 0 wrong
memes in 16 clips; full suite 388 passed.

## 2. State now (checked about 14:00 to 14:30)

| Item | Value | Source |
|---|---|---|
| Tests | 413 passed in about 72 s | `.venv/bin/python -m pytest -q`, run by this session after the ML change |
| Live model | trained 2026-10-17T13:47:21, l2 0.003, held-out accuracy 0.9711, cost 0.0747, with augmentation | `models/training_report.json` |
| Model protections | report has `dataset.fingerprint` (matches current `samples.csv`) and `artifacts.model_sha256` (matches the model file); `Predictor.load` loads it with no warnings; `staleness()` returns nothing | read-only check run by this session |
| Training time | about 34 s, 97 fits | ML session's message and `docs/ml-handoff/README.md`; not re-timed by this session |
| Lock file in `models/` | `.gesture_model.joblib.lock`, empty, created by the ML session's real training run | expected; listed in `DATA_CONTRACTS.md` "Lock files" |

## 3. Interfaces the backend owns, and what breaks if they change

| Interface | Used by | Breaks if changed |
|---|---|---|
| `train_model.training_job()`, `TrainingJob.start(**kw)`, `status()` fields `run, running, done, total, report, error` | `views/performance.py` (Frontend) | The progress bar and the one-time result message |
| `train(progress=...)` counts: l2 options x recordings + 1 | progress bar | The "N of M" text |
| `staleness(report, rows, feature_mode, dataset_fingerprint=)` returning sentences ending "Train again to include the changes." | dashboard and performance pages | Retrain warnings and how the pages word them (not re-checked after the frontend redesign) |
| Report fields `dataset.fingerprint`, `artifacts.model_sha256` | `Predictor.load`, staleness | A model with a wrong checksum is refused; missing fields fall back safely |
| `DatasetStore.fingerprint()`, `load_with_fingerprint()` | pages, `train()` | staleness |
| `storage.locked()`, `atomic_write_*`, `replace_together()` | every writer | data safety; any new file writer should use them |
| Lock files `data/.samples.csv.lock`, `assets/memes/.memes.json.lock`, `models/.gesture_model.joblib.lock` | OS only | harmless to delete when nothing runs |
| `LandmarkHook(retry_s=2.0)` | `ui.get_vision` | camera recovery without reload |

## 4. Conflicts and gaps this session knows of

| # | What | Evidence | Kind | Suggested owner |
|---|---|---|---|---|
| 1 | Frontend README still lists "Training blocks the page" as open and reports 387 tests | `docs/frontend-handoff/README.md` lines 53 and 139 | Doc fix | Frontend |
| 2 | ML README says "337 in the zipped snapshot" | `docs/ml-handoff/README.md` line 59 | Doc fix | ML |
| 3 | The training speed options in `README.md` section 7 here were measured before augmentation (5.9 s single thread, 3.0 s with 8 processes). With 34 s training they no longer describe the system; processes should now gain more | `README.md` section 7, marked as pre-augmentation | Re-measure, then decide | Backend (proposed session "Speed up training with worker processes", not started as of this file) |
| 4 | The background job only shows progress for runs started from the page. A run started with `python train_model.py` is invisible to the page; pressing Train model meanwhile gives "Another training run is already in progress" | `train_model.train` lock, `TrainingJob` is per process | Known limit; owner may not care | Backend if wanted |
| 5 | Three sessions edited `ui.py`, `views/dashboard.py`, `views/performance.py` the same day without git. This session diffed its files against the pre-work zip at about 13:13 and found both sets of edits present, and re-checked its own changes (fingerprint wiring, training job, CSS rule, tests) at about 13:55. Later frontend edits were not re-checked | diffs against `backend-handoff-2026-10-17.zip` | Integration check | Strategist or Frontend |
| 6 | The three handoff zips in the project root predate all 17 October work | zip dates 12:44 to 13:05 | Doc note | Whoever makes the next package |
| 7 | The 0.70 threshold was chosen on the 14 October model | `config.py`, ML handoff | Owner decision | Owner, with ML evidence |

## 5. Open backend work, in suggested order

| Item | Done looks like | Check | Depends on | Size |
|---|---|---|---|---|
| Re-measure training speed with the current recipe; add worker-process fits if worth it | Training faster with bit-identical report; or docs updated with new numbers and no code change | Report comparison with a sequential run; full suite; Train model in the browser on a scratch copy | ML recipe stable (do not run while ML edits `train_model.py`) | M |
| Integration check after all three departments' edits | Each department's 17 October changes still present in the shared files | Diff against the zips plus a read of each handoff's change list; full suite | Frontend and ML done editing | S |
| Show terminal-started training on the page (only if the owner wants it) | Page shows "training in progress" whenever the model lock is held | AppTest with the lock held from another thread | Owner says it matters | S |
| Per-gesture confidence thresholds | Only after the owner decides | | Owner decision | M |
| Hosting work (per-user data, a real database, HTTPS, TURN) | Only after local use is reliable | | Owner, launch checklist | L |

## 6. Working rules learned this pass

- Several sessions work in this folder at once (check `ListAgents` and file times). Use small edits,
  never whole-file rewrites of shared files, and re-run the suite before blaming your own change:
  one full run showed 12 failures that were another session mid-edit, and the re-run passed.
- Never train or import against the real `data/` and `models/` while testing. Use
  `BALLKNOWLEDGE_DATA_DIR` and `BALLKNOWLEDGE_MODEL_DIR` scratch copies. `assets/memes/` has no override.
- Port 8502 was the frontend session's test server. The backend used 8504 and stopped it afterwards.
- Streamlit does not reload imported modules: restart the server after editing `ui.py` or any backend file.
