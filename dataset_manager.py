"""Gesture metadata: the meme, title, Ball Knowledge rating and description for each gesture.

    python dataset_manager.py                                   # list every gesture's meme
    python dataset_manager.py first_meme --image "First meme/images.jpeg"
    python dataset_manager.py first_meme --title "..." --rating "8/10" --description "..."

Stored in assets/memes/memes.json, one record per gesture id:

    {
      "first_meme": {
        "gesture_name": "First meme",
        "meme_title": "",
        "image_path": "assets/memes/first_meme.jpeg",
        "ball_knowledge_level": "",
        "description": ""
      }
    }

Image paths are relative to the project folder, so the project can be moved. An image
set with --image is copied into assets/memes/ as <gesture id>.<extension>.

The rating and description are yours. The model only recognises the gesture; it does
not produce or judge either of them, and the Memes page says so. Empty fields stay
empty (the dashboard leaves them out; the Memes page and the listing above show them as
not set), never filled in with made-up text.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

import config
import data_collector as dc
import storage

FIELDS = ("gesture_name", "meme_title", "image_path", "ball_knowledge_level", "description")
MAX_TEXT = {"gesture_name": 60, "meme_title": 80, "ball_knowledge_level": 40, "description": 400}
# What Pillow calls the image types a browser can show (MPO is a JPEG from some phones).
# A file is checked by its content: a TIFF renamed .png is refused, since no browser shows it.
BROWSER_IMAGE_FORMATS = {"JPEG", "MPO", "PNG", "WEBP", "GIF"}


class MemeError(RuntimeError):
    """The meme list cannot be read or a change is invalid. The message says why."""


@dataclass
class MemeRecord:
    gesture_id: str
    gesture_name: str = ""
    meme_title: str = ""
    image_path: str = ""
    ball_knowledge_level: str = ""
    description: str = ""


def display_name(label: Optional[str], records: Optional[Dict[str, MemeRecord]]) -> str:
    """The name to show for a gesture id: its gesture_name from memes.json if set, else the id.
    Every panel uses this, so one gesture never appears under two names."""
    if label is None:
        return ""
    record = (records or {}).get(label)
    if record is not None and record.gesture_name:
        return record.gesture_name
    if label == config.NONE_LABEL:
        return "No gesture"              # the same words the dashboard's Meme panel uses
    return label


def image_file_problem(path: Path) -> Optional[str]:
    """Why the file cannot be shown as a meme image, or None if it can."""
    if path.suffix.lower() not in config.MEME_IMAGE_SUFFIXES:
        return f"{path.name} is not a supported image ({', '.join(config.MEME_IMAGE_SUFFIXES)})."
    if not path.is_file():
        return f"The image file {path.name} is missing."
    try:
        from PIL import Image
        with Image.open(path) as img:
            img.verify()
            readable = img.format in BROWSER_IMAGE_FORMATS
    except Exception:                            # truncated, not an image, unreadable
        readable = False
    if not readable:
        kinds = [s.lstrip(".").upper() for s in config.MEME_IMAGE_SUFFIXES]
        return (f"{path.name} cannot be read as an image. Choose a "
                f"{', '.join(kinds[:-1])} or {kinds[-1]} file.")
    return None


class MemeLibrary:
    """assets/memes/ and its memes.json under a project folder."""

    def __init__(self, root: Path = config.PROJECT_ROOT) -> None:
        self.root = Path(root)
        self.dir = self.root / "assets" / "memes"
        self.file = self.dir / config.MEMES_FILE.name

    # --- reading -----------------------------------------------------------------
    def load(self) -> Dict[str, MemeRecord]:
        """Every record, by gesture id. An absent file means no memes yet."""
        if not self.file.exists():
            return {}
        try:
            raw = json.loads(self.file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MemeError(f"Cannot read {self.file.name}: {exc}") from exc
        if not isinstance(raw, dict):
            raise MemeError(f"{self.file.name} must map gesture ids to records.")
        records = {}
        for gesture_id, fields in raw.items():
            if not isinstance(fields, dict):
                raise MemeError(f"The record for {gesture_id} in {self.file.name} is not an object.")
            unknown = sorted(set(fields) - set(FIELDS))
            if unknown:
                raise MemeError(f"The record for {gesture_id} has unknown fields: {', '.join(unknown)}.")
            bad = [k for k, v in fields.items() if not isinstance(v, str)]
            if bad:
                raise MemeError(f"The record for {gesture_id} has non-text values for: {', '.join(bad)}.")
            records[gesture_id] = MemeRecord(gesture_id, **fields)
        return records

    def image_file(self, record: MemeRecord) -> Path:
        return self.root / record.image_path

    def image_problem(self, record: MemeRecord) -> Optional[str]:
        """Why the record's image cannot be shown, or None if it can."""
        if not record.image_path:
            return f"No image is set for {record.gesture_id}."
        path = self.image_file(record)
        try:
            inside = path.resolve().is_relative_to(self.dir.resolve())
        except OSError:
            inside = False
        if Path(record.image_path).is_absolute() or not inside:
            return f"The image for {record.gesture_id} must be inside assets/memes/, not {record.image_path}."
        return image_file_problem(path)

    def missing_for(self, labels: List[str]) -> List[str]:
        """Gestures in `labels` without a usable meme. The no-gesture class needs none."""
        records = self.load()
        return [l for l in labels if l != config.NONE_LABEL
                and (l not in records or self.image_problem(records[l]) is not None)]

    # --- writing -----------------------------------------------------------------
    # Every change is a read-modify-write of memes.json, done under one lock so two tabs
    # (or a tab and the command line) editing at once never lose each other's edits.
    @contextmanager
    def _editing(self):
        try:
            with storage.locked(self.file, what=self.file.name):
                yield
        except storage.StorageBusyError as exc:
            raise MemeError(str(exc)) from exc

    def _save(self, records: Dict[str, MemeRecord]) -> None:
        data = {gid: {k: v for k, v in asdict(r).items() if k != "gesture_id"}
                for gid, r in sorted(records.items())}
        storage.atomic_write_text(self.file, json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    def update(self, gesture_id: str, image: Optional[Path] = None, **fields: Optional[str]) -> MemeRecord:
        """Create or change one gesture's record. Fields left as None keep their value.

        `image` is copied into assets/memes/ as <gesture id>.<extension>, replacing the
        gesture's previous image. Nothing is written if the image is not a readable image,
        and if memes.json cannot be saved the previous image and record are kept.
        """
        gesture_id = dc.slugify_label(gesture_id)
        unknown = sorted(set(fields) - (set(FIELDS) - {"image_path"}))      # images go through `image`
        if unknown:
            raise MemeError(f"Unknown fields: {', '.join(unknown)}.")
        cleaned = {}
        for key, value in fields.items():
            if value is None:
                continue
            value = " ".join(str(value).split())                # one line, no stray spaces
            if len(value) > MAX_TEXT.get(key, 200):
                raise MemeError(f"{key} is longer than {MAX_TEXT[key]} characters.")
            cleaned[key] = value
        if image is not None:
            image = Path(image).expanduser()
            problem = image_file_problem(image)
            if problem:
                raise MemeError(problem)

        with self._editing():
            records = self.load()
            record = records.get(gesture_id, MemeRecord(gesture_id))
            for key, value in cleaned.items():
                setattr(record, key, value)
            old = target = None
            if image is not None:
                target = self.dir / f"{gesture_id}{image.suffix.lower()}"
                old = self.image_file(record) if record.image_path else None
                data = image.read_bytes()
                before = target.read_bytes() if target.exists() else None
                if before != data:
                    storage.atomic_write_bytes(target, data)     # never shown half copied
                record.image_path = target.relative_to(self.root).as_posix()
            records[gesture_id] = record
            try:
                self._save(records)
            except BaseException:
                if target is not None and before != data:        # put the image back as it was
                    if before is None:
                        target.unlink(missing_ok=True)
                    else:
                        storage.atomic_write_bytes(target, before)
                raise
            # the previous image goes only once memes.json no longer points at it
            if old is not None and old != target and old.parent == self.dir and old.exists():
                old.unlink()
        return record

    def remove(self, gesture_id: str) -> bool:
        """Delete a gesture's record and its copied image. Returns False if there was none."""
        with self._editing():
            records = self.load()
            record = records.pop(gesture_id, None)
            if record is None:
                return False
            self._save(records)                      # the image goes only once nothing points at it
            path = self.image_file(record) if record.image_path else None
            if path is not None and path.parent == self.dir and path.exists():
                path.unlink()
        return True


def save_edit(library: MemeLibrary, gesture_id: str, *, gesture_name: str, meme_title: str,
              ball_knowledge_level: str, description: str,
              upload_name: Optional[str] = None, upload_bytes: Optional[bytes] = None) -> MemeRecord:
    """Save one gesture's meme from the Memes page. Text fields are saved as given (an empty
    field clears it). An uploaded image is checked and copied exactly like --image; if it
    is not a readable image, nothing at all is written."""
    image = None
    tmp_dir = None
    if upload_bytes is not None and len(upload_bytes) > config.MEME_MAX_UPLOAD_MB * 1024 * 1024:
        raise MemeError(f"{upload_name or 'The image'} is larger than {config.MEME_MAX_UPLOAD_MB} MB. "
                        "Choose a smaller image.")
    try:
        if upload_bytes is not None:
            import tempfile
            suffix = Path(upload_name or "").suffix.lower()
            tmp_dir = Path(tempfile.mkdtemp(prefix="bk-meme-"))
            image = tmp_dir / f"upload{suffix}"
            image.write_bytes(upload_bytes)
        try:
            return library.update(gesture_id, image=image, gesture_name=gesture_name,
                                  meme_title=meme_title, ball_knowledge_level=ball_knowledge_level,
                                  description=description)
        except MemeError as exc:            # name the file the user chose, not the temporary copy
            if image is not None and upload_name:
                raise MemeError(str(exc).replace(image.name, upload_name)) from exc
            raise
    finally:
        if tmp_dir is not None:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def describe(library: MemeLibrary) -> str:
    records = library.load()
    if not records:
        return "No memes yet. Add one with: python dataset_manager.py <gesture> --image <file>"
    lines = []
    for gid, r in records.items():
        problem = library.image_problem(r)
        lines += [f"{gid}",
                  f"  name         {r.gesture_name or 'not set'}",
                  f"  meme title   {r.meme_title or 'not set'}",
                  f"  image        {r.image_path or 'not set'}" + (f"  (problem: {problem})" if problem else ""),
                  f"  rating       {r.ball_knowledge_level or 'not set'}",
                  f"  description  {r.description or 'not set'}"]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("gesture", nargs="?", help="gesture id to change (omit to list every meme)")
    parser.add_argument("--image", help="image file to copy into assets/memes/")
    parser.add_argument("--name", help="gesture name shown on the dashboard")
    parser.add_argument("--title", help="meme title")
    parser.add_argument("--rating", help="Ball Knowledge rating, as you want it shown (e.g. 8/10)")
    parser.add_argument("--description", help="short description of the meme")
    parser.add_argument("--remove", action="store_true", help="delete this gesture's meme record and image")
    args = parser.parse_args(argv)
    library = MemeLibrary()
    try:
        if args.gesture is None:
            print(describe(library))
            return 0
        if args.remove:
            print("Removed." if library.remove(args.gesture) else f"No meme for {args.gesture}.")
            return 0
        library.update(args.gesture, image=args.image, gesture_name=args.name, meme_title=args.title,
                       ball_knowledge_level=args.rating, description=args.description)
        print(describe(library))
    except (MemeError, ValueError) as exc:
        print(f"\nCannot update memes: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
