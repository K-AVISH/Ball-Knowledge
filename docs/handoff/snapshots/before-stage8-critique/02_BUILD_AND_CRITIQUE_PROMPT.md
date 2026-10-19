# Build and critique prompt: Ball Knowledge Vision AI, Stage 5 onwards

Use this with `01_PROJECT_CONTEXT.md`, `03_REQUIREMENTS_AND_CHECKLIST.md` and `04_HANDOFF.md`. Read all three before changing code.

## Your role

You are the engineer for this project. Build the next unfinished stage, then critique the site and improve it. Do not stop at a plan.

## Ground rules

1. **Do not claim a model is trained, accurate or working** unless a real training run on real recordings has finished and produced the report. Synthetic data proves the code, not the gestures. Say which one a result is.
2. **Do not invent numbers.** Every figure on screen must come from the training report, the dataset or the camera. Show "n/a" or a dash when there is no value. Never show 0% or 100% as a stand-in.
3. **Do not add features outside the brief.** Stage 5 is live recognition. Stage 6 is the metadata manager and meme display. Stage 7 is smoothing, history and statistics. Stage 8 is end-to-end testing. Build in that order.
4. **Keep the design rules.** Run `tests/test_style_rules.py` after every change. Never loosen a test to make code pass.
5. **Keep camera, ML, data and UI separate** (`vision.py`, `train_model.py`, `dataset_manager` or equivalent, `views/`). The UI reads results. It does not compute them.
6. **Preserve the privacy promise.** Store landmark numbers only. Never store frames, images or video. If that changes, update `views/privacy.py` and `views/terms.py` in the same change.
7. **Do not retrain during live recognition.** Load the saved model once.

## Stage 5: live recognition (next)

Implement, in `predictor.py`:

- Load `models/gesture_model.joblib` and `models/label_mapping.json` once, with clear errors if either is missing or does not match the feature mode.
- Build the same feature vector the collector used (`features.py`), so training and prediction match.
- Apply the confidence threshold and report "Unrecognised" below it.
- Return the top predictions for the recognition panel.

Connect it to `views/dashboard.py` and `vision.py`. Keep the camera loop responsive. Do not block the video thread on model inference if it is slow.

## Critique loop (repeat for each stage)

Use this rubric. The same weights are in the "Rubric" section of `docs/ui-critique-log.md`.

1. **Data truth (25%).** Are all numbers measured, labelled and sourced? Is the model called "uncalibrated" and "estimated" where that applies?
2. **Recognition and data state (20%).** Do stale, missing, unrecognised and not-trained states each show distinctly?
3. **Flow and action clarity (15%).** Can a new user see what to do next?
4. **Visual hierarchy and brand (15%).** Is the most important information first, and is it consistent?
5. **Interaction reliability (10%).** Do Start, Stop, Record and Train behave, and recover from errors?
6. **Accessibility and responsive (10%).** Headings, captions, focus, keyboard, and no horizontal overflow at 390px.
7. **Maintainability (5%).** Shared logic in one place, tests for it, docs updated.

For each round, write the critique with evidence (file, line or render), make the fixes, run the tests, render the pages, and record the scores in `docs/ui-critique-log.md`. Report the defects you could not verify.

## Verification you must run

- Full test suite, from the project root with the venv active: `python -m pytest -q`. Report pass and fail counts. Quote each failure.
- Render check: run `streamlit run app.py` and open each page at 1280px and 390px. Note any horizontal scrolling.
- Camera check (manual, on the Mac): start the camera, confirm the landmarks appear, and confirm "Camera connected" shows.
- Recording check (manual): record one gesture, confirm the count rises and the file grows.
- Training check (manual): train on real recordings, confirm the report and confusion matrix appear.

## What not to do

- Do not present a validation or synthetic result as a test result.
- Do not hard-code a gesture name, a meme, or a rating.
- Do not use em dashes or emoji in code or UI text.
- Do not add a second camera control, a second record button, or a hidden fallback that shows fake results when the camera fails.

## Output

Update `docs/ui-critique-log.md` (one section per round), `docs/handoff/03_REQUIREMENTS_AND_CHECKLIST.md` (tick only what you verified) and `docs/handoff/04_HANDOFF.md` (what changed, how to run it, what is still open).
