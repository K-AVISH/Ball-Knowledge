# Page critique: proposals for the owner

Started 18 October 2026, after the code review (`CODE_REVIEW.md`, `OWNER_QUESTIONS.md`). These are
changes the page critic may not make alone (critic prompt rules 4 and 5): wording, content, the
order of panels, how a state is chosen, or a change that needs a test changed. Each has the
evidence, what would change, the options and a recommendation.

On 18 October you answered PR-1 (through Q6) yourself, then asked for the rest to be done in a
separate session. That session built the recommended option of each proposal on the branch
`claude/review-items-25418b`, one commit per item, and you merged the branch into `main` the same
day. Each proposal below says what was built, or that it was kept as recommended. PR-14 came out
of round 7; you chose its wording on 19 October and it was built on `main`.

| ID | Proposal | Finding | Recommendation |
|---|---|---|---|
| PR-1 | Recent detections and the Latest meme tile name a gesture that has no usable meme image | P1-5 (same as code review Q6) | Option C of Q6. **Answered 18 October: A, keep it** |
| PR-2 | A relaxed hand briefly gets "Hold it steady ... The meme appears ..." and a green meter | P1-2 | Show "No gesture" for a `none` frame at once. **Built on branch `claude/review-items-25418b`, merged into `main` on 18 October** |
| PR-3 | Model performance shows a model's results with no sign that the dashboard cannot load it | P1-3 | One warning line at the top of Model performance. **Built on branch `claude/review-items-25418b`, merged into `main` on 18 October** |
| PR-4 | "No trained model" tells you to record gestures when they are already recorded | P1-4 | Say "train" first when samples exist. **Built on branch `claude/review-items-25418b`, merged into `main` on 18 October** |
| PR-5 | On a phone the meme is below the first screen when a gesture is held | P1-6 | Keep the order; make the camera smaller on phones. **Built on branch `claude/review-items-25418b` in its own commit, merged into `main` on 18 October. Your layout: to drop it, revert commit `151ced2`** |
| PR-6 | The Meme panel says "Starting" while the hand model is missing | P2-3 (code review R1-5) | Answer `OWNER_QUESTIONS.md` Q1. **Built on branch `claude/review-items-25418b` as Q1 B, merged into `main` on 18 October** |
| PR-7 | The Data collector never points to training once the data is ready | P3-1 | A hint with a link when every gesture has 2 recordings. **Built on branch `claude/review-items-25418b`, merged into `main` on 18 October** |
| PR-8 | Start recording is disabled with no word on why | P3-2 | A short hint under the button while no gesture is named. **Built on branch `claude/review-items-25418b`, merged into `main` on 18 October** |
| PR-9 | On wide screens the right column ends well above the camera panel | P4-1 | Keep it; revisit with PR-5. **Kept, recorded on branch `claude/review-items-25418b`; no change** |
| PR-10 | A click on the help icon beside Show landmarks overlay flips the checkbox | P5-4 | Show the help sentence under the checkbox instead. **Built on branch `claude/review-items-25418b`, merged into `main` on 18 October** |
| PR-11 | On a phone, Start recording is far below the camera and its countdown | P5-5 | Keep it, unless you record on a phone. **Kept, recorded on branch `claude/review-items-25418b`; no change** |
| PR-12 | Leaving the collector mid-recording saves or drops it with no message you can read | P6-2 | Decide Q2 first; then keep the message until your next action. **Built on branch `claude/review-items-25418b` (with Q2 A), merged into `main` on 18 October** |
| PR-13 | Save meme says "Saved the meme" when a too-large image was refused | P6-3 | Say when the image was not changed. **Built on branch `claude/review-items-25418b`, merged into `main` on 18 October** |
| PR-14 | "Ready to train" next to gesture tags that say "Needs samples" and the line "Ready needs 100 samples ..." | P7-2 (round 7, on the branch) | Your choice of words; recommended B. **Your answer (19 October): B, built on `main`** |

## PR-1. Names in Recent detections (P1-5)

**Seen** (project copy, 1280x900, stand-in camera): with the `first_meme` record removed from
`memes.json`, Recent detections listed "14:29:23 first_meme 92%" and the Latest meme tile "first_meme
at 14:29:23". With `meme_3.jpg` deleted, the row read "Meme 3". With `memes.json` cut short, the row
read "meme_3" while the Meme panel said only "Memes cannot be shown". Your rule allows names only in
the messages that ask you to fix a gesture. This is the same question as `OWNER_QUESTIONS.md` Q6,
from the code review; answer it there.

