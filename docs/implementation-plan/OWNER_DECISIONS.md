# Decisions only the owner can make

Each decision has the options, a recommendation, the evidence and what waits on it. The
recommendation is advice; nothing here has been decided for you. Evidence sources are in brackets.
IDs match `ROADMAP.md` and `CONFLICTS.md`.

## Answers given on 18 October

| ID | Your answer | What was done |
|---|---|---|
| B1 | Webcam check with the current model: "it works just fine and I've tested all the steps" | Recorded as your report. `memes.json` was unchanged afterwards (modified 14 October), so step 7's save was not made on the real file |
| OD-1 | Follows from B1: no relaxed hand showed a meme | Threshold stays 0.70; no change to `config.py` |
| OD-8 | Local git, data tracked too | Repository created with no remote; video folders, screenshots, zips and `to be deleted/` ignored |
| OD-5 | Meme title, else "Meme" | `ui.meme_alt`; tests now check alt text too |
| OD-9 | Keep the new notice colours | No change needed |
| OD-10 | Camera hint fix approved. Augmentation line and classes-tile note **not** approved | Hint changed; the other two left as they are |
| OD-11 | Put the old folders in one folder named "to be deleted" | Done; nothing deleted |
| Meme titles | first_meme "Stressed Higuruma", second_meme "Peace Out", meme_3 "Absolute Cinema", meme_4 "I Guess Bro" | Written with `dataset_manager.py`; ratings and descriptions still empty for you |

Still open: OD-2, OD-3, OD-4 (titles now show under the meter, as the current behaviour does),
OD-6, OD-7 (your next recordings), OD-12, OD-13 to OD-15.

## Quick list, most urgent first

| ID | Decision | Recommendation | Blocks |
|---|---|---|---|
| OD-8 | Version control | Local git, no remote, one main branch | A1, and safe parallel work |
| OD-1 | Confidence threshold for the 17 October model | Keep 0.70 for now; decide right after your webcam check | B2, B4 |
| OD-5 | Alt text that names the gesture | Use the meme title when you set one, otherwise just "Meme" | B6, C4 |
| OD-7 | What to record next | The list in OD-7 | B3, then B4, B7, C7 to C9 |
| OD-11 | Archive the old critique documents | Yes, move them to `docs/archive/` | A5 |
| OD-4 | Show your meme text on the dashboard | Yes, under the meter once you write it (as now) | B5 makes sense |
| OD-9 | Notice colours | Keep the new ones | C3 |
| OD-10 | Four small wording changes | Approve all four | C3 |
| OD-12 | Confirm the decisions already made (Part 1) | Confirm, and say whether Figma is still an option | reviewers |
| OD-2 | Per-gesture thresholds | Later, after more data | C9 |
| OD-3 | Prediction History page | Do not build | C11 |
| OD-6 | Hosting and launch | Stay local until Phase B is done | All of Phase D |
| OD-13 | The `/train` command trains the live model | Keep it as your own command | none |
| OD-14 | A new feature layout (hand position) | Nothing to decide now | C7 |
| OD-15 | Show terminal training on the page | No | C10 |

## Part 1. Decisions already made, to confirm

These overrule parts of the original spec. Recording them in one place stops a reviewer from
"fixing" the app back to the spec (CONFLICTS N8).

