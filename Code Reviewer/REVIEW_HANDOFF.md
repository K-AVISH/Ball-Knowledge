# Handoff for the code reviewer and the critic

From the implementation strategist session, 18 October 2026, 10:15. The same session planned the
work on 17 October and built it on 18 October, so **nobody independent has reviewed either the plan
or the code yet**. That is your job. Treat every claim below as a claim to check; each names how it
was checked.

Project folder: `/Users/kavishseema/Desktop/Passion Project`. It is now a **local git repository**
(branch `main`, no remote).

The review process itself (six rounds, scoring, the gate, where to write) is set by
`docs/CODE_REVIEW_PROMPT.md`. Where this handoff and that prompt differ, follow the prompt. This
handoff adds the context the prompt does not have: what changed and when, what is verified, where the
risk is, and the judgement calls to challenge.

## Read this first

1. The code to review is in git: `baseline-2026-10-17..implemented-2026-10-18` (my changes) and, older
   and much larger, the three departments' 17 October work, which was tested but never read line by
   line by anyone else (section 3.2 says how to see it).
2. Never train, import or record into the real `data/`, `models/` or `assets/memes/`. Use scratch
   copies (section 4). `assets/memes/` has no override.
3. The raw video folders (`First meme/`, `Second meme/`, `Meme 3/`, `Meme 4/`, `None/`) show people's
   faces. Use them only through `check_pipeline.py`; never copy, extract frames to keep, or add them to git.
4. The owner's rules in section 8 are not up for debate in a review. If you think one is wrong, report
   it as an owner decision; do not change the code against it.
5. Meme ratings and descriptions are empty on purpose. Only the owner writes them.
6. The prompt requires `git status --short` to be empty before you start. If it is not, ask the owner;
   do not commit files you did not write.

## 1. The project in two minutes

A local Streamlit web app. A person holds a hand gesture up to the webcam; MediaPipe finds the hand
landmarks; a softmax regression model trained on the owner's own recordings classifies them; the
Live dashboard shows that gesture's meme with a confidence meter. Uncertain means no meme. The
dashboard never names a gesture. Five classes: `first_meme`, `second_meme`, `meme_3`, `meme_4` and
`none` (a hand that is not a gesture; never shows a meme). Six pages: Live dashboard, Data collector,
Model performance, Memes, Privacy policy, Terms and conditions.

Spec: `Context.md` (acceptance criteria in section 10) and `Instructions.md` (8 build stages). Several
spec lines were overruled by the owner; the list is in `docs/implementation-plan/OWNER_DECISIONS.md`,
Part 1. Read it before calling anything a spec violation.

## 2. What this session did

| When | What | Record |
|---|---|---|
| 17 Oct | Joined the Backend, Frontend and ML handoffs into one checked picture and plan. Re-ran the suite, a scratch retrain and the clip replay; found 22 conflicts the departments had not listed (the doc-fix session found a 23rd) | `SYSTEM_STATE.md`, `CONFLICTS.md`, `ROADMAP.md`, `OWNER_DECISIONS.md`, `RISKS.md` in `docs/implementation-plan/` |
| 17 Oct | A separate session fixed the department documents (roadmap A2 to A4); this session checked its work | `ROADMAP.md` progress note |
| 18 Oct | After the owner said the webcam steps all work and asked to "implement all of the 3 departments together": git, pinned dependencies, OpenCV clean-up, settings staleness check, alt text, camera hint, the owner's four meme titles, doc updates | `IMPLEMENTATION_LOG.md` (every change and every check) |

## 3. What to review

### 3.1 This session's changes (small, start here)

```bash
git log --oneline baseline-2026-10-17..implemented-2026-10-18
git diff baseline-2026-10-17..implemented-2026-10-18 -- '*.py' requirements.txt config.py assets/memes/memes.json
```

| Commit | What | Code files |
|---|---|---|
| `e315fb2` (tag `baseline-2026-10-17`) | Baseline: the state verified on 17 October, plus doc fixes and the old critique folders moved into `to be deleted/` (ignored) | `.gitignore` |
| `2a42316` | Webcam check recorded in docs; two stale comments | `config.py` (comments only) |
| `6f0d2bf` | The owner's four meme titles, written with `dataset_manager.py` | `assets/memes/memes.json` |
| `255363b` | Pinned dependencies; staleness also covers training settings; alt text; camera hint | `requirements.txt`, `train_model.py`, `ui.py`, `tests/test_status.py` |
| `b21c9e9` (tag `implemented-2026-10-18`) | Plan documents updated | none |

