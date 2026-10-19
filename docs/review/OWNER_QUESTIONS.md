# Questions for the owner from the code review

Started 18 October 2026. Each question comes from a confirmed finding in `CODE_REVIEW.md`. The
reviewer may not decide these (prompt rules 5, 11, 12 and 13): they change what you see, the
model file, or a decision you made. Nothing here has been changed in the code on `main`. The
recommendation is advice only. Line numbers refer to the code at the git tag
`code-review-start-2026-10-18`, before the review's fixes.

On 18 October you answered Q6 yourself and asked for the rest of the unfinished work to be done in
a separate session. That session built the recommended option of each other question on the branch
`claude/review-items-25418b`, one commit per item, and you merged the branch into `main` the same
day. Each item below says what was built.

| ID | Question | Finding | Recommendation |
|---|---|---|---|
| Q1 | What should the Meme panel say while the camera has a processing error, such as the hand model missing? | R1-5 | B: a "Camera problem" message in the frame. **Built on branch `claude/review-items-25418b`, merged into `main` on 18 October** |
| Q2 | Should leaving the Data collector for any page cancel a recording, as the dashboard does? | R1-4 | A: every page cancels. **Built on branch `claude/review-items-25418b`, merged into `main` on 18 October** |
| Q3 | Alt text: "Meme: Absolute Cinema" (today) or "Absolute Cinema" (your answer to OD-5)? | R1-13 | B: the title alone. **Built on branch `claude/review-items-25418b`, merged into `main` on 18 October** |
| Q4 | The report numbers its cost curve by accepted steps, but "steps" counts every step tried | R1-14 | C: note it now, renumber at the next planned retrain. **Note built on branch `claude/review-items-25418b`, merged into `main` on 18 October; no retrain** |
| Q5 | Two error messages that are untrue in rare cases: may they be reworded? | R2-1, R2-3 | Yes, both. **Built on branch `claude/review-items-25418b`, merged into `main` on 18 October** |
| Q6 | A gesture with no usable meme image is listed by its name in Recent detections and the Latest meme tile. Is that an allowed exception to "the dashboard never names a gesture"? | R3-3 | C: allow it only where a fix-this message names it too. **Answered 18 October: A** |
| Q7 | May two functions that only tests still use be removed, with their tests? | R6-4 | Yes. **Built on branch `claude/review-items-25418b`, merged into `main` on 18 October** |

## Q1. The Meme panel while frames cannot be processed (R1-5)

**What happens.** When the camera runs but every frame fails, for example on a new install
before `python download_models.py` (the hand model is missing), the camera panel says "Hand model
missing" with the fix. The Meme panel beside it says **"Starting. The model is classifying the
first frames."** for as long as the problem lasts. That sentence is not true then: no frame
reaches the model (`vision.py`: a failed frame is never handed to the recogniser, so
`ui.result_card` keeps showing its "no prediction yet" state, `ui.py` lines 563 and 564).

**Evidence.** With the camera live and no prediction, `ui.result_card` returns the "Starting"
frame, while `ui.camera_state` for the same frame stats returns "Hand model missing" (checked in
code on 18 October; `vision.py` lines 66 to 75 never offer a failed frame to the recogniser).

| Option | What it means |
|---|---|
| A. Keep as is | The camera panel already says what is wrong |
| B. A "Camera problem" message in the frame | When the camera reports an error, the Meme panel says so (red edge) and points to the hint under the video. One new state in `ui.result_card`, its test, and `DESIGN_SYSTEM.md` section 4 |
| C. Keep "Starting" but change its sentence | For example "Waiting for the first classified frame." Only the wording changes |

**Recommendation:** B. The two panels then agree, and the user is told the real reason.

**Built on branch `claude/review-items-25418b`, merged into `main` on 18 October (option B).** `ui.result_card` has a new state, "Camera
problem" (red edge): "The camera's frames cannot be processed, so no meme can be shown. The
message under the video says why." It shows whenever the camera is live and its stats carry a
frame error (`views/dashboard.py` passes `stats.error`), comes after Camera off and Waiting for
video, and hides a meme that was steady, since no new frame reaches the model. Tests:
`test_a_camera_problem_is_said_in_the_meme_panel_not_starting`,
`test_a_camera_problem_hides_a_meme_that_was_steady`,
`test_the_camera_being_off_comes_before_an_old_camera_problem` (`tests/test_status.py`), the
state added to the `STATES` table there (so it is checked as distinct and name-free like the
others), and `test_the_dashboard_meme_panel_reports_a_camera_problem` (`tests/test_pages.py`).
Docs: `DESIGN_SYSTEM.md` section 4, the frontend `ARCHITECTURE.md`, the README troubleshooting list.

