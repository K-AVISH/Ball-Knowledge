# Results and data

All numbers are measured, leave-one-recording-out, on the owner's own recordings. Source:
`models/training_report.json` (trained 17 October 2026), compared with the 14 October model.

## 1. Dataset

380 samples, 16 recordings, 5 classes, `hands` features (126). Recorded in Photo Booth
(1620x1080, 30 fps, unmirrored; mirrored on import), mostly in one room on 13 and 14 October.
`meme_4` was filmed by a different person. The `person` column is empty for every row, so people
cannot be counted or held out.

| Gesture | What it is | Samples | Recordings |
|---|---|---|---|
| `first_meme` | Both hands over the face | 58 | 2 |
| `second_meme` | Sideways V sign by the eye | 28 | 3 |
| `meme_3` | Both open palms raised ("Absolute Cinema") | 48 | 3 |
| `meme_4` | One hand over the eyes (facepalm) | 127 | 4 |
| `none` | Random hand shapes, not a gesture | 119 | 4 |

Collection targets in `config.py`: 100 to 300 samples and 3 or more recordings per gesture.
`first_meme`, `second_meme` and `meme_3` are under 100; `first_meme` is under 3 recordings.
`first_meme` originally had two byte-identical clips; only one was kept, since a copy would put the
same frames on both sides of the test.

Raw clips live in the folders `First meme/`, `Second meme/`, `Meme 3/`, `Meme 4/`, `None/`.
Photo Booth filenames contain U+202F (narrow no-break space) before "AM"; use globs.

## 2. Current model (17 October) and the one it replaced (14 October)

Same data, same leave-one-recording-out test. The 17 October model adds landmark augmentation
(4 copies per training sample, hands turned up to 15 degrees, jitter 0.01 hand sizes) and the l2
option 0.003. Old numbers: the 14 October report (snapshot in
`docs/handoff/snapshots/before-augmentation/`), reproduced on 17 October.

| Metric (held out unless stated) | 14 Oct | 17 Oct |
|---|---|---|
| Accuracy | 97.37% (10 wrong of 380) | 97.11% (11 wrong) |
| Balanced cross-entropy | 0.1056 | **0.0747** |
| Macro F1 | 0.973 | 0.972 |
| Mean confidence when right (median) | 0.924 (0.979) | **0.954 (0.992)** |
| Mean confidence when wrong | 0.672 | 0.683 |
| Frames at 0.7 or more / correct of those | 91.6% / 98.6% | **95.8% / 98.6%** |
| Frames at 0.9 or more / correct of those | 74.2% / 100% | **82.4% / 100%** |
| Wrong frames at 0.9 or more | 0 | 0 |
| l2 | 0.01 | 0.003 |
| Steps to converge (training cost) | 1,927 (0.0892) | 2,658 tried, 2,656 kept (0.0487, over augmented rows) |
| Training accuracy, not a quality measure | 99.47% | 100% |
| Training time on the Mac | about 7 s | about 34 s |

The one extra error is a `none` frame read as `first_meme`; across three augmentation seeds the
accuracy was 97.1% to 97.4%, so the two models are equally accurate within noise. The gain is in
confidence: the model is surer when right and not surer when wrong.

Per class (17 October):

| Gesture | Precision | Recall | F1 | Samples |
|---|---|---|---|---|
| first_meme | 0.934 | 0.983 | 0.958 | 58 |
| meme_3 | 1.000 | 1.000 | 1.000 | 48 |
| meme_4 | 0.992 | 0.976 | 0.984 | 127 |
| none | 0.966 | 0.941 | 0.953 | 119 |
| second_meme | 0.933 | 1.000 | 0.966 | 28 |

Confusion matrix (17 October; rows true, columns predicted, order first_meme, meme_3, meme_4, none, second_meme):

```
first_meme   57   0    0    1   0
meme_3        0  48    0    0   0
meme_4        0   0  124    3   0
none          4   0    1  112   2
second_meme   0   0    0    0  28
```

Most errors are still `none` predicted as a gesture (7 of 11), the costly direction. In both models
the `none` frames wrong at 0.7 or more come from the same recordings (c79027, 9225f0 and ae2595). The threshold and
vote absorb them live (0 wrong memes in the clip replay).

