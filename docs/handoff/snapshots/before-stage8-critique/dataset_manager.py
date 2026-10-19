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
not produce or judge either of them, and the dashboard says so. Empty fields are
shown as "not set", never filled in with made-up text.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

import config
import data_collector as dc

FIELDS = ("gesture_name", "meme_title", "image_path", "ball_knowledge_level", "description")
MAX_TEXT = {"gesture_name": 60, "meme_title": 80, "ball_knowledge_level": 40, "description": 400}


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

    @property
    def title(self) -> str:
        """The meme title, or the gesture name when no title is set."""
        return self.meme_title or self.gesture_name or self.gesture_id


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
    except Exception as exc:                     # truncated, not an image, unreadable
        return f"{path.name} cannot be read as an image ({type(exc).__name__})."
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
    def _save(self, records: Dict[str, MemeRecord]) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        data = {gid: {k: v for k, v in asdict(r).items() if k != "gesture_id"}
                for gid, r in sorted(records.items())}
        tmp = self.file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, self.file)

    def update(self, gesture_id: str, image: Optional[Path] = None, **fields: Optional[str]) -> MemeRecord:
        """Create or change one gesture's record. Fields left as None keep their value.

        `image` is copied into assets/memes/ as <gesture id>.<extension>, replacing the
        gesture's previous image. Nothing is written if the image is not a readable image.
        """
        gesture_id = dc.slugify_label(gesture_id)
        unknown = sorted(set(fields) - (set(FIELDS) - {"image_path"}))      # images go through `image`
        if unknown:
            raise MemeError(f"Unknown fields: {', '.join(unknown)}.")
        records = self.load()
        record = records.get(gesture_id, MemeRecord(gesture_id))
        for key, value in fields.items():
            if value is None:
                continue
            value = " ".join(str(value).split())                # one line, no stray spaces
            if len(value) > MAX_TEXT.get(key, 200):
                raise MemeError(f"{key} is longer than {MAX_TEXT[key]} characters.")
            setattr(record, key, value)

        if image is not None:
            image = Path(image).expanduser()
            problem = image_file_problem(image)
            if problem:
                raise MemeError(problem)
            suffix = image.suffix.lower()
            self.dir.mkdir(parents=True, exist_ok=True)
            target = self.dir / f"{gesture_id}{suffix}"
            old = self.image_file(record) if record.image_path else None
            if not (target.exists() and target.read_bytes() == image.read_bytes()):
                shutil.copyfile(image, target)
            if old is not None and old != target and old.parent == self.dir and old.exists():
                old.unlink()                                     # the gesture's previous image
            record.image_path = target.relative_to(self.root).as_posix()

        records[gesture_id] = record
        self._save(records)
        return record

    def remove(self, gesture_id: str) -> bool:
        """Delete a gesture's record and its copied image. Returns False if there was none."""
        records = self.load()
        record = records.pop(gesture_id, None)
        if record is None:
            return False
        path = self.image_file(record) if record.image_path else None
        if path is not None and path.parent == self.dir and path.exists():
            path.unlink()
        self._save(records)
        return True


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
