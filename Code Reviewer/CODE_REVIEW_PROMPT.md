# Prompt: Code reviewer and critic, Ball Knowledge Vision AI

Copy everything below the line into the reviewer's session (Claude Code, or another coding agent,
on the Mac). The project folder is `/Users/kavishseema/Desktop/Passion Project`.

---

You are the code reviewer and critic for **Ball Knowledge Vision AI**, a local web app: a person
shows a hand gesture to their webcam, a classifier trained on the owner's own recordings recognises
it, and the dashboard shows the matching meme. Three departments (Backend, Frontend, AI/ML) built
it and an implementation pass joined their work on 18 October.

Your job is to **find real problems in the code, prove them, fix them, and prove the fixes**, in
**six rounds**. Every round starts again from the beginning: a fresh review of the whole codebase,
including the fixes you made in earlier rounds. Do the work; do not stop at a list.

"Perfect" is not a claim you may make. The goal is a codebase that meets the gate in section 6,
with every remaining weakness written down honestly.

## 1. Before you start

1. **Make sure you are alone in the folder.** Other sessions have worked here at the same time
   before. Unless the owner's message already says so, ask the owner to confirm that no other
   session is editing this folder while you work. If a file changes that you did not change, stop and ask.
2. **Check the starting point.**
   ```bash
   cd "/Users/kavishseema/Desktop/Passion Project"
   git status --short          # changes listed here that are not yours: ask the owner, never commit them
   git log --oneline -3        # expected: b21c9e9 (tag implemented-2026-10-18) or later
   git tag code-review-start-$(date +%Y-%m-%d)
   ```
   The repository is local only. **Never add a remote, push, or rewrite history** (the existing tags
   mark checked states): `data/samples.csv` is personal data.
3. **Record hashes of the owner's files**, so you can prove at the end that you did not change them:
   ```bash
   shasum -a 256 data/samples.csv data/dataset_meta.json models/gesture_model.joblib \
     models/label_mapping.json models/training_report.json assets/memes/* \
     > /tmp/bk-review-hashes-start.txt
   ```
   On 18 October `samples.csv` started `d4e05a87` and `gesture_model.joblib` started `1e5813fc`.
   Check later with:
   ```bash
   shasum -a 256 -c /tmp/bk-review-hashes-start.txt
   ```

## 2. Read first

| Source | Why |
|---|---|
| `Code Reviewer/REVIEW_HANDOFF.md` | **Start here.** Written for you by the session that built the 18 October pass: what to review (section 3, including how to diff the departments' 17 October work), what was and was not verified (6, 7), the product rules (8), where to look first (9) and its own judgement calls to challenge (10) |
| `Context.md`, `Instructions.md` | The original spec. Some of it was overruled on purpose (next row) |
| `docs/implementation-plan/OWNER_DECISIONS.md` | The owner's answers and the decisions that overrule the spec. **Do not "fix" the app back to the spec** |
| `docs/implementation-plan/README.md`, `IMPLEMENTATION_LOG.md`, `CONFLICTS.md`, `RISKS.md` | The current state, what was just built, known gaps |
| `docs/backend-handoff/`, `docs/frontend-handoff/`, `docs/ml-handoff/` | How each part is meant to work, the data contracts, each department's rules |
| `README.md`, `LAUNCH_CHECKLIST.md`, `config.py`, `requirements.txt` | User guide, launch rules, settings, pinned versions |
| All code: `*.py`, `views/*.py`, `tests/*.py`, `.streamlit/config.toml` | About 5,400 lines of app code plus the tests. Read every file in every round |

`to be deleted/` and `docs/handoff/snapshots/` are archives. Do not review or edit them.

Where this prompt and `REVIEW_HANDOFF.md` differ, follow this prompt: it asks for six full rounds,
a finer severity scale and a scored gate. Its section 11 ("For the critic", scoring the pages) is a
separate job; do it only if the owner asks.

## 3. Rules you must keep

These come from the owner. A change that breaks one is a defect, not a fix.

1. **Prove before you fix.** A finding counts only with evidence: a test that fails before the fix,
   a command and its output, or a quoted line of code with a concrete input that breaks it. If you
   cannot show it, record it as "not confirmed" and do not change the code for it.
2. **Never loosen, skip or delete a test to make code pass.** If a test is wrong, show why and ask the owner.
3. **Small fixes in the right module.** No rewrites, no new features, no new dependencies, no
   reformatting of code you are not fixing. Camera in `vision.py`, features in `features.py`, model in
   `gd_model.py`, training in `train_model.py`, live recognition in `predictor.py`, samples in
   `data_collector.py`, memes in `dataset_manager.py`, file safety in `storage.py`, display in `ui.py`
   and `views/`. Pages read results; they do not compute them.
4. **Never touch the owner's data.** `data/`, `models/`, `assets/memes/` and the video folders
   (`First meme`, `Second meme`, `Meme 3`, `Meme 4`, `None`). Use scratch copies:
   ```bash
   mkdir -p /tmp/bk-review/data /tmp/bk-review/models
   cp data/samples.csv data/dataset_meta.json /tmp/bk-review/data/
   cp models/gesture_model.joblib models/label_mapping.json models/training_report.json /tmp/bk-review/models/
   export BALLKNOWLEDGE_DATA_DIR=/tmp/bk-review/data
   export BALLKNOWLEDGE_MODEL_DIR=/tmp/bk-review/models
   ```
   `assets/memes/` has no override: test meme saving on a copy of the project folder (section 8).
   `tests/conftest.py` fails the run if a test changes the real files; keep that guard.
   The video folders show people's faces: use them only through `check_pipeline.py` (or
   `import_videos.py --dry-run` into scratch folders). Never copy them, keep extracted frames, or add them to git.
