# Handoff: Ball Knowledge Vision AI (all 8 stages built)

For the next session, or for you picking this up later. Read `01_PROJECT_CONTEXT.md` first. To have an AI continue the work, give it `02_BUILD_AND_CRITIQUE_PROMPT.md` with the other three files.

## 1. Where things stand

All eight stages are built and tested without a webcam. Your trained model reaches 97.4% on recordings it never saw, and replaying all 16 clips through the live path never showed a wrong gesture. What is left:

1. Your webcam run (README, "With your webcam", steps 1 to 9).
2. Writing the meme titles, Ball Knowledge ratings and descriptions on the new Memes page. All four are empty.
3. More data: a third first_meme recording, more samples for first_meme, meme_3 and second_meme, and clips in other light or rooms.

## 2. What changed in this session (14 October 2026)

Six critique-and-improve rounds on the finished app. Full evidence and scores: `docs/ui-critique-log.md`. Weighted score 7.53 to 8.59; the 9.0 gate is not met, because the camera and the new page have not run live.

| Round | Change | Files |
|---|---|---|
| 1 | One name per gesture on every panel (from `memes.json`); collector hint names every shortfall; bar legend; recordings named by time | `dataset_manager.py`, `ui.py`, `views/dashboard.py`, `data_collector.py`, `views/collector.py`, `views/performance.py` |
| 2 | **New Memes page** to set name, title, rating, description and image, with a live preview; dashboard notice for memes without a rating or description; **privacy page corrected** (it named a Google STUN server the app does not use) and a Meme images section added | `views/memes.py`, `app.py`, `dataset_manager.py`, `ui.py`, `views/dashboard.py`, `views/privacy.py`, `config.py` |
| 3 | Dashboard layout: Recognition and Meme beside the camera, statistics and detections in a row below; tiles with a second line for the latest gesture's time | `views/dashboard.py`, `ui.py` |
| 4 | Contrast measured; confusion-matrix shading capped so numbers stay at least 4.5:1 | `ui.py` |
| 5 | Large meme images shrunk for display (the panel refreshes twice a second); uploads over 10 MB refused | `ui.py`, `dataset_manager.py`, `config.py`, `views/memes.py` |
| 6 | Same names on the performance page; `none` reads "No gesture"; Memes form keyed per gesture; README updated | `views/performance.py`, `dataset_manager.py`, `views/memes.py`, `README.md` |

New tests: `tests/test_display.py` (24 test cases). The style tests also check the new page and the critique log. No existing test was changed. The suite now has 312 test cases.

Your previous versions of every changed file are in `docs/handoff/snapshots/before-stage8-critique/`. `docs/handoff/changes-stage8-critique.diff` shows every change.

## 3. Run it on the Mac

```bash
cd "/Users/kavishseema/Desktop/Passion Project"
source .venv/bin/activate
pip install -r requirements.txt      # nothing new is needed; this only checks
streamlit run app.py
```

Open http://localhost:8501 in Chrome and press Start camera. If `.venv` is missing or broken, recreate it with the Setup commands in `README.md`.

## 4. Test it

```bash
source .venv/bin/activate
python -m pytest -q
python check_pipeline.py "First meme" "Second meme" "Meme 3" "Meme 4" None
```

Expect 312 tests passed. In the review environment 307 passed and 5 could not run (4 Streamlit AppTest tests for the legal pages, 1 test using pytest's `capsys`); they passed on your Mac before this session. The clip replay should report "A wrong gesture was shown in 0 of 16 clips".

## 5. Results so far

**Training (real data, 14 October):** 380 samples, 16 recordings, 5 gestures. Held-out accuracy 97.4%, cost 0.1056, macro F1 0.973, l2 0.01. At the 70% cutoff 92% of predictions are accepted and 98.6% of those are right. Reproduced exactly on a second machine.

**Clip replay** (each clip classified by a model that never saw it; shares of the frames from the first to the last frame with a hand):

| Gesture | Clips | Right | Wrong | No gesture | Unsure | No hand |
|---|---|---|---|---|---|---|
| first_meme | 2 | 75% | 0% | 5% | 19% | 0% |
| meme_3 | 3 | 87% | 0% | 2% | 12% | 0% |
| meme_4 | 4 | 59% | 0% | 0% | 7% | 33% |
| none | 4 | 78% (No gesture) | 0% | | 21% | 1% |
| second_meme | 3 | 85% | 0% | 2% | 13% | 0% |

The meme_4 "no hand" share is real: the hand was lowered between attempts in those clips.

**Known behaviour:** meme_4 depends on who does it (with one person's clips held out, the other person's were read as none). The WebRTC stream starts at a lower resolution and rises within seconds. Opening a page URL directly logs two harmless 404s from Streamlit's health check.

## 6. Pages and shared code

| Page | File |
|---|---|
| Live dashboard | `views/dashboard.py` |
| Data collector | `views/collector.py` |
| Model performance | `views/performance.py` |
| Memes | `views/memes.py` |
| Privacy policy, Terms | `views/privacy.py`, `views/terms.py` |

Shared display code in `ui.py`: `recognition_card`, `meme_card`, `history_card`, `tile`, `html_table`, `confusion_table`, `camera_widget`, `camera_state`, `load_predictor`. Gesture names: `dataset_manager.display_name`. Saving from the Memes page: `dataset_manager.save_edit`.

## 7. Data contracts

- **`data/samples.csv`**: `session_id`, `label`, `person`, `timestamp`, `f000` onward. Written by `DatasetStore.append`; `DatasetStore.session_times()` gives each recording's start.
- **`data/dataset_meta.json`**: feature mode and length.
- **`models/gesture_model.joblib`, `label_mapping.json`, `training_report.json`**: written together by `train_model.train()`. The report holds `test` (accuracy, cost, per class, confusion matrix, cutoffs), `evaluation.per_recording`, `cost` (l2 options, history) and `warnings`.
- **`assets/memes/memes.json`**: gesture id to `gesture_name`, `meme_title`, `image_path` (relative, inside `assets/memes/`), `ball_knowledge_level`, `description`. Text limits: name 60, title 80, rating 40, description 400 characters.

## 8. Open items

1. Webcam run (README steps 1 to 9). Steps 7 to 9 also check the Memes page.
2. Memes page in real Streamlit (prompt Part 2).
3. Write the titles, ratings and descriptions.
4. Data gaps listed in section 1.
5. Keyboard-only pass; screen-reader announcement of results is not built.
6. Your decisions: Figma or Streamlit (built in Streamlit), per-gesture threshold, Prediction History page.
7. Before any public launch: your name and email in `config.py`, a legal review, HTTPS on a real domain.
