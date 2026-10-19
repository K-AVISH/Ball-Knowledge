# Requirements and checklist: Ball Knowledge Vision AI (all 8 stages built)

Updated 14 October 2026, after Stage 8 and six critique rounds.

Status key:

- **[x]** built and verified by an automated test, a browser run, or a run on your real data. The line says which.
- **[~]** built, but not yet verified on your webcam or in real Streamlit.
- **[ ]** not built or not done.

Sources: `Context.md` and `Instructions.md` (sections 1 to 10), `LAUNCH_CHECKLIST.md`.

## A. Live camera (Instructions 2, Context 6A)

- [~] Start and Stop camera with one toggle button; the browser asks for camera permission. Browser run with a stand-in camera; not on your webcam.
- [x] Hand landmarks found by MediaPipe and drawn on the video when the overlay is on. MediaPipe ran on all 16 real clips.
- [~] Camera status: off, connecting, connected, hand model missing, processing error.
- [~] Hand status: "1 hand detected", "2 hands detected", "No hand".
- [x] Camera resources released on stop (`processor.reset()` and `recognizer.reset()`); browser run showed Stop camera clearing every panel.
- [ ] Body pose landmarks (`hands+pose` mode). Supported by config and `download_models.py`, not used.

## B. Data collection (Instructions 3, Context 4)

- [x] Enter or pick a gesture name; saved as a lowercase id.
- [x] Countdown, recording at 10 samples a second, progress bar, one Start/Stop recording button. Browser run on 14 October saved 40 samples.
- [x] Frames with no hand are not saved.
- [x] Each sample stored with label, recording id, person and timestamp.
- [x] Samples and recordings per gesture shown, with a status. The hint names every shortfall ("Needs 42 more samples and 1 more separate recording"), and a legend explains the bars (`tests/test_display.py`).
- [x] Undo last recording; delete a gesture's samples with confirmation.
- [x] Import video files into samples (`import_videos.py`), same pipeline as the camera, duplicates skipped.
- [x] Imported and live samples match (browser run, median distance 0.15 against 0.50 to other recordings).
- [~] Enough real data. Now: first_meme 2 recordings (58 samples), meme_3 3 (48), meme_4 4 (127), none 4 (119), second_meme 3 (28). first_meme needs a third recording; first_meme, meme_3 and second_meme are under 100 samples; all filmed in one room on one day.

## C. Training and evaluation (Instructions 3, Context 4)

- [x] Validates rows and reports dropped rows.
- [x] Leave one recording out, so no frame of a recording trains the model that tests it.
- [x] Softmax regression by gradient descent (`gd_model.py`); penalty chosen by the lowest held-out cost; matches scikit-learn's solver (`tests/test_gd_model.py`).
- [x] Accuracy, cost, precision, recall, F1, confusion matrix, mix-ups, confidence cutoffs, per-recording results.
- [x] Recordings named by when they started on the performance page ("14 Oct 11:35 (c79027)").
- [x] Saves model, label mapping and report together; a failed run keeps the old model.
- [x] Warnings for thin, unequal or optimistic results. Staleness shown on the dashboard and performance page.
- [x] Trained on your real data: 97.4% held-out accuracy, macro F1 0.973, l2 0.01. Reproduced exactly on a second machine on 14 October.

## D. Recognition (Instructions 3 and 6, Context 3 and 7)

- [x] Saved model loaded once at startup and reloaded only when the files change.
- [x] Same feature vector as collection.
- [x] Confidence threshold (70%) with an Unrecognised state.
- [x] Top three scores.
- [x] Steady vote: 4 of the last 7 frames, with a Checking state.
- [x] `none` shows "No gesture" and no meme.
- [x] Held-out replay of all 16 clips: no wrong gesture shown in any clip.
- [~] Live recognition on your webcam (README, With your webcam, steps 1 to 6).

## E. Memes (Instructions 4, Context 5)

