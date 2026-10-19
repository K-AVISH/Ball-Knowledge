# AI/ML handoff: Ball Knowledge Vision AI

Written 17 October 2026 for the AI/ML engineer taking over the gesture model.
Start here, then read the other files in this folder.

| File | What it covers |
|---|---|
| `README.md` (this file) | What the model does, current state, setup, how to run experiments safely, open work |
| `ARCHITECTURE.md` | The ML pipeline end to end: landmarks, features, model, training, evaluation, live decision rule |
| `RESULTS_AND_DATA.md` | The dataset, every measured result, past experiments, known weaknesses, ideas worth testing |

## Context files to read (in this order)

| File | Why |
|---|---|
| `docs/ml-handoff/*` | This handoff |
| `Context.md` | The original spec. Section 4 (training requirements), 7 (stability) and 11 (never fabricate scores) bind the model work |
| `README.md` (project root) | "Train the model" explains the model choice in the owner's words; "Test the whole pipeline" explains the clip replay |
| `config.py` | Every ML setting: feature mode, l2 options, tolerance, threshold, voting window |
| `features.py`, `gd_model.py`, `train_model.py`, `predictor.py` | The ML code, about 1,240 lines in total, well commented |
| `models/training_report.json` | The current model's full evaluation |
| `docs/backend-handoff/DATA_CONTRACTS.md` | Exact file formats for samples, model and report |
| `docs/implementation-plan/OWNER_DECISIONS.md` | Decisions already made that overrule the brief (Part 1), and the ones still open |

If you received `ml-handoff-2026-10-17.zip`: it holds the code, tests, these files, the training
data (`data/samples.csv`, landmark numbers only) and the current model. It leaves out the MediaPipe
models (run `python download_models.py --pose`) and the raw gesture videos, which show people's
faces. Without the videos you cannot re-extract features or run `check_pipeline.py` on the real
clips; ask the owner if you need them.

## 1. What the model does

A webcam frame goes through Google's MediaPipe hand landmarker (pretrained, not ours), which gives
21 3-D points per hand. `features.py` turns up to two hands into a 126-number vector that describes
hand shape only. Our own classifier, **softmax regression trained by gradient descent**
(`gd_model.py`), gives a probability per gesture. The live app accepts the top gesture only above
a 0.70 confidence and only once it wins 4 of the last 7 classified frames. Then the dashboard shows
that gesture's meme.

Five classes: `first_meme` (both hands over the face), `second_meme` (sideways V sign by the eye),
`meme_3` (both open palms raised), `meme_4` (one hand over the eyes), `none` (a hand that is not a
gesture; never shows a meme).

The owner chose this model on 13 October after asking for "minimum cost function, gradient descent
or gradient boosting". Gradient boosting and forests were measured and lost on held-out cost (see
`RESULTS_AND_DATA.md`). **Changing the model family is the owner's decision. Bring numbers.**

## 2. Current state (verified 17 October 2026)

- Model trained 17 October 13:47 with landmark augmentation (4 copies per training sample, hands
  turned up to 15 degrees and jittered by 0.01 hand sizes): 380 samples, 16 recordings, 5 classes, l2 0.003.
- Leave-one-recording-out: accuracy **97.1%**, balanced cross-entropy **0.0747**, macro F1 **0.972**.
  At 90% confidence or more: 82% of frames, all correct. Details and the comparison with the
  14 October model are in `RESULTS_AND_DATA.md` section 2.
- Training is deterministic and takes about 34 s on the Mac (it was 7 s without augmentation).
- Clip replay through the live path (17 October, real `check_pipeline.py`): a wrong gesture shown in
  **0 of 16** clips; right gesture on more frames than before for every gesture.
- The 14 October model and the pre-change ML files are in `docs/handoff/snapshots/before-augmentation/`.
- `python -m pytest -q`: **413 passed** (17 October, after the ML, backend and frontend work of the same day; Python 3.14.7, project `.venv`).
- The owner reported the live webcam works (14 October).

## 3. Setup (macOS, Apple Silicon, Python 3.14)

```bash
cd "/Users/kavishseema/Desktop/Passion Project"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python download_models.py --pose
```

MediaPipe 1.1.0 ships no models and has no `mp.solutions`; the task files come from `download_models.py`.
scikit-learn on this machine is 1.9.1; the report records the version and the app warns on a mismatch.

