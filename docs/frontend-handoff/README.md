# Frontend handoff: Ball Knowledge Vision AI

Written 17 October 2026 for the frontend developer taking over the pages and styling.
Start here, then read the other files in this folder.

| File | What it covers |
|---|---|
| `README.md` (this file) | What the project is, current state, setup, how to verify, open work |
| `ARCHITECTURE.md` | How Streamlit renders the pages, live refresh, the camera widget, every page and shared UI helper |
| `DESIGN_SYSTEM.md` | Colours, type, components, every recognition state and its copy, the enforced design rules |
| `CHANGES_2026-10-17.md` | What changed after the zip: the memes-not-names dashboard and the refinements, with how they were checked |
| `Implementation Stratergist/IMPLEMENTATION_STRATEGIST_HANDOFFfrom Frontend.md` | State, decisions, risks and the suggested order of next steps, for planning. Not in this folder: it moved on 17 October to `Implementation Stratergist/` in the project root (the folder and file names are spelled that way on disk) |

## Context files to read (in this order)

| File | Why |
|---|---|
| `docs/frontend-handoff/*` | This handoff |
| `Context.md` | The original product spec. Section 6 describes the dashboard and pages |
| `README.md` (project root) | User-facing guide. Its "With your webcam" table is the manual test of every page |
| `docs/ui-critique-log.md` | Every UI decision so far, with the defect it fixed and the measured evidence. Read before changing layout |
| `LAUNCH_CHECKLIST.md` | Favicon, badges, legal pages, domain: what must be done before launch |
| `.streamlit/config.toml` | Theme colours, radius, upload limit |
| `config.py` | App title, refresh-related settings, legal page fields, meme image limits |
| `docs/backend-handoff/README.md` | The backend side, only for what the pages call |
| `Instructions.md` | The 8 build stages (the owner refers to stages by number) |

If you received `frontend-handoff-2026-10-17.zip`: it holds the code, tests, these files,
the training data, the trained model and the meme images, so every page shows real content.
It leaves out the MediaPipe models (run `python download_models.py --pose`) and the raw gesture
videos, which show people's faces. The test suite passes from the unzipped folder.

## 1. What the project is

A local web app. You show a hand gesture to your webcam, a classifier trained on your own
recordings recognises it, and the dashboard shows the matching meme with a "Ball Knowledge"
rating and description.

The frontend is **Streamlit 1.65.0** with **streamlit-webrtc 0.78.1** for the camera. There
is no JavaScript build, no React app and no API: each page is a Python script that Streamlit
reruns, and the styling is one CSS block in `ui.py` plus the theme in `.streamlit/config.toml`.
Most panels are HTML strings built in `ui.py` and rendered with `st.markdown(..., unsafe_allow_html=True)`.

| Layer | Files |
|---|---|
| Frontend (your area) | `app.py`, `ui.py`, `views/*.py`, `.streamlit/config.toml`, `assets/favicon.png` |
| Backend (call, do not rewrite) | `vision.py`, `predictor.py`, `data_collector.py`, `dataset_manager.py`, `train_model.py`, `config.py` |
| Data | `data/`, `models/`, `assets/memes/` |
| Tests | `tests/` (pytest, no webcam needed); UI tests are `test_pages.py`, `test_style_rules.py`, `test_display.py`, `test_status.py`, `test_memes.py` |

## 2. Current state (verified 17 October 2026)

- Six pages, all built: Live dashboard, Data collector, Model performance, Memes, Privacy policy, Terms and conditions.
- `python -m pytest -q`: **413 passed** (17 October, after the frontend, backend and ML work of the same day; Python 3.14.7, project `.venv`).
- Two critique passes on 14 October, the second in real Streamlit in Chrome with a stand-in
  camera. Final weighted score 9.07 of 10 (14 October, before the Meme panel), every dimension at
  least 8.8 (`docs/ui-critique-log.md`). The dashboard rebuilt on 17 October has not been scored.
- The owner checked the site and webcam on 14 October and reported they work. On 18 October,
  with the 17 October model, the owner ran the README "With your webcam" steps and reported
  that all of them work. `memes.json` was unchanged afterwards, so step 7's save was not made on
  the real file.
- Meme titles, ratings and descriptions are empty, so the dashboard shows nothing under the meme
  and its meter; only the Your memes table on the Memes page shows a grey "Not set" tag. That is
  correct. **The owner writes those texts. Never fill them in.**

## 3. Setup and run (macOS, Apple Silicon)

```bash
cd "/Users/kavishseema/Desktop/Passion Project"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python download_models.py --pose
streamlit run app.py --server.port 8502
```

Open http://localhost:8502 in Chrome. Notes:

