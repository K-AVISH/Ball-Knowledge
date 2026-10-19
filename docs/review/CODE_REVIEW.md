# Code review: Ball Knowledge Vision AI

Reviewer: Claude Code session, 18 October 2026, working alone in the folder (confirmed by the
owner before starting). Process: `Code Reviewer/CODE_REVIEW_PROMPT.md` (six rounds, scored gate),
with the context in `Code Reviewer/REVIEW_HANDOFF.md`. Start tag: `code-review-start-2026-10-18`
at `8bc8d5a`.

**File and line numbers in the findings refer to the code at the start tag**, before any fix,
unless a row says otherwise.

## Summary for the owner

_Final, after round 6._

**Result: the gate is met, narrowly.** Weighted score 9.05 (needed 9.0); every dimension at least
8.5, with correctness exactly at 8.5 because seven of your decisions are still open; no open
Critical or High finding; 445 tests pass; the clip replay shows 0 wrong memes in 16 clips; your
data, model and meme files are byte-for-byte unchanged. This is not a claim that the code is
perfect: the weaknesses that remain are listed at the end of this summary.

| Round | Focus | Critical | High | Medium | Low | Nit | Fixed | Not confirmed | Owner decision | Weighted |
|---|---|---|---|---|---|---|---|---|---|---|
| Baseline | before any change | 0 | 1 | 4 | 9 | 1 | | | | 7.95 |
| 1 | baseline and broad pass | 0 | 1 | 4 | 9 | 1 | 10 | 1 | 4 | 8.68 |
| 2 | correctness, edge cases | 0 | 0 | 0 | 3 | 0 | 1 | 0 | 2 | 8.68 |
| 3 | concurrency, reliability | 0 | 0 | 1 | 2 | 0 | 2 | 0 | 1 | 8.80 |
| 4 | data integrity, security, privacy | 0 | 1 | 0 | 1 | 2 | 2 | 0 | 0 | 8.88 |
| 5 | ML integrity, performance | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8.95 |
| 6 | tests, maintainability, docs, final pass | 0 | 0 | 0 | 5 | 1 | 4 | 0 | 1 | 9.05 |
| **All rounds** | | **0** | **2** | **5** | **20** | **4** | **19** | **1** | **8** | |

