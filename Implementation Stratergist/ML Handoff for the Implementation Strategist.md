# ML Handoff for the Implementation Strategist

Oct 17, 2026 · @Kavish

## Summary

The gesture model was retrained on 17 October with landmark augmentation. It is as accurate as before and much more confident when it is right: held-out cost fell from 0.1056 to 0.0747, and frames at 90%+ confidence rose from 74% to 82%, all of them correct. Replaying all 16 recorded clips through the live path still shows **0 wrong memes**. The new model is live in `models/`; the app needed no change.

The owner asked for "very confident" answers and "50 epochs" of training. Confidence was delivered through augmentation. The 50-epoch cap was measured, found to make the model worse, and the owner chose not to apply it.

Scope: Ball Knowledge Vision AI, a local Streamlit app that recognises 5 hand gestures from a webcam (MediaPipe landmarks, then our softmax regression trained by gradient descent) and shows a meme. Data: 380 samples from 16 recordings, one room, about 2 people.

## Decisions and why

| Decision | Status | Evidence |
| --- | --- | --- |
| Landmark augmentation: 4 extra copies per training sample, hands turned up to 15 degrees about the wrist, jitter 0.01 hand sizes | Adopted | Same accuracy, held-out cost down 29%, no extra confident errors across 3 seeds |
| l2 options extended to 0.003, not 0.001 | Adopted | 0.001 had lower cost but showed a wrong meme for 3 frames in one `meme_4` clip (hand being lowered read as `second_meme`) and 1 to 2 frames wrong at 90%+ |
| Confidence cutoff stays at 0.70 | Kept | 0.80 and 0.90 replayed with fewer right frames and no fewer wrong memes |
| Train to the minimum (about 2,700 steps), no 50-epoch cap | Owner confirmed 17 Oct | Full-batch descent: 1 step = 1 epoch. 50 epochs gave 92.1% accuracy, 30 wrong frames (vs 11) and 2 confident errors |
| Engineered hand-shape features (joint angles, fingertip distances) | Rejected | Lower accuracy than raw coordinates at every l2 tried |
| Model family unchanged (softmax regression by gradient descent) | Kept | Owner's choice from 13 Oct; changing it needs the owner's approval with numbers |

Selection rule throughout: lowest held-out cross-entropy, checked against confident mistakes and the clip replay's wrong-meme count. A model that is confidently wrong is treated as worse than one that is unsure.

## Measured results

All numbers are leave-one-recording-out: each recording is predicted by a model that never saw it.

| Held-out measure | 14 Oct model | 17 Oct model |
| --- | --- | --- |
| Accuracy | 97.4% (10 wrong of 380) | 97.1% (11 wrong) |
| Cross-entropy (cost) | 0.1056 | 0.0747 |
| Macro F1 | 0.973 | 0.972 |
| Mean confidence when right (median) | 0.924 (0.979) | 0.954 (0.992) |
| Frames at 0.70+ / correct of those | 91.6% / 98.6% | 95.8% / 98.6% |
| Frames at 0.90+ / correct of those | 74.2% / 100% | 82.4% / 100% |
| l2 chosen | 0.01 | 0.003 |
| Training time on the Mac | about 7 s | about 34 s |

The one extra error is within seed noise (97.1% to 97.4% across seeds). Most errors remain random hands (`none`) read as a gesture, 7 of 11.

Clip replay through the live path (`check_pipeline.py`, 16 clips, share of hand frames):

| Gesture | Right, before | Right, now | Unsure, before | Unsure, now | Wrong |
| --- | --- | --- | --- | --- | --- |
| first\_meme | 75% | 87% | 19% | 8% | 0% |
| meme\_3 | 87% | 89% | 12% | 10% | 0% |
| meme\_4 | 59% | 60% | 7% | 7% | 0% |
| none (shown as No gesture) | 78% | 86% | 21% | 13% | 0% |
| second\_meme | 85% | 87% | 13% | 12% | 0% |

`meme_4` has 33% no-hand frames in both because the hand was lowered between attempts. Full tables are in `docs/ml-handoff/RESULTS_AND_DATA.md`.

