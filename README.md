# Ball Knowledge Vision AI

Show a gesture to your webcam; a model you train yourself recognises it and the
dashboard shows the matching meme with its Ball Knowledge rating.

**Current status: Stages 1 to 8 built and checked with your webcam on 14 October, and again with the current model on 18 October.** Built: the live webcam
dashboard, hand landmarks, a data collector and a video importer for your own gestures,
a gradient descent model with an evaluation page, live recognition with smoothing, the
meme panel (image, title, Ball Knowledge rating and description per gesture), recent
detections and session statistics. Stage 8 tested the whole pipeline without a webcam
(see Test the whole pipeline below), and the webcam check worked. What is left is writing the
meme titles, ratings and descriptions on the Memes page, and recording more data.

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
email prompt, so the browser does not open by itself). The app listens on this computer only,
so other devices on your network cannot open it. Press **Start camera** and allow
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
7. Once every gesture has 2 recordings (and there are at least 2 gestures), Your dataset
   says "You can train now" with a link to the Model performance page, where Train model is.

Samples are saved to `data/samples.csv` (landmark numbers only, never images
or video). Use **Manage data** to undo the last recording or delete a gesture.
Frames without a detected hand are never saved. If you press Stop camera while
recording, the samples recorded so far are kept. If you open another page while
recording, the recording stops and nothing of it is saved; the Data collector says so
when you come back. Its messages stay until you next use a control on the page.

The dataset list shows each gesture by the name you set on the Memes page, with the
id its samples are saved under next to it ("First meme first_meme").

## Import recorded videos (optional)

You can also turn video files into samples, for example clips recorded with Photo Booth.
Put each gesture's clips in its own folder; the folder name becomes the gesture name
(`First meme` is saved as `first_meme`). Each clip counts as one recording.

```bash
source .venv/bin/activate
python import_videos.py "First meme" "Second meme" --dry-run   # check first, saves nothing
python import_videos.py "First meme" "Second meme"
```

- Every frame goes through the same steps as the live camera: it is mirrored, the
  landmarks are found, and the same feature code builds the sample. At most 10 samples
  are kept per second of video, as on the Data collector page.
- The first and last 0.25 s in which a hand is visible are dropped, because the hand is
  usually still moving into or out of the gesture there (`--trim` changes this).
- A file that is a byte-for-byte copy of another one is skipped, and so is a file that
  was already imported. A copy would put the same frames in both the training and the
  test set and make the test score meaningless. A copy is not a new recording.
- Hold the gesture for at least 2 to 3 seconds in each clip. Short holds give few samples.
- Only landmark numbers are saved. The video files are read and left unchanged.

Features use the frame's real proportions, so clips and webcam frames of different
shapes (3:2, 4:3, 16:9) describe the same hand with the same numbers.

## Train the model (Stage 4)

You need at least 2 gestures, each recorded in at least 2 separate sessions (3 or
more give steadier numbers).

```bash
source .venv/bin/activate
python train_model.py
```

Or open **Model performance** in the dashboard and press **Train model**. Both do
the same thing. In the dashboard, training runs in the background with a progress
bar, so you can keep using the app; the result appears on the page when it is done.
Only one training run can happen at a time, from the app or the terminal.

**The model.** Softmax regression trained by gradient descent (`gd_model.py`). For
each gesture it learns one weight per feature; softmax turns the scores into
probabilities. Training minimises one cost function:

    cost = average cross-entropy  +  l2 / 2 x (sum of squared weights)

Cross-entropy is large when the model gives the true gesture a low probability.
Each gesture counts equally, however many samples it has. The l2 penalty keeps the
weights finite: without it, gestures that can be told apart perfectly would push
the weights to infinity and every prediction would claim 100%. The cost is convex,
so it has one minimum. Gradient descent starts from all-zero weights and stops when
the gradient is practically zero (`GD_TOLERANCE`), which is the test for being at
that minimum. It uses Nesterov momentum to get there in fewer steps.