| Decision | Spec it overrules | Made | Source |
|---|---|---|---|
| The model is softmax regression by gradient descent, not a Random Forest | `Instructions.md` 3, `Context.md` 4 | Owner, 13 October | ML handoff, decisions table; root README "Why gradient descent" |
| The Live dashboard never names a gesture; one Meme panel with the meter | `Context.md` 6B and 6C, `Instructions.md` 5B and 5C (gesture name, top predictions, gesture label) | Owner, 17 October | Frontend CHANGES section 2 |
| Exception to the row above: a gesture with no usable meme picture is listed by name (by id when `memes.json` cannot be read) in Recent detections and the Latest meme tile | none (refines the row above) | Owner, 18 October | `docs/review/OWNER_QUESTIONS.md` Q6, option A |
| No animations, gradients, pills, purple, shadows, emoji, em dashes | `Context.md` 6 ("subtle animations") | Owner, design rules | `tests/test_style_rules.py`; `LAUNCH_CHECKLIST.md` |
| Landmark augmentation adopted; training runs to the minimum, no 50-epoch cap | none | Owner confirmed the cap decision, 17 October | ML handoff |
| Recent detections stay in memory only | `Context.md` 2 mentions files for prediction history | Owner, privacy page | `views/privacy.py`; DATA_CONTRACTS |
| Streamlit, not Figma | `Instructions.md` 1 ("Figma for the web dashboard") | **Unclear**: the frontend handoff says you decided; `01_PROJECT_CONTEXT.md` 7.1 and `04_HANDOFF.md` 8.5 say "still undecided" (CONFLICTS N9) | Please confirm |

**OD-12.** Please confirm this table is right, and say whether Figma is still an option. Recommendation: confirm Streamlit; everything is built and tested in it.

## Part 2. Decisions waiting

### OD-1. Confidence threshold for the 17 October model

The model retrained on 17 October is surer of itself, so at the same 0.70 cutoff memes come up more
often and sooner than in the version you tested on 14 October.

| Option | What it means |
|---|---|
| A. Keep 0.70 | Memes on screen for 75.8% of hand frames in the clip replay, 0 wrong memes |
| B. Raise to 0.80 | 71.7% of hand frames, 0 wrong memes. About the same responsiveness you saw on 14 October (71.5% at 0.70), with a larger margin |
| C. Something else | Any value; it must be re-checked with the clip replay |

**Recommendation:** keep 0.70 for now and make the final call straight after your webcam check (B1).
If a relaxed hand ever shows a meme (step 4), or any gesture shows the wrong meme (step 3), choose 0.80.
Otherwise keep 0.70.

**Evidence:** held-out cutoff table: at 0.70, 95.8% of frames pass and 98.6% of those are right; at
0.80, 91.6% pass and 99.1% are right (`models/training_report.json`, `test.thresholds`). Clip replay
numbers from `docs/ml-handoff/RESULTS_AND_DATA.md` section 3; the 0.70 replay was re-run by the
strategist with the same result. The clips are Photo Booth video, not your webcam, so the safety margin
on webcam frames is not measured. The frames wrong at 0.70 or more come from three `none` recordings
(ML results, section 2). The value was chosen by the ML session, not by you.

**Blocked until decided:** B2 (and any change to `config.py`), the comparison baseline for B4.

### OD-2. Per-gesture confidence thresholds

The spec gives each meme its own `confidence_threshold` (`Context.md` section 5). Today there is one for all.

| Option | What it means |
|---|---|
| A. One threshold for all, permanently | Simplest; a known spec deviation |
| B. Per-gesture now | Needs a new field in `memes.json`, predictor and meter changes |
| C. Later, after more data | Decide again after B3 and B4 |

**Recommendation:** C.

**Evidence:** second_meme has 28 samples in recordings of 8 to 10 samples each, and first_meme has
only 2 recordings (`SYSTEM_STATE.md` section 3.3). A per-gesture cutoff fitted on that little data would
be mostly noise. The ML handoff (next steps, item 6) says the same.

**Blocked until decided:** C9.

### OD-3. Prediction History page

| Option | What it means |
|---|---|
| A. Do not build | Recent detections on the dashboard (last 10, memory only) covers it |
| B. A memory-only page with the whole session | You must also decide whether that page may name gestures; your rule covers the dashboard |
| C. Saved history | Changes the privacy promise; needs a privacy page update |

**Recommendation:** A.

**Evidence:** `Context.md` section 6 lists it as optional and warns against features that make the
first version unreliable. The privacy page promises memory only (`views/privacy.py`).

**Blocked until decided:** C11 only.

