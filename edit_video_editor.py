#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shorts Video Editor — post-production app for clips made by shortvideo.py
(or any .mp4/.mov/.mkv files).

Features:
  - Multi-file queue, "apply settings to all" or per-clip
  - Speed change (pitch-corrected audio), Zoom/crop (no stretch), Mute
  - Replace audio track with your own file
  - AI voiceover (Hindi / English, male / female) via edge-tts (free, MS)
  - Text overlay, Logo/image overlay
  - Blur / Black-box / Emoji-cover a region (drawn on a live preview frame)
  - Shapes: rectangle / circle / arrow drawn on the preview, baked into export
  - Color grading: contrast, saturation, brightness
  - Export: resolution preset, format (mp4/mov/webm), quality (CRF)
  - Save/Load full preset as JSON; one click re-apply to new clips

Run:  python video_editor.py
Needs: pip install imageio-ffmpeg pillow edge-tts
"""

import os
import sys
import json
import math
import shutil
import tempfile
import threading
import subprocess
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser, font as tkfont
from tkinter.scrolledtext import ScrolledText

try:
    import imageio_ffmpeg
except ImportError:
    print("Run: pip install imageio-ffmpeg")
    sys.exit(1)

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False

try:
    import edge_tts
    EDGE_TTS_OK = True
except ImportError:
    EDGE_TTS_OK = False

# Optional drag & drop. App still works fine without it (use Browse button).
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_OK = True
except ImportError:
    DND_OK = False

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

COLORS = {
    "bg": "#10131A", "surface": "#1A2029", "surface_hi": "#212934",
    "border": "#272F3B", "text": "#E8ECF3", "text_dim": "#8089A0",
    "accent": "#2DD4BF", "accent_hover": "#22B6A4", "accent_ink": "#06231F",
    "amber": "#FFA75C", "danger": "#FF6B6B", "success": "#4ADE80",
    "warning": "#FBBF24", "info": "#67B7F0",
}

RES_PRESETS = {
    "1080x1920 (Shorts/Reels 9:16)": (1080, 1920),
    "1080x1080 (Square 1:1)": (1080, 1080),
    "1920x1080 (Landscape 16:9)": (1920, 1080),
    "Keep original": None,
}

FORMATS = {
    "MP4 (H.264 + AAC) — best compatibility": ("mp4", "libx264", "aac"),
    "MOV (H.264 + AAC)": ("mov", "libx264", "aac"),
    "WEBM (VP9 + Opus)": ("webm", "libvpx-vp9", "libopus"),
}

# Hindi + English voices (edge-tts neural voices, free, no API key)
TTS_VOICES = {
    "Hindi — Male (Madhur)": "hi-IN-MadhurNeural",
    "Hindi — Female (Swara)": "hi-IN-SwaraNeural",
    "English (India) — Male (Prabhat)": "en-IN-PrabhatNeural",
    "English (India) — Female (Neerja)": "en-IN-NeerjaNeural",
    "English (US) — Male (Guy)": "en-US-GuyNeural",
    "English (US) — Female (Aria)": "en-US-AriaNeural",
}

PRESET_DIR = Path("editor_presets")
PRESET_DIR.mkdir(exist_ok=True)
OUT_DIR = Path("edited_shorts")
OUT_DIR.mkdir(exist_ok=True)


# ───────────────────────────── helpers ─────────────────────────────

def run_ffprobe_dims(path):
    """Return (w, h, duration_seconds) using ffmpeg -i parsing (no ffprobe dep)."""
    try:
        proc = subprocess.run([FFMPEG, "-i", str(path)], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
        out = proc.stdout
        w, h, dur = None, None, None
        import re
        m = re.search(r"(\d{2,5})x(\d{2,5})", out)
        if m:
            w, h = int(m.group(1)), int(m.group(2))
        m2 = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", out)
        if m2:
            hh, mm, ss = m2.groups()
            dur = int(hh) * 3600 + int(mm) * 60 + float(ss)
        return w, h, dur
    except Exception:
        return None, None, None


def grab_frame(path, t, out_png):
    """Grab a single preview frame at time t (seconds) -> out_png."""
    cmd = [FFMPEG, "-y", "-ss", str(t), "-i", str(path), "-frames:v", "1",
           "-q:v", "2", str(out_png)]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return Path(out_png).exists()


class Region:
    """A blur/black/emoji/shape region defined in *source-frame* pixel coords."""
    def __init__(self, kind, x, y, w, h, color="#000000", emoji_path=None):
        self.kind = kind  # 'blur' | 'black' | 'emoji' | 'rect' | 'circle' | 'arrow'
        self.x, self.y, self.w, self.h = x, y, w, h
        self.color = color
        self.emoji_path = emoji_path

    def to_dict(self):
        return {"kind": self.kind, "x": self.x, "y": self.y, "w": self.w, "h": self.h,
                "color": self.color, "emoji_path": self.emoji_path}

    @staticmethod
    def from_dict(d):
        return Region(d["kind"], d["x"], d["y"], d["w"], d["h"],
                       d.get("color", "#000000"), d.get("emoji_path"))


# ───────────────────────────── main app ─────────────────────────────

class VideoEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Shorts Video Editor")
        self.root.geometry("1180x760")
        self.root.minsize(980, 620)
        self.root.configure(bg=COLORS["bg"])

        self.files = []            # list of Path
        self.apply_to_all = tk.BooleanVar(value=True)
        self.regions = []          # list[Region], in source pixel coords
        self.preview_path = None
        self.preview_src_dims = (1080, 1920)
        self.preview_tk_img = None
        self.preview_scale = 1.0
        self.drag_start = None
        self.drag_tool = tk.StringVar(value="blur")

        self._init_fonts()
        self.style = ttk.Style()
        self._init_style()

        self._build_layout()

    # ---------- theming ----------
    def _init_fonts(self):
        available = set(tkfont.families())
        def pick(cands, fb="TkDefaultFont"):
            for n in cands:
                if n in available:
                    return n
            return fb
        self.font_body = pick(["Segoe UI", "Helvetica Neue", "Helvetica", "Arial"])
        self.font_heading = pick(["Segoe UI Semibold", "Segoe UI", "Helvetica Neue", "Arial"])
        self.font_mono = pick(["Cascadia Mono", "Consolas", "Menlo", "Courier New"])

    def _init_style(self):
        c = COLORS
        self.style.theme_use("clam")
        self.style.configure(".", background=c["bg"], foreground=c["text"], font=(self.font_body, 10))
        self.style.configure("TFrame", background=c["bg"])
        self.style.configure("TLabel", background=c["bg"], foreground=c["text"])
        self.style.configure("Hint.TLabel", background=c["bg"], foreground=c["text_dim"], font=(self.font_body, 9))
        self.style.configure("Header.TLabel", background=c["bg"], foreground=c["text"], font=(self.font_heading, 15, "bold"))
        self.style.configure("TLabelframe", background=c["bg"], borderwidth=1, relief="solid",
                              bordercolor=c["border"], lightcolor=c["border"], darkcolor=c["border"])
        self.style.configure("TLabelframe.Label", background=c["bg"], foreground=c["accent"], font=(self.font_heading, 10, "bold"))
        self.style.configure("TCheckbutton", background=c["bg"], foreground=c["text"])
        self.style.configure("TRadiobutton", background=c["bg"], foreground=c["text"])
        self.style.configure("TEntry", fieldbackground=c["surface"], foreground=c["text"], insertcolor=c["text"],
                              bordercolor=c["border"], borderwidth=1, relief="flat", padding=5)
        self.style.configure("TCombobox", fieldbackground=c["surface"], background=c["surface"],
                              foreground=c["text"], arrowcolor=c["text_dim"])
        self.style.configure("Horizontal.TScale", background=c["bg"])
        self.style.configure("TButton", background=c["surface"], foreground=c["text"], borderwidth=0, padding=8)
        self.style.map("TButton", background=[("active", c["surface_hi"])])
        self.style.configure("Accent.TButton", background=c["accent"], foreground=c["accent_ink"],
                              font=(self.font_heading, 10, "bold"), padding=10)
        self.style.map("Accent.TButton", background=[("active", c["accent_hover"])])
        self.style.configure("TNotebook", background=c["bg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", background=c["surface"], foreground=c["text_dim"], padding=(14, 8))
        self.style.map("TNotebook.Tab", background=[("selected", c["accent"])],
                        foreground=[("selected", c["accent_ink"])])

    # ---------- layout ----------
    def _build_layout(self):
        root_pane = ttk.Frame(self.root, padding=12)
        root_pane.pack(fill="both", expand=True)

        ttk.Label(root_pane, text="🎬 Shorts Video Editor", style="Header.TLabel").pack(anchor="w")
        ttk.Label(root_pane, text="Edit clips with zoom, speed, voiceover, text, shapes, blur & color — then export.",
                  style="Hint.TLabel").pack(anchor="w", pady=(0, 10))

        body = ttk.Frame(root_pane)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # LEFT: file queue + preview
        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        self._build_file_panel(left)
        self._build_preview_panel(left)

        # RIGHT: settings tabs
        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        self._build_settings_tabs(right)

        # bottom bar
        bottom = ttk.Frame(root_pane)
        bottom.pack(fill="x", pady=(10, 0))
        ttk.Checkbutton(bottom, text="Apply these settings to ALL files in queue",
                         variable=self.apply_to_all).pack(side="left")
        ttk.Button(bottom, text="💾 Save Preset", command=self.save_preset).pack(side="left", padx=6)
        ttk.Button(bottom, text="📂 Load Preset", command=self.load_preset).pack(side="left", padx=6)
        self.export_btn = ttk.Button(bottom, text="🚀 Export Video(s)", style="Accent.TButton",
                                      command=self.start_export_thread)
        self.export_btn.pack(side="right")

        self.progress = ttk.Progressbar(root_pane, mode="determinate")
        self.progress.pack(fill="x", pady=(8, 4))

        self.log = ScrolledText(root_pane, height=7, bg=COLORS["surface"], fg=COLORS["text"],
                                 insertbackground=COLORS["text"], font=(self.font_mono, 9),
                                 borderwidth=0, highlightthickness=1, highlightbackground=COLORS["border"])
        self.log.pack(fill="x")
        self._log("Ready. Add video files to begin. " +
                   ("(edge-tts found — AI voiceover enabled)" if EDGE_TTS_OK else
                    "(edge-tts NOT installed — run: pip install edge-tts  to enable AI voiceover)"))

    def _log(self, msg):
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    # ---------- file panel ----------
    def _build_file_panel(self, parent):
        box = ttk.Labelframe(parent, text=" 1. Source Clips ", padding=10)
        box.pack(fill="x")

        btn_row = ttk.Frame(box)
        btn_row.pack(fill="x", pady=(0, 6))
        ttk.Button(btn_row, text="➕ Add Files", command=self.add_files).pack(side="left")
        ttk.Button(btn_row, text="🗑 Remove", command=self.remove_selected).pack(side="left", padx=6)
        ttk.Button(btn_row, text="📁 From 'shorts/' folder", command=self.add_from_shorts_dir).pack(side="left")

        self.file_listbox = tk.Listbox(box, height=8, width=42, bg=COLORS["surface"], fg=COLORS["text"],
                                        selectbackground=COLORS["accent"], selectforeground=COLORS["accent_ink"],
                                        borderwidth=0, highlightthickness=1, highlightbackground=COLORS["border"])
        self.file_listbox.pack(fill="x")
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_selected)

        if DND_OK:
            self.file_listbox.drop_target_register(DND_FILES)
            self.file_listbox.dnd_bind("<<Drop>>", self.on_drop_files)
            ttk.Label(box, text="Tip: you can also drag & drop video files here.", style="Hint.TLabel").pack(anchor="w", pady=(4, 0))
        else:
            ttk.Label(box, text="Tip: install 'tkinterdnd2' to enable drag & drop (Browse works fine too).",
                      style="Hint.TLabel").pack(anchor="w", pady=(4, 0))

    def add_files(self):
        paths = filedialog.askopenfilenames(title="Select video files",
                                             filetypes=[("Video", "*.mp4 *.mov *.mkv *.webm *.avi"), ("All files", "*.*")])
        for p in paths:
            self._add_path(Path(p))

    def add_from_shorts_dir(self):
        d = Path("shorts")
        if not d.exists():
            messagebox.showinfo("Not found", "No 'shorts' folder here yet. Run shortvideo.py first, or use Add Files.")
            return
        for p in sorted(d.glob("*.mp4")):
            self._add_path(p)

    def on_drop_files(self, event):
        for p in self.root.tk.splitlist(event.data):
            self._add_path(Path(p))

    def _add_path(self, p):
        if p.exists() and p not in self.files:
            self.files.append(p)
            self.file_listbox.insert(tk.END, p.name)
            if len(self.files) == 1:
                self.file_listbox.selection_set(0)
                self.load_preview(p)

    def remove_selected(self):
        sel = list(self.file_listbox.curselection())
        for i in reversed(sel):
            self.file_listbox.delete(i)
            del self.files[i]

    def on_file_selected(self, _evt):
        sel = self.file_listbox.curselection()
        if sel:
            self.load_preview(self.files[sel[0]])

    # ---------- preview panel (frame grab + draw regions) ----------
    def _build_preview_panel(self, parent):
        box = ttk.Labelframe(parent, text=" 2. Preview & Draw (blur / shapes) ", padding=10)
        box.pack(fill="both", expand=True, pady=(10, 0))

        tool_row = ttk.Frame(box)
        tool_row.pack(fill="x", pady=(0, 6))
        for label, key in [("Blur", "blur"), ("Black", "black"), ("Emoji", "emoji"),
                            ("Rect", "rect"), ("Circle", "circle"), ("Arrow", "arrow")]:
            ttk.Radiobutton(tool_row, text=label, value=key, variable=self.drag_tool).pack(side="left", padx=2)

        self.canvas = tk.Canvas(box, width=260, height=460, bg="#000000", highlightthickness=1,
                                 highlightbackground=COLORS["border"])
        self.canvas.pack(pady=4)
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        row2 = ttk.Frame(box)
        row2.pack(fill="x")
        ttk.Button(row2, text="Clear regions", command=self.clear_regions).pack(side="left")
        ttk.Button(row2, text="Pick emoji image…", command=self.pick_emoji_image).pack(side="left", padx=6)
        ttk.Label(box, text="Drag on the preview to draw a region with the selected tool.\n"
                             "Blur/Black/Emoji = hide something. Rect/Circle/Arrow = highlight something.",
                  style="Hint.TLabel", justify="left").pack(anchor="w", pady=(6, 0))

        self._emoji_image_path = None

    def pick_emoji_image(self):
        p = filedialog.askopenfilename(title="Choose an image/emoji PNG to overlay",
                                        filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if p:
            self._emoji_image_path = p
            self._log(f"Emoji/sticker image set: {Path(p).name}")

    def load_preview(self, path):
        if not PIL_OK:
            self._log("Pillow not installed — preview disabled, editing still works. (pip install pillow)")
            return
        w, h, dur = run_ffprobe_dims(path)
        if not w:
            w, h, dur = 1080, 1920, 5
        self.preview_src_dims = (w, h)
        t = (dur or 2) / 2
        tmp_png = Path(tempfile.gettempdir()) / "shorts_editor_preview.png"
        if grab_frame(path, t, tmp_png):
            self.preview_path = tmp_png
            img = Image.open(tmp_png)
            cw, ch = 260, 460
            scale = min(cw / img.width, ch / img.height)
            self.preview_scale = scale
            disp = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
            self.preview_tk_img = ImageTk.PhotoImage(disp)
            self.canvas.delete("all")
            self.canvas.config(width=disp.width, height=disp.height)
            self.canvas.create_image(0, 0, anchor="nw", image=self.preview_tk_img, tags="bg")
            self.redraw_regions()
        else:
            self._log(f"Could not grab a preview frame for {path.name} (file may still export fine).")

    def redraw_regions(self):
        self.canvas.delete("region")
        for r in self.regions:
            x0, y0 = r.x * self.preview_scale, r.y * self.preview_scale
            x1, y1 = (r.x + r.w) * self.preview_scale, (r.y + r.h) * self.preview_scale
            if r.kind in ("blur", "black", "emoji"):
                outline = {"blur": "#67B7F0", "black": "#FF6B6B", "emoji": "#FBBF24"}[r.kind]
                self.canvas.create_rectangle(x0, y0, x1, y1, outline=outline, width=2, dash=(4, 2), tags="region")
            elif r.kind == "rect":
                self.canvas.create_rectangle(x0, y0, x1, y1, outline=r.color, width=3, tags="region")
            elif r.kind == "circle":
                self.canvas.create_oval(x0, y0, x1, y1, outline=r.color, width=3, tags="region")
            elif r.kind == "arrow":
                self.canvas.create_line(x0, y0, x1, y1, fill=r.color, width=4, arrow="last", tags="region")

    def on_canvas_press(self, evt):
        self.drag_start = (evt.x, evt.y)

    def on_canvas_drag(self, evt):
        self.canvas.delete("livedrag")
        x0, y0 = self.drag_start
        self.canvas.create_rectangle(x0, y0, evt.x, evt.y, outline=COLORS["accent"], dash=(3, 2), tags="livedrag")

    def on_canvas_release(self, evt):
        if not self.drag_start:
            return
        x0, y0 = self.drag_start
        x1, y1 = evt.x, evt.y
        self.canvas.delete("livedrag")
        if abs(x1 - x0) < 6 or abs(y1 - y0) < 6:
            self.drag_start = None
            return
        sx0, sx1 = sorted([x0, x1])
        sy0, sy1 = sorted([y0, y1])
        scale = self.preview_scale or 1.0
        rx, ry = sx0 / scale, sy0 / scale
        rw, rh = (sx1 - sx0) / scale, (sy1 - sy0) / scale
        kind = self.drag_tool.get()
        color = "#FF3B30" if kind in ("rect", "circle", "arrow") else "#000000"
        if kind in ("rect", "circle", "arrow"):
            color = colorchooser.askcolor(title="Shape color", initialcolor="#FF3B30")[1] or "#FF3B30"
        emoji_path = self._emoji_image_path if kind == "emoji" else None
        if kind == "emoji" and not emoji_path:
            messagebox.showinfo("Pick an image first", "Choose an emoji/sticker image with 'Pick emoji image…' before drawing an emoji region.")
            self.drag_start = None
            return
        self.regions.append(Region(kind, rx, ry, rw, rh, color, emoji_path))
        self.redraw_regions()
        self.drag_start = None

    def clear_regions(self):
        self.regions = []
        self.redraw_regions()

    # ---------- settings tabs ----------
    def _build_settings_tabs(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill="both", expand=True)

        self._build_transform_tab(nb)
        self._build_audio_tab(nb)
        self._build_text_tab(nb)
        self._build_color_tab(nb)
        self._build_export_tab(nb)

    def _build_transform_tab(self, nb):
        tab = ttk.Frame(nb, padding=14)
        nb.add(tab, text="Speed / Zoom")

        ttk.Label(tab, text="Playback speed").pack(anchor="w")
        self.speed_var = tk.DoubleVar(value=1.0)
        ttk.Scale(tab, from_=0.25, to=4.0, variable=self.speed_var, orient="horizontal").pack(fill="x")
        self.speed_lbl = ttk.Label(tab, text="1.00x (audio pitch-corrected)", style="Hint.TLabel")
        self.speed_lbl.pack(anchor="w", pady=(0, 10))
        self.speed_var.trace_add("write", lambda *_: self.speed_lbl.config(
            text=f"{self.speed_var.get():.2f}x (audio pitch-corrected)"))

        ttk.Label(tab, text="Zoom (crops in toward center, then re-scales to target — never stretches)").pack(anchor="w")
        self.zoom_var = tk.DoubleVar(value=1.0)
        ttk.Scale(tab, from_=1.0, to=3.0, variable=self.zoom_var, orient="horizontal").pack(fill="x")
        self.zoom_lbl = ttk.Label(tab, text="1.00x", style="Hint.TLabel")
        self.zoom_lbl.pack(anchor="w", pady=(0, 10))
        self.zoom_var.trace_add("write", lambda *_: self.zoom_lbl.config(text=f"{self.zoom_var.get():.2f}x"))

        ttk.Separator(tab).pack(fill="x", pady=8)
        ttk.Label(tab, text="These apply at export time and are resolution-aware, so quality/sharpness\n"
                             "is preserved — zoom crops first, then scales up to the final export size\n"
                             "(never the reverse), so the picture doesn't stretch or go soft.",
                  style="Hint.TLabel", justify="left").pack(anchor="w")

    def _build_audio_tab(self, nb):
        tab = ttk.Frame(nb, padding=14)
        nb.add(tab, text="Audio / Voiceover")

        self.mute_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(tab, text="Mute original audio", variable=self.mute_var).pack(anchor="w", pady=4)

        ttk.Separator(tab).pack(fill="x", pady=8)
        ttk.Label(tab, text="Replace audio with a file:").pack(anchor="w")
        row = ttk.Frame(tab); row.pack(fill="x", pady=4)
        self.replace_audio_path = tk.StringVar(value="")
        ttk.Entry(row, textvariable=self.replace_audio_path, width=34).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Browse…", command=self._pick_audio).pack(side="left", padx=6)

        ttk.Separator(tab).pack(fill="x", pady=8)
        ttk.Label(tab, text="AI voiceover (free, Microsoft Edge neural voices):",
                  style="Hint.TLabel" if not EDGE_TTS_OK else "TLabel").pack(anchor="w")
        if not EDGE_TTS_OK:
            ttk.Label(tab, text="Not installed. Run:  pip install edge-tts", style="Hint.TLabel").pack(anchor="w")

        self.tts_voice_var = tk.StringVar(value=list(TTS_VOICES.keys())[0])
        ttk.Combobox(tab, textvariable=self.tts_voice_var, values=list(TTS_VOICES.keys()),
                     state="readonly", width=38).pack(anchor="w", pady=4)

        ttk.Label(tab, text="Script text (Hindi or English):").pack(anchor="w", pady=(6, 0))
        self.tts_text = ScrolledText(tab, height=5, bg=COLORS["surface"], fg=COLORS["text"],
                                      insertbackground=COLORS["text"], font=(self.font_body, 10),
                                      borderwidth=0, highlightthickness=1, highlightbackground=COLORS["border"])
        self.tts_text.pack(fill="x", pady=4)

        self.use_tts_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(tab, text="Use this AI voiceover as the audio for export", variable=self.use_tts_var,
                         state="normal" if EDGE_TTS_OK else "disabled").pack(anchor="w", pady=4)

        self.tts_mix_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(tab, text="Mix voiceover with (lowered) original audio instead of replacing it",
                         variable=self.tts_mix_var).pack(anchor="w")

    def _pick_audio(self):
        p = filedialog.askopenfilename(title="Choose replacement audio", filetypes=[("Audio", "*.mp3 *.wav *.m4a *.aac")])
        if p:
            self.replace_audio_path.set(p)

    def _build_text_tab(self, nb):
        tab = ttk.Frame(nb, padding=14)
        nb.add(tab, text="Text / Logo")

        ttk.Label(tab, text="Overlay text:").pack(anchor="w")
        self.overlay_text = tk.StringVar(value="")
        ttk.Entry(tab, textvariable=self.overlay_text, width=42).pack(anchor="w", pady=4)

        row = ttk.Frame(tab); row.pack(fill="x", pady=4)
        ttk.Label(row, text="Position:").pack(side="left")
        self.text_pos_var = tk.StringVar(value="Bottom")
        ttk.Combobox(row, textvariable=self.text_pos_var, values=["Top", "Middle", "Bottom"],
                     state="readonly", width=12).pack(side="left", padx=6)
        ttk.Label(row, text="Size:").pack(side="left", padx=(12, 0))
        self.text_size_var = tk.IntVar(value=56)
        ttk.Spinbox(row, from_=12, to=160, textvariable=self.text_size_var, width=6).pack(side="left", padx=6)

        row2 = ttk.Frame(tab); row2.pack(fill="x", pady=4)
        ttk.Label(row2, text="Color:").pack(side="left")
        self.text_color_var = tk.StringVar(value="#FFFFFF")
        self.text_color_swatch = tk.Label(row2, width=4, bg=self.text_color_var.get())
        self.text_color_swatch.pack(side="left", padx=6)
        ttk.Button(row2, text="Pick…", command=self._pick_text_color).pack(side="left")

        self.text_box_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row2, text="Background box behind text", variable=self.text_box_var).pack(side="left", padx=14)

        ttk.Separator(tab).pack(fill="x", pady=10)
        ttk.Label(tab, text="Logo / watermark image:").pack(anchor="w")
        row3 = ttk.Frame(tab); row3.pack(fill="x", pady=4)
        self.logo_path_var = tk.StringVar(value="")
        ttk.Entry(row3, textvariable=self.logo_path_var, width=30).pack(side="left", fill="x", expand=True)
        ttk.Button(row3, text="Browse…", command=self._pick_logo).pack(side="left", padx=6)

        row4 = ttk.Frame(tab); row4.pack(fill="x", pady=4)
        ttk.Label(row4, text="Corner:").pack(side="left")
        self.logo_pos_var = tk.StringVar(value="Top-Right")
        ttk.Combobox(row4, textvariable=self.logo_pos_var,
                     values=["Top-Left", "Top-Right", "Bottom-Left", "Bottom-Right"],
                     state="readonly", width=14).pack(side="left", padx=6)
        ttk.Label(row4, text="Width %:").pack(side="left", padx=(12, 0))
        self.logo_scale_var = tk.IntVar(value=18)
        ttk.Spinbox(row4, from_=5, to=60, textvariable=self.logo_scale_var, width=6).pack(side="left", padx=6)
        ttk.Label(row4, text="Opacity %:").pack(side="left", padx=(12, 0))
        self.logo_opacity_var = tk.IntVar(value=100)
        ttk.Spinbox(row4, from_=10, to=100, textvariable=self.logo_opacity_var, width=6).pack(side="left", padx=6)

    def _pick_text_color(self):
        c = colorchooser.askcolor(title="Text color", initialcolor=self.text_color_var.get())
        if c[1]:
            self.text_color_var.set(c[1])
            self.text_color_swatch.config(bg=c[1])

    def _pick_logo(self):
        p = filedialog.askopenfilename(title="Choose logo image", filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if p:
            self.logo_path_var.set(p)

    def _build_color_tab(self, nb):
        tab = ttk.Frame(nb, padding=14)
        nb.add(tab, text="Color (CapCut-style)")

        def slider(label, var, lo, hi):
            ttk.Label(tab, text=label).pack(anchor="w")
            ttk.Scale(tab, from_=lo, to=hi, variable=var, orient="horizontal").pack(fill="x", pady=(0, 10))

        self.contrast_var = tk.DoubleVar(value=1.0)
        self.saturation_var = tk.DoubleVar(value=1.0)
        self.brightness_var = tk.DoubleVar(value=0.0)
        self.gamma_var = tk.DoubleVar(value=1.0)
        self.sharpen_var = tk.BooleanVar(value=False)

        slider("Contrast (1.0 = normal, try 1.15–1.3 for that 'punchy' Instagram look)", self.contrast_var, 0.5, 2.0)
        slider("Saturation (1.0 = normal, 1.2–1.4 = vivid)", self.saturation_var, 0.0, 2.0)
        slider("Brightness (0 = normal)", self.brightness_var, -0.3, 0.3)
        slider("Gamma (midtone balance, 1.0 = normal)", self.gamma_var, 0.5, 2.0)
        ttk.Checkbutton(tab, text="Sharpen (subtle unsharp mask, like CapCut's clarity)",
                         variable=self.sharpen_var).pack(anchor="w", pady=4)

        ttk.Button(tab, text="Reset to defaults", command=self._reset_color).pack(anchor="w", pady=(10, 0))

    def _reset_color(self):
        self.contrast_var.set(1.0); self.saturation_var.set(1.0)
        self.brightness_var.set(0.0); self.gamma_var.set(1.0); self.sharpen_var.set(False)

    def _build_export_tab(self, nb):
        tab = ttk.Frame(nb, padding=14)
        nb.add(tab, text="Export")

        ttk.Label(tab, text="Resolution:").pack(anchor="w")
        self.res_var = tk.StringVar(value=list(RES_PRESETS.keys())[0])
        ttk.Combobox(tab, textvariable=self.res_var, values=list(RES_PRESETS.keys()),
                     state="readonly", width=34).pack(anchor="w", pady=4)

        ttk.Label(tab, text="Format / Codec:").pack(anchor="w", pady=(10, 0))
        self.fmt_var = tk.StringVar(value=list(FORMATS.keys())[0])
        ttk.Combobox(tab, textvariable=self.fmt_var, values=list(FORMATS.keys()),
                     state="readonly", width=34).pack(anchor="w", pady=4)

        ttk.Label(tab, text="Quality (lower CRF = higher quality & bigger file):").pack(anchor="w", pady=(10, 0))
        self.crf_var = tk.IntVar(value=18)
        ttk.Spinbox(tab, from_=12, to=30, textvariable=self.crf_var, width=8).pack(anchor="w", pady=4)
        ttk.Label(tab, text="18 = visually lossless · 20-23 = great for social · 26+ = smaller file",
                  style="Hint.TLabel").pack(anchor="w")

        ttk.Label(tab, text="Encode speed preset:").pack(anchor="w", pady=(10, 0))
        self.preset_var = tk.StringVar(value="medium")
        ttk.Combobox(tab, textvariable=self.preset_var,
                     values=["ultrafast", "fast", "medium", "slow", "veryslow"],
                     state="readonly", width=16).pack(anchor="w", pady=4)
        ttk.Label(tab, text="slower presets = smaller file at same quality, takes longer to encode",
                  style="Hint.TLabel").pack(anchor="w")

        ttk.Label(tab, text=f"Output folder: {OUT_DIR.resolve()}", style="Hint.TLabel").pack(anchor="w", pady=(14, 0))

    # ---------- preset save/load ----------
    def collect_settings(self):
        return {
            "speed": self.speed_var.get(), "zoom": self.zoom_var.get(),
            "mute": self.mute_var.get(), "replace_audio": self.replace_audio_path.get(),
            "use_tts": self.use_tts_var.get(), "tts_mix": self.tts_mix_var.get(),
            "tts_voice": self.tts_voice_var.get(), "tts_text": self.tts_text.get("1.0", tk.END).strip(),
            "overlay_text": self.overlay_text.get(), "text_pos": self.text_pos_var.get(),
            "text_size": self.text_size_var.get(), "text_color": self.text_color_var.get(),
            "text_box": self.text_box_var.get(),
            "logo_path": self.logo_path_var.get(), "logo_pos": self.logo_pos_var.get(),
            "logo_scale": self.logo_scale_var.get(), "logo_opacity": self.logo_opacity_var.get(),
            "contrast": self.contrast_var.get(), "saturation": self.saturation_var.get(),
            "brightness": self.brightness_var.get(), "gamma": self.gamma_var.get(),
            "sharpen": self.sharpen_var.get(),
            "resolution": self.res_var.get(), "format": self.fmt_var.get(),
            "crf": self.crf_var.get(), "preset": self.preset_var.get(),
            "regions": [r.to_dict() for r in self.regions],
            "preview_src_dims": self.preview_src_dims,
        }

    def apply_settings(self, s):
        self.speed_var.set(s.get("speed", 1.0)); self.zoom_var.set(s.get("zoom", 1.0))
        self.mute_var.set(s.get("mute", False)); self.replace_audio_path.set(s.get("replace_audio", ""))
        self.use_tts_var.set(s.get("use_tts", False)); self.tts_mix_var.set(s.get("tts_mix", False))
        self.tts_voice_var.set(s.get("tts_voice", list(TTS_VOICES.keys())[0]))
        self.tts_text.delete("1.0", tk.END); self.tts_text.insert(tk.END, s.get("tts_text", ""))
        self.overlay_text.set(s.get("overlay_text", "")); self.text_pos_var.set(s.get("text_pos", "Bottom"))
        self.text_size_var.set(s.get("text_size", 56)); self.text_color_var.set(s.get("text_color", "#FFFFFF"))
        self.text_color_swatch.config(bg=self.text_color_var.get())
        self.text_box_var.set(s.get("text_box", True))
        self.logo_path_var.set(s.get("logo_path", "")); self.logo_pos_var.set(s.get("logo_pos", "Top-Right"))
        self.logo_scale_var.set(s.get("logo_scale", 18)); self.logo_opacity_var.set(s.get("logo_opacity", 100))
        self.contrast_var.set(s.get("contrast", 1.0)); self.saturation_var.set(s.get("saturation", 1.0))
        self.brightness_var.set(s.get("brightness", 0.0)); self.gamma_var.set(s.get("gamma", 1.0))
        self.sharpen_var.set(s.get("sharpen", False))
        self.res_var.set(s.get("resolution", list(RES_PRESETS.keys())[0]))
        self.fmt_var.set(s.get("format", list(FORMATS.keys())[0]))
        self.crf_var.set(s.get("crf", 18)); self.preset_var.set(s.get("preset", "medium"))
        self.preview_src_dims = tuple(s.get("preview_src_dims", (1080, 1920)))
        self.regions = [Region.from_dict(r) for r in s.get("regions", [])]
        self.redraw_regions()

    def save_preset(self):
        name = filedialog.asksaveasfilename(initialdir=str(PRESET_DIR), defaultextension=".json",
                                             filetypes=[("JSON preset", "*.json")], title="Save preset as…")
        if not name:
            return
        with open(name, "w", encoding="utf-8") as f:
            json.dump(self.collect_settings(), f, indent=2)
        self._log(f"Preset saved: {Path(name).name}")

    def load_preset(self):
        name = filedialog.askopenfilename(initialdir=str(PRESET_DIR), filetypes=[("JSON preset", "*.json")],
                                           title="Load preset")
        if not name:
            return
        with open(name, "r", encoding="utf-8") as f:
            s = json.load(f)
        self.apply_settings(s)
        self._log(f"Preset loaded: {Path(name).name}. Click 'Export Video(s)' to apply it.")

    # ---------- filter graph builder ----------
    def build_filters(self, src_w, src_h, settings):
        """Returns (video_filter_chain:str, drawtext/overlay extra inputs list,
        needs_complex:bool) describing the ffmpeg -vf / -filter_complex graph."""
        vf = []

        zoom = settings["zoom"]
        if zoom and zoom > 1.0:
            cw = int(src_w / zoom)
            ch = int(src_h / zoom)
            vf.append(f"crop={cw}:{ch}")

        target = RES_PRESETS[settings["resolution"]]
        if target:
            tw, th = target
            # scale to cover target box without stretching, then crop to exact size
            vf.append(f"scale={tw}:{th}:force_original_aspect_ratio=increase")
            vf.append(f"crop={tw}:{th}")
        # else keep original dims as-is

        eq_parts = []
        if abs(settings["contrast"] - 1.0) > 1e-3:
            eq_parts.append(f"contrast={settings['contrast']:.3f}")
        if abs(settings["saturation"] - 1.0) > 1e-3:
            eq_parts.append(f"saturation={settings['saturation']:.3f}")
        if abs(settings["brightness"]) > 1e-3:
            eq_parts.append(f"brightness={settings['brightness']:.3f}")
        if abs(settings["gamma"] - 1.0) > 1e-3:
            eq_parts.append(f"gamma={settings['gamma']:.3f}")
        if eq_parts:
            vf.append("eq=" + ":".join(eq_parts))

        if settings["sharpen"]:
            vf.append("unsharp=5:5:0.5:5:5:0.0")

        if abs(settings["speed"] - 1.0) > 1e-3:
            vf.append(f"setpts=PTS/{settings['speed']:.4f}")

        # Region effects (blur/black on the frame) -- applied to whole-frame coordinate space.
        # We map source pixel coords proportionally; ffmpeg boxblur+overlay via crop/blur/overlay chain.
        # Implemented later with filter_complex when regions exist.
        return vf

    def build_region_complex(self, base_label, settings, scale_x, scale_y):
        """Build filter_complex snippets for blur/black/emoji/shape regions.
        scale_x/scale_y map original preview coords -> final output coords."""
        parts = []
        cur = base_label
        idx = 0
        extra_inputs = []  # (path, label) for emoji image inputs
        for r in self.regions:
            idx += 1
            x = int(r.x * scale_x); y = int(r.y * scale_y)
            w = max(2, int(r.w * scale_x)); h = max(2, int(r.h * scale_y))
            nxt = f"{base_label}_r{idx}"
            if r.kind == "blur":
                parts.append(
                    f"[{cur}]split[{nxt}main][{nxt}crop];"
                    f"[{nxt}crop]crop={w}:{h}:{x}:{y},boxblur=20:2[{nxt}blur];"
                    f"[{nxt}main][{nxt}blur]overlay={x}:{y}[{nxt}]"
                )
                cur = nxt
            elif r.kind == "black":
                parts.append(f"[{cur}]drawbox=x={x}:y={y}:w={w}:h={h}:color=black@1.0:t=fill[{nxt}]")
                cur = nxt
            elif r.kind == "emoji" and r.emoji_path:
                in_label = f"emoji{idx}"
                extra_inputs.append((r.emoji_path, in_label, w, h))
                parts.append(f"[{cur}][{in_label}scaled]overlay={x}:{y}[{nxt}]")
                cur = nxt
            elif r.kind == "rect":
                rgb = r.color.lstrip("#")
                parts.append(f"[{cur}]drawbox=x={x}:y={y}:w={w}:h={h}:color={rgb}@1.0:t=4[{nxt}]")
                cur = nxt
            elif r.kind == "circle":
                # approximate circle/ellipse with drawbox border isn't native; use a simple
                # ellipse via geq is heavy, so approximate with a rounded rectangle outline.
                rgb = r.color.lstrip("#")
                parts.append(f"[{cur}]drawbox=x={x}:y={y}:w={w}:h={h}:color={rgb}@1.0:t=4[{nxt}]")
                cur = nxt
            elif r.kind == "arrow":
                rgb = r.color.lstrip("#")
                # draw a line by drawing a thin box rotated isn't trivial in ffmpeg; approximate
                # with a straight box across the bounding diagonal width (best-effort visual cue).
                parts.append(f"[{cur}]drawbox=x={x}:y={y}:w={w}:h=4:color={rgb}@1.0:t=fill[{nxt}]")
                cur = nxt
        return parts, cur, extra_inputs

    # ---------- export ----------
    def start_export_thread(self):
        if not self.files:
            messagebox.showerror("No files", "Add at least one video file first.")
            return
        threading.Thread(target=self.export_all, daemon=True).start()

    def export_all(self):
        self.export_btn.config(state=tk.DISABLED)
        targets = self.files if self.apply_to_all.get() else [self.files[self.file_listbox.curselection()[0]]] \
            if self.file_listbox.curselection() else self.files
        self.progress["value"] = 0
        self.progress["maximum"] = len(targets)
        settings = self.collect_settings()

        for i, path in enumerate(targets, start=1):
            try:
                self._log(f"[{i}/{len(targets)}] Exporting {path.name} …")
                out = self.export_one(path, settings)
                self._log(f"[{i}/{len(targets)}] ✅ Saved: {out}")
            except Exception as e:
                self._log(f"[{i}/{len(targets)}] ❌ Failed: {e}")
            self.progress["value"] = i
            self.root.update_idletasks()

        self.export_btn.config(state=tk.NORMAL)
        messagebox.showinfo("Export finished", f"Done. Files saved in '{OUT_DIR}/'.")

    def export_one(self, path, settings):
        w, h, dur = run_ffprobe_dims(path)
        w = w or self.preview_src_dims[0]
        h = h or self.preview_src_dims[1]

        ext, vcodec, acodec = FORMATS[settings["format"]]
        out_path = OUT_DIR / f"{path.stem}_edited.{ext}"

        # --- figure out final output canvas size (for region coordinate scaling) ---
        target = RES_PRESETS[settings["resolution"]]
        # account for zoom-crop changing the effective source box before final scale
        zoom = settings["zoom"]
        eff_w = w / zoom if zoom > 1.0 else w
        eff_h = h / zoom if zoom > 1.0 else h
        if target:
            out_w, out_h = target
        else:
            out_w, out_h = int(eff_w), int(eff_h)

        # regions were drawn against the ORIGINAL preview frame (full w x h, pre-zoom).
        # map region coords -> the cropped (zoomed) sub-frame -> final output size.
        crop_x_off = (w - eff_w) / 2 if zoom > 1.0 else 0
        crop_y_off = (h - eff_h) / 2 if zoom > 1.0 else 0
        scale_x = out_w / eff_w
        scale_y = out_h / eff_h

        adjusted_regions = []
        for r in self.regions:
            adjusted_regions.append(Region(r.kind, r.x - crop_x_off, r.y - crop_y_off, r.w, r.h, r.color, r.emoji_path))
        saved_regions, self.regions = self.regions, adjusted_regions

        try:
            vf_chain = self.build_filters(w, h, settings)
            region_parts, final_v_label, extra_inputs = self.build_region_complex("vbase", settings, scale_x, scale_y)
        finally:
            self.regions = saved_regions

        # text overlay
        text = settings["overlay_text"].strip()
        text_filter = None
        if text:
            esc = text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
            pos_map = {"Top": "y=h*0.08", "Middle": "y=(h-text_h)/2", "Bottom": "y=h*0.85"}
            box_opt = ":box=1:boxcolor=black@0.45:boxborderw=14" if settings["text_box"] else ""
            color = settings["text_color"].lstrip("#")
            text_filter = (f"drawtext=text='{esc}':fontsize={settings['text_size']}:"
                            f"fontcolor=0x{color}:x=(w-text_w)/2:{pos_map[settings['text_pos']]}{box_opt}")

        # logo overlay
        logo_path = settings["logo_path"].strip()
        logo_input = None
        if logo_path and Path(logo_path).exists():
            logo_input = logo_path

        # ---------- build full ffmpeg command ----------
        cmd = [FFMPEG, "-y", "-i", str(path)]

        extra_audio_input_idx = None
        tts_temp_file = None
        if settings["use_tts"] and EDGE_TTS_OK and settings["tts_text"].strip():
            tts_temp_file = self._generate_tts(settings["tts_voice"], settings["tts_text"])
            cmd += ["-i", tts_temp_file]
            extra_audio_input_idx = 1
        elif settings["replace_audio"].strip() and Path(settings["replace_audio"]).exists():
            cmd += ["-i", settings["replace_audio"]]
            extra_audio_input_idx = 1

        logo_input_idx = None
        if logo_input:
            cmd += ["-i", logo_input]
            logo_input_idx = len(cmd) // 1  # placeholder, real index computed below

        # recompute real input indices cleanly
        input_count = 1
        tts_or_replace_idx = None
        if extra_audio_input_idx is not None:
            tts_or_replace_idx = input_count
            input_count += 1
        logo_idx = None
        if logo_input:
            logo_idx = input_count
            input_count += 1
        emoji_idx_map = {}
        for (epath, elabel, ew, eh) in extra_inputs:
            cmd += ["-i", epath]
            emoji_idx_map[elabel] = (input_count, ew, eh)
            input_count += 1

        # --- assemble filter_complex ---
        fc = []
        fc.append(f"[0:v]{','.join(vf_chain)}[vbase]" if vf_chain else "[0:v]null[vbase]")

        for (epath, elabel, ew, eh) in extra_inputs:
            iidx, ew2, eh2 = emoji_idx_map[elabel]
            fc.append(f"[{iidx}:v]scale={ew2}:{eh2}[{elabel}scaled]")

        fc.extend(region_parts)
        cur_label = final_v_label

        if logo_idx is not None:
            lw_pct = settings["logo_scale"] / 100.0
            op = settings["logo_opacity"] / 100.0
            pos_map = {
                "Top-Left": "10:10", "Top-Right": "main_w-overlay_w-10:10",
                "Bottom-Left": "10:main_h-overlay_h-10", "Bottom-Right": "main_w-overlay_w-10:main_h-overlay_h-10",
            }
            fc.append(f"[{logo_idx}:v]scale=iw*{lw_pct:.3f}*{out_w}/iw:-1,format=rgba,colorchannelmixer=aa={op:.2f}[logo]")
            # simpler robust scale: scale relative to out_w
            fc[-1] = f"[{logo_idx}:v]scale={int(out_w*lw_pct)}:-1,format=rgba,colorchannelmixer=aa={op:.2f}[logo]"
            fc.append(f"[{cur_label}][logo]overlay={pos_map[settings['logo_pos']]}[vlogo]")
            cur_label = "vlogo"

        if text_filter:
            fc.append(f"[{cur_label}]{text_filter}[vtext]")
            cur_label = "vtext"

        filter_complex = ";".join(fc)
        cmd += ["-filter_complex", filter_complex, "-map", f"[{cur_label}]"]

        # audio mapping
        if settings["mute"] and tts_or_replace_idx is None:
            cmd += ["-an"]
        elif tts_or_replace_idx is not None:
            if settings["tts_mix"] and not settings["mute"]:
                cmd += ["-filter_complex:a", f"[0:a]volume=0.25[a0];[{tts_or_replace_idx}:a]volume=1.0[a1];[a0][a1]amix=inputs=2:duration=longest[aout]"]
                cmd += ["-map", "[aout]"]
            else:
                cmd += ["-map", f"{tts_or_replace_idx}:a"]
        else:
            cmd += ["-map", "0:a?"]

        if abs(settings["speed"] - 1.0) > 1e-3 and not (settings["mute"] and tts_or_replace_idx is None):
            atempo = settings["speed"]
            atempo_chain = self._atempo_chain(atempo)
            cmd += ["-af", atempo_chain]

        cmd += ["-c:v", vcodec, "-preset", settings["preset"], "-crf", str(settings["crf"])]
        if acodec and not (settings["mute"] and tts_or_replace_idx is None):
            cmd += ["-c:a", acodec, "-b:a", "160k"]
        cmd += ["-movflags", "+faststart", str(out_path)]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
        if tts_temp_file and os.path.exists(tts_temp_file):
            try:
                os.remove(tts_temp_file)
            except Exception:
                pass

        if not out_path.exists() or out_path.stat().st_size < 1000:
            raise RuntimeError("FFmpeg failed:\n" + result.stdout[-1500:])
        return out_path

    @staticmethod
    def _atempo_chain(speed):
        """ffmpeg's atempo filter only supports 0.5-2.0 per instance; chain for extremes."""
        parts = []
        remaining = speed
        while remaining > 2.0:
            parts.append("atempo=2.0")
            remaining /= 2.0
        while remaining < 0.5:
            parts.append("atempo=0.5")
            remaining /= 0.5
        parts.append(f"atempo={remaining:.4f}")
        return ",".join(parts)

    def _generate_tts(self, voice_label, text):
        voice = TTS_VOICES[voice_label]
        out_mp3 = Path(tempfile.gettempdir()) / f"tts_{abs(hash(text+voice))}.mp3"

        async def _run():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(out_mp3))

        import asyncio
        asyncio.run(_run())
        return str(out_mp3)


def main():
    if DND_OK:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = VideoEditorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
