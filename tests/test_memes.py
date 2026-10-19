"""Meme metadata (dataset_manager.py), the meme panel (ui.meme_card) and importing a
folder's meme image. Uses small generated images in a scratch folder."""
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
import dataset_manager as dm  # noqa: E402
import import_videos as iv  # noqa: E402
import storage  # noqa: E402
import ui  # noqa: E402


def picture(path, colour=(200, 30, 30), size=(40, 30)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, colour).save(path)
    return path


@pytest.fixture
def lib(tmp_path):
    return dm.MemeLibrary(tmp_path / "project")


# --- the metadata file ------------------------------------------------------------

def test_no_file_means_no_memes(lib):
    assert lib.load() == {}
    assert lib.missing_for(["a", config.NONE_LABEL]) == ["a"]        # none never needs a meme


def test_setting_an_image_copies_it_and_records_a_relative_path(lib, tmp_path):
    src = picture(tmp_path / "First meme" / "images.jpeg")
    record = lib.update("First meme", image=src, gesture_name="First meme")
    assert record.gesture_id == "first_meme"
    assert record.image_path == "assets/memes/first_meme.jpeg"
    assert (lib.dir / "first_meme.jpeg").read_bytes() == src.read_bytes()
    assert src.exists()                                              # the original is left alone
    saved = json.loads(lib.file.read_text())
    assert saved == {"first_meme": {"gesture_name": "First meme", "meme_title": "",
                                    "image_path": "assets/memes/first_meme.jpeg",
                                    "ball_knowledge_level": "", "description": ""}}
    assert lib.image_problem(lib.load()["first_meme"]) is None


def test_updates_keep_fields_that_are_not_given(lib, tmp_path):
    lib.update("wave", image=picture(tmp_path / "a.png"), meme_title="Hello", ball_knowledge_level="8/10")
    lib.update("wave", description="  A   short\nnote ")
    r = lib.load()["wave"]
    assert (r.meme_title, r.ball_knowledge_level, r.description) == ("Hello", "8/10", "A short note")
    assert r.image_path == "assets/memes/wave.png"


def test_a_new_image_replaces_the_old_one(lib, tmp_path):
    lib.update("wave", image=picture(tmp_path / "a.png"))
    lib.update("wave", image=picture(tmp_path / "b.jpg", colour=(0, 0, 200)))
    assert lib.load()["wave"].image_path == "assets/memes/wave.jpg"
    assert sorted(p.name for p in lib.dir.glob("wave.*")) == ["wave.jpg"]


def test_no_meme_record_falls_back_to_the_gesture_name():
    """Owner decision Q7 (code review R6-4): MemeRecord.title fell back to the gesture's name and
    dataset_manager.unfinished fed a dashboard notice removed on 17 October. Only tests still
    used them. Both are gone, so the name fallback cannot come back to the dashboard through them."""
    assert not hasattr(dm.MemeRecord("g", gesture_name="Name"), "title")
    assert not hasattr(dm, "unfinished")


@pytest.mark.parametrize("content,message", [
    ("{not json", "Cannot read"),
    ('["a"]', "map gesture ids"),
    ('{"a": "x"}', "not an object"),
    ('{"a": {"colour": "red"}}', "unknown fields"),
    ('{"a": {"ball_knowledge_level": 9}}', "non-text"),
])
def test_a_broken_file_is_a_clear_error(lib, content, message):
    lib.dir.mkdir(parents=True)
    lib.file.write_text(content)
    with pytest.raises(dm.MemeError, match=message):
        lib.load()


def test_image_problems_are_named(lib, tmp_path):
    lib.dir.mkdir(parents=True)
    (lib.dir / "broken.jpg").write_bytes(b"not an image")
    cases = {
        "": "No image is set",
        "assets/memes/gone.jpg": "missing",
        "assets/memes/broken.jpg": "cannot be read",
        "assets/memes/notes.txt": "not a supported image",
        "../outside.jpg": "must be inside assets/memes",
        "/etc/hosts": "must be inside assets/memes",
    }
    for image_path, message in cases.items():
        assert message in lib.image_problem(dm.MemeRecord("g", image_path=image_path))