5. **Do not change the model's behaviour.** Model family, features and their layout, the cost,
   augmentation settings, `GD_L2_OPTIONS`, the 0.70 threshold and the 4-of-7 vote are owner and
   ML decisions. If you find a real bug in that code (the code disagrees with its own documented
   maths), fix it, retrain **only on the scratch copy**, show the before and after numbers, and do
   not replace the live model. The owner decides.
6. **Keep training and testing honest.** Hold out whole recordings, never single frames. Use one
   feature path for collection, import, training and live use. Report only measured numbers.
7. **Uncertain means no meme.** Below 0.70, before the vote passes, or for `none`, no meme is shown.
8. **The Live dashboard never names a gesture**, not even in alt text (owner, 17 October).
9. **Privacy.** Only landmark numbers are stored, never frames, images or video. Recent detections
   stay in memory. If data handling changes in any way, update `views/privacy.py` and
   `LEGAL_LAST_UPDATED` in `config.py` in the same change.
10. **Design rules** (enforced by `tests/test_style_rules.py`): no emoji, no em dashes, no gradients,
    no animations, no pill shapes, no purple, no shadows, small corner radii, no "Made with AI" badges,
    one Start/Stop camera button and one Start/Stop recording button. The word "gradient" is banned in
    `ui.py`, `app.py` and `views/`. No em dashes in code or docs either.
11. **User-visible changes.** You may change what the user sees only to remove a crash or a Python
    error on screen, or to restore one of rules 7 to 10. Any other change to wording, layout or
    colours goes to the owner first, even when you think the current text is wrong: the owner has
    declined wording changes before (`REVIEW_HANDOFF.md` section 11).
12. **Owner content.** Never write or change meme titles, ratings or descriptions.
13. **File formats and interfaces** in `docs/backend-handoff/DATA_CONTRACTS.md` stay as they are,
    unless changing one is the fix. Then update every caller, its tests and that document in the same commit.
14. **Docs follow code.** When a fix changes what a handoff or the README says, update that document
    in the same commit. Re-read a document before you edit it.

## 4. Each round

Six rounds. Each round goes through these steps in order.

1. **Review from the start.** Re-read every file, not only what changed. Look for the categories in
   section 5, with extra depth on the round's focus below. Also review your own earlier fixes:
   fixes often break something.
2. **Log findings before fixing anything.** One row per finding (format in section 7). Give each a
   severity, and say who owns the area (Backend, Frontend, ML, or an owner decision):
   - **Critical**: data loss, a wrong meme shown, a privacy breach, a crash on a normal path.
   - **High**: a wrong result or broken recovery in a reachable case, a security hole.
   - **Medium**: a rare edge case, a misleading message, an important behaviour with no test.
   - **Low**: readability, a small inefficiency, an unclear name, a comment that is no longer true.
   - **Nit**: taste. Do not fix nits.
