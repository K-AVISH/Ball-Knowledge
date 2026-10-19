# Design system

Flat, dark, one accent colour, small corners, no motion. Everything below is in `ui.CSS`
(`ui.py`) and `.streamlit/config.toml`. Change a value in both places when it appears in both.

## 1. Colour tokens

| Token | Value | Use |
|---|---|---|
| `--bg` | `#0b0f0d` | Page background (also `backgroundColor`) |
| `--surface` | `#111815` | Cards and panels (also `secondaryBackgroundColor`, which Streamlit uses for widget fill) |
| `--surface2` | `#151d19` | Tiles inside cards, table cells, image backing |
| `--border` | `#212c26` | Card and table borders |
| `--text` | `#e6ece8` | Main text (also `textColor`) |
| `--muted` | `#8c9b93` | Labels, hints, captions |
| `--accent` | `#2fbf71` | The one accent: recognised, ok tags, bars, links, focus rings (also `primaryColor`) |
| `--warn` | `#e0b04a` | Unrecognised, retrain needed, short of data |
| `--bad` | `#e5645f` | Errors, recording dot |
| widget outline | `#5f7067` | `borderColor` with `showWidgetBorder = true`: text boxes are the same fill as panels, so they need this edge (3.4:1) |
| button hover | `#45c983` | Green buttons lighten on hover instead of Streamlit's darker green |

Measured contrast (critique round M4): green buttons use dark text `--bg` on `--accent`, 8.1:1
(Streamlit's default white text was 2.38:1); hovered 9.1:1. Do not bring back white text on green.

Banned: purple, violet, indigo, magenta, any gradient, box or text shadows. The one allowed form is
`box-shadow:none !important`, which removes the shadow the camera library puts on its button (the test strips exactly that string).

## 2. Type and spacing

- Font: Streamlit's sans serif (`font = "sans serif"`).
- Page title 1.75rem, weight 650. Brand line above it .78rem uppercase, muted.
- Card titles: real `<h2>`, .74rem, uppercase, letter-spacing .1em, muted.
- Big text (`.big`) 1.5rem, weight 650: the owner's meme title under the meter.
- Numbers use `font-variant-numeric: tabular-nums` so they do not jump while updating.
- Content max width 1280px. 1rem between stacked panels. Columns split 3:2 with a large gap.
- Phones (640px and narrower, columns stacked): the Live dashboard's camera is 60% of the width,
  centred (proposal PR-5); every other panel keeps the full width.
- Radius: 6px for controls (`baseRadius`), 8px for cards and tiles, 4px for tags, 2px for bars,
  50% only for the recording dot. Nothing else (tested).

## 3. Components

| Component | Class or helper | Notes |
|---|---|---|
| Card (HTML) | `.card` | Surface fill, 1px border, 8px radius, `h2` title |
| Panel (widgets) | `ui.panel(key)` | Same look as `.card`, for panels that hold Streamlit widgets |
| Tag | `ui.tag(text, kind)` | `ok` green, `warn` amber, `bad` red, `off` grey. A label, never a button |
| Stat tile | `ui.tile(...)` | Uppercase label, large tabular number, optional unit and second line. Each tile spans three rows of its grid through CSS subgrid, so values in a row line up even when one label wraps |
| Tile grid | `.tiles`, `.tiles.three`, `.tiles.four` | Two columns under 720px |
| Confidence bar | `ui.confidence_bar` | 8px bar, green when accepted, amber when below, white mark at the threshold, both numbers underneath |
| Empty state | `.empty` | Dashed border, bold title, one sentence on what to do |
| Table | `ui.html_table` | Caption, row headers, right-aligned numbers, scrolls inside a focusable region on narrow screens. Cells are escaped; wrap a cell in `ui.Html(...)` only when it is HTML built from escaped parts (a status tag). Under 480px tables tighten and a tag in a table shows as its coloured word alone |
| Confusion matrix | `ui.confusion_table` | Cells shaded by count with AA text contrast on the darkest cells |
| Hint | `.hint` | Muted .88rem sentence under a control or result |
| Notice | `st.warning`, `st.error`, `st.success`, `ui.notice(html, kind)` | One flat look: 1px border and a faint tint of `--warn`, `--bad` or `--accent`, neutral grey for info, text always `--text`. Streamlit's own olive and blue are overridden in `ui.CSS`. Use `ui.notice` when the text needs an in-app link (Streamlit's notices open links in a new tab) |
| Camera frame | `_IFRAME_CSS` | With the camera off or connecting the video area is a 4:3 frame with a dashed edge, the same size the video then fills, so nothing below it moves. The camera button has no shadow and no click ripple and lightens to `#45c983` on hover like the page's green buttons. The library's own error (camera denied) uses the red notice look |
| Meme frame | `.meme-frame`, `.meme-img` | 4:3, `--surface2`, the image `object-fit: contain`; `.meme-frame.msg` holds a state message instead (dashed edge, `.warn` amber, `.bad` red) |
| Meme thumbnail | `ui.meme_thumb`, `.thumb` | 52x39 (64x48 in a tile), a still made once per image file (`_thumb_uri`, 120px) |
| Countdown | `.count` | 3rem green number on the collector |
| Gesture row | `.cls` with `.meter` | Collector dataset list, meter green, amber or red |