def test_bad_images_are_refused_before_anything_is_written(lib, tmp_path):
    fake = tmp_path / "fake.jpg"
    fake.write_bytes(b"not an image")
    with pytest.raises(dm.MemeError, match="cannot be read"):
        lib.update("wave", image=fake)
    with pytest.raises(dm.MemeError, match="not a supported image"):
        lib.update("wave", image=tmp_path / "x.txt")
    assert not lib.file.exists()


@pytest.mark.parametrize("new_name", ["b.png", "b.jpeg"])      # another file type, then the same one
def test_a_failed_save_keeps_the_previous_image_and_record(lib, tmp_path, monkeypatch, new_name):
    """memes.json could not be written (disk full). The old image used to be deleted already,
    leaving the record pointing at nothing while the page said "Nothing was saved"."""
    lib.update("wave", image=picture(tmp_path / "a.jpeg"), gesture_name="Wave")
    before = {p.name: p.read_bytes() for p in lib.dir.iterdir()}
    real = storage.atomic_write_text

    def disk_full(path, text, encoding="utf-8"):
        if Path(path).name == "memes.json":
            raise OSError(28, "No space left on device")
        return real(path, text, encoding)
    monkeypatch.setattr(storage, "atomic_write_text", disk_full)
    with pytest.raises(OSError, match="No space"):
        lib.update("wave", image=picture(tmp_path / new_name, colour=(0, 0, 200)))
    assert {p.name: p.read_bytes() for p in lib.dir.iterdir()} == before      # nothing changed
    assert lib.image_problem(lib.load()["wave"]) is None


@pytest.mark.parametrize("kind", ["JPEG", "PNG", "WEBP", "GIF"])
def test_the_four_image_types_browsers_show_are_accepted(lib, tmp_path, kind):
    path = tmp_path / f"a.{kind.lower()}"
    Image.new("RGB", (40, 30), (200, 30, 30)).save(path, format=kind)
    assert lib.image_problem(lib.update("wave", image=path)) is None


def test_an_image_browsers_cannot_show_is_refused_whatever_its_name(lib, tmp_path):
    """A TIFF renamed .png used to be saved; Chrome then showed a broken image on the dashboard."""
    fake = tmp_path / "meme.png"
    Image.new("RGB", (40, 30), (200, 30, 30)).save(fake, format="TIFF")
    with pytest.raises(dm.MemeError, match="meme.png cannot be read as an image"):
        lib.update("wave", image=fake)
    assert not lib.file.exists()


def test_text_limits_and_unknown_fields(lib):
    with pytest.raises(dm.MemeError, match="longer than"):
        lib.update("wave", ball_knowledge_level="x" * 41)
    with pytest.raises(dm.MemeError, match="Unknown fields"):
        lib.update("wave", image_path="assets/memes/elsewhere.jpg")


def test_remove_deletes_the_record_and_its_copy(lib, tmp_path):
    lib.update("wave", image=picture(tmp_path / "a.png"))
    assert lib.remove("wave") and lib.load() == {}
    assert not (lib.dir / "wave.png").exists()
    assert not lib.remove("wave")


def test_a_failed_remove_keeps_the_image_and_record(lib, tmp_path, monkeypatch):
    """`python dataset_manager.py wave --remove` when memes.json cannot be written used to delete
    the image first, leaving the record pointing at nothing."""
    lib.update("wave", image=picture(tmp_path / "a.png"), gesture_name="Wave")
    before = {p.name: p.read_bytes() for p in lib.dir.iterdir()}

    def disk_full(*_args, **_kwargs):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(storage, "atomic_write_text", disk_full)
    with pytest.raises(OSError, match="No space"):
        lib.remove("wave")
    assert {p.name: p.read_bytes() for p in lib.dir.iterdir()} == before
    assert lib.image_problem(lib.load()["wave"]) is None


