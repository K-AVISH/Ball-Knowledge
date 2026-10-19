"""Import recorded videos as training samples.

    python import_videos.py "First meme" "Second meme"     # one gesture per folder
    python import_videos.py clip.mov --label thumbs_up     # a single file
    python import_videos.py "First meme" --dry-run         # report only, save nothing

Each video file becomes one recording in data/samples.csv, the same as a recording
made on the Data collector page:

* Every frame goes through the live camera path. `vision.FrameProcessor` mirrors it
  and `vision.LandmarkHook` finds the landmarks and builds the feature vector with
  `features.py`, so imported samples match what the dashboard sees live.
* `data_collector.Recorder` keeps at most COLLECT_RATE_HZ samples per second of
  video and skips frames without a hand, as it does for the webcam.
* The first and last TRIM seconds in which a hand is visible are dropped. In those
  frames the hand is usually still moving into or out of the gesture.

A folder is one gesture, named after the folder ("First meme" becomes first_meme), and
each video in it is a separate recording. The recording id comes from the file's
contents, so a copy of a file that is already in the dataset, or in the same import,
is skipped instead of being counted twice. Two identical recordings would put the same
frames in the training and test sets and make the test score meaningless.

If a folder also holds exactly one image (.jpg, .jpeg, .png, .webp or .gif), it becomes
that gesture's meme: dataset_manager.py copies it into assets/memes/ and records it in
memes.json, keeping any title, rating and description already set there.

Only landmark numbers are saved. Video files are read, never copied, moved or changed.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterator, List, Optional, Sequence, Tuple

import cv2
import numpy as np

import config
import data_collector as dc
import dataset_manager as dm
import vision

VIDEO_SUFFIXES = (".mov", ".mp4", ".m4v", ".avi", ".mkv", ".webm")
DEFAULT_TRIM_S = 0.25

IMPORTED, DUPLICATE, ALREADY_IMPORTED, NO_SAMPLES = "imported", "duplicate", "already imported", "no samples"


class VideoImportError(RuntimeError):
    """A video cannot be imported. The message says why."""


@dataclass
class VideoSource:
    path: Path
    label: str


@dataclass
class ImportOutcome:
    path: Path
    label: str
    status: str                  # IMPORTED, DUPLICATE, ALREADY_IMPORTED or NO_SAMPLES
    session_id: str = ""
    frames: int = 0              # frames decoded
    hand_frames: int = 0         # frames with a usable hand
    trimmed: int = 0             # hand frames dropped at the start and end
    samples: int = 0             # rows written (or that would be written in a dry run)
    detail: str = ""


# ---------------------------------------------------------------------------
# Finding the videos
# ---------------------------------------------------------------------------

def collect_sources(paths: Sequence[str], label: Optional[str] = None) -> List[VideoSource]:
    """Expand folders and files into (video, gesture) pairs, in a stable order."""
    sources: List[VideoSource] = []
    for raw in paths:
        path = Path(raw).expanduser()
        if path.is_dir():
            files = sorted(f for f in path.iterdir()
                           if f.is_file() and f.suffix.lower() in VIDEO_SUFFIXES
                           and not f.name.startswith("."))
            if not files:
                raise VideoImportError(f"No video files ({', '.join(VIDEO_SUFFIXES)}) in {path}.")
            name = label or path.name
        elif path.is_file():
            if path.suffix.lower() not in VIDEO_SUFFIXES:
                raise VideoImportError(f"{path.name} is not a supported video ({', '.join(VIDEO_SUFFIXES)}).")
            if not label:
                raise VideoImportError(f"Give the gesture for {path.name} with --label.")
            files, name = [path], label
        else:
            raise VideoImportError(f"{path} does not exist.")
        try:
            gesture = dc.slugify_label(name)
        except ValueError as exc:
            raise VideoImportError(f"Cannot make a gesture name from {name!r}: {exc}") from exc
        sources.extend(VideoSource(f, gesture) for f in files)
    return sources


def find_meme_images(paths: Sequence[str], label: Optional[str] = None) -> List[Tuple[str, str, List[Path]]]:
    """(gesture id, gesture name, image files) for each folder in `paths`."""
    found = []
    for raw in paths:
        path = Path(raw).expanduser()
        if not path.is_dir():
            continue
        name = label or path.name
        images = sorted(f for f in path.iterdir()
                        if f.is_file() and f.suffix.lower() in config.MEME_IMAGE_SUFFIXES
                        and not f.name.startswith("."))
        found.append((dc.slugify_label(name), name, images))
    return found


def register_memes(found: Sequence[Tuple[str, str, List[Path]]], library: Optional[dm.MemeLibrary] = None,
                   dry_run: bool = False, log: Callable[[str], None] = lambda _msg: None) -> List[str]:
    """Set each folder's single image as its gesture's meme. Returns notes on what was not set."""
    library = library or dm.MemeLibrary()
    notes = []
    for gesture, name, images in found:
        if not images:
            continue
        if len(images) > 1:
            notes.append(f"{name} has {len(images)} images, so none was set as its meme. Choose one with: "
                         f"python dataset_manager.py {gesture} --image <file>")
            continue
        try:
            existing = library.load().get(gesture)
            problem = dm.image_file_problem(images[0])
            if problem:
                raise dm.MemeError(problem)
            if dry_run:
                log(f"  meme for {gesture}: would use {images[0].name}")
                continue
            record = library.update(gesture, image=images[0],
                                    gesture_name=None if existing and existing.gesture_name else name)
        except dm.MemeError as exc:
            notes.append(f"Meme for {gesture} not set: {exc}")
            continue
        log(f"  meme for {gesture}: {images[0].name} saved as {record.image_path}")
    return notes


def file_digest(path: Path) -> str:
    """SHA-256 of the file's bytes. Identical files have identical digests."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def session_id_for(digest: str) -> str:
    """Recording id for an imported file: the same length as the recorder's random ids."""
    return digest[:12]