### OD-4. Show your meme title, rating and description on the dashboard

The frontend made a judgement call: these show under the meter **only when you have written them**.
None are written, so today you see the meme and meter only.

| Option | What it means |
|---|---|
| A. Show them when set (current) | Your text appears once you write it on the Memes page |
| B. Never on the dashboard | Memes page only; a spec deviation |
| C. Title only | A shorter panel |

**Recommendation:** A.

**Evidence:** the spec's success criteria ask for the rating and description to be shown
(`Instructions.md` section 10 item 5, `Context.md` section 10 item 4). The frontend handoff
(decisions table) says removing them is one block in `ui._meme_view`.

**Blocked until decided:** whether B5 (writing the texts) changes the dashboard; README step 9.

### OD-5. Alt text that names the gesture (new)

Images on the dashboard carry hidden text for screen readers. Today it reads "Meme: First meme",
"Meme: Meme 3" and so on, because it uses the meme title and falls back to the gesture's name when
no title is set (`ui._meme_view`, `ui.meme_thumb`, `MemeRecord.title`). The tests skip alt text on
purpose (`tests/test_status.py`, `visible()`), and no handoff told you.

| Option | What it means |
|---|---|
| A. Keep, and record it as the one exception | Screen-reader users hear gesture names |
| B. Always just "Meme" | Your rule holds fully; screen-reader users cannot tell memes apart |
| C. Your meme title when set, otherwise "Meme" | Your rule holds; once you write titles (B5), screen-reader users hear them |

**Recommendation:** C.

**Evidence:** code above; your 17 October rule (frontend CHANGES section 2).

**Blocked until decided:** B6 and the screen-reader work C4.

### OD-6. Hosting and launch

| Option | What it means |
|---|---|
| A. Stay local | As today; nothing in Phase D starts |
| B. Host for yourself only | Needs HTTPS, a TURN server and a sign-in |
| C. Public site | All of Phase D, a legal review, and per-visitor data handling |

**Recommendation:** A until Phase B is done, then decide between B and C.

**Evidence:** `Context.md` section 9: cloud deployment only after reliable local use.
`LAUNCH_CHECKLIST.md`: legal pages need your name and email; custom domain not done. Also missing
from the checklist (CONFLICTS N12): **no page has a sign-in**, so on a hosted copy anyone could record
into your dataset, retrain your model, delete gesture data or upload images. If you choose B or C,
please agree to adding "Owner-only actions need a sign-in" to `LAUNCH_CHECKLIST.md`.

**Blocked until decided:** all of Phase D.

### OD-7. What to record next

The single biggest lever on quality (ML handoff, "Risks and recommended next steps"). Targets from
`config.py`: at least 100 samples (`TARGET_MIN_PER_CLASS`) and 3 recordings (`MIN_SESSIONS_PER_CLASS`)
per gesture.

| Gesture | Today | Ask |
|---|---|---|
| first_meme | 58 samples, 2 recordings | At least 1 more recording (the report warns about having only 2), better 2 |
| second_meme | 28 samples, 3 recordings of 8 to 10 samples | 2 or more longer recordings: hold the gesture for the full Data collector countdown and progress bar |
| meme_3 | 48 samples, 3 recordings | 1 or 2 more recordings, to pass 100 samples |
| meme_4 | 127 samples, 4 recordings, filmed by someone else | At least 2 recordings by **you**, since meme_4 looks person-dependent |
| none | 119 samples, 4 recordings | 1 or 2 recordings in the new room or light; `none` read as a gesture is the main error (7 of 11) |

For every new recording:

- Fill in "Recorded by" on the Data collector page (or `--person` when importing). Today it is empty
  in all 380 rows, so the model cannot be tested on a new person.
- Record at least one per gesture **with the webcam on the Data collector page**, since all current data
  is Photo Booth video and the live stream differs.
- Use at least one other room or light, and if a friend can, have them record each gesture once.

