"""Video import tests: small synthetic videos and a stand-in detector.
No webcam, MediaPipe model or real recordings needed."""
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import data_collector as dc  # noqa: E402
import import_videos as iv  # noqa: E402
from vision import Detection, HandDetection  # noqa: E402

FPS = 30
HAND, EMPTY = 200, 0          # frame brightness the stand-in detector reads as "hand" or "no hand"


def write_video(path, frames, size=(160, 120)):
    """frames: a list of brightness values, or of BGR arrays."""
    path.parent.mkdir(parents=True, exist_ok=True)
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), FPS, size)
    assert out.isOpened()
    for f in frames:
        out.write(f if isinstance(f, np.ndarray) else np.full((size[1], size[0], 3), f, np.uint8))
    out.release()
    return path


def hand_video(path, before=0, hand=60, after=0, seed=0):
    """`before` empty frames, `hand` frames with a hand, `after` empty frames.
    `seed` changes one pixel so different videos have different bytes."""
    frames = [EMPTY] * before + [HAND] * hand + [EMPTY] * after
    arrays = [np.full((120, 160, 3), v, np.uint8) for v in frames]
    arrays[0][0, 0] = seed * 37 % 256
    return write_video(path, arrays)


class FakeDetector:
    """A hand when the frame is bright. The landmarks vary a little with each call."""

    def __init__(self):
        self.calls = 0
        self.frames = []

    def detect(self, frame):
        self.calls += 1
        self.frames.append(frame.copy())
        if frame.mean() < 100:
            return Detection()
        rng = np.random.default_rng(self.calls)
        lm = rng.uniform(0.3, 0.7, size=(21, 3)).astype(np.float32)
        return Detection(hands=[HandDetection("Right", 0.9, lm)])

    def close(self):
        pass


@pytest.fixture
def store(tmp_path):
    return dc.DatasetStore(tmp_path / "data" / "samples.csv", tmp_path / "data" / "meta.json", "hands")


def run(sources, store, **kw):
    kw.setdefault("detector_factory", FakeDetector)
    return iv.import_videos(sources, store, **kw)


# --- finding videos ----------------------------------------------------------

def test_folder_is_one_gesture_named_after_it(tmp_path):
    folder = tmp_path / "Thumbs Up"
    hand_video(folder / "b.mov", seed=1)
    hand_video(folder / "a.mp4", seed=2)
    (folder / "notes.txt").write_text("not a video")
    (folder / ".hidden.mov").write_bytes(b"")
    sources = iv.collect_sources([str(folder)])
    assert [s.path.name for s in sources] == ["a.mp4", "b.mov"]
    assert {s.label for s in sources} == {"thumbs_up"}


def test_label_option_overrides_folder_name(tmp_path):
    hand_video(tmp_path / "First meme" / "a.mov")
    assert iv.collect_sources([str(tmp_path / "First meme")], label="Facepalm")[0].label == "facepalm"


def test_single_file_needs_a_label(tmp_path):
    clip = hand_video(tmp_path / "clip.mov")
    with pytest.raises(iv.VideoImportError, match="--label"):
        iv.collect_sources([str(clip)])
    assert iv.collect_sources([str(clip)], label="wave")[0].label == "wave"


@pytest.mark.parametrize("make", ["missing", "empty_dir", "not_video"])
def test_bad_paths_are_reported(tmp_path, make):
    target = tmp_path / "x"
    if make == "empty_dir":
        target.mkdir()
    elif make == "not_video":
        target = tmp_path / "x.txt"
        target.write_text("hi")
    with pytest.raises(iv.VideoImportError):
        iv.collect_sources([str(target)], label="wave")


# --- importing -----------------------------------------------------------------

def test_each_video_becomes_one_recording(tmp_path, store):
    folder = tmp_path / "Second meme"
    for i in range(3):
        hand_video(folder / f"take{i}.mov", seed=i)
    outcomes = run(iv.collect_sources([str(folder)]), store, trim_s=0)
    assert [o.status for o in outcomes] == [iv.IMPORTED] * 3
    df = store.load()
    assert df["label"].unique().tolist() == ["second_meme"]
    assert sorted(df["session_id"].unique()) == sorted(o.session_id for o in outcomes)
    for o in outcomes:                                   # recording id comes from the file
        assert o.session_id == iv.session_id_for(iv.file_digest(o.path))
    summary = store.summary()
    assert summary.loc[0, "recordings"] == 3