## 4. Running experiments without breaking the app

The app reads `data/` and `models/` live. **Never train or import into them while experimenting.**

```bash
mkdir -p /tmp/bk-exp/data /tmp/bk-exp/models
cp data/samples.csv data/dataset_meta.json /tmp/bk-exp/data/
export BALLKNOWLEDGE_DATA_DIR=/tmp/bk-exp/data
export BALLKNOWLEDGE_MODEL_DIR=/tmp/bk-exp/models
python train_model.py
```

For model comparisons in a notebook, reuse the project's evaluation instead of writing your own:

```python
import data_collector as dc, train_model as tm
df = dc.DatasetStore().load()
df, dropped = tm.validate_dataset(df, 126)
labels = sorted(df["label"].unique())
proba = tm.held_out_probabilities(df, labels, l2=0.01)   # leave-one-recording-out
X, y = tm._xy(df.reset_index(drop=True), labels)
print(tm.balanced_cost(proba, y, len(labels)), tm.evaluate_proba(proba, y, labels)["accuracy"])
```

Any estimator with `fit`, `predict_proba`, `classes_` and `n_features_in_` can replace
`tm.make_model`. `Predictor` loads any such joblib model, so a new model needs no app change as long
as `save_artifacts` writes it with the label mapping and report.

Before you propose a model to the owner, run all three:

```bash
python -m pytest -q
python train_model.py                     # on the scratch copy
python check_pipeline.py "First meme" "Second meme" "Meme 3" "Meme 4" None    # needs the videos
```

## 5. Rules you must keep

1. **Split by recording, never by frame.** Frames 0.1 s apart are near-duplicates. A random row
   split reports accuracy close to 100% that means nothing. Every number in this project is
   leave-one-recording-out (`session_id`).
2. **One feature path.** Collection, video import and live prediction all use
   `features.build_feature_vector` via `vision.LandmarkHook`. If you change features, change them
   there, bump the feature mode or length, and re-extract every sample from video. Old
   `samples.csv` rows become unusable (`dataset_meta.json` blocks the mix).
3. **Honest numbers only.** Report measured held-out numbers, say what they were measured on, and
   never present training accuracy or a synthetic test as model quality (`Context.md` section 11).
4. **Confidence must stay meaningful.** The live app relies on a threshold. A model that is
   confidently wrong is worse than a less accurate one that is unsure; this is why held-out
   cross-entropy, not accuracy, picks the model and the penalty.
5. **`none` stays a class.** It is what keeps random hands from triggering memes.
6. **No video or images of people are stored.** Samples are landmark numbers only. Augmentation
   must happen on landmarks, not by saving frames.
7. **Deterministic training.** Same data in, same model and report out. Keep seeds fixed if you add randomness.
8. **UI wording.** The word "gradient" is banned in `ui.py`, `app.py` and `views/` (tested). Fine in ML code and docs.

## 6. Open work

| # | Item | Notes |
|---|---|---|
| 1 | More and more varied data | The biggest lever. One room, one day; the number of people is not recorded. `first_meme` has only 2 recordings; `second_meme` has 28 samples. Owner records; you can say what is needed |
| 2 | Generalisation to new people and rooms | Untested. `meme_4` already looks person-dependent. A leave-one-person-out test needs `person` filled in (it is empty for all rows today) |
| 3 | Optimistic held-out numbers | l2 is chosen on the same held-out recordings it is reported on (the report says so). The augmentation settings and the grid edge (17 October) were also chosen on these 16 recordings and the clip replay. Nested selection would fix it; with only 2 `first_meme` recordings, inner folds cannot hold that gesture out |
| 4 | l2 at the edge of the grid | 0.003 is the smallest option (17 October). 0.001 had a lower held-out cost but 1 to 2 frames wrong at 90% or more and a wrong meme for 3 frames in one replayed `meme_4` clip (the hand being lowered read as `second_meme`). Re-check with more data |
| 5 | Webcam vs Photo Booth gap | Training clips are Photo Booth, 1620x1080. Live webcam frames are 640x480 and more compressed; live confidence can be lower |
| 6 | Threshold and calibration | One global 0.70 threshold. The spec allows one per gesture. Probabilities are not calibrated (the UI says so) |
| 7 | Position relative to the face | Features are wrist-centred hand shape, so where the hand is (over the eyes, by the eye) is lost. `hands+pose` mode exists but is untested on real data |
