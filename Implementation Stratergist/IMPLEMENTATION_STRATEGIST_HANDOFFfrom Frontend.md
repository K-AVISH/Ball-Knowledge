# Frontend handoff for the implementation strategist

17 October 2026. What the frontend work delivered, what it decided, what it depends on, and what
should come next. The detailed change list is `CHANGES_2026-10-17.md` in this folder; the page
and styling reference is `ARCHITECTURE.md` and `DESIGN_SYSTEM.md`.

## 1. Where the frontend stands

| Area | State |
|---|---|
| Pages | Six, all working: Live dashboard, Data collector, Model performance, Memes, Privacy policy, Terms and conditions |
| Live dashboard | Camera on the left. On the right, one Meme panel: the meme for the gesture being held, with the confidence meter under it. No gesture names anywhere on the page (owner's rule) |
| Tests | `python -m pytest -q`: 413 passed from the unzipped handoff (includes the backend session's tests) |
| Browser check | Chrome-based browser at 1280x900 and 390x844, scratch data, stand-in camera fed from one of the owner's Meme 3 clips |
| Owner's webcam | Step 3 of the README "With your webcam" table reported working on 17 October. Steps 1, 2 and 4 to 9 not recorded |
| Delivery | Project folder and `frontend-handoff-2026-10-17.zip` hold the same code. No git repository, so nothing is versioned |

## 2. Decisions made, and who made them

| Decision | Made by | Consequence |
|---|---|---|
| The dashboard shows memes, never gesture names | Owner, 17 October | Recognition headline, name tags, Top scores table and the "rating not set" notice were removed. Latest meme and Recent detections use small meme pictures. Names stay on collector, performance and Memes pages and in "fix this" messages |
| Owner-written title, rating and description show under the meter only when set | This session (judgement call, told to the owner) | Today none are set, so the panel is meme plus meter only. Easy to remove if the owner wants it stricter (`ui._meme_view`, the `owner` block) |
| Notices restyled into the site palette (amber, red, green tints, grey for info) | This session; the handoff says colour scheme changes need the owner | Asked the owner whether to keep them; no answer recorded. Treat as pending approval. Reverting is one CSS block in `ui.CSS` |
| Model tag reads "softmax regression" | This session, enforcing the existing copy rule (no "gradient" in UI text) | Flagged to the owner as model wording |
| Every state keeps a fixed 4:3 frame (camera and meme) | This session | No layout jumps between states; a camera that is not 4:3 still shifts the camera panel a little |
| Streamlit stays the stack | Owner, earlier | All work is CSS and HTML strings in `ui.py`; no JavaScript build |

## 3. Dependencies and risks

| Risk | Why it matters | Mitigation in place | Suggested action |
|---|---|---|---|
| Two sessions editing the same files | Backend Guy and the frontend session both edited `views/dashboard.py` and `views/performance.py` the same day | Line-level edits only, re-read before editing; both sets intact | Put the project under git before more parallel work, one branch per role |
| Styling relies on Streamlit internals | Selectors such as `[data-testid="stAlertContainer"]`, `stAlertContent*`, `st-key-panel-*` | Streamlit pinned at 1.65.0; tests check the selectors exist | Re-check in the browser after any Streamlit upgrade |
| Camera styling relies on streamlit-webrtc internals | `_IFRAME_CSS` targets MUI classes (`.MuiPaper-root`, `.MuiAlert-root`, `.MuiButton-contained`) inside a same-origin iframe | Pinned at 0.78.1; if the iframe becomes cross-origin, the default look returns, nothing breaks | Re-check after any upgrade |
| Modern CSS | Subgrid (tiles) and `:has()` (notices) | Supported in current Chrome and Safari | Safari is unverified; include it in the next test pass |
| Images sent every refresh | The Meme panel refreshes twice a second with the meme as a data URI (shrunk to 900px / 250 KB); thumbnails are 120px and cached | Fine locally | Revisit before hosting over the internet |
| No screen-reader announcement | A new meme is not announced | None yet | Needs a VoiceOver test of a live region (see section 4) |

## 4. Open work, in suggested order

| # | Item | Owner input needed | Size | Notes |
|---|---|---|---|---|
| 1 | Finish the webcam check (README steps 1, 2, 4 to 9) | Yes, only the owner can run it | Small | Step 4 (relaxed hand never shows a meme) is the most important result |
| 2 | Confirm the notice colours | Yes, a yes or no | Trivial | Pending since the first pass |
| 3 | Put the project under git | Agreement on workflow | Small | Prerequisite for safe parallel sessions and rollbacks |
| 4 | Safari check | No | Small | Camera (WebRTC), subgrid tiles, `:has()` notices |
| 5 | Screen-reader announcement of a new meme | No, but needs VoiceOver testing | Medium | A polite live region announcing only changes of steady meme, not every refresh |
| 6 | Meme titles, ratings, descriptions | Yes, the owner writes them | Owner's time | Never fill them in for the owner |
| 7 | Launch items (`LAUNCH_CHECKLIST.md`) | Yes | Medium to large | Custom domain with HTTPS, TURN server for WebRTC, operator name and email in `config.py`, legal review |
| 8 | Prediction History page (optional in `Context.md`) | Yes, a decision | Medium | Recent detections covers it today, memory only |

## 5. Rules any next step must keep

From the owner, enforced by tests in `tests/test_style_rules.py` and `tests/test_pages.py`:

- No vibe-coded look: no emoji, em dashes, gradients, animations, pill shapes, purple, shadows
  (the one exception is `box-shadow:none` to remove a library's shadow), stock or AI images.
- No invented numbers; missing values show `n/a`.
- One control per action: one camera button, one recording button.
- Uncertain means no meme.
- The dashboard never names a gesture.
- The word "gradient" never appears in UI text.
- Data from files or users is escaped before it goes into HTML.
- Test on scratch data (`BALLKNOWLEDGE_DATA_DIR`, `BALLKNOWLEDGE_MODEL_DIR`); never on the
  owner's real `data/`, `models/` or `assets/memes/`.

## 6. Where to look

| Need | File |
|---|---|
| Every change with before and after | `docs/frontend-handoff/CHANGES_2026-10-17.md` |
| How pages are built, helpers | `docs/frontend-handoff/ARCHITECTURE.md` |
| Colours, components, every Meme panel state | `docs/frontend-handoff/DESIGN_SYSTEM.md` |
| Decision history with measured evidence | `docs/ui-critique-log.md` |
| Manual test with a webcam | `README.md`, "With your webcam" |
| Backend side | `docs/backend-handoff/`, `docs/ml-handoff/` |