def test_identical_copies_are_imported_once(tmp_path, store):
    folder = tmp_path / "First meme"
    original = hand_video(folder / "take.mov")
    shutil.copy(original, folder / "take (1).mov")
    hand_video(folder / "take #2.mov", seed=5)
    outcomes = run(iv.collect_sources([str(folder)]), store, trim_s=0)
    by_name = {o.path.name: o for o in outcomes}
    pair = [by_name["take.mov"], by_name["take (1).mov"]]
    assert sorted(o.status for o in pair) == [iv.DUPLICATE, iv.IMPORTED]   # whichever sorts first is kept
    dup, kept = sorted(pair, key=lambda o: o.status != iv.DUPLICATE)
    assert dup.detail == f"identical to {kept.path.name}"
    assert by_name["take #2.mov"].status == iv.IMPORTED
    assert store.summary().loc[0, "recordings"] == 2


def test_importing_again_adds_nothing(tmp_path, store):
    folder = tmp_path / "wave"
    hand_video(folder / "a.mov")
    run(iv.collect_sources([str(folder)]), store)
    rows = store.row_count()
    again = run(iv.collect_sources([str(folder)]), store)
    assert [o.status for o in again] == [iv.ALREADY_IMPORTED]
    assert store.row_count() == rows


def test_dry_run_saves_nothing(tmp_path, store):
    hand_video(tmp_path / "wave" / "a.mov")
    outcomes = run(iv.collect_sources([str(tmp_path / "wave")]), store, dry_run=True)
    assert outcomes[0].samples > 0
    assert not store.csv_path.exists()


def test_samples_at_the_recorder_rate(tmp_path, store):
    # 3 s of hand at 30 fps, sampled at 10 Hz: every third frame, 30 samples.
    # Frame times like 0.1 and 0.2 are not exact in floating point; none may be lost.
    hand_video(tmp_path / "wave" / "a.mov", hand=90)
    [o] = run(iv.collect_sources([str(tmp_path / "wave")]), store, trim_s=0, rate_hz=10)
    assert (o.frames, o.hand_frames, o.samples) == (90, 90, 30)


def test_trim_drops_the_start_and_end_of_the_gesture(tmp_path, store):
    # Hand from 1.0 s to 2.0 s (frames 30 to 60). Trimming 0.25 s keeps 1.25 s to 1.75 s:
    # frames 38 to 52, of which 38, 41, 44, 47 and 50 are taken at 10 Hz.
    hand_video(tmp_path / "wave" / "a.mov", before=30, hand=31, after=30)
    [o] = run(iv.collect_sources([str(tmp_path / "wave")]), store, trim_s=0.25, rate_hz=10)
    assert o.hand_frames == 31
    assert o.trimmed == 16
    assert o.samples == 5


def test_video_without_a_hand_saves_nothing(tmp_path, store):
    write_video(tmp_path / "wave" / "a.mov", [EMPTY] * 30)
    [o] = run(iv.collect_sources([str(tmp_path / "wave")]), store)
    assert o.status == iv.NO_SAMPLES and o.samples == 0
    assert "no hand" in o.detail
    assert not store.csv_path.exists()


def test_frames_are_mirrored_like_the_live_camera(tmp_path, store):
    frame = np.zeros((120, 160, 3), np.uint8)
    frame[:, :80] = 255                                   # bright left half in the file
    write_video(tmp_path / "wave" / "a.mov", [frame] * 3)
    fake = FakeDetector()
    run(iv.collect_sources([str(tmp_path / "wave")]), store, detector_factory=lambda: fake)
    seen = fake.frames[0]
    assert seen[:, :70].mean() < 30 and seen[:, 90:].mean() > 225   # the detector sees it flipped


def test_large_frames_are_scaled_to_camera_height():
    big = np.zeros((1080, 1620, 3), np.uint8)
    assert iv.to_camera_scale(big).shape == (480, 720, 3)
    small = np.zeros((240, 320, 3), np.uint8)
    assert iv.to_camera_scale(small) is small


def test_rejects_bad_settings(tmp_path, store):
    hand_video(tmp_path / "wave" / "a.mov")
    sources = iv.collect_sources([str(tmp_path / "wave")])
    with pytest.raises(iv.VideoImportError):
        run(sources, store, rate_hz=0)
    with pytest.raises(iv.VideoImportError):
        run(sources, store, trim_s=-1)


def test_unreadable_file_is_reported(tmp_path, store):
    bad = tmp_path / "wave" / "broken.mov"
    bad.parent.mkdir()
    bad.write_bytes(b"this is not a video")
    with pytest.raises(iv.VideoImportError, match="broken.mov"):
        run(iv.collect_sources([str(bad.parent)]), store)