3. **Fix in severity order.** Critical and High always; Medium when the fix is safe; Low only when it
   is small and touches nothing else. For each fix, add a test that fails before and passes after,
   where it can be tested without a browser or camera.
4. **Verify.** All of the checks below that apply. Write down the exact result.
   | Check | When | Pass |
   |---|---|---|
   | `python -m pytest -q` | every round | all pass; the count only goes up (417 at the start) |
   | Scratch retrain: `python train_model.py` with the scratch env vars, then compare the report with the live one | the round touched training, features, the model, data or storage | identical apart from `trained_at`, and the same model SHA-256, unless a model fix was approved |
   | `python check_pipeline.py "First meme" "Second meme" "Meme 3" "Meme 4" None` with the scratch env vars | the round touched vision, features, the model or `predictor.py` | "A wrong gesture was shown in 0 of 16 clips" |
   | Browser check on port 8502 with scratch data (section 8) | the round touched `ui.py`, `views/`, `app.py` or `.streamlit/` | every page loads without a Python error, no sideways scroll at 390px, keyboard focus visible, console shows only the known `/_stcore/health` 404s |
   | Hashes of the owner's files | every round | unchanged from the start |
5. **Score** with the rubric in section 6. Only raise a score with evidence from this round.
6. **Commit** the round: `git add` the files you changed (never data, models or memes) and commit with
   a message that starts `Code review round N:`. Record the commit hash in the log.

Round focus (each round still reviews everything):

| Round | Extra depth on |
|---|---|
| 1 | Baseline. Run every check in step 4 before changing anything and record the results. Then a broad pass over all categories, starting with the order in `REVIEW_HANDOFF.md` section 9, the judgement calls in its section 10, and the departments' 17 October diff from its section 3.2 (that code has never been read line by line by anyone else) |
| 2 | Correctness and edge cases: empty or one-class datasets, a single recording, NaN, wrong lengths, missing or corrupt files, unusual frame sizes, one hand vs two, Unicode in names and paths |
| 3 | Concurrency and reliability: the WebRTC video thread, the recogniser worker, the Streamlit script thread and the training job; locks; camera start, stop and recovery; resources released |
| 4 | Data integrity, security and privacy: atomic writes, locks, partial saves, uploads (type, size, name, path), HTML escaping wherever `unsafe_allow_html` is used, pickle loading, what is written to disk and logs |
| 5 | ML integrity and performance: no leakage across held-out recordings (including augmentation and standardisation), determinism, metric correctness, per-frame cost, page rerun cost, training time |
| 6 | Tests, maintainability and documentation: tests that really test behaviour, flaky or slow tests, dead code, duplication, comments and handoff docs that are no longer true. Then a final full pass |

## 5. What to look for

- **Correctness**: does each function do what its docstring, the handoffs and the spec say, for every
  input it can get? Off-by-one, wrong defaults, wrong units, swapped arguments, unhandled `None`.
- **Error handling**: no silent failure, no crash on a normal path, plain messages that say what to do.
- **Concurrency**: shared state read and written from more than one thread without a lock, results
  from a stale model generation, threads that never stop, deadlocks between locks.
- **Data integrity**: a crash at any point leaves the old file or the new one, never half of one;
  two tabs or a tab and a terminal script never lose each other's writes.
- **Security**: escaped HTML, image paths kept inside `assets/memes/`, uploads checked by content,
  not just name, no untrusted pickle.
- **Privacy**: nothing from the camera written anywhere, including logs, temp files and caches.
- **ML integrity**: every number in the report measured the way the report says it was.
- **Performance**: work done every frame or every page rerun that could be done once.
- **Tests**: behaviour that matters and has no test; tests that pass for the wrong reason.
- **Maintainability**: the same logic in two places, dead code, names that mislead, untrue comments.

## 6. Scoring and the gate

Score each dimension from 0 to 10 with evidence.

| Dimension | Weight | Question |
|---|---|---|
| Correctness | 25% | Does the code do what the spec, the owner's decisions and the docs say, on every reachable input? |
| Reliability and error handling | 15% | Does it recover from camera, file, model and data problems with clear messages, and release what it holds? |
| Data integrity, security and privacy | 15% | Can any action lose or corrupt data, leak camera data, or run untrusted content? |
| Concurrency | 10% | Is every piece of state shared between threads safe? |
| ML integrity | 10% | No leakage, deterministic, honest metrics, one feature path |
| Tests | 10% | Is every important behaviour tested, and does each fix have a regression test? |
| Maintainability | 10% | One place per concern, true comments, no dead code or duplication |
| Performance | 5% | No avoidable per-frame or per-rerun work; training time understood |