(The baseline row counts what round 1 then found in the unchanged code. Nits are not fixed, by the
prompt's rule. The 8 owner decisions are 7 questions: Q5 covers two findings.)

**What was fixed, in plain words**

- The two High findings. (1) A gesture named "Null" or "NaN", or a person named "NA", was saved
  but read back as blank: the recording vanished from the lists, could not be deleted, and the
  Memes page stopped with a Python error. (2) The app listened on the whole local network, where,
  with no sign-in, anyone on the same Wi-Fi could have deleted gesture data, retrained the model or
  replaced memes. It now listens on this computer only; nothing changes for you.
- A failed save (for example a full disk) no longer leaves a meme pointing at a deleted image, and
  removing a meme saves `memes.json` before deleting the image.
- Broken model, report, label or dataset files, a busy or full disk on Undo, Delete or saving a
  recording, and an image replaced in another tab now give a message instead of a Python error.
- Smaller fixes: error text in the camera hint is escaped; uploads are checked by content (a TIFF
  renamed `.png` is refused); a model load that overlaps a training save is retried instead of
  reported as broken; a race on the video thread is closed; the replay tool reports a damaged
  report per clip; stale comments, two unused CSS rules and two document errors are corrected.
- Every fix has a test that failed before it and passes after it: 28 new tests (417 to 445).

**Waiting for you** (`OWNER_QUESTIONS.md`): Q1 the Meme panel says "Starting" while the camera
reports an error; Q2 leaving the Data collector mid-recording saves it on return unless you went
to the dashboard; Q3 alt text "Meme: <title>" or the title alone; Q4 step numbers in the report;
Q5 two error messages that are untrue in rare cases; Q6 names in Recent detections when a meme
image is missing (and ids when `memes.json` cannot be read), **answered 18 October: allowed (A)**;
Q7 two functions only tests use.

**Final checks** (18 October): `pytest -q` 445 passed in 73.23 s; `shasum -a 256 -c` on your 10
files: all OK; scratch retrain gives the live model byte for byte (SHA-256 `1e5813fc...`, 34.7 s);
clip replay: "A wrong gesture was shown in 0 of 16 clips"; all six pages load with no Python error
at 1280x900 and 390x844, with no sideways scroll.

**Commits** (`git log --oneline code-review-start-2026-10-18..HEAD`): one per round, messages
starting "Code review round N:"; hashes are at the end of each round below.

**What could not be checked**: your real webcam (the replay runs the same live code path on your
clips, but not the browser camera); Safari; a screen reader; a second device on your network (the
binding was checked from this Mac: `127.0.0.1` only, the network address refused); Windows (the
file lock uses `fcntl`). The page critic checks the pages in the browser separately
(`CRITIQUE.md`).

**Weaknesses that remain**

- The open questions above, including two Medium ones that leave a misleading message on
  screen (Q1, Q2). Q6 (names on the dashboard) was answered after the review: allowed.
- Recognition quality is measured on your own 16 recordings from one room and two days; 97.1% is an
  upper bound for new people, rooms and light (RISKS R1), and the l2 choice makes it slightly
  optimistic (stated in the report).
- The meme image is sent again with every refresh (161 KB for `meme_3`, about 320 KB/s): fine on
  this computer, a cost if hosted (RISKS R16).
- No page has a sign-in: safe now that the app listens on this computer only, a blocker for any
  hosting (CONFLICTS N12).
- The model is a pickle: only files this project wrote should ever be loaded. The checksum catches
  a mixed or damaged set of files, but it is not protection against someone who can write the
  model folder.
- A recording that cannot be saved (full disk) is now reported, but its samples are dropped; it has
  to be recorded again.
- `dataset_manager.unfinished` and `MemeRecord.title` stay until you answer Q7.

## Baseline (before any change)

### Checks

| Check | Command | Result |
|---|---|---|
| Starting point | `git status --short`; `git log --oneline -3` | Clean; HEAD `8bc8d5a`, after `b21c9e9` |
| Owner's files | `shasum -a 256 ... > /tmp/bk-review-hashes-start.txt` | `samples.csv` `d4e05a87...`, `gesture_model.joblib` `1e5813fc...`, as on 18 October |
| Test suite | `.venv/bin/python -m pytest -q` | **417 passed in 72.39 s** |
| Scratch retrain | `BALLKNOWLEDGE_DATA_DIR=/tmp/bk-review/data BALLKNOWLEDGE_MODEL_DIR=/tmp/bk-review/retrain-r0 .venv/bin/python train_model.py` | 34.48 s wall. Model SHA-256 `1e5813fc...`, the live model's. Report identical apart from `trained_at`; `label_mapping.json` byte-identical |
| Clip replay | `BALLKNOWLEDGE_DATA_DIR=/tmp/bk-review/data BALLKNOWLEDGE_MODEL_DIR=/tmp/bk-review/models .venv/bin/python check_pipeline.py "First meme" "Second meme" "Meme 3" "Meme 4" None` | **"A wrong gesture was shown in 0 of 16 clips."** Right on 87% (first_meme), 89% (meme_3), 60% (meme_4, 33% no hand), 86% (none, as No gesture), 87% (second_meme); "1 clip(s) could not be checked" is the known identical copy. 44.0 s |
| Browser | Streamlit 1.65 on port 8502 with the scratch folders, built-in browser (Chromium) | All six pages load with no Python error at 1280x900 and 390x844; no sideways scroll at 390 px (`scrollWidth` equals `clientWidth` on every page); Tab focus shows a 2px `#2fbf71` outline on links and a ring on the Train model button. Console: only 404s for `/<page>/_stcore/health` and `/<page>/_stcore/host-config` when a page address is opened directly (the root ones return 200), plus browser warnings about iframe sandbox flags and unknown permission names |
| Environment | `git remote -v`; `pip check`; `pip list` | No remote. "No broken requirements found." Installed versions match the pins; one OpenCV (`opencv-contrib-python 5.0.0.93`) |

### Scores before any change

Scored on the findings of the round 1 review below, before any fix.

| Dimension | Weight | Score | Evidence |
|---|---|---|---|
| Correctness | 25% | 7.5 | R1-1 (High): a reachable gesture name loses its recording and crashes the Memes page. Core recognition is right: 0 wrong memes in 16 clips, threshold and vote as documented |
| Reliability and error handling | 15% | 7.5 | R1-3, R1-9: Python errors on screen for broken files and a busy dataset; R1-5 misleading state; R1-11 a false "Model cannot be used" |
| Data integrity, security and privacy | 15% | 7.5 | R1-2 leaves a broken meme after a failed save; R1-1 makes rows undeletable from the app; R1-6, R1-7 unescaped text in HTML; R1-12 upload checked by name and decodability only. Privacy: nothing from the camera is written anywhere (read every writer; listed in round 1) |
| Concurrency | 10% | 8.5 | Locks, atomic writes and the recogniser's generation counter are sound; R1-10 and R1-11 are narrow races |
| ML integrity | 10% | 9.0 | Byte-identical retrain; whole recordings held out; augmentation and standardisation inside each fit only. R1-14 is a report labelling mismatch |
| Tests | 10% | 8.0 | 417 tests that test behaviour, but none for the cases behind R1-1, R1-2, R1-3, R1-12 |
| Maintainability | 10% | 8.5 | One place per concern, true comments in most places; one handoff statement contradicts the code (R1-4) |
| Performance | 5% | 8.5 | Training time measured (34.5 s); per-refresh image checks and the meme data URI not yet measured |
| **Weighted** | | **7.95** | |

## Round 1: baseline, then a broad pass

Read every file listed in the prompt: all `*.py` (app, views, tests), `.streamlit/config.toml`,
`requirements.txt`, `pytest.ini`, the handoffs, `OWNER_DECISIONS.md`, `CONFLICTS.md`, `RISKS.md`
and the implementation log. Rebuilt the departments' 17 October diff
(`backend-handoff-2026-10-17.zip` against the `baseline-2026-10-17` tag, in `/tmp`): 29 files, 26
changed and 3 new, as the handoff says; its code part (1,836 diff lines) was read hunk by hunk.

### Findings

| ID | Sev. | Area | File and line | What is wrong | Failing case | Evidence | Fix | Test added | Status |
|---|---|---|---|---|---|---|---|---|---|
| R1-1 | High | Backend | `data_collector.py:249` (`pd.read_csv` in `_parse`); effect at `:311` and `views/memes.py:44` | pandas turns the text `null`, `nan`, `NA`, `None` and others into missing values when reading `samples.csv` | Name a new gesture "Null" (saved as `null`) and record it: "Saved 5 samples for null". Read back, the label is NaN: the gesture vanishes from the dataset list, "Delete gesture data" removes 0 rows, training drops the rows as "missing gesture label", and the Memes page stops with `TypeError: '<' not supported between instances of 'float' and 'str'`. A person "NA" reads back as blank | Scratch script: label read back `[nan, nan]`, `delete_label('null')` removed 0; Memes page AppTest raised the TypeError | Read with `keep_default_na=False`: text stays as written, an empty cell is empty text (nothing is ever saved as NaN) | `test_names_that_pandas_reads_as_missing_are_kept_as_typed`, `test_memes_page_lists_a_gesture_named_null` | Fixed |
| R1-2 | Medium | Backend | `dataset_manager.py:199-209` (`MemeLibrary.update`) | The new image is written and the old one deleted before `memes.json` is saved | Replace a `.jpeg` meme with a `.png` when `memes.json` cannot be written (disk full): `wave.jpeg` is deleted, the record still points at it (dashboard: "Image missing"), and the Memes page says "Nothing was saved". With the same file type the image is replaced although the page says nothing was saved | Scratch script: record `assets/memes/wave.jpeg`, files `['memes.json', 'wave.png']`, `image_problem`: "wave.jpeg is missing" | The old image is deleted only after `memes.json` is saved; on a failed save the new file is removed or the previous bytes put back | `test_a_failed_save_keeps_the_previous_image_and_record` (other type, same type) | Fixed |
| R1-3 | Medium | Backend | `predictor.py:77-81`, `:173-174`; `train_model.py:395-403`; `data_collector.py:220-224` | Reading JSON catches `OSError` and `JSONDecodeError` only, so bytes that are not UTF-8 raise `UnicodeDecodeError`; a report that is valid JSON but not an object raises `AttributeError` | Copy `gesture_model.joblib` over `training_report.json` or `label_mapping.json`, or put binary bytes in `dataset_meta.json`: the dashboard, Model performance and collector stop with a Python error instead of "Cannot read ... Train the model again" | Scratch script on copies: four `UNHANDLED UnicodeDecodeError`, two `UNHANDLED AttributeError` | Catch `UnicodeDecodeError` too (as `MemeLibrary.load` already does) and refuse a report or meta file that is not a JSON object, with the existing messages | `test_model_files_that_are_not_json_objects_are_a_clear_error` (3 cases), `test_a_meta_file_that_is_not_json_text_is_a_dataset_error`, two more cases in `test_load_report_missing_and_corrupt` | Fixed |
| R1-4 | Medium | Frontend (owner decision) | `docs/frontend-handoff/ARCHITECTURE.md:96` against `views/dashboard.py:29-31` and `views/collector.py:88-102` | The document says leaving the collector cancels a recording; only the dashboard cancels it | Start a recording, open Memes, come back: the partial recording is saved ("Saved N samples"). Left during the countdown it says "no hand was detected", which is not why | AppTest of the collector with a recording still going (12 samples): 12 rows saved | Changing the behaviour is user-visible (rule 11), so the document was corrected to describe the code and the choice went to the owner | none (no code change) | Owner decision (Q2); doc fixed |
| R1-5 | Medium | Frontend (owner decision) | `ui.py:563-564` with `vision.py:66-75` | A frame that fails in the landmark hook is never offered to the recogniser, so the Meme panel shows "Starting. The model is classifying the first frames." for as long as frames fail | Start the camera before `download_models.py` has run: the camera panel says "Hand model missing", the Meme panel keeps saying the model is classifying | `ui.result_card` with a live camera and no prediction returns "Starting"; `camera_state` for the same stats returns "Hand model missing" | New panel wording is the owner's (rule 11) | none | Owner decision (Q1) |
| R1-6 | Low | Frontend | `ui.py:735-739` (`camera_state`) | Frame error text goes into the hint unescaped; both pages render the hint as HTML | An OpenCV error such as `... size.width>0 && size.height>0 <cv::Mat>`, or a project path with `<`, is shown garbled (the `<...>` part is read as a tag) | `camera_state(VisionStats(error=...))` returned the raw `<` text | `esc(stats.error)` | `test_frame_errors_are_escaped_in_the_camera_hint` (2 cases) | Fixed |
| R1-7 | Low | Frontend | `views/collector.py:210` | The gesture id from `samples.csv` goes into HTML unescaped (the name next to it is escaped) | An id edited by hand in the CSV, with a display name in `memes.json`, becomes markup in Your dataset | Code; AppTest showed the raw `<i>odd</i>` | `ui.esc(row.label)` | `test_collector_escapes_a_gesture_id_from_the_files` | Fixed |
| R1-8 | Low | Backend | `train_model.py:387` (`_changed_settings`) | Builds a model with `GD_L2_OPTIONS[0]` only to read the augmentation settings | With `GD_L2_OPTIONS = ()` in `config.py`, both the dashboard and Model performance stop with `IndexError`, while training itself says "GD_L2_OPTIONS must list at least one value above 0." | Scratch script: `staleness` raised `IndexError: tuple index out of range` | Build it with a fixed penalty, which plays no part in those settings | `test_an_empty_l2_list_is_reported_not_a_crash` | Fixed |
| R1-9 | Low | Frontend | `views/collector.py:234`, `:242` | `delete_session` and `delete_label` raise `DatasetError` when the lock stays busy for 10 s or the file cannot be read; the page did not catch it | Undo while another program holds the samples lock: the page stops with a Python error | AppTest with the lock held in a second thread: the `DatasetError` traceback on the page | Catch it and say "Nothing was deleted: ..." (the error-path wording follows DESIGN_SYSTEM section 5, now noted there) | `test_a_busy_dataset_on_undo_or_delete_is_a_message_not_a_python_error` | Fixed |
| R1-10 | Low | Backend | `vision.py:70-73` (`FrameProcessor.process`) | Checks `self.recorder is not None`, then reads `self.recorder` again to call it; the pages set it to `None` from another thread | The dashboard sets `processor.recorder = None` (`views/dashboard.py:28`) between the two reads: that frame fails with `AttributeError: 'NoneType' object has no attribute 'offer'`, shown as a processing error | A trace hook that makes the assignment land just before the call: `stats.error` was that `AttributeError` | Read both attributes once per frame into locals | `test_a_page_detaching_the_recorder_mid_frame_is_not_an_error` | Fixed |
| R1-11 | Low | Frontend | `ui.py:376-384` (`load_predictor`), with `predictor.py:172-207` and `storage.py:111-112` | Training renames model, labels and report one after another. A load in between reads the old report and the new model, and the checksum check refuses it as "damaged or replaced". The failure is not cached, but the dashboard computes it at page level, so it stays until the whole page runs again | Open the dashboard at the moment another tab's training run saves: "Model cannot be used ... Train the model again", and no recognition, until you reload | Scratch script that lands the trainer's first rename between the two reads: `PredictorError: gesture_model.joblib is not the model that training_report.json was saved with` | When the files' modification times changed while loading, try again (three tries at most). A load whose files did not change reports the problem at once | `test_a_load_that_overlaps_a_training_save_is_tried_again`, `test_a_model_that_stays_unusable_is_reported_without_retrying` | Fixed |
| R1-12 | Low | Backend | `dataset_manager.py:83-97` (`image_file_problem`) | Accepts any file Pillow can decode, whatever its format | A TIFF renamed `meme.png` is saved as `wave.png`, the Memes table says "Set", and the dashboard shows a broken image (under 900 px and 250 KB the file is sent as it is) | Saved with `image_problem` None and Pillow format TIFF; in the built-in browser (Chromium) the data URI fails to decode while a PNG control loads | Accept only the formats browsers show: JPEG (and MPO), PNG, WebP, GIF. The owner's four images are JPEG | `test_an_image_browsers_cannot_show_is_refused_whatever_its_name`, `test_the_four_image_types_browsers_show_are_accepted` (4 cases) | Fixed |
| R1-13 | Low | Frontend (owner decision) | `ui.py:493` (`meme_alt`) | Alt text is "Meme: <title>"; the owner's OD-5 answer was "Meme title, else Meme" | Screen readers say "Meme: Absolute Cinema" | `OWNER_DECISIONS.md` OD-5 row; handoff section 10 lists it as a call to challenge | Wording is the owner's | none | Owner decision (Q3) |
| R1-14 | Low | ML (owner decision) | `gd_model.py:136-153`, `:166-172` | `n_iter_` (the report's `steps`) counts every step tried; `cost_history_` numbers only the steps kept | Live report: `steps` 2658, `history` ends at step 2656 (2 momentum restarts) | `models/training_report.json` | Renumbering changes the pickled model's bytes, so the live model would change (rule 5) | none | Owner decision (Q4) |
| R1-15 | Nit | Backend | `download_models.py:41-58` | Prints check-mark, arrow and cross symbols in the terminal | Terminal output only; the emoji rule and its test cover the UI files | Code | Not fixed (Nit) | none | Not fixed |
| R1-16 | n/a | Environment | `.venv` | macOS prints "Class AVFFrameReceiver is implemented in both" PyAV's and OpenCV's `libavdevice` when both are imported | No failure seen: the camera comes in through WebRTC, not AVFoundation, and every check passed | Warning text only | none | none | Not confirmed |

Counted in the summary: High R1-1; Medium R1-2 to R1-5; Low R1-6 to R1-14; Nit R1-15. R1-16 is
not confirmed and not counted by severity.

### Handoff section 9 (where to look) and section 10 (judgement calls)

| Item | Result |
|---|---|
| 9.1 `storage.py` and callers | Lock (thread `RLock` plus `fcntl.flock`, re-entrant), atomic write and `replace_together` read line by line: no defect. A crash between renames pairs a new model with the old report, and the checksum refuses it (existing test `test_model_from_another_run_is_refused`). Every write of project data goes through `storage.py` (grep of every write call). Timeouts (10 s, none for training) suit the work. Confirmed R1-2 in `MemeLibrary.update` and R1-9 in the collector |
| 9.2 Training job | `status()` returns a frozen copy under a lock; a run that raises ends with its message; two tabs start one run; the result is said once. No defect |
| 9.3 Model loading | Hashes and unpickles the same bytes; label, mode and length checks; scikit-learn note. Confirmed R1-3 and R1-11. The checksum is not a security boundary (whoever can write the model can write the report); only project-made files are loaded, as documented |
| 9.4 Camera path | Retry every 2 s and serialised `detect()`: correct. The iframe script interpolates only the constant `_IFRAME_CSS`, through `json.dumps`. Confirmed R1-5, R1-6, R1-10 |
| 9.5 Meme panel | Every state matches DESIGN_SYSTEM section 4; owner text escaped. Data URIs twice a second: measured in round 5 |
| 9.6 Augmentation | Deterministic (fixed seed per fit), missing hands stay zero, labels tiled in the same block order, held-out rows never augmented, standardisation from the training rows only. No defect |
| 9.7 CSV cache | Keyed on inode, mtime in ns and size; writers always replace the file, so a new version always has a new key. Two readers can store snapshots out of order, which only costs a re-read, never a stale result. No defect |
| 9.8 This session's 18 October changes | R1-8 and R1-13 |
| 10 Alt text prefix | R1-13, owner decision |
| 10 `_changed_settings` | R1-8 fixed. `GD_TOLERANCE` and `GD_MAX_STEPS` are not compared: the documents name exactly augmentation and the l2 list, so that is the documented scope, not a defect. A model trained by a script with other `l2_options` showing "Retrain needed" is correct: it was not trained with the app's settings |
| 10 Threshold 0.70 | Owner decision; replay shows 0 wrong memes. No defect |
| 10 Exact pins | Owner trade-off; installed versions match, `pip check` clean. Noted in `OWNER_QUESTIONS.md` |
| 10 Git tracks the samples | No remote (`git remote -v` empty); no video or zip tracked. No defect |
| 10 Screenshots ignored | Agree; not reviewed one by one |
| 10 Zips in the root | Housekeeping for the owner (`OWNER_QUESTIONS.md`, other notes) |
| 10 Plan's High conflicts | K4 (old prompt in `to be deleted/`), N3 (now pinned), N6 (owner ran the webcam steps), N12 (no sign-in; only if hosted): the severities are reasonable |

### Fixes and their checks

| Check | Command | Result |
|---|---|---|
| New tests before the fixes | `.venv/bin/python -m pytest -q -p no:cacheprovider <the 15 new test ids>` | 17 failed, 5 passed. The 5 that passed guard the fixes (the four accepted image types; a model that stays unusable is reported once) |
| New tests after the fixes | same | 22 passed |
| Test suite | `.venv/bin/python -m pytest -q` | **438 passed in 72.50 s** (417 + 21) |
| Scratch retrain | `train_model.py` into the empty `/tmp/bk-review/retrain-r1` | 34.87 s. Model SHA-256 `1e5813fc...`, unchanged. Report identical apart from `trained_at`; labels identical |
| Clip replay | as in the baseline | **"A wrong gesture was shown in 0 of 16 clips."** Per-gesture shares identical to the baseline. 43.3 s |
| Browser | Streamlit restarted on 8502 after the edits, scratch folders | All six pages load with no Python error at 1280x900 and 390x844, no sideways scroll; Memes preview alt text "Meme: Stressed Higuruma"; focus ring 2px `#2fbf71` on the navigation links |
| Owner's files | `shasum -a 256 -c /tmp/bk-review-hashes-start.txt` | All OK |

Process note: one proof script called `train_model.train()` without the scratch variables. It
stopped at its first check (an empty penalty list) before reading or writing anything; it held the
real `models/.gesture_model.joblib.lock` for that moment. The owner's file hashes and the lock
file's modification time (17 October 13:46:48) were checked straight away: unchanged. Every later
command sets the scratch variables.

### Scores after round 1

| Dimension | Weight | Score | Evidence this round |
|---|---|---|---|
| Correctness | 25% | 8.5 | R1-1, R1-3 fixed and tested. Two Medium owner decisions (R1-4, R1-5) leave misleading behaviour in place |
| Reliability and error handling | 15% | 8.5 | Broken files, a busy dataset and a load during a save now give messages; R1-5 still open (owner) |
| Data integrity, security and privacy | 15% | 9.0 | A failed meme save changes nothing (two tests); text kept as typed; escaping fixed; uploads checked by content |
| Concurrency | 10% | 9.0 | R1-10, R1-11 fixed with deterministic tests; a full concurrency pass is round 3 |
| ML integrity | 10% | 9.0 | Byte-identical retrain after the fixes; R1-14 open (owner) |
| Tests | 10% | 8.5 | 21 regression tests, each failing before its fix; test quality not yet reviewed in depth (round 6) |
| Maintainability | 10% | 8.5 | Five handoff documents updated with the code |
| Performance | 5% | 8.5 | Not yet measured (round 5) |
| **Weighted** | | **8.68** | |

Commit: `67e0ec1` (message "Code review round 1: baseline and broad pass").

## Round 2: correctness and edge cases

Re-read every module and page, and the tests that cover them, with these questions: empty and
one-class datasets, a single recording, NaN and infinity, wrong vector lengths, missing and corrupt
files, unusual frame sizes, one hand against two, Unicode in names and paths. Also re-checked the
round 1 fixes.

### Findings

| ID | Sev. | Area | File and line | What is wrong | Failing case | Evidence | Fix | Test added | Status |
|---|---|---|---|---|---|---|---|---|---|
| R2-1 | Low | Backend (owner decision) | `train_model.py:455-458` | When no row is valid, the message says "Only one gesture (none) has valid samples" | A damaged `samples.csv` in which every vector is all zeros: training says one gesture, named like the `none` class, has samples, while none has | Scratch script printed that message for two all-zero recordings | Wording is the owner's (rule 11) | none | Owner decision (Q5) |
| R2-2 | Low | ML tooling | `check_pipeline.py:111` (`ModelSource.l2`) | `tm.load_report()` raises `TrainingError` for an unreadable report; nothing caught it | `python check_pipeline.py "Meme 3"` with a damaged `training_report.json` (scratch copy) ends in a Python traceback instead of "not checked: ..." | The traceback, run on a scratch model folder | Turn it into `CheckError`, which `check_clips` reports per clip | `test_an_unreadable_report_is_a_clear_error_not_a_traceback` | Fixed |
| R2-3 | Low | Backend (owner decision) | `data_collector.py:48-55` (`slugify_label`) | Ids keep only `a-z` and `0-9`; the message asks for "letters or numbers" | "жест" or "手势" is refused with "Enter a gesture name using letters or numbers." (they are letters); "École" is saved as `cole` | Scratch script | Wording is the owner's; changing how ids are made would change an existing test (`test_slugify` expects `cole`) | none | Owner decision (Q5) |

### Checked and found sound (no finding)

| Case | Result |
|---|---|
| Empty dataset, one gesture, a gesture with one recording | Clear `TrainingError` messages (existing tests); the replay tool says a gesture's only recording cannot be held out |
| NaN, infinity, wrong lengths | Refused on save (`DatasetStore.append`), on prediction (`Predictor.predict`) and by features (`normalize_hand`, `normalize_pose`); dropped and counted by `validate_dataset` |
| Missing or corrupt files | `samples.csv`, `dataset_meta.json`, `memes.json`, the three model files and the hand model each give a message on every page that reads them (after R1-3). A missing report loads the model without the checksum by design, for models from before 17 October (DATA_CONTRACTS) |
| The R1-1 fix with an empty label (only possible by editing the CSV) | Shown as a blank gesture that can be deleted; training drops it as "missing gesture label"; the Memes page and the collector run without an error (AppTest). Before the fix the same row read back as NaN and stopped the Memes page |
| Unusual frame sizes | `correct_aspect` gives the same numbers for 4:3, 3:2 and 16:9 (existing test); `to_camera_scale` keeps portrait and wide shapes; a zero-sized frame cannot come from the camera or a video |
| One hand against two | A missing hand is 63 zeros; two hands labelled the same side keep the more confident one; augmentation leaves a missing hand at zero (existing tests) |
| Unicode in paths | The project path has a space and paths are handled with `pathlib` throughout; `memes.json` is written with `ensure_ascii=False` and read as UTF-8; samples are written and read as UTF-8 |

### Checks

| Check | Command | Result |
|---|---|---|
| New test before the fix | `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_check_pipeline.py::test_an_unreadable_report_is_a_clear_error_not_a_traceback` | 1 failed (`TrainingError`) |
| The tool after the fix | `check_pipeline.py "Meme 3"` on a scratch model folder with a damaged report | Each clip "not checked: Cannot read training_report.json: ..." and the summary; no traceback |
| Test suite | `.venv/bin/python -m pytest -q` | **439 passed in 71.69 s** |
| Clip replay | as in the baseline (this round changed `check_pipeline.py`) | **"A wrong gesture was shown in 0 of 16 clips."** Shares identical to the baseline. 44.7 s |
| Scratch retrain | not needed: no change to training, features, the model, data or storage | |
| Browser | not needed: no change to `ui.py`, `views/`, `app.py` or `.streamlit/` | |
| Owner's files | `shasum -a 256 -c /tmp/bk-review-hashes-start.txt` | 10 of 10 OK |

### Scores after round 2

No score moves: the one fix is in a terminal tool, and the two new findings wait for the owner.

| Dimension | Weight | Score | Evidence this round |
|---|---|---|---|
| Correctness | 25% | 8.5 | Every edge case in the list handled; R1-4, R1-5, R2-1, R2-3 wait for the owner |
| Reliability and error handling | 15% | 8.5 | R2-2 fixed; R1-5 still open |
| Data integrity, security and privacy | 15% | 9.0 | R1-1 fix re-checked with an empty label |
| Concurrency | 10% | 9.0 | Not this round's focus |
| ML integrity | 10% | 9.0 | Replay unchanged |
| Tests | 10% | 8.5 | One regression test added |
| Maintainability | 10% | 8.5 | No change |
| Performance | 5% | 8.5 | Not yet measured |
| **Weighted** | | **8.68** | |

Commit: `00855c3` (message "Code review round 2: correctness and edge cases").

## Round 3: concurrency and reliability

Re-read every module, page and test with these questions: what each thread (WebRTC video, the
`gesture-recognizer` worker, the Streamlit script thread, `model-training`) reads and writes,
under which lock; lock order; camera start, stop and recovery; whether threads stop and
resources are released.

### Findings

| ID | Sev. | Area | File and line | What is wrong | Failing case | Evidence | Fix | Test added | Status |
|---|---|---|---|---|---|---|---|---|---|
| R3-1 | Low | Frontend | `ui.py:522-523` (`_meme_view`), `:481-483` (`meme_thumb`) | The image is checked (`image_problem`), then `stat` and read; the Memes page in another tab can delete it in between (replacing it with another file type deletes the old file after `memes.json` is saved) | The dashboard's Meme panel stops with `FileNotFoundError` for one refresh | Scratch script that removes the file right after the check: `FileNotFoundError` from `result_card` | Catch `OSError` there: the panel shows "Image missing" for that refresh, the thumbnail its usual fallback | `test_an_image_removed_after_its_check_is_shown_as_missing_not_an_error` | Fixed |
| R3-2 | Low | Frontend | `views/collector.py:100`, `:237`, `:248` (at commit `00855c3`) | Saving a recording, Undo and Delete caught `DatasetError` only; a write that fails at the system level (a full disk) raises `OSError` from `storage.atomic_write_bytes` | Disk full when a recording finishes: the page stops with `OSError` and the recording is gone without a word | AppTest with `atomic_write_bytes` failing: `[Errno 28] No space left on device` as a page exception | Catch `OSError` too: "Could not save: ..." / "Nothing was deleted: ...", as the Memes page already does | `test_a_recording_that_cannot_be_written_is_a_message_not_a_python_error`; the round 1 Undo and Delete test now also runs with `OSError` | Fixed |
| R3-3 | Medium | Frontend (owner decision) | `ui.py:475-486` (`meme_thumb`), used by `views/dashboard.py:147` and `ui.history_card` | A gesture without a usable meme image is shown by its name or id in the Latest meme tile and Recent detections. The owner's rule allows names only in the two fix-this messages | (a) A newly trained gesture without a meme: listed by name, while the fix-this messages also name it. (b) `memes.json` unreadable: every detection listed by its id, for example `meme_3`, while nothing else on the page names it | `ui.history_card(..., None, lib)` and `ui.meme_thumb("meme_3", None, lib)` return `meme_3`; the frontend's own record calls the fallback its choice (`CHANGES_2026-10-17.md` section 2) | Two existing tests expect the name, so the change needs the owner (rules 2 and 11) | none | Owner decision (Q6) |

### Checked and found sound (no finding)

| Area | Result |
|---|---|
| Lock order | No path takes two of these in opposite orders: the per-file `storage.locked` locks, `_SNAPSHOTS_LOCK`, `_jobs_lock`, `TrainingJob._lock`, `LiveRecognizer._cond`, `FrameProcessor._lock`, `LandmarkHook._lock`, `Recorder._lock`. `_delete_where` takes the samples lock and then, briefly, the snapshot lock; nothing takes them the other way. `FrameProcessor.process` calls the hook, the recorder and the recogniser outside its own lock |
| Shared state | `FrameProcessor` stats and features under its lock (copies out); `Recorder` under its lock; `LiveRecognizer` latest, vote and history under its condition; `TrainingJob.status()` a frozen copy under its lock; the CSV snapshot cache under its lock; `show_landmarks` is a single boolean written by the page, which is safe |
| Stale results | `LiveRecognizer` drops results from an older generation (`use`, `reset`); tested |
| Threads stop | The recogniser worker exits after 5 s without frames and restarts on the next frame (tested); the training thread ends with its run, and any exception ends it as an error (tested); both are daemon threads |
| Resources | MediaPipe landmarkers close in `__del__` (read in the installed `mediapipe` 1.1.0), so a closed tab's detector is released; `cv2.VideoCapture` is released and the hook closed in `finally` (import and replay); every file handle is opened with `with`; temporary upload folders are removed in `finally`; caches are bounded (`_SNAPSHOTS` 8, `_data_uri` 16, `_thumb_uri` 32, history 10) |
| Camera start, stop, recovery | Stop camera reruns the page, which resets the stats and the recogniser; a missing hand model is retried every 2 s (tested); MediaPipe calls from two streams of one tab are serialised (tested) |
| Training in two tabs, or a tab and the terminal | One `TrainingJob` per model file; a second press while running starts nothing; a terminal run holds the file lock, so the app's run fails at once with a message (tested) |

### Checks

| Check | Command | Result |
|---|---|---|
| New tests before the fixes | `.venv/bin/python -m pytest -q -p no:cacheprovider <the 3 new or extended tests>` | 3 failed, 1 passed (the round 1 `DatasetError` case) |
| After the fixes | `tests/test_memes.py tests/test_pages.py tests/test_status.py tests/test_display.py` | 162 passed |
| Test suite | `.venv/bin/python -m pytest -q` | **442 passed in 72.35 s** |
| Browser | Streamlit restarted on 8502, scratch folders | All six pages at 1280x900 and 390x844: no Python error, no sideways scroll; Memes preview shows its image. Console errors: the known `/<page>/_stcore/health` and `/<page>/_stcore/host-config` 404s, and two `ERR_CONNECTION_REFUSED` while Streamlit restarted |
| Scratch retrain, clip replay | not needed: no change to training, features, the model, data, storage, vision or the predictor | |
| Owner's files | `shasum -a 256 -c /tmp/bk-review-hashes-start.txt` | 10 of 10 OK |

### Scores after round 3

| Dimension | Weight | Score | Evidence this round |
|---|---|---|---|
| Correctness | 25% | 8.5 | R3-3 (the no-names rule) waits for the owner, with R1-4, R1-5, R2-1, R2-3 |
| Reliability and error handling | 15% | 9.0 | A full disk on save, Undo or Delete and an image removed mid-refresh are now messages (tests); R1-5 still open |
| Data integrity, security and privacy | 15% | 9.0 | No change |
| Concurrency | 10% | 9.5 | Lock order, shared state, thread lifetimes and resource release reviewed in full (table above); every race found has a deterministic test |
| ML integrity | 10% | 9.0 | No change |
| Tests | 10% | 8.5 | 3 more regression tests |
| Maintainability | 10% | 8.5 | Frontend architecture updated |
| Performance | 5% | 8.5 | Not yet measured |
| **Weighted** | | **8.80** | |

Commit: `8b8e3e9` (message "Code review round 3: concurrency and reliability").

## Round 4: data integrity, security and privacy

Re-read every module, page and test with these questions: atomic writes, locks and partial saves;
uploads (type, size, name, path); escaping wherever `unsafe_allow_html` or `st.html` is used;
pickle loading; what is written to disk and to logs; how the server can be reached.

### Findings

| ID | Sev. | Area | File and line | What is wrong | Failing case | Evidence | Fix | Test added | Status |
|---|---|---|---|---|---|---|---|---|---|
| R4-2 | High | Backend (configuration) | `.streamlit/config.toml` (no `server.address`) | Streamlit listens on every network interface by default, and no page has a sign-in | Run the app on a shared Wi-Fi: any device on the network can open `http://<this Mac>:8501` and delete gesture data, press Train model or replace meme images. (A visitor's own camera does not work over plain HTTP, but every other page does.) | Startup log: "Network URL: http://192.168.0.203:8502"; `lsof`: `TCP *:8502 (LISTEN)`; `curl http://192.168.0.203:8502/_stcore/health` returned 200 | `server.address = "localhost"`; the camera only works on localhost anyway, so nothing the owner does changes | `test_the_app_listens_on_this_computer_only` | Fixed |
| R4-1 | Low | Backend | `dataset_manager.py:212-223` (`MemeLibrary.remove`) | Deletes the image before saving `memes.json` (the same order as R1-2) | `python dataset_manager.py wave --remove` when `memes.json` cannot be written: the image is gone and the record still points at it ("Image missing" on the dashboard) | Test against the unchanged code: the image was deleted, the record kept | Save `memes.json` first, then delete the image | `test_a_failed_remove_keeps_the_image_and_record` | Fixed |
| R4-3 | Nit | Frontend | `views/privacy.py:15-19`, `views/terms.py:14-25` | `OPERATOR_NAME`, `CONTACT_EMAIL` and `GOVERNING_LAW` go into HTML unescaped | They are written by the owner in `config.py` (code, not data from a file or a user); a name with `<` would be hidden | Code | Not fixed (Nit) | none | Not fixed |
| R4-4 | Nit | Backend | `.gitignore`, `storage.py:54` | A write interrupted by a crash can leave a hidden `.samples.csv.<random>.tmp` beside the data; `.gitignore` covers `.*.lock` but not `.*.tmp` | After a crash, `git add -A` would commit the leftover (the same data as the tracked `samples.csv`) | Code | Not fixed (Nit) | none | Not fixed |

### Checked and found sound (no finding)

| Area | Result |
|---|---|
| Escaping | All 46 `unsafe_allow_html` and `st.html` calls in `ui.py` and `views/` read one by one. Every value from a file, the user, an exception or the report goes through `ui.esc` or `ui.html_table` (after R1-6 and R1-7); the rest are constants or numbers formatted by the code. Alt text is escaped with quotes (`html.escape`). The only script, `_IFRAME_SCRIPT`, interpolates a constant through `json.dumps` |
| Uploads | Type: by content since R1-12. Size: Streamlit's 10 MB limit and `save_edit`'s own check (tested). Name: only the suffix is used, checked against the allowed list; the saved file is `<gesture id>.<suffix>` in `assets/memes/`. Path: the upload is written to a private temporary folder that is removed in `finally`; `image_problem` keeps every shown image inside `assets/memes/` after resolving links (tested with `../` and absolute paths) |
| Atomic writes and locks | Every write of project data goes through `storage.py` (round 1 grep); read-modify-writes hold the file's lock; a failed save leaves the old file (tests); `replace_together` plus the checksum make a half-renamed model set unusable rather than wrong |
| Pickle | Only `models/gesture_model.joblib` (or the scratch folder named by the owner's environment variable) is unpickled, after its checksum is compared with the report. Nothing from a user or the network is unpickled |
| Privacy | Nothing from the camera is written: frames stay in memory (`FrameProcessor`), recent detections are memory only (`DetectionLog`), no code writes images (`cv2.imwrite` and `Image.save` appear only with in-memory buffers). Samples are saved only on Start recording or an import, as the privacy page says. No `logging` is used; the app's training run prints nothing. The privacy page's statements were checked against the code: no change needed, so `LEGAL_LAST_UPDATED` stays |
| Server | Cross-site request protection and CORS are at Streamlit's defaults (both on); usage statistics are off |

### Checks

| Check | Command | Result |
|---|---|---|
| New tests before the fixes | `pytest -q -p no:cacheprovider` on the two new tests | Both failed (`KeyError: 'address'`; the image deleted) |
| Server after the fix | Streamlit restarted with the new config | Log: "Uvicorn server started on localhost:8502", only "URL: http://localhost:8502"; `lsof`: `TCP 127.0.0.1:8502 (LISTEN)`; `curl` to `localhost` and `127.0.0.1`: 200; to `192.168.0.203`: connection refused |
| Test suite | `.venv/bin/python -m pytest -q` | **444 passed in 72.66 s** |
| Scratch retrain | `train_model.py` into the empty `/tmp/bk-review/retrain-r4` | 34.61 s; model SHA-256 `1e5813fc...`; report identical apart from `trained_at` |
| Browser | built-in browser at `http://localhost:8502` | All six pages load with no Python error; at 390x844 no sideways scroll on any page |
| Clip replay | not needed: no change to vision, features, the model or the predictor | |
| Owner's files | `shasum -a 256 -c /tmp/bk-review-hashes-start.txt` | 10 of 10 OK |

Documents updated: `DATA_CONTRACTS.md` and the backend `ARCHITECTURE.md` (remove order), both
handoff READMEs and the root `README.md` (the app listens on this computer only),
`OWNER_QUESTIONS.md` (what changes if the app is ever opened from another device).

### Scores after round 4

| Dimension | Weight | Score | Evidence this round |
|---|---|---|---|
| Correctness | 25% | 8.5 | Owner decisions R1-4, R1-5, R2-1, R2-3, R3-3 still open |
| Reliability and error handling | 15% | 9.0 | No change |
| Data integrity, security and privacy | 15% | 9.5 | The network exposure closed and the last delete-before-save order fixed; full escaping, upload, pickle and privacy audit with no other gap |
| Concurrency | 10% | 9.5 | No change |
| ML integrity | 10% | 9.0 | Retrain unchanged |
| Tests | 10% | 8.5 | 2 more regression tests |
| Maintainability | 10% | 8.5 | Five documents updated with the code |
| Performance | 5% | 8.5 | Not yet measured |
| **Weighted** | | **8.88** | |

Commit: `683dd17` (message "Code review round 4: data integrity, security and privacy").

## Round 5: ML integrity and performance

Re-read every module, page and test with these questions: can a held-out recording leak into
its own model (including through augmentation and standardisation); is training deterministic;
is every number in the report measured the way the report says; what runs per frame and per
page refresh; what training time costs.

**No new finding confirmed this round.**

### ML integrity: evidence

| Question | Result |
|---|---|
| Leakage | Each fold fits on `X[~held_out]` only (`held_out_probabilities`, with an internal check that no recording is on both sides). Augmentation happens inside `fit`, on the rows it was given; the mean and spread for standardisation are taken inside `fit` from those rows and their copies. A recomputation script asserted, for every one of the 16 folds, that the held-out recording is absent from the training rows |
| Determinism | Three scratch retrains in this review (the baseline, rounds 1 and 4) gave the same model file, SHA-256 `1e5813fc...`, and reports identical apart from `trained_at` |
| Metric correctness | The live report's held-out numbers recomputed independently on the scratch data with scikit-learn: accuracy 0.9711 (report 0.9711), macro F1 0.9722 (0.9722), balanced cross-entropy (`log_loss` with balanced weights) 0.0747 (0.0747), confusion matrix equal, and all five cutoff rows equal (for example 0.70: 95.79% accepted, 98.63% of those right). 380 samples and 16 recordings, as reported; the per-recording rows add up to 380 |
| One feature path | Collection, import, replay and the live dashboard all build vectors in `vision.LandmarkHook` through `features.build_feature_vector`; training reads the same vectors from `samples.csv` (saved with `%.6g`, so a live vector and its saved copy differ only below the sixth significant digit) |
| Live rule matches the report | `Predictor.predict` accepts at `confidence >= threshold`, the same comparison as the report's cutoff table |
| Optimism | Choosing l2 on the same folds, and the replay reusing that l2, are stated in the report's cautions and in CONFLICTS N21; not a new finding |

### Performance: measurements

Measured with `time.perf_counter` on this Mac (Apple Silicon), scratch model, a copy of the meme
images in `/tmp`.

| Work | When | Cost |
|---|---|---|
| `FrameProcessor.process` without MediaPipe (mirror, drawing two hands, features), 640x480 | every frame | 1.09 ms |
| `Predictor.predict` | every classified frame | 0.009 ms |
| MediaPipe with video decoding | every frame | about 18 ms per frame in the clip replay (2,220 frames in 44.7 s, less about 5.6 s for 16 held-out fits) |
| Meme panel: read `memes.json`, `result_card` (image cached) | every 0.5 s | 0.10 ms |
| Session panels: read `memes.json`, 11 thumbnails (cached) | every 0.5 s | 0.78 ms |
| `image_problem` (opens and verifies the image) | per meme shown, per refresh | 0.05 to 0.06 ms |
| Meme image sent with each refresh | every 0.5 s while a meme shows | 17 to 27 KB for three memes; 161 KB for `meme_3` (1033x745, shrunk to 900 px and re-encoded once, then cached). About 320 KB/s on localhost: known, RISKS R16, only a cost if hosted |
| Training | Train model | 34.5 to 34.9 s for 97 fits (6 penalties x 16 recordings + 1), each on 5 times the rows because of augmentation; documented, with worker processes as the known option (ROADMAP B7, C1) |

Nothing done per frame or per refresh could be done once and is not already cached.

### Checks

| Check | Command | Result |
|---|---|---|
| Independent metric recomputation | scratch script on `/tmp/bk-review/data`, l2 from the report | All equal (table above) |
| Test suite | `.venv/bin/python -m pytest -q` | **444 passed in 71.74 s** |
| Scratch retrain, clip replay, browser | not needed: no code changed this round | |
| Owner's files | `shasum -a 256 -c /tmp/bk-review-hashes-start.txt` | 10 of 10 OK |

### Scores after round 5

| Dimension | Weight | Score | Evidence this round |
|---|---|---|---|
| Correctness | 25% | 8.5 | No change; owner decisions still open |
| Reliability and error handling | 15% | 9.0 | No change |
| Data integrity, security and privacy | 15% | 9.5 | No change |
| Concurrency | 10% | 9.5 | No change |
| ML integrity | 10% | 9.5 | Every held-out number recomputed independently and equal; no leakage path; three identical retrains. R1-14 (step numbering) waits for the owner |
| Tests | 10% | 8.5 | No change |
| Maintainability | 10% | 8.5 | No change |
| Performance | 5% | 9.0 | Per-frame and per-refresh costs measured and small; training time understood; the one repeated transfer is a known hosting risk |
| **Weighted** | | **8.95** | |

Commit: `73aab7a` (message "Code review round 5: ML integrity and performance").

## Round 6: tests, maintainability and documentation, then a final full pass

Re-read every module, page, test and handoff with these questions: does each test check
behaviour, or could it pass for the wrong reason; are any tests slow or flaky; dead code,
duplication, comments and documents that are no longer true. Then re-read the whole diff of the
review (`git diff code-review-start-2026-10-18`) and re-ran every check.

### Findings

| ID | Sev. | Area | File and line | What is wrong | Failing case | Evidence | Fix | Test added | Status |
|---|---|---|---|---|---|---|---|---|---|
| R6-1 | Low | Backend, ML | `predictor.py:25-26`, `check_pipeline.py:42`, `dataset_manager.py:22-24`, `:76` | Four comments still describe the dashboard before 17 October ("the recognition and meme panels", "the recognition panel", "the dashboard says so", "shown as not set") | A reader looks for panels and text that no longer exist | `grep -n -i "recognition panel\|recognition and meme"` | Comments now describe the one Meme panel and where empty fields show as not set | none (comments only) | Fixed |
| R6-2 | Low | Frontend | `docs/frontend-handoff/README.md:150` | "two 404s for `/<page>/_stcore/health`": the two are one `health` and one `host-config` | A tester sees a 404 the note does not mention | Network log: `/<page>/_stcore/health` and `/<page>/_stcore/host-config` both 404 on every page address opened directly | Note corrected | none (document) | Fixed |
| R6-3 | Low | ML (tests) | `tests/test_predictor.py:263-267` (`test_random_forest_is_switched_to_one_thread`) | Its assertion sits inside `if "n_jobs" in params`, and the saved model has had no `n_jobs` since the switch to softmax regression, so it checks nothing | Disabling `Predictor`'s `n_jobs` line (`predictor.py:139-140`) leaves the test passing | Mutation run: with that line disabled, this test passed and the new test failed; restored afterwards (`git diff` shows only the round's comment edit) | A new test gives `Predictor` a model that has `n_jobs` (a three-tree random forest). The old test is kept (rule 2) | `test_a_model_with_worker_threads_is_switched_to_one` | Fixed |
| R6-4 | Low | Backend (owner decision) | `dataset_manager.py:77-80` (`unfinished`), `:58-61` (`MemeRecord.title`) | No page or script calls them since 17 and 18 October; only tests do | `title` falls back to the gesture name: a later change that uses it for display would bring names back to the dashboard | `grep` of every caller | Removing them means removing tests (rule 2) | none | Owner decision (Q7) |
| R6-5 | Low | Frontend | `ui.py:106` (`.big.ok`), `:114` (`.gap`) | Two CSS rules no page uses (left from the Recognition panel); `DESIGN_SYSTEM.md` still said `.big` is "green when recognised" | A reader keeps or copies styles for markup that no longer exists | `grep` for `big ok` and `class="gap` in `ui.py` and `views/`: none | Rules removed; DESIGN_SYSTEM describes `.big` as the meme title (still 1.5rem: 24 px measured on the Memes preview) | none (no behaviour) | Fixed |
| R6-6 | Nit | Frontend, tests | `views/collector.py:55`, `views/performance.py:24` (`notify`, `name`); `tests/test_pages.py` `_contrast`, `tests/test_display.py` `_luminance` | Small helpers written twice | none | Code | Not fixed (Nit) | none | Not fixed |

### Checked and found sound (no finding)

| Area | Result |
|---|---|
| Flaky tests | The 11 tests that depend on timing or threads (recogniser worker, locks, second training run, two camera streams, the round 1 trace test) ran 20 times in a row while all 10 CPU cores were kept busy: 220 of 220 passed |
| Slow tests | Slowest: `test_train_end_to_end_saves_loadable_artifacts` 14.0 s, the predictor module's training fixture 9.8 s, `test_training_is_repeatable` 7.9 s. All train real models with augmentation; the suite takes about 73 s, as the handoffs say |
| Regression tests | Every fix in rounds 1 to 4 has a test that failed before it and passes after it (28 new tests in all, 417 to 445) |
| Root `README.md` | Read in full; nothing in it is untrue after the review's changes (one sentence added in round 4) |
| The review's own diff | Re-read in full. The restore path in `MemeLibrary.update` handles a new file, a replaced file of the same type and unchanged bytes; `load_predictor` returns at the first success and reports the last problem; the image race paths fall back to "Image missing" |

### Checks (final)

| Check | Command | Result |
|---|---|---|
| Test suite | `.venv/bin/python -m pytest -q` | **445 passed in 73.23 s** |
| Scratch retrain | `train_model.py` into the empty `/tmp/bk-review/retrain-r6` | 34.72 s; model SHA-256 `1e5813fc...`, the live model's; report identical apart from `trained_at`; labels identical |
| Clip replay | as in the baseline | **"A wrong gesture was shown in 0 of 16 clips."** Shares identical to the baseline. 43.7 s |
| Browser | Streamlit restarted on 8502 (localhost only), scratch folders | All six pages at 1280x900 and 390x844: no Python error, no sideways scroll; Tab focus ring 2px `#2fbf71` |
| Owner's files | `shasum -a 256 -c /tmp/bk-review-hashes-start.txt` | 10 of 10 OK |

### Scores after round 6

| Dimension | Weight | Score | Evidence this round |
|---|---|---|---|
| Correctness | 25% | 8.5 | No open defect the reviewer may fix; R1-4, R1-5 and R3-3 (Medium) and R2-1, R2-3 (Low) wait for the owner, and each can leave a misleading message or a name on screen in a reachable case |
| Reliability and error handling | 15% | 9.0 | No change; R1-5 still open |
| Data integrity, security and privacy | 15% | 9.5 | No change |
| Concurrency | 10% | 9.5 | Thread and lock tests stable under full load (220 of 220) |
| ML integrity | 10% | 9.5 | Final retrain and replay unchanged |
| Tests | 10% | 9.0 | Every fix has a failing-first test; no flakiness under load; the one test that checked nothing is now backed by one that does |
| Maintainability | 10% | 9.0 | Stale comments and dead CSS gone, documents corrected; two test-only functions wait for the owner (Q7) |
| Performance | 5% | 9.0 | No change |
| **Weighted** | | **9.05** | |

Commit: `1755264` (message "Code review round 6: tests, maintainability, documentation; final pass").