**Recommendation:** the table above, after the webcam check (B1), starting with any gesture that
stayed "Unrecognised" during it.

**Evidence:** `SYSTEM_STATE.md` section 3.3; report warnings; ML handoff next steps 2 and 3.

**Blocked until decided:** B3, then B4, B7, C7, C8 and C9.

### OD-8. Version control

Three sessions edited the same files on 17 October with no way to roll back except zips and snapshots.

| Option | What it means |
|---|---|
| A. Local git, one main branch | Each department commits only its own files after the standard check |
| B. Local git, one branch per department | Branches only help if each session works in its own copy (git worktrees); in one shared folder a branch switch affects everyone |
| C. No git | Keep zips and snapshots |

**Recommendation:** A now; move to B with separate worktrees only if parallel code work grows. Keep
it local, with no remote, unless you decide otherwise. The raw video folders (faces) must never be
added. Tracking `data/samples.csv`, `models/` and `assets/memes/` locally gives you a rollback; they
are small (about 380 KB, 30 KB and 185 KB), but the privacy page calls the samples personal data, so
never push them anywhere without a separate decision.

**Evidence:** backend handoff conflict 5; frontend handoff risk table; `SYSTEM_STATE.md` section 5.

**Blocked until decided:** A1, and with it safe parallel work.

### OD-9. Notice colours

The frontend restyled warnings, errors and info notes into the site palette (faint amber, red,
green, grey). Asked during its first pass; no answer recorded.

**Recommendation:** keep them. They replaced the only colours outside the palette (Streamlit's olive
and blue). Reverting is one CSS block in `ui.CSS` (frontend handoff, decisions table).

**Blocked until decided:** C3.

### OD-10. Four small wording changes

| # | Change | Recommendation |
|---|---|---|
| a | Model performance shows the model as "softmax regression" (the saved id also says "gradient descent", a word banned in UI text) | Approve |
| b | Add one line on Model performance: training also learns from 4 slightly turned copies of each sample, and "Cost at the end" is measured over those rows (CONFLICTS N11) | Approve; the honest-numbers rule asks to say what a number was measured on |
| c | The "Gesture classes" tile shows 5, which counts "No gesture", while there are 4 memes (CONFLICTS N19) | Keep 5 and add the note "including No gesture" |
| d | The camera hint after a missing hand model says "Then stop and restart the camera"; the camera now recovers by itself within 2 seconds (CONFLICTS N15) | Change it to say the camera picks the model up by itself |

**Blocked until decided:** C3.

### OD-11. Archive the old critique documents

`New files fopr critiquing/`, `old files for critiquing/` and `Claude outputs/` describe the dashboard
before 17 October (Recognition panel, gesture names in green, Top scores). One of them,
`02_BUILD_AND_CRITIQUE_PROMPT.md`, is a prompt meant to be given to an AI; used today it would ask
for gesture names back on the dashboard (CONFLICTS K4).

**Recommendation:** move all three folders to `docs/archive/2026-10-14/` with a short note at the top.
The current documents are `docs/implementation-plan/`, the three `docs/*-handoff/` folders and the root `README.md`.

**Blocked until decided:** A5.

### OD-13. The `/train` command

`.claude/commands/train.md` trains on your real data and replaces the live model. That is right when
you use it. Departments testing must use scratch folders instead (CONFLICTS N13).

**Recommendation:** keep it as your command; departments never run it.

### OD-14. A new feature layout (later)

Three gestures are defined by where the hand is relative to the face, which today's features ignore
(ML architecture section 2). Changing the features is your decision. **Nothing to decide now:** ML will
bring a comparison after the next recordings (C7).

### OD-15. Show a terminal-started training run on the page

A run started with `python train_model.py` is invisible to the Model performance page; pressing Train
model meanwhile says another run is in progress (backend handoff conflict 4).

**Recommendation:** no, unless it bothers you; the README troubleshooting section already explains it.

**Blocked until decided:** C10.
