# UI critique log: Ball Knowledge Vision AI (Stages 1 to 8 complete)

Two passes of six critique-and-improve rounds on the finished app, both on 14 October 2026. Each round: critique with evidence, fix, run the tests, look at the pages again, score.

- **First pass** (rounds 0 to 6): in a review environment without Streamlit. The pages were rendered by a stand-in and screenshotted.
- **Second pass** (rounds M0 to M6, at the end of this file): on your Mac, in real Streamlit 1.65 and streamlit-webrtc 0.78.1, in Chrome (the Claude desktop app's browser), with a stand-in camera. It found defects the first pass could not see, so its baseline score is lower than the first pass's final score.

## First pass: how it was checked, and its limits

- **Real data.** Every render used your real `data/samples.csv` (380 samples, 16 recordings, 5 gestures), your saved model and your `assets/memes/`, copied into scratch folders. Nothing in `data/`, `models/` or `assets/` was changed.
- **Real recognition code.** The live states were made by feeding real recorded samples through the real `predictor.Predictor` and `LiveRecognizer`. Only the camera was simulated (a placeholder box and fixed FPS and latency of 24 and 18.4 ms).
- **No live Streamlit.** Streamlit, streamlit-webrtc and MediaPipe could not be installed in the review environment (package registries unreachable). The page scripts in `views/` were executed against a stand-in that records the HTML they emit, using the real `ui.py` CSS, then screenshotted in Chromium at 1280px and 390px. Streamlit's own spacing, widgets and fonts differ slightly. The new Memes page form has not been run in real Streamlit.
- **Tests.** Run with a stand-in for pytest: 307 passed, 5 not run (4 Streamlit AppTest tests for the legal pages, 1 test that needs pytest's `capsys`). The suite on the Mac before this session was 284 passed; it now has 312 test cases (24 in the new `tests/test_display.py`).
- **Independent check of the numbers.** Retraining on your real samples in a scratch folder reproduced the saved report exactly: held-out accuracy 97.37%, cost 0.1056, macro F1 0.9729, l2 0.01, identical confusion matrix and cutoff table.

## Rubric

| Dimension | Weight | Question |
|---|---|---|
| Data truth | 25% | Is every number measured, labelled and sourced, and every statement on the site true? |
| Recognition and data state | 20% | Does each state (off, no hand, checking, unrecognised, no gesture, recognised, stale, not trained, meme missing) show distinctly and consistently? |
| Flow and action clarity | 15% | Can the user see what to do next, without the terminal? |
| Visual hierarchy and brand | 15% | Is the most important result first and balanced? |
| Interaction reliability | 10% | Do controls behave and recover from errors? |
| Accessibility and responsive | 10% | Headings, captions, contrast, focus, no sideways scroll at 390px. |
| Maintainability | 5% | Shared logic in one place, tests, docs. |

Gate: weighted 9.0 or more, every dimension 8.5 or more.

## First pass: scores

| Round | Data truth | State | Flow | Visual | Interaction | Access. | Maintain. | Weighted |
|---|---|---|---|---|---|---|---|---|
| 0 baseline | 8.0 | 8.0 | 6.5 | 7.0 | 7.5 | 7.5 | 8.0 | 7.53 |
| 1 names and hints | 8.5 | 8.5 | 6.5 | 7.0 | 7.5 | 7.5 | 8.0 | 7.75 |
| 2 Memes page, privacy | 8.8 | 8.5 | 8.0 | 7.0 | 7.5 | 7.5 | 8.2 | 8.06 |
| 3 dashboard layout | 8.8 | 8.5 | 8.0 | 8.3 | 7.5 | 7.5 | 8.2 | 8.26 |
| 4 contrast, 390px | 8.8 | 8.5 | 8.0 | 8.3 | 7.5 | 8.3 | 8.2 | 8.34 |
| 5 reliability | 9.0 | 8.5 | 8.0 | 8.3 | 8.0 | 8.3 | 8.4 | 8.45 |
| 6 consistency | 9.0 | 8.8 | 8.3 | 8.5 | 8.0 | 8.3 | 8.6 | 8.59 |

Final: weighted 8.59. The 9.0 gate is not met. Interaction (8.0) and Accessibility (8.3) stay below 8.5 because the camera, the Memes page form and a keyboard and screen-reader pass have not been run in a real browser session. Those need your Mac.

## Round 0: baseline

Renders: dashboard in 9 states, collector, performance, at 1280px and 390px. No sideways scroll in any.

What works: every state of the Recognition panel is distinct and honest (Checking, Unrecognised with the score below the 70% line, No gesture, No trained model); the confidence is called "the model's own estimate, not a calibrated probability"; every number on the performance page comes from `training_report.json`.

Defects found:

1. **One gesture, two names.** The Recognition panel, top scores, Latest gesture tile and Recent detections said `meme_3`; the Meme result panel said "Meme 3" (`ui.recognition_card`, `views/dashboard.py`).
2. **Every meme has an empty title, rating and description** (`assets/memes/memes.json`). Success criterion 5 (show the rating and description) cannot be met, and the only way to set them was the terminal.
3. **Collector hint hides a shortfall.** first_meme has 2 recordings, but its hint said only "Needs 42 more samples" (`data_collector.class_status` returned the first problem only). The performance page warned about the recordings; the collector did not.
4. **Collector bars and text disagree.** Bars fill toward 300 samples, the hint counts toward 100, with no legend.
5. **Recordings named by hash.** "Each recording, held out" listed ids like `c79027849fda`, which mean nothing to you.
6. **Unbalanced dashboard.** Right column about 1,650px tall, camera column about 870px; the Model tile and Latest gesture tile spanned full width with one word each.

## Round 1: names and hints

Fixes:

- `dataset_manager.display_name(label, records)`: the gesture name from `memes.json`, else the id. Used by the Recognition panel (headline, Checking hint, top scores), the Latest gesture tile and Recent detections.
- `data_collector.class_status` names both shortfalls: "Needs 42 more samples and 1 more separate recording". Plural handled.
- Collector legend: "Bars fill toward 300 samples, the suggested amount. Ready needs 100 samples from 3 separate recordings."
- `DatasetStore.session_times()`; the performance page names each recording by when it started, plus the start of its id: "14 Oct 11:35 (c79027)".

Evidence: render shows "Meme 3" in the headline and every table; collector shows the combined hint. Tests: `tests/test_display.py` (names, hints, session times).

## Round 2: Memes page and privacy page

Fixes:

- **New Memes page** (`views/memes.py`, in the navigation after Model performance): a table of what is set per gesture, a form for gesture name, meme title, Ball Knowledge rating, description and image, and a live preview that is the dashboard's own Meme result panel. Saving goes through `dataset_manager.save_edit`, the same checks as the terminal tool. A bad image or text over the limit saves nothing.
- Dashboard notice: "No Ball Knowledge rating or description yet for: First meme, Meme 3, Meme 4, Second meme. Set them on the Memes page." Missing-image messages now point to the Memes page.
- **Privacy page was wrong.** It said the camera connection uses Google's STUN server. `ui.py` sets an empty server list, so none is used. Corrected, and a "Meme images" section added. `LEGAL_LAST_UPDATED` is now 14 October 2026.

Tests: save with upload, save without upload keeps the image, bad upload names your file and writes nothing, text over the limit writes nothing, page in navigation.

## Round 3: dashboard layout

Fixes:

- Recognition and Meme result stay beside the camera; Live statistics and Recent detections moved to a full-width row below (a second fragment on the same 0.5 s refresh). Desktop page height fell from about 1,670px to about 1,400px. On a phone the order is camera, recognition, meme, statistics, detections.
- Six tiles in a three-column grid inside one Live statistics card. The Latest gesture tile shows the name, with the time on its own line ("at 07:39:18"), after the first attempt wrapped as "Meme / 3 07:38:58".

## Round 4: contrast and phone width

Measured contrast (WCAG formula) for the palette: body text 16.1:1, muted text 5.9 to 6.6:1, tags 5.0 to 7.9:1, button text 7.9:1, links 7.6:1. (Correction from round M4: in real Streamlit the green buttons had white text at 2.38:1, not 7.9:1. Fixed there.) All pass AA except **white numbers on the darkest confusion-matrix cells: 3.13:1 on green**. The shading is now capped (alpha 0.55), giving 4.66:1 on green and 5.98:1 on red. Test: `test_confusion_matrix_numbers_keep_aa_contrast_on_the_darkest_cells`.

390px renders of every page: no sideways scroll; tables scroll inside their own labelled regions.

## Round 5: reliability

- **Meme images were sent twice a second at full size.** The meme panel is part of the 0.5 s refresh and embeds the image. `meme_3.jpg` is 132 KB, so about 350 KB/s; an image uploaded on the new page could have been many MB. Large images are now shrunk for display only (longest side 900px when over 900px or 250 KB; GIFs untouched; the file on disk unchanged), and uploads over 10 MB are refused.
- Description help says line breaks are joined (the save collapses whitespace).
- Retrained on the real data in a scratch folder: the saved report reproduced exactly (see the limits section).

Tests: large image shrunk and file unchanged, small image sent as is, oversized upload refused.

## Round 6: consistency

- The Model performance page now uses the same gesture names (per-gesture table, confusion matrix, mix-ups, recordings).
- `none` reads "No gesture" everywhere, matching the Recognition panel.
- Memes form widgets keyed per gesture, so text typed for one gesture and not saved never shows in another's form.
- README: Memes page, new dashboard layout, image shrinking.

Final renders: 12 pages and states at 1280px and 390px, zero sideways scroll in all.

## Second pass: on the Mac in real Streamlit

### How this was checked, and its limits

- **Tests.** `python -m pytest -q` with the project's `.venv` (Python 3.14.7): 312 passed at the start of this pass, nothing failed.
- **Clip replay.** `python check_pipeline.py "First meme" "Second meme" "Meme 3" "Meme 4" None`: "A wrong gesture was shown in 0 of 16 clips", per-gesture shares identical to the table in `04_HANDOFF.md`.
- **Real Streamlit.** The app was run with `streamlit run app.py` and checked in the Claude desktop app's built-in browser (Chromium) at 1280px and 390px. Your own copy (`data/`, `models/`, `assets/memes/`) was opened read-only on port 8501. Everything that saves, uploads or records ran on a scratch copy of the project on port 8502. A checksum of every file in `data/`, `models/`, `assets/` and the gesture folders was taken before the pass and compared after it.
- **Stand-in camera.** The browser's camera call was replaced, in the page, by a canvas stream that plays frames taken from your own clips (15 frames per second, 640x427). The video went through the real WebRTC connection, MediaPipe, the model, the steady vote and the panels. It is not your webcam: lighting, compression and timing differ. No screenshot with camera frames was saved, because the clips show your face.
- **What could not be checked:** your webcam, Safari, and a screen reader.

### Scores

| Round | Data truth | State | Flow | Visual | Interaction | Access. | Maintain. | Weighted |
|---|---|---|---|---|---|---|---|---|
| M0 baseline in real Streamlit | 8.5 | 8.5 | 8.3 | 7.5 | 8.4 | 8.0 | 8.3 | 8.25 |
| M1 names and stated limits | 9.0 | 8.8 | 8.5 | 7.5 | 8.5 | 8.0 | 8.5 | 8.49 |
| M2 panels and spacing | 9.0 | 8.8 | 8.5 | 8.2 | 8.5 | 8.2 | 8.7 | 8.62 |
| M3 result first | 9.0 | 8.8 | 8.7 | 8.8 | 8.5 | 8.2 | 8.8 | 8.75 |
| M4 contrast and keyboard | 9.1 | 8.8 | 8.7 | 8.9 | 8.5 | 8.8 | 8.8 | 8.85 |
| M5 controls and recovery | 9.2 | 9.0 | 8.9 | 8.9 | 9.2 | 8.8 | 9.0 | 9.02 |
| M6 error states and consistency | 9.2 | 9.2 | 8.9 | 8.9 | 9.2 | 8.8 | 9.2 | 9.07 |

Final for the second pass: weighted **9.07**, lowest dimension Accessibility at 8.8. The gate (9.0, every dimension at least 8.5) is met for everything that can be checked without your webcam. Your webcam run (README, With your webcam) is still the check that counts for the camera and recognition.

### Round M0: baseline in real Streamlit

Checks from prompt Part 2, all passed: no red error box on any page; dashboard order Camera, Recognition, Meme result, then Live statistics and Recent detections; notice "No Ball Knowledge rating or description yet for: First meme, Meme 3, Meme 4, Second meme"; collector hints and legend; performance page 97.4%, "Meme 3", "No gesture", "14 Oct 11:35 (c79027)"; Memes table, form and preview; privacy page has no STUN mention and has a Meme images section. No page scrolls sideways at 390px (`document.documentElement.scrollWidth` 390 on all six pages). Console: only Streamlit's iframe feature-policy warnings, no errors.

Memes page in real Streamlit (scratch copy, prompt Part 2 steps 1 to 5): all five passed. Save gave the green "Saved" message, Set in the table and the preview, and `memes.json` held the values. A PNG upload was copied to `assets/memes/first_meme.png` and shown. A text file named `.png` gave "Nothing was saved" and `memes.json` kept its checksum. Unsaved text did not follow to another gesture. The dashboard notice dropped the finished gesture.

Live states with the stand-in camera: Camera off, No hand detected, Checking, Unrecognised, No gesture, Recognised (Meme 3, 7 of 7 frames, 99%), and Stop camera clearing the panels with Frames per second n/a. The browser's connection was created with `{"iceServers":[]}` and every request went to localhost, which confirms the privacy page's network section.

Defects found (most important first):

1. **The upload box states a limit that is not the real one.** It said "200MB per file" (Streamlit's default); saving refuses anything over 10 MB (`views/memes.py:107`, `.streamlit/config.toml`).
2. **Bordered panels are not styled as cards.** Streamlit 1.65 no longer has the `stVerticalBlockBorderWrapper` element that `ui.py:44` styles, so Camera, Train, Your memes, Edit a meme and the other bordered panels have a transparent background and Streamlit's grey outline at 6px, next to the filled HTML cards with an 8px radius. The rule at `ui.py:52` is dead.
3. **The meme is below the fold when a gesture is recognised.** At 1280x900 the Recognition card is 455px tall (its top-scores table), so the meme image starts at 849px and only 50px of it is visible. The brief asks for the meme to be displayed prominently (`views/dashboard.py:116`).
4. **One gesture, two names, again.** The Data collector listed ids (`first_meme`, `none`) and the Model performance warnings said "Fewer than 3 recordings for: first_meme" above tables that say "First meme". `01_PROJECT_CONTEXT.md` and the README say the name is used on every page (`views/collector.py:191`, `train_model.make_warnings`).
5. **The camera button has no visible keyboard focus.** Tab reaches Start camera inside the component's iframe, but it has `outline: none` and no focus ring (`ui._IFRAME_CSS`).
6. **Hints touch the bottom border of panels.** A hint that ends a panel sits 0px from the border (Streamlit gives the last markdown block a -1rem margin): collector Camera card, Your memes, Your dataset.
7. **The second row does not line up.** Live statistics and Recent detections split 1:1 under a 3:2 row (`views/dashboard.py:139`).
8. **At 390px there is a 64px gap** between the Camera card and Recognition (the large column gap becomes a row gap).
9. **After a save the upload box still lists the file**, as if it were waiting to be saved.
10. **Error text names a Python exception**: "cannot be read as an image (UnidentifiedImageError)".
11. **The meme title is never mentioned as missing.** The panel shows the gesture name in the title's place without saying the title is not set, and the Memes table has no Title column.

### Round M1: names and stated limits

Fixes:

- `.streamlit/config.toml`: `maxUploadSize = 10`, so the upload box says "10MB per file" and refuses a larger file before it is sent ("Error: File must be 10.0MB or smaller." for an 11.5 MB file, nothing written).
- Data collector: each gesture is listed by its name with the id beside it ("First meme first_meme"), and the gesture boxes read "First meme (first_meme)". Undo, delete and the saved messages use the name too.
- `train_model.make_warnings(report, name)`: the performance page shows the report's cautions with the gesture names ("Fewer than 3 recordings for: First meme."). Called without `name` it returns exactly the saved warnings (tested).
- `dataset_manager.image_file_problem`: "holiday.png cannot be read as an image. Choose a JPG, JPEG, PNG, WEBP or GIF file."
- Memes page: a Title column, and the none note now says "No gesture (the none gesture)". The meme panel says "No meme title set, so the gesture name is shown."

Tests: new `tests/test_pages.py` runs the collector, performance and Memes pages through Streamlit's AppTest on a small synthetic project (the camera widget replaced by one that reports the camera as off), plus the upload limit, the error text and the panel. 7 tests; 6 of them fail on the code from before this round. Suite: 319 passed.

Look again: the collector, performance and Memes pages at 1280px and 390px in real Streamlit show the names and the new texts; no sideways scroll; no error box.

Scores: Data truth 9.0 (the false 200MB statement is gone and names agree; checked in the browser). State 8.8 (names agree on every page). Flow 8.5 (plain error text; the table shows what is still missing). Interaction 8.5 (an oversized file is refused before upload). Maintainability 8.5 (page tests). Visual and Accessibility unchanged: defects 2, 3, 5 to 8 are still open.

### Round M2: panels and spacing

Critique (real Streamlit, 1280px and 390px): defects 2, 6, 7 and 8 from M0 were still there. Measured with the browser: a hint ending the collector Camera panel 0px from the border, the confusion matrix note 1px; Camera card to Recognition 64px apart at 390px.

Fixes:

- `ui.panel(key)` replaces `st.container(border=True)` on every page. It keys the container (`panel-camera`, `panel-train` and so on), Streamlit adds the class `st-key-panel-...`, and the CSS gives it the same fill (#111815), border (#212c26), 8px radius and padding as the HTML cards. The dead `stVerticalBlockBorderWrapper` rules are gone.
- The camera component's own page is made transparent, so the panel colour shows behind the video and the button (before, it showed as a darker band once the panel had a fill).
- Text that ends a block (hints, the confusion matrix note, empty boxes, the tips list) gets back the 1rem that Streamlit takes away. Every panel on every page now ends 17px below its last line (measured on all 14 panels).
- Live statistics and Recent detections use the same 3:2 split as the row above, so the gutters line up.
- Stacked columns on a phone are 1rem apart (measured 16px, was 64px).
- **A problem this round caused, and its fix.** With the panels filled, Streamlit's text boxes (fill #111815, border #111815) disappeared into them: an empty Meme title box could not be seen. `.streamlit/config.toml` now sets `showWidgetBorder = true` and `borderColor = "#5f7067"`, an outline of 3.4:1 on a panel. A focused box still turns green (#2fbf71, checked in the browser).

Tests: 6 more in `tests/test_pages.py` (panels go through `ui.panel`, the key it sets, the margin rule, the column split, the transparent camera frame, the outline contrast). Suite: 325 passed.

Look again: all six pages at 1280px and 390px. No sideways scroll, no error box, every panel the same colour as the cards, every text box outlined.

Scores: Visual 8.2 (one card style; aligned rows; the meme is still below the fold when recognised). Accessibility 8.2 (text boxes now have a 3.4:1 edge; the camera button still has no focus ring). Maintainability 8.7 (one panel helper, no dead CSS). Others unchanged.

### Round M3: the result first

Critique (stand-in camera, Meme 3 held): at 1280x900 the Recognition card ran from 334px to 789px because of its top-scores table, and the meme image from 849px to 1120px, so only its top 50px were on screen. On the Model performance page four separate yellow boxes stood between the summary tiles and the first table.

Fixes:

- `ui.recognition_card(..., scores=False)` leaves out the top-scores table, and `ui.scores_card` shows the same table in its own "Top scores" panel. The dashboard now shows Recognition, then Meme result, then Top scores. The panel is left out when there is nothing to explain (camera off, no hand, No gesture). Called as before, `recognition_card` still includes the table, so the existing tests and the Memes page are unchanged.
- The page description may run to 80 characters a line (was 64), which saves a line above the cards.
- The performance cautions share one box, "Read these results with care:", with one line each.

Evidence (stand-in camera, measured in the browser): with Meme 3 recognised the meme image now runs from 614px to 885px, fully inside a 900px window, beside the video. Unrecognised shows Top scores ("Meme 3 62%, No gesture 36%, First meme 2%", captioned "none high enough to count"); No gesture and No hand show none. At 390px the order is camera, Recognition, Meme result, Top scores, Live statistics, Recent detections, with no sideways scroll. On the performance page the first table now starts at 800px.

Tests: 4 more in `tests/test_pages.py` (one caution box, the card without and with scores, no scores panel without scores, the order on the dashboard). Suite: 329 passed.

Scores: Visual 8.8 (gesture and meme together in the first screen; one caution box). Flow 8.7 (the result and the reason for it read top to bottom). Maintainability 8.8 (the recognition states are worked out in one place, `_recognition_state`, for both panels). Others unchanged.

### Round M4: contrast and keyboard

Critique. A contrast check ran in the browser on every page: for each piece of visible text, its colour against the colour actually behind it (semi-transparent fills blended in), by the WCAG formula. It found:

1. **The green buttons fail AA.** Start recording, Train model and Save meme have Streamlit's white text on #2fbf71: **2.38:1** (4.5:1 needed). The first pass recorded "button text 7.9:1"; its stand-in render did not use Streamlit's buttons, so that figure was wrong.
2. On hover Streamlit darkens them to #20834d.
3. "Delete gesture data" at 3.39:1: it is disabled until you tick the box, and WCAG does not apply to disabled controls. The slider's value "100" was reported at 1:1 because the check blended in the slider handle beneath it; the number sits beside the handle, green on the panel, 7.56:1.

A keyboard-only pass (Tab through every page, focus logged as it moved) found:

4. **Start camera / Stop camera has no visible focus** (inside the component's frame: `outline: none`).
5. Tab stops once on the scrolling page area (Streamlit's main section) with nothing shown.

Fixes:

- Green buttons have dark text (#0b0f0d on #2fbf71, 8.10:1), the same as the camera button, and on hover a lighter green (#45c983, 9.13:1) instead of the darker one, where dark text would be 4.06:1.
- The camera button shows a 2px green ring when focused from the keyboard (7.56:1 against the panel).
- The page area shows the same ring when Tab stops on it.

Evidence after the fixes: the contrast check passes for every piece of text on all six pages (the lowest is 4.8:1, the confusion matrix numbers) and inside the camera frame (7.65:1). Keyboard pass at 1280px: every control on the dashboard, collector, performance, Memes, privacy and terms pages is reached in order (top links, page, then the controls top to bottom) and shows a ring, or for text boxes the green border Streamlit draws a moment after focus (checked: "Ball Knowledge rating" rgb(47, 191, 113)). At 390px the menu button is reached first and Enter opens it with all six pages. Hovered Train model measured at rgb(69, 201, 131) with dark text.

Tests: 4 more in `tests/test_pages.py`. Suite: 333 passed.

Not done: no screen reader was available, so results are still not announced (open item), and Safari was not checked.

Scores: Accessibility 8.8 (text contrast and focus rings measured on every page). Visual 8.9 (all green buttons now look alike). Data truth 9.1 (a wrong contrast figure in the first pass is corrected here and in the checklist). Others unchanged.

### Round M5: controls and recovery

Critique: every control that changes something, run in real Streamlit on the scratch copy with the stand-in camera.

| Action | What happened | Verdict |
|---|---|---|
| Start recording with the camera off | Warning "Press Start camera above the video first." | Wrong: the button is under the video, on a phone and on a desktop |
| Record 20 samples of Meme 3 | Countdown 3, 2, 1, then "Recording Meme 3: 1 of 20" up to 19, then "Saved 20 samples for Meme 3"; the one button read Start, Stop, Start; the file grew from 380 to 400 rows | Works |
| Live dashboard afterwards | Retrain needed in Recognition and in the Model tile: "380 samples then, 400 now. Train again to include the changes. Retrain on the Model performance page." | Works, but says train twice |
| Train model | Spinner "Training. This usually takes a few seconds.", then "Trained in 2025 steps. Held-out accuracy 97.5% on 400 samples from 17 recordings." after about 6.5 s; dashboard then "Model: Loaded" | Works (scratch data with a stand-in recording, so these are not your model's numbers) |
| Undo last recording | "Removed the last recording (20 samples)", 380 rows; every value identical to your original file (largest difference 0.0) | Works |
| Stop camera during a recording | "Saved 70 samples for First meme", button back to Start recording | Works (keeps what was recorded) |
| Save a meme with an image | Saved, preview shows the new image, but the upload box still listed the file | Confusing (defect 9 from M0) |
| Frames per second tile | Followed the browser's own WebRTC count (`getStats`): tile 4 to 8 against 3 to 5 while the browser pane was in the background, 14 against the stand-in's 15 while it was in front | Measured, not invented |

Fixes:

- Collector: "Start the camera first: press Start camera under the video."
- The retrain hint ends "Train model is on the Model performance page." instead of a second "Retrain".
- Memes page: a successful save starts a fresh form (its widget keys carry a version), which shows the saved text and an empty upload box. A failed save keeps what you typed.

Look again: Save with an image now leaves the upload box empty ("Upload, 10MB per file") with the new image in the preview. The collector warning and the retrain text read as above.

Tests: 3 more in `tests/test_pages.py`, two of them driving the real pages through AppTest (filling and submitting the Memes form; pressing Start recording with the camera off). Suite: 336 passed.

Scores: Interaction 9.2 (record, stop mid-recording, undo, train, save and refuse all ran and recovered). Data truth 9.2 and Flow 8.9 (the wrong camera instruction and the doubled retrain sentence are gone). State 9.0 (Retrain needed, then Loaded, shown the same in both places). Maintainability 9.0 (the form is tested end to end). The weighted score reaches 9.02 with every dimension at 8.5 or more.

### Round M6: error states and consistency

Critique. The error states had only been checked by unit tests. On the scratch copy each was caused on purpose and every page opened:

| Caused | Live dashboard | Other pages | Verdict |
|---|---|---|---|
| `memes.json` cut off halfway | Meme panel: "Meme list unreadable. Memes cannot be shown. Cannot read memes.json: Expecting property name enclosed in double quotes: line 1 column 49 (char 48)" | Memes page shows the same error and no form, so nothing can overwrite the file; collector and performance pages fall back to the gesture ids | Works |
| `meme_3.jpg` moved away | Notice "No usable meme image yet for: Meme 3"; with Meme 3 held in front of the stand-in camera the panel says "Image missing. The image file meme_3.jpg is missing." and shows no other meme | | Works |
| Model files moved away | "No trained model", every statistic n/a, Model "Not trained", Recent detections "Recognition starts once a model is trained." | Performance: "No trained model yet"; the Memes page still works | Works |
| `label_mapping.json` listing 2 of the 5 gestures | "Model cannot be used. label_mapping.json and training_report.json list different gestures. Train the model again." Model "Cannot load" | | Works |

One inconsistency: the performance page wrote its training time as "Trained 2026-10-14 11:55:54" and the recordings as "14 Oct 11:35".

Fixes:

- One time format on the performance page (`stamp`): "Trained 14 Oct 11:55", recordings "14 Oct 11:35 (c79027)".
- README: the collector shows names with ids, Stop camera during a recording keeps the samples, the Top scores panel, the Memes form after a save, and where the 10 MB limit is set.

Look again, all six pages: at 1280px and 390px no sideways scroll (`scrollWidth` 1280 and 390) and no error box. The only console errors on a clean load are the two known 404s for `/<page>/_stcore/health` when a page address is opened directly; Streamlit then asks the right address and gets 200.

Tests: 1 more in `tests/test_pages.py`. Suite: 337 passed.

Scores: State 9.2 (every error state checked in the browser, each distinct, none shows a meme). Maintainability 9.2 (README matches what the pages do). Others unchanged.

## Frontend refinement, 17 October

Done from `docs/frontend-handoff/`. Checked in real Streamlit in the built-in browser at 1280x900 and 390x844, on a scratch copy of `data/` and `models/` (port 8502). The camera was a stand-in: a plain grey canvas with a moving square, no recorded clips, so the live states seen were Camera off, No hand detected, Stop camera, and camera access denied. Recognised and the meme with a held gesture were not re-run; their code did not change.

| Found | Fix | Seen after |
|---|---|---|
| Camera off: the video area was a 152px strip with a small icon, and the panel grew by about 300px when video started, pushing Live statistics down | `_IFRAME_CSS` makes the off and connecting state a 4:3 frame (dashed edge, `--surface2`), the shape the camera is asked for | Frame 593x445 at 1280px and 318x239 at 390px; the iframe stays 497px tall through Start camera, video and Stop camera; the button does not move |
| The camera button had Material's raised shadow, a click ripple and a darker hover, unlike every other green button | No shadow, no ripple, dark text, hover `#45c983` | Computed `box-shadow: none`, hover background rgb(69, 201, 131), text rgb(11, 15, 13) |
| Camera denied showed the library's own dark red box | Same look as the page's red notices | Shown above the frame, not inside it |
| Notices used Streamlit's olive yellow and blue, the only colours outside the palette | `st.warning`, `st.error`, `st.success` and the new `ui.notice` share one look: 1px border, faint tint of the token colour, text `--text` | Performance cautions, legal page banner and dashboard notices |
| Dashboard notices said "Memes page" with no link (Streamlit's notices open links in a new tab) | `ui.notice` with `ui.link('memes', ...)` | Link opens /memes in the same tab |
| Live statistics: "Recognised this session" wraps to two lines, so its value sat 15px lower than its neighbours | Tiles use CSS subgrid | Values in each row start at the same height at 1280px and 390px |
| Model performance showed the tag "softmax regression gradient descent" from the saved model id, against the copy rule | Tag reads "softmax regression" | No "gradient" anywhere in the page text |
| Memes table: twenty plain "Set" / "Not set" words | Tags: Set green, Not set grey, image Missing amber | At 390px the tags became two-line boxes and the table overflowed, so tables tighten under 480px and a tag in a table becomes its coloured word; the table fits (318 of 318px) |
| Memes preview told you to go to the Memes page while on it | `meme_card(..., preview=True)` says "in the form on this page" | |
| Every browser tab was titled "Ball Knowledge Vision AI" | Tab title names the page, "Memes \| Ball Knowledge Vision AI" | All six pages |
| Confusion matrix 3px wider than a phone screen | Tighter spacing under 480px | Every table on the performance page fits at 390px |

Tests: 10 more in `tests/test_pages.py`; `tests/test_style_rules.py` now allows exactly `box-shadow:none !important`. Suite: 387 passed (this includes tests the backend work added the same day).

Not checked: Safari, a screen reader, your webcam.

## Dashboard: memes, not names (17 October, your request)

You asked for the dashboard not to say "Meme 1" or "Meme 2", and to show only the meme for the gesture you hold, beside the camera, with the confidence meter.

- Right column: the Recognition, Meme result and Top scores panels became one **Meme** panel (`ui.result_card`): the meme in a 4:3 frame and the confidence meter under it. Every other state puts a short message in the same frame (Camera off, No hand in view, Unrecognised, Hold it steady, No gesture and the error states), so the panel keeps its size.
- Live statistics "Latest gesture" became "Latest meme" with a small picture; Recent detections show a small picture of each meme instead of its name.
- Removed from the dashboard: the gesture name headline and tags, the Top scores table, the "No Ball Knowledge rating or description yet" notice, and the "not set" lines. Your title, rating and description still appear under the meter once you write them. "Retrain needed" moved to a notice at the top.
- Gesture names remain only where something must be fixed (a gesture with no meme or no image) and on the other pages, where you need them to record, judge and edit.

Checked in real Streamlit at 1280x900 and 390x844 on scratch data, with the camera fed frames from one of your Meme 3 clips (the video was hidden in the page while checking, and the frames were deleted afterwards). Over 9 seconds the panel went No hand in view, Hold it steady (74% to 96%), then the Absolute Cinema meme with the meter at 95% to 98%; Recent detections added one row with the meme's picture. No gesture name appeared. No sideways scroll at 390px.

Tests: the recognition state tests now test `result_card`, including that no state shows a gesture name. Suite: 402 passed.

## After the rounds: your webcam check

On 14 October, on the final version, you checked the website and the webcam yourself and reported that they work properly. You did not go through README steps 1 to 6 one by one. Steps 7 to 9 (save a rating and description, refuse a non-image, see them on the dashboard) were run on a scratch copy and passed; step 9 used the stand-in camera. Results per step: section M of `03_REQUIREMENTS_AND_CHECKLIST.md`. The scores above were not changed for this.

## Unresolved

1. **Step-by-step webcam record** (README, With your webcam, steps 1 to 6), if you want one; your check covered them as a whole.
2. **Screen readers.** No screen reader was available, and a new result is not announced (an ARIA live region inside a panel that redraws twice a second could be read out repeatedly; it needs a screen reader to test).
3. **Safari** was not checked; the camera has only been run in Chrome-based browsers.
4. **Data**: first_meme has 2 recordings; first_meme, meme_3 and second_meme are under 100 samples; all clips were filmed in one room on one day.
5. **Titles, ratings and descriptions** are still empty for all four memes. They are yours to write; nothing was filled in.

