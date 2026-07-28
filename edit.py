#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
All-in-One Video Studio
========================
Tab 1 — "Shorts Cutter": unchanged from your original tool. Paste a YouTube
         link, it resolves the stream once and cuts as many vertical 9:16
         clips as you want (auto mode or manual start-end ranges).

Tab 2 — "Video Editor": a real one-click editor for ANY local video file.
         Tick the features you want, set their options, hit Apply, get a
         new exported file. Nothing here touches or replaces your original.

Editor features (Tab 2):
    🔇 Audio        — remove / replace / mix-in a voiceover (with volume
                       controls + start offset for the new track)
    📝 Text x2       — two independent text overlays, each with its own
                       font file, size, color, 9-point position grid or
                       custom %x/%y placement, start time + duration
    🖼  Logo/Watermark — image overlay, position, size %, opacity, timing
    ⭕ Shape          — circle or rectangle annotation at an x%/y% point,
                       outline or filled, color, thickness, timing
    🎬 Intro / Outro  — auto-generated text title-card OR your own clip,
                       prepended / appended to the main video
    👁  Live Preview  — grabs a real frame from your video and draws a
                       mock-up of every enabled feature on it, so you see
                       the layout before you commit to a full render

Requirements:
    pip install yt-dlp imageio-ffmpeg moviepy==1.0.3 pillow numpy

Scope / intent:
    This tool is for editing video you have the legal right to use — your
    own footage, properly licensed clips, royalty-free music, cleared
    voiceovers, your own logo, etc. It does not contain — and will not be
    extended to contain — any feature designed to defeat copyright
    detection or to repost someone else's content without permission.