Focus: every link, scroll region, button and the page area show a 2px `--accent` outline on
`:focus-visible`. The camera button inside the iframe gets the same through `_IFRAME_CSS`.
A checkbox's visible box gets it while its hidden input has keyboard focus. Text boxes turn
their border green (Streamlit's own). In a narrow window the page links move into a menu;
while it is closed it is hidden (`visibility: hidden`), so Tab never stops on a link out of view.

Hidden Streamlit chrome: toolbar actions, main menu, Deploy button, decoration bar and footer.

## 4. The Meme panel and its states (dashboard)

The owner's rule (17 October): beside the camera, show only the meme for the gesture being held,
with the confidence meter under it. **The dashboard never names a gesture** ("Meme 3", "First meme"):
not in this panel, not in Live statistics, not in Recent detections, where memes appear as small
pictures (`ui.meme_thumb`). The other pages (collector, performance, Memes) still use names, since
there the owner has to tell gestures apart to record, judge and edit them.

The exceptions: the messages that ask the owner to fix a gesture (below), and, by the owner's
decision of 18 October, a recognised gesture with no usable meme picture (no meme set, its image
missing, or `memes.json` unreadable). Recent detections and the Latest meme tile list such a
gesture by its display name, which is its id when it has no name set or `memes.json` cannot be read.

All states are worked out in one function, `ui.result_card`. The meme sits in a 4:3 frame
(`.meme-frame`); every other state puts a short message in that same frame, so the panel never
changes size. Tests check each message is distinct and that no state shows a gesture name.

| State | In the frame | Meter |
|---|---|---|
| No model | "No trained model", links to Data collector and Model performance. Once the recorded data is ready for training (`data_collector.ready_to_train`), "Train a model on the Model performance page." instead (proposal PR-4) | n/a |
| Model unusable | "Model cannot be used" and the reason (red edge) | n/a |
| Camera off | "Camera off. Press Start camera." | n/a |
| Camera starting | "Waiting for video" | n/a |
| Frames cannot be processed (for example the hand model missing) | "Camera problem", pointing to the message under the video (red edge). It hides a meme that was steady, since no new frame reaches the model (owner's decision Q1, 18 October) | n/a |
| No prediction yet | "Starting" | n/a |
| Prediction error | "Prediction failed" and the error (red edge) | n/a |
| No hand in view | "No hand in view" | n/a |
| Below threshold | "Unrecognised", below the 70% threshold (amber edge) | The top score, amber |
| A gesture recognised in a frame, not yet steady | "Hold it steady", needs 4 of the last 7 frames | That frame's score, green |
| `none`, steady or in a single frame | "No gesture". A single `none` frame needs no vote, since no meme is at stake; a meme already held stays until the vote changes (proposal PR-2) | n/a |
| Steady gesture | **The meme** | Its average over the confirming frames, green |

Under the meter, only texts the owner has written: meme title, "Ball Knowledge: ..." tag and
description, each only if set. Nothing says "not set" on the dashboard.

Alt text on every meme picture (`ui.meme_alt`) is the meme title alone ("Absolute Cinema") when
the owner set one, otherwise "Meme": the panel and the Recent detections column are already headed
"Meme". It never names the gesture, and `tests/test_status.py` checks the panel HTML including alt
text (owner's decisions OD-5 and Q3, 18 October).

Problems that need fixing name the gesture, because the owner must know which one: "No meme set"
(amber edge, no record) and the top notice "No usable meme image yet for: ...". Also "Image missing"
(red edge) and "Memes cannot be shown" (red edge, `memes.json` broken).

"Retrain needed" is an amber notice at the top of the page (`ui.stale_notice`), not part of the panel.

Confidence wording: the meter's tooltip says "the model's own estimate, not a calibrated
probability". A score that rounds to 100% shows as "over 99%", one that rounds to 0% as
"under 1%". Missing numbers show `n/a`.

## 5. Copy rules

- Plain, concrete sentences that say what to do next ("Press Start camera."). No hype, no vague hero text.
- No em dashes, no emoji or decorative symbols (arrows, stars, check marks).
- The Live dashboard never names a gesture; it shows memes (section 4 lists the exceptions). Elsewhere gestures are
  shown by their display name from the Memes page, with the id only where the user needs it
  (collector dataset list: "First meme first_meme").
- The model is softmax regression trained step by step downhill on a cost; UI text never says "gradient".
- Never claim something was tested or measured when it was not.
- Buttons: Start camera / Stop camera, Start recording / Stop recording, Train model, Save meme,
  Delete gesture data. Success messages are green `st.success`, failures start "Nothing was saved:"
  ("Nothing was deleted:" when Undo or Delete gesture data cannot change the dataset).

## 6. Assets

- Favicon: `assets/favicon.png`, set through `config.FAVICON_PATH`. Replace the file to change it (a test checks it is a real PNG).
- Meme images: `assets/memes/<gesture id>.<ext>`, chosen by the owner. No stock or AI-generated images.
- No logo exists. The brand is the text "Ball Knowledge Vision AI" (`config.APP_TITLE`).
