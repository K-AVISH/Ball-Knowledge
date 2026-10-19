# ML architecture

## 1. Pipeline

```
Frame (webcam 640x480, or video frame scaled to camera size)
  │  mirrored (vision.FrameProcessor), so the user sees a mirror and the data matches it
  ▼
MediaPipe HandLandmarker  (models/mediapipe/hand_landmarker.task, pretrained)
  │  up to 2 hands, 21 landmarks x (x, y, z) each, plus a Left/Right label and score
  │  detection confidence 0.6, tracking 0.5; most confident hand per side is kept
  ▼
features.correct_aspect        x and z multiplied by width/height, so all axes are in frame heights
features.build_feature_vector  [right hand 63][left hand 63]  ->  126 floats
  │  normalize_hand: wrist at origin, divide by largest wrist-to-landmark distance (x, y)
  │  left hand mirrored into right-hand space; a missing hand is 63 zeros
  │  no hand at all -> None (never classified, shown as "No hand")
  ▼
GradientDescentClassifier.predict_proba   5 probabilities
  ▼
Predictor.predict      top probability >= 0.70 -> RECOGNISED, else UNRECOGNISED
  ▼
LiveRecognizer vote    last 7 classified frames; a label needs 4 RECOGNISED votes -> Steady
  ▼
Dashboard              Steady gesture -> its meme; Steady "none" -> "No gesture"
```

Training uses the same first three boxes: `data_collector.Recorder` saves at most 10 vectors per
second of recording (near-duplicate frames add nothing), and `import_videos.py` drops the first and
last 0.25 s with a hand in each clip, when the hand is still moving into the gesture.

## 2. Features (`features.py`)

| Mode | Length | Layout |
|---|---|---|
| `hands` (current) | 126 | `f000-f062` right hand, `f063-f125` left hand (mirrored) |
| `hands+pose` | 225 | as above, plus `f126-f224`: 33 pose landmarks, hip centre at origin, divided by shoulder width |

What the features keep: the shape of each hand, its orientation in the image plane, relative
depth (z), and whether one or two hands are visible (zeros for a missing hand).

What they throw away on purpose: where the hand is in the frame, how big it looks, and the frame's
aspect ratio. Side effect: where the hand is **relative to the face or body** is also lost, though
several gestures are defined by it (`first_meme` hands over the face, `meme_4` hand over the eyes,
`second_meme` V sign by the eye). `hands+pose` would add body context but has never been trained on
real data, and the pose model only runs in that mode.

Handedness comes from MediaPipe on the mirrored frame. If it swaps Left and Right on a frame, the
hand lands in the other slot. The left-hand mirroring limits the damage, but this is a likely source
of single-frame noise.

## 3. Model (`gd_model.py`)

Multiclass logistic (softmax) regression, written from scratch, scikit-learn compatible.

```
J(W, b) = sum_i w_i * ( -log softmax(W x_i + b)[y_i] )  +  (l2 / 2) * ||W||^2
w_i     = 1 / (K * n_class(y_i))        class-balanced: every gesture counts equally
```

- Inputs are standardised per feature (mean and std from the training data; constant features get scale 1).
- Bias not penalised. Weights start at zero.
- Optimiser: Nesterov accelerated gradient descent, step 1/L with
  L = 0.5 * ||sqrt(w) X||_2^2 + l2 (an upper bound on the curvature), restart when a momentum step raises the cost.
- Stops when the gradient norm is at most `GD_TOLERANCE` (1e-6) or after `GD_MAX_STEPS` (20000).
  J is strictly convex for l2 > 0, so this is the unique minimum. The current model converged in 2,658 steps.
- Augmentation (`augment_copies`, set from `GD_AUGMENT_*` in `config.py`): inside `fit` only, each
  training row also gets 4 copies from `features.augment_hands`: each hand turned in the image plane
  about its wrist by up to 15 degrees, Gaussian noise of 0.01 hand sizes per coordinate, then
  normalised again like `normalize_hand`. Missing hands stay zero; pose columns are untouched. Fixed
  seed, so training stays deterministic. Prediction is unchanged. It happens inside every held-out
  fit too, so held-out rows are never augmented and never leak. `cost_` and `cost_history_` are over
  the augmented rows. Models pickled before 17 October load with `augment_copies` 0 (`__setstate__`).
