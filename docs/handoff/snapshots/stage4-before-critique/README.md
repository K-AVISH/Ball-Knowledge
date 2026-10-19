# Ball Knowledge Vision AI

Show a gesture to your webcam; a model you train yourself recognises it and the
dashboard shows the matching meme with its Ball Knowledge rating.

**Current status: Stage 4 of 8** — live webcam dashboard, hand landmarks, a data
collector for recording your own gestures, and model training with an evaluation
page. Live recognition and memes are not built yet; the dashboard says so honestly.

## Setup (macOS)

```bash
cd "/Users/kavishseema/Desktop/Passion Project"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Download the landmark models (one time)

MediaPipe needs two small model files (hand 7.8 MB, pose 5.8 MB) from Google's
official model storage. They are saved to `models/mediapipe/`.

```bash
source .venv/bin/activate
python download_models.py --pose     # drop --pose if you only need hands
```

## Run the dashboard

```bash
source .venv/bin/activate
streamlit run app.py
```

Open http://localhost:8501 in Chrome (the project config skips Streamlit's first-run
email prompt, so the browser does not open by itself). Press **Start camera** and allow
camera access. The same button turns into **Stop camera** while the camera is running. If it is blocked, open **System Settings → Privacy & Security →
Camera** and enable your browser, then reload the page.

## Collect training samples (Stage 3)

1. Open the **Data collector** page from the navigation at the top.
2. Press **Start camera** and allow access. You should see the skeleton on your hand.
3. Pick **New gesture...** and type a name, e.g. `four_gesture` (it is saved as a
   lowercase id). Optionally enter your name.
4. Press **Start recording**. After a 3-second countdown, hold the gesture and slowly
   move and rotate your hand until the progress bar fills (default 100 samples).
   The same button becomes **Stop recording** if you want to finish early.
5. Repeat for **at least 3 separate sessions per gesture**, changing lighting,
   distance, background and hand angle between them. Aim for 100–300 samples per
   gesture and 5–10 gestures. Add a relaxed-hand "none" class too.
6. Friends can record with their own name — more people means a better model.

Samples are saved to `data/samples.csv` (landmark numbers only — never images
or video). Use **Manage data** to undo the last recording or delete a gesture.
Frames without a detected hand are never saved.

## Train the model (Stage 4)

You need at least 2 gestures, each recorded in at least 3 separate sessions.

```bash
source .venv/bin/activate
python train_model.py
```

Or open **Model performance** in the dashboard and press **Train model**. Both do
the same thing:

1. Validate `data/samples.csv` and drop malformed rows (the count is reported).
2. Split by whole recording into training, validation and test sets, so frames
   from one recording never appear in two sets.
3. Train three baseline models (two Random Forests and an SVM) and pick one using
   the validation set only.
4. Evaluate the chosen model once on the test set: accuracy, precision, recall,
   F1, a confusion matrix, the gestures it mixes up, and how accuracy changes at
   different confidence cutoffs.
5. Save `models/gesture_model.joblib`, `models/label_mapping.json` and
   `models/training_report.json`. If training fails, the previous model is kept.

Training is repeatable: the same data and `--seed` give the same split and scores.
Add more recordings and run it again whenever you want an updated model.

**Reading the results:** only the test numbers count. Training accuracy is
always high. With each gesture tested on one recording the test score is a
rough guide, and the report says so. Perfect scores usually mean your recordings
were all made in similar conditions, so also try the model live with new
lighting, distances and people once live recognition is added.

## Run the tests (no webcam needed)

```bash
source .venv/bin/activate
python -m pytest -v
```

## Project layout

| File | Purpose |
|---|---|
| `app.py` | Entry point: page setup, favicon, navigation |
| `ui.py` | Shared styling and camera widget |
| `views/` | Pages: `dashboard.py`, `collector.py`, `performance.py`, `privacy.py`, `terms.py` |
| `vision.py` | Frame processing, MediaPipe landmarks, overlay, FPS/latency stats |
| `features.py` | Landmark normalisation → feature vectors (used by collection, training and prediction) |
| `data_collector.py` | Recorder state machine and the `data/samples.csv` store |
| `train_model.py` | Validate, split by recording, train, evaluate and save the classifier |
| `download_models.py` | One-time download of the MediaPipe models |
| `config.py` | Paths, camera size, thresholds |
| `tests/` | Automated tests |
| `data/`, `models/`, `assets/memes/` | Training data, saved models, meme images (filled in later) |

## Before any public launch

See `LAUNCH_CHECKLIST.md`. The privacy and terms pages need your operator name and
contact email in `config.py`, and a custom domain is still to be connected.

## Troubleshooting

- **Stuck on "Connecting…"** — the browser has not granted camera access, or
  another app (Zoom, FaceTime) is using the camera.
- **Camera works but no video appears** — try Chrome; Safari's WebRTC can be picky.
- **Code changes not showing up** — stop Streamlit (Ctrl-C) and run it again.
- **"Hand model missing"** — run `python download_models.py`.
- **Port in use** — `streamlit run app.py --server.port 8502`.