**Why gradient descent and not gradient boosting.** Both were measured on the first
5 recordings (13 October 2026), each recording tested by a model that never saw it,
with gradient descent's penalty fixed at 0.01 and scikit-learn's default settings for
boosting. All three scored 93% held-out accuracy, but the held-out cost (plain average
cross-entropy on unseen recordings) was 0.083 for gradient descent, 0.131 for gradient
boosting and 0.719 for histogram gradient boosting. The boosted models were sure of themselves even when wrong,
which defeats the confidence threshold. With a few hundred samples, a convex model
with a regularisation penalty is the better fit; boosting needs far more data.

**What training does:**

1. Validate `data/samples.csv` and drop malformed rows (the count is reported).
2. Test by recording: each recording in turn is held out, a model is trained on all
   the others, and it predicts the held-out one. No frame of a recording is ever used
   to train the model that tests it.
3. Repeat step 2 for each penalty in `GD_L2_OPTIONS` and keep the one with the lowest
   held-out cost.
4. Train the final model on every recording with that penalty.
5. Save `models/gesture_model.joblib`, `models/label_mapping.json` and
   `models/training_report.json`. If training fails, the previous model is kept.

**Augmentation (added 17 October 2026).** Whenever a model is trained, in steps 2 to 4,
each training sample is also learned in 4 slightly changed copies: the hands turned up to
15 degrees about the wrist and the points moved by about 1% of the hand's size. That
teaches the model that a tilted head or a shaky frame is still the same gesture, so it can
be more confident without being confident about frames it has never seen. The copies exist
only during training; nothing extra is saved, and every held-out score is measured on
your real samples. Settings: `GD_AUGMENT_*` in `config.py` (0 copies turns it off).

Training is deterministic: the same data gives the same model and the same scores.
Add more recordings and run it again whenever you want an updated model.

**Reading the results:** only the held-out numbers count. Accuracy on the recordings
the model learned from is always high. The penalty is picked using the same held-out
recordings, so those numbers are slightly optimistic, and the report says so. Perfect
scores usually mean your recordings were all made in similar conditions, so also try
the model live with new lighting, distances and people.

**Record a `none` gesture.** Without one, the model must name one of your gestures for
any hand it sees. Record relaxed hands and random movements as a gesture called `none`;
the dashboard treats it as "no gesture" and shows no meme for it.

## Live recognition (Stage 5)

Once a model is trained, open **Live dashboard**, press **Start camera** and show
one of your gestures. Beside the video, the **Meme** panel shows the meme for the gesture
you are holding, with the confidence meter under it. It never shows the gesture's name.
When there is no meme to show, a short message stands in its place:

| Message | Meaning |
|---|---|
| No trained model | No `models/gesture_model.joblib` yet. Record and train first; once your gestures are recorded (2 recordings each), it just says to train. |
| Model cannot be used | The model files are missing, damaged, or were made for another feature mode. The message says what to do (usually: train again). |
| Camera off / Waiting for video | The camera is off or still connecting. |
| Camera problem | Frames from the camera cannot be processed (for example the hand model is missing). The message under the video says why. No meme. |
| No hand in view | No hand in the frame, so nothing is classified. |
| Unrecognised | The best score is below the confidence threshold. The meter shows that score in amber. No meme. |
| Hold it steady | The latest frame passed the threshold, but the gesture has not held steady yet. No meme yet. |
| No gesture | Your `none` gesture: a hand, but none of your gestures, at once from the first such frame (no meme is at stake, so no vote is needed). No meme. |
| (the meme) | A steady gesture. The meter shows its average confidence over the frames that confirmed it. |

If `data/samples.csv` changed since the model was trained, an amber notice at the top of
the page says so. The meme's title, Ball Knowledge rating and description appear under the
meter only once you set them on the Memes page.

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
- Smoothing: the Meme panel shows a meme only once its gesture is steady,
  meaning recognised in at least `MIN_STABLE_FRAMES` (4) of the last `SMOOTHING_WINDOW`
  (7) frames. Frames with no hand or below the threshold count against it. So a single
  frame never shows a meme, and a hand dropping out for a frame or two does not
  hide one you are holding.
- Nothing from recognition is saved to disk (see the next section).

## Recent detections and statistics (Stage 7)

The **Recent detections** panel lists each meme that came up, as a small picture, with its
time and confidence, newest first. The list does not grow with every video frame:

