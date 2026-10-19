"""storage.py: atomic writes and the lock that every saving module uses. Scratch files only."""
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import storage  # noqa: E402


def leftovers(folder):
    return sorted(p.name for p in folder.iterdir() if p.name.endswith(".tmp"))


# --- atomic writes ----------------------------------------------------------------

def test_atomic_write_replaces_the_file_and_leaves_no_temporary_file(tmp_path):
    target = tmp_path / "sub" / "a.json"
    storage.atomic_write_text(target, "one")
    storage.atomic_write_text(target, "two")
    assert target.read_text() == "two"
    assert leftovers(target.parent) == []


def test_a_replaced_file_keeps_its_permissions_and_a_new_one_is_private(tmp_path):
    shared = tmp_path / "shared.txt"
    shared.write_text("x")
    os.chmod(shared, 0o644)
    storage.atomic_write_text(shared, "y")
    assert shared.stat().st_mode & 0o777 == 0o644
    fresh = tmp_path / "fresh.txt"
    storage.atomic_write_text(fresh, "z")
    assert fresh.stat().st_mode & 0o777 == 0o600


def test_a_failed_rename_keeps_the_old_file(tmp_path, monkeypatch):
    target = tmp_path / "a.csv"
    target.write_text("old")

    def broken(*_a):
        raise OSError("disk full")
    monkeypatch.setattr(storage.os, "replace", broken)
    with pytest.raises(OSError, match="disk full"):
        storage.atomic_write_text(target, "new")
    assert target.read_text() == "old"
    assert leftovers(tmp_path) == []


def test_replace_together_touches_nothing_when_one_file_cannot_be_written(tmp_path, monkeypatch):
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_text("old a")
    b.write_text("old b")
    real = storage._write_temp

    def fail_on_b(path, data):
        if path.name == "b":
            raise OSError("no space")
        return real(path, data)
    monkeypatch.setattr(storage, "_write_temp", fail_on_b)
    with pytest.raises(OSError):
        storage.replace_together([(a, b"new a"), (b, b"new b")])
    assert (a.read_text(), b.read_text()) == ("old a", "old b")
    assert leftovers(tmp_path) == []


def test_replace_together_writes_every_file(tmp_path):
    files = [(tmp_path / "m" / "model", b"1"), (tmp_path / "m" / "labels", b"2"), (tmp_path / "m" / "report", b"3")]
    storage.replace_together(files)
    assert [p.read_bytes() for p, _ in files] == [b"1", b"2", b"3"]
    assert leftovers(tmp_path / "m") == []


# --- the lock ---------------------------------------------------------------------

def test_lock_file_is_hidden_and_beside_the_data(tmp_path):
    assert storage.lock_file_for(tmp_path / "samples.csv") == tmp_path / ".samples.csv.lock"
    with storage.locked(tmp_path / "samples.csv"):
        assert (tmp_path / ".samples.csv.lock").exists()


def test_lock_keeps_other_threads_out_until_released(tmp_path):
    target = tmp_path / "f"
    order = []
    holding = threading.Event()

    def holder():
        with storage.locked(target):
            holding.set()
            time.sleep(0.2)
            order.append("first done")

    t = threading.Thread(target=holder)
    t.start()
    holding.wait(2)
    with storage.locked(target):
        order.append("second in")
    t.join()
    assert order == ["first done", "second in"]


def test_lock_times_out_with_a_clear_error(tmp_path):
    target = tmp_path / "memes.json"
    holding, release = threading.Event(), threading.Event()

    def holder():
        with storage.locked(target):
            holding.set()
            release.wait(5)

    t = threading.Thread(target=holder)
    t.start()
    holding.wait(2)
    try:
        start = time.monotonic()
        with pytest.raises(storage.StorageBusyError, match="memes.json is being changed"):
            with storage.locked(target, timeout=0.2):
                pass
        assert 0.15 < time.monotonic() - start < 2
        with pytest.raises(storage.StorageBusyError):
            with storage.locked(target, timeout=0):
                pass
    finally:
        release.set()
        t.join()


def test_lock_is_reentrant_in_one_thread(tmp_path):
    target = tmp_path / "f"
    with storage.locked(target):
        with storage.locked(target, timeout=0):
            pass
    with storage.locked(target, timeout=0):       # fully released afterwards
        pass


@pytest.mark.skipif(storage.fcntl is None, reason="file locks need fcntl")
def test_lock_holds_across_processes(tmp_path):
    """The app and a terminal script are separate processes; they must exclude each other."""
    target = tmp_path / "samples.csv"
    script = (
        "import sys, time; sys.path.insert(0, sys.argv[1]); import storage\n"
        "with storage.locked(sys.argv[2]):\n"
        "    print('locked', flush=True); time.sleep(1.5)\n"
    )
    child = subprocess.Popen([sys.executable, "-c", script, str(ROOT), str(target)],
                             stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == "locked"
        with pytest.raises(storage.StorageBusyError):
            with storage.locked(target, timeout=0.2):
                pass
        with storage.locked(target, timeout=5):     # free once the other process is done
            pass
    finally:
        child.wait(10)


def test_sha256_bytes():
    assert storage.sha256_bytes(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
