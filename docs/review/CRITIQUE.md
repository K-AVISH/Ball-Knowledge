# Page critique: Ball Knowledge Vision AI

Critic: Claude Code session, 18 October 2026, after the code review in the same session (the owner
confirmed no other session works in the folder, and asked for both jobs, the review first). Process:
`Code Reviewer/PAGE_CRITIC_PROMPT.md` (six rounds, the rubric of `docs/ui-critique-log.md`, the
gate). Start tag: `page-critique-start-2026-10-18` at `8d02521`. File and line numbers in the
findings refer to the code at that tag.

## Summary for the owner

_Kept up to date after each round. Last updated: round 7, made on the branch
`claude/review-items-25418b`, which you merged into `main` on 18 October._

| Round | Critical | High | Medium | Low | Fixed | Proposals | Not confirmed | Weighted |
|---|---|---|---|---|---|---|---|---|
| Baseline | | | | | | | | 8.46 |
| 1 | 1 | 0 | 4 | 1 | 1 | 5 | 1 | 8.50 |
| 2 | 0 | 0 | 2 | 1 | 2 | 1 | 0 | 8.57 |
| 3 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 8.63 |
| 4 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 8.66 |
| 5 | 0 | 1 | 2 | 3 | 3 | 2 | 0 | 8.70 |
| 6 | 0 | 1 | 2 | 0 | 1 | 2 | 0 | 8.70 |
| 7 (branch) | 0 | 0 | 0 | 3 | 0 | 1 | 1 | 9.07 |

Gate status after round 6: **not met**. The weighted score is 8.70 (8.695), under 9.0; Recognition
and data state is 8.2, under 8.5. Flow and action clarity (8.6) is held back by the messages in
PR-4, PR-7, PR-8, PR-12 and PR-13.

After round 6 (18 October) you answered `OWNER_QUESTIONS.md` Q6 / proposal PR-1 with option A: a
gesture with no usable meme picture may be listed by name (or id) in Recent detections and the
Latest meme tile. The rule now lists that exception, so the Critical-scale finding P1-5 is closed
and no Critical or High finding is open. The scores above were not measured again after the
answer, so they still count P1-5; Recognition and data state was held at 8.2 mainly because of it.
Twelve proposals still wait for you in `CRITIQUE_PROPOSALS.md`.

Gate status after round 7: **met.** At your request the recommended option of each open question
and proposal was built on the branch `claude/review-items-25418b`, one commit per item (round 7
below lists them), and the pages were scored again with them: weighted **9.07**, every dimension at
least 8.7, no open Critical or High finding, 492 tests passing, your files unchanged. You merged the
branch into `main` on 18 October as it was, so this result now holds on `main`: 512 tests passed
there while the branch's worktree still sat inside the project folder (the em-dash check read its
20 files too), and 492 after the worktree and branch were removed on 19 October. The score holds only while the commits that carry it
stay; the ones that moved it most are Q1, PR-2, PR-3, PR-4, PR-12 and PR-13. Round 7 found three Low
findings and one new proposal (PR-14, a wording choice); you chose its option B on 19 October and
it is built on `main`, which closes P7-2.

## How the pages were checked

- Streamlit 1.65 from the project `.venv` on port 8502 (it now listens on localhost only), with the
  scratch copies `/tmp/bk-critic/data` and `/tmp/bk-critic/models`, or variants of them per state;
  meme-file states on a project copy in `/tmp/bk-critic-copy` without the videos, screenshots or
  archive. Your port 8501 was not touched.
