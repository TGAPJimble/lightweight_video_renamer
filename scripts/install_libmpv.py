"""Download libmpv for Windows and place mpv-2.dll inside the lightweight_video_renamer package.

Usage:  python scripts/install_libmpv.py

Uses the shinchiro/mpv-winbuild-cmake GitHub releases ("mpv-dev" archive) and
the `tar` (bsdtar) that ships with Windows 10+ to unpack the .7z archive.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

API = "https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/latest"
DEST = Path(__file__).resolve().parent.parent / "lightweight_video_renamer"


def main() -> int:
    with urllib.request.urlopen(API) as r:
        release = json.load(r)
    pattern = re.compile(r"^mpv-dev-x86_64-(?!v3)\d.*\.7z$")
    asset = next((a for a in release["assets"] if pattern.match(a["name"])), None)
    if asset is None:
        print("Could not find an mpv-dev x86_64 asset in the latest release.")
        return 1

    tmp = Path(tempfile.mkdtemp())
    try:
        archive = tmp / asset["name"]
        print(f"Downloading {asset['name']} ...")
        urllib.request.urlretrieve(asset["browser_download_url"], archive)
        subprocess.run(["tar", "-xf", str(archive), "-C", str(tmp)], check=True)
        dll = next(tmp.rglob("libmpv-2.dll"), None) or next(tmp.rglob("mpv-2.dll"), None)
        if dll is None:
            print("No libmpv DLL found in the archive.")
            return 1
        DEST.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dll, DEST / "mpv-2.dll")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"Installed {DEST / 'mpv-2.dll'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