l2 search, held-out cost and accuracy (14 October: no augmentation; 17 October: augmented):

| l2 | 14 Oct | 17 Oct |
|---|---|---|
| 1.0 | 0.5381, 81.3% | 0.5438, 81.6% |
| 0.3 | 0.3599, 88.4% | 0.3619, 86.8% |
| 0.1 | 0.2443, 90.8% | 0.2437, 90.8% |
| 0.03 | 0.1549, 95.3% | 0.1524, 96.3% |
| 0.01 | **0.1056, 97.4%** | 0.1023, 97.6% |
| 0.003 | 0.0782, 97.4% (2 wrong at 0.9+) | **0.0747, 97.1%** (0 wrong at 0.9+) |
| 0.001 (not in the grid) | 0.0681, 97.4% (3 wrong at 0.9+) | 0.0637, 97.4% (2 wrong at 0.9+, wrong meme in replay) |

Without augmentation the lighter penalties are confident on their mistakes; with it, 0.003 is not.

Confidence cutoff (17 October; share of held-out frames above the cutoff, and accuracy of those):

| Cutoff | Coverage | Accuracy |
|---|---|---|
| 0.5 | 99.7% | 97.4% |
| 0.6 | 98.2% | 98.4% |
| **0.7 (live)** | **95.8%** | **98.6%** |
| 0.8 | 91.6% | 99.1% |
| 0.9 | 82.4% | 100% |

Weakest held-out recordings: the three `none` recordings at 92 to 93% accuracy (cost 0.15 to 0.24),
and one `meme_4` recording at 95%. Every other recording is at 97% or 100%.

## 3. Clip replay through the live path

Each clip classified by a model that never saw it; shares of frames from the first to the last
frame with a hand. 17 October: the real `check_pipeline.py` run on all five folders after the
retrain. 14 October: the old recipe on the same clips (reproduced exactly on 17 October).
`check_pipeline.py` trains each held-out clip's model with the saved report's l2 (0.003 on 17 October), which was chosen with that clip's recording in the folds, so the replay shares the slight optimism of the held-out numbers (section 5, item 3).

| Gesture | Clips | Right, 14 Oct | Right, 17 Oct | Wrong | Unsure, 14 Oct | Unsure, 17 Oct | No hand |
|---|---|---|---|---|---|---|---|
| first_meme | 2 | 75% | **87%** | 0% | 19% | 8% | 0% |
| meme_3 | 3 | 87% | 89% | 0% | 12% | 10% | 0% |
| meme_4 | 4 | 59% | 60% | 0% | 7% | 7% | 33% |
| none | 4 | 78% (No gesture) | **86%** | 0% | 21% | 13% | 1% |
| second_meme | 3 | 85% | 87% | 0% | 13% | 12% | 0% |

A wrong gesture was shown in 0 of 16 clips with either model. Over all clips the right result was
on screen for 75.8% of hand frames (was 71.5%) and "unsure" for 9.5% (was 13.6%). The `meme_4`
no-hand share is real: the hand was lowered between attempts. "Unsure" frames only delay the meme.

Replay of the alternatives (same clips): augmented with l2 0.001 showed `second_meme` in
`Meme 4/...11.43 AM #2.mov` while the hand was lowered: 3 frames at the 0.70 cutoff, 1 at 0.80,
none at 0.90 (but then only 67.7% right). Augmented l2 0.003 at a 0.80 cutoff: 0 wrong, 71.7% right. So the cutoff
stays at 0.70.

## 4. Past experiments and decisions