- The built-in browser of the Claude desktop app (Chromium), sized with its viewport tool. Its pane
  was hidden for this pass; the stand-in still ran at 13 to 15 frames per second (Frames per second
  tile and the browser's own count).
- Stand-in camera as in the critic prompt: frames from one clip per gesture, extracted into
  `/tmp/bk-critic/frames` and served on `127.0.0.1:8765` only. No screenshot with camera video was
  saved in the project. One browser screenshot in round 6 showed a frame of a clip; the browser
  tool kept it in the Claude session folder outside the project, and it was deleted the same day.
  Evidence is measured text, positions (`getBoundingClientRect`) and colours (`getComputedStyle`
  with the WCAG formula, against the colour really behind the text).
- Your files: SHA-256 of `data/`, `models/` and `assets/memes/` files taken at the start
  (`/tmp/bk-critic-hashes-start.txt`) and checked in the project folder.

## Baseline (round 1 critique, before any change)

### States reached (critic prompt section 8)

| State | How | What the Meme panel and the page showed |
|---|---|---|
| Camera off | page load | "Camera off. Press Start camera. The meme for the gesture you show appears here.", meter n/a; tag "Camera off" |
| Waiting for video | a canvas never drawn on | "Waiting for video" for the whole 8 s; tag "Connecting" |
| No hand in view | `meme_3` clip between holds | "No hand in view" |
| Hold it steady | `meme_3` and `first_meme` clips | "Hold it steady", meter 84% to 99% (green) for 0.3 to 0.5 s |
| Unrecognised | `meme_3` (12.6 s), `none` (4.9 s) | "Unrecognised", meter 58% and 50% (amber) |
| The meme | each gesture's clip | its meme with its title: Stressed Higuruma, Peace Out, Absolute Cinema, I Guess Bro; meter 85% to 99%; alt text "Meme: <title>" |
| No gesture | `none` clip | "No gesture" for most of the clip; never a meme; Recent detections stayed empty |
| Switching gestures | clip changed mid-stream (middle of each clip) | the new meme after 782, 827, 1,007 and 1,397 ms; the old meme stays until then; never a third meme |
| Stop camera | Stop camera | Meme panel "Camera off", Frames per second and Latency n/a, Recent detections kept (README says it is kept). Defect P1-1 |
| No trained model | empty model folder | "No trained model" with links to Data collector and Model performance (same tab); every tile n/a; Model "Not trained"; Model performance "No trained model yet" |
| Model cannot be used | `gesture_model.joblib` cut to 1,000 bytes | "Model cannot be used" and the reason (184 px of text inside the 278 px frame; 238 px frame at 390 px, 27 px to spare); Model "Cannot load". Model performance silent: P1-3 |
| Retrain needed | last line of `samples.csv` deleted | amber notice "The dataset has changed since this model was trained (380 samples then, 379 now). Train again to include the changes. Train model is on the Model performance page." with an in-tab link; the same first sentence on Model performance; Model tile "Retrain needed" |
| No meme set | copy: `first_meme` record removed | "No meme set. first_meme has no meme yet. Add one on the Memes page, or with python dataset_manager.py first_meme --image <file>."; notice "No usable meme image yet for: first_meme" |
| Image missing | copy: `meme_3.jpg` deleted | "Image missing. The image file meme_3.jpg is missing. Choose the image again on the Memes page."; notice for Meme 3 |
| Memes cannot be shown | copy: `memes.json` cut to 120 bytes | Meme panel says why (fits: 140 px in a 278 px frame, 238 px at 390 px); Memes page shows the error and no form; collector and Model performance fall back to ids |
| Training in progress | Train model on a scratch model folder | button disabled, "Training: 4 of 97 models trained ..."; after 36.3 s "Trained in 2658 steps. Held-out accuracy 97.1% on 380 samples from 16 recordings. ..." once; button enabled again |
| Collector countdown, recording, finished | Start recording with the `first_meme` clip | 3, 2, 1; "Recording First meme: N of 100 samples" with the bar; "No hand in view, so sampling is paused. K empty frames skipped." between holds; "Saved 100 samples for First meme." after 23.8 s; one button reads Start, then Stop, then Start |

### Measurements

| What | Result |
|---|---|
| Meme panel with a title, 1280x900 (`meme_3` held) | Image 281 to 560 px (900x649 sent, shown 371x268), title 618 to 646 px, panel bottom 663 px: as measured on 18 October. In full view |
| Camera panel | 710 px tall with the camera off (iframe 497 px, a 4:3 frame); 661 px with the stand-in's 3:2 video (iframe 448 px). See P1-7 |
| Phone, 390x844 (`meme_3` held) | Stacked: camera 288 to 766, Meme 782 to 1168 (image 827 to 1065), Live statistics 1184 to 1612, Recent detections 1628 to 1939; 16 px gaps, 16 px side gutters; `scrollWidth` 390; nothing overflows. See P1-6 |
| Contrast, every visible text, all six pages at 1280x900 | No text under 4.5:1. Lowest: 4.73:1 (red "Needs samples" tags, collector), 4.8:1 (confusion matrix numbers), 5.91:1 (tile labels, "Not set" tags), 6.64:1 (legal pages). The slider value "100" first measured 1:1: it sits above the handle (469 to 491 px, handle 491 to 503 px), green on the panel, 7.56:1 |
| Frames per second | 13 to 15 with the pane hidden |
| Console | Only `/<page>/_stcore/health` and `/<page>/_stcore/host-config` 404s when a page address is opened directly, and `ERR_CONNECTION_REFUSED` only while Streamlit was being restarted |

### Scores before any change

| Dimension | Weight | Score | Evidence |
|---|---|---|---|
| Data truth | 25% | 8.5 | Every number traced (the report was recomputed independently in the code review, round 5). Untrue in some states: "Starting ... classifying" while the hand model is missing (code review R1-5), "The meme appears ..." for a relaxed hand (P1-2), "Record your gestures" when they are recorded (P1-4); Model performance silent about an unusable model (P1-3) |
| Recognition and data state | 20% | 8.0 | All 16 states reached and distinct, none shows a wrong meme; a stale hand tag after Stop camera (P1-1); gesture names in Recent detections when a meme image is missing (P1-5) |
| Flow and action clarity | 15% | 8.5 | Every link opens in the same tab; messages say what to do; P1-4; leaving the collector mid-recording (code review R1-4) |
| Visual hierarchy and brand | 15% | 8.5 | The meme in full view beside the video at 1280x900; below the first screen on a phone (P1-6); flat dark style throughout |
| Interaction reliability | 10% | 8.5 | Record, stop, train and Start/Stop camera work; Memes saving and two tabs not yet run (round 6) |
| Accessibility and responsive | 10% | 8.8 | No text below AA; focus rings on links and the green buttons (code review checks); no sideways scroll at 390 px; no screen reader to test |
| Maintainability | 5% | 9.0 | Display code in `ui.py`, page tests, documents kept up with the code review |
| **Weighted** | | **8.46** | |

## Round 1

### Findings

| ID | Sev. | Area | Page | State | Size | What was seen | How measured | File and line | Fix or proposal | Test added | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P1-5 | Critical | Frontend (owner decision) | Live dashboard | a recognised gesture without a usable meme image; `memes.json` unreadable | 1280x900 | Recent detections "14:29:23 first_meme 92%", Latest meme "first_meme at 14:29:23"; "Meme 3" with its image missing; "meme_3" with `memes.json` broken | page text, project copy, stand-in camera | `ui.py:484-498` (`meme_thumb`) | Proposal PR-1 (code review Q6). Not fixable by the critic: three tests fix the current text (rule 2) and the replacement is wording (rule 4) | none | Closed: you allowed it (Q6, option A, 18 October) |
| P1-1 | Medium | Frontend | Live dashboard, Data collector | just after Stop camera | 1280x900 | "Camera off" beside "2 hands detected" for about 640 ms | tags polled every 100 ms: 211 ms "Camera off,2 hands detected", 848 ms "Camera off" | `ui.py:765-771` (`hand_tag`) | Hand tag only while frames arrive (a stale result after Stop camera is a broken state) | `test_no_hand_tag_once_the_camera_is_off` | Fixed |
| P1-2 | Medium | Frontend (owner decision) | Live dashboard | relaxed hand, frame recognised as `none` | 1280x900 | "Hold it steady. The meme appears once ..." and a green 91% meter, then "No gesture" | Meme panel polled every 100 ms (8,922 ms, then 9,449 ms) | `ui.py:595-599` (`result_card`, last branch) | Proposal PR-2 | none | Proposal |
| P1-3 | Medium | Frontend (owner decision) | Model performance | model file unusable | 1280x900 | Full results, no warning, while the dashboard says "Model cannot be used" | page text with `models-broken` | `views/performance.py:47-51` | Proposal PR-3 | none | Proposal |
| P1-6 | Medium | Frontend (owner decision) | Live dashboard | a gesture held | 390x844 | The meme image starts at 827 px; 17 px of it in the first screen | `getBoundingClientRect` | `views/dashboard.py:81` (column order) | Proposal PR-5 | none | Proposal |
| P1-4 | Low | Frontend (owner decision) | Live dashboard, Model performance | no model, samples recorded | 1280x900 | "Record your gestures ..." / "Record at least two gestures ..." though 380 samples of 5 gestures exist | page text with `models-empty` | `ui.py:567-569`, `views/performance.py:128-134` | Proposal PR-4 | none | Proposal |
| P1-7 | n/a | Frontend | Live dashboard | camera off, then live | 1280x900 | The camera panel shrinks 49 px when video starts (710 to 661 px) | `getBoundingClientRect` | `ui._IFRAME_CSS` | The stand-in sends 3:2 video; a 4:3 webcam fills the same 4:3 frame as the placeholder, so this cannot be judged without one | none | Not confirmed |

### Checks

| Check | Method | Result |
|---|---|---|
| Fix before and after | `pytest -q -p no:cacheprovider tests/test_status.py::test_no_hand_tag_once_the_camera_is_off` | failed before the fix ("2 hands detected" with the camera off), passed after; `tests/test_status.py tests/test_pages.py` 103 passed |
| Fix in the browser | Streamlit restarted; 3 cycles of Start camera, hand in view, Stop camera, tags polled every 50 ms | each time straight from "Camera connected,2 hands detected" to "Camera off" (102, 157, 163 ms) |
| Test suite | `.venv/bin/python -m pytest -q` | **446 passed in 72.15 s** |
| Owner's files | `shasum -a 256 -c /tmp/bk-critic-hashes-start.txt` in the project folder | 10 of 10 OK |

### Scores after round 1

| Dimension | Weight | Score | Evidence this round |
|---|---|---|---|
| Data truth | 25% | 8.5 | No change; P1-2, P1-3, P1-4 are proposals |
| Recognition and data state | 20% | 8.2 | The stale hand tag is gone (measured); P1-5 open |
| Flow and action clarity | 15% | 8.5 | No change |
| Visual hierarchy and brand | 15% | 8.5 | No change |
| Interaction reliability | 10% | 8.5 | No change |
| Accessibility and responsive | 10% | 8.8 | No change |
| Maintainability | 5% | 9.0 | A test for the fix |
| **Weighted** | | **8.50** | |

Commit: `2cf370a` (message "Page critique round 1: baseline of every page and state").

## Round 2: data truth and state

Every page again at 1280x900 and 390x844, with the stand-in camera on the dashboard. Every number
traced to its source; every state compared wherever it appears; the 0.5 s refresh watched for
flicker; what Stop camera clears.

### Findings

| ID | Sev. | Area | Page | State | Size | What was seen | How measured | File and line | Fix or proposal | Test added | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P2-1 | Medium | Frontend | Model performance | trained model | 1280x900 | Confidence cutoff: "Accepted 100%" at the 50% cutoff; the report says 0.9974 (1 of 380 rejected). The Correct column beside it uses one decimal | page table read in the browser against `training_report.json` formatted the page's way | `views/performance.py:207` | One decimal, as Correct (false number fixed; listed for the owner) | `test_the_cutoff_table_never_rounds_a_share_up_to_all` | Fixed |
| P2-3 | Medium | Frontend (owner decision) | Live dashboard | hand model missing | 1280x900 | "Starting. The model is classifying the first frames." for 9 s beside "Hand model missing" | Meme panel and tags polled every 100 ms, project copy | `ui.py:579-580` | Proposal PR-6 (code review Q1) | none | Proposal |
| P2-2 | Low | Frontend | Live dashboard, Data collector | hand model missing | 1280x900, 390x844 | "ModelMissingError: Hand model not found at ... Run: python download_models.py The camera picks ..." | hint text in the browser | `ui.py:751-753` | Python error name dropped and the sentence ended (listed for the owner) | `test_missing_hand_model_hint_names_no_python_error_and_ends_its_sentence` | Fixed |
| P2-4 | Nit | Backend | Model performance | a recording predicted with certainty | test data | Its cost can show as "-0.000" (minus zero) | AppTest page text on the synthetic test project | `train_model.py:190` (`per_recording`) | Not fixed (Nit; the real recordings' costs are 0.002 and up) | none | Not fixed |
| P2-5 | Nit | Frontend | Live dashboard | camera on | any | "Latency 11.1 ms" is the server's processing time per frame; the tile does not say so | `vision.FrameProcessor.process` | `views/dashboard.py:152` | Not fixed (Nit) | none | Not fixed |

### Every number traced (no finding unless listed above)

| Page | Numbers | Source | Result |
|---|---|---|---|
| Model performance | tags, four tiles, per-gesture table (25 values), confusion matrix (25), mix-ups (5 rows), cutoff table (15), each recording (16 rows x 4), final model table (5), penalty table (6 rows x 3) | `training_report.json`, formatted the page's way in Python; recording times from `samples.csv` | All equal (P2-1 apart). The report itself was recomputed independently in the code review, round 5 |
| Data collector | 380 samples, 5 gestures; per gesture samples, recordings, hint and bar width (58/2/19%, 48/3/16%, 127/4/42%, 119/4/40%, 28/3/9%) | `DatasetStore.summary()` and `class_status` on the scratch `samples.csv` | All equal |
| Memes | Set and Not set for image, title, rating, description | `memes.json` | All equal: images and titles set, ratings and descriptions not set |
| Live dashboard | Gesture classes 5; Recognised this session equal to the rows in Recent detections; Frames per second 13 to 15 for a 15 fps stand-in; confidence equal to the mean of the voting frames (code review) | model labels, `DetectionLog`, `VisionStats` | Consistent |

### State checks

| Check | Result |
|---|---|
| Flicker on the 0.5 s refresh | 12 s of a steady hold (the middle of the `meme_3` clip, hand always in view), polled every 100 ms: the meme in all 114 polls, the hand tag "2 hands detected" in all 114 |
| Stop camera clears old results | Meme panel "Camera off", Frames per second and Latency n/a, hand tag gone (after P1-1); Recent detections kept on purpose (README) |
| The same state everywhere | "Retrain needed": the same sentence on the dashboard and Model performance, and the Model tile. "No gesture" on every page for `none`. Camera tag and Meme panel agree on Camera off, Connecting / Waiting for video, Camera connected |
| Recovery | Hand model put back while the camera ran: the meme 0.6 s later, no reload, as the hint says |

### Checks

| Check | Method | Result |
|---|---|---|
| New tests | the two new tests with and without the fixes (`git stash`) | 2 failed without, 158 passed with (`test_status.py`, `test_pages.py`, `test_style_rules.py`) |
| Browser after the fixes | Streamlit restarted (project and copy) | Cutoff column "99.7%, 98.2%, 95.8%, 91.6%, 82.4%", table fits at 390 px (318 of 318 px); hint "Hand model not found at ... Run: python download_models.py. The camera picks ...", wraps inside the panel at 390 px, `scrollWidth` 390 |
| Test suite | `.venv/bin/python -m pytest -q` | **448 passed in 71.18 s** |
| Owner's files | `shasum -a 256 -c /tmp/bk-critic-hashes-start.txt` in the project folder | 10 of 10 OK |

### Scores after round 2

| Dimension | Weight | Score | Evidence this round |
|---|---|---|---|
| Data truth | 25% | 8.8 | Every number on every page traced and equal; the one false number fixed; the false "Starting" sentence (P2-3) and P1-2, P1-3, P1-4 wait for the owner |
| Recognition and data state | 20% | 8.2 | No flicker; old results cleared; states agree across pages; P1-5 open |
| Flow and action clarity | 15% | 8.5 | The missing-model hint now reads as an instruction |
| Visual hierarchy and brand | 15% | 8.5 | No change |
| Interaction reliability | 10% | 8.5 | No change |
| Accessibility and responsive | 10% | 8.8 | No change |
| Maintainability | 5% | 9.0 | Two more tests |
| **Weighted** | | **8.57** | |

Commit: `944ce39` (message "Page critique round 2: data truth and state").

## Round 3: flow and action clarity

A first-time user without a terminal, on a project copy with no samples, no model and no memes
(`/tmp/bk-critic-copy` with empty data and model folders), at 1280x900, the stand-in camera for
recording and for the end check. Every click went through the page's own links and buttons.

### The journey

| Step | What the page said and did | Verdict |
|---|---|---|
| Open the dashboard | Meme panel "No trained model. Record your gestures on the Data collector page, then train on the Model performance page."; Recent detections "Recognition starts once a model is trained." | Says what to do |
| Click "Data collector" in that message | `/collector` opened in the same tab | Works |
| Collector, empty | "No samples yet. Record your first gesture above."; Start recording disabled | P3-2 |
| Type "Open palm", Enter | Caption "Saved as open_palm"; Start recording enabled | Works |
| Slider to 20 (keyboard: Home), Start camera, Start recording, twice | Countdown, recording, "Saved 20 samples for open_palm." each time; the gesture box then shows `open_palm` for the next recording; "Add at least 2 gestures before training." | Works |
| Choose "New gesture...", type "Fist", record twice | "Saved 20 samples for fist." twice; "80 samples, 2 gestures"; the hint about 2 gestures disappears | No pointer to training: P3-1 |
| Top navigation, Model performance | "No trained model yet. Record at least two gestures on the Data collector page, then press Train model." (P1-4: they are recorded) | Works |
| Train model | After 2 s: "Trained in 343 steps. Held-out accuracy 98.8% on 80 samples from 4 recordings. The Live dashboard uses the new model the next time it loads."; cautions name the next steps (more sessions; record a `none` gesture) | Says what to do |
| Top navigation, Memes | Table: both gestures Missing / Not set; preview "No meme set ... Add one in the form on this page" | Says what to do |
| Upload a test image, type a test title, Save meme (copy only; test text) | "Saved the meme for fist. The Live dashboard shows it the next time this gesture is recognised."; table Set; preview shows the image and the title; upload box empty again ("Replace the image") | Works |
| Top navigation, Live dashboard, show the gesture | Model "Loaded" without a restart; the test meme after 2.9 s with its title, alt "Meme: Test title"; Recent detections one row with its picture; notice "No usable meme image yet for: open_palm. Add one on the Memes page." | Works |
| Click "Memes" in that notice | `/memes` opened in the same tab | Works |

Every link used opened the right page in the same tab: the Meme panel's two links, the notice's
link, the retrain notice's link (`target="_self"`, round 1) and the top navigation.

### Findings

| ID | Sev. | Area | Page | State | Size | What was seen | How measured | File and line | Fix or proposal | Test added | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P3-1 | Low | Frontend (owner decision) | Data collector | data ready to train | 1280x900 | No pointer to training once 2 gestures have 2 recordings each | the journey above, page text | `views/collector.py:221-223` | Proposal PR-7 | none | Proposal |
| P3-2 | Low | Frontend (owner decision) | Data collector | "New gesture..." with no name | 1280x900 | Start recording disabled with no reason given | button state and page text | `views/collector.py:180-181` | Proposal PR-8 | none | Proposal |
| P3-3 | Nit | Frontend | Memes | no `none` gesture recorded | 1280x900 | The note about "No gesture (the none gesture)" shows although that gesture does not exist yet | page text | `views/memes.py:80-83` | Not fixed (Nit) | none | Not fixed |

### Checks

| Check | Method | Result |
|---|---|---|
| Every page, 390x844 | Streamlit restarted on the project; `scrollWidth`, error boxes | All six: no Python error, no sideways scroll |
| Test suite | `.venv/bin/python -m pytest -q` | **448 passed in 71.07 s** (no code change this round) |
| Owner's files | `shasum -a 256 -c /tmp/bk-critic-hashes-start.txt` in the project folder | 10 of 10 OK |

### Scores after round 3

| Dimension | Weight | Score | Evidence this round |
|---|---|---|---|
| Data truth | 25% | 8.8 | No change |
| Recognition and data state | 20% | 8.2 | No change; P1-5 open |
| Flow and action clarity | 15% | 8.7 | The whole journey done without a terminal; every message on the way named the next step except two small gaps (P3-1, P3-2) |
| Visual hierarchy and brand | 15% | 8.5 | No change |
| Interaction reliability | 10% | 8.8 | Four recordings, a training run and a meme save with an upload all behaved; the form reset after saving |
| Accessibility and responsive | 10% | 8.8 | No change |
| Maintainability | 5% | 9.0 | No change |
| **Weighted** | | **8.63** | |

Commit: `d918f6a` (message "Page critique round 3: flow and action clarity").

## Round 4: visual hierarchy and brand

Every page at 1440x900, 1280x900, 1024x768, 768x1024 and 390x844 (the dashboard with `meme_3` held
by the stand-in camera at each size). Each page was reloaded after a size change: with the pane
hidden the page does not re-measure itself on a resize (see P4-2).

### The dashboard at each size (meme held)

| Size | Columns (left, right) | Meme image | In the first screen | Rows aligned | Sideways scroll |
|---|---|---|---|---|---|
| 1440x900 | 640, 416 px (content centred at its 1,280 px maximum) | 376 px wide, 281 to 563 px | yes | yes (second row 640 and 416 px, same edges) | no |
| 1280x900 | 633, 412 px | 371 px wide, 281 to 560 px | yes | yes | no |
| 1024x768 | 480, 309 px | 269 px wide, 281 to 483 px | yes | yes | no |
| 768x1024 | 403, 258 px | 218 px wide, 281 to 445 px | yes | yes | no |
| 390x844 | stacked, 358 px | 318 px wide, 827 to 1065 px | no (17 px) | stacked in order | no |

The meme is the first result at every size except the phone (P1-6, PR-5). At every two-column size
the Meme panel's top is level with the camera panel's, and the statistics row uses the same split.

### The same components on every page (1280x900, computed styles)

| Component | Dashboard, Data collector, Model performance, Memes |
|---|---|
| Cards and widget panels | background `rgb(17, 24, 21)` (`--surface`), 1 px border `rgb(33, 44, 38)` (`--border`), radius 8 px, padding 16 px by 19.2 px: one value on all four pages |
| Page title | 28 px, weight 650, `--text` |
| Card titles | 11.84 px, weight 650, `--muted`, uppercase, letter spacing 1.184 px |
| Hints | 14.08 px, `--muted` |
| Tags | 12.48 px, radius 4 px |
| Table headers | 11.52 px, `--muted`, uppercase (Model performance and Memes) |
| Space between stacked panels | 16 px everywhere (collector 2 gaps, Model performance 4, Memes 1, dashboard 1) |

All values match `DESIGN_SYSTEM.md` sections 1 and 2. The style rules hold (`tests/test_style_rules.py`
passes): no gradient, shadow, pill, purple or emoji; one green accent.

### Findings

| ID | Sev. | Area | Page | State | Size | What was seen | How measured | File and line | Fix or proposal | Test added | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P4-1 | Low | Frontend (owner decision) | Live dashboard | meme held | 1440x900, 1280x900 | The right column ends 236 px (1440) and 235 px (1280) above the camera panel | `getBoundingClientRect` | `views/dashboard.py:81-127` | Proposal PR-9 (recommends keeping it) | none | Proposal |
| P4-2 | n/a | Frontend | Live dashboard | camera live, window resized without reload | 1024 to 1440 | The camera frame kept its old size (439x345 px, `width` attribute 439.42) 6 s after widening | iframe size and attributes | streamlit-webrtc component sizing | Streamlit resizes component frames from a resize observer, which does not run while the browser pane is hidden; cannot be judged here | none | Not confirmed |

### Checks

| Check | Method | Result |
|---|---|---|
| Sizes | five sizes above, reload after each | no sideways scroll, no Python error |
| Test suite | `.venv/bin/python -m pytest -q` | **448 passed in 71.83 s** (no code change) |
| Owner's files | `shasum -a 256 -c /tmp/bk-critic-hashes-start.txt` in the project folder | 10 of 10 OK |

### Scores after round 4

| Dimension | Weight | Score | Evidence this round |
|---|---|---|---|
| Data truth | 25% | 8.8 | No change |
| Recognition and data state | 20% | 8.2 | No change; P1-5 open |
| Flow and action clarity | 15% | 8.7 | No change |
| Visual hierarchy and brand | 15% | 8.7 | The meme first and in view at four of five sizes; one component style, type scale and 16 px spacing on every page, measured; the phone (PR-5) and the band beside the camera (PR-9) remain |
| Interaction reliability | 10% | 8.8 | No change |
| Accessibility and responsive | 10% | 8.8 | No sideways scroll at five sizes |
| Maintainability | 5% | 9.0 | No change |
| **Weighted** | | **8.66** | |

Commit: `f3da03f` (message "Page critique round 4: visual hierarchy and brand").

## Round 5: accessibility and responsive

Every page at 1280x900, 640x450 (a 1280x900 window at 200% zoom) and 390x844. No screen reader is
available here, so what one would announce was not tested. The names below come from the DOM and
the accessible name rules, not from a screen reader.

### Keyboard pass (Tab, Shift+Tab, Enter and Space, focus logged as it moved)

| Page | Order | Focus shown | Result |
|---|---|---|---|
| Live dashboard | six page links, page area, Start camera (in its frame), Show landmarks overlay, its help icon, back to the links | 2 px green outline on links and the page area; the camera button's ring; the checkbox nothing before the fix (P5-1) | no trap; Space turns the overlay off and on again, focus stays on it |
| Data collector | links, page area, Start camera, Gesture, Recorded by, help icon, Samples slider, Start recording, Manage data, Undo last recording, gesture to delete, confirmation checkbox | text boxes and the select turn their border green (`rgb(47, 191, 113)`), the slider thumb a green halo, buttons a ring; the confirmation checkbox nothing before the fix (P5-1) | no trap |
| Model performance | links, page area, Train model, the seven table regions | 2 px green outline on each | no trap |
| Memes | links, page area, the table region, Gesture, each form field with its help icon, Upload, Save meme, back to the links | rings on links, the region, help icons and buttons; text boxes turn their border green about 0.3 s after focus (Streamlit's own) | no trap |
| Privacy policy, Terms and conditions | links, page area, (Terms) the privacy policy link in the text | 2 px green outline | no trap; Enter on a link opens the page in the same tab |

### Other checks

| Check | Method | Result |
|---|---|---|
| Headings | visible `h1` to `h6` on all six pages | one `h1` per page, then `h2`s; no level skipped |
| Table captions | a `caption` in every `table` | 8 of 8 (Model performance 7, Memes 1) |
| Labels | every input, text area and select has `aria-label` or a label | all six pages |
| Alt text | every `img` | without a camera, one image (the Memes preview, alt "Meme: " and its title); the dashboard's meme alt was checked in round 3 |
| Text contrast | every element with its own text on all six pages at 1280x900, WCAG formula against the colour really behind it (alpha blended) | all at least 4.5:1 (3:1 for large text); notices 14.3:1. Two flags checked by eye: the disabled "Delete gesture data" button (3.39:1; disabled controls are exempt) and the slider value "100", whose DOM parent is the green thumb but which is drawn above it, on the panel |
| Target size | every control under 24x24 px: distance from its centre to the nearest other control (12 px needed) | the 16x16 help icons are 17 to 30 px from the nearest control; the overlay's help icon sits inside the checkbox's own label (P5-4) |
| 200% zoom (640x450) | `scrollWidth`, any element past the right edge, fixed or sticky elements | no sideways scroll on any page; nothing fixed or sticky covers content; the page links move into a menu (P5-3) |
| Stacked order at 390x844 | panel positions | Data collector: camera 288 to 758, tips 774 to 1156, record 1172 to 1526, dataset 1542 to 2417 (P5-5). Dashboard as in round 4 |
| Button names | DOM | Streamlit writes `aria-label=""` on its buttons; the name rules skip an empty label, so a button is named by its text ("Save meme"). The browser tool lists these buttons, and every link, without a name: a limit of that tool. Two names come from icon text (P5-6) |

### Findings

| ID | Sev. | Area | Page | State | Size | What was seen | How measured | File and line | Fix or proposal | Test added | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P5-1 | Medium | Frontend | Live dashboard, Data collector | any | 1280x900 | Neither checkbox (Show landmarks overlay, the delete confirmation) showed keyboard focus. Streamlit keeps the input in a 1 px clipped box, and the visible 16x16 box did not change | focus logged (`:focus-visible` true), computed outline of the box `none` | `ui.py` CSS | The visible box gets the 2 px `--accent` outline, offset 2 px, while the input has keyboard focus. After: `solid 2px rgb(47, 191, 113)`, offset 2 px | `test_checkboxes_show_keyboard_focus` | Fixed |
| P5-2 | High | Frontend | Live dashboard | any | 1280x900 | Show landmarks overlay ignored every second click: from off, four clicks on its label gave on, on, off, off. Its default is the camera's current setting, and without a key Streamlit 1.65 counts a changed default as a new checkbox, which starts at that default | state logged 2 s after each click; Streamlit's `checkbox.py` (`compute_and_register_element_id`, `key_as_main_identity=True`) | `views/dashboard.py:88-91` | `key="show_landmarks"`, so it stays one checkbox. After: from on, four clicks give off, on, off, on; the choice is kept after visiting Memes and coming back, and the next click works. Listed for the owner (critic rule 3, something broken) | `test_the_landmarks_overlay_box_changes_at_every_click` (the first AppTest run of the dashboard) | Fixed |
| P5-3 | Medium | Frontend | every page | page menu closed | 640x450, 390x844 | In a narrow window the page links move into a menu that Streamlit slides 300 px off screen when closed. The first six Tab stops were those links, at x = -280 and out of view; at 390 px also the menu's close button, at x = -270 | focus logged with positions; `transform` and `visibility` of `stSidebar` | `ui.py` CSS | The closed menu and everything in it get `visibility: hidden`. After: the first stop is the visible menu button, then the page; opened, the menu shows its six links and its close button; a link opens its page and the menu closes and hides again. 1280x900 unchanged (top navigation, no menu) | `test_the_closed_page_menu_takes_no_keyboard_focus` | Fixed |
| P5-4 | Low | Frontend (owner decision) | Live dashboard | any | 1280x900 | A mouse click on the help icon beside Show landmarks overlay also flips the checkbox (seen before and after the P5-2 fix). Streamlit puts the icon inside the checkbox's label, so the 16x16 icon is also inside the checkbox's click area. Enter on the icon shows the tip and flips nothing | clicks logged with their target and the state after; Enter from the keyboard | `views/dashboard.py:88-91` (`help=`) | Proposal PR-10 | none | Proposal |
| P5-5 | Low | Frontend (owner decision) | Data collector | recording | 390x844 | Stacked, the tips panel sits between the camera and the record panel: Start recording is at 1469 px, the camera panel at 288 to 758 px, where the 3 s countdown and the progress show. You press Start recording and scroll up to see the countdown | `getBoundingClientRect` | `views/collector.py:73-191` (left column camera and tips, right column record and dataset) | Proposal PR-11 | none | Proposal |
| P5-6 | Low | Frontend (Streamlit) | every page; Memes | menu open; upload box | 640x450, 390x844; 1280x900 | (a) After Enter opens the menu, the next Tab goes to the page: in Streamlit's order the links come before the menu button, and Shift+Tab reaches them (in view, with a ring). (b) Two Streamlit buttons are named by their icon text: the menu button "keyboard_double_arrow_right" and the upload button "upload Upload" | focus logged; DOM | Streamlit 1.65 | No change: neither can be set from the page's CSS | none | Open (Streamlit) |

### Checks

| Check | Method | Result |
|---|---|---|
| Failing first | each new test run before its fix | 3 failed, then passed after the fix |
| Browser after the fixes | Streamlit restarted on the project with scratch data | P5-1 ring measured on the overlay box; P5-2 four clicks off, on, off, on and kept across pages; P5-3 first stop the menu button at 640 and 390 px, menu opens, shows and closes |
| Test suite | `.venv/bin/python -m pytest -q` | **451 passed in 71.70 s** (448 before, 3 added) |
| Owner's files | `shasum -a 256 -c /tmp/bk-critic-hashes-start.txt` in the project folder | 10 of 10 OK |
| Docs | `DESIGN_SYSTEM.md` focus paragraph, frontend `ARCHITECTURE.md` (camera panel, tests) | updated |

### Scores after round 5

| Dimension | Weight | Score | Evidence this round |
|---|---|---|---|
| Data truth | 25% | 8.8 | No change |
| Recognition and data state | 20% | 8.2 | No change; P1-5 open |
| Flow and action clarity | 15% | 8.7 | No change |
| Visual hierarchy and brand | 15% | 8.7 | No change |
| Interaction reliability | 10% | 8.9 | The overlay checkbox changes at every click (P5-2); the help icon still flips it (P5-4) |
| Accessibility and responsive | 10% | 9.1 | Keyboard pass on all six pages with focus shown at every stop after P5-1 and P5-3; contrast, headings, captions, labels, targets and 200% zoom measured; no screen reader; P5-4 and P5-6 open |
| Maintainability | 5% | 9.0 | No change |
| **Weighted** | | **8.70** | |

Commit: `4b03bd1` (message "Page critique round 5: accessibility and responsive").

## Round 6: interaction reliability, then a final full pass

At 1280x900 with the stand-in camera, scratch data and a scratch model folder; the Memes form on
the project copy (code synced to this round first). Clicks went through the page's own buttons and
links; state was polled every 100 to 250 ms and logged.

### Interaction checks

| Check | What happened | Verdict |
|---|---|---|
| Start and Stop camera, five times (`meme_3`) | Each Start: Connecting, then the meme "Absolute Cinema" 0.6 to 1.7 s after the click, at 88 to 99%. Each Stop: Camera off and the Meme panel cleared within 0.3 s | Works |
| Stop while still connecting (0.4 s after Start) | Connecting, then Camera off within 0.3 s; the next Start worked | Works |
| Recognised this session | Rose once per camera start, not for each hold: the detection log adds the same meme again only after `HISTORY_REPEAT_GAP_S` (its documented rule); equal to the rows in Recent detections | As designed |
| Camera tag and Meme panel | For 0.2 to 0.6 s they can differ ("1 hand detected" beside "No hand in view"; the meme still shown 0.4 s after the hand left): the tag is per frame, the panel follows the 4-of-7 vote | As designed (owner rule) |
| Switch pages with the camera on | Dashboard to Data collector: the camera stops (Camera off); back to the dashboard: Camera off, Meme panel cleared, Recent detections kept | Works |
| Overlay after the collector | Off on the dashboard, then the collector (which turns it on for recording), then back: on, as before the P5-2 fix | Unchanged |
| Stop a recording early | "Saved 19 samples for First meme." at 19 of 100; 380 to 399 samples, 400 lines in the file | Works |
| Undo | "Removed the last recording (19 samples)."; the file back to 380 samples, but a faded copy of Your dataset with 399 stayed above the right one (P6-1) | Fixed |
| Leave the collector mid-recording for Memes, come back | 23 samples saved, as documented; the message showed for about 0.1 s (P6-2) | Proposal |
| Open the dashboard mid-recording, come back | The recording is cancelled (422 before and after), as documented; no message (P6-2) | Proposal |
| Reload mid-recording | Nothing saved (422); the page comes back with the camera off and Start recording enabled; no error | Works |
| Delete behind the checkbox (a test gesture `test_wave`, 20 samples) | Delete gesture data disabled until the box is ticked; "Deleted 20 samples of test_wave."; 422 samples, 5 gestures; gone from the gesture list; one Your dataset panel | Works |
| Train model from two tabs within 1 s | One run of 109 models; the second tab's click joined it (button disabled, same progress); one result message, in the tab that started it ("Trained in 3430 steps. Held-out accuracy 96.0% on 422 samples from 18 recordings. ..."); both tabs then show 96.0%; the model files written once (19:18:51) | Works |
| Memes, save a good image twice (copy, test text) | "Saved the meme for First meme. ..."; preview alt "Meme: Test title A", then "Meme: Test title B"; upload box empty again; `first_meme.png` written; no faded copy | Works |
| Memes, a text file renamed `notes.png` | "Nothing was saved: notes.png cannot be read as an image. Choose a JPG, JPEG, PNG, WEBP or GIF file."; the copy's files unchanged (hashes) | Works |
| Memes, a file over 10 MB | The upload box itself refuses it ("Error: File must be 10.0MB or smaller."); it then lists both files chosen so far. Save meme with only that file chosen says "Saved the meme for First meme. ..." and clears the box, while the image is unchanged (P6-3) | Proposal |
| Memes, reload with files chosen | Nothing saved (hashes unchanged); the form starts fresh | Works |
| Memes, reload 0.15 s after Save meme | The save had finished: new image and record agree; after the reload the preview shows the new image (its corner pixel is the third test colour) | Works |

### Final full pass

| Check | Result |
|---|---|
| Each clip on the dashboard (owed since round 5 changed `views/dashboard.py`) | `first_meme`: "Stressed Higuruma"; `second_meme`: "Peace Out"; `meme_3`: "Absolute Cinema"; `meme_4`: "I Guess Bro", each once steady; Hold it steady and Unrecognised seen briefly; 14 frames per second; Stop camera clears the panels each time |
| `none` clip | "No gesture", no image at any poll, Recent detections empty; "Hold it steady" about 1.8 s in total over 14 s (PR-2) |
| Every page loaded fresh, 1280x900 | No Python error, no faded element left, no sideways scroll; the only failed requests are the known `/<page>/_stcore/health` and `/<page>/_stcore/host-config` 404s from opening a page address directly |
| Every page loaded fresh, 390x844 | The same; the page menu closed and hidden on all six |
| Browser console | Besides those 404s, only `ERR_CONNECTION_REFUSED` and "Cannot send rerun backMessage when disconnected" while the critic restarted Streamlit |

### Findings

| ID | Sev. | Area | Page | State | Size | What was seen | How measured | File and line | Fix or proposal | Test added | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P6-1 | High | Frontend | Data collector | after Undo | 1280x900 | A faded copy of Your dataset with the numbers from before the undo (399, then 403 in a second try) stayed above the right one (380) until the page was reloaded; a later rerun did not remove it. The message at the top of the right column is there in some runs and not in others: Undo's run ends early (`st.rerun()`) with no message, the next run shows one, so the panels move one place and the browser kept the old copy | two `.st-key-panel-dataset`, one with `data-stale="true"` at opacity 0.33; reproduced twice; a plain message coming and going did not do it | `views/collector.py:144-147` | The message has a slot (`st.empty()`) in every run, so the panels never move. After: record, stop, Undo gives one Your dataset (380) and nothing faded; Delete the same; the slot is 0 px high and the record panel still starts level with the camera (237 px) | `test_collector_panels_keep_their_place_when_a_message_comes_and_goes` | Fixed |
| P6-2 | Medium | Frontend (owner decision) | Data collector | left mid-recording | 1280x900 | Coming back from another page, the recording is saved but "Saved 23 samples for First meme." shows for about 0.1 s before the camera's own rerun clears it; from the dashboard the recording is dropped with no message. Both behaviours are documented; whether leaving should save at all is `OWNER_QUESTIONS.md` Q2 | message polled every 100 ms; sample counts | `views/collector.py:81-102` | Proposal PR-12 | none | Proposal |
| P6-3 | Medium | Frontend (owner decision) | Memes | a file over 10 MB chosen | 1280x900 | The upload box shows "Error: File must be 10.0MB or smaller.", but Save meme then says "Saved the meme for First meme. ..." and empties the box, so the error disappears while the image is unchanged. The page cannot tell a refused file from no file: Streamlit passes neither | page text; the copy's file hashes before and after | `views/memes.py:113-126` | Proposal PR-13 | none | Proposal |

### Checks

| Check | Method | Result |
|---|---|---|
| Failing first | the new test before the fix | failed (3 elements in the column with a message, 2 without), then passed |
| Browser after the fix | Streamlit restarted; record, stop, Undo; Delete | one Your dataset, no faded element |
| Test suite | `.venv/bin/python -m pytest -q` | **452 passed in 72.20 s** (451 before, 1 added) |
| Owner's files | `shasum -a 256 -c /tmp/bk-critic-hashes-start.txt` in the project folder | 10 of 10 OK |
| Docs | frontend `ARCHITECTURE.md` (collector messages) | updated |

### Scores after round 6

| Dimension | Weight | Score | Evidence this round |
|---|---|---|---|
| Data truth | 25% | 8.8 | No change; every number in the checks above matched its source |
| Recognition and data state | 20% | 8.2 | All five clips right in the final pass, no meme for `none`; P1-5 still open, so no rise |
| Flow and action clarity | 15% | 8.6 | Two messages that mislead or vanish (P6-2, P6-3) |
| Visual hierarchy and brand | 15% | 8.7 | No change |
| Interaction reliability | 10% | 9.0 | Camera cycles, page switches, recordings, undo, delete, two-tab training and every Memes case behave; the faded panel fixed (P6-1) |
| Accessibility and responsive | 10% | 9.1 | No change; the closed menu hidden on every page at 390 px |
| Maintainability | 5% | 9.0 | No change |
| **Weighted** | | **8.70** | 8.695, rounded |

Commit: `5dc9911` (message "Page critique round 6: interaction reliability and final pass").

## Round 7: after the owner decisions

After round 6 you answered Q6 yourself and asked for the rest to be done in a separate session,
in a worktree, for your review; that session built the recommended option of every other open
question and proposal. This round was made on the branch `claude/review-items-25418b`, cut from
`main` at `2722a1a`, after those commits. Nothing was merged during the round; you merged the
branch into `main` afterwards, on 18 October.
The project folder was renamed twice while this round ran (to "Ball Knowledge" and back to
"Passion Project"); the branch's link to the repository was repaired each time with
`git worktree repair`, and your files were checked after each rename (10 of 10 unchanged).

### What was built before this round (one commit per item)

| Item | Commit | What you now see |
|---|---|---|
| Q1 (PR-6) | `87ba3cd`, `49e24f0` | Meme panel "Camera problem" (red edge) while frames cannot be processed |
| Q2 | `416c3ed`, `a5c17ef` | Every page but the Data collector cancels a recording in progress |
| PR-12 | `fb38b96` | "The recording was stopped when you left the page. Nothing was saved."; collector messages stay until your next action |
| Q3 | `1057c3b` | Alt text is the meme title alone ("Absolute Cinema") |
| Q4 | `4ae3996` | The step-numbering note in the ML docs and in `python train_model.py`'s report text; no retrain |
| Q5 | `432c360` | Two messages reworded so they are true |
| Q7 | `520a865` | `dataset_manager.unfinished` and `MemeRecord.title` removed with the two tests that only tested them |
| PR-2 | `ced18ff`, `d7fd67e` | A relaxed-hand frame shows "No gesture" at once |
| PR-3 | `b36a2f0` | Model performance warns when the dashboard cannot load the model |
| PR-7 | `d1375ec` | "Ready to train: Train model is on the Model performance page." on the collector |
| PR-4 | `f894d13` | "No trained model" says to train once the data is ready |
| PR-8 | `2d6b131` | "Type a gesture name to start." under a disabled Start recording |
| PR-10 | `7b7f142` | The overlay checkbox has a hint under it instead of a help icon |
| PR-13 | `1929b7e` | "The image was not changed." when Save meme came with no new image |
| PR-9, PR-11 | `f08c10d`, `098aa72` | Kept, as recommended; no change |
| PR-5 | `151ced2` | Your layout, in its own commit: the dashboard camera is 60% wide on phones |

### How this round was checked

- Streamlit 1.65 on port 8503, run from a project copy in `/tmp` with the scratch data and model
  folders (your port 8501 was not touched), restarted after every code change and for each state.
- The stand-in camera of the critic prompt, section 9: frames from one clip per gesture, extracted
  into `/tmp` and served on `127.0.0.1:8765` only. No screenshot was taken while it showed video;
  one screenshot of the dashboard with the camera off was taken to check the top navigation (see
  P7-4). Evidence is measured text, positions (`getBoundingClientRect`) and computed colours.
- The browser pane was hidden for the whole round; the stand-in still ran at 14 to 15 frames per
  second (Frames per second tile).

### Every page, both sizes

| Page | 1280x900 | 390x844 |
|---|---|---|
| Live dashboard | no Python error, `scrollWidth` 1280; Meme panel image 281 to 560 px, title 618 to 646, panel bottom 663 (as on 18 October) | no error, `scrollWidth` 390, no element past the right edge; camera 60% wide (191 px, centred) |
| Data collector | no error, 1280; "Ready to train" with an in-tab link | no error, 390; camera full width (318 px), unchanged |
| Model performance | no error, 1280; no model warning with the good model | no error, 390 |
| Memes | no error, 1280; preview alt "Stressed Higuruma" | no error, 390; preview alt "Stressed Higuruma" |
| Privacy policy, Terms and conditions | no error, 1280 | no error, 390 |

### The stand-in camera, each clip (1280x900, Meme panel polled every 100 ms for 14 s)

| Clip | What the panel showed | Recent detections |
|---|---|---|
| `first_meme` | the meme "Stressed Higuruma" at 89 to 93% in each hold; "No gesture" for one refresh as the hands came up and went down (4 times, P7-1); Unrecognised once (57%) | 3 rows, alt "Stressed Higuruma" |
| `second_meme` | "Peace Out" at 97% to over 99%; Hold it steady twice | 1 row, alt "Peace Out" |
| `meme_3` | "Absolute Cinema" at 94 to 99%; Hold it steady three times; "No gesture" once as the camera started | 1 row, alt "Absolute Cinema" |
| `meme_4` | "I Guess Bro" at 96 to 98%; Hold it steady twice | 2 rows, alt "I Guess Bro" |
| `none` (20 s, 194 polls) | "No gesture" 163 polls, "No hand in view" 25, no meme, never "Hold it steady" (round 6: about 1.8 s of it in 14 s) | empty, "Nothing detected yet" |
| `none` at 390x844 (12 s, 113 polls) | "No gesture" 84, "No hand in view" 24, "Unrecognised" 5, no meme | empty |

Stop camera: Meme panel "Camera off", camera tag "Camera off", Frames per second and Latency n/a,
106 ms after the click.

### The states the built items touch

| Item | State and how it was reached | Result |
|---|---|---|
| Q1 | hand model moved away in the copy, `meme_3` clip | "Camera problem" 623 ms after Start camera, the same moment the camera tag said "Hand model missing"; red edge `rgba(229, 100, 95, 0.5)`; text 97 px in the 278 px frame (1280) and in the 238 px frame (390). Model put back: both panels moved on 1.8 s later, the meme 2.3 s later, without a reload |
| Q2, PR-12 | Start recording (`first_meme`), then Memes in the top navigation, then back | "The recording was stopped when you left the page. Nothing was saved." on arrival; still there 7 s later, through the camera component's own rerun; 380 samples before and after |
| Q2, PR-12 | Start recording, then the Live dashboard during the countdown, then back | The same message; 380 samples |
| PR-12 | type a name in "Recorded by" and press Enter | the message goes at once; one Your dataset panel, nothing faded |
| PR-12 | Start recording, Stop recording after 7 s | "Saved 29 samples for First meme." still there 8 s later; then Undo: "Removed the last recording (29 samples)." in its place, 380 samples, one Your dataset panel, no faded copy |
| PR-7 | scratch data (5 gestures, 2 to 4 recordings each) | "Ready to train: Train model is on the Model performance page." with `href="/performance" target="_self"` (P7-2) |
| PR-8 | "New gesture..." with no name | Start recording disabled, "Type a gesture name to start." under it (680 to 702 px, inside the panel); muted on `--surface`, 6.2:1 |
| Q5 | name "жест" | "Enter a gesture name using the letters a to z or numbers."; Start recording stays disabled |
| Q5 | a scratch `samples.csv` with every vector all zeros, Train model | "No sample in data/samples.csv is valid, so there is nothing to train on. Record your gestures again." after 0.3 s; the scratch model unchanged |
| PR-4 | empty scratch model folder, data ready | dashboard "No trained model. Train a model on the Model performance page." (in-tab link); Model performance "No trained model yet. Press Train model."; Model tile "Not trained" |
| PR-4, training | Train model on that folder | button disabled, progress "Training: 0 of 97 models trained ...", after 36.9 s "Trained in 2658 steps. Held-out accuracy 97.1% on 380 samples from 16 recordings. ..." once. The scratch model's SHA-256 equals your live model's (`1e5813fc...`) and the report is identical apart from `trained_at` |
| PR-3 | scratch model file cut to 1,000 bytes | Model performance: amber warning first (237 to 343 px, border `rgba(224, 176, 74, 0.5)`), "Model cannot be used: the Live dashboard cannot load it. gesture_model.joblib is not the model that ... Train the model again. The results below are from the training run that saved it."; the dashboard gives the same reason; at 390 the warning wraps in 358 px, no sideways scroll |
| PR-13 | Memes on the project copy, a 10.5 MB file chosen, Save meme | the box: "Error: File must be 10.0MB or smaller."; then "Saved the meme for First meme. The Live dashboard shows it the next time this gesture is recognised. The image was not changed."; the copy's meme files byte for byte as before |
| PR-10 | Show landmarks overlay | no help icon in the checkbox; two mouse clicks on its label: off, then on; the hint "Draw the detected hand skeleton on the video." under it (P7-3) |
| PR-5 | 390x844, `meme_3` held | camera panel 288 to 718 px, meme frame from 779 px: 65 px of the meme in the first screen (17 px before); camera off: the 4:3 frame 191x143 px, centred. 640 px wide: stacked, camera 60%; 641 px: two columns, camera full width. The collector's camera stays full width |
| Q3 | every meme picture | alt text "Absolute Cinema", "Stressed Higuruma", "Peace Out", "I Guess Bro" on the Meme panel, in Recent detections and in the Memes preview |
| Q4 | `format_report` on the scratch copy of your report | "2 of these 2658 steps were tried and undone when the momentum overshot, so the cost history in the report ends at step 2656." |

Not reached again this round, since no built item changed them: No meme set, Image missing and
Memes cannot be shown (their code is unchanged apart from the alt text, checked above), and
Waiting for video with a never-drawn canvas (seen as the camera connected each time).

### Findings

| ID | Sev. | Area | Page | State | Size | What was seen | How measured | File and line | Fix or proposal | Test added | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P7-1 | Low | Frontend (owner decision) | Live dashboard | a gesture coming up or going down | 1280x900 | For one refresh (about 0.5 s) "No gesture" shows before or after the meme while the hands move: 4 times in 14 s with `first_meme`, once with `meme_3`, not with `second_meme` or `meme_4`. These are frames the model calls `none`; before PR-2 they showed "Hold it steady. The meme appears ..." with a green meter | Meme panel polled every 100 ms | `ui.py` `result_card` (the PR-2 branch) | None: it is the state PR-2 B chose, and the sentence is true of those frames. Listed so you know what PR-2 looks like in use | none | Open, by design |
| P7-2 | Low | Frontend (owner decision) | Data collector | data ready to train | 1280x900, 390x844 | "Ready to train" sits under gesture rows tagged "Needs samples" and "Needs sessions", one line below "Ready needs 100 samples from 3 separate recordings.": the word Ready means two thresholds on one panel (training's minimum, 2 recordings each, and the tag's 100 samples from 3 recordings) | page text, scratch data (First meme: 58 samples, 2 recordings, "Needs samples") | `views/collector.py` (the PR-7 hint) | Proposal PR-14 (wording) | none | Fixed after the round: you chose B on 19 October ("You can train now") |
| P7-3 | Low | Frontend (owner decision) | Live dashboard | any | 1280x900 | The PR-10 hint adds 44 px to the camera panel: with a 3:2 video it ends at 942 px (898 before), so the camera tags and hint end below the first screen, and the band beside the camera (PR-9) grows from 235 to 279 px. The proposal said it would add "one more short line" | `getBoundingClientRect`, `meme_3` held | `views/dashboard.py` (the PR-10 hint) | None: the option you approved; PR-10 option C (no explanation) is the way back | none | Open, noted |
| P7-4 | n/a | Frontend (Streamlit) | every page | browser pane hidden | 1280x900 | The top navigation showed only "5 more", with the links in its menu, until the pane was drawn once (a screenshot with the camera off); then all six links showed. Same cause as P4-2: Streamlit measures from a resize observer that does not run while the pane is hidden | DOM of `stTopNav*` before and after | Streamlit 1.65 | none | none | Not confirmed |

### Checks

| Check | Method | Result |
|---|---|---|
| Failing first | each item's new test run before its code change | all failed first (named in each item's section of `OWNER_QUESTIONS.md` and `CRITIQUE_PROPOSALS.md`); passed after |
| Test suite | `.venv/bin/python -m pytest -q` | **492 passed in 75.35 s** (452 at the start; 2 removed for Q7, 42 added) |
| Browser console | the console log | only the known `/<page>/_stcore/health` and `/<page>/_stcore/host-config` 404s from opening page addresses directly, and `ERR_CONNECTION_REFUSED` while Streamlit was being restarted |
| Owner's files | `shasum -a 256 -c` of the 10 files, in the project folder (after each rename) | 10 of 10 OK |
| Design rules | `tests/test_style_rules.py` | pass |

### Scores after round 7 (on the branch)

| Dimension | Weight | Score | Evidence this round |
|---|---|---|---|
| Data truth | 25% | 9.2 | The four untrue statements round 6 named are gone, each seen in the browser: "Starting ... classifying" while the hand model is missing (now "Camera problem"), "The meme appears ..." for a relaxed hand, "Record your gestures" when they are recorded, and Model performance silent about an unusable model. "Saved the meme" now says when the image did not change; the two Q5 messages are true. Not higher: the two meanings of Ready (P7-2) |
| Recognition and data state | 20% | 9.0 | P1-5 closed by your answer; Camera problem agrees with the camera tag at the same moment; the no-model and unusable-model states agree on both pages; every clip right, the `none` clip never shows a meme or "Hold it steady". Not higher: "No gesture" for a moment while a gesture comes up (P7-1) |
| Flow and action clarity | 15% | 9.1 | Every gap round 6 named has its message: train first (PR-4), Ready to train with a link (PR-7), type a name (PR-8), the recording stopped on leaving and messages that stay (PR-12), the image not changed (PR-13). Not higher: P7-2 |
| Visual hierarchy and brand | 15% | 8.7 | The phone shows 65 px of the meme in the first screen instead of 17 (PR-5), still not the whole meme; at 1280 the camera panel is 44 px taller (P7-3). Flat style unchanged |
| Interaction reliability | 10% | 9.2 | One click target for the overlay; leaving the collector behaves the same from every page; messages survive the camera's rerun; Undo, Stop recording and Save meme each leave one panel and an honest message; training twice in round 6 unchanged |
| Accessibility and responsive | 10% | 9.2 | No sideways scroll on any page at 390; the new hints at 6.2:1; alt text without the repeated "Meme:"; one small help icon less (P5-4 resolved). No screen reader available |
| Maintainability | 5% | 9.2 | Leaving the collector handled in one place (`app.py`, `ui.leave_collector`), readiness in one function (`data_collector.ready_to_train`), dead code removed (Q7), 42 tests added, handoff docs and the README follow each change |
| **Weighted** | | **9.07** | |

Gate after round 7: **met** (9.07, lowest dimension 8.7, no open Critical or High, tests passing,
your files unchanged). Scored on the branch; it holds on `main` since the merge of 18 October.

Commit: `31440c2` (message "Page critique round 7: after the owner decisions"), now on `main`.