## What changed in the code

All edits are small and additive. Prediction, features at inference time and the UI are unchanged.

| File | Change |
| --- | --- |
| `features.py` | New `augment_hands(X, copies, rotation_deg, noise, seed)`: rotates each hand in the image plane, adds jitter, renormalises like `normalize_hand`. Missing hands stay zero, pose columns untouched |
| `gd_model.py` | New params `augment_copies`, `augment_rotation_deg`, `augment_noise`, `random_state`, used only inside `fit`. `__setstate__` gives pre-17-Oct pickles `augment_copies=0`, so old models still load |
| `config.py` | `GD_L2_OPTIONS = (1.0, 0.3, 0.1, 0.03, 0.01, 0.003)`; new `GD_AUGMENT_COPIES = 4`, `GD_AUGMENT_ROTATION_DEG = 15.0`, `GD_AUGMENT_NOISE = 0.01`, `GD_AUGMENT_SEED = 0` |
| `train_model.py` | `make_model` passes the augmentation settings; report gains `cost.augmentation`; console report prints one augmentation line |
| `tests/` | 11 new tests (augmentation geometry, determinism, old-pickle loading, report). Two asserts that hardcoded 5 l2 options now use `len(config.GD_L2_OPTIONS)`. Suite: 413 passed |
| Docs | Root `README.md` (augmentation paragraph), `docs/ml-handoff/README.md`, `ARCHITECTURE.md`, `RESULTS_AND_DATA.md` |

Augmentation runs inside every held-out fit, so held-out rows are never augmented and never leak. Training stays deterministic (fixed seed). No images or video are stored; only landmark numbers are copied, in memory.

## Implications for planning

- **Training time is about 5 times longer:** 34 s instead of 7 s (97 model fits instead of 81). The Train model button already runs in the background with a progress bar, so it stays usable, but the time grows with samples x recordings. Plan for this before large data collection.
- **Live threshold behaviour changed:** memes appear more often and sooner at the same 0.70 cutoff. Any future change to the model or its confidence must be re-checked with `check_pipeline.py` and the cutoff table.
- **Compatibility:** the joblib model is still a `GradientDescentClassifier`; `Predictor.load` needs no change. The report has one new optional key, `cost.augmentation`.
- **Rollback:** the 14 October model and the pre-change ML files are in `docs/handoff/snapshots/before-augmentation/`. Copy its three model files back, or set `GD_AUGMENT_COPIES = 0` and the old l2 list to retrain the old way.
- **Coordination:** a backend session works in the same folder. It was told the facts now out of date in `docs/backend-handoff/` (training time, l2 list, the new report key) and owns those docs.
- **Not verified:** the owner's real webcam with the new model. Training clips are Photo Booth (1620x1080); live frames are 640x480 and more compressed.

## Risks and recommended next steps

The biggest limit is data, not the model: the 97% describes one room, one day and about 2 people, so treat it as an upper bound.

| # | Next step | Why | Who |
| --- | --- | --- | --- |
| 1 | Live webcam test of the new model (README, Test the whole pipeline) | Only end-to-end check not yet done | Owner |
| 2 | More data: a 3rd `first_meme` recording, more `second_meme` (28 samples) and `meme_3`, other rooms, light and people, with the `--person` flag | Largest lever; enables a leave-one-person-out test | Owner records, ML advises |
| 3 | Webcam recordings via the Data collector if a gesture shows Unrecognised live | Closes the Photo Booth vs webcam gap | Owner |
| 4 | Hand position relative to the face (`hands+pose` mode or face landmarks) | 3 gestures are defined by where the hand is, which current features discard; needs re-extracting from video | ML |
| 5 | Nested selection of l2 and augmentation settings | Current held-out numbers are slightly optimistic; blocked by `first_meme` having only 2 recordings | ML, after step 2 |
| 6 | Re-check the l2 grid edge (0.003) and per-gesture thresholds once data grows | Both were set on 16 recordings | ML |

Known risks: `meme_4` looks person-dependent (filmed by someone else); `none` frames read as gestures remain the main error type; probabilities are not calibrated (the UI says so).