- A gesture is added when it becomes the steady result.
- Holding it adds nothing more. A hand that drops out briefly adds nothing.
- The same gesture is added again only after a different gesture, or after it has not
  been the result for more than `HISTORY_REPEAT_GAP_S` (2 seconds).
- The `none` gesture is never added.
- Confidence is the average over the frames that confirmed the gesture.

Both panels sit in a row below the camera, so the Meme panel stays next to the video.
The **Live statistics** tiles show the **latest meme** (as a small picture) and its time, how many gestures were
**recognised this session**, the number of gesture classes, frames per second, latency
and the model state. The panel keeps the last `HISTORY_LENGTH` (10) entries; the count
includes all of them.

The list lives in memory for your browser session only. Reloading the page or stopping
the app clears it, and it is never written to disk. Stopping and starting the camera
keeps it.

## Memes (Stage 6)

Each gesture's meme lives in `assets/memes/`, listed in `assets/memes/memes.json`:
gesture name, meme title, image, Ball Knowledge rating and description. Paths are
relative, so the project can be moved.

- **On the Memes page (easiest):** open Memes in the top navigation, pick a gesture, type
  the gesture name, meme title, Ball Knowledge rating and description, choose an image if
  you want to replace it (up to 10 MB), and press Save meme. The panel on the right is the
  dashboard's Meme panel without its meter, so you see exactly what will appear. The table at the top
  shows what is still not set. After a save the form shows what was saved, with the upload
  box empty again. The 10 MB limit is set in two places that must stay equal:
  `MEME_MAX_UPLOAD_MB` in `config.py` and `maxUploadSize` in `.streamlit/config.toml` (a
  test checks it).
- **From a gesture folder:** put exactly one image (.jpg, .jpeg, .png, .webp or .gif)
  next to the clips and run `import_videos.py` on the folder. The image is copied to
  `assets/memes/<gesture>.<extension>`. Fields you already set are kept.
- **By hand:**

```bash
python dataset_manager.py                                   # list every meme
python dataset_manager.py first_meme --image "First meme/images.jpeg"
python dataset_manager.py first_meme --title "Meme title" --rating "8/10" --description "One line"
python dataset_manager.py first_meme --remove
```

The rating and description are yours to set. The model only recognises the gesture,
and the Memes page says so. Anything not set is left off the dashboard, never filled in;
only the Your memes table on the Memes page shows a "Not set" tag.
A missing or unreadable image, or a damaged `memes.json`, is shown as a message on
the dashboard instead of a meme. The name you give a gesture is used on every page,
including the tables on the Model performance page. Large images are shrunk for display
on the dashboard (the file itself is not changed), because the meme panel refreshes twice
a second.

## Test the whole pipeline (Stage 8)

### Without a webcam: replay your clips

```bash
source .venv/bin/activate
python check_pipeline.py "First meme" "Second meme" "Meme 3" "Meme 4" None
```

Every frame of every clip goes through the same code as the Live dashboard: mirroring,
MediaPipe landmarks, the feature vector, the model, the steady vote and the recent
detections list. For each clip it reports what the dashboard would have shown between
the first and the last frame with a hand: the right gesture, a wrong gesture, No gesture,
unsure (below the threshold or still checking), or no hand in view.

A clip that is already in `data/samples.csv` is classified by a model trained on every
other recording, so the model has never seen it. Any other clip uses your saved model.
To test new conditions, record a fresh clip in Photo Booth (another room, other light,
another person) and check it without adding it to the dataset:

```bash
python check_pipeline.py ~/Desktop/new_clip.mov --label meme_3
```

The line to watch is "A wrong gesture was shown in N clips". A wrong gesture means a
wrong meme on screen. Unsure frames only delay the meme.

### With your webcam (about 15 minutes)

Only you can run this part. Start the app as in Run the dashboard, open the Live
dashboard in Chrome and press Start camera.