**Why not fixed by the critic:** two tests expect the name (`tests/test_memes.py`
`test_a_gesture_without_a_picture_falls_back_to_its_name`, `tests/test_display.py`
`test_history_without_pictures_uses_display_names`), and a third checks the dashboard's exact call
(`tests/test_pages.py` `test_the_stats_and_history_show_memes_by_picture`). Tests change only with
your say (critic rule 2), and what to show instead is new wording (rule 4).

**Options and recommendation:** as in Q6. Recommended C: keep the name only while a fix-this
message names the same gesture; show "No meme" when `memes.json` cannot be read.

**Your answer (18 October): A.** Nothing to build: the names stay, and the rule now lists this
exception (`docs/frontend-handoff/DESIGN_SYSTEM.md` section 4).

## PR-2. "Hold it steady" for a relaxed hand (P1-2)

**Seen** (1280x900, stand-in camera, the `none` clip, polled every 100 ms): the panel went "No hand
in view", then "Hold it steady. The meme appears once the gesture is recognised in 4 of the last 7
frames." with the meter green at 91%, then "No gesture" (8.9 s to 9.4 s into the clip). For a
relaxed hand no meme ever appears, so for that half second the sentence is not true and the green
meter suggests a meme is coming. Code: `ui.result_card` (`ui.py`, the final `else` branch) treats
every recognised frame alike; only a steady `none` gets "No gesture".

| Option | What it means |
|---|---|
| A. Keep | It lasts about one refresh |
| B. A frame recognised as `none` shows "No gesture" at once | No vote is needed, since no meme is at stake. The meter shows n/a, as in the steady "No gesture" state. One condition in `ui.result_card` and a state test |
| C. Keep "Hold it steady" but drop the meme sentence for `none` | New wording |

**Recommendation:** B. It uses an existing state and its text, and "uncertain means no meme" is
untouched.

**Built on branch `claude/review-items-25418b`, merged into `main` on 18 October (option B).** In `ui.result_card`, a fresh frame
recognised as `none`, with no steady result, gives exactly the steady "No gesture" panel (the same
text, meter n/a). A meme that is already held still stays until the 4-of-7 vote changes, so one
relaxed frame does not hide it. The vote, the threshold and the model are untouched. Tests:
`test_a_relaxed_hand_says_no_gesture_at_once`, `test_a_held_meme_stays_through_one_relaxed_frame`
(`tests/test_status.py`). Docs: `DESIGN_SYSTEM.md` section 4.

Seen in use (critique round 7, P7-1): as the hands come up into a gesture or go down, a frame
the model calls `none` now shows "No gesture" for one refresh (about 0.5 s) before or after the
meme, 4 times in 14 s with the `first_meme` clip, once with `meme_3`, never with `second_meme` or
`meme_4`. Before, those frames showed "Hold it steady. The meme appears ..." with a green meter.
The `none` clip itself never showed "Hold it steady" in 194 polls (about 1.8 s of it in 14 s in
round 6).

## PR-3. Model performance when the model cannot be loaded (P1-3)

**Seen** (1280x900, a scratch model folder with `gesture_model.joblib` cut to 1,000 bytes): the
dashboard said "Model cannot be used ... Train the model again" and its Model tile "Cannot load".
Model performance showed "Held-out accuracy 97.1%" and every table, with no warning. The numbers are
true of the training run, but nothing tells you that the model they describe cannot be used.
`views/performance.py` reads only the report; it never tries to load the model.

| Option | What it means |
|---|---|
| A. Keep | The dashboard is where recognition happens, and it says so |
| B. One warning at the top of Model performance | The same reason the dashboard shows, from `ui.load_predictor()`, in the amber notice style already used there |

**Recommendation:** B. Both pages then tell the same story.