## Q2. Leaving the Data collector during a recording (R1-4)

**What happens.** Opening the Live dashboard cancels a recording in progress (`views/dashboard.py`
lines 29 to 31). The Model performance, Memes, Privacy and Terms pages do not. Coming back to the
collector then stops the recording and saves what was recorded before you left, with "Saved N
samples". A recording left during the 3 s countdown reports "Nothing was saved because no hand
was detected during the recording", which is not the reason.

**Evidence.** A Streamlit page run (AppTest) of the collector, given a recording still going with
12 samples, as after a visit to the Memes page, saved those 12 samples (18 October). The frontend architecture
document said "Leaving this page cancels a recording in progress"; it now describes what the code
does and points here.

| Option | What it means |
|---|---|
| A. Every page cancels | As the dashboard does today and the old document said. A recording only ever ends on the collector, or is dropped |
| B. Keep, and say so | Coming back saves what was recorded, with a message that says the recording was cut short when you left |
| C. Save at once on leaving | Not possible cleanly: a page that is not shown does not run |

**Recommendation:** A. It matches the rule the dashboard already follows, and no partial
recording is saved without you seeing it happen.

**Built on branch `claude/review-items-25418b`, merged into `main` on 18 October (option A).** `app.py` calls `ui.leave_collector()`
for every page but the Data collector, which drops a recording still in its countdown or
recording (`Recorder.cancel_unfinished`). The dashboard's own cancel moved there. One choice made
while building: a recording that already reached its target and is waiting the half second until
the collector saves it is kept, and saved when you come back, since it ended on the collector.
Tests: `test_every_other_page_cancels_a_recording_in_progress` (one run per page, through
`app.py`), `test_the_collector_itself_does_not_cancel_its_recording` (`tests/test_pages.py`),
`test_leaving_the_collector_drops_only_a_recording_still_going` (`tests/test_data_collector.py`).
The message you see when you come back is proposal PR-12, in its own commit. The code is in
two commits, "Q2: every page ..." and "Q2: docs ..."; drop both together.

## Q3. Alt text on meme pictures (R1-13)

**What happens.** Your answer to OD-5 on 18 October was "Meme title, else Meme". The code writes
"Meme: <title>" (`ui.meme_alt`, `ui.py` line 493), for example "Meme: Absolute Cinema". The prefix
was the implementation session's own choice (its handoff lists it as a judgement call to check).
Both versions keep your rule that the dashboard never names a gesture.

| Option | What it means |
|---|---|
| A. Keep "Meme: <title>" | A screen reader says "Meme: Absolute Cinema, image" |
| B. The title alone, as answered | "Absolute Cinema, image". The panel and the table column are already headed "Meme", so the prefix repeats them |

**Recommendation:** B, since it is what you chose and the heading already says "Meme". One line in
`ui.meme_alt`, its test and `DESIGN_SYSTEM.md`.

**Built on branch `claude/review-items-25418b`, merged into `main` on 18 October (option B).** `ui.meme_alt` returns the title alone,
or "Meme" when none is set, for the Meme panel, the Memes page preview, Recent detections and the
Latest meme tile. Two existing tests were changed because this option changes the text they
check, and nothing else in them: `test_alt_text_is_the_meme_title_or_just_meme`
(`tests/test_status.py`, now expects `alt="Peace Out"`) and
`test_a_steady_gesture_shows_its_image_title_rating_and_description` (`tests/test_memes.py`, now
expects `alt="Big &lt;wave&gt;"`). Both failed before the code change and pass after. Docs:
`DESIGN_SYSTEM.md` section 4 and the frontend `ARCHITECTURE.md`.

## Q4. Step numbers in the training report (R1-14)

**What happens.** The final model's report says `"steps": 2658` (shown on Model performance as
"Training steps 2658"). Its cost curve, `cost.history`, ends at step 2656. Both are right about
different things: 2658 counts every step tried, and the curve counts the steps kept; 2 steps were
tried and undone when the momentum overshot (`gd_model.py` lines 144 to 146). No page shows the
curve, so nothing on screen is wrong today.

