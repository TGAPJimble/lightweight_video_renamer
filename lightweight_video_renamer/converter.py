"""Convert image types mpv can't show (HEIC/HEIF, AVIF, RAW, SVG, ...) into a
temporary JPEG/PNG that mpv *can* show. The original file is never modified, and
all renaming/deleting still acts on the original.

Heavy libraries are imported lazily, so video mode never loads them.
"""
import gzip
import io
import itertools
import shutil
import tempfile
import threading
import xml.etree.ElementTree as ET
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from .scanner import (
    PILLOW_IMAGE_EXTENSIONS, RAW_EXTENSIONS, SVG_EXTENSIONS,
)

JPEG_QUALITY = 95
RAW_PREVIEW_MIN_EDGE = 2000     # use the embedded JPEG preview if its long edge >= this
SVG_BOX_W = 0.60                # SVGs are fitted into this fraction of the screen width...
SVG_BOX_H = 0.80                # ...and this fraction of the screen height
SVG_MAX_EDGE = 4096


def kind_of(path: Path):
    """'pillow' | 'raw' | 'svg' if the file needs converting, None if mpv can play it."""
    ext = path.suffix.lower()
    if ext in SVG_EXTENSIONS:
        return "svg"
    if ext in RAW_EXTENSIONS:
        return "raw"
    if ext in PILLOW_IMAGE_EXTENSIONS:
        return "pillow"
    return None


def check_dependencies() -> None:
    """Raise ImportError with a clear message if an image library is missing."""
    missing = []
    for mod, pkg in (("PIL", "pillow"), ("pillow_heif", "pillow-heif"),
                     ("rawpy", "rawpy"), ("resvg_py", "resvg-py")):
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        raise ImportError(
            "Image mode needs: " + ", ".join(missing)
            + "\nInstall with:  pip install " + " ".join(missing)
        )


_heif_registered = False
_heif_lock = threading.Lock()


def _register_heif():
    global _heif_registered
    with _heif_lock:
        if not _heif_registered:
            import pillow_heif
            pillow_heif.register_heif_opener()
            _heif_registered = True


def _save_pillow_image(im, dest_base: Path) -> Path:
    """Save as PNG when there is transparency, otherwise high-quality JPEG."""
    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    if has_alpha:
        out = dest_base.with_suffix(".png")
        im.convert("RGBA").save(out, compress_level=1)
    else:
        out = dest_base.with_suffix(".jpg")
        im.convert("RGB").save(out, quality=JPEG_QUALITY)
    return out


def _convert_pillow(src: Path, dest_base: Path) -> Path:
    from PIL import Image, ImageOps
    _register_heif()
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        im.load()
        return _save_pillow_image(im, dest_base)


def _convert_raw(src: Path, dest_base: Path) -> Path:
    import rawpy
    from PIL import Image
    with rawpy.imread(str(src)) as raw:
        try:
            thumb = raw.extract_thumb()
        except (rawpy.LibRawNoThumbnailError, rawpy.LibRawUnsupportedThumbnailError):
            thumb = None
        if thumb is not None and thumb.format == rawpy.ThumbFormat.JPEG:
            with Image.open(io.BytesIO(thumb.data)) as t:
                big_enough = max(t.size) >= RAW_PREVIEW_MIN_EDGE
            if big_enough:  # camera's own full-size preview: instant, EXIF orientation kept
                out = dest_base.with_suffix(".jpg")
                out.write_bytes(thumb.data)
                return out
        if thumb is not None and thumb.format == rawpy.ThumbFormat.BITMAP:
            im = Image.fromarray(thumb.data)
            if max(im.size) >= RAW_PREVIEW_MIN_EDGE:
                return _save_pillow_image(im, dest_base)
        # No usable preview: half-size demosaic with the camera white balance.
        rgb = raw.postprocess(half_size=True, use_camera_wb=True)
        return _save_pillow_image(Image.fromarray(rgb), dest_base)


def _svg_aspect(src: Path):
    """Width/height ratio from the SVG header, or None if it can't be determined."""
    try:
        opener = gzip.open if src.suffix.lower() == ".svgz" else open
        with opener(src, "rb") as f:
            root = next(ET.iterparse(f, events=("start",)))[1]
        def num(v):
            if not v or v.strip().endswith("%"):
                return None
            digits = "".join(ch for ch in v if ch.isdigit() or ch == ".")
            return float(digits) if digits else None
        w, h = num(root.get("width")), num(root.get("height"))
        if not (w and h) and root.get("viewBox"):
            parts = root.get("viewBox").replace(",", " ").split()
            if len(parts) == 4:
                w, h = float(parts[2]), float(parts[3])
        return w / h if (w and h) else None
    except Exception:  # noqa: BLE001
        return None


def _convert_svg(src: Path, dest_base: Path, screen_w: int, screen_h: int) -> Path:
    import resvg_py
    from PIL import Image
    aspect = _svg_aspect(src)
    if aspect is None:  # unusual header: render once at intrinsic size to learn it
        probe = bytes(resvg_py.svg_to_bytes(svg_path=str(src)))
        with Image.open(io.BytesIO(probe)) as im:
            aspect = im.size[0] / im.size[1]
    width = min(screen_w * SVG_BOX_W, screen_h * SVG_BOX_H * aspect, SVG_MAX_EDGE)
    width = max(1, int(width))
    png = bytes(resvg_py.svg_to_bytes(svg_path=str(src), width=width, background="#000000"))
    out = dest_base.with_suffix(".png")
    out.write_bytes(png)
    return out


class Converter:
    """Converts files on a single background thread; supports one-ahead preloading."""

    def __init__(self, screen_w: int, screen_h: int):
        self.screen_w, self.screen_h = screen_w, screen_h
        self.tmpdir = Path(tempfile.mkdtemp(prefix="lvr_"))
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="convert")
        self._futures: dict[Path, Future] = {}
        self._counter = itertools.count()
        self._lock = threading.Lock()

    def _convert(self, src: Path) -> Path:
        dest_base = self.tmpdir / f"img{next(self._counter)}"
        kind = kind_of(src)
        if kind == "svg":
            return _convert_svg(src, dest_base, self.screen_w, self.screen_h)
        if kind == "raw":
            return _convert_raw(src, dest_base)
        return _convert_pillow(src, dest_base)

    def request(self, src: Path) -> Future:
        """Start (or reuse) a conversion. Safe to call repeatedly for the same file."""
        with self._lock:
            fut = self._futures.get(src)
            if fut is None:
                fut = self._pool.submit(self._convert, src)
                self._futures[src] = fut
            return fut

    def release(self, src: Path) -> None:
        """Forget a file and delete its temp output (best effort)."""
        with self._lock:
            fut = self._futures.pop(src, None)
        if fut is not None and fut.done() and not fut.cancelled() and fut.exception() is None:
            try:
                fut.result().unlink()
            except OSError:
                pass  # still open in mpv; removed with the temp dir on exit

    def cleanup(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
        shutil.rmtree(self.tmpdir, ignore_errors=True)
