---
description: Run the full test suite, including the design-rule guards, and report plainly
---

Run the project's tests from the project root with the virtual environment:

```bash
source .venv/bin/activate && python -m pytest -q
```

Report the pass and fail counts. For every failure, quote the assertion and say which file and rule it comes from. If `tests/test_style_rules.py` fails, fix the UI code to follow the rule (no emoji, em dashes, gradients, animations, pill shapes or invented numbers); never loosen the test. Do not claim anything works that the tests do not cover, and say which parts need a real camera to verify.