- [x] `assets/memes/memes.json` maps each gesture to name, title, image, rating and description (`dataset_manager.py`).
- [x] Images in `assets/memes/` with relative paths; missing or unreadable images and an unreadable `memes.json` show a message (`tests/test_memes.py`).
- [x] Add a gesture, set its image, change its rating and description without touching code: the Memes page, `dataset_manager.py`, or an image in the gesture folder with `import_videos.py`.
- [x] Memes page saving checked by tests: text, upload, bad upload saves nothing, text over the limit saves nothing, uploads over 10 MB refused (`tests/test_display.py`).
- [~] Memes page in real Streamlit (prompt Part 2, steps 1 to 5).
- [x] One name per gesture on every page, from the Memes page (`dataset_manager.display_name`).
- [x] Large images shrunk for display only, so the twice-a-second refresh stays light (`tests/test_display.py`).
- [~] Meme panel updates by itself from the steady gesture. Stand-in camera only.
- [ ] Titles, ratings and descriptions written. All four are empty. This is yours to do.

## F. Decisions for you

- [x] Video import: decided 13 October (`import_videos.py`).
- [ ] Figma or Streamlit for the dashboard. Built in Streamlit.
- [ ] Per-gesture confidence threshold. Not built; one global threshold.
- [ ] Prediction History page (optional in the brief). Not built.

## G. Dashboard (Instructions 5, Context 6)

- [x] Dark theme, football styling, consistent cards.
- [x] Recognition and Meme result beside the camera; Live statistics and Recent detections in a row below (renders at 1280px and 390px).
- [x] Live statistics: latest gesture with its time, recognised this session, gesture classes, FPS, latency, model state.
- [x] Recent detections: time, gesture, confidence, newest first, one row per change, memory only.
- [x] Notice naming gestures without a rating or description, pointing to the Memes page.
- [~] Responsive at 1280px and 390px in renders; not yet checked in a live Streamlit session.

## H. Pages (Context 6)

- [x] Live dashboard, Data collector, Model performance (real data).
- [x] Memes (new, 14 October). Renders checked; real Streamlit run pending.
- [x] Privacy policy and Terms. The privacy page's network section was wrong (it named a Google STUN server that the app does not use); corrected 14 October.

## I. Quality and accessibility

- [x] Headings in order; table captions; row and column header scope; confusion matrix legend in words.
- [x] Contrast measured: text 16.1:1, muted text at least 5.9:1, tags at least 5.0:1, matrix numbers at least 4.66:1 after capping the shading (`tests/test_display.py`).
- [x] No sideways scroll at 390px on any page or dashboard state in renders.
- [~] Keyboard-only pass in a real browser.
- [ ] Screen-reader announcement of a new result. Not built: an ARIA live region would re-read the panel every 0.5 seconds.

## J. Testing (Instructions 9, Context 10)

- [x] Automated suite: 307 passed in the review environment; 5 could only run on the Mac (4 AppTest, 1 capsys). 284 passed on the Mac before this session.
- [x] Clip replay through the live path (`check_pipeline.py`): 0 wrong gestures in 16 clips.
- [x] Browser run on a scratch dataset: record, train, recognise, stop, undo, retrain-needed.
- [ ] Full suite on the Mac after this session's changes (prompt Part 1).
- [ ] Your webcam run (README, steps 1 to 9).

## K. Launch (LAUNCH_CHECKLIST.md)

- [x] Favicon present and used.
- [x] No attribution badges; Streamlit footer and Deploy button hidden.
- [~] Privacy and terms drafted; need your name, contact email and a legal review.
- [ ] Custom domain and HTTPS (needed for camera access anywhere other than localhost).
- [ ] Camera tested on the final domain in Chrome and Safari.

## L. Final success criteria (Instructions 10)

1. [~] Open a live webcam dashboard. Stand-in camera only.
2. [~] Show a gesture to the camera. Needs your webcam.
3. [~] Your trained model identifies the gesture. 0 wrong gestures in 16 replayed clips; webcam pending.
4. [~] The matching image from your dataset appears by itself. Stand-in camera.
5. [~] The rating and description appear. Works from `memes.json`, but none are written yet.
6. [x] Confidence scores and recent recognition activity are shown.
7. [x] New samples can be collected and the model retrained for new gestures (browser run on a scratch dataset).
8. [x] New memes can be added and linked to gestures (Memes page and `dataset_manager.py`; Memes page real Streamlit run pending).
9. [x] Runs locally without paid services.
