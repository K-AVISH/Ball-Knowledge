# Requirements and checklist: Ball Knowledge Vision AI

Status key: **[x]** built and covered by a test or a render. **[~]** built, but not verified on a real camera or real recordings. **[ ]** not built.

Sources: `Context.md` (Sections 1 to 10), `Instructions.md` (Sections 1 to 10) and `LAUNCH_CHECKLIST.md`.

## A. Live camera (Instructions 2, Context 6A)

- [~] Start and Stop camera, one toggle button, camera permission requested by the browser.
- [~] Hand landmarks detected and drawn on the video when the overlay is on.
- [~] Camera status: connected, connecting, off, missing model or processing error.
- [~] Hand detection status: "1 hand detected", "No hand".
- [x] Camera resources released on stop (dashboard calls `processor.reset()` when the camera is off).
- [ ] Body pose landmarks (`hands+pose` mode). Supported by config and `download_models.py`, not exercised.

## B. Data collection (Instructions 3, Context 4)

- [x] Enter or pick a gesture name; name saved as a lowercase id.
- [x] Countdown, then recording at a fixed rate; progress bar; Stop recording saves what was collected.
- [x] Frames with no hand are not saved.
- [x] Samples stored with label, recording session id, person and timestamp (`data/samples.csv`).
- [x] Samples per gesture and recordings per gesture shown, with a status per gesture.
- [x] Undo last recording; delete all samples of a gesture (with confirmation).
- [~] Real recordings collected. 14 October 2026: 16 imported clips, 380 samples: first_meme 2 recordings (58), second_meme 3 (28), meme_3 3 (48), meme_4 4 (127), none 4 (119). first_meme needs a third recording; first_meme, second_meme and meme_3 are under 100 samples.
- [x] Ingest video files into samples (`import_videos.py`, `tests/test_import_videos.py`). Same pipeline as the camera, duplicates skipped.
- [x] Imported and live samples match (Stage 8, 14 October 2026): the same clip recorded through the Data collector page in the browser gave samples at median distance 0.15 from its imported samples, against 0.50 to other recordings of the gesture.

## C. Training and evaluation (Instructions 3, Context 4)

- [x] Validates rows and reports dropped rows by reason.
- [x] Tests by recording (leave one recording out), so no frame of a recording trains the model that tests it.
- [x] Leakage check.
- [x] Softmax regression trained by gradient descent (`gd_model.py`), minimising cross-entropy plus an l2 penalty. The penalty is chosen by the lowest held-out cost. Matches scikit-learn's solver to 1e-5 (`tests/test_gd_model.py`). Replaced the random forests and SVM on 13 October 2026; gradient boosting was measured and had a higher held-out cost.
- [x] Held-out results: accuracy, cost, precision, recall, F1, confusion matrix, top confusions, confidence cutoffs, per-recording results. Slightly optimistic because the penalty is chosen on the same recordings; the report says so.
- [x] Saves model, label mapping and report. A failed run keeps the previous model.
- [x] Warns on thin or perfect results.
- [x] Shows staleness (dataset changed, feature mode changed).
- [x] Readiness line before training (per-gesture recording count).
- [~] Trained on real recordings and evaluated (14 October 2026): 380 samples, 16 recordings, 5 gestures including `none`, 97.4% held-out accuracy, macro F1 0.973, l2 0.01. Most mistakes are `none` read as first_meme (4) or second_meme (2). All held-out clips were filmed in one room on one day, so this is a rough guide.
- [x] Per-class report and per-recording results checked on real data in the browser.

## D. Recognition (Instructions 3 and 6, Context 3 and 7)

- [x] Load the saved model at startup.
- [x] Same feature vector as collection.
- [x] Confidence threshold, with an Unrecognised state.
- [x] Top alternative predictions.
- [x] Voting window and stable-frames requirement: the Recognition and meme panels both show only the steady gesture (`LiveRecognizer.steady`), with a Checking state while a gesture is being confirmed (`tests/test_predictor.py`, `tests/test_status.py`). Checked with the stand-in camera on 13 October 2026: a 0.6 s dropout kept the result on screen.
- [~] Recognition result and confidence shown live. Held-out replay of all 16 clips on 14 October 2026: right gesture in 59% to 87% of hand frames per gesture, wrong gesture in none; most of the rest is unsure or no hand in view. Checked again on 13 October 2026 in the browser with a stand-in camera playing frames from the clips: No hand, Unrecognised (56% while the hands moved in), Recognised for both gestures, meme shown after the steady vote and cleared when the hands left, Stop camera clears everything. Those clips are training data, so this checks the wiring, not accuracy. Not yet run on a real webcam.
- [x] Scores that round to 100% or 0% are shown as "over 99%" or "under 1%" (`ui.score_pct`, `tests/test_status.py`).

## E. Meme dataset (Instructions 4, Context 5)

