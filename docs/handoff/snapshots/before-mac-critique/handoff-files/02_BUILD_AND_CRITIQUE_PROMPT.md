# Build and critique prompt: Ball Knowledge Vision AI, after Stage 8

Give this file to the AI together with `01_PROJECT_CONTEXT.md`, `03_REQUIREMENTS_AND_CHECKLIST.md` and `04_HANDOFF.md`. Run it in Claude Code (or another coding agent) on the Mac, from the project folder `/Users/kavishseema/Desktop/Passion Project`.

---

## Your role

You are the engineer on this project. All eight stages are built. Your job is to verify the app on this Mac, fix what fails, then critique the site and improve it in six rounds. Do the work; do not stop at a plan. Work through the parts below in order and finish each before starting the next.

Read `01_PROJECT_CONTEXT.md`, `03_REQUIREMENTS_AND_CHECKLIST.md` and `04_HANDOFF.md` first. Then read `README.md` and `docs/ui-critique-log.md`.

## Ground rules

1. **Never claim something works unless you ran it.** For every result, say how it was checked: automated test, browser run, the user's webcam, or not run.
2. **Never invent numbers.** Every figure on screen comes from the camera, `data/samples.csv` or `models/training_report.json`. Show "n/a" when there is none. Never fill in a meme title, rating or description; those belong to the user.
3. **Never loosen or delete a test to make code pass.** If a test is wrong, say why and ask the user.
4. **Keep the design rules** in `tests/test_style_rules.py`: no emoji, no em dashes, no gradients, no animation, no pill shapes, no purple, small corner radii, one camera button, one record button.
5. **Keep responsibilities separate**: camera in `vision.py`, model in `predictor.py` and `train_model.py`, data in `data_collector.py`, memes in `dataset_manager.py`, display in `ui.py` and `views/`. Pages read results; they do not compute them.
6. **Keep the privacy promise.** Store landmark numbers only, never frames, images or video from the camera. If anything about data handling changes, update `views/privacy.py` and `LEGAL_LAST_UPDATED` in `config.py` in the same change.
7. **Do not touch the user's data without asking**: `data/`, `models/`, `assets/memes/`, and the gesture folders (`First meme`, `Second meme`, `Meme 3`, `Meme 4`, `None`). For experiments, set `BALLKNOWLEDGE_DATA_DIR` and `BALLKNOWLEDGE_MODEL_DIR` to a scratch folder.
8. **Do not add features outside the brief** (`Context.md`, `Instructions.md`). Optional extras from the brief need the user's yes first.

## Part 1: automated checks

Run from the project folder:

```bash
source .venv/bin/activate
python -m pytest -q
```

