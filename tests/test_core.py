from pathlib import Path

from lightweight_video_renamer.actions import rename_file
from lightweight_video_renamer.sanitize import sanitize_stem
from lightweight_video_renamer.scanner import scan_videos


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
