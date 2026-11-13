# Lightweight Video Renamer

**Rename video and image files in seconds, without leaving the viewer.**

Lightweight Video Renamer is a small desktop tool for naming a pile of video or image files. Pick a folder and each file displays fullscreen (videos and animated images loop). Type a new name into the translucent bar at the bottom, press Enter, and the file is renamed on disk. Then the next file loads. There are no file dialogs and no copying filenames around.

It is built for the case where you have dozens or hundreds of unnamed clips or photos (camera dumps, screen recordings, downloads) and the only way to name them properly is to look at them.

## Features

- **Two dedicated modes (never mixed):** Run in **video mode** by default, or pass `--images` for **image & GIF mode**. Each mode strictly processes only its own file types and ignores the other.
- **Fullscreen playback & display:** Powered by [mpv](https://mpv.io) (libmpv) for fast GPU-accelerated rendering and broad codec/format support.
- **Background conversion & preloading:** Formats that `mpv` cannot display directly (HEIC/HEIF, AVIF, Camera RAW, SVG) are converted in a background thread to a temporary preview file and preloaded one file ahead while you type, while renames and deletes still apply directly to your original file.
- **Native-size view by default:** Videos and images start at their natural 1:1 pixel resolution, centered on a solid black background (scaling down only if larger than the screen). Press **Alt+Enter** at any time to toggle fit-to-screen.
- **Clean black backdrop for transparency:** Transparent PNGs, WebPs, GIFs, and SVGs render over a solid black background instead of a checkerboard.
- **Translucent overlay UI:** Outlined, high-contrast filename header at the top and a translucent input bar at the bottom.
- **In-place renaming:** Only the filename stem changes; the original file extension and its casing are always preserved.
- **Cross-platform safe names:** Illegal Windows/Linux characters are automatically replaced with Unicode look-alikes (for example `:` becomes `：`), preserving the information you typed.
- **Full Unicode input:** Supports accented characters, CJK, and IME input.
- **Collision-safe:** Never overwrites an existing file; appends ` (1)`, ` (2)`, etc. when a name is already taken.
- **Safe deletion:** Pressing **Delete** pauses playback and asks for confirmation before moving the file to the Recycle Bin / Trash.
- **Session logging:** Writes a timestamped log (`lightweight_video_renamer_YYYYMMDD_HHMMSS.log`) recording every rename, skip, delete, and error.
- **Non-recursive:** Only the top level of the chosen folder is processed; subfolders are ignored.

## Supported File Types

All extensions are matched case-insensitively. Video files and image files are never mixed in the same run.

### Video Mode (default)

| Category | Extensions |
|---|---|
| Common containers | `.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v` |
| MPEG / transport streams | `.mpg`, `.mpeg`, `.m2ts`, `.mts`, `.ts`, `.vob` |
| Other formats | `.3gp`, `.ogv`, `.divx`, `.asf`, `.f4v`, `.mxf`, `.rm`, `.rmvb` |

### Image Mode (`--images`)

| Category | Extensions | How it is displayed |
|---|---|---|
| Standard & animated images | `.jpg`, `.jpeg`, `.jpe`, `.jfif`, `.png`, `.apng`, `.gif`, `.webp`, `.bmp`, `.tif`, `.tiff` | Displayed directly by `mpv` (animated `.gif`, `.webp`, and `.apng` loop continuously) |
| HEIC / HEIF & modern formats | `.heic`, `.heif`, `.hif`, `.avif`, `.jp2`, `.j2k`, `.jpf`, `.jpx`, `.ico` | Decoded via `Pillow` + `pillow-heif` with EXIF orientation applied |
| Vector graphics | `.svg`, `.svgz` | Rasterized via `resvg-py` onto a black background at a fraction of screen dimensions (`60%` width × `80%` height box, preserving aspect ratio) |
| Camera RAW | `.cr2`, `.cr3`, `.crw`, `.nef`, `.nrw`, `.arw`, `.srf`, `.sr2`, `.raf`, `.orf`, `.rw2`, `.rwl`, `.pef`, `.dng`, `.3fr`, `.erf`, `.kdc`, `.mrw`, `.mef`, `.mos`, `.x3f`, `.iiq`, `.srw`, `.raw` | Decoded via `rawpy` (LibRaw): uses the embedded camera JPEG preview when ≥2000px on the long edge, or falls back to a half-size demosaic |

## Controls

| Key / action | What it does |
|---|---|
| Type + **Enter** | Rename the current file, then go to the next |
| **Enter** on an empty box | Skip the file |
| **Delete** | Pause and ask to move the file to the Recycle Bin. Enter confirms, Esc cancels |
| **Left click** | Pause / resume video playback or GIF/WebP/APNG animation |
| **Alt+Enter** | Toggle between native-size view (default) and fit-to-screen view |
| **Esc** | Quit |

A log named `lightweight_video_renamer_YYYYMMDD_HHMMSS.log` is written into the folder you choose.

## Setup

> [!NOTE]
> **Platform Support:** This application has only been tested on **Windows** and **Arch Linux**. Requires Python 3.9 or later.

### Arch Linux (Step-by-Step)

1. **Clone the repository and enter the project folder:**
   ```bash
   git clone <repo-url>
   cd lightweight_video_renamer
   ```

2. **Run the Arch Linux dependency setup script:**
   ```bash
   ./scripts/setup_arch.sh
   ```
   This script:
   - Checks for required system packages (`python`, `tk`, `mpv`, `libheif`, `libraw`) via `pacman` and installs any missing packages with `sudo pacman -S --needed`.
   - Creates a local Python virtual environment at `.venv/` (respecting Arch's PEP 668 externally-managed Python environment).
   - Installs `lightweight-video-renamer` in editable mode along with all Python dependencies (`python-mpv`, `send2trash`, `pillow`, `pillow-heif`, `rawpy`, `resvg-py`) and `pytest`.
   - Verifies that `libmpv`, `tkinter`, and all Python modules import cleanly.

3. **Activate the virtual environment and run the app:**
   ```bash
   source .venv/bin/activate
   lightweight-video-renamer [folder]            # Video mode (omit folder to open the folder picker)
   lightweight-video-renamer --images [folder]   # Image mode (omit folder to open the folder picker)
   ```
   *(Alternatively, run `.venv/bin/lightweight-video-renamer` directly without activating the virtual environment.)*

### Windows (Step-by-Step)

1. **Install Python 3.9+** (with `tkinter` included, which is enabled by default in the official Windows Python installer).

2. **Clone the repository and open a PowerShell terminal in the project folder:**
   ```powershell
   git clone <repo-url>
   cd lightweight_video_renamer
   ```

3. **Install the Python dependencies:**
   ```powershell
   pip install python-mpv send2trash pillow pillow-heif rawpy resvg-py
   ```

4. **Download `libmpv` (`mpv-2.dll`):**
   ```powershell
   python scripts/install_libmpv.py
   ```
   This fetches the latest `mpv-dev` release from [shinchiro/mpv-winbuild-cmake](https://github.com/shinchiro/mpv-winbuild-cmake) and places `mpv-2.dll` inside `lightweight_video_renamer/`.

5. **Run the app:**
   ```powershell
   python -m lightweight_video_renamer [folder]            # Video mode (omit folder to open the folder picker)
   python -m lightweight_video_renamer --images [folder]   # Image mode (omit folder to open the folder picker)
   ```

### Running Tests

- **Arch Linux:**
  ```bash
  .venv/bin/pytest
  ```
- **Windows:**
  ```powershell
  pip install pytest
  pytest
  ```

## Disclaimer

> [!WARNING]
> **This is a vibe-coded application.** It was written with AI assistance using **Google Antigravity** and **Claude Sonnet 5.5**, with the author directing the design and testing it by hand rather than hand-writing and reviewing every line. It may contain bugs and has not been audited.
>
> Lightweight Video Renamer **renames and deletes files**. Deleted files go to the Recycle Bin / Trash, but renames are not automatically undoable (the log file records old and new names). **Try it on copies of your files first, and keep backups.** It is provided as-is, with no warranty. See [LICENSE](LICENSE).

## Third-party software

This project's own code is released under the [MIT License](LICENSE). It relies on the following projects, which are **not** included in this repository and have their own licenses:

| Project | License | Use |
|---|---|---|
| [mpv / libmpv](https://mpv.io) | GPL (build-dependent) | Video and image display. Installed via `pacman` (`scripts/setup_arch.sh`) on Arch Linux, or downloaded separately by `scripts/install_libmpv.py` from [shinchiro/mpv-winbuild-cmake](https://github.com/shinchiro/mpv-winbuild-cmake) on Windows |
| [python-mpv](https://github.com/jaseg/python-mpv) | GPLv2+ or LGPLv2.1+ | Python bindings for libmpv |
| [Send2Trash](https://github.com/arsenetar/send2trash) | BSD-3-Clause | Moving files to the Recycle Bin / Trash |
| [Pillow](https://python-pillow.org) | MIT-CMU | Image decoding, EXIF orientation, and temporary preview encoding |
| [pillow-heif](https://github.com/bigcat88/pillow_heif) | BSD-3-Clause (wheels bundle LGPL libheif) | HEIC / HEIF decoding |
| [rawpy](https://github.com/letmaik/rawpy) | MIT (wheels bundle LGPL-2.1 / CDDL LibRaw) | Camera RAW preview extraction and demosaicing |
| [resvg-py](https://github.com/baseplate-admin/resvg-py) | MIT (wraps Apache-2.0 / MPL-2.0 resvg) | SVG / SVGZ rasterization |
| Python / Tkinter | PSF License | Runtime and UI windows |

libmpv is a GPL-licensed binary. If you redistribute it (for example inside a release zip), you take on the GPL's obligations for that binary. This repository deliberately does not include it.