**Built on branch `claude/review-items-25418b`, merged into `main` on 18 October (option B).** Model performance calls
`ui.load_predictor()` (the dashboard's own loader, cached) and, when it fails for a reason other
than "not trained", shows one amber warning at the top: "Model cannot be used: the Live dashboard
cannot load it. <the dashboard's reason, which ends "Train the model again."> The results below
are from the training run that saved it." The warning has an `st.empty()` slot in every run, so
the panels below never move. Tests: `test_performance_says_when_the_dashboard_cannot_load_the_model`
(failed before the change, passes after) and
`test_performance_has_no_such_warning_for_a_usable_model` (`tests/test_pages.py`). Docs: the
frontend `ARCHITECTURE.md`.

## PR-4. "No trained model" when samples exist (P1-4)

**Seen** (scratch data with 380 samples of 5 gestures, empty model folder): the dashboard said
"Record your gestures on the Data collector page, then train on the Model performance page.", and
Model performance "Record at least two gestures on the Data collector page, then press Train model."
With gestures already recorded, the next step is just to train. The text is true for a new
project, so this is wording only.

| Option | What it means |
|---|---|
| A. Keep | One sentence covers both cases |
| B. When samples exist, say "Train a model on the Model performance page." (dashboard) and "Press Train model." (Model performance) | Two short conditions, new wording |

**Recommendation:** B.

**Built on branch `claude/review-items-25418b`, merged into `main` on 18 October (option B, with one refinement).** The two texts
are as proposed: the dashboard's Meme panel says "No trained model. Train a model on the Model
performance page." (in-tab link) and Model performance "No trained model yet. Press Train model."
The refinement: they show when the recorded data is ready for training
(`data_collector.ready_to_train`: at least 2 gestures with 2 recordings each, the minimum training
itself checks), not as soon as any sample exists. With one gesture recorded, "Press Train model"
would lead straight to a refusal, so the first-time text stays until training can run. Tests:
`test_no_trained_model_says_train_first_when_the_data_is_ready` (`tests/test_status.py` and
`tests/test_pages.py`) and `test_no_trained_model_still_says_record_first_for_a_new_project`
(`tests/test_pages.py`). This commit uses `ready_to_train` from the PR-7 commit. Docs:
`DESIGN_SYSTEM.md` section 4, the frontend `ARCHITECTURE.md`, the README message table.

## PR-5. The meme on a phone (P1-6)

**Seen** (390x844, stand-in camera, `meme_3` held): the columns stack camera, Meme panel, Live
statistics, Recent detections. The camera panel runs from 288 to 766 px, so the meme image starts
at 827 px; on an 844 px screen only its top 17 px show without scrolling. At 1280x900 the meme is in
full view beside the video (281 to 560 px).

| Option | What it means |
|---|---|
| A. Keep | You see your hand in the video and scroll for the meme |
| B. Meme panel first on phones | The video then sits below the meme; you cannot see your hand while you look at the meme |
| C. A smaller camera on phones (for example 60% of the width) | Both may fit in the first screen; the camera frame keeps its 4:3 shape |

**Recommendation:** C, but only with your agreement: it changes the dashboard's layout, which is
yours (critic rule 4).

**Built on branch `claude/review-items-25418b`, merged into `main` on 18 October (option C), in a commit of its own** ("PR-5 (owner's
layout, drop if unwanted): ..."), since you kept the layout for yourself. When the columns stack
(640 px and narrower) the Live dashboard's camera is 60% of the width, centred; its 4:3 frame
shrinks with it. The Data collector's camera and every wider layout are unchanged.

Measured with the stand-in camera (`meme_3` held) at 390x844: the camera panel runs from 288 to
718 px (was 288 to 766), the meme frame from 779 px, so 65 px of the meme are in the first screen
(was 17 px). Not all of it: the page header and the camera panel's title, checkbox, tags and hints
take most of the first screen whatever the camera's size. With the camera off the 4:3 frame is
191x143 px, centred. At 641 px the two columns are side by side and the camera is full width;
at 640 px they stack and it is 60%. Test: `test_on_a_phone_the_dashboard_camera_is_smaller`
(`tests/test_pages.py`). Docs: `DESIGN_SYSTEM.md` section 2, the frontend `ARCHITECTURE.md`.

## PR-6. "Starting" while the hand model is missing (P2-3)

**Seen** (project copy with `models/mediapipe/hand_landmarker.task` moved away, 1280x900, stand-in
camera): for 9 s the camera tag said "Hand model missing" and the Meme panel "Starting. The model is
classifying the first frames.", which is not what was happening. With the file put back the meme
showed 0.6 s later, without a reload. This is `OWNER_QUESTIONS.md` Q1 from the code review; answer it
there (recommended: a "Camera problem" message in the frame).

**Built on branch `claude/review-items-25418b`, merged into `main` on 18 October**, as `OWNER_QUESTIONS.md` Q1 option B (the same
commit): the Meme panel says "Camera problem" with a red edge and points to the message under
the video.

## PR-7. A next step on the Data collector (P3-1)

**Seen** (first-time journey on a project copy with no samples, model or memes, 1280x900): after two
gestures with two recordings each, the collector said "Saved 20 samples for fist." and listed the
two gestures; nothing on the page said that training is now possible or where it is. The only
pointer was the dashboard's "No trained model" message seen before recording.

| Option | What it means |
|---|---|
| A. Keep | The dashboard message and the navigation are enough |
| B. When there are 2 or more gestures with 2 or more recordings each, a hint under Your dataset: "Ready to train: Train model is on the Model performance page." with an in-tab link | New text |

**Recommendation:** B.

**Built on branch `claude/review-items-25418b`, merged into `main` on 18 October (option B).** Under the gesture rows of Your dataset,
"Ready to train: Train model is on the Model performance page." with an in-tab link, once
`data_collector.ready_to_train()` holds: at least 2 gestures, each with 2 recordings
(`MIN_SESSIONS_FOR_TRAINING`, what training itself checks). It shares one `st.empty()` slot with
the existing "Add at least 2 gestures before training." hint, so the expander below never moves.
Tests: `test_ready_to_train_matches_what_training_asks_for` (`tests/test_data_collector.py`),
`test_the_collector_points_to_training_once_the_data_is_ready` and
`test_no_pointer_to_training_while_a_gesture_is_short_of_recordings` (`tests/test_pages.py`).
Docs: the frontend and backend `ARCHITECTURE.md`, the README section on collecting samples.

## PR-8. Why Start recording is disabled (P3-2)

**Seen** (same journey): with "New gesture..." chosen and the name box empty, "Start recording" is
disabled and nothing says why; it enables as soon as a name is typed ("Saved as open_palm" then
appears). The name box is right above the button, so most people will find it.

| Option | What it means |
|---|---|
| A. Keep | |
| B. A hint "Type a gesture name to start." while the button is disabled for that reason | New text |

**Recommendation:** B, low priority.

**Built on branch `claude/review-items-25418b`, merged into `main` on 18 October (option B).** While "New gesture..." is chosen and
the name box is empty, the hint "Type a gesture name to start." shows under the disabled Start
recording button; it goes as soon as a name is typed, and never shows during a recording. A name
that cannot be used keeps its own red message instead. Test:
`test_start_recording_says_why_it_is_disabled_until_a_name_is_typed` (`tests/test_pages.py`).
Docs: the frontend `ARCHITECTURE.md`.

## PR-9. Balance beside the camera on wide screens (P4-1)

**Seen** (stand-in camera, `meme_3` held): at 1440x900 the camera panel runs from 237 to 903 px and
the Meme panel from 237 to 667 px, so the right column has 236 px of empty page beside the lower
part of the camera; 1280x900 is the same (camera 237 to 898, Meme 237 to 663). The second row (Live
statistics, Recent detections) starts below both. With a 4:3 webcam the camera panel is taller
still (710 px with the 4:3 frame), so the gap grows to about 280 px.

| Option | What it means |
|---|---|
| A. Keep | The meme sits beside the top of the video, which is what matters; the empty band is quiet |
| B. Recent detections under the Meme panel on wide screens, Live statistics alone in the second row | Fills the band with something related to the meme; changes the 17 October layout |

**Recommendation:** A for now. The layout was chosen with you on 17 October and the meme is where it
should be; if you take PR-5 (a smaller camera on phones), look at this at the same time.

**Kept (option A), recorded on branch `claude/review-items-25418b`, merged into `main` on 18 October; no code changed.** Looked at
again with PR-5: option C there (built on the same branch, in its own commit) applies to narrow
windows only, so the wide layout, and this band beside the camera, are exactly as before.

## PR-10. The help icon inside the overlay checkbox (P5-4)

**Seen** (1280x900, camera off): a mouse click on the help icon beside "Show landmarks overlay"
shows the tip and also turns the overlay off (or on). Streamlit draws a checkbox's help icon inside
the checkbox's label, so the icon is part of the checkbox's click area. Enter on the icon shows the
tip and changes nothing. The setting is easy to turn back, and the box shows the change.

| Option | What it means |
|---|---|
| A. Keep | Streamlit's own behaviour |
| B. Drop `help=` and show the same sentence, "Draw the detected hand skeleton on the video.", as a small hint under the checkbox | No new words; one more short line in the Camera panel |
| C. Drop the help and keep the label alone | One sentence less; "landmarks" is then not explained |

**Recommendation:** B. It keeps the explanation and leaves the checkbox one click target.

**Built on branch `claude/review-items-25418b`, merged into `main` on 18 October (option B).** The checkbox has no `help=`, and
"Draw the detected hand skeleton on the video." is a hint (`.hint`) right under it, so the
checkbox is one click target again. Test:
`test_the_overlay_explains_itself_under_the_box_not_in_a_help_icon` (`tests/test_pages.py`).
Docs: the frontend `ARCHITECTURE.md`.

Seen in use (critique round 7, P7-3): the hint makes the camera panel 44 px taller. At 1280x900
with a 3:2 video it now ends at 942 px (898 before), so the camera tags and hint end below the
first screen, and the band beside the camera (PR-9) grows from 235 to 279 px. Option C (no
explanation at all) is the way back if you prefer the shorter panel.

## PR-11. Recording on a phone (P5-5)

**Seen** (390x844, Data collector): the columns stack camera (288 to 758 px), Tips for good data
(774 to 1156), Record a gesture (1172 to 1526) and Your dataset. Start recording is at 1469 px, so
after pressing it you scroll up about 700 px to see the 3 s countdown and the progress, which show
in the camera panel. At 1280x900 the camera and the record panel are side by side.

| Option | What it means |
|---|---|
| A. Keep | The collector is used at a desk with a webcam, where both are in view |
| B. On phones only, Record a gesture straight after the camera, the tips after Your dataset | Desktop unchanged; a layout change on phones |
| C. Tips for good data moved to the right column on every size | Also changes the desktop layout |

**Recommendation:** A, unless you record on a phone; then B. Like PR-5, this changes a layout that
is yours (critic rule 4).

**Kept (option A), recorded on branch `claude/review-items-25418b`, merged into `main` on 18 October; no code changed.** Your
request named this one as kept. The collector's stacked order on a phone is as before; PR-5's
smaller camera applies to the Live dashboard only. If you start recording on a phone, option B
is still open.

## PR-12. Leaving the collector during a recording (P6-2)

**Seen** (1280x900, stand-in camera, scratch data): Start recording, then Memes in the top
navigation 3 s into the recording, then back. The 23 samples were saved, but "Saved 23 samples for
First meme." showed for about 0.1 s (polled every 100 ms): the camera starting again reruns the
page and clears it. From the Live dashboard instead, the recording is dropped and nothing says so.
Both are documented (frontend `ARCHITECTURE.md`); whether leaving should save at all is
`OWNER_QUESTIONS.md` Q2 from the code review.

| Option | What it means |
|---|---|
| A. Keep | You see the change only in the sample counts |
| B. After you answer Q2, keep the message until you act on the page (for example, until the next button press), and when a recording is dropped, say so: "The recording was stopped when you left the page. Nothing was saved." | One more message; a change to when messages clear |

**Recommendation:** answer Q2 first; then B.

**Built on branch `claude/review-items-25418b`, merged into `main` on 18 October (option B, after Q2 option A).** Opening any other
page during a recording drops it (the Q2 commits), and `ui.leave_collector()` leaves the message
"The recording was stopped when you left the page. Nothing was saved." for the collector, also
when you come back through more than one page. Collector messages now stay until you use a
control on the page (each has an `on_change` or `on_click` callback that clears it); reruns you
did not ask for, such as the camera component's when it mounts, keep it. Opening another page
clears a message already shown, so an old "Saved ..." does not come back later. Tests:
`test_a_collector_message_stays_until_your_next_action`,
`test_leaving_mid_recording_says_it_was_stopped_and_nothing_saved`,
`test_an_old_collector_message_is_gone_after_another_page` (`tests/test_pages.py`). Docs: the
frontend `ARCHITECTURE.md`, the README section on collecting samples. This commit builds on the
Q2 commits, so it cannot be kept without them.

## PR-13. "Saved the meme" when the image was refused (P6-3)

**Seen** (project copy, 1280x900): choose a 10.5 MB PNG. The upload box shows "Error: File must be
10.0MB or smaller." Press Save meme: "Saved the meme for First meme. The Live dashboard shows it the
next time this gesture is recognised." The box empties, so the error disappears, and the image is
the old one (file hashes unchanged). Streamlit gives the page no file in this case, so the page
cannot tell a refused file from no file at all.

| Option | What it means |
|---|---|
| A. Keep | The error was on screen before you pressed Save |
| B. When no new image came with the save, add "The image was not changed." to the message | True in both cases; new wording |

**Recommendation:** B.

**Built on branch `claude/review-items-25418b`, merged into `main` on 18 October (option B).** When a save came with no new image,
the message reads "Saved the meme for First meme. The Live dashboard shows it the next time this
gesture is recognised. The image was not changed." A save with a new image keeps the old message.
Tests: `test_a_save_without_a_new_image_says_the_image_was_not_changed` (failed before, passes
after) and `test_a_save_with_a_new_image_does_not_say_it_was_not_changed` (`tests/test_pages.py`,
both on a scratch meme library). Docs: the frontend `ARCHITECTURE.md`.

## Changes made under critic rule 3, listed for you

Rule 3 lets the critic fix what is broken and change only the false part of a text, quote it before
and after, and tell you. Say if you want any of these back.

| Finding | Page | Before | After |
|---|---|---|---|
| P2-1 | Model performance, Confidence cutoff, column Accepted | "100%" at the 50% cutoff (the report: 99.74%, so 1 of 380 held-out predictions is rejected); the other rows "98%", "96%", "92%", "82%" | "99.7%", "98.2%", "95.8%", "91.6%", "82.4%": one decimal, as the Correct column beside it |
| P2-2 | Live dashboard and Data collector, hint under the camera with the hand model missing | "ModelMissingError: Hand model not found at <path>. Run: python download_models.py The camera picks the model up by itself within a few seconds." | "Hand model not found at <path>. Run: python download_models.py. The camera picks the model up by itself within a few seconds." (no Python error name; the two sentences separated) |
| P1-1 | Live dashboard and Data collector, tags under the camera, just after Stop camera | "Camera off" with "2 hands detected" for about 0.6 s | "Camera off" alone |
| P5-2 | Live dashboard, Show landmarks overlay | Every second click did nothing: from off, four clicks gave on, on, off, off | Each click changes it: from on, off, on, off, on. The checkbox got a key (`views/dashboard.py`); no wording or layout change |

## PR-14. Two meanings of "Ready" on the Data collector (P7-2)

**Seen** (round 7, on the branch `claude/review-items-25418b`, 1280x900 and 390x844, scratch data): the PR-7
hint "Ready to train: Train model is on the Model performance page." sits under gesture rows
tagged "Needs samples" (First meme: 58 samples, 2 recordings) and "Needs sessions", one line below
"Bars fill toward 300 samples, the suggested amount. Ready needs 100 samples from 3 separate
recordings." Both statements are true: training can run once each gesture has 2 recordings
(`MIN_SESSIONS_FOR_TRAINING`), while the green Ready tag asks for 100 samples from 3 recordings.
But one panel now uses "Ready" for two thresholds.

| Option | What it means |
|---|---|
| A. Keep | The text you approved in PR-7 |
| B. "You can train now: Train model is on the Model performance page." | Same link and condition; no second meaning of Ready |
| C. Keep "Ready to train" and add "More recordings still help." when a gesture is not tagged Ready | One more sentence |

**Recommendation:** B. Nothing has been built for this; it is wording, so it waits for you.

**Your answer (19 October): B, built on `main`.** The hint now reads "You can train now: Train model is
on the Model performance page.", with the same link and the same condition
(`data_collector.ready_to_train`). "Ready" is left to the gesture tag. The two collector tests that
held the old text were changed with your answer: one checks the new hint and that "Ready to train"
is gone, the other that the hint is absent while a gesture has too few recordings.
