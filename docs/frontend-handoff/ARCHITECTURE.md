# Frontend architecture

## 1. How a page is drawn

```
streamlit run app.py
  │
  app.py
  ├─ st.set_page_config(title, favicon, layout="wide")
  ├─ ui.inject_css()                       the one CSS block (ui.CSS)
  ├─ st.navigation([...], position="top")  top nav, picks the page
  ├─ ui.leave_collector()                 every page but the collector cancels a recording
  ├─ st.set_page_config(page_title="<page> | <app>")  browser tab names the page
  └─ page.run()                            runs one views/*.py
       │
       views/<page>.py                     plain script, top to bottom, on every interaction
       ├─ ui.page_header(title, description)
       ├─ st.columns([3, 2], gap="large")  every two-column page uses this split
       ├─ with ui.panel("<key>"):          bordered card around Streamlit widgets
       │     ui.card_title("...")          real <h2>
       │     st.selectbox / st.button / st.form ...
       └─ st.markdown(ui.<x>_card(...), unsafe_allow_html=True)   HTML cards built in ui.py
```

Streamlit reruns the whole page script on every widget interaction. Objects that must survive a
rerun live in `st.session_state` (per browser tab) or `st.cache_resource` (shared by all tabs).

| Object | Where | Created by |
|---|---|---|
| `FrameProcessor`, `LandmarkHook` | `st.session_state` | `ui.get_vision()` |
| `LiveRecognizer` | `st.session_state` | `ui.get_recognizer()` |
| `Recorder` | `st.session_state` | `views/collector.py` |
| Loaded model (`Predictor`) | `st.cache_resource` | `ui.load_predictor()`, keyed on the model files' modification times, so a retrain is picked up without a restart |
| Memes form version | `st.session_state.meme_form_version` | `views/memes.py`, bumped after a successful save so the form resets |
| One-shot messages | `st.session_state.memes_msg`, `perf_msg` | Set before `st.rerun()`, shown once on the next run |
| Collector message | `st.session_state.collector_msg`, `collector_msg_seen` | Stays until a control on the collector is used (its `on_change` / `on_click` callback) or, once shown, until another page opens (`ui.leave_collector()`) |

## 2. Live refresh

Live panels use `@st.fragment(run_every=0.5)`. A fragment reruns only itself every 0.5 s, not the
whole page, so the camera iframe is never redrawn.

| Page | Fragment | Shows |
|---|---|---|
| Live dashboard | `camera_status` | Camera tag, hand tag, hint under the video |
| Live dashboard | `live_panels` | The Meme panel: meme and confidence meter (right column) |
| Live dashboard | `session_panels` | Live statistics tiles and Recent detections (second row) |
| Data collector | `recording_panel` | Countdown, recording progress, saving a finished recording |

The camera status and the result panels refresh at the same rate on purpose, so the hand tag
under the video never contradicts the Meme panel for more than one refresh.

The fragments only **read**: `processor.get_stats()`, `recognizer.latest()`, `.steady()`,
`.history()`. The frames themselves are handled on the WebRTC thread (see the backend handoff).
Never call the model or touch frames from a page.

## 3. The camera widget (`ui.camera_widget`)

- `webrtc_streamer(mode=SENDRECV, video_frame_callback=processor.process, async_processing=True)`.
  The callback mirrors the frame, draws the hand skeleton and returns it, so the video the user
  sees is the processed one.
- Constraints: ideal 640x480 at 30 fps, no audio.
- `translations={"start": "Start camera", "stop": "Stop camera"}`: the component's own button
  is the single toggle the owner asked for.
- `media_toggle_controls=False` and `controls=False` remove the extra camera, mute and play bars.
- `iceServers: []` on both ends: local only, so it also works offline. Hosting needs a TURN server here.
- The component renders in a same-origin iframe. `_IFRAME_SCRIPT` injects `_IFRAME_CSS` into it
  to hide "Select Device", make the background transparent and add the focus ring. If the iframe
  ever becomes cross-origin, the patch silently does nothing and the default buttons show.
- **Do not use `desired_playing_state`.** It hides the built-in button but makes the component
  retry `getUserMedia` hundreds of times per second when the camera is denied.
- `streamlit-webrtc` is pinned to 0.78.1 because of the iframe styling. Re-check after upgrading.
- When `ctx.state.playing` goes false, the dashboard calls `processor.reset()` and
  `recognizer.reset()` so stale numbers clear. Until that rerun, `ui.hand_tag` shows nothing
  unless frames are arriving, so "Camera off" never sits beside a hand count.

## 4. Pages

All pages start with `ui.page_header`. Two-column pages split 3:2. On a phone the columns stack
with a 1rem gap.

### Live dashboard (`views/dashboard.py`, default page)
- Notices at the top: model warnings (`st.warning`), "Retrain needed" (`ui.notice(ui.stale_notice(...), "warn")`),
  memes without an image (`ui.notice`, so "Memes" links to the page in the same tab).