- [x] Metadata file `assets/memes/memes.json` mapping each gesture to name, meme title, image path, Ball Knowledge rating and description (`dataset_manager.py`). Ratings, titles and descriptions are empty until the user sets them.
- [x] Images in `assets/memes/`, relative paths.
- [x] Add a gesture, assign an image, edit description and rating without changing code: `dataset_manager.py` or one image in the gesture folder plus `import_videos.py`. No dashboard page for it yet.
- [x] Missing or invalid image and metadata handled with a visible message (`tests/test_memes.py`).
- [~] Meme panel updates automatically from the steady recognised gesture. Checked with a stand-in camera, not a real webcam.

## F. Open decisions for the user

- [x] **Video upload.** Decided 13 October 2026: option (b). `import_videos.py` reads local video files, extracts landmarks with the live pipeline and writes samples. Videos are processed locally and never copied. The privacy page has an Imported videos section.
- [ ] Figma or Streamlit for the dashboard (assumed Streamlit).
- [ ] Per-gesture confidence threshold (Stage 6).

## G. Dashboard (Instructions 5, Context 6)

- [x] Dark theme, football-inspired halfway-line mark, consistent cards.
- [x] Live statistics: FPS, latency, number of classes, model state. FPS fixed 13 October 2026: it averaged 1/gap per frame, which overstated uneven WebRTC delivery (24 shown for a 15 fps stream). It now averages the gaps and matches the browser's own count (`tests/test_vision.py`).
- [x] Live statistics: recognised this session and latest gesture with its time (Stage 7). Checked with the stand-in camera on 13 October 2026.
- [x] Right-hand order: recognition, meme, statistics, recent detections.
- [x] Progress strip: no longer on the dashboard (checked 14 October 2026). The Model tile and the Recognition panel show the model and recognition state.
- [~] Responsive at 1280px and 390px in a stand-in render. Not checked in a live Streamlit session.
- [x] Recent detections, with time, label and confidence, newest first (`predictor.DetectionLog`). One entry per change of steady gesture, or the same gesture after a pause over 2 s; holding a gesture or a short dropout adds nothing. Memory only, per browser session; the privacy page says so. Checked with the stand-in camera on 13 October 2026.

## H. Additional pages (Context 6, optional)

- [ ] Dataset Manager page (optional, Context 6).
- [~] Model Performance page: built and covered by the report contract. Verified with synthetic data only.
- [ ] Prediction History page (optional, Context 6).

## I. Quality and accessibility

- [x] Headings: page title, then section titles, in order.
- [x] Table captions, column and row header scope, confusion-matrix text legend.
- [x] Keyboard focus outline; wide tables scroll inside a labelled, focusable region.
- [x] Status region for camera changes; recording progress not announced repeatedly.
- [~] Keyboard and screen-reader pass in a live browser.
- [~] Contrast checked by eye against the palette, not measured with a tool.

## J. Testing (Instructions 9, Context 10)

- [x] Test suite exists: style rules, features, vision, landmark hook, data collector, training, status.
- [x] Full suite passes on the Mac (`python -m pytest -q`): 284 passed on 14 October 2026, also in two fresh venvs built from `requirements.txt`.
- [x] Stage 8 without a webcam (14 October 2026): `check_pipeline.py` replayed all 16 recordings through the live path, each with a model that never saw it: no wrong gesture shown in any clip. Browser run on a scratch dataset: record, train, recognise, stop, undo and retrain-needed all worked (`04_HANDOFF.md`).
- [x] Fresh install: `requirements.txt` installs one OpenCV package (`opencv-contrib-python`, the one MediaPipe needs) and passes the suite.
- [ ] Stage 8 with your webcam: the six steps in README, Test the whole pipeline.

## K. Launch (LAUNCH_CHECKLIST.md)

- [x] Favicon present and used.
- [x] No attribution badges; Streamlit footer and Deploy button hidden.
- [~] Privacy and terms pages drafted; need operator name, contact email and legal review.
- [ ] Custom domain and HTTPS (browsers need HTTPS for camera access outside localhost).
- [ ] Re-test the camera on the final domain in Chrome and Safari.

## L. Acceptance criteria (Context 10)

1. [~] Launches locally and accesses the webcam with permission.
2. [~] Recognises custom gestures with a trained classifier (stand-in camera only so far).
3. [~] Displays the correct dataset image for a recognised gesture (stand-in camera only so far).
4. [x] Ball Knowledge rating and description come only from the metadata (none are set yet).
5. [x] Rejects uncertain predictions (70% threshold, Unrecognised state).
6. [~] A new gesture can be added by collecting labelled samples and training (collection and training built, not run end to end).
7. [~] Dashboard updates during live camera use (stand-in camera only so far).
8. [x] Training metrics and a held-out evaluation are available, from real recordings.
9. [~] Camera errors, missing images and missing models handled (camera and model handled in code; images depend on Stage 6).
10. [x] README explains installation, data collection, training and execution.
