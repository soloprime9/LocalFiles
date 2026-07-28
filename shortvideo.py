#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import subprocess
import threading
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
from tkinter.scrolledtext import ScrolledText

try:
    import yt_dlp
    import imageio_ffmpeg
except ImportError:
    print("Dependency Error: Run -> pip install yt-dlp imageio-ffmpeg")
    sys.exit(1)


# ───────────────────────────── Design tokens ─────────────────────────────
# A small, deliberate dark palette (no built-in ttk theme involved) so the
# look is fully custom and doesn't depend on the OS theme or any extra
# pip-installed theme pack. Teal = primary action / focus. Amber = the
# "auto mode" accent, echoing the orange/teal duo common in video-editing
# tools, which fits a clip-cutting app.
COLORS = {
    "bg":          "#10131A",   # app background
    "surface":     "#1A2029",   # input wells / log console
    "surface_hi":  "#212934",   # hovered / lighter surface
    "border":      "#272F3B",   # hairline borders
    "text":        "#E8ECF3",   # primary text
    "text_dim":    "#8089A0",   # secondary / hint text
    "accent":      "#2DD4BF",   # teal - primary
    "accent_hover":"#22B6A4",
    "accent_ink":  "#06231F",   # text-on-accent
    "amber":       "#FFA75C",   # secondary accent (auto-mode / highlights)
    "danger":      "#FF6B6B",
    "success":     "#4ADE80",
    "warning":     "#FBBF24",
    "info":        "#67B7F0",
}


def _set_dpi_awareness():
    """Windows renders Tk windows blurry on HiDPI/scaled displays unless the
    process tells Windows it's DPI-aware (otherwise Windows bitmap-stretches
    the whole window). No-op on macOS/Linux. Must run before tk.Tk()."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _sync_tk_scaling(root):
    """After declaring DPI awareness, nudge Tk's internal scaling to match
    the real display DPI so fonts/widgets stay correctly sized instead of
    shrinking. No-op on macOS/Linux."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        ctypes.windll.user32.ReleaseDC(0, hdc)
        if dpi:
            root.tk.call('tk', 'scaling', dpi / 72.0)
    except Exception:
        pass