| Date | Experiment | Result | Decision |
|---|---|---|---|
| 13 Oct | Softmax regression (l2 0.01) vs scikit-learn gradient boosting vs histogram gradient boosting, defaults, first 5 recordings, leave-one-recording-out | All 93% accuracy; held-out cross-entropy 0.083, 0.131 and 0.719. Boosted models were confident when wrong | Softmax regression by gradient descent, chosen with the owner |
| 13 Oct | Random forest (the spec's suggested baseline) | Higher held-out cost | Not used. `Predictor` still forces `n_jobs=1` for forests (26 ms vs 10 ms per frame) |
| 14 Oct | l2 below 0.01 | Lower held-out cost, but only by being more confident, not more accurate | `GD_L2_OPTIONS` kept |
| 14 Oct | Added `meme_3`, `meme_4`, `none`; retrained from 2 to 5 classes | 97.4% held-out | Model until 17 October. Pre-change data and model in `docs/handoff/snapshots/before-meme3-meme4-none/` |
| 17 Oct | Gradient descent capped at 50 epochs (full batch, so 1 step = 1 pass over the data) instead of running to the minimum | Old recipe: 91.8% held-out, cost 0.192, 31 wrong, 2 wrong at 0.9+. New recipe: 92.1%, cost 0.187, 30 wrong, 2 wrong at 0.9+ | Not used: stopping early leaves the model less accurate and less sure when right, and more often sure when wrong. Training runs to the minimum (about 2,700 passes) |
| 17 Oct | Engineered hand-shape features (15 joint bend angles, 10 fingertip distances, 5 tip-to-wrist distances per hand) next to the raw 126, computed inside the model | Lower held-out cost (0.092 at l2 0.01) but lower accuracy than raw features at every l2 tried (95.3% at 0.01), with or without augmentation | Not used |
| 17 Oct | Landmark augmentation: 4 or 8 copies, rotation 10 to 20 degrees, noise 0.01 to 0.02, swapping a lone hand to the other slot, seeds 0 to 2 | Rotation 15, noise 0.01, 4 copies: same accuracy, lower cost, no extra confident errors. 8 copies: same within noise, twice the time. Hand swapping: worse | Adopted with l2 0.003 (current model) |
| 14 Oct | Webcam vs Photo Booth | Live stream starts around 320x213 and rises within seconds; more compressed than the clips | Advice: add webcam recordings via the Data collector if a gesture stays Unrecognised |

The exact scripts for the 13 October comparison were not kept; numbers are from the README.
Re-run them with `held_out_probabilities(..., make=...)` before relying on them.

## 5. Known weaknesses

1. **Small, narrow data.** One room, one day per gesture; the number of people is not recorded
   (`person` is empty in all 380 rows). The 97% does not describe
   a new person or room. Treat it as an upper bound.
2. **`meme_4` is person-dependent.** It was filmed by someone else; the owner's own version may not
   match. Needs at least 2 recordings per person.
3. **Optimistic selection.** l2 is picked and reported on the same folds (the report warns about this).
   The augmentation settings and the grid edge were also picked on these recordings and the clip replay.
4. **Imbalance.** 28 to 127 samples per class. The loss is class-balanced, but small classes still
   have noisy estimates.
5. **No hand position.** See `ARCHITECTURE.md` section 2.
6. **Uncalibrated confidence.** The UI says so. The cutoff table is the only calibration evidence.

## 6. Ideas worth testing

Ranked by expected value per effort. Measure each with leave-one-recording-out held-out cost and
`check_pipeline.py` wrong-meme count, and compare against the current numbers above.

1. **Data first.** Ask the owner for a third `first_meme` recording, more `second_meme` and `meme_3`,
   clips in other rooms and light, and other people with the `--person` flag so a leave-one-person-out
   test becomes possible.
2. **Nested selection** for l2, to get an unbiased number.
3. **Hand position relative to the face** (pose or face landmarks, or the hand's position in the
   frame scaled by face size). Requires re-extracting features from the videos.
4. **Engineered shape features** (finger joint angles, fingertip distances) next to raw coordinates.
   Tried 17 October: lower accuracy on this data (section 4). Worth another look with more data.
5. **Landmark augmentation** (small rotations, scale jitter, noise) at training time only, inside each fold.
   Done 17 October (current model).
6. **Temperature scaling or per-class thresholds**, fitted on held-out probabilities, then re-check the vote.
7. **A small MLP** if data grows past a few thousand samples. Compare on held-out cost, not accuracy.
8. **Temporal model** over a short window of vectors, only if static frames stop being enough.
