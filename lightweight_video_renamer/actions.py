"""Rename / delete operations. Retries cover mpv releasing the file handle."""
import os
import time
from pathlib import Path

from send2trash import send2trash

from .sanitize import sanitize_stem


def _retry(fn, attempts=8, delay=0.06):
    for i in range(attempts):
        try:
            return fn()
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(delay)


def unique_target(src: Path, new_stem: str) -> Path:
    """Target path with the original extension, never overwriting another file."""
    ext = src.suffix
    candidate = src.with_name(new_stem + ext)
    if candidate.name == src.name:
        return candidate
    n = 1
    while any(
        e.name.lower() == candidate.name.lower() for e in src.parent.iterdir()
    ) and candidate.name != src.name:
        candidate = src.with_name(f"{new_stem} ({n}){ext}")
        n += 1
    return candidate


def rename_file(src: Path, typed: str) -> tuple[Path | None, str]:
    """Rename src using the typed stem. Returns (new_path or None if invalid, note)."""
    stem = sanitize_stem(typed, src.suffix)
    if not stem:
        return None, "invalid name"
    target = unique_target(src, stem)
    notes = []
    if stem != typed.strip():
        notes.append("sanitized")
    if target.stem != stem:
        notes.append("collision-suffix")
    if target.name == src.name:
        return src, "unchanged"
    _retry(lambda: os.rename(src, target))
    return target, ",".join(notes)


def trash_file(src: Path) -> None:
    _retry(lambda: send2trash(str(src)))
