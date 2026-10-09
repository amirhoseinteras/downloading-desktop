import os
import sys
import json
import threading
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yt_dlp

APP_NAME = "Downloading"
APP_VERSION = "3.1"
BG = "#0b1020"
CARD = "#141b2d"
FIELD = "#202a42"
TEXT = "#f6f8fc"
MUTED = "#9ca9c3"
ACCENT = "#6f8cff"
GREEN = "#35d08a"
RED = "#ff6b7a"


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def default_download_dir():
    path = os.path.join(os.path.expanduser("~"), "Downloads", "Downloading")
    os.makedirs(path, exist_ok=True)
    return path


def ffmpeg_path():
    path = os.path.join(app_dir(), "ffmpeg.exe")
    return path if os.path.exists(path) else None


def node_runtime_path():
    found = shutil.which("node")
    if found:
        return found
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    candidate = os.path.join(program_files, "nodejs", "node.exe")
    return candidate if os.path.exists(candidate) else None


def youtube_compat_options():
    opts = {"remote_components": ["ejs:github"]}
    node = node_runtime_path()
    if node:
        opts["js_runtimes"] = {"node": {"path": node}}
    return opts


def human_size(value):
    if not value:
        return "—"
    value = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{value:.0f} {unit}"
        value /= 1024


class DownloadingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("500x515")
        self.overrideredirect(True)
        self.resizable(False, False)
        self.configure(bg=BG)
        ico = os.path.join(app_dir(), "Downloading.ico")
        if os.path.exists(ico):
            try:
                self.iconbitmap(ico)
            except Exception:
                pass

        self.url = tk.StringVar()
        self.mode = tk.StringVar(value="video")
        self.quality = tk.StringVar(value="Best")
        self.save_dir = tk.StringVar(value=default_download_dir())
        self.status = tk.StringVar(value="Ready")
        self.size_text = tk.StringVar(value="Estimated size: —")
        self.progress = tk.DoubleVar(value=0)
        self.metadata = None
        self.meta_job = None
        self.manual_browser = None
        self.history = self.load_history()
        self.build_ui()
        self.url.trace_add("write", self.schedule_metadata)

    def build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TProgressbar", troughcolor=FIELD, background=ACCENT, borderwidth=0)
        style.configure("TCombobox", fieldbackground=FIELD, background=FIELD,
                        foreground=TEXT, arrowcolor=TEXT, borderwidth=0)
        style.map("TCombobox", fieldbackground=[("readonly", FIELD)],
                  foreground=[("readonly", TEXT)])

        self.build_titlebar()
        shell = tk.Frame(self, bg=BG)
        shell.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        card = tk.Frame(shell, bg=CARD, highlightthickness=1, highlightbackground="#24304a")
        card.pack(fill="both", expand=True, pady=(8, 0))

        tk.Label(card, text="Paste link", font=("Segoe UI Semibold", 9),
                 fg=TEXT, bg=CARD).pack(anchor="w", padx=14, pady=(9, 3))
        link_row = tk.Frame(card, bg=CARD)
        link_row.pack(fill="x", padx=14)
        self.link_entry = tk.Entry(link_row, textvariable=self.url, font=("Segoe UI", 9),
                                   bg=FIELD, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0)
        self.link_entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.link_entry.bind("<Return>", lambda _e: self.start_metadata_fetch())
        tk.Button(link_row, text="Paste", command=self.paste_clipboard,
                  bg=ACCENT, fg="white", activebackground="#806cff",
                  activeforeground="white", relief="flat", bd=0,
                  font=("Segoe UI Semibold", 9), padx=12, pady=5,
                  cursor="hand2").pack(side="left", padx=(8, 0))

        options = tk.Frame(card, bg=CARD)
        options.pack(fill="x", padx=14, pady=(9, 0))
        left = tk.Frame(options, bg=CARD)
        left.pack(side="left", fill="x", expand=True)
        right = tk.Frame(options, bg=CARD)
        right.pack(side="right")
        tk.Label(left, text="Format", font=("Segoe UI Semibold", 8),
                 fg=MUTED, bg=CARD).pack(anchor="w")
        mode_row = tk.Frame(left, bg=CARD)
        mode_row.pack(anchor="w", pady=(1, 0))
        tk.Radiobutton(mode_row, text="Video", variable=self.mode, value="video",
                       command=self.refresh_mode, bg=CARD, fg=TEXT, selectcolor=FIELD,
                       activebackground=CARD, activeforeground=TEXT,
                       font=("Segoe UI", 9)).pack(side="left")
        tk.Radiobutton(mode_row, text="Audio", variable=self.mode, value="audio",
                       command=self.refresh_mode, bg=CARD, fg=TEXT, selectcolor=FIELD,
                       activebackground=CARD, activeforeground=TEXT,
                       font=("Segoe UI", 9)).pack(side="left", padx=(10, 0))

        self.quality_label = tk.Label(right, text="Video quality",
                                      font=("Segoe UI Semibold", 8), fg=MUTED, bg=CARD)
        self.quality_label.pack(anchor="w")
        self.quality_box = ttk.Combobox(right, textvariable=self.quality,
                                        values=["Best", "1080p", "720p", "480p"],
                                        state="readonly", width=16)
        self.quality_box.pack(pady=(3, 0))
        self.quality_box.bind("<<ComboboxSelected>>", lambda _e: self.update_estimate())

        estimate_row = tk.Frame(card, bg=CARD)
        estimate_row.pack(fill="x", padx=14, pady=(5, 0))
        tk.Label(estimate_row, textvariable=self.size_text, font=("Segoe UI", 8),
                 fg="#b8c4da", bg=CARD).pack(side="right")

        save_wrap = tk.Frame(card, bg=CARD)
        save_wrap.pack(fill="x", padx=14, pady=(7, 0))
        tk.Label(save_wrap, text="Save to", font=("Segoe UI Semibold", 8),
                 fg=MUTED, bg=CARD).pack(anchor="w")
        save_row = tk.Frame(save_wrap, bg=CARD)
        save_row.pack(fill="x", pady=(3, 0))
        tk.Entry(save_row, textvariable=self.save_dir, font=("Segoe UI", 8),
                 bg=FIELD, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0).pack(
                 side="left", fill="x", expand=True, ipady=4)
        tk.Button(save_row, text="Browse", command=self.choose_folder,
                  bg="#273450", fg=TEXT, activebackground="#334463",
                  activeforeground=TEXT, relief="flat", bd=0,
                  font=("Segoe UI", 8), padx=9, pady=4, cursor="hand2").pack(
                  side="left", padx=(8, 0))

        progress_row = tk.Frame(card, bg=CARD)
        progress_row.pack(fill="x", padx=14, pady=(8, 2))
        self.progress_bar = ttk.Progressbar(progress_row, variable=self.progress, maximum=100)
        self.progress_bar.pack(side="left", fill="x", expand=True)
        self.status_icon_label = tk.Label(progress_row, text="", width=2,
                                          font=("Segoe UI Symbol", 11, "bold"),
                                          fg=MUTED, bg=CARD)
        self.status_icon_label.pack(side="right", padx=(6, 0))
        tk.Label(card, textvariable=self.status, font=("Segoe UI", 8),
                 fg=MUTED, bg=CARD, anchor="w").pack(fill="x", padx=14)

        actions = tk.Frame(card, bg=CARD)
        actions.pack(fill="x", padx=14, pady=(6, 7))
        self.download_btn = tk.Button(actions, text="Download", command=self.start_download,
                                      bg=GREEN, fg="#07170f", activebackground="#2fc27f",
                                      relief="flat", bd=0, font=("Segoe UI Semibold", 9),
                                      width=14, pady=5, cursor="hand2")
        self.download_btn.pack(side="left")
        tk.Button(actions, text="Open folder", command=self.open_folder,
                  bg="#273450", fg=TEXT, activebackground="#334463",
                  activeforeground=TEXT, relief="flat", bd=0,
                  font=("Segoe UI", 8), width=11, pady=5, cursor="hand2").pack(
                  side="left", padx=(7, 0))
        tk.Label(actions, text="Default: Video • Best", font=("Segoe UI", 7),
                 fg=MUTED, bg=CARD).pack(side="right")

        self.build_history_ui(card)
        self.refresh_mode(initial=True)

    def build_titlebar(self):
        bar = tk.Frame(self, bg=BG, height=62, bd=0, highlightthickness=0)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        logo = os.path.join(app_dir(), "Downloading_header_logo.png")
        if os.path.exists(logo):
            self._title_logo = tk.PhotoImage(file=logo)
            tk.Label(bar, image=self._title_logo, bg=BG, bd=0).place(x=12, y=4, width=54, height=54)

        tk.Label(bar, text=APP_NAME, font=("Segoe UI Semibold", 14),
                 fg=TEXT, bg=BG).place(x=76, y=12)
        tk.Label(bar, text=f"v{APP_VERSION}", font=("Segoe UI", 8),
                 fg=MUTED, bg=BG).place(x=78, y=37)

        self.min_btn = tk.Button(bar, text="−", command=self.minimize_window,
                                 bg=FIELD, fg="#cbd5e8", activebackground="#2b3656",
                                 activeforeground="white", relief="flat", bd=0,
                                 font=("Segoe UI Semibold", 13), cursor="hand2")
        self.min_btn.place(relx=1.0, x=-88, y=14, width=34, height=30, anchor="ne")
        self.close_btn = tk.Button(bar, text="×", command=self.destroy,
                                   bg=FIELD, fg="#cbd5e8", activebackground="#5a2941",
                                   activeforeground="white", relief="flat", bd=0,
                                   font=("Segoe UI Semibold", 13), cursor="hand2")
        self.close_btn.place(relx=1.0, x=-46, y=14, width=34, height=30, anchor="ne")
        self.min_btn.bind("<Enter>", lambda _e: self.min_btn.config(bg="#2b3656"))
        self.min_btn.bind("<Leave>", lambda _e: self.min_btn.config(bg=FIELD))
        self.close_btn.bind("<Enter>", lambda _e: self.close_btn.config(bg="#5a2941", fg="#ffdbe6"))
        self.close_btn.bind("<Leave>", lambda _e: self.close_btn.config(bg=FIELD, fg="#cbd5e8"))

        self.bind_all("<ButtonPress-1>", self.start_move, add="+")
        self.bind_all("<B1-Motion>", self.do_move, add="+")
        self.bind("<Map>", self.restore_borderless)

    def start_move(self, event):
        if event.widget.winfo_class() in {"Entry", "Button", "TCombobox", "Radiobutton", "TEntry"}:
            self._drag_origin = None
            return
        self._drag_origin = (event.x_root, event.y_root, self.winfo_x(), self.winfo_y())

    def do_move(self, event):
        if not getattr(self, "_drag_origin", None):
            return
        x0, y0, wx, wy = self._drag_origin
        self.geometry(f"+{wx + event.x_root - x0}+{wy + event.y_root - y0}")

    def minimize_window(self):
        self.overrideredirect(False)
        self.iconify()

    def restore_borderless(self, _event=None):
        if self.state() == "normal":
            self.after(20, lambda: self.overrideredirect(True))

    def refresh_mode(self, initial=False):
        if self.mode.get() == "video":
            self.quality_label.config(text="Video quality")
            self.quality_box.config(values=["Best", "1080p", "720p", "480p"])
            if not initial or self.quality.get() not in ("Best", "1080p", "720p", "480p"):
                self.quality.set("Best")
        else:
            self.quality_label.config(text="Audio quality")
            self.quality_box.config(values=["MP3 320", "Best (Original)"])
            if not initial or self.quality.get() not in ("MP3 320", "Best (Original)"):
                self.quality.set("MP3 320")
        self.update_estimate()

    def paste_clipboard(self):
        try:
            self.url.set(self.clipboard_get().strip())
        except tk.TclError:
            pass

    def schedule_metadata(self, *_args):
        if self.meta_job:
            try:
                self.after_cancel(self.meta_job)
            except Exception:
                pass
        self.metadata = None
        self.size_text.set("Estimated size: —")
        url = self.url.get().strip()
        if url.startswith("http"):
            self.meta_job = self.after(700, self.start_metadata_fetch)

    def start_metadata_fetch(self):
        url = self.url.get().strip()
        if not url.startswith("http"):
            return
        self.meta_job = None
        self.size_text.set("Estimated size: checking…")
        threading.Thread(target=self.metadata_worker, args=(url,), daemon=True).start()

    def choose_folder(self):
        path = filedialog.askdirectory(initialdir=self.save_dir.get())
        if path:
            self.save_dir.set(path)

    def open_folder(self):
        os.makedirs(self.save_dir.get(), exist_ok=True)
        os.startfile(self.save_dir.get())

    def history_path(self):
        return os.path.join(default_download_dir(), ".downloading_history.json")

    def load_history(self):
        try:
            with open(self.history_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def save_history(self):
        try:
            with open(self.history_path(), "w", encoding="utf-8") as f:
                json.dump(self.history[:3], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_history(self, item):
        self.history = [x for x in self.history if x.get("url") != item.get("url")]
        self.history.insert(0, item)
        self.history = self.history[:3]
        self.save_history()
        self.after(0, self.render_history)

    def build_history_ui(self, parent):
        tk.Frame(parent, bg="#26324d", height=1).pack(fill="x", padx=14, pady=(0, 4))
        head = tk.Frame(parent, bg=CARD)
        head.pack(fill="x", padx=14)
        tk.Label(head, text="Recent downloads", font=("Segoe UI Semibold", 8),
                 fg=TEXT, bg=CARD).pack(side="left")
        tk.Label(head, text="Last 3", font=("Segoe UI", 7),
                 fg=MUTED, bg=CARD).pack(side="right")
        self.history_box = tk.Frame(parent, bg=CARD)
        self.history_box.pack(fill="x", padx=14, pady=(2, 4))
        self.render_history()

    def render_history(self):
        if not hasattr(self, "history_box"):
            return
        for child in self.history_box.winfo_children():
            child.destroy()
        if not self.history:
            tk.Label(self.history_box, text="No downloads yet", font=("Segoe UI", 8),
                     fg=MUTED, bg=CARD).pack(anchor="w", pady=3)
            return
        for item in self.history[:3]:
            row = tk.Frame(self.history_box, bg="#182238", height=29)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)
            info = tk.Frame(row, bg="#182238")
            info.pack(side="left", fill="both", expand=True, padx=6, pady=1)
            title = (item.get("title") or "Untitled").strip()
            if len(title) > 34:
                title = title[:31] + "..."
            title_label = tk.Label(info, text=title, font=("Segoe UI Semibold", 8),
                                   fg=TEXT, bg="#182238", anchor="w")
            title_label.pack(fill="x")
            url = item.get("url") or ""
            short = url if len(url) <= 42 else url[:39] + "..."
            url_label = tk.Label(info, text=short, font=("Segoe UI", 6),
                                 fg=MUTED, bg="#182238", anchor="w")
            url_label.pack(fill="x")
            ok = item.get("status") == "Downloaded"
            status_label = tk.Label(row, text="✓" if ok else "✕",
                                    font=("Segoe UI Symbol", 11, "bold"),
                                    fg=GREEN if ok else RED, bg="#182238")
            status_label.pack(side="right", padx=(3, 7))
            tk.Button(row, text="Retry", command=lambda u=url: self.retry_download(u),
                      bg="#273450", fg=TEXT, activebackground="#334463",
                      activeforeground=TEXT, relief="flat", bd=0,
                      font=("Segoe UI", 7), padx=5, pady=2,
                      cursor="hand2").pack(side="right", padx=3)
            if ok:
                for widget in (row, info, title_label, url_label, status_label):
                    widget.config(cursor="hand2")
                    widget.bind("<Button-1>", lambda _e, current=item: self.open_history_item(current))

    def retry_download(self, url):
        self.url.set(url)
        self.start_download()

    def open_history_item(self, item):
        path = self.resolve_history_file(item)
        if path:
            item["file_path"] = path
            self.save_history()
            try:
                os.startfile(path)
            except Exception as exc:
                messagebox.showerror(APP_NAME, str(exc))

    def resolve_history_file(self, item):
        path = item.get("file_path") or ""
        if path and os.path.exists(path):
            return path
        folder = self.save_dir.get() or default_download_dir()
        media_id = item.get("id") or ""
        try:
            files = [os.path.join(folder, n) for n in os.listdir(folder)]
            files = [p for p in files if os.path.isfile(p) and not p.endswith((".part", ".ytdl"))]
            if media_id:
                matches = [p for p in files if f"[{media_id}]" in os.path.basename(p)]
                if matches:
                    return max(matches, key=os.path.getmtime)
        except Exception:
            pass
        return ""

    def set_status_icon(self, state):
        if state == "ok":
            self.status_icon_label.config(text="✓", fg=GREEN)
        elif state == "error":
            self.status_icon_label.config(text="✕", fg=RED)
        else:
            self.status_icon_label.config(text="", fg=MUTED)

    def format_selector(self):
        if self.mode.get() == "audio":
            return "bestaudio/best"
        q = self.quality.get()
        if q == "1080p":
            return "bestvideo*[height<=1080]+bestaudio/best[height<=1080]"
        if q == "720p":
            return "bestvideo*[height<=720]+bestaudio/best[height<=720]"
        if q == "480p":
            return "bestvideo*[height<=480]+bestaudio/best[height<=480]"
        return "bestvideo*+bestaudio/best"

    def browser_candidates(self):
        home = os.path.expanduser("~")
        appdata = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))
        local = os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
        checks = [
            ("firefox", os.path.join(appdata, "Mozilla", "Firefox", "Profiles")),
            ("edge", os.path.join(local, "Microsoft", "Edge", "User Data")),
            ("chrome", os.path.join(local, "Google", "Chrome", "User Data")),
            ("brave", os.path.join(local, "BraveSoftware", "Brave-Browser", "User Data")),
            ("vivaldi", os.path.join(local, "Vivaldi", "User Data")),
            ("chromium", os.path.join(local, "Chromium", "User Data")),
            ("opera", os.path.join(appdata, "Opera Software", "Opera Stable")),
            ("opera", os.path.join(appdata, "Opera Software", "Opera GX Stable")),
        ]
        found = []
        for name, path in checks:
            if not os.path.exists(path):
                continue
            candidate = (name, path) if name == "opera" else name
            if candidate not in found:
                found.append(candidate)
        return found

    def browser_label(self, browser):
        name = browser[0] if isinstance(browser, tuple) else browser
        profile = browser[1] if isinstance(browser, tuple) and len(browser) > 1 else ""
        if name == "opera" and "GX" in profile:
            return "Opera GX"
        return name.title()

    def choose_browser_for_auth(self):
        candidates = self.browser_candidates()
        if not candidates:
            messagebox.showerror(APP_NAME, "This download needs login, but no supported browser profile was found.")
            return None
        win = tk.Toplevel(self)
        win.title("Choose login browser")
        win.configure(bg=CARD)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        tk.Label(win, text="This link needs login. Choose a browser manually:", bg=CARD, fg=TEXT,
                 font=("Segoe UI Semibold", 9)).pack(padx=16, pady=(14, 8))
        choice = tk.StringVar(value="")
        for i, browser in enumerate(candidates):
            tk.Radiobutton(win, text=self.browser_label(browser), variable=choice, value=str(i),
                           bg=CARD, fg=TEXT, selectcolor=FIELD, activebackground=CARD,
                           activeforeground=TEXT, font=("Segoe UI", 9)).pack(anchor="w", padx=18)
        result = {"browser": None}
        def use_selected():
            if choice.get():
                result["browser"] = candidates[int(choice.get())]
                win.destroy()
        tk.Button(win, text="Use selected browser", command=use_selected, bg=ACCENT, fg="white",
                  relief="flat", bd=0, font=("Segoe UI Semibold", 9), padx=12, pady=5,
                  cursor="hand2").pack(pady=14)
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        self.wait_window(win)
        return result["browser"]

    def needs_auth(self, error):
        text = str(error).lower()
        keys = (
            "login required", "sign in", "sign-in", "private", "authentication",
            "cookies", "logged in", "log in", "login to", "followers only",
            "members-only", "members only", "requires authentication",
        )
        return any(k in text for k in keys)

    def metadata_options(self, browser=None):
        opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
        }
        opts.update(youtube_compat_options())
        if browser:
            opts["cookiesfrombrowser"] = browser if isinstance(browser, tuple) else (browser,)
        return opts

    def metadata_worker(self, url):
        info = None
        try:
            with yt_dlp.YoutubeDL(self.metadata_options()) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception:
            pass
        if self.url.get().strip() != url:
            return
        self.metadata = info if isinstance(info, dict) else None
        self.after(0, self.update_estimate)

    def format_bytes(self, fmt, duration):
        if not isinstance(fmt, dict):
            return 0
        size = fmt.get("filesize") or fmt.get("filesize_approx") or 0
        if size:
            return float(size)
        rate = fmt.get("tbr") or fmt.get("abr") or fmt.get("vbr") or 0
        if rate and duration:
            return float(rate) * 1000 / 8 * float(duration)
        return 0

    def best_audio_format(self, formats):
        audio = [f for f in formats if f.get("acodec") not in (None, "none")
                 and f.get("vcodec") in (None, "none")]
        if not audio:
            audio = [f for f in formats if f.get("acodec") not in (None, "none")]
        return max(audio, key=lambda f: (f.get("abr") or 0, f.get("tbr") or 0,
                                         f.get("filesize") or f.get("filesize_approx") or 0),
                   default=None)

    def video_estimate_bytes(self, formats, duration):
        limit = None
        if self.quality.get().endswith("p"):
            try:
                limit = int(self.quality.get()[:-1])
            except Exception:
                limit = None
        videos = [f for f in formats if f.get("vcodec") not in (None, "none")]
        if limit:
            limited = [f for f in videos if not f.get("height") or f.get("height") <= limit]
            if limited:
                videos = limited
        best_video = max(videos,
                         key=lambda f: (f.get("height") or 0, f.get("fps") or 0,
                                        f.get("tbr") or f.get("vbr") or 0),
                         default=None)
        total = self.format_bytes(best_video, duration)
        if best_video and best_video.get("acodec") in (None, "none"):
            total += self.format_bytes(self.best_audio_format(formats), duration)
        return total

    def update_estimate(self):
        info = self.metadata
        if not isinstance(info, dict):
            self.size_text.set("Estimated size: —")
            return
        duration = info.get("duration") or 0
        formats = info.get("formats") or []
        total = 0
        if self.mode.get() == "audio":
            if self.quality.get() == "MP3 320" and duration:
                total = float(duration) * 320000 / 8
            else:
                total = self.format_bytes(self.best_audio_format(formats), duration)
        else:
            total = self.video_estimate_bytes(formats, duration)
        if total:
            self.size_text.set(f"Estimated size: ≈ {human_size(total)}")
        else:
            self.size_text.set("Estimated size: unavailable")

    def start_download(self):
        url = self.url.get().strip()
        if not url:
            messagebox.showwarning(APP_NAME, "Paste a link first.")
            return
        os.makedirs(self.save_dir.get(), exist_ok=True)
        self.download_btn.config(state="disabled")
        self.progress.set(0)
        self.status.set("Preparing…")
        self.set_status_icon("")
        threading.Thread(target=self.download_worker, args=(url,), daemon=True).start()

    def progress_hook(self, data):
        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            done = data.get("downloaded_bytes") or 0
            percent = (done * 100 / total) if total else 0
            speed = data.get("speed") or 0
            speed_mb = speed / (1024 * 1024) if speed else 0
            self.after(0, lambda p=percent: self.progress.set(p))
            self.after(0, lambda p=percent, s=speed_mb:
                       self.status.set(f"Downloading… {p:.1f}%  •  {s:.1f} MB/s"))
        elif data.get("status") == "finished":
            self.after(0, lambda: self.status.set("Finishing file…"))

    def build_options(self, browser=None):
        opts = {
            "outtmpl": os.path.join(self.save_dir.get(), "%(title).180B [%(id)s].%(ext)s"),
            "noplaylist": True,
            "progress_hooks": [self.progress_hook],
            "ffmpeg_location": ffmpeg_path(),
            "windowsfilenames": True,
            "quiet": True,
            "no_warnings": True,
            "format": self.format_selector(),
        }
        opts.update(youtube_compat_options())
        if browser:
            opts["cookiesfrombrowser"] = browser if isinstance(browser, tuple) else (browser,)
        if self.mode.get() == "video":
            opts["merge_output_format"] = "mp4"
        elif self.quality.get() == "MP3 320":
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }]
        return opts

    def find_output_file(self, info):
        media_id = (info or {}).get("id") or ""
        folder = self.save_dir.get() or default_download_dir()
        try:
            files = [os.path.join(folder, n) for n in os.listdir(folder)]
            files = [p for p in files if os.path.isfile(p) and not p.endswith((".part", ".ytdl"))]
            if media_id:
                matches = [p for p in files if f"[{media_id}]" in os.path.basename(p)]
                if matches:
                    return max(matches, key=os.path.getmtime)
            return max(files, key=os.path.getmtime) if files else ""
        except Exception:
            return ""

    def attempt_download(self, url, browser=None):
        with yt_dlp.YoutubeDL(self.build_options(browser)) as ydl:
            return ydl.extract_info(url, download=True)

    def download_worker(self, url):
        info = None
        try:
            try:
                self.after(0, lambda: self.status.set("Downloading…"))
                info = self.attempt_download(url)
            except Exception as exc:
                if not self.needs_auth(exc):
                    raise
                selected = {"browser": None}
                ready = threading.Event()
                def ask_browser():
                    selected["browser"] = self.choose_browser_for_auth()
                    ready.set()
                self.after(0, ask_browser)
                ready.wait()
                if not selected["browser"]:
                    raise exc
                browser = selected["browser"]
                self.after(0, lambda b=browser:
                           self.status.set(f"Using {self.browser_label(b)} login…"))
                info = self.attempt_download(url, browser)
            title = info.get("title") if isinstance(info, dict) else "Download"
            media_id = info.get("id") if isinstance(info, dict) else ""
            output_file = self.find_output_file(info if isinstance(info, dict) else {})
            self.after(0, lambda: self.progress.set(100))
            self.after(0, lambda: self.status.set("Downloaded successfully"))
            self.after(0, lambda: self.set_status_icon("ok"))
            self.add_history({
                "title": title or "Download",
                "url": url,
                "status": "Downloaded",
                "id": media_id or "",
                "file_path": output_file,
            })
        except Exception as exc:
            error_text = str(exc)
            self.add_history({"title": "Download", "url": url, "status": "Failed"})
            self.after(0, lambda: self.status.set("Download failed"))
            self.after(0, lambda: self.set_status_icon("error"))
            if self.needs_auth(error_text):
                error_text = "Could not access this private/login-only content with the available browser sessions."
            self.after(0, lambda e=error_text: messagebox.showerror(APP_NAME, e))
        finally:
            self.after(0, lambda: self.download_btn.config(state="normal"))


if __name__ == "__main__":
    DownloadingApp().mainloop()