Not in git: in the project `.venv`, `opencv-python-headless` was uninstalled and
`opencv-contrib-python 5.0.0.93` reinstalled from the same version's wheel (CONFLICTS N4). Writing the
titles also created the empty lock file `assets/memes/.memes.json.lock` (expected, ignored by git).

Exact places:

| Change | Where |
|---|---|
| Settings staleness | `train_model.py:374` (call), `train_model.py:382` (`_changed_settings`) |
| Alt text | `ui.py:489` (`meme_alt`), used at `ui.py:485` (thumbnails) and `ui.py:525` (meme frame) |
| Camera hint | `ui.py:737` |
| New and changed tests | `tests/test_status.py:97`, `:107`, `:193` (now includes alt text), `:199`, `:212` |
| Pins | `requirements.txt` (all direct dependencies `==`, Pillow added) |

### 3.2 The departments' 17 October work (large, never independently reviewed)

These changes are inside the baseline commit, so git cannot show them as a diff. The file
`backend-handoff-2026-10-17.zip` in the project root (12:45, ignored by git) predates them: it has no
`storage.py`, no `tests/conftest.py`, no `ui.result_card`, no `features.augment_hands` and no
`TrainingJob` (checked by searching the unzipped files). Compare it with the baseline tag in scratch
folders; this shows only the departments' 17 October work, not this session's:

```bash
mkdir -p /tmp/bk-pre17 /tmp/bk-baseline
unzip -q -o backend-handoff-2026-10-17.zip -d /tmp/bk-pre17
git archive baseline-2026-10-17 | tar -x -C /tmp/bk-baseline
diff -ru /tmp/bk-pre17 /tmp/bk-baseline -x docs -x 'New files fopr critiquing' -x 'Implementation Stratergist' -x .claude -x .agents -x .streamlit -x .gitignore -x .gitkeep > /tmp/bk-dept-17oct.diff
```

Checked on 18 October: 29 files differ (26 changed, 3 new: `storage.py`, `tests/conftest.py`,
`tests/test_storage.py`), about 4,400 diff lines. The zip also holds the owner's samples and model;
delete `/tmp/bk-pre17` when done.

What each department says it changed, with its own write-up:

| Department | Main changes | Write-up |
|---|---|---|
| Backend | `storage.py` (atomic writes, thread plus file locks), locks in `data_collector`, `dataset_manager`, `train_model`; background `TrainingJob`; model SHA-256 in the report, checked by `Predictor.load`; dataset fingerprint for staleness; `LandmarkHook` retry and serialised detector calls; parsed-CSV cache; `tests/conftest.py` guard | `docs/backend-handoff/README.md` section 7 |
| Frontend | One Meme panel (`ui.result_card`) and no gesture names on the dashboard; meme thumbnails; notices restyled; subgrid tiles; camera iframe CSS; per-page tab titles | `docs/frontend-handoff/CHANGES_2026-10-17.md` |
| ML | Landmark augmentation (`features.augment_hands`, `gd_model` parameters and `__setstate__`), the 0.003 penalty, retrained live model | `docs/ml-handoff/README.md`, `RESULTS_AND_DATA.md` |

## 4. Setup and the standard check

