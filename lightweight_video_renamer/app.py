"""Tk front-end: fullscreen libmpv video, translucent input bar, delete popup."""
import os
import sys
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox

if __package__:
    from .actions import rename_file, trash_file
    from .logger import SessionLog
    from .scanner import scan_videos
else:  # run directly: `python app.py`
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from lightweight_video_renamer.actions import rename_file, trash_file
    from lightweight_video_renamer.logger import SessionLog
    from lightweight_video_renamer.scanner import scan_videos

BAR_BG = "#2b2b2b"
BAR_ALPHA = 0.26          # backdrop opacity
TEXT_KEY = "#010101"      # colour-keyed transparent background for the text layer
FONT = ("Segoe UI", 35, "bold")   # input text (35pt, bold)
TEXT_START = 0.40         # input text starts at 40% of the screen width
BAR_PAD_LEFT = 50         # box edge sits this far left of the text; right edge mirrors it
TEXT_OUTLINE = 2          # black outline thickness (px) around the input text


def _load_mpv():
    """Import python-mpv, making sure the bundled mpv-2.dll can be found."""
    here = Path(__file__).resolve().parent
    for d in (here, here.parent):
        if (d / "mpv-2.dll").exists() and os.name == "nt":
            os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")
            os.add_dll_directory(str(d))
            break
    try:
        import mpv
    except OSError as e:
        sys.exit(
            "libmpv (mpv-2.dll / libmpv.so) was not found.\n"
            "Windows: run `python scripts/install_libmpv.py`.\n"
            "Linux: install libmpv (e.g. `apt install libmpv2`).\n"
            f"({e})"
        )
    return mpv


class OutlinedText:
    """Bold text with a black outline, drawn onto a shared colour-keyed canvas.
    Offers a Label-like `.config(text=...)`; each instance owns its own canvas tag."""

    _count = 0

    def __init__(self, canvas, font, fill, anchor, x, y):
        OutlinedText._count += 1
        self.tag = f"ot{OutlinedText._count}"
        self.canvas = canvas
        self.font = tkfont.Font(family=font[0], size=font[1], weight=font[2])
        self.fill, self.anchor, self.x, self.y = fill, anchor, x, y

    def config(self, text=""):
        c = self.canvas
        c.delete(self.tag)
        r = TEXT_OUTLINE
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if dx or dy:
                    c.create_text(self.x + dx, self.y + dy, text=text, fill="black",
                                  anchor=self.anchor, font=self.font, tags=self.tag)
        c.create_text(self.x, self.y, text=text, fill=self.fill,
                      anchor=self.anchor, font=self.font, tags=self.tag)