def test_edits_made_at_the_same_time_are_all_kept(lib, tmp_path):
    """Two tabs saving different memes at once used to be able to lose one of the edits."""
    import threading
    images = {f"g{i}": picture(tmp_path / f"src{i}.png", colour=(i * 20, 10, 10)) for i in range(6)}
    threads = [threading.Thread(target=lib.update, args=(gid,),
                                kwargs={"image": img, "gesture_name": f"Gesture {gid}"})
               for gid, img in images.items()]
    threads += [threading.Thread(target=lib.update, args=(f"t{i}",), kwargs={"meme_title": f"T{i}"})
                for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    records = lib.load()
    assert sorted(records) == sorted([*images, *(f"t{i}" for i in range(6))])
    assert all(lib.image_problem(records[g]) is None for g in images)
    assert not [p for p in lib.dir.iterdir() if p.name.endswith(".tmp")]


# --- the meme panel -----------------------------------------------------------------

def _live(lib, steady, status="recognised"):
    import time
    import predictor as pr
    prediction = pr.Prediction(status, label="wave", confidence=0.9, top=(("wave", 0.9),), at=time.time())
    return ui.result_card(None, prediction, True, True, steady, lib.load(), None, lib)


def test_no_steady_gesture_shows_no_meme(lib, tmp_path):
    lib.update("wave", image=picture(tmp_path / "a.png"), gesture_name="Wave")
    html = _live(lib, None)
    assert "<b>Hold it steady</b>" in html and "<img" not in html
    assert f"{config.MIN_STABLE_FRAMES} of the last {config.SMOOTHING_WINDOW}" in html


def test_the_none_gesture_has_no_meme(lib):
    import predictor as pr
    html = _live(lib, pr.Steady(config.NONE_LABEL, 0.9, 5, 7))
    assert "<b>No gesture</b>" in html and "<img" not in html


def test_a_gesture_without_a_record_says_how_to_add_one(lib):
    html = ui.meme_card("wave", {}, None, lib)
    assert "No meme set" in html and "dataset_manager.py wave --image" in html and "<img" not in html


def test_a_missing_image_is_reported_not_hidden(lib):
    html = ui.meme_card("wave", {"wave": dm.MemeRecord("wave", image_path="assets/memes/wave.jpg")}, None, lib)
    assert "Image missing" in html and "missing" in html and "<img" not in html


def test_an_unreadable_list_is_reported(lib):
    html = ui.meme_card("wave", None, "Cannot read memes.json: bad", lib)
    assert "Memes cannot be shown" in html and "Cannot read memes.json" in html


def test_a_steady_gesture_shows_its_image_title_rating_and_description(lib, tmp_path):
    lib.update("wave", image=picture(tmp_path / "a.png"), gesture_name="Wave", meme_title="Big <wave>",
               ball_knowledge_level="9/10", description="Says hello & more")
    html = ui.meme_card("wave", lib.load(), None, lib)
    assert '<img class="meme-img" src="data:image/png;base64,' in html
    assert 'alt="Big &lt;wave&gt;"' in html          # the title alone (owner decision Q3, B)
    assert "Big &lt;wave&gt;" in html and "Ball Knowledge: 9/10" in html and "Says hello &amp; more" in html
    assert ">Wave<" not in html                       # the gesture name is never shown


def test_nothing_is_shown_under_the_meme_until_the_owner_writes_it(lib, tmp_path):
    lib.update("wave", image=picture(tmp_path / "a.png"), gesture_name="Wave")
    html = ui.meme_card("wave", lib.load(), None, lib)
    assert '<img class="meme-img"' in html and 'class="owner"' not in html
    assert "not set" not in html and ">Wave<" not in html and ">wave<" not in html


def test_a_held_gesture_shows_its_meme_and_meter(lib, tmp_path):
    import predictor as pr
    lib.update("wave", image=picture(tmp_path / "a.png"), gesture_name="Wave", ball_knowledge_level="9/10")
    html = _live(lib, pr.Steady("wave", 0.88, 6, 7))
    assert '<img class="meme-img"' in html and "Confidence <b>88%</b>" in html
    assert "Ball Knowledge: 9/10" in html                 # the owner's own text, once written


# --- memes as small pictures ----------------------------------------------------------

def test_an_image_removed_after_its_check_is_shown_as_missing_not_an_error(lib, tmp_path, monkeypatch):
    """The Memes page in another tab replaces the image with another file type: the dashboard
    checked the old file, then the save removed it before the dashboard read it. That used to
    stop the Meme panel with FileNotFoundError."""
    import predictor as pr
    lib.update("wave", image=picture(tmp_path / "a.jpeg"), gesture_name="Wave")
    real = lib.image_problem

    def checked_then_removed(record):
        problem = real(record)
        lib.image_file(record).unlink(missing_ok=True)       # the other tab's save lands here
        return problem
    monkeypatch.setattr(lib, "image_problem", checked_then_removed)
    html = _live(lib, pr.Steady("wave", 0.9, 5, 7))
    assert "<b>Image missing</b>" in html and "<img" not in html
    assert ui.meme_thumb("wave", lib.load(), lib) == "Wave"   # the thumbnail's usual fallback


def test_a_meme_thumbnail_is_a_small_picture(lib, tmp_path):
    lib.update("wave", image=picture(tmp_path / "a.png", size=(800, 600)), gesture_name="Wave")
    html = ui.meme_thumb("wave", lib.load(), lib)
    assert html.startswith('<img class="thumb" src="data:image/jpeg;base64,')
    from base64 import b64decode
    from io import BytesIO
    data = b64decode(html.split("base64,")[1].split('"')[0])
    assert max(Image.open(BytesIO(data)).size) <= 120


def test_a_gesture_without_a_picture_falls_back_to_its_name(lib):
    assert ui.meme_thumb("wave", {}, lib) == "wave"
    assert ui.meme_thumb("<b>", {}, lib) == "&lt;b&gt;"


def test_recent_detections_show_memes_not_names(lib, tmp_path):
    import time
    import predictor as pr
    lib.update("wave", image=picture(tmp_path / "a.png"), gesture_name="Wave")
    html = ui.history_card((pr.HistoryEntry(time.time(), "wave", 0.9),), 1, True, lib.load(), lib)
    assert '<img class="thumb"' in html and ">Wave<" not in html and ">Meme</th>" in html


# --- importing a folder's image -------------------------------------------------------

def test_a_folder_with_one_image_sets_the_gestures_meme(lib, tmp_path):
    folder = tmp_path / "First meme"
    picture(folder / "images.jpeg")
    notes = iv.register_memes(iv.find_meme_images([str(folder)]), lib)
    assert notes == []
    r = lib.load()["first_meme"]
    assert r.gesture_name == "First meme" and r.image_path == "assets/memes/first_meme.jpeg"


def test_importing_again_keeps_what_the_user_wrote(lib, tmp_path):
    folder = tmp_path / "First meme"
    picture(folder / "images.jpeg")
    iv.register_memes(iv.find_meme_images([str(folder)]), lib)
    lib.update("first_meme", gesture_name="Facepalm", ball_knowledge_level="7/10")
    iv.register_memes(iv.find_meme_images([str(folder)]), lib)
    r = lib.load()["first_meme"]
    assert (r.gesture_name, r.ball_knowledge_level) == ("Facepalm", "7/10")


def test_several_images_are_not_guessed_between(lib, tmp_path):
    folder = tmp_path / "wave"
    picture(folder / "a.png")
    picture(folder / "b.png")
    notes = iv.register_memes(iv.find_meme_images([str(folder)]), lib)
    assert "has 2 images" in notes[0] and lib.load() == {}


def test_dry_run_and_bad_images_write_nothing(lib, tmp_path):
    folder = tmp_path / "wave"
    picture(folder / "a.png")
    assert iv.register_memes(iv.find_meme_images([str(folder)]), lib, dry_run=True) == []
    assert not lib.file.exists()
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "x.jpg").write_bytes(b"nope")
    notes = iv.register_memes(iv.find_meme_images([str(bad)]), lib)
    assert "not set" in notes[0] and not lib.file.exists()
