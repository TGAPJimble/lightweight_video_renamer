from pathlib import Path
from PIL import Image

from lightweight_video_renamer.actions import rename_file
from lightweight_video_renamer.converter import Converter, kind_of
from lightweight_video_renamer.sanitize import sanitize_stem
from lightweight_video_renamer.scanner import (
    IMAGE_EXTENSIONS,
    MODE_IMAGE,
    MODE_VIDEO,
    VIDEO_EXTENSIONS,
    count_other_kind,
    scan_files,
    scan_videos,
)


def test_lookalikes_preserve_info():
    out = sanitize_stem('a:b/c\\d|e?f*g"h<i>j')
    assert out == "a：b／c＼d｜e？f＊g＂h＜i＞j"
    for ch in ':/\\|?*"<>':
        assert ch not in out


def test_trailing_dots_spaces_and_whitespace():
    assert sanitize_stem("  hello   world. . ") == "hello world"


def test_reserved_and_empty():
    assert sanitize_stem("CON") == "CON_"
    assert sanitize_stem("  ... ") == ""


def test_non_ascii_and_length():
    s = sanitize_stem("é" * 300, ".mp4")
    assert len((s + ".mp4").encode()) <= 255
    assert sanitize_stem("日本語タイトル") == "日本語タイトル"


def test_scanner_non_recursive(tmp_path: Path):
    (tmp_path / "b10.MP4").write_bytes(b"x")
    (tmp_path / "b2.mkv").write_bytes(b"x")
    (tmp_path / "notes.txt").write_bytes(b"x")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.mp4").write_bytes(b"x")
    assert [p.name for p in scan_videos(tmp_path)] == ["b2.mkv", "b10.MP4"]


def test_video_and_image_modes_never_mix(tmp_path: Path):
    assert VIDEO_EXTENSIONS.isdisjoint(IMAGE_EXTENSIONS)
    for name in ("clip1.mp4", "clip2.MKV", "pic1.jpg", "anim.GIF", "shot.HEIC", "vec.svg", "raw.NEF"):
        (tmp_path / name).write_bytes(b"x")
    vids = [p.name for p in scan_files(tmp_path, MODE_VIDEO)]
    imgs = [p.name for p in scan_files(tmp_path, MODE_IMAGE)]
    assert vids == ["clip1.mp4", "clip2.MKV"]
    assert imgs == ["anim.GIF", "pic1.jpg", "raw.NEF", "shot.HEIC", "vec.svg"]
    assert count_other_kind(tmp_path, MODE_VIDEO) == 5
    assert count_other_kind(tmp_path, MODE_IMAGE) == 2


def test_converter_heic_and_svg(tmp_path: Path):
    assert kind_of(Path("a.jpg")) is None
    assert kind_of(Path("a.HEIC")) == "pillow"
    assert kind_of(Path("a.svg")) == "svg"
    assert kind_of(Path("a.NEF")) == "raw"

    svg = tmp_path / "icon.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">'
        '<rect width="200" height="100" fill="#2266cc"/></svg>',
        encoding="utf-8",
    )
    heic = tmp_path / "photo.heic"
    import pillow_heif
    pillow_heif.register_heif_opener()
    Image.new("RGB", (320, 240), (180, 40, 40)).save(heic)

    conv = Converter(screen_w=2000, screen_h=1200)
    try:
        out_svg = conv.request(svg).result(timeout=10)
        assert out_svg.suffix == ".png" and out_svg.exists()
        with Image.open(out_svg) as im:
            assert im.size == (1200, 600)  # 60% of 2000 screen_w, 2:1 aspect preserved

        out_heic = conv.request(heic).result(timeout=10)
        assert out_heic.suffix == ".jpg" and out_heic.exists()
        with Image.open(out_heic) as im:
            assert im.size == (320, 240)

        conv.release(svg)
        assert not out_svg.exists()
    finally:
        conv.cleanup()


def test_rename_keeps_extension_and_avoids_collision(tmp_path: Path):
    a = tmp_path / "a.MP4"
    b = tmp_path / "Holiday.mp4"
    a.write_bytes(b"1")
    b.write_bytes(b"2")
    new, note = rename_file(a, "holiday")
    assert new.name == "holiday (1).MP4"
    assert b.read_bytes() == b"2"
    assert "collision-suffix" in note


def test_rename_sanitizes(tmp_path: Path):
    a = tmp_path / "a.mp4"
    a.write_bytes(b"1")
    new, note = rename_file(a, "what? 12:30")
    assert new.name == "what？ 12：30.mp4"
    assert new.exists() and not a.exists()


def test_ass_escape():
    from lightweight_video_renamer.app import _ass_escape
    escaped = _ass_escape("clip {1} \\N test")
    assert "\\{" in escaped and "\\}" in escaped
    assert "\\h" in escaped
    assert "\\N" not in escaped