**Why this is yours.** The curve is stored inside the model file too (`cost_history_`), so
renumbering it changes the model file's bytes and checksum. The review rules let only you replace
the live model.

| Option | What it means |
|---|---|
| A. Leave it | Nothing visible changes |
| B. Number the curve by steps tried | Needs a retrain and a new live model |
| C. Note it in the ML docs now; do B at the next retrain you plan anyway (OD-7) | No change to the live model today |

**Recommendation:** C.

**Built on branch `claude/review-items-25418b`, merged into `main` on 18 October (option C, the note only).** No retrain, and the
live model and report are unchanged. The mismatch is written down in the ML `ARCHITECTURE.md`
(with the instruction to renumber at the next planned retrain and then remove the note), the
report's field list in `docs/backend-handoff/DATA_CONTRACTS.md`, `RESULTS_AND_DATA.md` ("2,658
tried, 2,656 kept"), the `gd_model.GradientDescentClassifier` docstring and a comment where
`train_model.py` writes `steps`. The report text that `python train_model.py` prints now adds,
when the two differ: "2 of these 2658 steps were tried and undone when the momentum overshot, so
the cost history in the report ends at step 2656." Test:
`test_the_report_text_says_when_steps_were_tried_and_undone` (`tests/test_train_model.py`).

## Q5. Two error messages that are untrue in rare cases (R2-1, R2-3)

Both are wording, so they wait for you.

| Message | When it is untrue | Proposed wording |
|---|---|---|
| "Only one gesture (none) has valid samples. Record at least 2 different gestures." (`train_model.py` line 456) | When **no** row is valid (only after the file was damaged, for example every vector all zeros). "(none)" then reads like the gesture called `none` | "No sample in data/samples.csv is valid, so there is nothing to train on. Record your gestures again." for the zero case; the current text stays for one gesture |
| "Enter a gesture name using letters or numbers." (`data_collector.py` line 52) | A name in another script, such as "жест" or "手势", is refused although it is letters; and "École" is saved as `cole`, losing the É | "Enter a gesture name using the letters a to z or numbers." Changing how ids are made (keeping "ecole") would change an existing test, so that part is not proposed |

**Recommendation:** approve both new wordings. Evidence: scratch scripts on 18 October printed
both messages for those inputs.

**Built on branch `claude/review-items-25418b`, merged into `main` on 18 October (both, as proposed).** Training with no valid row
now says "No sample in data/samples.csv is valid, so there is nothing to train on. Record your
gestures again." (the file name comes from `config.SAMPLES_CSV`); one valid gesture keeps "Only
one gesture (a) has valid samples. Record at least 2 different gestures." A name with nothing in
a to z or 0 to 9 is refused with "Enter a gesture name using the letters a to z or numbers." How
ids are made is unchanged ("École" is still saved as `cole`, as `test_slugify` expects). Tests:
`test_names_in_other_scripts_are_refused_with_a_true_message` (`tests/test_data_collector.py`,
"жест", "手势" and "!!!"), `test_no_valid_sample_at_all_is_not_called_one_gesture` and
`test_one_valid_gesture_keeps_its_message` (`tests/test_train_model.py`).

## Q6. Names in Recent detections for a gesture without a meme image (R3-3)

**What happens.** Your rule (17 October): the Live dashboard never names a gesture. The only
exceptions written down are the two messages that ask you to fix a gesture ("No meme set" and the
notice "No usable meme image yet for: ..."). But when a recognised gesture has no usable meme
image (no record yet, or its image file is missing), Recent detections and the Latest meme tile
show the gesture's **name** in place of the picture (`ui.meme_thumb`, `ui.py` lines 475 to 486).
The frontend chose this on 17 October "since nothing else can identify it"
(`docs/frontend-handoff/CHANGES_2026-10-17.md`); it was not one of your answers.

**When you would see it.**

- Record and train a new gesture before choosing its meme, then show it: the Meme panel says "No
  meme set: <name> has no meme yet", the notice at the top names it, and Recent detections lists
  it by name. The name is already on screen in the two allowed messages.
- If `memes.json` cannot be read, every detection is listed by its **id** (for example `meme_3`),
  while the Meme panel says only "Memes cannot be shown" and no notice names a gesture (checked in
  code: `ui.history_card` and `ui.meme_thumb` with no records return `meme_3`). Here the ids are
  not on screen anywhere else.

