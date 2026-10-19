"""End-to-end check without a webcam: play recorded clips through the live path.

    python check_pipeline.py "First meme" "Second meme" "Meme 3" "Meme 4" None
    python check_pipeline.py new_clip.mov --label meme_3

Every frame of every video goes through the same code as the Live dashboard, in order:
`vision.FrameProcessor` mirrors it, `vision.LandmarkHook` finds the hands with MediaPipe
and builds the feature vector, and `predictor.LiveRecognizer` classifies it, applies the
steady vote (MIN_STABLE_FRAMES of the last SMOOTHING_WINDOW frames) and keeps the recent
detections. The script reports what the dashboard would have shown during the clip.

Which model classifies a clip:

* A clip that is already in data/samples.csv (imported with import_videos.py) is
  classified by a model trained on every other recording, with the regularisation
  strength of the saved model. That model has never seen the clip, so the result
  says how a new recording of the gesture would do.
* Any other clip is classified by the saved model in models/, the one the dashboard
  uses. Record a fresh clip, for example in other light, and check it this way.

A folder is one gesture, named after the folder, as in import_videos.py. Frames are
classified one at a time at the video's own timing; the live dashboard skips frames
when the computer falls behind, so its timings can differ a little. Nothing is saved.
"""
from __future__ import annotations

import argparse
import statistics
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import config
import data_collector as dc
import import_videos as iv
import predictor as pr
import train_model as tm
import vision

# What the dashboard's Meme panel shows in a frame
RIGHT, WRONG, NO_GESTURE, UNSURE, NO_HAND = "right", "wrong", "no gesture", "unsure", "no hand"
STATES = (RIGHT, WRONG, NO_GESTURE, UNSURE, NO_HAND)


class CheckError(RuntimeError):
    """The check cannot run. The message says why."""


@dataclass
class ClipResult:
    path: Path
    label: str
    model: str = ""                  # which model classified the clip
    frames: int = 0
    hand_frames: int = 0
    span: int = 0                    # frames from the first to the last frame with a hand
    shown: Counter = field(default_factory=Counter)    # state -> frames, within the span
    first_right_s: Optional[float] = None   # from the first hand frame to the first right result
    detections: List[Tuple[float, str]] = field(default_factory=list)   # (seconds, gesture)
    error: str = ""

    def share(self, state: str) -> float:
        return self.shown[state] / self.span if self.span else 0.0


def dashboard_state(steady: Optional[pr.Steady], latest: Optional[pr.Prediction], expected: str) -> str:
    """What the dashboard shows for this steady result and latest frame, judged against
    the clip's gesture."""
    if steady is None:                           # no gesture shown: why not?
        return NO_HAND if latest is None or latest.status == pr.NO_HAND else UNSURE
    if steady.label == expected:
        return RIGHT
    if steady.label == config.NONE_LABEL:
        return NO_GESTURE
    return WRONG                                 # another gesture, and its meme


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ModelSource:
    """Gives each clip a model: one trained without the clip when the clip is in the
    dataset, otherwise the saved model."""

    def __init__(self, store: Optional[dc.DatasetStore] = None,
                 saved_loader: Callable[[], pr.Predictor] = pr.Predictor.load,
                 l2: Optional[float] = None) -> None:
        self.store = store or dc.DatasetStore()
        try:
            raw = self.store.load()
        except dc.DatasetError as exc:
            raise CheckError(str(exc)) from exc
        self._df = tm.validate_dataset(raw, self.store.feature_length)[0].reset_index(drop=True) \
            if not raw.empty else raw
        self._saved_loader = saved_loader
        self._saved: Optional[pr.Predictor] = None
        self._l2 = l2
        self._held_out: Dict[str, pr.Predictor] = {}

    def recordings(self) -> Dict[str, str]:
        """{recording id: gesture} for every recording in the dataset."""
        if self._df.empty:
            return {}
        return dict(zip(self._df["session_id"], self._df["label"]))

    def l2(self) -> float:
        if self._l2 is None:
            try:
                report = tm.load_report()
            except tm.TrainingError as exc:
                raise CheckError(str(exc)) from exc
            if not report or "cost" not in report:
                raise CheckError("Train the model first (python train_model.py), so clips from the "
                                 "dataset are checked with the same settings as the saved model.")
            self._l2 = float(report["cost"]["l2"])
        return self._l2

    def saved(self) -> pr.Predictor:
        if self._saved is None:
            try:
                self._saved = self._saved_loader()
            except pr.PredictorError as exc:
                raise CheckError(str(exc)) from exc
        return self._saved

    def without(self, session_id: str) -> pr.Predictor:
        """A model trained on every recording except `session_id`."""
        if session_id not in self._held_out:
            df = self._df
            labels = sorted(df["label"].unique())
            keep = df["session_id"] != session_id
            label = df.loc[~keep, "label"].iloc[0]
            if not (df.loc[keep, "label"] == label).any():
                raise CheckError(f"This is the only recording of {label}, so no model can learn "
                                 "the gesture without it. Record another one.")
            X, y = tm._xy(df, labels)
            model = tm.make_model(self.l2()).fit(X[keep.to_numpy()], y[keep.to_numpy()])
            self._held_out[session_id] = pr.Predictor(model, labels, self.store.feature_mode)
        return self._held_out[session_id]

    def for_clip(self, session_id: str) -> Tuple[pr.Predictor, str]:
        """(predictor, description of it) for the clip with this recording id."""
        if session_id in self.recordings():
            return self.without(session_id), "a model trained without this clip"
        return self.saved(), "the saved model"