- The app listens on this computer only (`server.address = "localhost"` in
  `.streamlit/config.toml`), so another device on the network cannot open it.
- The owner usually keeps their own Streamlit on port 8501. Use 8502 for your work.
- **Restart Streamlit after editing `ui.py` or any imported module.** Streamlit only reloads the
  page script reliably; changes to `ui.py` CSS otherwise look like they did nothing.
- `server.headless = true`, so the browser does not open by itself.
- The camera only works on `localhost` or HTTPS. Chrome is the tested browser; Safari is not.

## 4. How to verify a change

```bash
source .venv/bin/activate
python -m pytest -q
```

Then check in the browser, at 1280x900 and at 390px wide:

1. Every page loads with no Python error and no sideways scroll at 390px.
2. The dashboard states: Camera off, Waiting for video, No hand in view, Hold it steady,
   Unrecognised, No gesture, the meme (in view at 1280x900), and Stop camera clears the panels.
3. Keyboard: Tab reaches every control with a visible focus ring.
4. Run the "With your webcam" table in the root `README.md` for anything that touches the camera or the Memes form.

**Work on scratch data.** Recording, training and saving memes write real files. Point the app
at copies first:

```bash
export BALLKNOWLEDGE_DATA_DIR=/tmp/bk-scratch/data
export BALLKNOWLEDGE_MODEL_DIR=/tmp/bk-scratch/models
```

`assets/memes/` has no override, so test the Memes page on a copy of the whole project folder.

**Without a webcam:** the camera runs inside the streamlit-webrtc iframe. You can patch
`navigator.mediaDevices.getUserMedia` in that iframe to return `canvas.captureStream()` and draw
frames onto the canvas. Return a new stream on every call, because Stop camera ends the tracks.
This is how the 14 October critique was done.

## 5. Rules you must keep

These are the owner's standing rules. The mechanical ones are tests in `tests/test_style_rules.py`
and `tests/test_pages.py`, so breaking them fails the suite.

1. **No vibe-coded look.** No emoji, no em dashes, no gradients, no keyframe or scroll
   animations, no pill shapes (radius only 2, 4, 6, 8px or 50% for dots), no purple, violet,
   indigo or magenta, no box or text shadows, no custom cursors, no stock or AI-generated images.
2. **No fake numbers.** Every number on screen comes from measured data. A missing value shows
   `n/a`, never a placeholder. No invented reviews, counters or vague hero text.
3. **One control per action.** The camera is one Start camera / Stop camera button; recording is
   one Start recording / Stop recording button. Do not split them.
4. **Uncertain means no meme.** The meme only shows for a steady, recognised gesture. Every other
   state shows a distinct message instead of a guess.
5. **The word "gradient" may not appear** in `ui.py`, `app.py` or `views/`. Explain the model as
   "steps downhill" and "slope".
6. **No "Made with AI" or Streamlit badges.** The Deploy button, menu and footer are hidden in CSS.
7. **Escape data.** Anything from a file or the user (gesture names, meme text) goes through `ui.esc()` before it goes into HTML.
8. **Contrast and focus.** Text at least 4.5:1, green buttons use dark text (8.1:1), every control shows a focus ring.

Ask the owner before changing the layout order of the dashboard, any user-visible wording about
privacy or the model, or the colour scheme.

## 6. Open work and decisions

| # | Item | Notes |
|---|---|---|
| 1 | Screen reader announcement | A newly recognised gesture is not announced. A live region inside a panel that redraws twice a second could be read out repeatedly, so it needs testing with VoiceOver. No screen reader has been tested. |
| 2 | Safari | Never checked. Safari's WebRTC is stricter than Chrome's. |
| 3 | Webcam step-by-step record | Done 18 October by the owner's report (all steps work, current model). No per-step notes were written. |
| 4 | Training in the background | **Done 17 October.** Train model starts `train_model.TrainingJob` on a background thread; the page disables the button and shows a progress bar until the run ends (`views/performance.py`). |
| 5 | Prediction History page | Listed as optional in `Context.md`. Today Recent detections on the dashboard covers it, memory only. Owner decision. |
| 6 | Figma | Streamlit was chosen; Figma is only for mockups. No Figma file exists for the current pages. |
| 7 | Launch | Custom domain with HTTPS, a TURN server for WebRTC over the internet, operator name and email in `config.py` (the legal pages show a warning until then), and a legal review. See `LAUNCH_CHECKLIST.md`. |

Known harmless behaviour: opening a page address directly logs two 404s, for
`/<page>/_stcore/health` and `/<page>/_stcore/host-config` (the root ones answer); the WebRTC stream starts at a low resolution (320x213 seen) and rises
within seconds; with the window in the background the browser slows the page and the Frames per
second tile drops, honestly.
