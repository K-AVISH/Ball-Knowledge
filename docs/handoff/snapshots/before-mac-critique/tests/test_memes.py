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


def test_title_falls_back_to_the_gesture_name_then_id():
    assert dm.MemeRecord("g", gesture_name="Name").title == "Name"
    assert dm.MemeRecord("g").title == "g"
    assert dm.MemeRecord("g", gesture_name="Name", meme_title="T").title == "T"


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


# --- the meme panel -----------------------------------------------------------------

def test_no_steady_gesture_shows_no_meme(lib):
    html = ui.meme_card(None, {}, None, lib)
    assert "No meme yet" in html and "<img" not in html
    assert f"{config.MIN_STABLE_FRAMES} of the last {config.SMOOTHING_WINDOW}" in html


def test_the_none_gesture_has_no_meme(lib):
    html = ui.meme_card(config.NONE_LABEL, {}, None, lib)
    assert "No gesture" in html and "<img" not in html


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
    assert 'alt="Meme: Big &lt;wave&gt;"' in html
    assert "Big &lt;wave&gt;" in html and "Ball Knowledge: 9/10" in html and "Says hello &amp; more" in html
    assert "The model only recognises the gesture" in html


def test_unset_rating_and_description_are_said_plainly(lib, tmp_path):
    lib.update("wave", image=picture(tmp_path / "a.png"))
    html = ui.meme_card("wave", lib.load(), None, lib)
    assert "Ball Knowledge rating not set" in html and "No description set" in html
    assert ">wave<" in html                                       # the title falls back to the id


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
