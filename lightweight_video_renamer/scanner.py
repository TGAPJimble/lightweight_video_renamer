"""Find video files in a single folder (non-recursive)."""
import re
from pathlib import Path

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg",
    ".mpeg", ".m2ts", ".mts", ".ts", ".3gp", ".ogv", ".vob", ".divx", ".asf",
    ".f4v", ".mxf", ".rm", ".rmvb",
}


def _natural_key(name: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def scan_videos(folder: Path) -> list[Path]:
    files = [
        p for p in Path(folder).iterdir()
        if p.is_file() and not p.name.startswith(".")
        and p.suffix.lower() in VIDEO_EXTENSIONS
    ]
    return sorted(files, key=lambda p: _natural_key(p.name))
