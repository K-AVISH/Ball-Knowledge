# UI critique log: Ball Knowledge Vision AI (Stages 1 to 8 complete)

Six critique-and-improve rounds on the finished app, 14 October 2026. Each round: critique with evidence, fix, run the tests, render the pages, score.

## How this was checked, and its limits

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

## Scores

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

Measured contrast (WCAG formula) for the palette: body text 16.1:1, muted text 5.9 to 6.6:1, tags 5.0 to 7.9:1, button text 7.9:1, links 7.6:1. All pass AA except **white numbers on the darkest confusion-matrix cells: 3.13:1 on green**. The shading is now capped (alpha 0.55), giving 4.66:1 on green and 5.98:1 on red. Test: `test_confusion_matrix_numbers_keep_aa_contrast_on_the_darkest_cells`.

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

## Unresolved

1. Camera, landmarks and live recognition have not been run on your webcam (README, Test the whole pipeline, With your webcam).
2. The Memes page has not been run in real Streamlit. Check: save text, upload an image, upload a non-image, switch gesture.
3. No keyboard or screen-reader pass in a real browser. The live panels are not announced to screen readers (an ARIA live region would re-read the panel every 0.5 s).
4. Data: first_meme has 2 recordings; first_meme, meme_3 and second_meme are under 100 samples; all clips were filmed in one room on one day.
5. Titles, ratings and descriptions are still empty. They are yours to write; nothing was filled in.