- Left: **Camera** panel (video, "Show landmarks overlay" checkbox, camera and hand tags, hint).
  The checkbox has a key, so it stays one widget while its default (the camera's current
  setting) changes; without it every second click was lost. It has no help icon: Streamlit puts
  that icon inside the checkbox's label, so clicking it flipped the box. The same sentence is a
  hint under it instead (proposal PR-10).
- Right: one **Meme** panel (`ui.result_card`): the meme for the gesture being held and the confidence
  meter under it, nothing else. No gesture names on this page (owner's request, 17 October), except
  the fix-this messages and, for a gesture with no usable meme picture, Recent detections and the
  Latest meme tile (owner's decision, 18 October; `DESIGN_SYSTEM.md` section 4).
  It replaced the Recognition, Meme result and Top scores panels.
- On a phone (640 px and narrower, where the columns stack) the dashboard's camera is 60% of the
  width and centred, its 4:3 frame shrinking with it, so more of the Meme panel below is in the
  first screen (proposal PR-5, option C, the owner's layout). The collector's camera keeps the
  full width. CSS: `[class*="st-key-dashboard-camera"] iframe` in `ui.CSS`.
- Second row, same 3:2 split: **Live statistics** (six tiles: Latest meme as a small picture, Recognised
  this session, Gesture classes, Frames per second, Latency, Model) and **Recent detections**
  (`ui.history_card(..., library)`, memes as small pictures).

### Data collector (`views/collector.py`)
- Left: **Camera** panel with the live recording state (3 s countdown number, red dot and
  progress bar while recording); **Tips for good data**.
- Right: **Record a gesture** (gesture select or "New gesture...", name input, "Recorded by",
  samples slider 20 to 500, one Start/Stop recording button); **Your dataset** (per-gesture rows
  with a meter, undo last recording, delete a gesture behind a confirmation checkbox).
- While "New gesture..." is chosen and no name is typed, Start recording is disabled and the hint
  "Type a gesture name to start." shows under it (proposal PR-8).
- Under the gesture rows, one slot for the next step: "Add at least 2 gestures before training."
  with fewer than 2 gestures, or, once `data_collector.ready_to_train(summary)` holds (2 or more
  gestures, each with `MIN_SESSIONS_FOR_TRAINING` recordings), "You can train now: Train model is
  on the Model performance page." with an in-tab link (proposal PR-7; worded as the owner chose in
  PR-14, so "Ready" stays the gesture tag's word, which asks for more samples).
- Opening any other page cancels a recording in its countdown or while it records
  (`ui.leave_collector()`, called from `app.py` for every page but this one; owner's answer to
  `docs/review/OWNER_QUESTIONS.md` Q2, 18 October). Nothing of it is saved, so a recording only
  ends here or is dropped. A recording that already reached its target and waits to be saved is
  kept, and saved when you come back.
- Saving a recording, Undo and Delete report a busy or unreadable dataset, or a full disk, as a
  message ("Could not save: ..." or "Nothing was deleted: ...") instead of stopping the page.
- Messages appear in one slot (`st.empty()`) at the top of the right column, present in every run
  so the panels below never move. When they moved (Undo ends one run early with no message, then
  shows one), the browser kept a faded copy of Your dataset with the old numbers.
- A message stays until your next action on this page: every control has `on_click` or
  `on_change=dismiss`. Reruns you did not ask for (the camera component reruns the page when it
  mounts) keep it; before, a message such as "Saved 23 samples" showed for about 0.1 s. A
  recording dropped by leaving (above) leaves "The recording was stopped when you left the page.
  Nothing was saved." (`ui.RECORDING_STOPPED`) for when you come back (proposal PR-12).

### Model performance (`views/performance.py`)
- At the top, when the saved model cannot be loaded (but one was trained): an amber warning with
  the reason the dashboard shows, from `ui.load_predictor()`: "Model cannot be used: the Live
  dashboard cannot load it. <reason> The results below are from the training run that saved it."
  It has its own `st.empty()` slot, so the panels below never move (proposal PR-3).
- Full width: **Train** panel (Train model button; the run goes to a background `train_model.TrainingJob`,
  the button is disabled while it runs, and a progress bar shows "Training: N of M models trained",
  refreshed every 0.5 s), then four summary tiles (Held-out accuracy,
  Held-out cost, Macro F1, Recordings tested) and the training cautions in one box.
- Left: **Per gesture (held-out recordings)**, **Confusion matrix**.
- Right: **Gestures it mixes up**, **Confidence cutoff**, **Each recording, held out**.
- Full width: **Cost function** (explained without the word "gradient").
- Every number comes from `models/training_report.json`.
- With no report: "No trained model yet" and "Press Train model." once the data is ready for
  training (`data_collector.ready_to_train`), otherwise "Record at least two gestures on the Data
  collector page, then press Train model." (proposal PR-4).
- The model tag reads "softmax regression". The saved id (`model_name`) also names the training method in the word the UI avoids, so it is not shown raw.

### Memes (`views/memes.py`)
- Left: **Your memes** table (Image, Title, Rating, Description: Set or Missing per gesture);
  **Edit a meme** form (name 60, title 80, rating 40, description 400 characters; image up to 10 MB).
- Right: a live preview using the real `ui.meme_card(..., preview=True)` for the selected gesture, which says "in the form on this page" instead of linking to the Memes page.
- The Your memes table shows each state as a tag: Set (green), Not set (grey), image Missing (amber).
- One form per gesture and version, so unsaved text never leaks between gestures. A failed save
  keeps the text; a successful one resets the form.
- A save with no new image adds "The image was not changed." to its message. A file over the
  upload limit is refused by the upload box and reaches the page as no file at all, so this is how
  the message stays true in that case (proposal PR-13).

### Privacy policy, Terms and conditions (`views/privacy.py`, `views/terms.py`)
- Text in a `.legal` block, 70 characters wide. Operator name, email and governing law come from
  `config.py`. Until name and email are set, a warning banner shows at the top. Launch only when it is gone.
- The privacy page states that video is never stored and recent detections are memory only.
  Update it whenever data handling changes.

## 5. Shared helpers in `ui.py`

| Helper | Use |
|---|---|
| `inject_css()` | Adds `ui.CSS`. Called once in `app.py` |
| `page_header(title, description)` | Brand line, `<h1>`, description |
| `panel(key)` | `st.container(border=True, key="panel-<key>")`. Streamlit 1.65 adds class `st-key-panel-<key>`, which the CSS styles as a card. Always use this, never `st.container(border=True)` directly (tested) |
| `card_title(text)` | `<h2 class="ctitle">` inside a panel |
| `tag(text, kind)` | Status label, kind `ok`, `warn`, `bad`, `off` |
| `tile(label, value, unit, wide, note)` | Stat tile |
| `html_table(headers, rows, numeric_from, caption)` | Table in a focusable, labelled scroll region. Every cell is escaped except one wrapped in `Html(...)` |
| `notice(html, kind)` | A notice in the same look as `st.warning`, for text with an in-app link. Escape data in `html` |
| `confusion_table(labels, matrix)` | Confusion matrix with row and column headers |
| `confidence_bar(confidence, threshold, accepted)` | Bar with the threshold mark |
| `result_card(problem, prediction, playing, live, steady, records, load_error, library, camera_error=None, can_train=False)` | The dashboard's Meme panel: every state in one place (DESIGN_SYSTEM section 4). `camera_error` is the frame error from the camera stats, shown as "Camera problem"; `can_train` (the data is ready for training) makes "No trained model" say to train |
| `meme_card(label, records, load_error, library, preview=False)` | One gesture's meme without the meter: the Memes page preview. Images are shrunk to 900px / 250 KB for display and sent as data URIs |
| `meme_thumb(label, records, library)` | A gesture as a small picture of its meme, or its name when it has no image |
| `meme_alt(record)` | Alt text for every meme picture: the owner's title alone, or "Meme" when no title is set. Never the gesture name (owner, 18 October, OD-5 and Q3) |
| `stale_notice(stale)` | HTML for the "data changed since training" notice |
| `history_card(entries, total, model_ready, records, library=None)` | Recent detections; with `library` each row shows the meme as a small picture |
| `camera_widget(key, processor)`, `camera_state(stats, playing)`, `hand_tag(stats, live)` | Camera control and its status |
| `get_vision()`, `get_recognizer()`, `load_predictor()`, `model_state(problem, stale)` | Per-session objects and model status |
| `esc(value)`, `link(page, text)`, `pct(v)`, `score_pct(v)`, `clock(at)` | Escaping, in-app links, `n/a` for missing numbers, "over 99%" instead of a false 100% |

Where gesture names are shown (collector, performance, Memes page, and the dashboard's "fix this"
messages) they come from `dataset_manager.display_name(label, records)`, so every page shows the
same name ("Meme 3", not `meme_3`). The dashboard otherwise shows memes, never names, except that
a gesture with no usable meme picture is listed by that name in Recent detections and the Latest
meme tile (by its id when `memes.json` cannot be read), the owner's decision of 18 October.

## 6. Moving off Streamlit

If you rebuild the UI in another stack (for example React with a FastAPI backend), keep the
backend modules and rebuild: the per-session objects in section 1, a WebRTC or WebSocket frame
path into `FrameProcessor.process`, a 0.5 s poll or push of the recognizer state, and every state
and string in `DESIGN_SYSTEM.md`. Agree it with the owner first; Streamlit was their choice.

## 7. Tests for the UI

| File | Covers |
|---|---|
| `tests/test_style_rules.py` | Banned styles, radii, em dashes, badges, favicon, legal pages in the nav, single toggle buttons, no invented numbers |
| `tests/test_pages.py` | Streamlit AppTest runs of dashboard, collector, performance and Memes pages (with the camera patched out), panel helper, contrast, focus, upload limit, dashboard order, the overlay checkbox |
| `tests/test_display.py` | Display names on every panel, Memes form saving and refusals, confusion matrix contrast, image shrinking |
| `tests/test_status.py` | Model status, every recognition state distinct, no invented numbers, escaping, Recent detections |
| `tests/test_memes.py` | Meme records and the save path the form uses |

Add a test for any state, string or layout rule you change.
