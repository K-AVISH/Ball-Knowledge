# Roadmap

The sequenced plan for all three departments and the owner, built from `SYSTEM_STATE.md` and
`CONFLICTS.md` (snapshot 17 October 2026, 16:29 to 16:37). IDs in brackets (K1, N3, OD-1) point to
those files and to `OWNER_DECISIONS.md`.

Owners: **B** Backend, **F** Frontend, **M** AI/ML, **O** Owner. Sizes: **S** under half a day,
**M** up to 2 days, **L** more.

## The standard check

Every item below that changes code, settings, data or the model ends with this check, on scratch
copies, unless the item says otherwise. It is what the strategist ran for the snapshot.

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

Pass means: the suite passes with no fewer tests than before (413 at the snapshot), and the replay
ends with "A wrong gesture was shown in 0 of 16 clips". Items that change training also retrain on a
scratch copy and compare the report with the live one.

## Phase A. Reconcile the documents and protect the work

Why first: three departments edited the same files on one day without version control. The
integration check passed (`SYSTEM_STATE.md` section 5), so this is the cheapest moment to freeze a known
good state before anyone edits again.

**Progress (18 October, 10:00):** Phase A is done (A1 to A8; A8 by the git tag, the three zips stay
ignored in the project root). B1 done by the owner's report, B2 settled (0.70 kept), B6 done, C2 done,
C3 done as approved (hint fixed, colours kept; augmentation line and classes note declined), meme titles
in. Details and checks: `IMPLEMENTATION_LOG.md`. Next: B3 (owner's recordings), then B4 and B7.

**Earlier progress (17 October, about 17:00):** the doc-fix session finished A3 and A4 and all of A2 except the
`config.py` comments (N14), which stay with Backend. The strategist re-ran the three grep checks
(nothing printed) and confirmed only 6 documents changed: no code, data or model. One leftover,
N23, goes to Frontend.

| ID | Item | Owner | Done looks like | Verified by | Depends on | Size |
|---|---|---|---|---|---|---|
| A1 | Put the project under local git (K6) | O decides (OD-8), B sets it up | A local repository whose first commit is today's verified state. `.gitignore` excludes `.venv/`, `__pycache__/`, `.pytest_cache/`, the raw video folders (`First meme/`, `Second meme/`, `Meme 3/`, `Meme 4/`, `None/`), `*.zip` and lock files. No remote unless the owner says so | `git status` clean; `git ls-files \| grep -i "\.mov$"` prints nothing; standard check | OD-8 | S |
| A2 | Backend document fixes | B | `docs/backend-handoff/` fixed for N2 (dead link), N16 (live model has a checksum), N17 ("Hold it steady"), K5 (speed table says "before augmentation" and adds the 34.78 s measurement); `config.py` comments fixed (N14) | `grep -nE "STRATEGIST_HANDOFF.md\|has no checksum\|or \"Checking\"" docs/backend-handoff/*.md` prints nothing; suite passes | none (A1 first if possible) | S |
| A3 | Frontend document fixes | F | `docs/frontend-handoff/` fixed for K1 (413 tests, training runs in the background, no spinner), N7 (9.07 labelled as 14 October), N18, N2; root `README.md` line 255 (N18) | `grep -nE "387 passed\|spinner\|Training blocks\|blue \"Set them\|IMPLEMENTATION_STRATEGIST_HANDOFF.md" docs/frontend-handoff/*.md` prints nothing | none | S |
| A4 | ML document fixes | M | `docs/ml-handoff/` fixed for K2 (413), N20 ("person not recorded" instead of "about 2 people"), N21 (replay uses the saved l2) | `grep -n "337 in the zipped" docs/ml-handoff/*.md` prints nothing | none | S |
| A5 | Archive the old documents (K4) | O approves (OD-11), F moves | `New files fopr critiquing/`, `old files for critiquing/` and `Claude outputs/` moved to `docs/archive/2026-10-14/` with a one-line note at the top of each folder: "Archive. Describes the dashboard before 17 October. Current docs: `docs/implementation-plan/README.md`". Links in `docs/backend-handoff/README.md` line 24 and `docs/ml-handoff/README.md` line 23 updated by B and M | `grep -rn "New files fopr critiquing" README.md docs/backend-handoff docs/frontend-handoff docs/ml-handoff` only shows the new archive path | OD-11 | S |
| A6 | Pin the tested versions and clean OpenCV (N3, N4, N22) | B | `requirements.txt` pins the versions in `SYSTEM_STATE.md` section 0, adds Pillow, keeps one OpenCV. The real `.venv` has only `opencv-contrib-python` | In a **new scratch venv**: `pip install -r requirements.txt`, `pip list \| grep -i opencv` shows one line, suite passes. Then the same in the real `.venv` (uninstall both OpenCV packages, reinstall contrib), standard check | A1; **not while the owner's Streamlit server or any test run uses `.venv`** | S |
| A7 | Integration re-check after Phase A | B (or the strategist) | `SYSTEM_STATE.md` section 5 table re-run; standard check; scratch retrain gives model SHA-256 `1e5813fc...` | Commands in `SYSTEM_STATE.md` section 3.2 | A2 to A6 | S |
| A8 | One package instead of three zips (N1) | B | A git tag `reconciled-2026-10` (or one dated zip) replaces the three `*-handoff-2026-10-17.zip` files; the old zips moved to `docs/archive/` | Unzip or check out into a scratch folder; suite passes there | A7 | S |

## Phase B. Make local use reliable for the owner

Why second: `Context.md` section 9 says no cloud deployment until local use is reliable, and the one
end-to-end check of the new model (the owner's webcam) is not on record (N6).

| ID | Item | Owner | Done looks like | Verified by | Depends on | Size |
|---|---|---|---|---|---|---|
| B1 | Webcam check with the current model (N6) | O | Restart Streamlit first so it loads the current code and model. Run README "With your webcam" steps 1 to 9 and write down each step's result (pass or what you saw, which gesture, roughly how long). Step 4 (a relaxed hand never shows a meme) and step 3 for meme_4 done by you are the results that matter most | The written record, plus the Model performance tag "Trained 17 Oct 13:47" seen during the check | none | S (about 15 minutes) |
| B2 | Confidence threshold decision (K3, OD-1) | O decides, M implements | Decision recorded in `OWNER_DECISIONS.md`. If changed: `DEFAULT_CONFIDENCE_THRESHOLD` updated, the "In use" row on Model performance moves | Standard check (0 wrong memes); B1 steps 3 and 4 repeated with the new value | B1 | S |
| B3 | Record the next data (OD-7) | O records, M briefs | Every gesture has at least 3 recordings and 100 samples; every new recording has "Recorded by" (or `--person`) filled in; at least one recording per gesture made with the webcam on the Data collector page; at least one other room or light; at least 2 meme_4 recordings by the owner | Data collector "Your dataset" list; per-gesture counts and non-empty `person` for new rows (pandas one-liner in `SYSTEM_STATE.md` section 3.3) | B1 (to know which gestures fail live). A1 if the owner wants data changes in git | M (owner's time) |
| B4 | Retrain on the new data and compare | M | Scratch retrain; a table comparing held-out accuracy, cost, per-class F1 and the cutoff table with today's numbers; replay 0 wrong; the owner then approves training the live model | Standard check; comparison table in `docs/ml-handoff/RESULTS_AND_DATA.md`; B1 steps 3 and 4 again | B3, B2 | S to M |
| B5 | Meme titles, ratings and descriptions | O | All four memes Set in the Memes table | README steps 7 to 9 | none. While the owner edits, nobody else writes `assets/memes/` | S |
| B6 | Alt text decision implemented (N5, OD-5) | F | `ui._meme_view` and `ui.meme_thumb` follow the decision; `tests/test_status.py` either checks alt text too or names the exception in its docstring | Suite; the dashboard HTML (AppTest or browser) checked for the decided alt text | OD-5 | S |
| B7 | Training time at the new data size (K5) | B | Training timed on a scratch copy of the post-B3 data with the current recipe; `docs/backend-handoff/README.md` section 7 table updated; a yes or no on worker processes with the number behind it | The timing run's output | B3; no ML change to `train_model.py` in progress | S |

## Phase C. Quality improvements

Items here wait for B3 or B4 where they need more data, and for an owner decision where noted.
Safari moved here from the frontend's list (its item 4): the owner runs Chrome locally, so Safari does
not affect local reliability; it becomes a launch requirement in D6.

| ID | Item | Owner | Done looks like | Verified by | Depends on | Size |
|---|---|---|---|---|---|---|
| C1 | Worker processes for training (only if B7 says so) | B | Training faster, with a report identical to a sequential run apart from `trained_at` | Report comparison; suite; Train model on a scratch copy in the browser shows the progress bar to the end | B7; ML not editing `train_model.py` | M |
| C2 | Staleness also covers training settings (N10) | B | `staleness()` returns a reason when `config` augmentation or l2 options differ from the report's | New test in `tests/test_train_model.py`; suite | none (touches `train_model.py`: not with C1) | S |
| C3 | Wording approvals implemented (N11, N15, N19, OD-9, OD-10) | F, M checks model text | Notice colours kept or reverted; Model performance says augmentation was used and that "Cost at the end" is over augmented rows; camera hint updated; Gesture classes tile wording as decided | Suite (`tests/test_style_rules.py` still bans "gradient"); browser check at 1280 and 390 px | OD-9, OD-10 | S |
| C4 | Screen-reader announcement of a new meme | F | A polite live region announces only changes of the steady meme, following the OD-5 naming decision | VoiceOver on the Mac: one announcement per meme change, none on every refresh; suite | B6 | M |
| C5 | Safari check | F | README webcam steps 1 to 6 in Safari on localhost with scratch data; tiles (subgrid) and notices (`:has()`) render; results written down | The record; screenshots | none | S |
| C6 | Override for the memes folder (I15) | B | `BALLKNOWLEDGE_MEMES_DIR` redirects `memes.json` and images; `tests/conftest.py` still guards the real folder | Tests for the override; suite | A1 | S |
| C7 | Hand position relative to the face | M | A new feature mode, re-extracted from all videos into a scratch data folder, compared leave-one-recording-out (and leave-one-person-out once B3 gives 2 people per gesture) with the current model; replay 0 wrong | Comparison table; standard check | B3; owner approval (feature layout is the owner's call, OD-14) | L |
| C8 | Nested selection of l2 and augmentation | M | Unbiased held-out numbers reported next to today's | Comparison table in `RESULTS_AND_DATA.md` | B3 (needs 3 first_meme recordings) | M |
| C9 | Per-gesture thresholds (only if OD-2 says yes) | M analysis, B `memes.json` field and `predictor`, F meter | Each gesture's cutoff from held-out data; meter shows that gesture's threshold | Replay 0 wrong; suite; cutoff table per gesture | OD-2, B4 | M |
| C10 | Terminal-started training shown on the page (only if wanted, OD-15) | B, F | Page shows "Training in progress" whenever the model lock is held | AppTest with the lock held from another thread | OD-15 | S |
| C11 | Prediction History page (only if OD-3 says yes) | F, B | As decided in OD-3 | Suite; browser | OD-3 | M |

## Phase D. Launch preparation

Gated: start only after the owner decides to host (OD-6) and Phase B is done.

| ID | Item | Owner | Done looks like | Verified by | Depends on | Size |
|---|---|---|---|---|---|---|
| D1 | Hosting decision, domain, operator details | O | Domain and host chosen; `OPERATOR_NAME`, `CONTACT_EMAIL` (and `GOVERNING_LAW` if wanted) set in `config.py` | The legal pages' warning banner is gone | OD-6, Phase B | S |
| D2 | Access control for owner-only actions (N12) | B, F | Visitors reach the Live dashboard only; recording, Train model, meme editing and deleting need the owner. Added to `LAUNCH_CHECKLIST.md` | A visitor session on a test host cannot reach any write action; tests | D1 | M to L |
| D3 | Per-user data or a read-only public mode | B | Visitors never share or change files; a database only if the owner wants visitor data | Two browser sessions on a test host do not see each other's recent detections or data | D2 | L |
| D4 | HTTPS and a TURN server | B, F | `iceServers` set on both ends; camera works over the internet; the privacy page names the TURN provider (the page says it must) | Camera test from another network; privacy page diff approved by the owner | D1 | M |
| D5 | Image bandwidth | F | The meme image is not re-sent as a data URI twice a second | Browser network panel shows one image request per meme change | D1 | M |
| D6 | Camera on the final domain, Chrome and Safari | F | README webcam steps 1 to 6 pass on the domain in both browsers | The record | D4, C5 | S |
| D7 | Legal review | O (a qualified person) | Privacy and terms reviewed against the final data handling | Reviewer's sign-off | D2 to D4 | external |
| D8 | Launch audit | any | `/launch-check` reports every item done | Its table | D1 to D7 | S |

## Dependency view

Arrows mean "must finish before". Items on the same line with no arrow between them can run together.

```
OD-8 -> A1 -> A6 -> A7 -> A8
             A2, A3, A4 (each in its own docs folder) -> A7
OD-11 -> A5 -> (B and M update their links in A2, A4)

B1 -> OD-1 -> B2 --+
B1 -> B3 ----------+-> B4 -> C9 (if OD-2), C7 (if OD-14), C8
          B3 -> B7 -> C1
OD-5 -> B6 -> C4
OD-9, OD-10 -> C3
B5, C5, C6, C2: no dependencies inside the plan

OD-6 + Phase B -> D1 -> D2 -> D3
                  D1 -> D4 -> D6 (also needs C5)
                  D1 -> D5
          D2, D3, D4 -> D7 -> D8
```

Cross-department blockers, in plain words:

- The owner's webcam check (B1) blocks the threshold decision (B2), the next recordings (B3) and so
  all model work in Phase C.
- New data (B3) blocks ML's retrain (B4), Backend's speed decision (B7, then C1) and ML's nested
  selection and face-position work (C7, C8).
- The owner's alt text decision (OD-5) blocks Frontend's B6 and the screen-reader work (C4).
- Hosting (OD-6) blocks all of Phase D; Backend's access control (D2) blocks per-user data (D3) and
  the legal review (D7).

## What can run in parallel right now

These lanes touch different files, so they can run at the same time:

| Lane | Work | Files it writes |
|---|---|---|
| Owner | B1 webcam check, then the decisions, then B5 meme texts | `assets/memes/` (B5 only; nobody else writes there meanwhile) |
| Backend | A2 | `docs/backend-handoff/`, comments in `config.py` |
| Frontend | A3, then C5 Safari on scratch data (port 8502) | `docs/frontend-handoff/`, root `README.md` |
| ML | A4, then the threshold evidence for OD-1 | `docs/ml-handoff/` |

Not in parallel:

- **A6 (reinstalling OpenCV) must not run while the owner's Streamlit server or any test run uses
  `.venv`.** Do it after B1, at a time agreed with the owner.
- A1 (git) should land before any department edits code.
- Anything that writes `data/` or `models/` for real (B3 recordings, the live retrain after B4) runs
  only when no one else is testing. Everyone else uses scratch folders.

## Shared files: who goes first

| File | Departments that edit it | Rule and order |
|---|---|---|
| `train_model.py` | B (job, locks, saving, staleness), M (recipe, evaluation) | One at a time. Order: M's recipe changes (C7, C8, C9) before B's C1 worker processes; C2 must not overlap C1 |
| `config.py` | B (paths, comments), M (training and threshold settings), F (display and legal settings) | One at a time, smallest edits. Order now: A2 comments, then B2 threshold (if changed), then D1 operator details |
| `ui.py` | F owns; B changed one CSS rule on 17 October | F only. Backend needs go to F as a request. Order: B6, then C3, then C4 |
| `views/dashboard.py`, `views/performance.py` | F owns the layout; B wired the fingerprint and `TrainingJob` | F only during Phase B and C; B's C10 wiring after C3 |
| `predictor.py` | B (threading, loading), M (decision rule) | Only C9 needs both: M writes the rule first, then B the loading |
| `README.md` (root) | all three | F edits in Phase A (N18); M edits "Train the model" after B4; B edits setup after A6. Never two at once |
| `requirements.txt` | B | B only (A6) |
| `assets/memes/memes.json` | O (content), F (form), B (library) | Owner only during B5; schema change (C9) after B5 |
| `tests/test_pages.py`, `tests/test_status.py` | F, B | Same order as the code they test |

## Items not planned, and why

| Item | Why it is not in the plan |
|---|---|
| A different model family | Owner's choice (13 October); ML says "bring numbers". No evidence today that it would help more than data |
| A 50-epoch training cap | Measured on 17 October and declined by the owner (ML handoff) |
| Engineered hand-shape features | Measured on 17 October: lower accuracy (`RESULTS_AND_DATA.md` section 4). Worth another look only after B3 |
| Persisting recent detections | Privacy rule; only with OD-3 and a privacy page update |