# ---------------------------------------------------------------------------
# Replaying one clip
# ---------------------------------------------------------------------------

def replay_clip(path: Path, expected: str, model: pr.Predictor, mode: str = config.FEATURE_MODE,
                detector_factory: Optional[Callable[[], object]] = None) -> ClipResult:
    """Play every frame of `path` through the live path and record what the dashboard shows."""
    result = ClipResult(path, expected)
    video_ms = [0]
    factory = detector_factory or (lambda: vision.MediaPipeDetector(
        use_pose=(mode == "hands+pose"), clock_ms=lambda: video_ms[0]))
    hook = vision.LandmarkHook(detector_factory=factory, mode=mode)
    hook.show_landmarks = False
    processor = vision.FrameProcessor(frame_hook=hook)
    recognizer = pr.LiveRecognizer(model)

    timeline: List[Tuple[float, bool, str]] = []        # (seconds, hand in view, dashboard state)
    try:
        for t, frame in iv.read_frames(path):
            video_ms[0] = int(round(t * 1000))
            processor.process(iv.to_camera_scale(frame))
            error = processor.get_stats().error
            if error:
                raise CheckError(f"{path.name}: {error}")
            vector = processor.get_latest_features()
            latest = recognizer.classify(vector, at=t)
            timeline.append((t, vector is not None, dashboard_state(recognizer.steady(), latest, expected)))
    finally:
        hook.close()

    result.frames = len(timeline)
    hand_at = [i for i, (_, hand, _) in enumerate(timeline) if hand]
    result.hand_frames = len(hand_at)
    if hand_at:
        span = timeline[hand_at[0]: hand_at[-1] + 1]
        result.span = len(span)
        result.shown = Counter(state for _, _, state in span)
        start = timeline[hand_at[0]][0]
        result.first_right_s = next((t - start for t, _, state in span if state == RIGHT), None)
    entries, _ = recognizer.history()
    result.detections = [(e.at, e.label) for e in reversed(entries)]
    return result


def check_clips(sources: Sequence[iv.VideoSource], models: ModelSource,
                detector_factory: Optional[Callable[[], object]] = None,
                log: Callable[[str], None] = lambda _msg: None) -> List[ClipResult]:
    """Replay each clip with the right model. A clip that cannot be checked gets `error` set."""
    results = []
    known = models.recordings()
    first_file_for: Dict[str, Path] = {}             # digest -> clip checked earlier in this run
    for src in sources:
        try:
            digest = iv.file_digest(src.path)
            if digest in first_file_for:
                raise CheckError(f"identical to {first_file_for[digest].name}, which is checked once")
            first_file_for[digest] = src.path
            session_id = iv.session_id_for(digest)
            if session_id in known and known[session_id] != src.label:
                raise CheckError(f"this clip is in the dataset as {known[session_id]}, not {src.label}")
            model, which = models.for_clip(session_id)
            if src.label not in model.labels:
                raise CheckError(f"the model does not know the gesture {src.label}. It knows "
                                 f"{', '.join(model.labels)}.")
            result = replay_clip(src.path, src.label, model, models.store.feature_mode, detector_factory)
            result.model = which
        except (CheckError, iv.VideoImportError, pr.PredictorError) as exc:
            result = ClipResult(src.path, src.label, error=str(exc))
        results.append(result)
        log(format_clip(result))
    return results


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _pct(x: float) -> str:
    return f"{x:.0%}"


