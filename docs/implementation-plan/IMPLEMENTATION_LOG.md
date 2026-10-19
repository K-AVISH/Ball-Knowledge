# Implementation log, 18 October 2026

What was built from `ROADMAP.md` after the owner's go-ahead on 18 October ("proceed with the
implementation stage ... implement all of the 3 departments together"), in one session working
for all three departments. The strategist prompt limited the strategist to planning; the owner's
message lifted that for this pass. Every rule in the prompt's section 4 still applied.

Owner's answers that this pass relied on: `OWNER_DECISIONS.md`, "Answers given on 18 October".

## 1. What was done

| Roadmap item | Department | Change | Files | Commit |
|---|---|---|---|---|
| B1 | Owner | Webcam steps with the 17 October model: owner reports all work | records in root `README.md`, backend and frontend READMEs | `2a42316` |
| B2 / OD-1 | ML | Threshold stays 0.70 (no relaxed-hand meme in B1); nothing to change | none | |
| A5 / OD-11 | Frontend | `New files fopr critiquing/`, `old files for critiquing/`, `Claude outputs/` moved into `to be deleted/`; links in the backend and ML READMEs now point to `docs/implementation-plan/` | backend and ML READMEs | `e315fb2` |
| A1 / OD-8 | Backend | Local git, no remote. Ignored: `.venv`, caches, the raw video folders, `docs/screenshots/`, `models/mediapipe/`, `*.zip`, `to be deleted/`, lock files. Tag `baseline-2026-10-17` | `.gitignore` | `e315fb2` |
| A2 rest (N14) | Backend | `config.py` comments for `TOP_PREDICTIONS` and frame dropping | `config.py` | `2a42316` |
| A3 rest (N23) | Frontend | Browser checklist uses the current state names | `docs/frontend-handoff/README.md` | `2a42316` |
| B5 (titles only) | Owner content | The owner's four meme titles written with `dataset_manager.py`; ratings and descriptions left empty | `assets/memes/memes.json` | `6f0d2bf` |
| A6 (N3, N4, N22) | Backend | Every direct dependency pinned to the tested version, Pillow added; the project `.venv` now has one OpenCV (`opencv-python-headless` removed, contrib reinstalled from the same 5.0.0.93 wheel) | `requirements.txt` | `255363b` |
| C2 (N10) | Backend | `staleness()` also reports changed augmentation settings or `GD_L2_OPTIONS`, when the report records them | `train_model.py`, `tests/test_status.py` | `255363b` |
| B6 (N5, OD-5) | Frontend | Alt text on every meme picture is "Meme: <title>" or "Meme"; the no-names test now includes alt text | `ui.py` (`meme_alt`), `tests/test_status.py` | `255363b` |
| C3 part (N15, OD-10d) | Frontend | Missing-hand-model hint says the camera picks the model up by itself | `ui.py`, `tests/test_status.py` | `255363b` |
| Docs | all | Backend ARCHITECTURE and README, frontend ARCHITECTURE and DESIGN_SYSTEM describe the changes | | `255363b` |

## 2. Not done, and why

| Item | Why |
|---|---|
| OD-10 b and c (augmentation line, classes-tile note) | Not approved by the owner on 18 October |
| B3, B4, B7, C1, C7, C8, C9 | Need the owner's next recordings (OD-7) first |
| B5 ratings and descriptions | The owner's content; never written for them |
| C4 screen-reader announcement | Needs a VoiceOver test, which this session cannot run; the alt text it builds on is done |
| C5 Safari check | Needs Safari; the session's browser is Chromium-based |
| C6 memes folder override | Not needed for this pass; testing used read-only pages |
| C10, C11, Phase D | Owner said no (OD-15 recommendation) or not decided (OD-3, OD-6) |
| A8 one package | The git tag replaces the zips; the three zips are left in the project root (ignored by git) for the owner to move or delete |

## 3. Checks (18 October, 09:52 to 10:00)

| Check | Result | How |
|---|---|---|
| Test suite, project `.venv` after the OpenCV clean-up | **417 passed** in 73 s (413 before, plus 4 new: settings staleness, older reports not flagged, alt text, camera hint) | `.venv/bin/python -m pytest -q` |
| Test suite, fresh environment from the pinned `requirements.txt` | **417 passed** in 108 s; `pip check`: no broken requirements; one OpenCV only | new venv in the scratchpad, `pip install -r requirements.txt` |
| Project `.venv` versions | Match every pin; `cv2` 5.0.0 with contrib modules; MediaPipe 1.1.0 imports | `pip freeze`, `python -c "import cv2, mediapipe"` |
| Live model still current | `staleness()` returns nothing for the live report with the new settings check | one-line check against `models/training_report.json` |
| Retrain on a scratch copy | 34.62 s; model SHA-256 `1e5813fc...`, the same as the live model; report identical apart from `trained_at` | `train_model.py` with `BALLKNOWLEDGE_DATA_DIR` and `BALLKNOWLEDGE_MODEL_DIR` |
| Clip replay | **A wrong gesture was shown in 0 of 16 clips**; per-gesture shares identical to 17 October | `check_pipeline.py` on scratch copies |
| Browser, Streamlit on port 8502 with scratch data and model | Dashboard: Camera off state, model Loaded, no retrain notice. Memes: all four titles Set, preview shows "Stressed Higuruma", image alt text "Meme: Stressed Higuruma". Model performance: 97.1%, 0.0747, 0.972, 16; no "gradient" in the page text. Data collector: five gestures listed. No Python errors on those four pages; Privacy policy and Terms and conditions were opened later (10:12) with no errors and the expected "Before launch" banner. At 390 px: no sideways scroll on Memes or the dashboard. Console: only the six known 404s for `/<page>/_stcore/health` from opening page addresses directly | built-in browser |
| Real files | `data/samples.csv` and the model unchanged (SHA-256 `d4e05a87...`, `1e5813fc...`); `memes.json` changed only by the four titles | `git diff`, `shasum` |

Not checked in this pass: the dashboard with a gesture held (needs a camera; the HTML is covered by
`tests/test_status.py` and `tests/test_memes.py`, and the owner can see it on port 8501), Safari,
and a screen reader.
