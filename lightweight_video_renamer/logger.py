"""Timestamped session log written into the chosen folder."""
from datetime import datetime
from pathlib import Path


class SessionLog:
    def __init__(self, folder: Path, mode: str = "video"):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = Path(folder) / f"lightweight_video_renamer_{stamp}.log"
        n = 1
        while self.path.exists():  # extremely unlikely; keep names unique
            self.path = Path(folder) / f"lightweight_video_renamer_{stamp}_{n}.log"
            n += 1
        self._f = open(self.path, "w", encoding="utf-8")
        self.write("START", f"folder={folder}\tmode={mode}")

    def write(self, action: str, detail: str = "") -> None:
        ts = datetime.now().isoformat(timespec="seconds")
        self._f.write(f"{ts}\t{action}\t{detail}\n")
        self._f.flush()

    def close(self, summary: str = "") -> None:
        self.write("END", summary)
        self._f.close()