"""

import os
import sys
import re
import subprocess
import threading
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser, font as tkfont
from tkinter.scrolledtext import ScrolledText

try:
    import yt_dlp
    import imageio_ffmpeg
except ImportError:
    print("Dependency Error: Run -> pip install yt-dlp imageio-ffmpeg moviepy==1.0.3 pillow numpy")
    sys.exit(1)

# Editor-tab dependencies are optional at import time so Tab 1 (the original
# cutter) keeps working even on a machine that hasn't installed them yet.
# Tab 2 just shows a clear "install this" message instead of crashing.
EDITOR_DEPS_OK = True
EDITOR_DEPS_ERROR = ""
try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    from moviepy.editor import (
        VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip,
        CompositeAudioClip, concatenate_videoclips, afx
    )
except ImportError as _e:
    EDITOR_DEPS_OK = False
    EDITOR_DEPS_ERROR = str(_e)


# ───────────────────────────── Design tokens ─────────────────────────────
COLORS = {
    "bg":          "#10131A",
    "surface":     "#1A2029",
    "surface_hi":  "#212934",
    "border":      "#272F3B",
    "text":        "#E8ECF3",
    "text_dim":    "#8089A0",
    "accent":      "#2DD4BF",
    "accent_hover":"#22B6A4",
    "accent_ink":  "#06231F",
    "amber":       "#FFA75C",
    "danger":      "#FF6B6B",
    "success":     "#4ADE80",
    "warning":     "#FBBF24",
    "info":        "#67B7F0",
}


def _set_dpi_awareness():
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
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
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


# ═══════════════════════════ Image / overlay helpers ═══════════════════════════
# Pure PIL functions used by BOTH the live preview and the final render, so
# what you see in the preview is exactly what you get in the exported file.

def hex_to_rgb(hex_str, default=(255, 255, 255)):
    try:
        h = hex_str.strip().lstrip('#')
        if len(h) == 6:
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        pass
    return default


def load_font(font_path, size):
    size = max(8, int(size))
    if font_path and Path(font_path).exists():
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10
    except Exception:
        return ImageFont.load_default()


POSITION_PRESETS = [
    "Top-Left", "Top-Center", "Top-Right",
    "Middle-Left", "Middle-Center", "Middle-Right",
    "Bottom-Left", "Bottom-Center", "Bottom-Right",
    "Custom",
]


def resolve_anchor_xy(preset, custom_x, custom_y, frame_w, frame_h, content_w, content_h, margin=24):
    if preset == "Custom":
        x = int(frame_w * custom_x / 100) - content_w // 2
        y = int(frame_h * custom_y / 100) - content_h // 2
        return max(0, min(x, max(0, frame_w - content_w))), max(0, min(y, max(0, frame_h - content_h)))
    presets = {
        "Top-Left":      (margin, margin),
        "Top-Center":    ((frame_w - content_w) // 2, margin),
        "Top-Right":     (frame_w - content_w - margin, margin),
        "Middle-Left":   (margin, (frame_h - content_h) // 2),
        "Middle-Center": ((frame_w - content_w) // 2, (frame_h - content_h) // 2),
        "Middle-Right":  (frame_w - content_w - margin, (frame_h - content_h) // 2),
        "Bottom-Left":   (margin, frame_h - content_h - margin),
        "Bottom-Center": ((frame_w - content_w) // 2, frame_h - content_h - margin),
        "Bottom-Right":  (frame_w - content_w - margin, frame_h - content_h - margin),
    }
    x, y = presets.get(preset, presets["Bottom-Center"])
    return max(0, x), max(0, y)


def render_text_image(frame_w, frame_h, text, font_path, size, color_hex, position,
                       custom_x, custom_y, box_bg=False):
    img = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = load_font(font_path, size)
    bbox = draw.multiline_textbbox((0, 0), text, font=font, align="center")
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = resolve_anchor_xy(position, custom_x, custom_y, frame_w, frame_h, tw, th)
    if box_bg:
        pad = 14
        draw.rectangle([x - pad, y - pad, x + tw + pad, y + th + pad], fill=(0, 0, 0, 140))
    color = hex_to_rgb(color_hex) + (255,)
    draw.multiline_text((x - bbox[0], y - bbox[1]), text, font=font, fill=color, align="center",
                         stroke_width=max(1, int(size) // 22), stroke_fill=(0, 0, 0, 200))
    return img


def render_logo_image(frame_w, frame_h, logo_path, position, size_pct, opacity, margin):
    logo = Image.open(logo_path).convert("RGBA")
    target_w = max(8, int(frame_w * size_pct / 100))
    ratio = target_w / logo.width
    target_h = max(8, int(logo.height * ratio))
    logo = logo.resize((target_w, target_h), Image.LANCZOS)
    if opacity < 100:
        alpha = logo.split()[3].point(lambda p: int(p * (opacity / 100.0)))
        logo.putalpha(alpha)
    img = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
    x, y = resolve_anchor_xy(position, 50, 50, frame_w, frame_h, target_w, target_h, margin=margin)
    img.paste(logo, (x, y), logo)
    return img


def render_shape_image(frame_w, frame_h, shape_type, x_pct, y_pct, size_pct, color_hex, thickness, filled):
    img = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = int(frame_w * x_pct / 100), int(frame_h * y_pct / 100)
    r = max(2, int(frame_w * size_pct / 100 / 2))
    color = hex_to_rgb(color_hex) + (255,)
    fill = color if filled else None
    width = max(1, int(thickness))
    if shape_type == "Circle":
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=width, fill=fill)
    else:
        draw.rectangle([cx - r, cy - r, cx + r, cy + r], outline=color, width=width, fill=fill)
    return img


def render_title_card(frame_w, frame_h, text, bg_hex):
    img = Image.new("RGB", (frame_w, frame_h), hex_to_rgb(bg_hex, (10, 12, 18)))
    draw = ImageDraw.Draw(img)
    font = load_font(None, max(24, frame_w // 14))
    bbox = draw.multiline_textbbox((0, 0), text or "", font=font, align="center")
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.multiline_text(((frame_w - tw) // 2 - bbox[0], (frame_h - th) // 2 - bbox[1]),
                         text or "", font=font, fill=(255, 255, 255), align="center")
    return img


def parse_duration_field(raw, total_available):
    """'' / 'full' / 'rest' -> rest of the clip. Otherwise a float seconds value."""
    raw = (raw or "").strip().lower()
    if raw in ("", "full", "rest"):
        return total_available
    try:
        return max(0.1, min(float(raw), total_available))
    except ValueError:
        return total_available


# ═══════════════════════════════ Main application ═══════════════════════════════
class AllInOneVideoStudio:
    def __init__(self, root):
        self.root = root
        self.root.title("All-in-One Video Studio — Shorts Cutter + Editor")
        self.root.geometry("1020x800")
        self.root.minsize(840, 580)
        self.root.configure(bg=COLORS["bg"])

        self.shorts_dir = Path("shorts")
        self.shorts_dir.mkdir(exist_ok=True)
        self.edited_dir = Path("edited")
        self.edited_dir.mkdir(exist_ok=True)

        self.video_duration = None  # seconds — Tab 1 cutter state

        self._init_fonts()
        self.style = ttk.Style()
        self._init_style()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        tab1 = ttk.Frame(self.notebook)
        tab2 = ttk.Frame(self.notebook)
        self.notebook.add(tab1, text="  ✂️  Shorts Cutter  ")
        self.notebook.add(tab2, text="  🎛️  Video Editor  ")

        self.canvas1, self.scroll_frame1 = self._make_scrollable(tab1)
        self.canvas2, self.scroll_frame2 = self._make_scrollable(tab2)

        self.create_cutter_widgets(self.scroll_frame1)
        self.create_editor_widgets(self.scroll_frame2)

    # ───────────────────────────── Theming ─────────────────────────────
    def _init_fonts(self):
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
        self.style.theme_use("clam")

        self.style.configure(".", background=c["bg"], foreground=c["text"], font=(self.font_body, 10))
        self.style.configure("TFrame", background=c["bg"])
        self.style.configure("TLabel", background=c["bg"], foreground=c["text"])
        self.style.configure("Hint.TLabel", background=c["bg"], foreground=c["text_dim"], font=(self.font_body, 9))
        self.style.configure("Header.TLabel", background=c["bg"], foreground=c["text"], font=(self.font_heading, 16, "bold"))
        self.style.configure("Subheader.TLabel", background=c["bg"], foreground=c["text_dim"], font=(self.font_body, 10))

        self.style.configure("TLabelframe", background=c["bg"], borderwidth=1, relief="solid",
                              bordercolor=c["border"], lightcolor=c["border"], darkcolor=c["border"])
        self.style.configure("TLabelframe.Label", background=c["bg"], foreground=c["accent"], font=(self.font_heading, 10, "bold"))

        self.style.configure("TCheckbutton", background=c["bg"], foreground=c["text"],
                              font=(self.font_body, 10), indicatorbackground=c["surface"], indicatormargin=6)
        self.style.map("TCheckbutton",
                        background=[("active", c["bg"])],
                        foreground=[("active", c["accent"])],
                        indicatorbackground=[("selected", c["accent"]), ("active", c["surface_hi"])])

        self.style.configure("TEntry", fieldbackground=c["surface"], foreground=c["text"],
                              insertcolor=c["text"], bordercolor=c["border"],
                              lightcolor=c["border"], darkcolor=c["border"], borderwidth=1, relief="flat", padding=6)
        self.style.map("TEntry", bordercolor=[("focus", c["accent"])],
                        lightcolor=[("focus", c["accent"])], darkcolor=[("focus", c["accent"])])

        self.style.configure("TSpinbox", fieldbackground=c["surface"], foreground=c["text"],
                              arrowcolor=c["text_dim"], bordercolor=c["border"],
                              lightcolor=c["border"], darkcolor=c["border"], borderwidth=1, relief="flat",
                              padding=5, insertcolor=c["text"])
        self.style.map("TSpinbox", arrowcolor=[("active", c["accent"])], bordercolor=[("focus", c["accent"])])

        self.style.configure("TCombobox", fieldbackground=c["surface"], foreground=c["text"],
                              background=c["surface"], arrowcolor=c["text_dim"],
                              bordercolor=c["border"], lightcolor=c["border"], darkcolor=c["border"],
                              borderwidth=1, relief="flat", padding=5)
        self.style.map("TCombobox",
                        fieldbackground=[("readonly", c["surface"])],
                        foreground=[("readonly", c["text"])],
                        bordercolor=[("focus", c["accent"])],
                        arrowcolor=[("active", c["accent"])])
        self.root.option_add("*TCombobox*Listbox.background", c["surface"])
        self.root.option_add("*TCombobox*Listbox.foreground", c["text"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", c["accent"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", c["accent_ink"])
        self.root.option_add("*TCombobox*Listbox.font", (self.font_body, 10))

        self.style.configure("TButton", background=c["surface"], foreground=c["text"],
                              borderwidth=0, focusthickness=0, padding=(14, 8), font=(self.font_body, 10))
        self.style.map("TButton", background=[("active", c["surface_hi"]), ("disabled", c["surface"])],
                        foreground=[("disabled", c["text_dim"])])

        self.style.configure("Accent.TButton", background=c["accent"], foreground=c["accent_ink"],
                              borderwidth=0, padding=(18, 11), font=(self.font_heading, 11, "bold"))
        self.style.map("Accent.TButton", background=[("active", c["accent_hover"]), ("disabled", c["border"])],
                        foreground=[("disabled", c["text_dim"])])

        self.style.configure("Ghost.TButton", background=c["bg"], foreground=c["accent"],
                              borderwidth=1, relief="solid", bordercolor=c["accent"],
                              lightcolor=c["accent"], darkcolor=c["accent"], padding=(16, 10), font=(self.font_body, 10, "bold"))
        self.style.map("Ghost.TButton", background=[("active", c["surface"])], bordercolor=[("active", c["accent_hover"])])

        self.style.configure("Utility.TButton", background=c["surface"], foreground=c["text"],
                              borderwidth=1, relief="solid", bordercolor=c["border"],
                              lightcolor=c["border"], darkcolor=c["border"], padding=(12, 8), font=(self.font_body, 10))
        self.style.map("Utility.TButton", background=[("active", c["surface_hi"])], bordercolor=[("active", c["accent"])])

        self.style.configure("Modern.Horizontal.TProgressbar", troughcolor=c["surface"], background=c["accent"],
                              bordercolor=c["surface"], lightcolor=c["accent"], darkcolor=c["accent"], thickness=10)

        self.style.configure("Vertical.TScrollbar", background=c["surface"], troughcolor=c["bg"],
                              bordercolor=c["bg"], arrowcolor=c["text_dim"], relief="flat", gripcount=0)
        self.style.map("Vertical.TScrollbar", background=[("active", c["accent"])])

        self.style.configure("TNotebook", background=c["bg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", background=c["surface"], foreground=c["text_dim"],
                              padding=(16, 10), font=(self.font_heading, 10, "bold"), borderwidth=0)
        self.style.map("TNotebook.Tab",
                        background=[("selected", c["bg"])],
                        foreground=[("selected", c["accent"])])

    # ───────────────────────── Scrollable wrapper (shared by both tabs) ─────────────────────────
    def _make_scrollable(self, parent):
        outer = ttk.Frame(parent)
        outer.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(outer, highlightthickness=0, bg=COLORS["bg"])
        vscroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        frame = ttk.Frame(canvas, padding="22")
        frame_id = canvas.create_window((0, 0), window=frame, anchor="nw")

        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(frame_id, width=e.width))

        def _wheel(event):
            if event.num == 4:
                delta = -1
            elif event.num == 5:
                delta = 1
            else:
                delta = -1 if event.delta > 0 else 1
            canvas.yview_scroll(delta, "units")

        def _bind_wheel(_e=None):
            canvas.bind_all("<MouseWheel>", _wheel)
            canvas.bind_all("<Button-4>", _wheel)
            canvas.bind_all("<Button-5>", _wheel)

        def _unbind_wheel(_e=None):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _bind_wheel)
        canvas.bind("<Leave>", _unbind_wheel)
        return canvas, frame

    # ═══════════════════════════ TAB 1 — Shorts Cutter (original tool) ═══════════════════════════
    def create_cutter_widgets(self, main_frame):
        c = COLORS

        header_box = ttk.Frame(main_frame)
        header_box.pack(fill=tk.X, pady=(0, 18), anchor="w")
        ttk.Label(header_box, text="⚡ Multi-Shorts Cutter", style="Header.TLabel").pack(anchor="w")
        ttk.Label(header_box, text="Resolve the stream once, cut as many vertical clips as you need.",
                  style="Subheader.TLabel").pack(anchor="w", pady=(4, 0))

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
        self.duration_label = ttk.Label(source_frame, text="Video duration: not checked yet", style="Hint.TLabel")
        self.duration_label.pack(anchor="w", pady=(10, 0))

        config_frame = ttk.LabelFrame(main_frame, text="  2 · Clip Generation  ", padding="14")
        config_frame.pack(fill=tk.X, pady=6)

        self.auto_mode_var = tk.BooleanVar(value=True)
        self.auto_check = ttk.Checkbutton(
            config_frame,
            text="Auto mode — detect full video duration and auto-generate shorts to cover the whole video",
            variable=self.auto_mode_var, command=self.toggle_mode)
        self.auto_check.pack(anchor="w")

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

        ttk.Label(config_frame,
                  text='Example: a 2-minute video with a 30s clip length auto-generates 4 shorts (0-30, 30-60, 60-90, 90-120).\n'
                       'Duration is detected automatically when you click "Build" — no need to check it first.',
                  style="Hint.TLabel", justify="left").pack(anchor="w", pady=(12, 0))

        self.manual_frame = ttk.LabelFrame(main_frame, text="  Manual Clips — one per line as  start-end  (seconds)  ", padding="14")
        ttk.Label(self.manual_frame, text="Example:\n10-40\n75-100\n200-230", style="Hint.TLabel", justify="left").pack(anchor="w", pady=(0, 8))
        self.ranges_text = tk.Text(self.manual_frame, height=5, font=(self.font_mono, 10),
                                    bg=c["surface"], fg=c["text"], insertbackground=c["accent"],
                                    selectbackground=c["border"], selectforeground=c["text"],
                                    relief="flat", highlightthickness=1, highlightbackground=c["border"],
                                    highlightcolor=c["accent"], padx=10, pady=8)
        self.ranges_text.pack(fill=tk.X)
        self.ranges_text.insert("1.0", "10-40\n75-100")

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

        activity_frame = ttk.LabelFrame(main_frame, text="  3 · Live Pipeline Monitor (Step-by-Step)  ", padding="14")
        activity_frame.pack(fill=tk.BOTH, expand=True, pady=14)
        self.log_box = ScrolledText(activity_frame, height=12, font=(self.font_mono, 10),
                                     bg="#0D1117", fg="#C9D1D9", insertbackground=c["accent"],
                                     selectbackground=c["border"], selectforeground=c["text"],
                                     relief="flat", highlightthickness=1, highlightbackground=c["border"],
                                     highlightcolor=c["accent"], padx=10, pady=8)
        self.log_box.pack(fill=tk.BOTH, expand=True)
        try:
            self.log_box.frame.configure(bg=c["bg"])
            self.log_box.vbar.configure(bg=c["surface"], activebackground=c["accent"],
                                         troughcolor=c["bg"], highlightthickness=0, bd=0, elementborderwidth=0, width=14)
        except Exception:
            pass
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

        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", mode="determinate", style="Modern.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, pady=(6, 12))

        self.btn_frame = ttk.Frame(main_frame, padding="5")
        self.btn_frame.pack(fill=tk.X, pady=5)
        self.process_btn = ttk.Button(self.btn_frame, text="🚀 Build All Shorts Now", style="Accent.TButton",
                                       cursor="hand2", command=self.start_pipeline_thread)
        self.process_btn.pack(side=tk.LEFT, padx=(0, 8), expand=True, fill=tk.X)
        self.open_folder_btn = ttk.Button(self.btn_frame, text="📁 Open Shorts Folder", style="Ghost.TButton",
                                           cursor="hand2", command=self.open_shorts_folder)
        self.open_folder_btn.pack(side=tk.RIGHT, padx=(8, 0), expand=True, fill=tk.X)

    def toggle_mode(self):
        if self.auto_mode_var.get():
            self.manual_frame.pack_forget()
        else:
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

        leftover = total - start
        if leftover >= clip_len / 2 and (not ranges or ranges[-1][1] < total):
            last_start = max(total - clip_len, ranges[-1][1] if ranges else 0)
            if last_start < total - 1:
                ranges.append((last_start, total))

        if not ranges and total > 1:
            ranges.append((0, total))

        if max_clips > 0:
            ranges = ranges[:max_clips]

        if not ranges:
            raise ValueError("Could not generate any clips from this video's duration.")

        return ranges

    def log_message(self, message):
        if not isinstance(message, str):
            message = str(message)
        message = message.encode('utf-8', errors='replace').decode('utf-8')

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
                self.duration_label.config(text=f"Video duration: {fmt_duration(duration)}  ({duration}s)  —  \"{title[:60]}\"")
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

    def start_pipeline_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube link.")
            return

        if not self.auto_mode_var.get():
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
                'quiet': True, 'no_warnings': True, 'noplaylist': True,
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

            if ranges is None:
                if not self.video_duration:
                    raise RuntimeError("Could not determine video duration for auto mode.")
                ranges = self.compute_auto_ranges(self.video_duration)
                self.progress_bar['maximum'] = len(ranges)
                self.log_message(f"[INFO] Auto mode: video is {fmt_duration(self.video_duration)} long. "
                                  f"Generating {len(ranges)} short(s) of ~{self.clip_len_spin.get()}s each.")
                for i, (s, e) in enumerate(ranges, start=1):
                    self.log_message(f"   • Short {i}: {s}s -> {e}s ({e - s}s)")

            if self.video_duration:
                out_of_range = [r for r in ranges if r[1] > self.video_duration]
                if out_of_range:
                    self.log_message(f"[WARNING] {len(out_of_range)} clip(s) exceed video length "
                                      f"({fmt_duration(self.video_duration)}). They may be shorter than requested or fail.")

            self.log_message("[STEP 1/2] Stream endpoints resolved successfully — reused for every clip.")
            self.log_message(f"[STEP 2/2] Cutting {len(ranges)} clip(s) @ {max_height}p, preset={preset}, vertical 9:16...")

            for idx, (start_time, end_time) in enumerate(ranges, start=1):
                duration = end_time - start_time
                output_file = self.shorts_dir / f"{safe_title}_short_{idx:02d}_{start_time}-{end_time}.mp4"
                self.log_message(f"[CLIP {idx}/{len(ranges)}] {start_time}s -> {end_time}s ({duration}s) — downloading only this segment...")

                if video_url == audio_url:
                    ffmpeg_cmd = [
                        ffmpeg_exe_path, "-y", "-ss", str(start_time), "-i", video_url, "-t", str(duration),
                        "-vf", "crop=ih*9/16:ih,scale=1080:1920",
                        "-c:v", "libx264", "-preset", preset, "-crf", "23",
                        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output_file)
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
                        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output_file)
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
                messagebox.showinfo("Pipeline Complete",
                                     f"{success_count} short(s) created successfully" + (f", {fail_count} failed" if fail_count else "") +
                                     f".\nCheck the '{self.shorts_dir}' folder.")
            else:
                messagebox.showerror("Pipeline Failed", "No clips were created successfully. Check the log.")

        except Exception as e:
            self.log_message(f"[ERROR] Pipeline Failed: {str(e)}")
            messagebox.showerror("Pipeline Processing Error", f"Details:\n{str(e)}")
        finally:
            self.process_btn.config(state=tk.NORMAL)

    # ═══════════════════════════ TAB 2 — Video Editor (new) ═══════════════════════════
    def create_editor_widgets(self, main_frame):
        c = COLORS

        header_box = ttk.Frame(main_frame)
        header_box.pack(fill=tk.X, pady=(0, 18), anchor="w")
        ttk.Label(header_box, text="🎛️ Video Editor", style="Header.TLabel").pack(anchor="w")
        ttk.Label(header_box,
                  text="Tick the features you want, set their options, then hit Apply. Your original file is never overwritten.",
                  style="Subheader.TLabel").pack(anchor="w", pady=(4, 0))

        if not EDITOR_DEPS_OK:
            warn = ttk.LabelFrame(main_frame, text="  ⚠ Missing dependencies  ", padding="14")
            warn.pack(fill=tk.X, pady=6)
            ttk.Label(warn, text="The Editor tab needs a few extra packages that aren't installed:",
                      style="Hint.TLabel", justify="left").pack(anchor="w")
            ttk.Label(warn, text="pip install moviepy==1.0.3 pillow numpy", font=(self.font_mono, 10),
                      foreground=c["amber"]).pack(anchor="w", pady=(6, 6))
            ttk.Label(warn, text=f"Detail: {EDITOR_DEPS_ERROR}", style="Hint.TLabel", justify="left").pack(anchor="w")
            return

        # ---- 1 · Input video ----
        input_frame = ttk.LabelFrame(main_frame, text="  1 · Input Video  ", padding="14")
        input_frame.pack(fill=tk.X, pady=6)
        row = ttk.Frame(input_frame)
        row.pack(fill=tk.X)
        self.ed_input_path = tk.StringVar()
        ttk.Entry(row, textvariable=self.ed_input_path, width=55).pack(side=tk.LEFT, padx=(0, 10), expand=True, fill=tk.X)
        ttk.Button(row, text="📂 Browse", style="Utility.TButton", cursor="hand2",
                   command=self._browse_input_video).pack(side=tk.RIGHT)
        ttk.Label(input_frame, text="Tip: pick a clip you already cut in the Shorts Cutter tab, or any video you have rights to edit.",
                  style="Hint.TLabel").pack(anchor="w", pady=(8, 0))

        # ---- 2 · Audio ----
        audio_frame = ttk.LabelFrame(main_frame, text="  2 · Audio  ", padding="14")
        audio_frame.pack(fill=tk.X, pady=6)
        self.aud_mode = tk.StringVar(value="keep")
        mode_row = ttk.Frame(audio_frame)
        mode_row.pack(fill=tk.X)
        for val, label in [("keep", "Keep Original"), ("remove", "🔇 Remove Audio"),
                            ("replace", "🔁 Replace Audio"), ("mix", "🎤 Mix Voiceover")]:
            ttk.Radiobutton(mode_row, text=label, value=val, variable=self.aud_mode).pack(side=tk.LEFT, padx=(0, 14))

        aud_file_row = ttk.Frame(audio_frame)
        aud_file_row.pack(fill=tk.X, pady=(10, 0))
        self.aud_file = tk.StringVar()
        ttk.Label(aud_file_row, text="Audio file (for Replace / Mix)").pack(anchor="w")
        aud_file_inner = ttk.Frame(audio_frame)
        aud_file_inner.pack(fill=tk.X, pady=(4, 0))
        ttk.Entry(aud_file_inner, textvariable=self.aud_file, width=48).pack(side=tk.LEFT, padx=(0, 10), expand=True, fill=tk.X)
        ttk.Button(aud_file_inner, text="🎵 Browse Audio", style="Utility.TButton", cursor="hand2",
                   command=self._browse_audio).pack(side=tk.RIGHT)

        vol_row = ttk.Frame(audio_frame)
        vol_row.pack(fill=tk.X, pady=(12, 0))
        ttk.Label(vol_row, text="Original volume %").pack(side=tk.LEFT, padx=(0, 6))
        self.aud_orig_vol = tk.IntVar(value=20)
        ttk.Spinbox(vol_row, from_=0, to=200, width=6, textvariable=self.aud_orig_vol).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(vol_row, text="New track volume %").pack(side=tk.LEFT, padx=(0, 6))
        self.aud_new_vol = tk.IntVar(value=100)
        ttk.Spinbox(vol_row, from_=0, to=200, width=6, textvariable=self.aud_new_vol).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(vol_row, text="New track start offset (s)").pack(side=tk.LEFT, padx=(0, 6))
        self.aud_offset = tk.DoubleVar(value=0)
        ttk.Spinbox(vol_row, from_=0, to=3600, width=6, textvariable=self.aud_offset).pack(side=tk.LEFT)
        ttk.Label(audio_frame, text="\"Mix Voiceover\" keeps the original audio quiet underneath and layers your new track on top.",
                  style="Hint.TLabel").pack(anchor="w", pady=(10, 0))

        # ---- 3 · Text overlays (2 slots) ----
        self.text_slots = []
        for slot_idx in (1, 2):
            self.text_slots.append(self._build_text_slot_ui(main_frame, slot_idx))

        # ---- 4 · Logo / Watermark ----
        logo_frame = ttk.LabelFrame(main_frame, text="  4 · Logo / Watermark  ", padding="14")
        logo_frame.pack(fill=tk.X, pady=6)
        self.logo_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(logo_frame, text="Enable logo / watermark", variable=self.logo_enabled).pack(anchor="w")

        logo_row1 = ttk.Frame(logo_frame)
        logo_row1.pack(fill=tk.X, pady=(10, 0))
        self.logo_path = tk.StringVar()
        ttk.Entry(logo_row1, textvariable=self.logo_path, width=46).pack(side=tk.LEFT, padx=(0, 10), expand=True, fill=tk.X)
        ttk.Button(logo_row1, text="🖼 Browse Image", style="Utility.TButton", cursor="hand2",
                   command=self._browse_logo).pack(side=tk.RIGHT)

        logo_row2 = ttk.Frame(logo_frame)
        logo_row2.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(logo_row2, text="Position").pack(side=tk.LEFT, padx=(0, 6))
        self.logo_position = tk.StringVar(value="Top-Right")
        ttk.Combobox(logo_row2, textvariable=self.logo_position, values=POSITION_PRESETS, width=14, state="readonly").pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(logo_row2, text="Size % of width").pack(side=tk.LEFT, padx=(0, 6))
        self.logo_size_pct = tk.IntVar(value=15)
        ttk.Spinbox(logo_row2, from_=2, to=100, width=5, textvariable=self.logo_size_pct).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(logo_row2, text="Opacity %").pack(side=tk.LEFT, padx=(0, 6))
        self.logo_opacity = tk.IntVar(value=100)
        ttk.Spinbox(logo_row2, from_=5, to=100, width=5, textvariable=self.logo_opacity).pack(side=tk.LEFT)

        logo_row3 = ttk.Frame(logo_frame)
        logo_row3.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(logo_row3, text="Margin (px)").pack(side=tk.LEFT, padx=(0, 6))
        self.logo_margin = tk.IntVar(value=24)
        ttk.Spinbox(logo_row3, from_=0, to=200, width=5, textvariable=self.logo_margin).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(logo_row3, text="Start (s)").pack(side=tk.LEFT, padx=(0, 6))
        self.logo_start = tk.DoubleVar(value=0)
        ttk.Spinbox(logo_row3, from_=0, to=3600, width=6, textvariable=self.logo_start).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(logo_row3, text="Duration (s, blank/full = rest)").pack(side=tk.LEFT, padx=(0, 6))
        self.logo_duration = tk.StringVar(value="full")
        ttk.Entry(logo_row3, textvariable=self.logo_duration, width=8).pack(side=tk.LEFT)

        # ---- 5 · Shape annotation ----
        shape_frame = ttk.LabelFrame(main_frame, text="  5 · Shape Annotation  ", padding="14")
        shape_frame.pack(fill=tk.X, pady=6)
        self.shape_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(shape_frame, text="Enable shape annotation (circle / rectangle)", variable=self.shape_enabled).pack(anchor="w")

        shape_row1 = ttk.Frame(shape_frame)
        shape_row1.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(shape_row1, text="Shape").pack(side=tk.LEFT, padx=(0, 6))
        self.shape_type = tk.StringVar(value="Circle")
        ttk.Combobox(shape_row1, textvariable=self.shape_type, values=["Circle", "Rectangle"], width=10, state="readonly").pack(side=tk.LEFT, padx=(0, 18))
        self.shape_filled = tk.BooleanVar(value=False)
        ttk.Checkbutton(shape_row1, text="Filled", variable=self.shape_filled).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(shape_row1, text="Color").pack(side=tk.LEFT, padx=(0, 6))
        self.shape_color = tk.StringVar(value="#2DD4BF")
        ttk.Button(shape_row1, text="🎨 Pick", style="Utility.TButton", cursor="hand2",
                   command=lambda: self._pick_color(self.shape_color)).pack(side=tk.LEFT)

        shape_row2 = ttk.Frame(shape_frame)
        shape_row2.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(shape_row2, text="X position %").pack(side=tk.LEFT, padx=(0, 6))
        self.shape_x = tk.IntVar(value=50)
        ttk.Spinbox(shape_row2, from_=0, to=100, width=5, textvariable=self.shape_x).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(shape_row2, text="Y position %").pack(side=tk.LEFT, padx=(0, 6))
        self.shape_y = tk.IntVar(value=50)
        ttk.Spinbox(shape_row2, from_=0, to=100, width=5, textvariable=self.shape_y).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(shape_row2, text="Size % of width").pack(side=tk.LEFT, padx=(0, 6))
        self.shape_size = tk.IntVar(value=15)
        ttk.Spinbox(shape_row2, from_=2, to=100, width=5, textvariable=self.shape_size).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(shape_row2, text="Line thickness").pack(side=tk.LEFT, padx=(0, 6))
        self.shape_thickness = tk.IntVar(value=4)
        ttk.Spinbox(shape_row2, from_=1, to=40, width=5, textvariable=self.shape_thickness).pack(side=tk.LEFT)

        shape_row3 = ttk.Frame(shape_frame)
        shape_row3.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(shape_row3, text="Start (s)").pack(side=tk.LEFT, padx=(0, 6))
        self.shape_start = tk.DoubleVar(value=0)
        ttk.Spinbox(shape_row3, from_=0, to=3600, width=6, textvariable=self.shape_start).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(shape_row3, text="Duration (s, blank/full = rest)").pack(side=tk.LEFT, padx=(0, 6))
        self.shape_duration = tk.StringVar(value="3")
        ttk.Entry(shape_row3, textvariable=self.shape_duration, width=8).pack(side=tk.LEFT)
        ttk.Label(shape_frame, text="X/Y position is a percentage of the frame — 50/50 is dead center, 0/0 is top-left.",
                  style="Hint.TLabel").pack(anchor="w", pady=(10, 0))

        # ---- 6 · Intro / Outro ----
        self.intro_enabled, self.intro_mode, self.intro_text, self.intro_bg, self.intro_duration, self.intro_clip_path = \
            self._build_card_ui(main_frame, "6 · Intro", "Plays BEFORE your video")
        self.outro_enabled, self.outro_mode, self.outro_text, self.outro_bg, self.outro_duration, self.outro_clip_path = \
            self._build_card_ui(main_frame, "7 · Outro", "Plays AFTER your video")

        # ---- 8 · Preview ----
        preview_frame = ttk.LabelFrame(main_frame, text="  8 · Live Placement Preview  ", padding="14")
        preview_frame.pack(fill=tk.X, pady=6)
        prev_row = ttk.Frame(preview_frame)
        prev_row.pack(fill=tk.X)
        ttk.Label(prev_row, text="Preview timestamp (s)").pack(side=tk.LEFT, padx=(0, 6))
        self.preview_time = tk.DoubleVar(value=0)
        ttk.Spinbox(prev_row, from_=0, to=99999, width=8, textvariable=self.preview_time).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Button(prev_row, text="🔄 Refresh Preview", style="Utility.TButton", cursor="hand2",
                   command=self.refresh_preview).pack(side=tk.LEFT)
        self.preview_canvas = tk.Canvas(preview_frame, width=480, height=270, bg="#000000", highlightthickness=1,
                                         highlightbackground=c["border"])
        self.preview_canvas.pack(pady=(12, 0))
        self._preview_imgtk = None
        ttk.Label(preview_frame, text="Shows text / logo / shape placement on a real frame from your video — exactly what export will produce.",
                  style="Hint.TLabel").pack(anchor="w", pady=(10, 0))

        # ---- 9 · Export ----
        export_frame = ttk.LabelFrame(main_frame, text="  9 · Export  ", padding="14")
        export_frame.pack(fill=tk.X, pady=6)
        self.ed_log = ScrolledText(export_frame, height=8, font=(self.font_mono, 10),
                                    bg="#0D1117", fg="#C9D1D9", insertbackground=c["accent"],
                                    selectbackground=c["border"], selectforeground=c["text"],
                                    relief="flat", highlightthickness=1, highlightbackground=c["border"],
                                    highlightcolor=c["accent"], padx=10, pady=8)
        self.ed_log.pack(fill=tk.BOTH, expand=True)
        try:
            self.ed_log.frame.configure(bg=c["bg"])
            self.ed_log.vbar.configure(bg=c["surface"], activebackground=c["accent"], troughcolor=c["bg"],
                                        highlightthickness=0, bd=0, elementborderwidth=0, width=14)
        except Exception:
            pass
        self.ed_log.tag_configure("err", foreground=c["danger"])
        self.ed_log.tag_configure("ok", foreground=c["success"])
        self.ed_log.tag_configure("info", foreground=c["info"])
        self.ed_log.config(state=tk.NORMAL)
        self.ed_log.insert(tk.END, "[SYSTEM] Editor ready. Tick your features above, then Apply.\n")
        self.ed_log.config(state=tk.DISABLED)

        export_btn_row = ttk.Frame(export_frame)
        export_btn_row.pack(fill=tk.X, pady=(12, 0))
        self.ed_apply_btn = ttk.Button(export_btn_row, text="✅ Apply All Selected Features (Export)", style="Accent.TButton",
                                        cursor="hand2", command=self.start_apply_thread)
        self.ed_apply_btn.pack(side=tk.LEFT, padx=(0, 8), expand=True, fill=tk.X)
        ttk.Button(export_btn_row, text="📁 Open Edited Folder", style="Ghost.TButton", cursor="hand2",
                   command=self.open_edited_folder).pack(side=tk.RIGHT, padx=(8, 0), expand=True, fill=tk.X)

    # ---- Editor sub-builders ----
    def _build_text_slot_ui(self, parent, slot_idx):
        c = COLORS
        frame = ttk.LabelFrame(parent, text=f"  3.{slot_idx} · Text Overlay #{slot_idx}  ", padding="14")
        frame.pack(fill=tk.X, pady=6)

        enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Enable this text overlay", variable=enabled).pack(anchor="w")

        text_row = ttk.Frame(frame)
        text_row.pack(fill=tk.X, pady=(10, 0))
        text_var = tk.StringVar(value="Your text here" if slot_idx == 1 else "")
        ttk.Entry(text_row, textvariable=text_var, width=50).pack(side=tk.LEFT, expand=True, fill=tk.X)

        row2 = ttk.Frame(frame)
        row2.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(row2, text="Font file (.ttf/.otf, optional)").pack(side=tk.LEFT, padx=(0, 6))
        font_path = tk.StringVar()
        ttk.Entry(row2, textvariable=font_path, width=28).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(row2, text="🔤 Browse", style="Utility.TButton", cursor="hand2",
                   command=lambda v=font_path: self._browse_font(v)).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(row2, text="Size").pack(side=tk.LEFT, padx=(0, 6))
        size_var = tk.IntVar(value=48)
        ttk.Spinbox(row2, from_=8, to=200, width=5, textvariable=size_var).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(row2, text="Color").pack(side=tk.LEFT, padx=(0, 6))
        color_var = tk.StringVar(value="#FFFFFF")
        ttk.Button(row2, text="🎨 Pick", style="Utility.TButton", cursor="hand2",
                   command=lambda v=color_var: self._pick_color(v)).pack(side=tk.LEFT)

        row3 = ttk.Frame(frame)
        row3.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(row3, text="Position").pack(side=tk.LEFT, padx=(0, 6))
        position_var = tk.StringVar(value="Bottom-Center" if slot_idx == 1 else "Top-Center")
        ttk.Combobox(row3, textvariable=position_var, values=POSITION_PRESETS, width=14, state="readonly").pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(row3, text="Custom X%").pack(side=tk.LEFT, padx=(0, 6))
        custom_x = tk.IntVar(value=50)
        ttk.Spinbox(row3, from_=0, to=100, width=5, textvariable=custom_x).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(row3, text="Custom Y%").pack(side=tk.LEFT, padx=(0, 6))
        custom_y = tk.IntVar(value=50)
        ttk.Spinbox(row3, from_=0, to=100, width=5, textvariable=custom_y).pack(side=tk.LEFT, padx=(0, 18))
        box_bg = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text="Background box", variable=box_bg).pack(side=tk.LEFT)

        row4 = ttk.Frame(frame)
        row4.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(row4, text="Start (s)").pack(side=tk.LEFT, padx=(0, 6))
        start_var = tk.DoubleVar(value=0)
        ttk.Spinbox(row4, from_=0, to=3600, width=6, textvariable=start_var).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(row4, text="Duration (s, blank/full = rest)").pack(side=tk.LEFT, padx=(0, 6))
        duration_var = tk.StringVar(value="full" if slot_idx == 1 else "3")
        ttk.Entry(row4, textvariable=duration_var, width=8).pack(side=tk.LEFT)

        return {
            'enabled': enabled, 'text': text_var, 'font_path': font_path, 'size': size_var,
            'color': color_var, 'position': position_var, 'custom_x': custom_x, 'custom_y': custom_y,
            'box_bg': box_bg, 'start': start_var, 'duration': duration_var,
        }

    def _build_card_ui(self, parent, title, hint):
        frame = ttk.LabelFrame(parent, text=f"  {title}  ", padding="14")
        frame.pack(fill=tk.X, pady=6)
        enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text=f"Enable {title.split('·')[-1].strip()} ({hint})", variable=enabled).pack(anchor="w")

        mode = tk.StringVar(value="text")
        row1 = ttk.Frame(frame)
        row1.pack(fill=tk.X, pady=(10, 0))
        ttk.Radiobutton(row1, text="Generate text title card", value="text", variable=mode).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Radiobutton(row1, text="Use my own video clip", value="clip", variable=mode).pack(side=tk.LEFT)

        row2 = ttk.Frame(frame)
        row2.pack(fill=tk.X, pady=(10, 0))
        text_var = tk.StringVar(value="")
        ttk.Label(row2, text="Title text").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Entry(row2, textvariable=text_var, width=30).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(row2, text="Background color").pack(side=tk.LEFT, padx=(0, 6))
        bg_var = tk.StringVar(value="#10131A")
        ttk.Button(row2, text="🎨 Pick", style="Utility.TButton", cursor="hand2",
                   command=lambda v=bg_var: self._pick_color(v)).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(row2, text="Duration (s)").pack(side=tk.LEFT, padx=(0, 6))
        dur_var = tk.DoubleVar(value=2)
        ttk.Spinbox(row2, from_=0.5, to=30, increment=0.5, width=6, textvariable=dur_var).pack(side=tk.LEFT)

        row3 = ttk.Frame(frame)
        row3.pack(fill=tk.X, pady=(10, 0))
        clip_var = tk.StringVar(value="")
        ttk.Label(row3, text="Or pick a clip:").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Entry(row3, textvariable=clip_var, width=38).pack(side=tk.LEFT, padx=(0, 10), expand=True, fill=tk.X)
        ttk.Button(row3, text="🎬 Browse Clip", style="Utility.TButton", cursor="hand2",
                   command=lambda v=clip_var: self._browse_video(v)).pack(side=tk.RIGHT)

        return enabled, mode, text_var, bg_var, dur_var, clip_var

    # ---- Browse / pick helpers ----
    def _browse_input_video(self):
        start_dir = str(self.shorts_dir.resolve()) if self.shorts_dir.exists() else "."
        path = filedialog.askopenfilename(initialdir=start_dir, title="Pick a video to edit",
                                           filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi *.webm"), ("All files", "*.*")])
        if path:
            self.ed_input_path.set(path)

    def _browse_video(self, var):
        path = filedialog.askopenfilename(title="Pick a video clip",
                                           filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi *.webm"), ("All files", "*.*")])
        if path:
            var.set(path)

    def _browse_audio(self):
        path = filedialog.askopenfilename(title="Pick an audio file",
                                           filetypes=[("Audio files", "*.mp3 *.wav *.m4a *.aac *.flac"), ("All files", "*.*")])
        if path:
            self.aud_file.set(path)

    def _browse_logo(self):
        path = filedialog.askopenfilename(title="Pick a logo / watermark image",
                                           filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")])
        if path:
            self.logo_path.set(path)

    def _browse_font(self, var):
        path = filedialog.askopenfilename(title="Pick a font file",
                                           filetypes=[("Font files", "*.ttf *.otf"), ("All files", "*.*")])
        if path:
            var.set(path)

    def _pick_color(self, var):
        rgb, hex_code = colorchooser.askcolor(color=var.get() or "#FFFFFF", title="Pick a color")
        if hex_code:
            var.set(hex_code)

    def open_edited_folder(self):
        full_path = self.edited_dir.resolve()
        if sys.platform == "win32":
            os.startfile(full_path)
        elif sys.platform == "darwin":
            subprocess.run(["open", full_path])
        else:
            subprocess.run(["xdg-open", full_path])

    def ed_log_msg(self, message):
        message = str(message).encode('utf-8', errors='replace').decode('utf-8')
        tag = None
        upper = message.upper()
        if "[ERROR]" in upper:
            tag = "err"
        elif "[DONE]" in upper:
            tag = "ok"
        elif "[INFO]" in upper or "[" in message:
            tag = "info"
        self.ed_log.config(state=tk.NORMAL)
        start_index = self.ed_log.index(tk.END)
        self.ed_log.insert(tk.END, f"-> {message}\n")
        if tag:
            self.ed_log.tag_add(tag, start_index, self.ed_log.index(tk.END))
        self.ed_log.see(tk.END)
        self.ed_log.config(state=tk.DISABLED)
        self.root.update_idletasks()

    # ---- Live preview ----
    def refresh_preview(self):
        try:
            input_path = self.ed_input_path.get().strip()
            if not input_path or not Path(input_path).exists():
                messagebox.showerror("Error", "Pick a video file first (Section 1).")
                return

            clip = VideoFileClip(input_path)
            t = min(max(0.0, float(self.preview_time.get() or 0)), max(0.0, clip.duration - 0.05))
            frame = clip.get_frame(t)
            base = Image.fromarray(frame).convert("RGBA")
            w, h = base.size

            for tslot in self.text_slots:
                if tslot['enabled'].get() and tslot['text'].get().strip():
                    overlay = render_text_image(w, h, tslot['text'].get(), tslot['font_path'].get(),
                                                 tslot['size'].get(), tslot['color'].get(), tslot['position'].get(),
                                                 tslot['custom_x'].get(), tslot['custom_y'].get(), tslot['box_bg'].get())
                    base = Image.alpha_composite(base, overlay)

            if self.logo_enabled.get() and self.logo_path.get().strip() and Path(self.logo_path.get()).exists():
                overlay = render_logo_image(w, h, self.logo_path.get(), self.logo_position.get(),
                                             self.logo_size_pct.get(), self.logo_opacity.get(), self.logo_margin.get())
                base = Image.alpha_composite(base, overlay)

            if self.shape_enabled.get():
                overlay = render_shape_image(w, h, self.shape_type.get(), self.shape_x.get(), self.shape_y.get(),
                                              self.shape_size.get(), self.shape_color.get(),
                                              self.shape_thickness.get(), self.shape_filled.get())
                base = Image.alpha_composite(base, overlay)

            clip.close()

            max_w, max_h = 480, 270
            ratio = min(max_w / w, max_h / h)
            disp = base.convert("RGB").resize((max(1, int(w * ratio)), max(1, int(h * ratio))), Image.LANCZOS)
            self._preview_imgtk = ImageTk.PhotoImage(disp)
            self.preview_canvas.config(width=disp.width, height=disp.height)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(0, 0, anchor="nw", image=self._preview_imgtk)
        except Exception as e:
            messagebox.showerror("Preview Failed", str(e))

    # ---- Export pipeline ----
    def start_apply_thread(self):
        self.ed_apply_btn.config(state=tk.DISABLED)
        threading.Thread(target=self._apply_worker, daemon=True).start()

    def _build_card_clip(self, mode, text, bg_hex, duration, clip_path, w, h, fps):
        if mode == "clip" and clip_path and Path(clip_path).exists():
            card = VideoFileClip(clip_path)
            if card.size != [w, h] and card.size != (w, h):
                card = card.resize((w, h))
            return card
        img = render_title_card(w, h, text, bg_hex)
        return ImageClip(np.array(img)).set_duration(max(0.5, float(duration or 2))).set_fps(fps)

    def _apply_worker(self):
        opened_clips = []
        try:
            input_path = self.ed_input_path.get().strip()
            if not input_path or not Path(input_path).exists():
                raise RuntimeError("Pick a valid input video first (Section 1).")

            self.ed_log_msg(f"[INFO] Loading {Path(input_path).name} ...")
            clip = VideoFileClip(input_path)
            opened_clips.append(clip)
            w, h = clip.size
            fps = clip.fps or 30

            # ---- Audio ----
            mode = self.aud_mode.get()
            if mode == "remove":
                clip = clip.without_audio()
                self.ed_log_msg("[AUDIO] Removed original audio.")
            elif mode in ("replace", "mix"):
                apath = self.aud_file.get().strip()
                if not apath or not Path(apath).exists():
                    raise RuntimeError("Pick an audio file for Replace/Mix mode (Section 2).")
                new_audio = AudioFileClip(apath)
                opened_clips.append(new_audio)
                offset = max(0.0, float(self.aud_offset.get() or 0))
                remaining = max(0.1, clip.duration - offset)
                if new_audio.duration < remaining:
                    new_audio = afx.audio_loop(new_audio, duration=remaining)
                else:
                    new_audio = new_audio.subclip(0, remaining)
                new_audio = new_audio.set_start(offset).volumex(self.aud_new_vol.get() / 100.0)
                if mode == "mix" and clip.audio is not None:
                    orig = clip.audio.volumex(self.aud_orig_vol.get() / 100.0)
                    final_audio = CompositeAudioClip([orig, new_audio]).set_duration(clip.duration)
                else:
                    final_audio = CompositeAudioClip([new_audio]).set_duration(clip.duration)
                clip = clip.set_audio(final_audio)
                self.ed_log_msg(f"[AUDIO] Mode={mode}, file={Path(apath).name}")
            else:
                self.ed_log_msg("[AUDIO] Kept original audio.")

            layers = [clip]

            # ---- Text overlays ----
            for i, t in enumerate(self.text_slots, start=1):
                if not t['enabled'].get():
                    continue
                txt = t['text'].get().strip()
                if not txt:
                    continue
                img = render_text_image(w, h, txt, t['font_path'].get(), t['size'].get(), t['color'].get(),
                                         t['position'].get(), t['custom_x'].get(), t['custom_y'].get(), t['box_bg'].get())
                start = max(0.0, float(t['start'].get() or 0))
                dur = parse_duration_field(t['duration'].get(), max(0.1, clip.duration - start))
                layers.append(ImageClip(np.array(img)).set_start(start).set_duration(dur))
                self.ed_log_msg(f"[TEXT {i}] \"{txt[:30]}\" @ {t['position'].get()} from {start:.1f}s for {dur:.1f}s")

            # ---- Logo ----
            if self.logo_enabled.get():
                lpath = self.logo_path.get().strip()
                if lpath and Path(lpath).exists():
                    img = render_logo_image(w, h, lpath, self.logo_position.get(), self.logo_size_pct.get(),
                                             self.logo_opacity.get(), self.logo_margin.get())
                    start = max(0.0, float(self.logo_start.get() or 0))
                    dur = parse_duration_field(self.logo_duration.get(), max(0.1, clip.duration - start))
                    layers.append(ImageClip(np.array(img)).set_start(start).set_duration(dur))
                    self.ed_log_msg(f"[LOGO] {Path(lpath).name} @ {self.logo_position.get()}")
                else:
                    self.ed_log_msg("[WARNING] Logo enabled but no valid image picked — skipped.")

            # ---- Shape ----
            if self.shape_enabled.get():
                img = render_shape_image(w, h, self.shape_type.get(), self.shape_x.get(), self.shape_y.get(),
                                          self.shape_size.get(), self.shape_color.get(), self.shape_thickness.get(),
                                          self.shape_filled.get())
                start = max(0.0, float(self.shape_start.get() or 0))
                dur = parse_duration_field(self.shape_duration.get(), max(0.1, clip.duration - start))
                layers.append(ImageClip(np.array(img)).set_start(start).set_duration(dur))
                self.ed_log_msg(f"[SHAPE] {self.shape_type.get()} @ ({self.shape_x.get()}%, {self.shape_y.get()}%)")

            composed = CompositeVideoClip(layers, size=(w, h)).set_duration(clip.duration)
            if clip.audio is not None:
                composed = composed.set_audio(clip.audio)

            # ---- Intro / Outro ----
            segments = [composed]
            if self.intro_enabled.get():
                intro_clip = self._build_card_clip(self.intro_mode.get(), self.intro_text.get(), self.intro_bg.get(),
                                                    self.intro_duration.get(), self.intro_clip_path.get(), w, h, fps)
                opened_clips.append(intro_clip)
                segments.insert(0, intro_clip)
                self.ed_log_msg("[INTRO] Added.")
            if self.outro_enabled.get():
                outro_clip = self._build_card_clip(self.outro_mode.get(), self.outro_text.get(), self.outro_bg.get(),
                                                    self.outro_duration.get(), self.outro_clip_path.get(), w, h, fps)
                opened_clips.append(outro_clip)
                segments.append(outro_clip)
                self.ed_log_msg("[OUTRO] Added.")

            final = concatenate_videoclips(segments, method="compose") if len(segments) > 1 else segments[0]

            self.edited_dir.mkdir(exist_ok=True)
            out_path = self.edited_dir / f"{Path(input_path).stem}_edited.mp4"
            self.ed_log_msg(f"[EXPORT] Rendering -> {out_path.name} (this can take a while, watch the terminal)...")
            final.write_videofile(str(out_path), codec="libx264", audio_codec="aac", fps=fps, preset="medium", threads=4)
            self.ed_log_msg(f"[DONE] Saved: {out_path}")
            messagebox.showinfo("Export Complete", f"Saved to:\n{out_path}")

        except Exception as e:
            self.ed_log_msg(f"[ERROR] {e}")
            messagebox.showerror("Export Failed", str(e))
        finally:
            for oc in opened_clips:
                try:
                    oc.close()
                except Exception:
                    pass
            self.ed_apply_btn.config(state=tk.NORMAL)


if __name__ == '__main__':
    _set_dpi_awareness()
    root = tk.Tk()
    _sync_tk_scaling(root)
    app = AllInOneVideoStudio(root)
    root.mainloop()