| Step | Do this | You should see |
|---|---|---|
| 1 | Allow camera access | Camera connected, "Receiving 640x480 video" or similar, Frames per second above 10 |
| 2 | Raise one hand, then both, then lower them | "1 hand detected", "2 hands detected", then No hand. The skeleton follows your hands |
| 3 | Hold each gesture for 3 seconds: first_meme, second_meme, meme_3, meme_4 | "Hold it steady" for a moment, then that gesture's meme with a green confidence meter under it, and one new row in Recent detections with a small picture of the meme. No gesture name anywhere |
| 4 | Move a relaxed hand around | No gesture or Unrecognised. Never a meme |
| 5 | Switch straight from one gesture to another | The meme changes within about a second and Recent detections adds a row |
| 6 | Press Stop camera | The Meme panel says Camera off, Frames per second shows n/a and the camera light goes off |
| 7 | Open Memes, pick a gesture, type a rating such as 8/10 and a description, press Save meme | A green "Saved" message, the table shows Set, and the preview shows the rating and description |
| 8 | On Memes, choose a file that is not an image (for example a .txt renamed to .png) and save | A red "Nothing was saved" message; the old image stays |
| 9 | Back on the Live dashboard, show that gesture | Your rating and description now show under its meme and meter |

Write down any step that does not match, with the gesture and roughly how long it took.
A wrong meme in step 3 or any meme in step 4 is the result that matters most.

Your training clips were all filmed in Photo Booth. The webcam stream is more compressed
than those clips, so confidence can be a little lower live. If a gesture often stays on
Unrecognised, record one or two recordings of it on the Data collector page with the
webcam, then train again.

## Run the tests (no webcam needed)

```bash
source .venv/bin/activate
python -m pytest -q
```

`pytest.ini` limits collection to `tests/`. The prediction tests train a model on
synthetic data, so they check the code, not how well your gestures are recognised.
The tests only use scratch folders; if one ever changes your real `data/`, `models/`
or `assets/memes/`, the run ends with an error naming the files (`tests/conftest.py`).

## Project layout

| File | Purpose |
|---|---|
| `app.py` | Entry point: page setup, favicon, navigation |
| `ui.py` | Shared styling and camera widget |
| `views/` | Pages: `dashboard.py`, `collector.py`, `performance.py`, `memes.py`, `privacy.py`, `terms.py` |
| `vision.py` | Frame processing, MediaPipe landmarks, overlay, FPS/latency stats |
| `features.py` | Landmark normalisation → feature vectors (used by collection, training and prediction) |
| `data_collector.py` | Recorder state machine and the `data/samples.csv` store |
| `import_videos.py` | Turn video files into samples through the same pipeline as the camera |
| `check_pipeline.py` | Replay clips through the live recognition path and report what the dashboard would show |
| `gd_model.py` | Softmax regression trained by gradient descent (the classifier) |
| `train_model.py` | Validate, test by recording, choose the penalty, train and save the classifier |
| `predictor.py` | Load the saved model once, classify live frames on a worker thread, vote for a steady gesture, keep the session's recent detections |
| `dataset_manager.py` | Meme metadata: image, title, rating and description per gesture |
| `storage.py` | Safe saving: files are replaced in one step and locked while they change, so two tabs or a tab and a script never lose each other's work |
| `download_models.py` | One-time download of the MediaPipe models |
| `config.py` | Paths, camera size, thresholds |
| `tests/` | Automated tests |
| `data/`, `models/`, `assets/memes/` | Training data, saved models, meme images and `memes.json` |
| `docs/` | Critique log and handoff notes |

## Before any public launch

See `LAUNCH_CHECKLIST.md`. The privacy and terms pages need your operator name and
contact email in `config.py`, and a custom domain is still to be connected.

## Troubleshooting

- **Stuck on "Connecting"**: the browser has not granted camera access, or
  another app (Zoom, FaceTime) is using the camera.
- **Camera works but no video appears**: try Chrome; Safari's WebRTC can be picky.
- **Code changes not showing up**: stop Streamlit (Ctrl-C) and run it again.
- **"Hand model missing"** (the Meme panel says "Camera problem" meanwhile): run
  `python download_models.py`. The camera picks the model up within a couple of seconds;
  no reload is needed.
- **"... is being changed by another tab or program"**: another tab, or a script such
  as `import_videos.py`, is saving the same file. Wait a moment and try again.
- **"Another training run is already in progress"**: a run started from another tab
  or the terminal is still going. Its results appear on the Model performance page.
- **Port in use**: `streamlit run app.py --server.port 8502`.
