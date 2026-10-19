"""Shared test setup: a guard that the tests never change the owner's real project files.

Every test works in scratch folders. If one ever writes to, or leaves a file in, the real
data/, models/ or assets/memes/ (the recordings, the trained model and the memes), the run
ends with an error naming the files.
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUARDED = [ROOT / "data", ROOT / "models", ROOT / "assets" / "memes"]


def _snapshot():
    files = {}
    for folder in GUARDED:
        if folder.is_dir():
            for path in folder.rglob("*"):
                if path.is_file():
                    st = path.stat()
                    files[str(path.relative_to(ROOT))] = (st.st_size, st.st_mtime_ns)
    return files


@pytest.fixture(scope="session", autouse=True)
def real_project_files_are_untouched():
    before = _snapshot()
    yield
    after = _snapshot()
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    assert not changed, f"Tests changed the real project files: {', '.join(changed)}"