Expected: 312 passed and nothing failed. Five of these (4 legal page tests using Streamlit's AppTest and 1 `capsys` test) have only ever run on this Mac, not in the review environment.

If anything fails: quote the failure, find the cause, fix the code (not the test), and run the full suite again. Record the final counts.

Then run the clip replay:

```bash
python check_pipeline.py "First meme" "Second meme" "Meme 3" "Meme 4" None
```

Expected: "A wrong gesture was shown in 0 of 16 clips" (the duplicate copy in First meme is checked once), and per-gesture results close to the table in `04_HANDOFF.md`. If any clip shows a wrong gesture, stop Part 1 and report the clip, the gesture shown and how long it was shown.

## Part 2: run the app and check every page

Start the app and open it in a browser:

```bash
streamlit run app.py
```

Open http://localhost:8501. Check each page at a desktop width (about 1280px) and at a phone width (390px):

| Page | Pass when |
|---|---|
| Live dashboard | No red error box. Camera card, Recognition, Meme result, then a row with Live statistics and Recent detections. A blue notice names the gestures without a rating or description |
| Data collector | Dataset list shows 5 gestures with the combined hints (first_meme: "Needs 42 more samples and 1 more separate recording") and the bar legend |
| Model performance | Held-out accuracy 97.4%. Gesture names match the dashboard ("Meme 3", "No gesture"). Recordings named by time, for example "14 Oct 11:35 (c79027)" |
| Memes | The table, the form and the preview panel. Nothing is saved until Save meme is pressed |
| Privacy policy | No mention of a Google STUN server. A "Meme images" section |

At 390px no page may scroll sideways. Tables may scroll inside their own box. Check the browser console for errors and list any you find.

**Memes page in real Streamlit** (this has never been run): use a scratch copy so the user's memes are not changed. Copy the project to a scratch folder, run `streamlit run app.py --server.port 8502` from that copy, and check:

1. Save a title, a rating of "8/10" and a description for one gesture. Expect a green "Saved" message, Set in the table, and the preview showing them. `assets/memes/memes.json` in the scratch copy contains them.
2. Upload a PNG. Expect it in the preview and copied to `assets/memes/<gesture>.png`.
3. Upload a text file renamed to `.png`. Expect a red "Nothing was saved" message naming the file, and no change to `memes.json`.
4. Type text in one gesture's form without saving, switch to another gesture. The other gesture's form must not show that text.
5. Open the Live dashboard in the scratch copy: the notice no longer lists the gesture you completed.

Fix anything that fails and add a test for it where it can be tested without a browser.

## Part 3: the user's webcam run

Only the user can do this, because it needs a person in front of the camera. Ask the user to do the nine steps in `README.md`, "Test the whole pipeline", "With your webcam", and to tell you, for each step, pass or what happened instead. Record the answers in `03_REQUIREMENTS_AND_CHECKLIST.md`.

If a gesture often stays on Unrecognised live, the fix is more data, not a lower threshold: ask the user to record one or two recordings of it on the Data collector page, then train again on the Model performance page. Do not change `DEFAULT_CONFIDENCE_THRESHOLD` without showing the user the cutoff table and getting a yes.

## Part 4: six critique-and-improve rounds

Do six rounds. In each round:

1. **Critique.** Look at the running app (all pages, desktop and 390px, and the dashboard states you can reach: camera off, no hand, checking, unrecognised, no gesture, recognised). List defects with evidence: page, state, what you saw, and the file and line responsible.
2. **Fix** the most important defects first. Keep changes small and in the right module.
3. **Test.** Run `python -m pytest -q`. Add a test for each fix that can be tested without a browser.
4. **Look again** at the pages you changed, at both widths.
5. **Score** with the rubric below and add a section for the round to `docs/ui-critique-log.md`: defects, fixes, evidence, scores.

Rubric (weights add to 100%):

| Dimension | Weight | Question |
|---|---|---|
| Data truth | 25% | Is every number measured, labelled and sourced, and every statement on the site true? |
| Recognition and data state | 20% | Does each state show distinctly and the same way on every page? |
| Flow and action clarity | 15% | Can the user see what to do next without the terminal? |
| Visual hierarchy and brand | 15% | Is the result (gesture and meme) first and the layout balanced, dark and football-like? |
| Interaction reliability | 10% | Do Start, Stop, Record, Train and Save behave, and recover from errors? |
| Accessibility and responsive | 10% | Headings in order, captions, contrast at least 4.5:1, keyboard focus visible, no sideways scroll at 390px |
| Maintainability | 5% | Shared logic in one place, tests, docs updated |

Weighted score = the sum of each score times its weight. The release gate is a weighted score of at least 9.0 with every dimension at least 8.5. Do not raise a score without evidence from that round. If the gate is not met after six rounds, say which dimensions are short and why.

Start from the open defects in `docs/ui-critique-log.md` ("Unresolved") and section I of `03_REQUIREMENTS_AND_CHECKLIST.md`. A keyboard-only pass (Tab through each page; every control reachable and its focus visible) counts as evidence for Accessibility.

## Part 5: wrap up

1. Run `python -m pytest -q` one last time and record the counts.
2. Update `03_REQUIREMENTS_AND_CHECKLIST.md`: tick only what you verified in this session, and say how.
3. Update `04_HANDOFF.md`: what changed, how to run it, test counts, what is still open. Replace outdated sections instead of adding dated updates on top.
4. Update `01_PROJECT_CONTEXT.md` section 2 if a stage's verification changed.
5. Update `README.md` for anything a user would do differently.
6. Before changing files, save copies of the originals in `docs/handoff/snapshots/<short-name>/`.

## What not to do

- Do not present a held-out, synthetic or stand-in camera result as a webcam result.
- Do not hard-code a gesture name, meme, rating or description.
- Do not add a second camera control, a second record button, or a fallback that shows a meme when recognition fails.
- Do not delete or overwrite the user's recordings, model or memes.
- Do not use em dashes or emoji in code, UI text or docs.

## Report back to the user

End with a short report: test counts, what you ran and how, what changed (by file), the final round scores, and what still needs the user (webcam steps, memes to write, recordings to add).
