# Implementation plan: Ball Knowledge Vision AI

The three departments' 17 October handoffs joined into one checked picture and one plan
(snapshot 17 October, 16:29 to 16:37), then built on 18 October after the owner's go-ahead.
What was built and how it was checked: [IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md).

## Where things stand (18 October, 10:00)

1. The site works as one unit: **417 tests pass** in the project `.venv` and in a fresh install from the pinned `requirements.txt`, and replaying all 16 clips through the live path shows **0 wrong memes**.
2. You ran the webcam steps with the current model and reported that all work, so the 0.70 threshold stays. The live model is unchanged and still exactly reproducible (byte-identical scratch retrain, 34.6 s).
3. Phase A is done: local git (tag `baseline-2026-10-17`), every document fix, old critique folders in `to be deleted/`, exact package versions, and one OpenCV in `.venv`.
4. Your four meme titles are in and show under the meter; the dashboard's hidden image text now says the meme title, never a gesture name; "Retrain needed" also appears if training settings change.
5. What remains needs you first: new recordings (OD-7), your ratings and descriptions, and later decisions on per-gesture thresholds and hosting.

## Next three actions

| Who | 1 | 2 | 3 |
|---|---|---|---|
| **You (owner)** | Open the site (port 8501) and hold each gesture: the meme now has its title under the meter | Write ratings and descriptions on the Memes page when you want them shown | Record the next data with "Recorded by" filled in (OD-7) |
| **Backend** | After your new recordings: time training at the new size and decide on worker processes (B7, then C1) | Add a memes-folder override for safer testing (C6) | Hosting work only after you decide (Phase D) |
| **Frontend** | Safari check on scratch data (C5) | Screen-reader announcement of a new meme, tested with VoiceOver (C4) | Hosting work only after you decide (Phase D) |
| **AI/ML** | Write the data brief for your next recordings (OD-7) | After them: retrain on a scratch copy and compare with today's numbers before anything goes live (B4) | Then nested selection and the face-position features (C8, C7) |

## Decisions still open

Details, options and evidence: [OWNER_DECISIONS.md](OWNER_DECISIONS.md). Answers already given are
at the top of that file.

| ID | Decision | Recommendation |
|---|---|---|
| OD-7 | What to record next | A 3rd first_meme recording, longer second_meme holds, more meme_3, meme_4 by you, `none` in a new room, at least one webcam recording each |
| OD-12 | Confirm decisions already made, including Streamlit over Figma | Confirm |
| OD-2, OD-3, OD-6 | Per-gesture thresholds, a Prediction History page, hosting | Later, no, and stay local for now |

## The files

| File | What it holds |
|---|---|
| [Code Reviewer/REVIEW_HANDOFF.md](../../Code%20Reviewer/REVIEW_HANDOFF.md) | Handoff for the code reviewer and the critic: what to review, how to run it, what is and is not verified, the rules, the judgement calls to challenge |
| [IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md) | What was built on 18 October, by department, with every check and its result |
| [SYSTEM_STATE.md](SYSTEM_STATE.md) | The verified system as of 17 October: camera-to-meme flow with owners, every interface between departments, measured numbers |
| [CONFLICTS.md](CONFLICTS.md) | 29 disagreements and gaps (6 known, 23 new), each with the fix owner and the kind of fix |
| [ROADMAP.md](ROADMAP.md) | Phases A to D with done conditions and checks, the dependency view, what can run in parallel, and the order for shared files |
| [OWNER_DECISIONS.md](OWNER_DECISIONS.md) | Your answers so far and the decisions still open |
| [RISKS.md](RISKS.md) | 17 risks with likelihood, impact, early warning signs and mitigations |