**Why the reviewer did not change it.** Two existing tests expect the name
(`test_a_gesture_without_a_picture_falls_back_to_its_name`,
`test_history_without_pictures_uses_display_names`), and tests may only change with your say.

| Option | What it means |
|---|---|
| A. Allow it, and write the exception down | A gesture with no usable meme image (none set, its image missing, or `memes.json` unreadable) is listed by its name or id. The rule's documents list it as a third exception |
| B. Show "No meme" instead of the name | The rule holds without exception; such a row then cannot say which gesture it was |
| C. A for a gesture without a meme, B when `memes.json` cannot be read | Names appear only where a fix-this message already shows them |

**Recommendation:** C. It adds no name that is not already on screen for the first case, and keeps
ids off the dashboard when the file is broken, where nothing else names them. B or C changes the two
tests with the code.

**Your answer (18 October): A.** The names and ids stay as they are. The exception is now written
into the rule: `docs/frontend-handoff/DESIGN_SYSTEM.md` section 4, the frontend `ARCHITECTURE.md`,
the decisions table in `docs/implementation-plan/OWNER_DECISIONS.md` and the comment in
`views/dashboard.py`. No code or test changed.

## Q7. Code that only tests use (R6-4)

Since the dashboard was rebuilt on 17 October and the alt text changed on 18 October, no page or
script calls these any more; only tests do:

| Code | What it did | Tests that use it |
|---|---|---|
| `dataset_manager.unfinished(records, labels)` | Listed gestures without a rating or description, for a dashboard notice that was removed on 17 October | `test_unfinished_lists_memes_without_rating_or_description`, and two assertions in the `save_edit` tests in `tests/test_display.py` |
| `MemeRecord.title` (property) | The meme title, else the gesture name; it fed the alt text that used to name gestures | `test_title_falls_back_to_the_gesture_name_then_id` |

Removing them means removing or changing those tests, which the review rules leave to you.

**Recommendation:** remove both with their tests (the `save_edit` tests keep their other checks),
so nobody brings back the name fallback by using `title`. Keeping them does no harm today.

**Built on branch `claude/review-items-25418b`, merged into `main` on 18 October (removed, with your request as the approval).**
Both are gone from `dataset_manager.py`. Tests removed, since they only tested these two:
`tests/test_display.py::test_unfinished_lists_memes_without_rating_or_description` and
`tests/test_memes.py::test_title_falls_back_to_the_gesture_name_then_id`. Tests changed: the two
`save_edit` tests in `tests/test_display.py` lost their `dm.unfinished` line, and
`test_save_edit_without_upload_keeps_the_image_and_can_clear_text` now checks the cleared rating
and description directly, so it checks what it checked before. Test added:
`test_no_meme_record_falls_back_to_the_gesture_name` (`tests/test_memes.py`), which fails while
either still exists. `docs/backend-handoff/ARCHITECTURE.md` no longer lists `unfinished`.

## Other notes (no decision needed now)

- R4-2 changed how the app listens: `.streamlit/config.toml` now has `server.address =
  "localhost"`. Before, Streamlit also listened on your local network (it printed a "Network URL"
  such as `http://192.168.0.203:8501`), and as no page has a sign-in, anyone on the same Wi-Fi
  could have deleted gesture data, retrained the model or replaced memes. Nothing changes on your
  own computer. If you ever open the app from another device or host it, that line has to change,
  and a sign-in comes first (CONFLICTS N12, OD-6).

- R1-12 changed one thing you can see: a meme upload that is not a JPEG, PNG, WebP or GIF image
  inside (for example a TIFF renamed `.png`) is now refused with the existing message "... cannot
  be read as an image. Choose a JPG, JPEG, PNG, WEBP or GIF file." Before, it was saved and showed
  as a broken image on the dashboard. Say if you would rather keep accepting such files.

- The three handoff zips in the project root are ignored by git; `backend-handoff-2026-10-17.zip`
  (and the others) hold a copy of your samples and model outside git. Delete or move them when you
  no longer need them (handoff section 10).
- Exact version pins in `requirements.txt` block security updates until someone updates a pin on
  purpose (handoff section 10). That is the trade-off you accepted for a pickled model and
  Streamlit-specific styling; review the pins when you next update anything.