- Exposes `cost_`, `grad_norm_`, `n_iter_`, `converged_`, `cost_history_` (about 200 points, log-spaced), `coef_`, `intercept_` on the original feature scale.
- Step numbering (code review R1-14, owner decision Q4, option C): `n_iter_` (the report's
  `cost.steps`) counts every step tried, while `cost_history_` (the report's `cost.history`)
  numbers only the steps kept. A momentum step that raises the cost is tried and undone, so the
  two differ by the number of restarts: the live model says 2,658 steps and its history ends at
  step 2,656. No page shows the history. `python train_model.py` says so in its report text when
  they differ. Numbering the history by steps tried changes the model file, so it waits for the
  next retrain you plan anyway (OD-7); do it then and remove this note.
- Saved with joblib (a pickle). Loading needs `gd_model.py` importable.

## 4. Training and evaluation (`train_model.py`)

1. **Validate** `samples.csv`: drop rows with a missing label or recording id, NaN or infinity,
   an all-zero vector, or a recording id used by more than one gesture. Counts by reason go into the report.
2. **Check recordings**: every gesture needs at least `MIN_SESSIONS_FOR_TRAINING` (2) recordings,
   otherwise it cannot be held out and still trained on.
3. **Leave-one-recording-out**: for each of the 16 recordings, train on the other 15, predict it.
   An internal check raises if a recording would be on both sides.
4. **Choose l2** from `GD_L2_OPTIONS` (1.0, 0.3, 0.1, 0.03, 0.01, 0.003) by lowest held-out balanced
   cross-entropy. Ties go to the larger l2 (smoother model).
5. **Refit** on all recordings with that l2.
6. **Report**: accuracy, balanced cost, macro and weighted precision, recall and F1, per-class
   metrics, confusion matrix, top confusions, mean confidence when right and when wrong, a cutoff
   table (coverage and accuracy at 0.5 to 0.9), per-recording accuracy and cost, warnings.
7. **Save** model, label mapping and report together (temporary names, then renamed).

`train(...)` takes `l2_options`, `min_sessions`, paths and a `log` callback. `held_out_probabilities(df, labels, l2, make=make_model)` lets you plug in any estimator factory.

## 5. Live decision rule (`predictor.py`, `config.py`)

| Setting | Value | Effect |
|---|---|---|
| `DEFAULT_CONFIDENCE_THRESHOLD` | 0.70 | Below this the frame is UNRECOGNISED. Picked from the cutoff table: with the 17 October model 96% of held-out frames pass (92% with the 14 October one), 98.6% of those are right. 0.80 and 0.90 were replayed on 17 October and gave fewer right frames with no fewer wrong memes |
| `SMOOTHING_WINDOW` | 7 | Classified frames in the vote |
| `MIN_STABLE_FRAMES` | 4 | Votes a label needs to become the result |
| `HISTORY_REPEAT_GAP_S` | 2.0 | Same gesture is logged again only after a 2 s gap |

The worker classifies only the newest frame and skips frames that arrive while it is busy, so the
vote runs over classified frames, not every video frame. Inference is a single matrix product
(about 5 microseconds per frame, measured 17 October); MediaPipe dominates latency.

Thresholds and the vote act together: a gesture needs 4 frames at 70% or more in a 7-frame window.
Any change to the model's confidence (calibration, a different l2, a new model family) changes how
often memes appear. Re-check with `check_pipeline.py` and the cutoff table.

## 6. Offline evaluation tools

| Tool | What it tells you |
|---|---|
| `python train_model.py` | Held-out metrics per class and recording, as above |
| `python check_pipeline.py <folders>` | Each clip replayed frame by frame through MediaPipe, features, model, threshold and vote, with a model trained without that clip. Shares of frames: right, wrong, no gesture, unsure, no hand. "Wrong" means a wrong meme on screen, the failure that matters most |
| `python check_pipeline.py clip.mov --label meme_3` | A new clip (another room, person, light) against the saved model, without adding it to the data |
| `python import_videos.py <folders> --dry-run` | How many samples a clip would give, nothing saved |

## 7. Tests for the ML code

`tests/test_features.py`, `test_gd_model.py` (same minimum as scikit-learn's logistic regression, cost never rises, zero
gradient at the end, class balance, determinism, save and load),
`test_train_model.py` (validation, no recording leakage, report), `test_predictor.py` (threshold,
vote, history, load errors), `test_import_videos.py`, `test_check_pipeline.py`,
`test_landmark_hook.py`. They use synthetic data, so they test code, not recognition quality.