class App:
    def __init__(self, folder: Path):
        self.mpv_mod = _load_mpv()
        self.folder = folder
        self.files = scan_videos(folder)
        self.index = 0
        self.counts = {"RENAME": 0, "DELETE": 0, "SKIP": 0, "ERROR": 0}
        self.popup_open = False
        self.busy = False
        self.native_size = False
        self.log = SessionLog(folder)

        # Make sure the log file is never treated as a video
        self.root = tk.Tk()
        self.root.configure(bg="black")
        self.root.attributes("-fullscreen", True)
        self.root.title("Lightweight Video Renamer")
        self.root.update_idletasks()
        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()

        self.player = self.mpv_mod.MPV(
            wid=str(self.root.winfo_id()),
            loop="inf",
            osc=False,
            input_default_bindings=False,
            input_vo_keyboard=False,
            keep_open="no",
            idle="yes",
            log_handler=None,
        )

        # mpv's embedded child window doesn't deliver mouse events to us, so a
        # near-invisible full-screen Tk window sits above the video and catches clicks.
        self.catcher = tk.Toplevel(self.root)
        self.catcher.overrideredirect(True)
        self.catcher.attributes("-topmost", True)
        self.catcher.attributes("-alpha", 0.01)
        self.catcher.configure(bg="black", cursor="arrow")
        self.catcher.geometry(f"{self.sw}x{self.sh}+0+0")
        self.catcher.bind("<Button-1>", self.on_click)

        self._build_title()
        self._build_bar()
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.bind("<FocusIn>", lambda e: self.root.after(50, self._focus_entry))
        self.root.after(100, self.load_current)

    # ---- UI construction -------------------------------------------------
    def _overlay(self, w, h, x, y, alpha):
        t = tk.Toplevel(self.root)
        t.overrideredirect(True)
        t.attributes("-topmost", True)
        t.attributes("-alpha", alpha)
        t.configure(bg=BAR_BG)
        t.geometry(f"{w}x{h}+{x}+{y}")
        return t

    def _build_title(self):
        # Transparent-colour window: only the text is visible.
        self.title_win = tk.Toplevel(self.root)
        self.title_win.overrideredirect(True)
        self.title_win.attributes("-topmost", True)
        key = "#010101"
        self.title_win.configure(bg=key)
        try:
            self.title_win.attributes("-transparentcolor", key)  # Windows
        except tk.TclError:
            self.title_win.attributes("-alpha", 0.8)
        self.title_win.geometry(f"{self.sw}x90+0+10")
        self.title_canvas = tk.Canvas(
            self.title_win, bg=key, highlightthickness=0, bd=0, width=self.sw, height=90
        )
        self.title_canvas.pack()
        self.title_canvas.bind("<Button-1>", self.on_click)
        self.title_label = OutlinedText(
            self.title_canvas, (FONT[0], 27, "bold"), "white", "center", self.sw // 2, 45,
        )
        self.progress = OutlinedText(
            self.title_canvas, (FONT[0], 14, "bold"), "#d0d0d0", "e", self.sw - 24, 22,
        )

    def _build_bar(self):
        h = 130
        text_abs = int(self.sw * TEXT_START)
        x = text_abs - BAR_PAD_LEFT          # box starts just left of the text
        w = self.sw - 2 * x                  # ...and mirrors the left margin on the right
        y = self.sh - h - 60
        # Layer 1: faint dark backdrop (window-level alpha).
        self.backdrop = self._overlay(w, h, x, y, BAR_ALPHA)
        # Layer 2: text layer. Its background is colour-keyed to be fully transparent,
        # so the text stays crisp while the backdrop stays see-through.
        self.bar = tk.Toplevel(self.root)
        self.bar.overrideredirect(True)
        self.bar.attributes("-topmost", True)
        self.bar.configure(bg=TEXT_KEY)
        try:
            self.bar.attributes("-transparentcolor", TEXT_KEY)  # Windows
        except tk.TclError:
            self.bar.configure(bg=BAR_BG)  # no colour-key support: opaque fallback
        self.bar.geometry(f"{w}x{h}+{x}+{y}")
        bg = self.bar.cget("bg")
        self.text_x = BAR_PAD_LEFT
        self.text_w = w - BAR_PAD_LEFT - 30
        self.msg = tk.Label(self.bar, text="", fg="#ff9d9d", bg=bg,
                            font=("Segoe UI", 12), anchor="w")
        self.msg.place(x=self.text_x, y=8)
        # Hidden Entry owns focus and editing; the visible text is drawn on a canvas
        # so it can have a black outline (Tk labels/entries can't outline text).
        self.entry = tk.Entry(
            self.bar, font=FONT, bg=bg, fg=bg, insertbackground=bg,
            relief="flat", highlightthickness=0, borderwidth=0,
        )
        self.entry.place(x=0, y=0, width=2, height=2)
        self.canvas = tk.Canvas(self.bar, bg=bg, highlightthickness=0, bd=0)
        self.canvas.place(x=0, y=30, width=w, height=h - 30)
        self.canvas_h = h - 30
        self.font = tkfont.Font(family=FONT[0], size=FONT[1], weight="bold")
        self.cursor_on = True
        self._last_state = None
        self._redraw_pending = False
        self._build_text_items()
        self.entry.bind("<KeyPress>", lambda e: self.schedule_redraw())
        self.entry.bind("<KeyRelease>", lambda e: self.schedule_redraw())
        self.entry.bind("<ButtonRelease>", lambda e: self.schedule_redraw())
        self.entry.bind("<<Paste>>", lambda e: self.schedule_redraw())
        for w_ in (self.entry, self.bar, self.canvas):
            w_.bind("<Return>", self.on_enter)
            w_.bind("<KP_Enter>", self.on_enter)
            w_.bind("<Escape>", lambda e: self.quit())
            w_.bind("<Delete>", self.on_delete_key)
            w_.bind("<Alt-Return>", self.toggle_native_size)
            w_.bind("<Alt-KP_Enter>", self.toggle_native_size)
        self.canvas.bind("<Button-1>", self.on_click)
        self.backdrop.bind("<Button-1>", self.on_click)
        self.redraw_text()
        self._blink()

    def _build_text_items(self):
        """Create the outline/text/caret canvas items once; later only update them."""
        c, r = self.canvas, TEXT_OUTLINE
        self.outline_offsets = [
            (-r, 0), (r, 0), (0, -r), (0, r), (-r, -r), (-r, r), (r, -r), (r, r),
        ]
        self.outline_items = [
            c.create_text(0, 0, text="", fill="black", anchor="w", font=self.font)
            for _ in self.outline_offsets
        ]
        self.text_item = c.create_text(0, 0, text="", fill="white", anchor="w", font=self.font)
        self.caret_outline = c.create_line(
            0, 0, 0, 0, fill="black", width=TEXT_OUTLINE * 2 + 3)
        self.caret_item = c.create_line(0, 0, 0, 0, fill="white", width=3)
        self.line_h = self.font.metrics("linespace")

    def schedule_redraw(self):
        # Class bindings (the actual text edit) run after widget bindings, so defer.
        self.cursor_on = True
        if not self._redraw_pending:
            self._redraw_pending = True
            self.root.after_idle(self._do_redraw)

    def _do_redraw(self):
        self._redraw_pending = False
        self.redraw_text()

    def redraw_text(self):
        c = self.canvas
        text = self.entry.get()
        idx = self.entry.index("insert")
        state = (text, idx)
        if state != self._last_state:
            self._last_state = state
            caret = self.font.measure(text[:idx])
            shift = max(0, caret - self.text_w + 10)   # keep caret visible on long names
            y = self.canvas_h // 2
            x = self.text_x - shift
            for item, (dx, dy) in zip(self.outline_items, self.outline_offsets):
                c.coords(item, x + dx, y + dy)
                c.itemconfigure(item, text=text)
            c.coords(self.text_item, x, y)
            c.itemconfigure(self.text_item, text=text)
            cx = self.text_x + caret - shift
            top, bot = y - self.line_h // 2, y + self.line_h // 2
            c.coords(self.caret_outline, cx, top, cx, bot)
            c.coords(self.caret_item, cx, top, cx, bot)
        vis = "normal" if self.cursor_on else "hidden"
        c.itemconfigure(self.caret_outline, state=vis)
        c.itemconfigure(self.caret_item, state=vis)

    def _blink(self):
        self.cursor_on = not self.cursor_on
        self.redraw_text()
        self.root.after(530, self._blink)

    def toggle_native_size(self, _e=None):
        """Alt+Enter: show the video at its natural resolution, centered (videos larger
        than the screen are scaled down to fit). The app itself stays fullscreen."""
        self.native_size = not self.native_size
        self.player.video_unscaled = "downscale-big" if self.native_size else "no"
        return "break"

    def on_click(self, _e=None):
        """Left click anywhere toggles pause (not during delete popup / file operations)."""
        if not self.popup_open and not self.busy:
            self.player.pause = not self.player.pause
        self.root.after(10, self._focus_entry)  # keep typing focus on the hidden entry
        return "break"

    def _focus_entry(self):
        if not self.popup_open:
            self.backdrop.lift()
            self.bar.lift()
            self.entry.focus_force()

    # ---- playback --------------------------------------------------------
    def load_current(self):
        if self.index >= len(self.files):
            return self.finish()
        p = self.files[self.index]
        self.title_label.config(text=p.name)
        self.progress.config(text=f"{self.index + 1} / {len(self.files)}")
        self.entry.delete(0, "end")
        self.redraw_text()
        self.msg.config(text="")
        self.player.pause = False
        self.player.play(str(p))
        self.root.after(80, self._focus_entry)

    def release_current(self):
        """Make mpv let go of the file so it can be renamed/deleted."""
        self.player.command("stop")
        self.root.update()

    def advance(self):
        self.index += 1
        self.load_current()

    # ---- actions ---------------------------------------------------------
    def on_enter(self, _e=None):
        if self.busy or self.popup_open or self.index >= len(self.files):
            return "break"
        typed = self.entry.get().strip()
        src = self.files[self.index]
        if not typed:
            self.counts["SKIP"] += 1
            self.log.write("SKIP", src.name)
            self.advance()
            return "break"
        self.busy = True
        try:
            self.release_current()
            new, note = rename_file(src, typed)
            if new is None:
                self.msg.config(text="That name isn't usable - try again")
                self.player.play(str(src))
                return "break"
            if note == "unchanged":
                self.counts["SKIP"] += 1
                self.log.write("SKIP", f"{src.name}\tunchanged")
            else:
                self.counts["RENAME"] += 1
                self.log.write("RENAME", f"{src.name}\t->\t{new.name}\t{note}")
            self.advance()
        except Exception as ex:  # noqa: BLE001
            self.counts["ERROR"] += 1
            self.log.write("ERROR", f"{src.name}\t{ex!r}")
            self.msg.config(text=f"Rename failed: {ex}")
            self.player.play(str(src))
        finally:
            self.busy = False
        return "break"

    def on_delete_key(self, _e=None):
        # Delete key acts as the popup trigger (user request), not text editing.
        if self.busy or self.popup_open or self.index >= len(self.files):
            return "break"
        self.open_delete_popup()
        return "break"

    def open_delete_popup(self):
        self.popup_open = True
        self.player.pause = True
        src = self.files[self.index]
        w, h = int(self.sw * 0.5), 190
        x, y = (self.sw - w) // 2, (self.sh - h) // 2
        pop = self._overlay(w, h, x, y, 0.92)
        self.popup = pop
        tk.Frame(pop, bg="#d9534f", height=6).pack(fill="x")
        tk.Label(pop, text="Move to Recycle Bin?", fg="white", bg=BAR_BG,
                 font=("Segoe UI", 22, "bold")).pack(pady=(18, 6))
        tk.Label(pop, text=src.name, fg="#dddddd", bg=BAR_BG, font=("Segoe UI", 14),
                 wraplength=w - 40).pack()
        tk.Label(pop, text="Enter = delete      Esc = cancel", fg="#aaaaaa", bg=BAR_BG,
                 font=("Segoe UI", 12)).pack(pady=(14, 0))
        pop.bind("<Return>", self.confirm_delete)
        pop.bind("<KP_Enter>", self.confirm_delete)
        pop.bind("<Escape>", self.cancel_delete)
        pop.lift()
        pop.focus_force()

    def cancel_delete(self, _e=None):
        self.popup.destroy()
        self.popup_open = False
        self.player.pause = False
        self.root.after(30, self._focus_entry)
        return "break"

    def confirm_delete(self, _e=None):
        src = self.files[self.index]
        self.popup.destroy()
        self.popup_open = False
        self.busy = True
        try:
            self.release_current()
            trash_file(src)
            self.counts["DELETE"] += 1
            self.log.write("DELETE", f"{src.name}\t(recycle bin)")
            self.advance()
        except Exception as ex:  # noqa: BLE001
            self.counts["ERROR"] += 1
            self.log.write("ERROR", f"{src.name}\tdelete: {ex!r}")
            self.msg.config(text=f"Delete failed: {ex}")
            self.player.pause = False
            self.player.play(str(src))
        finally:
            self.busy = False
        return "break"

    # ---- lifecycle -------------------------------------------------------
    def finish(self):
        self.entry.config(state="disabled")
        self.title_label.config(text="All done - press Esc to exit")
        self.progress.config(text="")
        self.player.command("stop")

    def quit(self):
        summary = " ".join(f"{k.lower()}={v}" for k, v in self.counts.items())
        try:
            self.log.close(summary)
        finally:
            try:
                self.player.terminate()
            finally:
                self.root.destroy()

    def run(self):
        if not self.files:
            self.log.close("no video files")
            messagebox.showinfo("Lightweight Video Renamer", "No video files found in that folder.")
            self.player.terminate()
            self.root.destroy()
            return
        self.root.mainloop()


def _enable_dpi_awareness():
    """Windows: make the process DPI-aware so 'native size' video is 1 video pixel per
    screen pixel instead of being stretched by display scaling."""
    if os.name != "nt":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor
    except Exception:  # noqa: BLE001
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:  # noqa: BLE001
            pass


def main():
    _enable_dpi_awareness()
    if len(sys.argv) > 1:
        folder = Path(sys.argv[1])
    else:
        picker = tk.Tk()
        picker.withdraw()
        chosen = filedialog.askdirectory(title="Select a folder of videos")
        picker.destroy()
        if not chosen:
            return
        folder = Path(chosen)
    if not folder.is_dir():
        sys.exit(f"Not a folder: {folder}")
    App(folder).run()


if __name__ == "__main__":
    main()