def format_clip(r: ClipResult) -> str:
    head = f"{r.path.parent.name}/{r.path.name} ({r.label})"
    if r.error:
        return f"{head}\n  not checked: {r.error}\n"
    if not r.hand_frames:
        return f"{head}\n  {r.frames} frames, no hand found in any of them. Checked with {r.model}.\n"
    expected = "No gesture" if r.label == config.NONE_LABEL else r.label
    lines = [
        head,
        f"  {r.frames} frames, a hand in {r.hand_frames}. Checked with {r.model}.",
        f"  From the first to the last frame with a hand, the dashboard showed: {expected} "
        f"{_pct(r.share(RIGHT))}, a wrong gesture {_pct(r.share(WRONG))}"
        + ("" if r.label == config.NONE_LABEL else f", No gesture {_pct(r.share(NO_GESTURE))}")
        + f", unsure or still checking {_pct(r.share(UNSURE))}, no hand in view {_pct(r.share(NO_HAND))}.",
    ]
    if r.label != config.NONE_LABEL:
        lines.append(f"  {r.label} first showed {r.first_right_s:.2f} s after the hand appeared."
                     if r.first_right_s is not None else f"  {r.label} never showed.")
    shown = ", ".join(f"{label} at {t:.1f} s" for t, label in r.detections) or "none"
    lines.append(f"  Recent detections: {shown}.")
    return "\n".join(lines) + "\n"


def format_summary(results: Sequence[ClipResult]) -> str:
    checked = [r for r in results if not r.error and r.span]
    lines = ["Summary, per gesture (shares of the frames from the first to the last hand frame):",
             f"  {'gesture':<16}{'clips':>6}{'right':>8}{'wrong':>8}{'no gesture':>12}{'unsure':>8}"
             f"{'no hand':>9}{'first right, median':>22}"]
    for label in sorted({r.label for r in checked}):
        group = [r for r in checked if r.label == label]
        span = sum(r.span for r in group)
        share = {s: sum(r.shown[s] for r in group) / span for s in STATES}
        firsts = [r.first_right_s for r in group if r.first_right_s is not None]
        first = ("n/a" if label == config.NONE_LABEL
                 else f"{statistics.median(firsts):.2f} s" if firsts else "never")
        lines.append(f"  {label:<16}{len(group):>6}{_pct(share[RIGHT]):>8}{_pct(share[WRONG]):>8}"
                     f"{_pct(share[NO_GESTURE]) if label != config.NONE_LABEL else '':>12}"
                     f"{_pct(share[UNSURE]):>8}{_pct(share[NO_HAND]):>9}{first:>22}")
    wrong = [r for r in checked if r.shown[WRONG]]
    lines.append("")
    lines.append(f"A wrong gesture was shown in {len(wrong)} of {len(checked)} clips"
                 + (": " + "; ".join(f"{r.path.parent.name}/{r.path.name} for {r.shown[WRONG]} frames"
                                     for r in wrong) if wrong else "."))
    missed = [r for r in checked if r.label != config.NONE_LABEL and r.first_right_s is None]
    if missed:
        lines.append("The right gesture never showed in: "
                     + "; ".join(f"{r.path.parent.name}/{r.path.name}" for r in missed) + ".")
    skipped = [r for r in results if r.error or not r.span]
    if skipped:
        lines.append(f"{len(skipped)} clip(s) could not be checked; see above.")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", help="folders (one gesture each) or video files")
    parser.add_argument("--label", help="gesture of every video given (default: the folder name)")
    args = parser.parse_args(argv)
    try:
        sources = iv.collect_sources(args.paths, args.label)
        models = ModelSource()
        print(f"Checking {len(sources)} clips through the live recognition path "
              f"(steady after {config.MIN_STABLE_FRAMES} of {config.SMOOTHING_WINDOW} frames, "
              f"confidence threshold {config.DEFAULT_CONFIDENCE_THRESHOLD:.0%}).\n")
        results = check_clips(sources, models, log=print)
    except (CheckError, iv.VideoImportError, dc.DatasetError) as exc:
        print(f"\nCannot check: {exc}", file=sys.stderr)
        return 1
    print(format_summary(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