# ---------------------------------------------------------------------------
# Reading frames
# ---------------------------------------------------------------------------

def read_frames(path: Path) -> Iterator[Tuple[float, np.ndarray]]:
    """Yield (seconds from the start, BGR frame) for every frame in the file."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise VideoImportError(f"Cannot open {path.name}. OpenCV could not read it as a video.")
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or not np.isfinite(fps) or fps <= 0:
            raise VideoImportError(f"{path.name} does not report a frame rate.")
        index = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            yield index / fps, frame
            index += 1
        if index == 0:
            raise VideoImportError(f"No frames could be read from {path.name}.")
    finally:
        cap.release()


def to_camera_scale(frame: np.ndarray) -> np.ndarray:
    """Shrink a large frame to the live camera's height, keeping its shape.

    Landmarks are then found at about the resolution the webcam provides. The aspect
    ratio does not need to match: `features.correct_aspect` handles that.
    """
    h, w = frame.shape[:2]
    if h <= config.CAMERA_HEIGHT:
        return frame
    scale = config.CAMERA_HEIGHT / h
    return cv2.resize(frame, (max(1, round(w * scale)), config.CAMERA_HEIGHT),
                      interpolation=cv2.INTER_AREA)


# ---------------------------------------------------------------------------
# One video -> one recording
# ---------------------------------------------------------------------------

def extract_recording(path: Path, label: str, person: str = "",
                      rate_hz: float = config.COLLECT_RATE_HZ, trim_s: float = DEFAULT_TRIM_S,
                      mode: str = config.FEATURE_MODE,
                      detector_factory: Optional[Callable[[], object]] = None,
                      ) -> Tuple[dc.RecordingResult, ImportOutcome]:
    """Run a video through the live landmark pipeline and sample it like the recorder.

    `detector_factory` replaces MediaPipe in tests. The returned result has a random
    session id; `import_videos` replaces it with one derived from the file.
    """
    video_ms = [0]                                   # time of the frame being processed
    factory = detector_factory or (lambda: vision.MediaPipeDetector(
        use_pose=(mode == "hands+pose"), clock_ms=lambda: video_ms[0]))
    hook = vision.LandmarkHook(detector_factory=factory, mode=mode)
    hook.show_landmarks = False                      # nothing is displayed
    processor = vision.FrameProcessor(frame_hook=hook)   # mirrors frames as the camera path does

    seen: List[Tuple[float, Optional[np.ndarray]]] = []
    try:
        for t, frame in read_frames(path):
            video_ms[0] = int(round(t * 1000))
            processor.process(to_camera_scale(frame))
            error = processor.get_stats().error
            if error:
                raise VideoImportError(f"{path.name}: {error}")
            seen.append((t, processor.get_latest_features()))
    finally:
        hook.close()

    outcome = ImportOutcome(path, label, NO_SAMPLES, frames=len(seen))
    hand_times = [t for t, v in seen if v is not None]
    outcome.hand_frames = len(hand_times)
    if not hand_times:
        outcome.detail = "no hand was found in any frame"
        return dc.RecordingResult("", label, person, ""), outcome

    first, last = hand_times[0] + trim_s, hand_times[-1] - trim_s
    video_t = [0.0]
    recorder = dc.Recorder(rate_hz=rate_hz, clock=lambda: video_t[0])
    recorder.start(label, target=len(seen), person=person, countdown_s=0)
    for t, vector in seen:
        if vector is not None and not first <= t <= last:
            outcome.trimmed += 1
            continue
        video_t[0] = t
        recorder.offer(vector)
    recorder.stop()
    result = recorder.pop_finished()
    outcome.samples = len(result.samples)
    if not result.samples:
        outcome.detail = (f"a hand was visible for only {hand_times[-1] - hand_times[0]:.2f} s, "
                          f"less than the {trim_s:.2f} s trimmed at each end")
    return result, outcome


def import_videos(sources: Sequence[VideoSource], store: Optional[dc.DatasetStore] = None,
                  person: str = "", rate_hz: float = config.COLLECT_RATE_HZ,
                  trim_s: float = DEFAULT_TRIM_S, dry_run: bool = False,
                  detector_factory: Optional[Callable[[], object]] = None,
                  log: Callable[[str], None] = lambda _msg: None) -> List[ImportOutcome]:
    """Import each video as one recording. Returns one outcome per video, in order."""
    if rate_hz <= 0:
        raise VideoImportError("The sample rate must be above 0.")
    if trim_s < 0:
        raise VideoImportError("The trim must be 0 seconds or more.")
    store = store or dc.DatasetStore()
    try:
        existing = store.load()
    except dc.DatasetError as exc:
        raise VideoImportError(str(exc)) from exc
    known = dict(zip(existing["session_id"], existing["label"]))

    outcomes: List[ImportOutcome] = []
    first_file_for: dict = {}                        # digest -> path imported earlier in this run
    for src in sources:
        digest = file_digest(src.path)
        session_id = session_id_for(digest)
        if digest in first_file_for:
            outcomes.append(ImportOutcome(src.path, src.label, DUPLICATE, session_id,
                                          detail=f"identical to {first_file_for[digest].name}"))
            log(f"  {src.path.name}: skipped, it is an identical copy of {first_file_for[digest].name}")
            continue
        first_file_for[digest] = src.path
        if session_id in known:
            outcomes.append(ImportOutcome(src.path, src.label, ALREADY_IMPORTED, session_id,
                                          detail=f"already in the dataset as {known[session_id]}"))
            log(f"  {src.path.name}: skipped, already in the dataset as {known[session_id]}")
            continue

        result, outcome = extract_recording(src.path, src.label, person, rate_hz, trim_s,
                                            store.feature_mode, detector_factory)
        outcome.session_id = session_id
        if outcome.samples:
            result.session_id = session_id
            result.timestamp = datetime.fromtimestamp(src.path.stat().st_mtime).isoformat(timespec="seconds")
            if not dry_run:
                store.append(result)
            outcome.status = IMPORTED
            known[session_id] = src.label
        outcomes.append(outcome)
        verb = "would add" if dry_run else "added"
        log(f"  {src.path.name}: {outcome.frames} frames, hand in {outcome.hand_frames}, "
            f"{outcome.trimmed} trimmed, {verb} {outcome.samples} samples"
            + (f" ({outcome.detail})" if outcome.detail else ""))
    return outcomes


def format_summary(outcomes: Sequence[ImportOutcome], store: dc.DatasetStore, dry_run: bool) -> str:
    """Per-gesture totals after the import, with what each gesture still needs."""
    added = sum(o.samples for o in outcomes if o.status == IMPORTED)
    lines = ["", "Dry run: nothing was saved." if dry_run
             else f"Saved to {store.csv_path}." if added else "No new samples, so the dataset is unchanged."]
    lines.append(f"{'Would add' if dry_run else 'Added'} {added} samples from "
                 f"{sum(o.status == IMPORTED for o in outcomes)} of {len(outcomes)} videos.")
    skipped = [o for o in outcomes if o.status != IMPORTED]
    if skipped:
        lines.append("Not imported:")
        lines += [f"  {o.path.parent.name}/{o.path.name}: {o.status}, {o.detail}" for o in skipped]
    if not dry_run:
        summary = store.summary()
        if not summary.empty:
            lines += ["", f"  {'gesture':<20}{'samples':>8}{'recordings':>12}   status"]
            for row in summary.itertuples():
                _, hint = dc.class_status(row.samples, row.recordings)
                lines.append(f"  {row.label:<20}{row.samples:>8}{row.recordings:>12}   {hint}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", help="folders (one gesture each) or video files")
    parser.add_argument("--label", help="gesture name for every video given (default: the folder name)")
    parser.add_argument("--person", default="", help="who is in the videos (optional, saved with the samples)")
    parser.add_argument("--rate", type=float, default=config.COLLECT_RATE_HZ,
                        help=f"samples per second of video (default {config.COLLECT_RATE_HZ}, as the recorder)")
    parser.add_argument("--trim", type=float, default=DEFAULT_TRIM_S,
                        help=f"seconds dropped at the start and end of the hand being visible (default {DEFAULT_TRIM_S})")
    parser.add_argument("--dry-run", action="store_true", help="report what would be imported, save nothing")
    args = parser.parse_args(argv)

    store = dc.DatasetStore()
    try:
        sources = collect_sources(args.paths, args.label)
        print(f"Importing {len(sources)} videos ({config.FEATURE_MODE} features, "
              f"{args.rate:g} samples per second, {args.trim:g} s trimmed at each end)...")
        outcomes = import_videos(sources, store, args.person, args.rate, args.trim, args.dry_run, log=print)
        meme_notes = register_memes(find_meme_images(args.paths, args.label), dry_run=args.dry_run, log=print)
    except (VideoImportError, dc.DatasetError) as exc:
        print(f"\nCannot import: {exc}", file=sys.stderr)
        return 1
    print(format_summary(outcomes, store, args.dry_run))
    for note in meme_notes:
        print(note)
    if not args.dry_run and any(o.status == IMPORTED for o in outcomes):
        print("\nTrain the model with: python train_model.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