def fmt_duration(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"


class FastShortsPipelineGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ultra-Fast Multi-Shorts Cutter (No Local Download)")
        self.root.geometry("840x700")
        self.root.minsize(720, 500)
        self.root.configure(bg=COLORS["bg"])

        self.shorts_dir = Path("shorts")
        self.shorts_dir.mkdir(exist_ok=True)

        self.video_duration = None  # seconds, filled after "Check Duration" or auto on build

        self._init_fonts()
        self.style = ttk.Style()
        self._init_style()

        self.create_scrollable_container()
        self.create_widgets()

    # ───────────────────────────── Theming ─────────────────────────────
    def _init_fonts(self):
        """Pick the best available font family on this system. Falls back
        gracefully so nothing breaks on machines without these fonts."""
        available = set(tkfont.families())

        def pick(candidates, fallback="TkDefaultFont"):
            for name in candidates:
                if name in available:
                    return name
            return fallback

        self.font_body = pick(["Segoe UI", "Helvetica Neue", "Helvetica", "Arial"])
        self.font_heading = pick(["Segoe UI Semibold", "Segoe UI", "Helvetica Neue", "Helvetica", "Arial"])
        self.font_mono = pick(["Cascadia Mono", "Consolas", "Menlo", "Courier New"])

    def _init_style(self):
        c = COLORS
        # 'clam' is the only built-in theme that allows full custom
        # recoloring (borders, focus rings, field colors). Native themes
        # like vista/xpnative render via the OS and ignore most colors.
        self.style.theme_use("clam")

        self.style.configure(".", background=c["bg"], foreground=c["text"],
                              font=(self.font_body, 10))

        self.style.configure("TFrame", background=c["bg"])
        self.style.configure("TLabel", background=c["bg"], foreground=c["text"])

        self.style.configure("Hint.TLabel", background=c["bg"], foreground=c["text_dim"],
                              font=(self.font_body, 9))
        self.style.configure("Header.TLabel", background=c["bg"], foreground=c["text"],
                              font=(self.font_heading, 16, "bold"))
        self.style.configure("Subheader.TLabel", background=c["bg"], foreground=c["text_dim"],
                              font=(self.font_body, 10))

        # Section group boxes
        self.style.configure("TLabelframe", background=c["bg"], borderwidth=1,
                              relief="solid", bordercolor=c["border"],
                              lightcolor=c["border"], darkcolor=c["border"])
        self.style.configure("TLabelframe.Label", background=c["bg"], foreground=c["accent"],
                              font=(self.font_heading, 10, "bold"))

        # Checkbutton
        self.style.configure("TCheckbutton", background=c["bg"], foreground=c["text"],
                              font=(self.font_body, 10), indicatorbackground=c["surface"],
                              indicatormargin=6)
        self.style.map("TCheckbutton",
                        background=[("active", c["bg"])],
                        foreground=[("active", c["accent"])],
                        indicatorbackground=[("selected", c["accent"]), ("active", c["surface_hi"])])

        # Entry
        self.style.configure("TEntry", fieldbackground=c["surface"], foreground=c["text"],
                              insertcolor=c["text"], bordercolor=c["border"],
                              lightcolor=c["border"], darkcolor=c["border"],
                              borderwidth=1, relief="flat", padding=6)
        self.style.map("TEntry",
                        bordercolor=[("focus", c["accent"])],
                        lightcolor=[("focus", c["accent"])],
                        darkcolor=[("focus", c["accent"])])

        # Spinbox
        self.style.configure("TSpinbox", fieldbackground=c["surface"], foreground=c["text"],
                              arrowcolor=c["text_dim"], bordercolor=c["border"],
                              lightcolor=c["border"], darkcolor=c["border"],
                              borderwidth=1, relief="flat", padding=5, insertcolor=c["text"])
        self.style.map("TSpinbox",
                        arrowcolor=[("active", c["accent"])],
                        bordercolor=[("focus", c["accent"])])

        # Combobox
        self.style.configure("TCombobox", fieldbackground=c["surface"], foreground=c["text"],
                              background=c["surface"], arrowcolor=c["text_dim"],
                              bordercolor=c["border"], lightcolor=c["border"],
                              darkcolor=c["border"], borderwidth=1, relief="flat", padding=5)
        self.style.map("TCombobox",
                        fieldbackground=[("readonly", c["surface"])],
                        foreground=[("readonly", c["text"])],
                        bordercolor=[("focus", c["accent"])],
                        arrowcolor=[("active", c["accent"])])
        # Combobox dropdown listbox isn't a ttk widget, style it via the option db
        self.root.option_add("*TCombobox*Listbox.background", c["surface"])
        self.root.option_add("*TCombobox*Listbox.foreground", c["text"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", c["accent"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", c["accent_ink"])
        self.root.option_add("*TCombobox*Listbox.font", (self.font_body, 10))

        # Buttons
        self.style.configure("TButton", background=c["surface"], foreground=c["text"],
                              borderwidth=0, focusthickness=0, padding=(14, 8),
                              font=(self.font_body, 10))
        self.style.map("TButton",
                        background=[("active", c["surface_hi"]), ("disabled", c["surface"])],
                        foreground=[("disabled", c["text_dim"])])

        # Primary call-to-action
        self.style.configure("Accent.TButton", background=c["accent"], foreground=c["accent_ink"],
                              borderwidth=0, padding=(18, 11), font=(self.font_heading, 11, "bold"))
        self.style.map("Accent.TButton",
                        background=[("active", c["accent_hover"]), ("disabled", c["border"])],
                        foreground=[("disabled", c["text_dim"])])

        # Secondary / outline button
        self.style.configure("Ghost.TButton", background=c["bg"], foreground=c["accent"],
                              borderwidth=1, relief="solid", bordercolor=c["accent"],
                              lightcolor=c["accent"], darkcolor=c["accent"],
                              padding=(16, 10), font=(self.font_body, 10, "bold"))
        self.style.map("Ghost.TButton",
                        background=[("active", c["surface"])],
                        bordercolor=[("active", c["accent_hover"])])

        # Small utility button (Check Duration)
        self.style.configure("Utility.TButton", background=c["surface"], foreground=c["text"],
                              borderwidth=1, relief="solid", bordercolor=c["border"],
                              lightcolor=c["border"], darkcolor=c["border"],
                              padding=(12, 8), font=(self.font_body, 10))
        self.style.map("Utility.TButton",
                        background=[("active", c["surface_hi"])],
                        bordercolor=[("active", c["accent"])])

        # Progress bar
        self.style.configure("Modern.Horizontal.TProgressbar", troughcolor=c["surface"],
                              background=c["accent"], bordercolor=c["surface"],
                              lightcolor=c["accent"], darkcolor=c["accent"], thickness=10)

        # Scrollbar
        self.style.configure("Vertical.TScrollbar", background=c["surface"],
                              troughcolor=c["bg"], bordercolor=c["bg"],
                              arrowcolor=c["text_dim"], relief="flat", gripcount=0)
        self.style.map("Vertical.TScrollbar", background=[("active", c["accent"])])

    # ───────────────────────── Scrollable wrapper ─────────────────────────
    def create_scrollable_container(self):
        outer = ttk.Frame(self.root)
        outer.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(outer, highlightthickness=0, bg=COLORS["bg"])
        vscroll = ttk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vscroll.set)

        vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scroll_frame = ttk.Frame(self.canvas, padding="22")
        self.scroll_frame_id = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        self.scroll_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse wheel scrolling (Windows / macOS / Linux)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.scroll_frame_id, width=event.width)

    def _on_mousewheel(self, event):
        if event.num == 4:        # Linux scroll up
            delta = -1
        elif event.num == 5:      # Linux scroll down
            delta = 1
        else:                      # Windows / macOS
            delta = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(delta, "units")

    # ───────────────────────────── Widgets ─────────────────────────────
    def create_widgets(self):
        main_frame = self.scroll_frame
        c = COLORS

        header_box = ttk.Frame(main_frame)
        header_box.pack(fill=tk.X, pady=(0, 18), anchor="w")
        header = ttk.Label(header_box, text="⚡ Multi-Shorts Cutter", style="Header.TLabel")
        header.pack(anchor="w")
        subheader = ttk.Label(
            header_box,
            text="Resolve the stream once, cut as many vertical clips as you need.",
            style="Subheader.TLabel"
        )
        subheader.pack(anchor="w", pady=(4, 0))

        # Section 1: Video Link
        source_frame = ttk.LabelFrame(main_frame, text="  1 · YouTube Source  ", padding="14")
        source_frame.pack(fill=tk.X, pady=6)

        url_row = ttk.Frame(source_frame)
        url_row.pack(fill=tk.X)

        self.url_entry = ttk.Entry(url_row, width=55)
        self.url_entry.pack(side=tk.LEFT, padx=(0, 10), expand=True, fill=tk.X)
        self.url_entry.insert(0, "https://www.youtube.com/watch?v=9fUYUItUgSk")

        self.check_btn = ttk.Button(url_row, text="🔍 Check Duration", style="Utility.TButton",
                                     cursor="hand2", command=self.start_check_duration_thread)
        self.check_btn.pack(side=tk.RIGHT)

        self.duration_label = ttk.Label(source_frame, text="Video duration: not checked yet",
                                         style="Hint.TLabel")
        self.duration_label.pack(anchor="w", pady=(10, 0))

        # Section 2: Clip generation mode
        config_frame = ttk.LabelFrame(
            main_frame,
            text="  2 · Clip Generation  ",
            padding="14"
        )
        config_frame.pack(fill=tk.X, pady=6)

        self.auto_mode_var = tk.BooleanVar(value=True)
        self.auto_check = ttk.Checkbutton(
            config_frame,
            text="Auto mode — detect full video duration and auto-generate shorts to cover the whole video",
            variable=self.auto_mode_var,
            command=self.toggle_mode
        )
        self.auto_check.pack(anchor="w")

        # Auto-mode settings row
        auto_row = ttk.Frame(config_frame)
        auto_row.pack(fill=tk.X, pady=(12, 0))

        ttk.Label(auto_row, text="Clip length (sec)").pack(side=tk.LEFT, padx=(0, 6))
        self.clip_len_spin = ttk.Spinbox(auto_row, from_=5, to=180, width=6)
        self.clip_len_spin.set(30)
        self.clip_len_spin.pack(side=tk.LEFT, padx=(0, 18))

        ttk.Label(auto_row, text="Gap between clips (sec)").pack(side=tk.LEFT, padx=(0, 6))
        self.gap_spin = ttk.Spinbox(auto_row, from_=0, to=600, width=6)
        self.gap_spin.set(0)
        self.gap_spin.pack(side=tk.LEFT, padx=(0, 18))

        ttk.Label(auto_row, text="Max clips (0 = no limit)").pack(side=tk.LEFT, padx=(0, 6))
        self.max_clips_spin = ttk.Spinbox(auto_row, from_=0, to=200, width=6)
        self.max_clips_spin.set(0)
        self.max_clips_spin.pack(side=tk.LEFT)

        auto_hint = ttk.Label(
            config_frame,
            text='Example: a 2-minute video with a 30s clip length auto-generates 4 shorts (0-30, 30-60, 60-90, 90-120).\nDuration is detected automatically when you click "Build" — no need to check it first.',
            style="Hint.TLabel", justify="left"
        )
        auto_hint.pack(anchor="w", pady=(12, 0))

        # Manual mode panel (hidden by default)
        self.manual_frame = ttk.LabelFrame(
            main_frame,
            text="  Manual Clips — one per line as  start-end  (seconds)  ",
            padding="14"
        )

        manual_hint = ttk.Label(
            self.manual_frame,
            text="Example:\n10-40\n75-100\n200-230",
            style="Hint.TLabel", justify="left"
        )
        manual_hint.pack(anchor="w", pady=(0, 8))

        self.ranges_text = tk.Text(
            self.manual_frame, height=5, font=(self.font_mono, 10),
            bg=c["surface"], fg=c["text"], insertbackground=c["accent"],
            selectbackground=c["border"], selectforeground=c["text"],
            relief="flat", highlightthickness=1, highlightbackground=c["border"],
            highlightcolor=c["accent"], padx=10, pady=8
        )
        self.ranges_text.pack(fill=tk.X)
        self.ranges_text.insert("1.0", "10-40\n75-100")

        # Quality / speed selector
        quality_row = ttk.Frame(main_frame)
        quality_row.pack(fill=tk.X, pady=(14, 0))
        ttk.Label(quality_row, text="Max Quality").pack(side=tk.LEFT, padx=(0, 6))
        self.quality_combo = ttk.Combobox(quality_row, values=["1080", "720", "480"], width=6, state="readonly")
        self.quality_combo.set("720")
        self.quality_combo.pack(side=tk.LEFT, padx=(0, 24))

        ttk.Label(quality_row, text="Encode Speed").pack(side=tk.LEFT, padx=(0, 6))
        self.speed_combo = ttk.Combobox(quality_row, values=["ultrafast", "veryfast", "fast"], width=10, state="readonly")
        self.speed_combo.set("ultrafast")
        self.speed_combo.pack(side=tk.LEFT)

        # Section 3: Log Monitor
        activity_frame = ttk.LabelFrame(main_frame, text="  3 · Live Pipeline Monitor (Step-by-Step)  ", padding="14")
        activity_frame.pack(fill=tk.BOTH, expand=True, pady=14)

        self.log_box = ScrolledText(
            activity_frame, height=12, font=(self.font_mono, 10),
            bg="#0D1117", fg="#C9D1D9", insertbackground=c["accent"],
            selectbackground=c["border"], selectforeground=c["text"],
            relief="flat", highlightthickness=1, highlightbackground=c["border"],
            highlightcolor=c["accent"], padx=10, pady=8
        )
        self.log_box.pack(fill=tk.BOTH, expand=True)
        try:
            # Cosmetic only — keeps the surrounding ScrolledText frame on-theme.
            self.log_box.frame.configure(bg=c["bg"])
            # ScrolledText's vertical scrollbar is a plain (non-ttk) tk.Scrollbar,
            # so our ttk style never reaches it — style it directly or it shows
            # up as a stark default-white bar against the dark console.
            self.log_box.vbar.configure(
                bg=c["surface"], activebackground=c["accent"],
                troughcolor=c["bg"], highlightthickness=0,
                bd=0, elementborderwidth=0, width=14
            )
        except Exception:
            pass

        # Tag colors used by log_message() to highlight log levels
        self.log_box.tag_configure("err", foreground=c["danger"])
        self.log_box.tag_configure("warn", foreground=c["warning"])
        self.log_box.tag_configure("ok", foreground=c["success"])
        self.log_box.tag_configure("info", foreground=c["info"])
        self.log_box.tag_configure("sys", foreground=c["text_dim"])
        self.log_box.tag_configure("step", foreground=c["accent"])
        self.log_box.tag_configure("clip", foreground=c["amber"])

        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, "[SYSTEM] Engine Ready. Input link + clip ranges, then press build.\n", "sys")
        self.log_box.config(state=tk.DISABLED)

        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", mode="determinate",
                                             style="Modern.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, pady=(6, 12))

        # Section 4: Action Row
        self.btn_frame = ttk.Frame(main_frame, padding="5")
        self.btn_frame.pack(fill=tk.X, pady=5)

        self.process_btn = ttk.Button(self.btn_frame, text="🚀 Build All Shorts Now", style="Accent.TButton",
                                       cursor="hand2", command=self.start_pipeline_thread)
        self.process_btn.pack(side=tk.LEFT, padx=(0, 8), expand=True, fill=tk.X)

        self.open_folder_btn = ttk.Button(self.btn_frame, text="📁 Open Shorts Folder", style="Ghost.TButton",
                                           cursor="hand2", command=self.open_shorts_folder)
        self.open_folder_btn.pack(side=tk.RIGHT, padx=(8, 0), expand=True, fill=tk.X)

    # ───────────────────────────── Mode toggling ─────────────────────────────
    def toggle_mode(self):
        if self.auto_mode_var.get():
            self.manual_frame.pack_forget()
        else:
            # Insert manual frame right after the config_frame (auto settings)
            self.manual_frame.pack(fill=tk.X, pady=5, after=self.auto_check.master)

    def compute_auto_ranges(self, total_duration):
        try:
            clip_len = int(self.clip_len_spin.get())
            gap = int(self.gap_spin.get())
            max_clips = int(self.max_clips_spin.get())
            if clip_len <= 0:
                raise ValueError
        except ValueError:
            raise ValueError("Clip length and gap must be valid non-negative numbers (clip length > 0).")

        total = int(total_duration)
        if total <= 0:
            raise ValueError("Video duration could not be determined.")

        step = clip_len + gap
        ranges = []
        start = 0
        while start + clip_len <= total:
            ranges.append((start, start + clip_len))
            start += step

        # If there's meaningful leftover (>= half a clip), add a final clip ending at total
        leftover = total - start
        if leftover >= clip_len / 2 and (not ranges or ranges[-1][1] < total):
            last_start = max(total - clip_len, ranges[-1][1] if ranges else 0)
            if last_start < total - 1:
                ranges.append((last_start, total))

        # If video is shorter than clip_len, just take the whole video as one clip
        if not ranges and total > 1:
            ranges.append((0, total))

        if max_clips > 0:
            ranges = ranges[:max_clips]

        if not ranges:
            raise ValueError("Could not generate any clips from this video's duration.")

        return ranges

    # ───────────────────────────── Helpers ─────────────────────────────
    def log_message(self, message):
        if not isinstance(message, str):
            message = str(message)
        # Strip characters that some Tk builds can't render
        message = message.encode('utf-8', errors='replace').decode('utf-8')

        # Pick a color tag based on log level / marker in the message.
        # Purely cosmetic — does not change what gets logged or how.
        tag = None
        upper = message.upper()
        if "[ERROR]" in upper or "❌" in message:
            tag = "err"
        elif "[WARNING]" in upper:
            tag = "warn"
        elif "[DONE]" in upper or "✅" in message:
            tag = "ok"
        elif "[SYSTEM]" in upper:
            tag = "sys"
        elif "[STEP" in upper:
            tag = "step"
        elif "[CLIP" in upper:
            tag = "clip"
        elif "[INFO]" in upper:
            tag = "info"

        self.log_box.config(state=tk.NORMAL)
        start_index = self.log_box.index(tk.END)
        self.log_box.insert(tk.END, f"-> {message}\n")
        if tag:
            self.log_box.tag_add(tag, start_index, self.log_box.index(tk.END))
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def open_shorts_folder(self):
        full_path = self.shorts_dir.resolve()
        if sys.platform == "win32":
            os.startfile(full_path)
        elif sys.platform == "darwin":
            subprocess.run(["open", full_path])
        else:
            subprocess.run(["xdg-open", full_path])

    def parse_ranges(self, raw_text):
        ranges = []
        for line_no, line in enumerate(raw_text.strip().splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            m = re.match(r'^(\d+)\s*-\s*(\d+)$', line)
            if not m:
                raise ValueError(f"Line {line_no} ('{line}') is not in 'start-end' format.")
            start, end = int(m.group(1)), int(m.group(2))
            if end <= start:
                raise ValueError(f"Line {line_no}: end ({end}) must be greater than start ({start}).")
            ranges.append((start, end))
        if not ranges:
            raise ValueError("No valid clip ranges found.")
        return ranges

    # ───────────────────────────── Duration check ─────────────────────────────
    def start_check_duration_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube link.")
            return
        self.check_btn.config(state=tk.DISABLED)
        self.duration_label.config(text="Video duration: checking...")
        threading.Thread(target=self.check_duration, args=(url,), daemon=True).start()

    def check_duration(self, url):
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True, 'noplaylist': True, 'skip_download': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            duration = info.get('duration')
            title = info.get('title', 'video')
            if duration:
                self.video_duration = duration
                self.duration_label.config(
                    text=f"Video duration: {fmt_duration(duration)}  ({duration}s)  —  \"{title[:60]}\""
                )
                self.log_message(f"[INFO] Duration detected: {fmt_duration(duration)} ({duration}s)")
            else:
                self.video_duration = None
                self.duration_label.config(text="Video duration: unavailable (live stream?)")
        except Exception as e:
            self.video_duration = None
            self.duration_label.config(text="Video duration: failed to fetch")
            self.log_message(f"[ERROR] Duration check failed: {str(e)}")
        finally:
            self.check_btn.config(state=tk.NORMAL)

    # ───────────────────────────── Pipeline ─────────────────────────────
    def start_pipeline_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube link.")
            return

        if not self.auto_mode_var.get():
            # Manual mode: validate ranges now
            try:
                ranges = self.parse_ranges(self.ranges_text.get("1.0", tk.END))
            except ValueError as e:
                messagebox.showerror("Invalid Clip Ranges", str(e))
                return
            self.process_btn.config(state=tk.DISABLED)
            self.progress_bar['value'] = 0
            self.progress_bar['maximum'] = len(ranges)
            threading.Thread(target=self.run_fast_pipeline, args=(url, ranges), daemon=True).start()
        else:
            # Auto mode: ranges computed inside run_fast_pipeline once duration is known
            self.process_btn.config(state=tk.DISABLED)
            self.progress_bar['value'] = 0
            self.progress_bar['maximum'] = 1
            threading.Thread(target=self.run_fast_pipeline, args=(url, None), daemon=True).start()

    def run_fast_pipeline(self, url, ranges):
        success_count = 0
        fail_count = 0
        try:
            max_height = self.quality_combo.get()
            preset = self.speed_combo.get()

            ffmpeg_exe_path = imageio_ffmpeg.get_ffmpeg_exe()
            self.log_message(f"[SYSTEM] Using FFmpeg binary: {Path(ffmpeg_exe_path).name}")
            clip_count_str = str(len(ranges)) if ranges is not None else "auto-detected"
            self.log_message(f"[STEP 1/2] Resolving direct stream URLs (resolved ONCE, reused for all {clip_count_str} clips)...")

            ydl_opts = {
                'format': f'bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={max_height}][ext=mp4]/best',
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                video_url = None
                audio_url = None

                if 'requested_formats' in info and info['requested_formats']:
                    for f in info['requested_formats']:
                        if f.get('vcodec') != 'none' and f.get('acodec') == 'none':
                            video_url = f['url']
                        elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                            audio_url = f['url']

                if not video_url:
                    video_url = info.get('url')
                if not audio_url:
                    audio_url = video_url

                video_title = info.get('title', 'video')
                safe_title = re.sub(r'[^\w\-]+', '_', video_title)[:40]

                duration_total = info.get('duration')
                if duration_total:
                    self.video_duration = duration_total
                    self.duration_label.config(text=f"Video duration: {fmt_duration(duration_total)} ({duration_total}s)")

            if not video_url:
                raise RuntimeError("Could not resolve a playable stream URL.")

            # Auto mode: compute ranges now that we know the full duration
            if ranges is None:
                if not self.video_duration:
                    raise RuntimeError("Could not determine video duration for auto mode.")
                ranges = self.compute_auto_ranges(self.video_duration)
                self.progress_bar['maximum'] = len(ranges)
                self.log_message(
                    f"[INFO] Auto mode: video is {fmt_duration(self.video_duration)} long. "
                    f"Generating {len(ranges)} short(s) of ~{self.clip_len_spin.get()}s each."
                )
                for i, (s, e) in enumerate(ranges, start=1):
                    self.log_message(f"   • Short {i}: {s}s -> {e}s ({e - s}s)")

            # Warn (but don't block) if any requested range exceeds video duration
            if self.video_duration:
                out_of_range = [r for r in ranges if r[1] > self.video_duration]
                if out_of_range:
                    self.log_message(
                        f"[WARNING] {len(out_of_range)} clip(s) exceed video length "
                        f"({fmt_duration(self.video_duration)}). They may be shorter than requested or fail."
                    )

            self.log_message("[STEP 1/2] Stream endpoints resolved successfully — reused for every clip.")
            self.log_message(f"[STEP 2/2] Cutting {len(ranges)} clip(s) @ {max_height}p, preset={preset}, vertical 9:16...")

            for idx, (start_time, end_time) in enumerate(ranges, start=1):
                duration = end_time - start_time
                output_file = self.shorts_dir / f"{safe_title}_short_{idx:02d}_{start_time}-{end_time}.mp4"

                self.log_message(f"[CLIP {idx}/{len(ranges)}] {start_time}s -> {end_time}s ({duration}s) — downloading only this segment...")

                # -ss before -i = fast seek via HTTP range requests, only pulls needed bytes.
                # ultrafast preset = minimal CPU time, saves the file almost instantly after download.
                if video_url == audio_url:
                    ffmpeg_cmd = [
                        ffmpeg_exe_path, "-y",
                        "-ss", str(start_time), "-i", video_url,
                        "-t", str(duration),
                        "-vf", "crop=ih*9/16:ih,scale=1080:1920",
                        "-c:v", "libx264", "-preset", preset, "-crf", "23",
                        "-c:a", "aac", "-b:a", "128k",
                        "-movflags", "+faststart",
                        str(output_file)
                    ]
                else:
                    ffmpeg_cmd = [
                        ffmpeg_exe_path, "-y",
                        "-ss", str(start_time), "-i", video_url,
                        "-ss", str(start_time), "-i", audio_url,
                        "-t", str(duration),
                        "-filter_complex", "[0:v]crop=ih*9/16:ih,scale=1080:1920[v]",
                        "-map", "[v]", "-map", "1:a",
                        "-c:v", "libx264", "-preset", preset, "-crf", "23",
                        "-c:a", "aac", "-b:a", "128k",
                        "-movflags", "+faststart",
                        str(output_file)
                    ]

                result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         encoding='utf-8', errors='replace')

                if output_file.exists() and output_file.stat().st_size > 1000:
                    self.log_message(f"[CLIP {idx}/{len(ranges)}] ✅ Saved: {output_file.name}")
                    success_count += 1
                else:
                    self.log_message(f"[CLIP {idx}/{len(ranges)}] ❌ Failed. FFmpeg output:\n" + result.stdout[-800:])
                    fail_count += 1

                self.progress_bar['value'] = idx
                self.root.update_idletasks()

            self.log_message(f"[DONE] {success_count} succeeded, {fail_count} failed. Saved in '{self.shorts_dir}/'.")
            if success_count:
                messagebox.showinfo(
                    "Pipeline Complete",
                    f"{success_count} short(s) created successfully"
                    + (f", {fail_count} failed" if fail_count else "")
                    + f".\nCheck the '{self.shorts_dir}' folder."
                )
            else:
                messagebox.showerror("Pipeline Failed", "No clips were created successfully. Check the log.")

        except Exception as e:
            self.log_message(f"[ERROR] Pipeline Failed: {str(e)}")
            messagebox.showerror("Pipeline Processing Error", f"Details:\n{str(e)}")
        finally:
            self.process_btn.config(state=tk.NORMAL)


if __name__ == '__main__':
    _set_dpi_awareness()
    root = tk.Tk()
    _sync_tk_scaling(root)
    app = FastShortsPipelineGUI(root)
    root.mainloop()