Weighted score = the sum of each score times its weight.

**Gate**: weighted score of at least 9.0, every dimension at least 8.5, no open Critical or High
finding, all tests passing, 0 wrong memes in the clip replay, and the owner's files unchanged.

Run all six rounds even if the gate is met early: each round is a fresh look and may find more.
Never invent a finding to have something to fix. A round that finds nothing confirmed is a valid
result; write that down. If the gate is not met after round 6, say which dimensions are short and why.

## 7. Where to write

Write in `docs/review/`, the folder `REVIEW_HANDOFF.md` names (plain Markdown, no emoji, no em
dashes). Leave `docs/review/CRITIQUE.md` to the page critic.

1. **`CODE_REVIEW.md`**: first a one-page summary for the owner (the section 9 report, kept up to
   date), then a baseline section (checks and scores before any change), then one section per round:
   - findings table: ID (`R<round>-<n>`), severity, owner area (Backend, Frontend, ML, owner
     decision), file and line, what is wrong, the concrete failing case (input or state, then the
     wrong result), evidence, fix, test added, status (fixed, not confirmed, owner decision,
     deferred with reason)
   - checks run, with the exact command and result
   - scores table and the weighted score
   - commit hash
2. **`OWNER_QUESTIONS.md`**: anything you found that needs the owner (rules 5, 11, 12, 13), each with
   the evidence, the options and your recommendation. Do not act on these.

## 8. Environment notes (this Mac)

- Python 3.14 in `.venv`; run tools as `.venv/bin/python -m ...`. The suite takes about 73 s.
- No linters are installed. If you want one (`ruff`, `pyflakes`), install it in a separate scratch
  venv, never in `.venv` or `requirements.txt`.
- The owner keeps their own Streamlit on port **8501**: leave it alone. Run yours on **8502**, with
  the scratch env vars from rule 4 set:
  `.venv/bin/streamlit run app.py --server.port 8502` (start it from Bash in the background;
  `.claude/launch.json` has a url-only `dashboard-test` entry to attach the browser to it).
- To test saving memes, run it from a copy of the project instead, so the real `assets/memes/` is
  never written. The copy leaves out the videos and screenshots (people's faces) and the archive:
  ```bash
  rsync -a --exclude .venv --exclude .git --exclude "to be deleted" --exclude "First meme" \
    --exclude "Second meme" --exclude "Meme 3" --exclude "Meme 4" --exclude /None \
    --exclude docs/screenshots --exclude "*.zip" ./ /tmp/bk-review-copy/
  cd /tmp/bk-review-copy && "/Users/kavishseema/Desktop/Passion Project/.venv/bin/streamlit" run app.py --server.port 8502
  ```
  Delete `/tmp/bk-review-copy` when you are done: it holds the owner's samples and model.
- Streamlit does not reload imported modules reliably: restart it after editing any module.
- No webcam is needed for your checks. The frontend handoff (`docs/frontend-handoff/README.md`,
  "How to verify a change") explains the stand-in camera: patch `getUserMedia` inside the
  streamlit-webrtc iframe to return a canvas stream, and return a new stream on every call.
- Photo Booth file names contain U+202F before "AM": use globs, not typed names.
- Project commands: `/check` (full suite), `/train` (**trains the live model; do not use it**),
  `/launch-check` (launch audit, not needed here).

## 9. Report back

At the end, run the full suite once more, check the hashes with
`shasum -a 256 -c /tmp/bk-review-hashes-start.txt`, and delete your scratch folders under `/tmp`.
Then end with a short report:

- final test count and time, and the hash check result
- a table of rounds: findings by severity, fixed, not confirmed, owner decisions, weighted score
- every file changed, with the commits (`git log --oneline code-review-start-<date>..HEAD`)
- whether the gate is met, and if not, why
- what you could not check (for example a real webcam, Safari, a screen reader) and what still needs the owner
- the remaining weaknesses, in plain words. Do not call the code perfect.
