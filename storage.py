"""Safe file writes, shared by every module that saves something.

Two guarantees, so the app can run in several browser tabs and next to a terminal
script (import_videos.py, train_model.py, dataset_manager.py) without losing data:

* `atomic_write_bytes` / `atomic_write_text` / `replace_together` write to a temporary
  file in the same folder, flush it to disk, then rename it over the target. Anyone
  reading sees the old file or the new one, never half of one, and a crash part way
  through leaves the old file as it was.
* `locked(path)` is an exclusive lock for one read-modify-write of a file. It holds
  across the threads of this process (Streamlit runs each browser tab on its own
  thread) and across processes (the app and a terminal script). Reading never needs
  the lock, because files are only ever replaced whole.

The lock is a hidden, empty file next to the data (for example data/.samples.csv.lock).
The operating system releases it when the process holding it exits, so a crash never
leaves it stuck.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, Sequence, Tuple

try:                                   # macOS and Linux; elsewhere only threads are locked out
    import fcntl
except ImportError:                    # pragma: no cover - not used on this project's Mac
    fcntl = None

LOCK_POLL_S = 0.05


class StorageBusyError(RuntimeError):
    """Another thread or program held the lock for longer than the timeout."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Atomic writes
# ---------------------------------------------------------------------------

def _write_temp(path: Path, data: bytes) -> Path:
    """Write `data` to a new temporary file beside `path` and flush it to disk.
    Each call gets its own name, so two writers never share a temporary file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            try:                                # a replaced file keeps its permissions
                os.fchmod(fh.fileno(), path.stat().st_mode & 0o777)
            except FileNotFoundError:
                pass                            # a new file stays private to this user (0600)
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return Path(tmp)


def _sync_folder(folder: Path) -> None:
    """Make a rename in `folder` survive a power cut. Best effort: not every system allows it."""
    try:
        fd = os.open(folder, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Replace `path` with `data` in one step."""
    path = Path(path)
    tmp = _write_temp(path, data)
    try:
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    _sync_folder(path.parent)


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, text.encode(encoding))


def replace_together(files: Sequence[Tuple[Path, bytes]]) -> None:
    """Write every file to a temporary name first, then rename them in the order given.

    If any write fails, no target is touched. The renames themselves are separate steps,
    so put last the file whose presence says the set is complete (the training report),
    and let readers check that the others match it.
    """
    temps = []
    try:
        for path, data in files:
            temps.append((_write_temp(Path(path), data), Path(path)))
        for tmp, path in temps:
            os.replace(tmp, path)
    finally:
        for tmp, _ in temps:
            tmp.unlink(missing_ok=True)       # already renamed ones are gone; this is a no-op
    for folder in {Path(p).parent for p, _ in files}:
        _sync_folder(folder)


# ---------------------------------------------------------------------------
# Locks
# ---------------------------------------------------------------------------

class _PathLock:
    """A thread lock plus an OS file lock for one path. Re-entrant within a thread."""

    def __init__(self, lock_file: Path) -> None:
        self.lock_file = lock_file
        self.thread_lock = threading.RLock()
        self.depth = 0                 # changed only by the thread holding thread_lock
        self.handle = None


_locks: Dict[str, _PathLock] = {}
_locks_guard = threading.Lock()


def lock_file_for(path: Path) -> Path:
    """data/samples.csv -> data/.samples.csv.lock"""
    path = Path(path)
    return path.parent / f".{path.name.lstrip('.')}.lock"


def _path_lock(path: Path) -> _PathLock:
    key = str(Path(path).resolve())
    with _locks_guard:
        if key not in _locks:
            _locks[key] = _PathLock(lock_file_for(Path(key)))
        return _locks[key]


def _busy(path: Path, what: str) -> StorageBusyError:
    return StorageBusyError(
        f"{what or Path(path).name} is being changed by another tab or program. "
        "Wait a moment and try again.")


@contextmanager
def locked(path: Path, timeout: float = 10.0, what: str = "") -> Iterator[None]:
    """Hold the exclusive lock for `path` (the data file, not the lock file).

    Waits up to `timeout` seconds; 0 means do not wait. Raises StorageBusyError when the
    lock is still taken. `what` names the file in that message.
    """
    entry = _path_lock(path)
    deadline = time.monotonic() + max(0.0, timeout)
    acquired = (entry.thread_lock.acquire(timeout=timeout) if timeout > 0
                else entry.thread_lock.acquire(blocking=False))
    if not acquired:
        raise _busy(path, what)
    try:
        if entry.depth == 0 and fcntl is not None:
            entry.lock_file.parent.mkdir(parents=True, exist_ok=True)
            handle = open(entry.lock_file, "a+b")
            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        handle.close()
                        raise _busy(path, what) from None
                    time.sleep(LOCK_POLL_S)
            entry.handle = handle
        entry.depth += 1
        try:
            yield
        finally:
            entry.depth -= 1
            if entry.depth == 0 and entry.handle is not None:
                fcntl.flock(entry.handle.fileno(), fcntl.LOCK_UN)
                entry.handle.close()
                entry.handle = None
    finally:
        entry.thread_lock.release()
