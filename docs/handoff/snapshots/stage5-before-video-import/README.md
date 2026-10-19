# Ball Knowledge Vision AI

Show a gesture to your webcam; a model you train yourself recognises it and the
dashboard shows the matching meme with its Ball Knowledge rating.

**Current status: Stage 5 of 8.** Built: the live webcam dashboard, hand landmarks,
a data collector for recording your own gestures, model training with an evaluation
page, and live recognition of the trained gestures. Not built yet: memes and ratings
(Stage 6), smoothing and detection history (Stage 7) and end-to-end testing (Stage 8).
The dashboard says so instead of showing placeholder results.

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
6. Friends can record with their own name. More people means a better model.

Samples are saved to `data/samples.csv` (landmark numbers only, never images
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
lighting, distances and people.

## Live recognition (Stage 5)

Once a model is trained, open **Live dashboard**, press **Start camera** and show
one of your gestures. The Recognition panel shows one of these states:

| State | Meaning |
|---|---|
| Not trained | No `models/gesture_model.joblib` yet. Record and train first. |
| Model cannot be used | The model files are missing, damaged, or were made for another feature mode. The message says what to do (usually: train again). |
| Retrain needed | The model works, but `data/samples.csv` changed since it was trained. |
| Waiting for the camera / video | The camera is off or still connecting. |
| No hand detected | No hand in the frame, so nothing is classified. |
| Unrecognised | The best score is below the confidence threshold. No gesture is shown. |
| Recognised | The gesture name, its confidence and the top scores. |

How it works:

- `predictor.py` loads the model and `models/label_mapping.json` once, and checks
  they match each other and `FEATURE_MODE`. A retrained model is picked up the next
  time the dashboard loads.
- The landmark hook builds the feature vector with `features.py`, the same code the
  data collector used, so live input matches the training data.
- The model runs on its own thread. The video never waits for it; if the model is
  slower than the camera, the newest frame is classified and older ones are skipped.
- `DEFAULT_CONFIDENCE_THRESHOLD` in `config.py` (70% by default) decides what counts.
  Confidence is the model's own estimate, not a calibrated probability. Use the
  confidence cutoff table on **Model performance** to choose the value; the row in
  use is marked there.
- Each result describes one frame. Smoothing over several frames is Stage 7, so the
  result can flicker while your hand moves.
- Nothing from recognition is saved.

## Run the tests (no webcam needed)

```bash
source .venv/bin/activate
python -m pytest -q
```

`pytest.ini` limits collection to `tests/`. The prediction tests train a model on
synthetic data, so they check the code, not how well your gestures are recognised.

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
| `predictor.py` | Load the saved model once and classify live frames on a worker thread |
| `download_models.py` | One-time download of the MediaPipe models |
| `config.py` | Paths, camera size, thresholds |
| `tests/` | Automated tests |
| `data/`, `models/`, `assets/memes/` | Training data, saved models, meme images (Stage 6) |
| `docs/` | Critique log and handoff notes |

## Before any public launch

See `LAUNCH_CHECKLIST.md`. The privacy and terms pages need your operator name and
contact email in `config.py`, and a custom domain is still to be connected.

## Troubleshooting

- **Stuck on "Connecting"**: the browser has not granted camera access, or
  another app (Zoom, FaceTime) is using the camera.
- **Camera works but no video appears**: try Chrome; Safari's WebRTC can be picky.
- **Code changes not showing up**: stop Streamlit (Ctrl-C) and run it again.
- **"Hand model missing"**: run `python download_models.py`.
- **Port in use**: `streamlit run app.py --server.port 8502`.
