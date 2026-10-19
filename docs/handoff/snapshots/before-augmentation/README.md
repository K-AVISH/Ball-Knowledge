# Snapshot before landmark augmentation (17 October 2026)

`models/` holds the model that was live before augmentation was added: trained 14 October,
softmax regression with l2 0.01, no augmentation, 97.4% held-out accuracy, held-out cost 0.1056.
`config.py`, `features.py` and `gd_model.py` are those files as they were before the change.

To go back to that model, copy the three files in `models/` over the ones in the project's
`models/` folder. To train the old way again, set `GD_AUGMENT_COPIES = 0` and
`GD_L2_OPTIONS = (1.0, 0.3, 0.1, 0.03, 0.01)` in `config.py`; that reproduces the old
held-out accuracy and cost (checked 17 October).
