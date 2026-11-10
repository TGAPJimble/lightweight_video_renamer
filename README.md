# Lightweight Video Renamer

**Rename video files in seconds, without leaving the video.**

Lightweight Video Renamer is a small desktop tool for naming a pile of video files. Pick a folder and each video plays fullscreen on a loop. Type a new name into the translucent bar at the bottom, press Enter, and the file is renamed on disk. Then the next video starts. There are no file dialogs and no copying filenames around.

It is built for the case where you have dozens or hundreds of unnamed clips (camera dumps, screen recordings, downloads) and the only way to name them properly is to watch them.

## Features

- Fullscreen looping playback powered by [mpv](https://mpv.io) (libmpv), with broad codec and format support
- Names are made safe for Windows and Linux. Illegal characters become look-alikes (for example `:` becomes `：`), so what you typed is preserved
- Unicode input supported (accents, CJK, IME)
- Never overwrites: if the name is taken, ` (1)`, ` (2)` and so on is added
- Delete moves the file to the Recycle Bin / Trash, after a confirmation pop-up
- A timestamped log of every rename, skip and delete is written into the folder
- Native-size view: show the video at its natural resolution, centered

## Controls

| Key / action | What it does |
|---|---|
| Type + **Enter** | Rename the current video, then go to the next |
| **Enter** on an empty box | Skip the video |
| **Delete** | Pause and ask to move the file to the Recycle Bin. Enter confirms, Esc cancels |
| **Left click** | Pause / resume |
| **Alt+Enter** | Toggle native-size view (the app stays fullscreen; videos larger than the screen are scaled down) |
| **Esc** | Quit |

A log named `lightweight_video_renamer_YYYYMMDD_HHMMSS.log` is written into the folder you choose.

## Setup

Requires Python 3.9 or later.

```
pip install python-mpv send2trash
python scripts/install_libmpv.py     # Windows: downloads libmpv (mpv-2.dll) into lightweight_video_renamer/
python -m lightweight_video_renamer [folder]         # no folder = folder picker
```

On Linux, install libmpv with your package manager (for example `apt install libmpv2`) instead of running the script.

Run the tests with `pip install pytest` and then `pytest`.

## Disclaimer

> [!WARNING]
> **This is a vibe-coded application.** It was written with AI assistance using **Google Antigravity** and **Claude Sonnet 5.5**, with the author directing the design and testing it by hand rather than hand-writing and reviewing every line.
>
> Lightweight Video Renamer **renames and deletes files**. Deleted files go to the Recycle Bin / Trash, but renames are not automatically undoable (the log file records old and new names). **Try it on copies of your files first, and keep backups.** It is provided as-is, with no warranty. See [LICENSE](LICENSE).

## Third-party software

This project's own code is released under the [MIT License](LICENSE). It relies on the following projects, which are **not** included in this repository and have their own licenses:

| Project | License | Use |
|---|---|---|
| [mpv / libmpv](https://mpv.io) | GPL (build-dependent) | Video playback. Downloaded separately by `scripts/install_libmpv.py` from [shinchiro/mpv-winbuild-cmake](https://github.com/shinchiro/mpv-winbuild-cmake) |
| [python-mpv](https://github.com/jaseg/python-mpv) | GPLv2+ or LGPLv2.1+ | Python bindings for libmpv |
| [Send2Trash](https://github.com/arsenetar/send2trash) | BSD-3-Clause | Moving files to the Recycle Bin / Trash |
| Python / Tkinter | PSF License | Runtime and UI windows |
