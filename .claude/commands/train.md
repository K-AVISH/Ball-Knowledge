---
description: Train the gesture model on the recorded samples and report the real results
---

Train the model from the project root:

```bash
source .venv/bin/activate && python train_model.py
```

Report exactly what the script prints: the dataset size, the split by recording, the test accuracy, macro F1, per-gesture precision and recall, the gestures it confuses, and every caution it lists. If it fails, give the message and say what to record or fix. Never describe a model as good or ready from the training accuracy; only the held-out test numbers count, and they are rough when each gesture is tested on one recording. If there is no real data in data/samples.csv, say so and do not invent results.