macOS on Apple Silicon, Python 3.14.7, project `.venv` (already set up). A fresh setup:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python download_models.py --pose
```

The checks every change must pass (from `ROADMAP.md`):

```bash
source .venv/bin/activate
python -m pytest -q
```

```bash
mkdir -p /tmp/bk-check/data /tmp/bk-check/models
cp data/samples.csv data/dataset_meta.json /tmp/bk-check/data/
cp models/gesture_model.joblib models/label_mapping.json models/training_report.json /tmp/bk-check/models/
BALLKNOWLEDGE_DATA_DIR=/tmp/bk-check/data BALLKNOWLEDGE_MODEL_DIR=/tmp/bk-check/models python check_pipeline.py "First meme" "Second meme" "Meme 3" "Meme 4" None
```

Pass: at least 417 tests pass, and the replay ends with "A wrong gesture was shown in 0 of 16 clips".
For training changes, also retrain into an empty scratch model folder and compare the report with
`models/training_report.json`.

To look at the site with scratch data (port 8502; the owner uses 8501):

```bash
BALLKNOWLEDGE_DATA_DIR=/tmp/bk-check/data BALLKNOWLEDGE_MODEL_DIR=/tmp/bk-check/models streamlit run app.py --server.port 8502
```

## 5. Working rules for reviewers

- Other Claude sessions may work in this folder. Check recent file times before editing, use small
  edits, and re-run the suite before blaming your own change.
- Streamlit does not reload imported modules. Restart it after any change to `ui.py` or a backend module.
- Git: commit as the prompt says (one commit per round, message starting `Code review round N:`,
  never data, models or memes), never `git push`, never add a remote, never rewrite history or move
  the tags `baseline-2026-10-17` and `implemented-2026-10-18`.
- `to be deleted/` holds old documents the owner will delete. Do not use them: they describe the
  dashboard before 17 October. The one useful thing in them, the critique rubric, is also in
  `docs/ui-critique-log.md`.
- `/train` (`.claude/commands/train.md`) trains the live model. Do not run it.

## 6. What has been verified

| Claim | Result | How, when |
|---|---|---|
| Test suite | 417 passed (73 s) in the project `.venv`; 417 passed in a fresh venv built from `requirements.txt` | 18 Oct, 09:55 to 09:58 |
| Environment | Installed versions match every pin; one OpenCV; `pip check` clean | `pip freeze`, `pip check`, 18 Oct |
| Live model is reproducible | Scratch retrain gives a model with the same SHA-256 (`1e5813fc...`) and a report identical apart from `trained_at`, in 34.6 s | 18 Oct, 09:58 |
| Clip replay | 0 wrong memes in 16 clips; right result on 87% (first_meme), 89% (meme_3), 60% (meme_4, 33% no hand), 86% (none, shown as No gesture), 87% (second_meme) of hand frames | `check_pipeline.py` on scratch copies, 18 Oct, 09:59 |
| Live model numbers | Held-out (leave one recording out) accuracy 97.1%, cost 0.0747, macro F1 0.972, l2 0.003 | `models/training_report.json`, trained 17 Oct 13:47 |
| Report protections | `dataset.fingerprint` matches `data/samples.csv`; `artifacts.model_sha256` matches the model file; `staleness()` returns nothing | 17 and 18 Oct |
| Pages | All six load with no Python error (Privacy and Terms checked at 10:12, both with the expected "Before launch" banner); Memes shows the four titles and alt text "Meme: Stressed Higuruma"; Model performance shows no "gradient"; no sideways scroll at 390 px on Memes and the dashboard; only the known `/<page>/_stcore/health` 404s in the console | built-in browser (Chromium), port 8502, scratch data, 18 Oct |
| Owner's webcam | "It works just fine and I've tested all the steps" (owner, 18 Oct, current model) | Owner's report only. `memes.json` was unchanged afterwards, so README step 7 (saving a rating) cannot have been done on the real file |
| Integration of the three departments' work | Every change each handoff lists is present in the code | 17 Oct, `SYSTEM_STATE.md` section 5 |

## 7. What has not been verified

| Item | Why |
|---|---|
| The dashboard with a gesture held, since the titles were added | No camera in this session; the HTML is covered by `tests/test_status.py` and `tests/test_memes.py` |
| Safari | Never tested by anyone |
| A screen reader | Never tested; the dashboard has no live region for new memes (roadmap C4) |
| Any recognition quality beyond the owner's own 16 recordings | All data is one room, two days, `person` empty in all 380 rows; 97% is an upper bound (`RISKS.md` R1) |
| The departments' code, line by line | See 3.2 |
| Hosting | Not built; `LAUNCH_CHECKLIST.md` and roadmap Phase D |

## 8. Rules the product must keep

Mechanical ones are enforced by `tests/test_style_rules.py`, `tests/test_pages.py` and
`tests/test_status.py`; the rest need reading.

| Rule | Enforced by tests? |
|---|---|
| Uncertain means no meme: below 0.70, or before 4 of the last 7 frames agree, no meme; `none` never shows one | Partly (`test_status.py`, `test_predictor.py`) |
| The Live dashboard never names a gesture, including alt text. Exception: messages that ask the owner to fix a gesture ("No meme set", "No usable meme image yet for: ...") | Yes (`test_status.py`) |
| Honest numbers: only measured values, said what they were measured on; `n/a` when missing; no training accuracy shown as quality | Partly |
| Split by recording: every evaluation holds out whole `session_id`s | Yes (`test_train_model.py`) |
| One feature path: collection, import, training and live prediction all use `features.build_feature_vector` via `vision.LandmarkHook` | No, read the code |
| Privacy: no video or images of people stored, only landmark numbers; recent detections memory only; any change needs the owner and a privacy page update | No, read the code and `views/privacy.py` |
| Design: no emoji, em dashes, gradients, animations, pill shapes, purple, shadows (except `box-shadow:none`), "Made with" badges; one camera button, one record button; the word "gradient" never in `ui.py`, `app.py`, `views/` | Yes (`test_style_rules.py`) |
| Data from files or users is escaped (`ui.esc`) before it goes into HTML | Partly |
| Every file write goes through `storage.py` (atomic, locked) | No, read the code |
| Owner decisions only: model family, features, privacy, colours, dashboard layout, anything user-visible, launch | Not testable |

## 9. For the code reviewer: where to look, in order

1. **`storage.py` and its callers.** Locking (`storage.py:159`, thread lock plus `fcntl.flock`,
   re-entrant per thread), atomic writes (`:84`), `replace_together` (`:100`, renames in order, report
   last). Questions: can a crash between renames still pair a new model with old labels (the report's
   SHA-256 is meant to catch it)? Is every writer in `data_collector` (`append` at `:335`),
   `dataset_manager` (`update` at `:170`, `remove` at `:212`) and `train_model` inside the lock? Are
   the timeouts (10 s, none for training) right?
2. **Training job and model saving.** `train_model.TrainingJob` (`:551`), `training_job` (`:609`),
   `train` (`:410`), `save_artifacts` (`:327`), and `views/performance.py:108`. Thread safety of
   `status()`, a run that raises, two tabs pressing Train model, the one-time result message.
3. **Model loading.** `predictor.Predictor.load` (`:143`): it hashes and unpickles the same bytes;
   label and feature-mode cross-checks; scikit-learn version warning. `LiveRecognizer.use` (`:334`) and
   its generation counter. Pickles run code when loaded: only project-made files should ever be loaded.
4. **Camera path.** `vision.LandmarkHook` (`:265`, retry every 2 s, serialised `detect()`), and
   `ui.py:665` / `ui.py:728`, which injects CSS into the streamlit-webrtc iframe with
   `unsafe_allow_javascript=True` (check nothing from data is interpolated).
5. **The Meme panel.** `ui.result_card` (`ui.py:536`) and `_meme_view` (`:502`): every state, escaping,
   images sent as data URIs twice a second (`_data_uri`, `:443`).
6. **Augmentation.** `features.augment_hands` (`features.py:127`) and `gd_model.fit` (`:80`),
   `__setstate__` (`:72`): determinism, missing hands stay zero, held-out rows never augmented.
7. **CSV cache.** `DatasetStore._snapshot` (`data_collector.py:258`), keyed on inode, mtime in ns and
   size (`:196`): any way to read stale samples?
8. **This session's changes** (section 3.1). They are small; see section 10 for the calls to challenge.

## 10. Judgement calls in this session's work, to challenge

| Call | Why it was made | Possible objection |
|---|---|---|
| Alt text is "Meme: <title>", not just "<title>" | Tells a screen-reader user it is a meme picture; kept an existing test | The owner's chosen option read "meme title, else Meme"; the "Meme: " prefix was not asked for |
| `_changed_settings` compares augmentation and the l2 list only | Those are what the ML rollback advice changes | `GD_TOLERANCE` is also in the report (`cost.tolerance`) and is not compared; `GD_MAX_STEPS` is not recorded at all; it builds a model just to read settings and would fail if `GD_L2_OPTIONS` were empty; a model trained programmatically with other `l2_options` now shows "Retrain needed" |
| Threshold kept at 0.70 | The owner reported all webcam steps work, including "a relaxed hand never shows a meme" | That report had no per-step notes |
| `requirements.txt` pins exact versions, including pytest | Reproducibility; the CSS depends on Streamlit 1.65 internals and the model is a pickle | Exact pins block security fixes until someone updates them on purpose |
| Local git tracks `data/samples.csv`, the model and the meme images | The owner chose it, for rollback | The privacy page calls the samples personal data; any future remote must exclude them or get a separate owner decision |
| `docs/screenshots/` ignored by git | Critique screenshots may show frames from the owner's videos (not checked one by one) | Some may be harmless and useful history |
| The three old zips left in the project root, ignored | Not asked about; the git tags replace them | Clutter, and one of them holds personal data outside git |
| Plan's own judgement | Twenty-three new conflicts and their severities in `CONFLICTS.md` | Unreviewed; check the High rows (K4, N3, N6, N12) in particular |

## 11. UI notes for the browser checks and the critique

Score with the prompt's rubric (its section 6). The notes below are for the browser checks and for
judging user-visible findings.

### What changed since the last scored UI critique

The last scored critique was on 14 October: 9.07 weighted (`docs/ui-critique-log.md`, round M6). Since
then the dashboard was rebuilt and **has not been scored again** (CONFLICTS N7):

| Date | Change |
|---|---|
| 17 Oct | The Recognition, Meme result and Top scores panels became one Meme panel: the meme in a 4:3 frame, the confidence meter under it. Every non-meme state is a message in the same frame. No gesture names on the dashboard. Thumbnails in Live statistics and Recent detections. Notices restyled into the site palette. Subgrid tiles. Camera off shows a 4:3 placeholder. Per-page tab titles |
| 18 Oct | The owner's meme titles now show under the meter (1.5rem, `.big`). Alt text never names a gesture. The missing-hand-model hint says the camera recovers by itself |

### What to measure

- The earlier UI rubric is in `docs/ui-critique-log.md`, section "Rubric". It helps judge whether a
  user-visible problem is real; it does not replace the prompt's code rubric.
- Every dashboard state in `docs/frontend-handoff/DESIGN_SYSTEM.md` section 4, at 1280x900 and 390x844.
- **New with the titles:** the Meme panel is now one title line taller. The 17 October claim "meme in
  view at 1280x900" was measured with no titles; measure it again with a gesture held.
- Keyboard focus on every control, text contrast (4.5:1 or more), no sideways scroll at 390 px.
- Without a webcam: patch `navigator.mediaDevices.getUserMedia` inside the streamlit-webrtc iframe to
  return a new `canvas.captureStream()` on every call and draw frames onto the canvas
  (`docs/frontend-handoff/README.md` section 4). If you feed frames from the owner's clips, keep them
  hidden and delete any extracted frames afterwards.

### Limits on what you may recommend

Owner decisions, not critique findings: the no-names rule, showing the owner's meme text under the
meter (OD-4), colour scheme (notice colours approved 18 Oct), Streamlit as the stack, no animations.
The owner declined two wording changes on 18 October (an augmentation line on Model performance, and
"including No gesture" on the classes tile); do not re-propose them without new evidence. Never write
meme ratings or descriptions, even as examples on the real site.

## 12. Open items you will run into

| Item | State | Where |
|---|---|---|
| New recordings (more people, rooms, webcam recordings, `person` filled in) | Waiting on the owner | `OWNER_DECISIONS.md` OD-7 |
| Retrain on new data, training time, worker processes | Blocked on the recordings | `ROADMAP.md` B4, B7, C1 |
| Screen-reader announcement, Safari | Not done (needs VoiceOver and Safari) | `ROADMAP.md` C4, C5 |
| Per-gesture thresholds, Prediction History page, hosting | Owner has not decided | OD-2, OD-3, OD-6 |
| No sign-in on any page | Fine locally; a launch blocker if hosted | `CONFLICTS.md` N12 |

## 13. How to report

Follow the prompt: findings, checks and scores in `docs/code-review/REVIEW_LOG.md`, questions for the
owner in `docs/code-review/OWNER_QUESTIONS.md`, a one-page summary in `docs/code-review/README.md`, with
its severity scale (Critical, High, Medium, Low, Nit) and its fix policy (sections 3 and 4).

Two additions from this handoff:

- For each item in section 9 (where to look) and section 10 (judgement calls), record whether you
  confirmed a problem, found none, or could not check it, so the owner can see every one was looked at.
- When a finding is about one department's 17 October work, name the department (Backend, Frontend or
  ML), so its handoff can be corrected in the same commit.

## 14. File map

| Need | File |
|---|---|
| The review process: rounds, rubric, gate, where to write | `docs/CODE_REVIEW_PROMPT.md` |
| Overview of the plan and today's state | `docs/implementation-plan/README.md` |
| What was built on 18 October, with checks | `docs/implementation-plan/IMPLEMENTATION_LOG.md` |
| The verified system, every interface between departments | `docs/implementation-plan/SYSTEM_STATE.md` |
| Known conflicts and gaps | `docs/implementation-plan/CONFLICTS.md` |
| Plan, order and shared-file rules | `docs/implementation-plan/ROADMAP.md` |
| Owner's answers and open decisions | `docs/implementation-plan/OWNER_DECISIONS.md` |
| Risks | `docs/implementation-plan/RISKS.md` |
| Backend modules, data formats | `docs/backend-handoff/ARCHITECTURE.md`, `DATA_CONTRACTS.md` |
| Pages, styling, every UI state | `docs/frontend-handoff/ARCHITECTURE.md`, `DESIGN_SYSTEM.md` |
| Model, training, results | `docs/ml-handoff/ARCHITECTURE.md`, `RESULTS_AND_DATA.md` |
| UI decision history and the rubric | `docs/ui-critique-log.md` |
| User guide and the webcam test | `README.md` (root) |
| Launch requirements | `LAUNCH_CHECKLIST.md` |
