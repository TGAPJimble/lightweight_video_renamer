"""Find media files in a single folder (non-recursive).

A run is either "video" mode or "image" mode and never a mix: each mode only ever
returns files whose extension belongs to its own set, and the sets are disjoint.
"""
import re
from pathlib import Path

MODE_VIDEO = "video"
MODE_IMAGE = "image"

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg",
    ".mpeg", ".m2ts", ".mts", ".ts", ".3gp", ".ogv", ".vob", ".divx", ".asf",
    ".f4v", ".mxf", ".rm", ".rmvb",
}

# Images mpv decodes itself (animated GIF / WebP / APNG loop).
DIRECT_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".jpe", ".jfif", ".png", ".apng", ".gif", ".webp", ".bmp",
    ".tif", ".tiff",
}
# Images converted through Pillow (+ pillow-heif) to a temporary file for mpv.
PILLOW_IMAGE_EXTENSIONS = {
    ".heic", ".heif", ".hif", ".avif", ".jp2", ".j2k", ".jpf", ".jpx", ".ico",
}
# Camera RAW (LibRaw via rawpy).
RAW_EXTENSIONS = {
    ".cr2", ".cr3", ".crw", ".nef", ".nrw", ".arw", ".srf", ".sr2", ".raf",
    ".orf", ".rw2", ".rwl", ".pef", ".dng", ".3fr", ".erf", ".kdc", ".mrw",
    ".mef", ".mos", ".x3f", ".iiq", ".srw", ".raw",
}
SVG_EXTENSIONS = {".svg", ".svgz"}

IMAGE_EXTENSIONS = (
    DIRECT_IMAGE_EXTENSIONS | PILLOW_IMAGE_EXTENSIONS | RAW_EXTENSIONS | SVG_EXTENSIONS
)

_EXTENSIONS = {MODE_VIDEO: VIDEO_EXTENSIONS, MODE_IMAGE: IMAGE_EXTENSIONS}


def _natural_key(name: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def _candidates(folder: Path):
    return (
        p for p in Path(folder).iterdir()
        if p.is_file() and not p.name.startswith(".")
    )


def scan_files(folder: Path, mode: str = MODE_VIDEO) -> list[Path]:
    """Top-level files of `folder` that belong to `mode`, naturally sorted."""
    exts = _EXTENSIONS[mode]
    files = [p for p in _candidates(folder) if p.suffix.lower() in exts]
    return sorted(files, key=lambda p: _natural_key(p.name))


def count_other_kind(folder: Path, mode: str) -> int:
    """How many top-level files belong to the *other* mode (for a helpful message)."""
    other = MODE_IMAGE if mode == MODE_VIDEO else MODE_VIDEO
    return len(scan_files(folder, other))


def scan_videos(folder: Path) -> list[Path]:
    return scan_files(folder, MODE_VIDEO)
