#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shorts Studio — fetch a YouTube video, auto/manually cut it into vertical
shorts, LIVE-EDIT each one in your browser (speed, zoom, mute/replace audio,
AI Hindi/English voiceover, text, logo, blur/black/emoji hide-regions,
rect/circle/arrow shapes, color grading) and only write the final file to
disk when you click Save.

One process, one script: a local Flask server + a modern single-page UI
(vanilla HTML/CSS/JS, no build step) that opens in your default browser.

PERFORMANCE NOTES (this version):
  - Clips are cut in PARALLEL (ThreadPoolExecutor) instead of one-by-one,
    since each cut is an independent network-read + ffmpeg job.
  - Proxy cuts use preset=ultrafast (they're just scratch/preview files;
    the real quality knob is the final export preset/CRF you pick).
  - ffmpeg is told to use all CPU threads (-threads 0).
  - Export has a fast "stream copy" path: if you didn't change speed/zoom/
    color/regions/text/logo/audio/resolution/format from defaults, Save
    just remuxes the proxy file instead of re-encoding it — this turns a
    multi-second re-encode into a near-instant copy.

Run:
    pip install flask yt-dlp imageio-ffmpeg edge-tts gTTS
    python shortvideo.py
    (put .mp3 background-music files in an "audio" folder next to this script)
"""

import os
import sys
import re
import json
import time
import uuid
import asyncio
import threading
import subprocess
import webbrowser
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request, jsonify, send_file, Response

try:
    import yt_dlp
    import imageio_ffmpeg
except ImportError:
    print("Run: pip install yt-dlp imageio-ffmpeg flask")
    raise SystemExit(1)

try:
    import edge_tts
    EDGE_TTS_OK = True
except ImportError:
    EDGE_TTS_OK = False

try:
    from gtts import gTTS
    GTTS_OK = True
except ImportError:
    GTTS_OK = False

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def _no_console_kwargs():
    """Prevents a flashing black CMD window on Windows every time ffmpeg is
    shelled out to — keeps things looking clean and modern for users who
    aren't going to understand a terminal popping up mid-task."""
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}

if getattr(sys, 'frozen', False):
    # Running as a packaged EXE/APK: keep data next to the actual executable,
    # not inside PyInstaller's temporary extraction folder (which gets deleted).
    BASE = Path(sys.executable).resolve().parent
else:
    BASE = Path(__file__).resolve().parent
PROXY_DIR = BASE / "proxy_clips"
UPLOAD_DIR = BASE / "uploads"
OUTPUT_DIR = BASE / "shorts_final"
AUDIO_LIB_DIR = BASE / "audio"          # <-- put your .mp3 background-music files here
for d in (PROXY_DIR, UPLOAD_DIR, OUTPUT_DIR, AUDIO_LIB_DIR):
    d.mkdir(exist_ok=True)

TTS_VOICES = {
    "hi_male": ("edge", "hi-IN-MadhurNeural"),
    "hi_female": ("edge", "hi-IN-SwaraNeural"),
    "en_in_male": ("edge", "en-IN-PrabhatNeural"),
    "en_in_female": ("edge", "en-IN-NeerjaNeural"),
    "en_us_male": ("edge", "en-US-GuyNeural"),
    "en_us_female": ("edge", "en-US-AriaNeural"),
    "gtts_hi": ("gtts", "hi"),          # Google TTS Hindi (the "ladki" voice users like)
    "gtts_en_in": ("gtts", "en"),       # Google TTS English
}

# in-memory background job registry for progressive (live) clip cutting:
# job_id -> {"clips": [...], "done": False, "title": "", "error": None, "total": N}
JOBS = {}

# CapCut-style one-click color/look presets (pure ffmpeg eq/curves/colorchannelmixer combos)
COLOR_PRESETS = {
    "none": {},
    "vivid": {"contrast": 1.15, "saturation": 1.35, "brightness": 0.02},
    "cinematic": {"contrast": 1.2, "saturation": 0.85, "brightness": -0.02, "curves": "vintage"},
    "moody": {"contrast": 1.25, "saturation": 0.7, "brightness": -0.05},
    "vintage_vhs": {"contrast": 0.95, "saturation": 0.8, "brightness": 0.0, "curves": "vintage", "vignette": True},
    "warm_glow": {"contrast": 1.08, "saturation": 1.2, "brightness": 0.03, "colorchannelmixer": "rr=1.1:gg=1.02:bb=0.9"},
    "cool_blue": {"contrast": 1.1, "saturation": 1.05, "brightness": 0.0, "colorchannelmixer": "rr=0.9:gg=1.0:bb=1.15"},
}

# How many clips to cut at once. Network-bound + ffmpeg, so a modest
# worker count helps a lot without saturating CPU/bandwidth.
MAX_CUT_WORKERS = min(6, max(2, (os.cpu_count() or 4)))

app = Flask(__name__)

# in-memory job/clip registry: clip_id -> {path, w, h, duration}
CLIPS = {}


# ───────────────────────────── helpers ─────────────────────────────

def probe(path):
    proc = subprocess.run([FFMPEG, "-i", str(path)], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", **_no_console_kwargs())
    out = proc.stdout
    w = h = None
    dur = None
    m = re.search(r"(\d{2,5})x(\d{2,5})", out)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
    m2 = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", out)
    if m2:
        hh, mm, ss = m2.groups()
        dur = int(hh) * 3600 + int(mm) * 60 + float(ss)
    return w, h, dur


COOKIES_FILE = BASE / "cookies.txt"   # export from your browser (see note below) if auto-detect fails
COOKIE_BROWSERS = ["chrome", "edge", "firefox", "brave"]  # tried in this order

# Remembers whichever auth mode last succeeded so repeat resolves (every new
# URL pasted on the main page) skip straight to the method that's known to
# work, instead of re-running the whole slow cookies_file->chrome->edge->
# firefox->brave->default->bypass fallback chain from scratch every time.
# Each browser-cookie attempt can cost 15-30+ seconds (yt-dlp has to copy and
# decrypt that browser's entire cookie DB), so paying that cost once per
# process instead of once per video is the single biggest speed win here.
_RESOLVED_MODE = {"mode": None}


def _ydl_base_opts():
    opts = {
        'quiet': True, 'no_warnings': True, 'noplaylist': True,
        'socket_timeout': 15, 'retries': 2, 'extractor_retries': 1,
        'geo_bypass': True,
    }
    if COOKIES_FILE.exists():
        opts['cookiefile'] = str(COOKIES_FILE)
    return opts


def _auth_attempts():
    """Cached working mode first, then the rest of the fallback chain
    (skipping duplicates) — same pattern as downloader.py's smart caching."""
    attempts = []
    if _RESOLVED_MODE["mode"]:
        attempts.append(_RESOLVED_MODE["mode"])
    rest = []
    if COOKIES_FILE.exists():
        rest.append("cookies_file")
    rest.extend(COOKIE_BROWSERS)
    rest.append("default")
    rest.append("bypass")
    for m in rest:
        if m not in attempts:
            attempts.append(m)
    return attempts


def _apply_auth_mode(opts, mode):
    opts = dict(opts)
    if mode == "cookies_file":
        opts['cookiefile'] = str(COOKIES_FILE)
    elif mode in COOKIE_BROWSERS:
        opts.pop('cookiefile', None)
        opts['cookiesfrombrowser'] = (mode,)
    elif mode == "default":
        opts.pop('cookiefile', None)
    elif mode == "bypass":
        opts.pop('cookiefile', None)
        opts['extractor_args'] = {
            'youtube': {'player_client': ['ios', 'android', 'mweb']}
        }
    return opts


def _resolve_info(url, ydl_opts, download=False):
    """Runs yt-dlp's extract_info through the cached-auth fallback chain.
    Shared by resolve_stream() (used for cutting), the video-details API,
    and the in-file download API — one resolution path, one cache, used
    everywhere in this file. Returns (info, ydl, error); ydl is only kept
    around (non-None) when download=True, since callers need it afterwards
    for ydl.prepare_filename()."""
    last_err = None
    for mode in _auth_attempts():
        opts = _apply_auth_mode(ydl_opts, mode)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=download)
            _RESOLVED_MODE["mode"] = mode  # remember what worked
            return info, (ydl if download else None), None
        except Exception as e:
            last_err = e
            continue
    return None, None, last_err


def resolve_stream(url, max_height=None):
    ydl_opts = _ydl_base_opts()
    if max_height and str(max_height).lower() not in ("best", "auto", "0", ""):
        h = int(max_height)
        ydl_opts['format'] = f'bestvideo[height<={h}]+bestaudio/best[height<={h}]/best'
    else:
        ydl_opts['format'] = 'bestvideo+bestaudio/best'

    info, _, err = _resolve_info(url, ydl_opts, download=False)
    if info is None:
        raise err or RuntimeError("Could not resolve video")

    video_url = audio_url = None
    video_headers = audio_headers = None
    if info.get('requested_formats'):
        for f in info['requested_formats']:
            if f.get('vcodec') != 'none' and f.get('acodec') == 'none':
                video_url = f['url']
                video_headers = f.get('http_headers')
            elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                audio_url = f['url']
                audio_headers = f.get('http_headers')
    if not video_url:
        video_url = info.get('url')
        video_headers = info.get('http_headers')
    if not audio_url:
        audio_url = video_url
        audio_headers = video_headers
    # Fall back to top-level headers if a specific format didn't carry its own —
    # googlevideo URLs are signed to a particular client (see the c= param in
    # the URL) and will 403 if ffmpeg's request doesn't look like that client.
    video_headers = video_headers or info.get('http_headers') or {}
    audio_headers = audio_headers or info.get('http_headers') or {}
    title = info.get('title', 'video')
    safe = re.sub(r'[^\w\-]+', '_', title)[:40]
    return video_url, audio_url, safe, info.get('duration'), video_headers, audio_headers

def _ffmpeg_header_args(headers):
    """Builds ffmpeg's -headers block from a yt-dlp http_headers dict.
    Without this, googlevideo signed URLs come back 403 because ffmpeg's
    default User-Agent doesn't match the client the URL was signed for."""
    if not headers:
        return []
    lines = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
    return ["-headers", lines]


def cut_proxy(video_url, audio_url, start, end, out_path, video_headers=None, audio_headers=None):
    duration = end - start
    vf = "crop=ih*9/16:ih"
    v_hdr = _ffmpeg_header_args(video_headers)
    a_hdr = _ffmpeg_header_args(audio_headers)
    # Proxy clips are throwaway scratch/preview files that get re-encoded
    # again on export — ultrafast + a light crf is plenty and cuts encode
    # time dramatically vs. the previous near-lossless veryfast/crf15.
    if video_url == audio_url:
        cmd = [FFMPEG, "-y"] + v_hdr + ["-ss", str(start), "-i", video_url, "-t", str(duration),
           "-vf", vf,
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
           "-c:a", "aac", "-b:a", "192k",
               "-threads", "0", "-movflags", "+faststart", str(out_path)]
    else:
        cmd = [FFMPEG, "-y"] + v_hdr + ["-ss", str(start), "-i", video_url] + a_hdr + ["-ss", str(start), "-i", audio_url,
           "-t", str(duration),
           "-vf", vf,
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
           "-c:a", "aac", "-b:a", "192k",
               "-threads", "0", "-movflags", "+faststart", str(out_path)]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", **_no_console_kwargs())
    if not (out_path.exists() and out_path.stat().st_size > 1000):
        print("──── FFMPEG CUT FAILED ────")
        print(result.stdout[-2000:])   # last 2000 chars — error usually right at the end
        print("───────────────────────────")
    return out_path.exists() and out_path.stat().st_size > 1000




def compute_auto_ranges(total_dur, clip_len, start_from_one=True):
    ranges = []
    t = 1 if start_from_one else 0
    while t < total_dur - 1:
        e = min(t + clip_len, total_dur)
        if e - t >= 2 or len(ranges) == 0:
            ranges.append((int(t), int(e)))
        t += clip_len
    return ranges


def _resolve_user_file(url):
    """A url can point at /uploaded/<fname> (user uploads) or /audio_lib/<fname>
    (the local audio/ folder) — resolve to the real path on disk either way."""
    if not url:
        return None
    name = Path(url).name
    if "/audio_lib/" in url:
        return AUDIO_LIB_DIR / name
    return UPLOAD_DIR / name


def atempo_chain(speed):
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


# ───────────────────────────── API: fetch + cut ─────────────────────────────

def _run_cut_job(job_id, url, height, mode, clip_len, manual_ranges, start_from_one=True, local_path=None):
    job = JOBS[job_id]
    try:
        video_headers = audio_headers = None
        if local_path:
            # User uploaded a file already on their PC/phone - no yt-dlp,
            # no internet fetch, no external server involved. We just point
            # the existing cut pipeline at the local file on disk.
            video_url = audio_url = str(local_path)
            title = Path(local_path).stem
            _, _, total_dur = probe(Path(local_path))
        else:
            video_url, audio_url, title, total_dur, video_headers, audio_headers = resolve_stream(url, max_height=height)
    except Exception as e:
        job["error"] = f"Could not resolve video: {e}"
        job["done"] = True
        return

    job["title"] = title

    if mode == "auto":
        if not total_dur:
            job["error"] = "Could not detect duration for auto mode"
            job["done"] = True
            return
        ranges = compute_auto_ranges(total_dur, clip_len, start_from_one)
    else:
        ranges = manual_ranges

    if not ranges:
        job["error"] = "No clip ranges to cut"
        job["done"] = True
        return

    job["total"] = len(ranges)

    work_jobs = []
    for i, (s, e) in enumerate(ranges, start=1):
        clip_id = uuid.uuid4().hex[:12]
        out_path = PROXY_DIR / f"{clip_id}.mp4"
        work_jobs.append((i, s, e, clip_id, out_path))

    def _do_job(j):
        i, s, e, clip_id, out_path = j
        ok = cut_proxy(video_url, audio_url, s, e, out_path, video_headers, audio_headers)
        return j, ok

    # As each clip finishes cutting it's appended to job["clips"] immediately —
    # the frontend polls and shows each short the moment it's ready, instead
    # of waiting for the whole batch.
    with ThreadPoolExecutor(max_workers=MAX_CUT_WORKERS) as pool:
        futures = [pool.submit(_do_job, j) for j in work_jobs]
        for fut in as_completed(futures):
            (i, s, e, clip_id, out_path), ok = fut.result()
            if ok:
                w, h, dur = probe(out_path)
                CLIPS[clip_id] = {"path": str(out_path), "w": w, "h": h, "duration": dur,
                                   "title": f"{title}_{i:02d}", "start": s, "end": e}
                job["clips"].append({"index": i, "clip_id": clip_id, "w": w, "h": h,
                                      "duration": dur, "label": f"Short {i} ({s}s–{e}s)"})
    job["done"] = True


@app.route("/api/fetch_and_cut", methods=["POST"])
def api_fetch_and_cut_start():
    """Starts cutting in a background thread and returns immediately with a
    job_id. Poll /api/cut_status/<job_id> to get each clip the moment it's
    ready (live, one-by-one) instead of waiting for the whole batch."""
    data = request.json
    url = data.get("url", "").strip()
    local_rel = (data.get("local_path") or "").strip()  # e.g. "/uploaded/myclip.mp4" from /api/upload
    height = str(data.get("quality", "1080"))
    mode = data.get("mode", "auto")
    clip_len = int(data.get("clip_len", 30))
    start_from_one = bool(data.get("start_from_one", True))
    manual_ranges = []
    if mode != "auto":
        manual_ranges = [(int(r[0]), int(r[1])) for r in data.get("ranges", [])]

    local_path = None
    if local_rel:
        # Only allow files that /api/upload itself created, under UPLOAD_DIR -
        # never trust an arbitrary filesystem path from the browser.
        fname = Path(local_rel).name
        candidate = UPLOAD_DIR / fname
        if not candidate.exists():
            return jsonify({"error": "Uploaded file not found on server"}), 400
        local_path = candidate
    elif not url:
        return jsonify({"error": "No URL or uploaded file given"}), 400

    job_id = uuid.uuid4().hex[:10]
    JOBS[job_id] = {"clips": [], "done": False, "title": "", "error": None, "total": 0}
    threading.Thread(target=_run_cut_job,
                      args=(job_id, url, height, mode, clip_len, manual_ranges, start_from_one, local_path),
                      daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/cut_status/<job_id>")
def api_cut_status(job_id):
    """Returns all clips sorted by index, plus done/error flags."""
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Unknown job"}), 404
    clips = sorted(job["clips"], key=lambda c: c["index"])
    return jsonify({
        "title": job["title"], "error": job["error"], "done": job["done"],
        "total": job["total"], "clips": clips,
    })


# ═══════════════ API: main-page video details + single-file download ═══════════════
# Fully self-contained in THIS file — same yt-dlp + _resolve_info/_RESOLVED_MODE
# cache used by the cutting pipeline above, not the separate downloader.py
# blueprint. Lets the main page show details + offer one best-quality
# video+audio download without touching another module.

def _fmt_size(n):
    if not n:
        return None
    n = float(n)
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _fmt_int(n):
    if n is None:
        return None
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return str(n)


def _fmt_duration(sec):
    if sec is None:
        return None
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _build_minimal_details(info):
    """Just what the main-page panel needs: title, uploader, duration,
    views, thumbnail, description, tags, and the true best resolution/size
    (which the download endpoint below always merges into a single file
    with audio included, regardless of whether a native combined format
    exists at that resolution)."""
    best_h = None
    best_size = None
    for f in info.get("formats", []) or []:
        if f.get("vcodec") not in (None, "none") and f.get("height"):
            if not best_h or f["height"] > best_h:
                best_h = f["height"]
    for f in info.get("formats", []) or []:
        if f.get("filesize") and (f.get("vcodec") not in (None, "none")) and (f.get("acodec") not in (None, "none")):
            best_size = max(best_size or 0, f["filesize"])

    tags = info.get("tags") or []
    return {
        "title": info.get("title"),
        "uploader": info.get("uploader") or info.get("channel"),
        "duration": info.get("duration"),
        "duration_str": _fmt_duration(info.get("duration")),
        "view_count_str": _fmt_int(info.get("view_count")),
        "thumbnail": info.get("thumbnail"),
        "description": info.get("description"),
        "tags": tags[:8],
        "resolution": f"{best_h}p" if best_h else None,
        "best_filesize_str": _fmt_size(best_size),
    }


@app.route("/api/main_video_info", methods=["POST"])
def api_main_video_info():
    data = request.json or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Paste a video URL first"}), 400

    ydl_opts = _ydl_base_opts()
    ydl_opts['format'] = 'bestvideo+bestaudio/best'
    info, _, err = _resolve_info(url, ydl_opts, download=False)
    if info is None:
        return jsonify({"error": f"Could not resolve video: {err}"}), 400

    return jsonify(_build_minimal_details(info))


# dl_id -> {status, percent, downloaded, total, speed, eta, filename, error}
MAIN_DL_JOBS = {}
MAIN_DL_DIR = BASE / "main_downloads"
MAIN_DL_DIR.mkdir(exist_ok=True)


def _run_main_download_job(dl_id, url):
    job = MAIN_DL_JOBS[dl_id]

    def hook(d):
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes") or 0
            speed = d.get("speed")
            job.update({
                "status": "downloading",
                "downloaded": downloaded, "total": total,
                "downloaded_str": _fmt_size(downloaded),
                "total_str": _fmt_size(total) if total else None,
                "percent": round(downloaded * 100 / total, 1) if total else None,
                "speed": speed,
                "speed_str": (_fmt_size(speed) + "/s") if speed else None,
                "eta": d.get("eta"),
            })
        elif status == "finished":
            job["status"] = "processing"

    ydl_opts = _ydl_base_opts()
    ydl_opts.update({
        "format": "bestvideo+bestaudio/best",   # single best video + audio, merged into one file
        "outtmpl": str(MAIN_DL_DIR / f"{dl_id}_%(title).60s.%(ext)s"),
        "progress_hooks": [hook],
        "merge_output_format": "mp4",
        "postprocessor_args": {"default": []},
        "ffmpeg_location": str(FFMPEG),
    })

    # Keeps ffmpeg's merge step from flashing a console window on Windows.
    _orig_popen = subprocess.Popen
    def _quiet_popen(*args, **kwargs):
        kwargs.update(_no_console_kwargs())
        return _orig_popen(*args, **kwargs)
    subprocess.Popen = _quiet_popen
    try:
        info, ydl, err = _resolve_info(url, ydl_opts, download=True)
    finally:
        subprocess.Popen = _orig_popen

    if info is None:
        job["status"] = "error"
        job["error"] = f"Download failed: {err}"
        return

    try:
        fname = ydl.prepare_filename(info)
        p = Path(fname)
        if not p.exists():
            p2 = p.with_suffix(".mp4")
            if p2.exists():
                p = p2
        job["filename"] = p.name
        job["status"] = "done"
        job["percent"] = 100
    except Exception as e:
        job["status"] = "error"
        job["error"] = f"Could not finalize file: {e}"


@app.route("/api/main_download/start", methods=["POST"])
def api_main_download_start():
    data = request.json or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "No URL given"}), 400
    dl_id = uuid.uuid4().hex[:10]
    MAIN_DL_JOBS[dl_id] = {
        "status": "starting", "percent": 0, "downloaded": 0, "total": None,
        "speed": None, "eta": None, "filename": None, "error": None,
    }
    threading.Thread(target=_run_main_download_job, args=(dl_id, url), daemon=True).start()
    return jsonify({"dl_id": dl_id})


@app.route("/api/main_download/progress/<dl_id>")
def api_main_download_progress(dl_id):
    job = MAIN_DL_JOBS.get(dl_id)
    if not job:
        return jsonify({"error": "Unknown download job"}), 404
    return jsonify(job)


@app.route("/api/main_download/file/<dl_id>")
def api_main_download_file(dl_id):
    job = MAIN_DL_JOBS.get(dl_id)
    if not job or job.get("status") != "done" or not job.get("filename"):
        return "Not ready", 404
    p = MAIN_DL_DIR / job["filename"]
    if not p.exists():
        return "Not found", 404
    display_name = job["filename"].split("_", 1)[-1]
    return send_file(p, as_attachment=True, download_name=display_name)






@app.route("/audio_lib/<fname>")
def audio_lib_file(fname):
    p = AUDIO_LIB_DIR / fname
    if not p.exists():
        return "Not found", 404
    return send_file(p)


# ---------------------------------------------------------------------------
# Auto-detect audio/video already on the user's own device (PC or Android),
# so people don't have to manually copy files into the audio/ folder.
# ---------------------------------------------------------------------------
import platform
AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")
VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".webm")
DEVICE_MEDIA_INDEX = {}  # id -> Path, filled in each time /api/audio_library is scanned


def get_common_media_dirs():
    """Common folders where people already keep music/video, per platform,
    including Android's shared storage path when running as a packaged app."""
    home = Path.home()
    system = platform.system()
    candidates = []
    if system == "Windows":
        candidates += [home / "Music", home / "Downloads", home / "Videos"]
    elif system == "Darwin":
        candidates += [home / "Music", home / "Downloads", home / "Movies"]
    else:
        candidates += [
            Path("/storage/emulated/0/Music"),
            Path("/storage/emulated/0/Download"),
            Path("/storage/emulated/0/Movies"),
            Path("/storage/emulated/0/DCIM"),
            home / "Music", home / "Downloads",
        ]
    return [d for d in candidates if d.exists() and d.is_dir()]


def scan_device_media():
    """Walk common device folders (one level deep) for audio/video files
    and register them so they can be streamed back via /device_media/<id>."""
    found = []
    for folder in get_common_media_dirs():
        try:
            for p in folder.iterdir():
                if p.is_file() and p.suffix.lower() in AUDIO_EXTS + VIDEO_EXTS:
                    fid = uuid.uuid4().hex[:12]
                    DEVICE_MEDIA_INDEX[fid] = p
                    found.append({
                        "id": fid,
                        "name": p.stem,
                        "filename": p.name,
                        "kind": "video" if p.suffix.lower() in VIDEO_EXTS else "audio",
                        "source": "device",
                        "url": f"/device_media/{fid}",
                    })
        except Exception:
            continue
    return found


@app.route("/device_media/<fid>")
def device_media_file(fid):
    p = DEVICE_MEDIA_INDEX.get(fid)
    if not p or not p.exists():
        return "Not found", 404
    return send_file(p)


# ---------------------------------------------------------------------------
# Optional: pull a curated background-music library from a GitHub repo
# (e.g. https://github.com/you/your-audio-repo) instead of bundling mp3s
# inside the packaged app itself. Point manifest_url at a raw JSON file
# shaped like: [{"name": "Chill Beat", "url": "https://raw.githubusercontent.com/.../chill.mp3"}]
# ---------------------------------------------------------------------------
import urllib.request

@app.route("/api/sync_github_audio", methods=["POST"])
def api_sync_github_audio():
    manifest_url = (request.json or {}).get("manifest_url", "").strip()
    if not manifest_url:
        return jsonify({"error": "manifest_url required"}), 400
    try:
        with urllib.request.urlopen(manifest_url, timeout=15) as r:
            manifest = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return jsonify({"error": f"Could not fetch manifest: {e}"}), 400

    added = []
    for item in manifest:
        name = item.get("name") or "track"
        url = item.get("url")
        if not url:
            continue
        safe_name = re.sub(r"[^A-Za-z0-9_\-. ]", "_", name) + ".mp3"
        dest = AUDIO_LIB_DIR / safe_name
        if dest.exists():
            continue
        try:
            urllib.request.urlretrieve(url, dest)
            added.append(safe_name)
        except Exception:
            continue
    return jsonify({"added": added, "total_requested": len(manifest)})


@app.route("/api/audio_library")
def api_audio_library():
    files = []
    for p in sorted(AUDIO_LIB_DIR.glob("*.mp3")):
        files.append({
            "name": p.stem,
            "filename": p.name,
            "source": "bundled",
            "url": f"/audio_lib/{p.name}"
        })
    # merge in whatever audio/video the scan finds already on this device
    files += scan_device_media()
    return jsonify({"files": files})

@app.route("/media/<clip_id>")
def media(clip_id):
    info = CLIPS.get(clip_id)
    if not info:
        return "Not found", 404
    return send_file(info["path"])


@app.route("/uploaded/<fname>")
def uploaded(fname):
    p = UPLOAD_DIR / fname
    if not p.exists():
        return "Not found", 404
    return send_file(p)


@app.route("/api/upload", methods=["POST"])
def api_upload():
    f = request.files["file"]
    ext = Path(f.filename).suffix
    fname = uuid.uuid4().hex[:10] + ext
    f.save(UPLOAD_DIR / fname)
    return jsonify({"url": f"/uploaded/{fname}", "filename": fname})


@app.route("/api/tts", methods=["POST"])
def api_tts():
    data = request.json
    voice_key = data.get("voice", "hi_male")
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text given"}), 400
    engine, voice = TTS_VOICES.get(voice_key, TTS_VOICES["hi_male"])
    fname = f"tts_{uuid.uuid4().hex[:10]}.mp3"
    out_path = UPLOAD_DIR / fname

    if engine == "gtts":
        if not GTTS_OK:
            return jsonify({"error": "gTTS not installed. Run: pip install gTTS"}), 400
        try:
            gTTS(text=text, lang=voice).save(str(out_path))
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        if not EDGE_TTS_OK:
            return jsonify({"error": "edge-tts not installed. Run: pip install edge-tts"}), 400

        async def _run():
            comm = edge_tts.Communicate(text, voice)
            await comm.save(str(out_path))

        try:
            asyncio.run(_run())
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"url": f"/uploaded/{fname}"})


# ───────────────────────────── API: export ─────────────────────────────

EXPORT_JOBS = {}

# Caps how many exports actually run their ffmpeg re-encode at once. The
# frontend now fires several exports concurrently (MAX_CONCURRENT_EXPORTS),
# so this is the backend-side safety net that keeps CPU usage sane even if
# more requests land than we want running heavy re-encodes simultaneously.
MAX_EXPORT_WORKERS = min(4, max(2, (os.cpu_count() or 4) // 2))
_EXPORT_SEMAPHORE = threading.Semaphore(MAX_EXPORT_WORKERS)


def run_export_thread(export_id, src, w, h, settings, title, src_duration):
    def progress_cb(pct):
        if export_id in EXPORT_JOBS:
            EXPORT_JOBS[export_id]["progress"] = pct

    with _EXPORT_SEMAPHORE:
        try:
            out_path = build_and_run_export(
                src, w, h, settings, title,
                progress_callback=progress_cb,
                src_duration=src_duration
            )
            if export_id in EXPORT_JOBS:
                EXPORT_JOBS[export_id].update({
                    "status": "done",
                    "progress": 100,
                    "path": str(out_path),
                    "url": f"/api/download/{out_path.name}"
                })
        except Exception as e:
            if export_id in EXPORT_JOBS:
                EXPORT_JOBS[export_id].update({
                    "status": "failed",
                    "error": str(e)
                })


@app.route("/api/export", methods=["POST"])
def api_export():
    data = request.json
    clip_id = data.get("clip_id")
    settings = data.get("settings", {})
    info = CLIPS.get(clip_id)
    if not info:
        return jsonify({"error": "Unknown clip"}), 400

    src = Path(info["path"])
    w, h = info["w"] or 720, info["h"] or 1280
    src_duration = info.get("duration") or 30.0

    export_id = uuid.uuid4().hex[:12]
    EXPORT_JOBS[export_id] = {
        "status": "processing",
        "progress": 0,
        "path": None,
        "url": None,
        "error": None
    }

    threading.Thread(
        target=run_export_thread,
        args=(export_id, src, w, h, settings, info["title"], src_duration),
        daemon=True
    ).start()

    return jsonify({"export_id": export_id})


@app.route("/api/export_status/<export_id>")
def api_export_status(export_id):
    job = EXPORT_JOBS.get(export_id)
    if not job:
        return jsonify({"error": "Unknown export job"}), 404
    return jsonify(job)


@app.route("/api/download/<fname>")
def api_download(fname):
    p = OUTPUT_DIR / fname
    if not p.exists():
        return "Not found", 404
    return send_file(p, as_attachment=True)


# ═══════════════════ Downloader (separate file, imported here) ═══════════════════
# The general "download any video" feature lives entirely in downloader.py —
# it registers itself as a Flask Blueprint, so it runs in this SAME process
# and on this SAME port (no second server, nothing extra to start).
from downloader import downloader_bp, init_downloader
init_downloader(BASE, FFMPEG)
app.register_blueprint(downloader_bp)


def _is_trivial_export(s, src_ext):
    """True if the requested settings make no actual change to the video —
    in that case we can stream-copy instead of re-encoding (near-instant)."""
    if float(s.get("speed", 1.0)) != 1.0:
        return False
    if float(s.get("zoom", 1.0)) != 1.0:
        return False
    if abs(float(s.get("contrast", 1.0)) - 1.0) > 1e-3:
        return False
    if abs(float(s.get("saturation", 1.0)) - 1.0) > 1e-3:
        return False
    if abs(float(s.get("brightness", 0.0))) > 1e-3:
        return False
    if bool(s.get("sharpen", False)):
        return False
    if bool(s.get("enhance", False)):
        return False
    if bool(s.get("hflip", False)):
        return False
    if s.get("rotate", "0") != "0":
        return False
    if s.get("regions"):
        return False
    if s.get("text") and s["text"].get("content"):
        return False
    if s.get("texts"):
        return False
    if s.get("logo") and s["logo"].get("url"):
        return False
    if s.get("color_preset", "none") != "none":
        return False
    if abs(float(s.get("pan_x", 0.0))) > 1e-3 or abs(float(s.get("pan_y", 0.0))) > 1e-3:
        return False
    audio_mode = s.get("audio_mode", "original")
    if audio_mode not in ("original",):
        return False
    if s.get("resolution", "1080x1920") != "original":
        return False
    fmt = s.get("format", "mp4")
    if fmt != src_ext.lstrip("."):
        return False
    return True


def fast_copy_export(src, fmt, title):
    """Just remux the proxy clip to the output dir — no re-encode at all."""
    out_name = f"{title}_final_{uuid.uuid4().hex[:6]}.{fmt}"
    out_path = OUTPUT_DIR / out_name
    cmd = [FFMPEG, "-y", "-i", str(src), "-c", "copy", "-movflags", "+faststart", str(out_path)]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", **_no_console_kwargs())
    if not out_path.exists() or out_path.stat().st_size < 1000:
        raise RuntimeError("FFmpeg copy failed:\n" + result.stdout[-1500:])
    return out_path


def build_and_run_export(src, w, h, s, title, progress_callback=None, src_duration=30.0):
    fmt = s.get("format", "mp4")

    # ---- fast path: nothing was actually edited, just remux/copy ----
    if _is_trivial_export(s, src.suffix):
        return fast_copy_export(src, fmt, title)

    speed = float(s.get("speed", 1.0))
    zoom = float(s.get("zoom", 1.0))
    pan_x = float(s.get("pan_x", 0.0))   # -1..1, manual drag-to-pan inside the zoomed crop
    pan_y = float(s.get("pan_y", 0.0))
    mute = bool(s.get("mute", False))
    contrast = float(s.get("contrast", 1.0))
    saturation = float(s.get("saturation", 1.0))
    brightness = float(s.get("brightness", 0.0))
    sharpen = bool(s.get("sharpen", False))
    enhance = bool(s.get("enhance", False))  # extra detail/denoise pass, keeps quality from breaking on upscale
    hflip = bool(s.get("hflip", False))
    rotate = s.get("rotate", "0")
    resolution = s.get("resolution", "1080x1920")
    crf = int(s.get("crf", 18))
    preset = s.get("preset", "medium")
    regions = s.get("regions", [])
    # texts: prefer the new multi-text array; fall back to the legacy single `text` dict
    texts = s.get("texts") or ([s["text"]] if s.get("text") and s["text"].get("content") else [])
    logo = s.get("logo", None)
    audio_mode = s.get("audio_mode", "original")  # original | mute | replace | tts
    audio_file_url = s.get("audio_file_url")
    tts_url = s.get("tts_url")
    tts_mix = bool(s.get("tts_mix", False))
    preset_name = s.get("color_preset", "none")
    look = COLOR_PRESETS.get(preset_name, {})
    # Note: We do NOT multiply or offset contrast, saturation, or brightness by look values here,
    # because the client-side sliders already contain the preset's exact values.
    # We still use 'look' below to apply advanced look-specific filters like curves, vignette, and mixers.

    if enhance:
        contrast = contrast * 1.04
        saturation = saturation * 1.08

    out_w, out_h = w, h   # hamesha source/proxy ka actual resolution — kabhi fixed target nahi

    ext_codec = {"mp4": ("mp4", "libx264", "aac"), "mov": ("mov", "libx264", "aac"),
                 "webm": ("webm", "libvpx-vp9", "libopus")}[fmt]
    ext, vcodec, acodec = ext_codec

    eff_w = w / zoom if zoom > 1.0 else w
    eff_h = h / zoom if zoom > 1.0 else h
    # manual pan moves the crop window inside the available slack instead of
    # always centering it — clamped so we never crop outside the source frame
    max_off_x = max(0.0, (w - eff_w) / 2)
    max_off_y = max(0.0, (h - eff_h) / 2)
    crop_x_off = max_off_x * (1 - pan_x)   # pan_x: -1 = full left, 0 = center, 1 = full right
    crop_y_off = max_off_y * (1 - pan_y)
    scale_x = out_w / eff_w
    scale_y = out_h / eff_h

    vf = []
    if zoom > 1.0:
        vf.append(f"crop={int(eff_w)}:{int(eff_h)}:{int(crop_x_off)}:{int(crop_y_off)}")
        scale_flags = "lanczos+accurate_rnd"
        vf.append(f"scale={out_w}:{out_h}:flags={scale_flags}")

# zoom na ho to yahan koi scale filter hi nahi lagta — pixels bilkul native rehte hain

    # Rotate & Mirror Video (Horizontal Flip)
    if hflip:
        vf.append("hflip")
    if rotate == "90":
        vf.append("transpose=1")
    elif rotate == "180":
        vf.append("transpose=2,transpose=2")
    elif rotate == "270":
        vf.append("transpose=2")

    # Dynamic sharpening on zoom to maintain clarity and avoid pixelation
    if zoom > 1.0:
        zoom_sharp = min(1.2, 0.4 * (zoom - 1.0))
        if zoom_sharp > 0.05:
            vf.append(f"unsharp=5:5:{zoom_sharp:.2f}:5:5:0.0")

    if enhance:
        # Professional-grade 4K-upscale enhancement:
        # 1. Advanced 3D denoising to clear compression artifacts from source/proxy
        vf.append("hqdn3d=2.0:2.0:6.0:6.0")
        # 2. Stronger unsharp mask for pristine edge clarity without haloing
        vf.append("unsharp=5:5:1.5:5:5:0.8")

    eq_parts = []
    if abs(contrast - 1.0) > 1e-3:
        eq_parts.append(f"contrast={contrast:.3f}")
    if abs(saturation - 1.0) > 1e-3:
        eq_parts.append(f"saturation={saturation:.3f}")
    if abs(brightness) > 1e-3:
        eq_parts.append(f"brightness={brightness:.3f}")
    if eq_parts:
        vf.append("eq=" + ":".join(eq_parts))
    if look.get("curves"):
        vf.append(f"curves=preset={look['curves']}")
    if look.get("colorchannelmixer"):
        vf.append(f"colorchannelmixer={look['colorchannelmixer']}")
    if s.get("vignette") or look.get("vignette"):
        vf.append("vignette=PI/4")
    if s.get("film_grain"):
        vf.append("noise=alls=3:allf=t")
    if sharpen:
        vf.append("unsharp=5:5:0.6:5:5:0.0")
    if abs(speed - 1.0) > 1e-3:
        vf.append(f"setpts=PTS/{speed:.4f}")

    cmd = [FFMPEG, "-y", "-i", str(src)]
    extra_audio_idx = None
    input_count = 1

    if audio_mode == "tts" and tts_url:
        local_tts = _resolve_user_file(tts_url)
        cmd += ["-i", str(local_tts)]
        extra_audio_idx = input_count
        input_count += 1
    elif audio_mode == "replace" and audio_file_url:
        local_audio = _resolve_user_file(audio_file_url)
        # Infinite looping of replaced audio to handle video length larger than audio length
        cmd += ["-stream_loop", "-1", "-i", str(local_audio)]
        extra_audio_idx = input_count
        input_count += 1

    logo_idx = None
    if logo and logo.get("url"):
        local_logo = _resolve_user_file(logo["url"])
        cmd += ["-i", str(local_logo)]
        logo_idx = input_count
        input_count += 1

    emoji_inputs = []
    for r in regions:
        if r.get("kind") == "emoji" and r.get("emoji_url"):
            local_emoji = UPLOAD_DIR / Path(r["emoji_url"]).name
            cmd += ["-i", str(local_emoji)]
            emoji_inputs.append((r, input_count))
            input_count += 1

    fc = [f"[0:v]{','.join(vf)}[vbase]"]
    cur = "vbase"
    idx = 0
    emoji_map = {id(r): i for r, i in emoji_inputs}
    for r in regions:
        idx += 1
        rx = r["x"] * w - crop_x_off
        ry = r["y"] * h - crop_y_off
        rw = r["w"] * w
        rh = r["h"] * h
        x = int(rx * scale_x); y = int(ry * scale_y)
        bw = max(2, int(rw * scale_x)); bh = max(2, int(rh * scale_y))
        kind = r.get("kind")
        nxt = f"v{idx}"
        if kind == "blur":
            fc.append(f"[{cur}]split[{nxt}m][{nxt}c];[{nxt}c]crop={bw}:{bh}:{x}:{y},boxblur=20:2[{nxt}b];"
                       f"[{nxt}m][{nxt}b]overlay={x}:{y}[{nxt}]")
            cur = nxt
        elif kind == "black":
            fc.append(f"[{cur}]drawbox=x={x}:y={y}:w={bw}:h={bh}:color=black@1.0:t=fill[{nxt}]")
            cur = nxt
        elif kind == "emoji":
            iidx = emoji_map.get(id(r))
            if iidx is not None:
                fc.append(f"[{iidx}]scale={bw}:{bh}[{nxt}e]")
                fc.append(f"[{cur}][{nxt}e]overlay={x}:{y}[{nxt}]")
                cur = nxt
        elif kind in ("rect", "circle"):
            rgb = (r.get("color") or "#ff3b30").lstrip("#")
            fc.append(f"[{cur}]drawbox=x={x}:y={y}:w={bw}:h={bh}:color={rgb}@1.0:t=4[{nxt}]")
            cur = nxt
        elif kind == "arrow":
            rgb = (r.get("color") or "#ff3b30").lstrip("#")
            fc.append(f"[{cur}]drawbox=x={x}:y={y}:w={bw}:h=4:color={rgb}@1.0:t=fill[{nxt}]")
            cur = nxt

    if logo_idx is not None:
        lw = float(logo.get("w", 0.18)) * out_w
        lop = float(logo.get("opacity", 1.0))
        lx = float(logo.get("x", 0.78)) * out_w
        ly = float(logo.get("y", 0.04)) * out_h
        fc.append(f"[{logo_idx}]scale={int(lw)}:-2,format=rgba,colorchannelmixer=aa={lop:.2f}[logo]")
        fc.append(f"[{cur}][logo]overlay={int(lx)}:{int(ly)}[vlogo]")
        cur = "vlogo"

    # Try to find system font to prevent drawtext crashes on headless environments
    sys_font = None
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:\\Windows\\Fonts\\arial.ttf"
    ]:
        if os.path.exists(p):
            sys_font = p
            break
    if not sys_font:
        try:
            for p in Path("/usr/share/fonts").glob("**/*.ttf"):
                sys_font = str(p)
                break
        except Exception:
            pass

    stage_w = float(s.get("stage_w", 360.0))
    stage_h = float(s.get("stage_h", 640.0))
    if stage_h <= 0: stage_h = 640.0

    for t in texts:
        if not t or not t.get("content"):
            continue
        esc = t["content"].replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        tx = int(float(t.get("x", 0.1)) * out_w)
        ty = int(float(t.get("y", 0.8)) * out_h)
        orig_size = int(t.get("size", 56))
        # Scale size proportionally based on stage height to match preview exactly
        size = int(orig_size * (out_h / stage_h))
        color = (t.get("color") or "#ffffff").lstrip("#")
        box = ":box=1:boxcolor=black@0.45:boxborderw=14" if t.get("box", True) else ""
        if sys_font:
            escaped_font = sys_font.replace("\\", "/").replace(":", "\\:")
            font_opt = f":fontfile='{escaped_font}'"
        else:
            font_opt = ""
        nxt = "vtext" + uuid.uuid4().hex[:6]
        fc.append(f"[{cur}]drawtext=text='{esc}':fontsize={size}:fontcolor='#{color}':x={tx}:y={ty}{box}{font_opt}[{nxt}]")
        cur = nxt

    filter_complex = ";".join(fc)
    cmd += ["-filter_complex", filter_complex, "-map", f"[{cur}]"]

    pitch_af = None
    if s.get("audio_pitch"):
        # We can shift pitch slightly (e.g. 1.025x which is about +40 cents, completely natural for humans but breaks audio hashing algorithms)
        pitch_af = f"asetrate=44100*1.025,atempo={1/1.025:.4f}"

    if audio_mode == "mute":
        cmd += ["-an"]
    elif extra_audio_idx is not None:
        if audio_mode == "tts" and tts_mix:
            a0 = "[0:a]volume=0.25"
            if abs(speed - 1.0) > 1e-3:
                a0 += "," + atempo_chain(speed)   # keep original track in sync with sped-up video
            if pitch_af:
                a0 += "," + pitch_af
            a0 += "[a0]"
            cmd += ["-filter_complex:a",
                    f"{a0};[{extra_audio_idx}:a]volume=1.0[a1];[a0][a1]amix=inputs=2:duration=longest[aout]"]
            cmd += ["-map", "[aout]"]
        else:
            # replaced file / TTS-only audio is an independent track — it must
            # play at its own normal speed regardless of video speed changes
            cmd += ["-map", f"{extra_audio_idx}:a"]
            if pitch_af:
                cmd += ["-af", pitch_af]
    else:
        cmd += ["-map", "0:a?"]
        af_parts = []
        if pitch_af:
            af_parts.append(pitch_af)
        if abs(speed - 1.0) > 1e-3:
            af_parts.append(atempo_chain(speed))
        if af_parts:
            cmd += ["-af", ",".join(af_parts)]

    out_name = f"{title}_final_{uuid.uuid4().hex[:6]}.{ext}"
    out_path = OUTPUT_DIR / out_name
    cmd += ["-c:v", vcodec, "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p", "-threads", "0"]
    if audio_mode != "mute":
        cmd += ["-c:a", acodec, "-b:a", "160k"]
    # Limit output length to exactly match the video's actual playing duration
    target_duration = src_duration / speed if speed > 0 else src_duration
    cmd += ["-t", f"{target_duration:.3f}"]
    cmd += ["-movflags", "+faststart", str(out_path)]

    if progress_callback is None:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", **_no_console_kwargs())
        if not out_path.exists() or out_path.stat().st_size < 1000:
            raise RuntimeError("FFmpeg failed:\n" + result.stdout[-1500:])
    else:
        # Popen to parse live logs and report progress percent
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            universal_newlines=True
        )
        full_output = []
        target_duration = src_duration / speed if speed > 0 else src_duration

        while True:
            line = proc.stdout.readline()
            if not line:
                break
            full_output.append(line)
            m = re.search(r"time=(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)", line)
            if m and target_duration > 0:
                hh, mm, ss = m.groups()
                cur_secs = int(hh) * 3600 + int(mm) * 60 + float(ss)
                pct = min(99, int((cur_secs / target_duration) * 100))
                progress_callback(pct)

        proc.wait()
        if proc.returncode != 0 or not out_path.exists() or out_path.stat().st_size < 1000:
            stdout_tail = "".join(full_output[-100:]) if full_output else ""
            raise RuntimeError(f"FFmpeg failed (exit code {proc.returncode}):\n{stdout_tail[-1500:]}")

    return out_path


# ───────────────────────────── Frontend ─────────────────────────────

@app.route("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AutoShortAi</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
:root{
  --bg:#0b0d12; --panel:#13151c; --panel2:#191c25; --border:#262a36;
  --text:#eef0f6; --dim:#8a90a4; --accent:#6e5bff; --accent2:#22d3c4;
  --grad: linear-gradient(135deg,#6e5bff,#22d3c4);
  --btn-text:#0a0a0f;
  --danger:#ff5a6e; --warn:#ffb84d; --radius:16px;
}
/* ── Theme presets — switch instantly via the 🎨 menu top-right ───────── */
html[data-theme="light"]{
  --bg:#f4f5f9; --panel:#ffffff; --panel2:#eef0f6; --border:#dde1ea;
  --text:#171923; --dim:#5b6472; --accent:#5b46e0; --accent2:#0891b2;
  --grad: linear-gradient(135deg,#5b46e0,#0891b2);
  --btn-text:#ffffff; --danger:#e0324a; --warn:#c47a06;
}
html[data-theme="midnight-blue"]{
  --bg:#050a16; --panel:#0c1526; --panel2:#12213a; --border:#1f3358;
  --text:#e8f1ff; --dim:#7f93b8; --accent:#3b82f6; --accent2:#22d3ee;
  --grad: linear-gradient(135deg,#3b82f6,#22d3ee);
  --btn-text:#04101f;
}
html[data-theme="forest"]{
  --bg:#0a130d; --panel:#0f1e14; --panel2:#16301f; --border:#234a30;
  --text:#eafbea; --dim:#86b399; --accent:#22c55e; --accent2:#a3e635;
  --grad: linear-gradient(135deg,#16a34a,#a3e635);
  --btn-text:#06170a;
}
html[data-theme="sunset"]{
  --bg:#1a0e12; --panel:#241419; --panel2:#331d27; --border:#4a2635;
  --text:#fdf1ee; --dim:#cb9aa3; --accent:#fb7185; --accent2:#f59e0b;
  --grad: linear-gradient(135deg,#fb7185,#f59e0b);
  --btn-text:#1a0e12;
}
html[data-theme="ocean"]{
  --bg:#061319; --panel:#0b1f27; --panel2:#123039; --border:#1e4a56;
  --text:#e6fbff; --dim:#7fb8c4; --accent:#06b6d4; --accent2:#6366f1;
  --grad: linear-gradient(135deg,#06b6d4,#6366f1);
  --btn-text:#031015;
}
html[data-theme="rose"]{
  --bg:#170f14; --panel:#221720; --panel2:#2e1e2b; --border:#4a2f45;
  --text:#fdeef5; --dim:#c79ab0; --accent:#ec4899; --accent2:#f472b6;
  --grad: linear-gradient(135deg,#ec4899,#f472b6);
  --btn-text:#170f14;
}
html[data-theme="amber"]{
  --bg:#160f05; --panel:#221708; --panel2:#33230d; --border:#4d3416;
  --text:#fdf4e3; --dim:#c9a877; --accent:#f59e0b; --accent2:#eab308;
  --grad: linear-gradient(135deg,#f59e0b,#eab308);
  --btn-text:#160f05;
}
html[data-theme="slate"]{
  --bg:#101215; --panel:#181b1f; --panel2:#20242a; --border:#333941;
  --text:#eceef1; --dim:#9aa2ad; --accent:#64748b; --accent2:#94a3b8;
  --grad: linear-gradient(135deg,#475569,#94a3b8);
  --btn-text:#0b0d0f;
}
html[data-theme="cyberpunk"]{
  --bg:#0a0014; --panel:#150124; --panel2:#210235; --border:#4a0a6b;
  --text:#f5e6ff; --dim:#b083d6; --accent:#e91e9c; --accent2:#00f0ff;
  --grad: linear-gradient(135deg,#e91e9c,#00f0ff);
  --btn-text:#0a0014;
}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;}
.topbar{display:flex;align-items:center;gap:14px;padding:18px 28px;border-bottom:1px solid var(--border);
  background:linear-gradient(180deg,var(--panel),var(--bg));}
.logo{font-weight:800;font-size:20px;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent;}
.sub{color:var(--dim);font-size:13px;}
.nav-tabs{display:flex; gap:8px; margin-left:24px;}
.nav-tab-btn{
  background:var(--panel2); border:1px solid var(--border); color:var(--text); border-radius:10px;
  padding:9px 16px; font-size:13px; font-weight:700; cursor:pointer; transition:.15s;
}
.nav-tab-btn:hover{border-color:var(--accent);}
.nav-tab-btn.active{background:var(--grad); color:var(--btn-text); border-color:transparent;}
@media (max-width:760px){
  .nav-tabs{margin-left:0; order:3; width:100%; margin-top:10px;}
}

/* ── Downloader feature ─────────────────────────────────────────────── */
.dl-info-row{display:flex; gap:22px; flex-wrap:wrap; align-items:flex-start;}
.dl-thumb-wrap{flex:0 0 auto; width:320px; max-width:100%;}
.dl-thumb-main{
  width:100%; aspect-ratio:16/9; object-fit:cover; border-radius:12px;
  border:1px solid var(--border); background:var(--panel2);
}
.dl-thumb-strip{display:flex; gap:8px; margin-top:8px;}
.dl-thumb-strip img{
  width:64px; height:40px; object-fit:cover; border-radius:6px; cursor:pointer;
  border:1px solid var(--border); opacity:.75; transition:.15s;
}
.dl-thumb-strip img:hover{opacity:1; border-color:var(--accent);}
.dl-meta{flex:1; min-width:260px;}
.dl-title{margin:0 0 10px 0; font-size:19px; font-weight:800; color:var(--text); line-height:1.35;}
.dl-meta-badges{display:flex; flex-wrap:wrap; gap:8px; margin-bottom:14px;}
.dl-meta-badges span{
  background:var(--panel2); border:1px solid var(--border); color:var(--text);
  padding:5px 10px; border-radius:8px; font-size:12px; font-weight:700;
}
.dl-copy-row{display:flex; gap:8px;}
.dl-copy-row input{
  flex:1; padding:10px 12px; border-radius:10px; border:1px solid var(--border);
  background:var(--panel2); color:var(--text); font-size:12px;
}
.dl-section-title{margin:22px 0 10px 0; font-size:15px; font-weight:800; color:var(--text);}
.dl-formats-table-wrap{overflow-x:auto; border:1px solid var(--border); border-radius:12px;}
.dl-formats-table{width:100%; border-collapse:collapse; min-width:520px;}
.dl-formats-table th{
  text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:.4px;
  color:var(--dim); padding:10px 12px; background:var(--panel2); border-bottom:1px solid var(--border);
}
.dl-formats-table td{padding:10px 12px; font-size:13px; color:var(--text); border-bottom:1px solid var(--border);}
.dl-formats-table tr:last-child td{border-bottom:none;}
.dl-formats-table tr:hover td{background:rgba(255,255,255,0.03);}
.dl-fmt-btn{
  background:var(--grad); color:var(--btn-text); border:none; border-radius:8px;
  padding:7px 14px; font-size:12px; font-weight:800; cursor:pointer; white-space:nowrap;
}
.dl-fmt-btn:hover{filter:brightness(1.08);}
.dl-progress-stats{
  display:grid; grid-template-columns:repeat(auto-fit, minmax(130px,1fr)); gap:10px; margin-bottom:14px;
}
.dl-stat{
  background:var(--panel2); border:1px solid var(--border); border-radius:10px; padding:10px 12px;
  display:flex; flex-direction:column; gap:4px;
}
.dl-stat-label{font-size:10px; text-transform:uppercase; letter-spacing:.4px; color:var(--dim);}
.dl-stat-val{font-size:16px; font-weight:800; color:var(--text);}
@media (max-width:600px){
  .dl-thumb-wrap{width:100%;}
}

.dl-inline-status{
  margin-top:12px; padding:10px 14px; border-radius:10px; font-size:13px; font-weight:600;
  background:var(--panel2); border:1px solid var(--border); color:var(--text);
}
.dl-title-row{display:flex; align-items:flex-start; gap:8px;}
.dl-copy-icon-btn{
  background:var(--panel2); border:1px solid var(--border); color:var(--text);
  border-radius:8px; width:30px; height:30px; flex:0 0 auto; cursor:pointer; font-size:13px;
  display:flex; align-items:center; justify-content:center; transition:.15s;
}
.dl-copy-icon-btn:hover{border-color:var(--accent); filter:brightness(1.1);}
.dl-details-grid{
  display:grid; grid-template-columns:repeat(auto-fill, minmax(190px,1fr)); gap:10px; margin-bottom:6px;
}
.dl-detail-item{
  background:var(--panel2); border:1px solid var(--border); border-radius:10px; padding:9px 12px;
  display:flex; flex-direction:column; gap:3px; position:relative;
}
.dl-detail-label{font-size:10px; text-transform:uppercase; letter-spacing:.4px; color:var(--dim);}
.dl-detail-val{font-size:13.5px; font-weight:700; color:var(--text); word-break:break-word; padding-right:22px;}
.dl-detail-item .dl-copy-icon-btn{
  position:absolute; top:6px; right:6px; width:22px; height:22px; font-size:11px; background:transparent; border:none;
}
.dl-desc-wrap{margin:16px 0; border:1px solid var(--border); border-radius:10px; overflow:hidden;}
.dl-desc-head{
  display:flex; justify-content:space-between; align-items:center; padding:8px 12px;
  background:var(--panel2); font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:.4px; color:var(--dim);
}
.dl-desc-text{
  padding:12px 14px; font-size:13px; line-height:1.6; color:var(--text); white-space:pre-wrap;
}
.dl-desc-text.collapsed{max-height:70px; overflow:hidden; mask-image:linear-gradient(to bottom, black 60%, transparent 100%);}
.dl-chips-wrap{margin-bottom:14px;}
.dl-chips-label{font-size:11px; text-transform:uppercase; letter-spacing:.4px; color:var(--dim); display:block; margin-bottom:6px;}
.dl-chips{display:flex; flex-wrap:wrap; gap:6px;}
.dl-chips span{
  background:var(--panel2); border:1px solid var(--border); color:var(--text);
  padding:4px 10px; border-radius:999px; font-size:11.5px; font-weight:600;
}

/* ── Modern download progress: step tracker instead of a raw scrolling log ── */
.dl-stepper{display:flex; align-items:flex-start; margin-bottom:18px; gap:0;}
.dl-step{display:flex; flex-direction:column; align-items:center; gap:6px; flex:0 0 auto; width:80px;}
.dl-step-ico{
  width:38px; height:38px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  background:var(--panel2); border:2px solid var(--border); font-size:16px; opacity:.5; transition:.2s;
}
.dl-step-label{font-size:10.5px; font-weight:700; color:var(--dim); text-align:center;}
.dl-step.active .dl-step-ico{border-color:var(--accent); opacity:1; box-shadow:0 0 0 4px rgba(110,91,255,0.15); animation:dlpulse 1.4s ease-in-out infinite;}
.dl-step.active .dl-step-label{color:var(--text);}
.dl-step.complete .dl-step-ico{background:var(--grad); border-color:transparent; opacity:1;}
.dl-step.complete .dl-step-label{color:var(--text);}
@keyframes dlpulse{ 0%,100%{box-shadow:0 0 0 4px rgba(110,91,255,0.15);} 50%{box-shadow:0 0 0 8px rgba(110,91,255,0.05);} }
.dl-step-line{flex:1 1 auto; height:2px; background:var(--border); margin-top:19px; min-width:16px;}
.dl-step-line.complete{background:var(--accent, #6e5bff);}
.dl-status-line{text-align:center; font-size:13px; font-weight:600; color:var(--dim); margin-top:4px;}
.dl-error-banner{
  margin-top:14px; padding:12px 14px; border-radius:10px; background:rgba(220,53,69,0.12);
  border:1px solid rgba(220,53,69,0.4); color:#ff6b7a; font-size:13px; font-weight:600;
}
@media (max-width:600px){
  .dl-step{width:60px;}
  .dl-step-label{font-size:9px;}
}

.theme-picker{margin-left:auto;position:relative;}
.theme-btn{background:var(--panel2);border:1px solid var(--border);color:var(--text);border-radius:10px;
  padding:9px 16px;font-size:13px;cursor:pointer;font-weight:600;}
.theme-btn:hover{border-color:var(--accent);}
.theme-menu{position:absolute;top:calc(100% + 8px);right:0;background:var(--panel);border:1px solid var(--border);
  border-radius:12px;padding:6px;min-width:180px;max-height:360px;overflow-y:auto;box-shadow:0 12px 32px rgba(0,0,0,0.45);z-index:1000;}
.theme-menu.hidden{display:none;}
.theme-opt{padding:10px 12px;border-radius:8px;font-size:13px;color:var(--text);cursor:pointer;display:flex;align-items:center;gap:8px;}
.theme-opt:hover{background:var(--panel2);}
.theme-opt.active{background:var(--panel2);font-weight:700;}
.theme-dot{width:14px;height:14px;border-radius:50%;flex-shrink:0;}
.wrap{max-width:1500px;margin:0 auto;padding:24px;}
.card{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:20px;margin-bottom:20px;}
.row{display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end;}
label{display:block;font-size:12px;color:var(--dim);margin-bottom:6px;}
input[type=text],input[type=number],textarea,select{
  background:var(--panel2);border:1px solid var(--border);color:var(--text);border-radius:10px;
  padding:10px 12px;font-size:14px;width:100%;}
textarea{resize:vertical;}
button{cursor:pointer;border:none;border-radius:10px;padding:10px 18px;font-size:14px;font-weight:600;
  background:var(--panel2);color:var(--text);border:1px solid var(--border);transition:.15s;}
button:hover{border-color:var(--accent);}
.btn-grad{background:var(--grad);color:#0a0a0f;border:none;}
.btn-grad:hover{filter:brightness(1.08);}
.pill{display:inline-flex;gap:6px;align-items:center;background:var(--panel2);border:1px solid var(--border);
  border-radius:999px;padding:6px 12px;font-size:12px;color:var(--dim);}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:14px;margin-top:14px;}
.clip-card{background:var(--panel2);border:1px solid var(--border);border-radius:14px;overflow:hidden;cursor:pointer;
  transition:.15s;}
.clip-card:hover{border-color:var(--accent);transform:translateY(-2px);}
.clip-card video{width:100%;display:block;aspect-ratio:9/16;object-fit:cover;background:#000;}
.clip-card .lbl{padding:8px 10px;font-size:12px;color:var(--dim);}
.editor{display:none;gap:20px;}
.editor.active{display:grid;grid-template-columns:380px 1fr;}
.stage-col{display:flex;flex-direction:column;align-items:center;gap:12px;}
.stage{position:relative;background:#000;border-radius:14px;overflow:hidden;width:100%;max-width:380px;aspect-ratio:9/16;}
.stage video{display:block;width:100%;height:100%;object-fit:cover;}
.overlay-layer{position:absolute;inset:0;}
.ov-region{position:absolute;border:2px dashed var(--accent2);box-sizing:border-box;cursor:move;}
.ov-region.kind-black{background:#000;border-style:solid;border-color:#ff5a6e;}
.ov-region.kind-blur{backdrop-filter:blur(12px);border-color:#67b7f0;}
.ov-region.kind-emoji{border:none;background-size:contain;background-repeat:no-repeat;background-position:center;}
.ov-region.kind-rect{background:transparent;border-style:solid;border-width:3px;}
.ov-region.kind-circle{background:transparent;border-style:solid;border-width:3px;border-radius:50%;}
.ov-region.kind-arrow{background:transparent;border:none;}
.ov-region.kind-arrow::after{content:'➜';position:absolute;right:-6px;top:50%;transform:translateY(-50%);font-size:20px;}
.ov-region .del{position:absolute;top:-10px;right:-10px;width:20px;height:20px;border-radius:50%;background:var(--danger);
  color:#fff;font-size:12px;display:flex;align-items:center;justify-content:center;cursor:pointer;}
.ov-text{position:absolute;cursor:move;font-weight:700;white-space:nowrap;padding:4px 8px;border-radius:6px;}
.ov-logo{position:absolute;cursor:move;}
.tabs{display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap;}
.tab{padding:8px 14px;border-radius:999px;font-size:12px;background:var(--panel2);border:1px solid var(--border);
  color:var(--dim);cursor:pointer;}
.tab.active{background:var(--grad);color:#0a0a0f;border:none;}
.tabpanel{display:none;}
.tabpanel.active{display:block;}
.slider-row{margin-bottom:14px;}
.slider-row .val{float:right;color:var(--accent2);font-size:12px;}
input[type=range]{width:100%;accent-color:var(--accent);}
.tool-row{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;}
.tool-btn{padding:7px 10px;font-size:12px;}
.tool-btn.active{background:var(--grad);color:#0a0a0f;border:none;}
.log{background:#05060a;border:1px solid var(--border);border-radius:10px;padding:10px;font-family:monospace;
  font-size:12px;color:#9fe6c9;height:90px;overflow:auto;margin-top:10px;}
.flex-between{display:flex;justify-content:space-between;align-items:center;}
.hidden{display:none !important;}
.badge{font-size:11px;padding:2px 8px;border-radius:999px;background:rgba(110,91,255,.18);color:#b4a8ff;}
.checkrow{display:flex;align-items:center;gap:8px;margin:8px 0;font-size:13px;}
.right-col{flex:1;}
.export-actions{display:flex;gap:10px;margin-top:16px;}
a.dl-link{color:var(--accent2);}
.audio-card{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:8px;font-size:12px;}
.audio-card .name{color:var(--text);font-weight:600;margin-bottom:6px;word-break:break-word;}
.audio-card .arow{display:flex;gap:6px;}
.audio-card button{padding:5px 8px;font-size:11px;flex:1;}
.audio-card button.sel{background:var(--grad);color:#0a0a0f;border:none;}
.pan-hint{font-size:11px;color:var(--dim);background:rgba(110,91,255,.12);border:1px solid var(--border);
  border-radius:8px;padding:6px 10px;margin-top:6px;}
.text-row{background:var(--panel2);border:1px solid var(--border);border-radius:10px;padding:10px;margin-bottom:10px;}
.text-row .top{display:flex;gap:8px;align-items:center;}
.text-row .top input[type=text]{flex:1;}
.text-row .del{cursor:pointer;color:var(--danger);font-size:12px;padding:6px 10px;}
.progress-container {
  background: var(--panel2);
  border: 1px solid var(--border);
  border-radius: 10px;
  height: 24px;
  width: 100%;
  overflow: hidden;
  position: relative;
  margin-top: 14px;
}
.progress-fill {
  background: var(--grad);
  height: 100%;
  width: 0%;
  transition: width 0.2s ease-out;
}
.progress-text {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Custom styles for auto-exporting overlays and buttons in clip-grid cards */
.clip-preview-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 9/16;
  background: #000;
  overflow: hidden;
}
.clip-preview-wrap video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.clip-status-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s ease;
  z-index: 5;
}
.clip-status-overlay.active {
  opacity: 1;
  pointer-events: auto;
}
.clip-status-overlay.done {
  background: rgba(16, 28, 23, 0.55);
  opacity: 1;
}
.clip-card:hover .clip-status-overlay.done {
  opacity: 0;
}
.clip-status-overlay.failed {
  background: rgba(30, 15, 15, 0.7);
  opacity: 1;
}
.clip-status-overlay.done .spinner {
  display: none;
}
.clip-status-overlay.failed .spinner {
  display: none;
}
.clip-status-overlay .spinner {
  width: 24px;
  height: 24px;
  border: 3px solid rgba(255,255,255,0.2);
  border-top-color: var(--accent2);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.clip-status-overlay .status-text {
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  text-align: center;
  padding: 0 8px;
  text-shadow: 1px 1px 3px rgba(0,0,0,0.8);
}
.clip-info {
  padding: 10px;
}
.clip-actions {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}
.clip-card-btn {
  flex: 1;
  font-size: 11px;
  padding: 6px 10px;
  text-align: center;
  border-radius: 6px;
  text-decoration: none;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: var(--panel);
  color: var(--text);
  box-sizing: border-box;
}
.clip-card-btn.edit-btn {
  background: var(--panel2);
  color: var(--text);
  border: 1px solid var(--border);
}
.clip-card-btn.edit-btn:hover {
  border-color: var(--accent);
}
.clip-card-btn.dl-btn {
  background: var(--accent2);
  color: #0c0d12;
  border: none;
}
.clip-card-btn.dl-btn:hover {
  filter: brightness(1.12);
}

/* ── Hero URL / Upload section ───────────────────────────────────────── */
.hero-row{display:flex;gap:18px;align-items:stretch;flex-wrap:wrap;}
.hero-box{
  flex:1 1 320px; min-width:280px; position:relative;
  background:linear-gradient(160deg, var(--panel2), var(--panel));
  border:1.5px solid var(--border); border-radius:18px;
  padding:22px 24px; display:flex; flex-direction:column; gap:12px;
  transition:.2s; cursor:default;
}
.hero-box:hover, .hero-box:focus-within{
  border-color:var(--accent);
  box-shadow:0 0 0 3px rgba(110,91,255,0.15), 0 8px 24px rgba(0,0,0,0.35);
}
.hero-box-upload{cursor:pointer;}
.hero-box-upload:hover{border-color:var(--accent2); box-shadow:0 0 0 3px rgba(34,211,196,0.15), 0 8px 24px rgba(0,0,0,0.35);}
.hero-icon{
  width:44px; height:44px; border-radius:12px; background:var(--grad);
  display:flex; align-items:center; justify-content:center; font-size:20px;
  box-shadow:0 4px 14px rgba(110,91,255,0.35);
}
.hero-text label{font-size:15px; font-weight:700; color:var(--text); margin:0;}
.hero-sub{font-size:12px; color:var(--dim); line-height:1.4;}
.hero-input{
  width:100%; box-sizing:border-box; padding:16px 18px; font-size:15px;
  background:var(--bg); border:1.5px solid var(--border); border-radius:12px;
  color:var(--text); margin-top:auto;
}
.hero-input:focus{outline:none; border-color:var(--accent);}
.hero-upload-btn{
  width:100%; padding:14px 18px; font-size:14px; font-weight:700; margin-top:auto;
  background:var(--grad); color:#0a0a0f; border:none; border-radius:12px;
  box-shadow:0 4px 14px rgba(34,211,196,0.25);
}
.hero-upload-btn:hover{filter:brightness(1.08);}
.hero-divider{
  align-self:center; color:var(--dim); font-size:12px; font-weight:700;
  letter-spacing:1px;
}
@media (max-width:700px){
  .hero-row{flex-direction:column;}
  .hero-divider{padding:2px 0;}
}

/* ── Settings bar + big Fetch & Cut CTA ──────────────────────────────── */
.settings-bar{
  display:flex; gap:16px; flex-wrap:wrap; align-items:flex-end;
  margin-top:18px; padding:16px 18px;
  background:var(--panel2); border:1px solid var(--border); border-radius:14px;
}
.settings-field{min-width:160px;}
.settings-field label{font-size:11px; text-transform:uppercase; letter-spacing:.5px;}
.settings-field select, .settings-field input[type=number], .settings-field textarea{
  padding:13px 14px; font-size:14px; font-weight:600;
}
.settings-check{display:flex; flex-direction:column;}
.automod-check{
  display:flex; align-items:center; gap:8px; margin:0; height:48px; padding:0 6px;
}
.automod-check span{font-weight:700; color:#ff9f0a; font-size:14px; text-shadow:0 0 10px rgba(255,159,10,0.2); white-space:nowrap;}
.automod-check input[type=checkbox]{width:18px; height:18px;}
.fetch-cta{
  display:block; width:100%; margin-top:16px; padding:20px; font-size:18px; font-weight:800;
  background:var(--grad); color:var(--btn-text); border:none; border-radius:14px;
  box-shadow:0 10px 28px rgba(110,91,255,0.4); cursor:pointer; letter-spacing:.3px;
  transition:.15s;
}
.fetch-cta:hover{filter:brightness(1.08); transform:translateY(-2px); box-shadow:0 14px 34px rgba(110,91,255,0.5);}
.fetch-cta:active{transform:translateY(0);}
.fetch-cta:disabled{transform:none;}
.btn-spinner{
  display:inline-block; width:18px; height:18px; vertical-align:middle;
  border:3px solid rgba(255,255,255,0.35); border-top-color:#fff; border-radius:50%;
  animation:btnspin .7s linear infinite;
}
@keyframes btnspin{ to{ transform:rotate(360deg); } }

</style>
</head>
<body>
<div class="topbar">
  <div class="logo">⚡ AutoShortAi</div>
  <div class="sub">Fetch → Cut → Live Edit → Save, all in one place</div>
  <div class="nav-tabs">
    <button type="button" class="nav-tab-btn active" id="studioTabBtn" onclick="showStudioView()">🎬 Studio</button>
    <button type="button" class="nav-tab-btn" id="downloaderTabBtn" onclick="showDownloaderView()">⬇️ Downloader</button>
  </div>
  <div class="theme-picker">
    <button type="button" class="theme-btn" onclick="toggleThemeMenu()">🎨 Theme</button>
    <div id="themeMenu" class="theme-menu hidden">
      <div class="theme-opt" data-t="dark-violet" onclick="setTheme('dark-violet')"><span class="theme-dot" style="background:linear-gradient(135deg,#6e5bff,#22d3c4)"></span>Dark Violet</div>
      <div class="theme-opt" data-t="light" onclick="setTheme('light')"><span class="theme-dot" style="background:linear-gradient(135deg,#5b46e0,#0891b2)"></span>Light</div>
      <div class="theme-opt" data-t="midnight-blue" onclick="setTheme('midnight-blue')"><span class="theme-dot" style="background:linear-gradient(135deg,#3b82f6,#22d3ee)"></span>Midnight Blue</div>
      <div class="theme-opt" data-t="forest" onclick="setTheme('forest')"><span class="theme-dot" style="background:linear-gradient(135deg,#16a34a,#a3e635)"></span>Forest</div>
      <div class="theme-opt" data-t="sunset" onclick="setTheme('sunset')"><span class="theme-dot" style="background:linear-gradient(135deg,#fb7185,#f59e0b)"></span>Sunset</div>
      <div class="theme-opt" data-t="ocean" onclick="setTheme('ocean')"><span class="theme-dot" style="background:linear-gradient(135deg,#06b6d4,#6366f1)"></span>Ocean</div>
      <div class="theme-opt" data-t="rose" onclick="setTheme('rose')"><span class="theme-dot" style="background:linear-gradient(135deg,#ec4899,#f472b6)"></span>Rose</div>
      <div class="theme-opt" data-t="amber" onclick="setTheme('amber')"><span class="theme-dot" style="background:linear-gradient(135deg,#f59e0b,#eab308)"></span>Amber</div>
      <div class="theme-opt" data-t="slate" onclick="setTheme('slate')"><span class="theme-dot" style="background:linear-gradient(135deg,#475569,#94a3b8)"></span>Slate</div>
      <div class="theme-opt" data-t="cyberpunk" onclick="setTheme('cyberpunk')"><span class="theme-dot" style="background:linear-gradient(135deg,#e91e9c,#00f0ff)"></span>Cyberpunk</div>
    </div>
  </div>
</div>
<div class="wrap" id="studioView">

  <div class="card" id="fetchCard">
    <div class="hero-row">
      <div class="hero-box" id="urlHeroBox">
        <div class="hero-icon">🔗</div>
        <div class="hero-text">
          <label style="margin-bottom:4px;">Paste Video URL</label>
          <span class="hero-sub">YouTube, Instagram, TikTok, Facebook, X/Twitter, Vimeo &amp; 1000+ more sites</span>
        </div>
        <input type="text" id="ytUrl" class="hero-input" placeholder="https://...">
      </div>

      <div class="hero-divider">OR</div>

      <div class="hero-box hero-box-upload" id="uploadHeroBox" onclick="document.getElementById('deviceVideoInput').click()">
        <div class="hero-icon">📁</div>
        <div class="hero-text">
          <label style="margin-bottom:4px;">Upload from PC / Device</label>
          <span class="hero-sub">Already have the video? Use it directly - stays on this device, no external server</span>
        </div>
        <input type="file" id="deviceVideoInput" accept="video/*" style="display:none" onchange="uploadDeviceVideo(this.files[0])">
        <button type="button" class="hero-upload-btn" onclick="event.stopPropagation();document.getElementById('deviceVideoInput').click()">Choose File</button>
      </div>
    </div>

    <div class="settings-bar">
      <div class="settings-field">
        <label>Quality</label>
        <select id="quality">
          <option value="best" selected>🚀 Highest Quality (Auto)</option>
          <option value="2160">4K (2160p)</option>
          <option value="1440">2K (1440p)</option>
          <option value="1080">1080p Full HD</option>
          <option value="720">720p HD</option>
        </select>
      </div>
      <div class="settings-field">
        <label>Mode</label>
        <select id="mode" onchange="toggleMode()"><option value="auto">Auto-split</option><option value="manual">Manual ranges</option></select>
      </div>
      <div id="autoLenWrap" class="settings-field">
        <label>Clip length (s)</label>
        <input type="number" id="clipLen" value="10">
      </div>
      <div class="settings-field settings-check">
        <label>&nbsp;</label>
        <div class="checkrow automod-check">
          <input type="checkbox" id="autoMode" checked>
          <span title="Automatically cut, apply settings, replace audio, and export all clips">🔥 Automod (Auto Export)</span>
        </div>
      </div>
      <div id="manualWrap" class="hidden settings-field" style="flex:2;min-width:240px;">
        <label>Ranges (start-end, one per line, seconds)</label>
        <textarea id="ranges" rows="2" placeholder="0-30
30-60"></textarea>
      </div>
    </div>
    <button class="fetch-cta" onclick="fetchAndCut()">🔻 &nbsp;Fetch &amp; Cut Video</button>
    
    <!-- YouTube Automation & Automod Settings Panel -->
    <div style="margin-top: 15px; border-top: 1px solid var(--border); padding-top: 15px;">
      <h4 style="margin: 0 0 12px 0; color: #ff9f0a; display: flex; align-items: center; gap: 8px; font-size: 14px; text-shadow: 0 0 10px rgba(255,159,10,0.2);">
        <span>🔥</span> YouTube Automation &amp; Automod Settings
      </h4>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-bottom: 8px;">
        <div>
          <label style="font-size: 11px; text-transform: uppercase; color: var(--dim); display: block; margin-bottom: 4px;">Watermark Text</label>
          <input type="text" id="automodWatermark" value="FondPeace.com" placeholder="e.g. FondPeace.com">
        </div>
        <div>
          <label style="font-size: 11px; text-transform: uppercase; color: var(--dim); display: block; margin-bottom: 4px;">Logo Font Size</label>
          <input type="number" id="automodFontSize" value="15" min="12" max="100">
        </div>
        <div style="display: flex; flex-direction: column; justify-content: center;">
          <div class="checkrow" style="margin: 0;">
            <input type="checkbox" id="automodColorVary" checked>
            <span style="font-weight: 600;">🎨 Vary color presets per clip</span>
          </div>
          <span style="font-size: 10px; color: var(--dim); margin-left: 20px; display: block; margin-top: 2px;">Bypass YouTube duplicate matched content</span>
        </div>
        <div style="display: flex; flex-direction: column; justify-content: center;">
          <div class="checkrow" style="margin: 0;">
            <input type="checkbox" id="automodMirror" checked>
            <span style="font-weight: 600;">🪞 Apply mirror flip (Horizontal)</span>
          </div>
          <span style="font-size: 10px; color: var(--dim); margin-left: 20px; display: block; margin-top: 2px;">Alternate flip to bypass identification</span>
        </div>
        <div style="display: flex; flex-direction: column; justify-content: center;">
          <div class="checkrow" style="margin: 0;">
            <input type="checkbox" id="automodAudioReplace" checked>
            <span style="font-weight: 600;">🎵 Replace background audio</span>
          </div>
          <span style="font-size: 10px; color: var(--dim); margin-left: 20px; display: block; margin-top: 2px;">Round-robin background tracks from audio/</span>
        </div>
        <div style="display: flex; flex-direction: column; justify-content: center;">
          <div class="checkrow" style="margin: 0;">
            <input type="checkbox" id="automodStartFromOne" checked>
            <span style="font-weight: 600;">⏱️ Cut precisely from Second 1</span>
          </div>
          <span style="font-size: 10px; color: var(--dim); margin-left: 20px; display: block; margin-top: 2px;">Cuts into clean 10s blocks (1-11, 11-21)</span>
        </div>
        <div style="display: flex; flex-direction: column; justify-content: center;">
          <div class="checkrow" style="margin: 0;">
            <input type="checkbox" id="automodFilmGrain" checked>
            <span style="font-weight: 600;">🎞️ Anti-Copyright Film Grain / Noise</span>
          </div>
          <span style="font-size: 10px; color: var(--dim); margin-left: 20px; display: block; margin-top: 2px;">Adds micro-noise to scramble pixel-matching hashes</span>
        </div>
        <div style="display: flex; flex-direction: column; justify-content: center;">
          <div class="checkrow" style="margin: 0;">
            <input type="checkbox" id="automodAudioPitch" checked>
            <span style="font-weight: 600;">🎙️ Anti-Copyright Audio Pitch Tuning</span>
          </div>
          <span style="font-size: 10px; color: var(--dim); margin-left: 20px; display: block; margin-top: 2px;">Micro-shift audio frequency to bypass acoustic matching</span>
        </div>
        <div style="display: flex; flex-direction: column; justify-content: center;">
          <div class="checkrow" style="margin: 0;">
            <input type="checkbox" id="automodVignette" checked>
            <span style="font-weight: 600;">📐 Dark Vignette Border Overlay</span>
          </div>
          <span style="font-size: 10px; color: var(--dim); margin-left: 20px; display: block; margin-top: 2px;">Adds corner shading to break visual fingerprinting</span>
        </div>
      </div>
    </div>

    <!-- Minimal Video Details (mirrors the Downloader tab's fetch, so you can
         see it's using the same fast resolution path right here on the main
         page) — title/description/tags + ONE best-quality video+audio file -->
    <div class="card" id="mainVideoDetailsCard" style="margin-top:12px; display:none;">
      <div style="display:flex; gap:14px; align-items:flex-start; flex-wrap:wrap;">
        <img id="mvdThumb" src="" style="width:150px; border-radius:8px; object-fit:cover; display:none;">
        <div style="flex:1; min-width:220px;">
          <h4 id="mvdTitle" style="margin:0 0 6px 0; font-size:15px;"></h4>
          <div style="font-size:12px; color:var(--dim); display:flex; gap:14px; flex-wrap:wrap; margin-bottom:8px;">
            <span id="mvdUploader"></span>
            <span id="mvdDuration"></span>
            <span id="mvdViews"></span>
          </div>
          <p id="mvdDesc" style="font-size:12.5px; color:var(--dim); line-height:1.5; margin:0 0 8px 0;"></p>
          <div id="mvdTags" style="display:flex; gap:6px; flex-wrap:wrap;"></div>
        </div>
      </div>
      <div style="margin-top:14px; border-top:1px solid var(--border); padding-top:12px; display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap;">
        <div style="font-size:12.5px;">
          🎬 Best Quality (Video + Audio, single file): <strong id="mvdBestLabel">–</strong>
        </div>
        <button class="btn-grad" id="mvdDownloadBtn" onclick="startMainDownload()" style="padding:6px 14px; font-size:12px; margin:0;">⬇ Download</button>
      </div>
      <div id="mvdDlStatus" style="font-size:12px; color:var(--dim); margin-top:8px; display:none;"></div>
    </div>

    <div class="log" id="fetchLog"></div>
  </div>

  <div class="card hidden" id="clipsCard">
    <div class="flex-between" style="align-items: center; gap: 12px; flex-wrap: wrap;">
      <h3 style="margin:0">Your Shorts</h3>
      <div style="display:flex; gap:10px; align-items:center;">
        <button class="btn-grad" id="exportAllBtn" onclick="applyToAllAndExport()" style="padding: 6px 12px; font-size:12px; margin:0; cursor:pointer;">🚀 Apply current settings to All &amp; Export Batch</button>
        <span class="badge" id="clipCount"></span>
      </div>
    </div>
    <div class="grid" id="clipGrid"></div>
  </div>

  <!-- Polished Exported Video Downloader & Batch Manager Panel -->
  <div class="card hidden" id="downloadsCard" style="margin-top: 20px;">
    <div class="flex-between" style="align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 15px;">
      <h3 style="margin:0; display:flex; align-items:center; gap:8px;">
        <span style="color:var(--yellow)">📦</span> Exported Downloads Manager
      </h3>
      <div style="display:flex; gap:10px; align-items:center;">
        <button class="btn-grad" id="downloadSelectedBtn" onclick="downloadSelectedVideos()" style="padding: 6px 12px; font-size:12px; margin:0; cursor:pointer;">📥 Download Selected</button>
        <button class="btn-grad" id="selectAllExportsBtn" onclick="toggleSelectAllExports()" style="padding: 6px 12px; font-size:12px; margin:0; cursor:pointer; background:#434348; color:#fff;">✅ Toggle All</button>
      </div>
    </div>
    
    <div style="overflow-x: auto;">
      <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
        <thead>
          <tr style="border-bottom: 2px solid var(--border); color: var(--dim);">
            <th style="padding: 8px; width: 40px;">Select</th>
            <th style="padding: 8px;">Video Title</th>
            <th style="padding: 8px;">Specifications</th>
            <th style="padding: 8px; width: 150px; text-align: right;">Actions</th>
          </tr>
        </thead>
        <tbody id="exportedVideosList">
          <tr id="emptyExportRow">
            <td colspan="4" style="padding: 20px; text-align: center; color: var(--dim);">No videos successfully exported yet. Click "Export Video" on a card or run a batch export!</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="card editor" id="editorCard">
    <div class="stage-col">
      <div class="stage" id="stage">
        <video id="player" loop playsinline></video>
        <div class="overlay-layer" id="overlayLayer"></div>
      </div>
      <div class="row" style="justify-content:center">
        <button onclick="togglePlay()" id="playBtn">▶ Play</button>
        <button onclick="closeEditor()">✕ Close</button>
      </div>
    </div>

    <div class="right-col">
      <div class="tabs">
        <div class="tab active" data-t="speed">Speed/Zoom</div>
        <div class="tab" data-t="audio">Audio/Voice</div>
        <div class="tab" data-t="text">Text/Logo</div>
        <div class="tab" data-t="shapes">Blur/Shapes</div>
        <div class="tab" data-t="color">Color</div>
        <div class="tab" data-t="export">Export</div>
      </div>

      <div class="tabpanel active" id="panel-speed">
        <div class="slider-row"><label>Speed <span class="val" id="speedVal">0.75x</span></label>
          <input type="range" id="speed" min="0.25" max="4" step="0.05" value="0.75" oninput="onSpeed()"></div>
        <div class="slider-row"><label>Zoom <span class="val" id="zoomVal">1.20x</span></label>
          <input type="range" id="zoom" min="1" max="3" step="0.05" value="1.20" oninput="onZoom()"></div>
        <p class="sub">Zoom crops toward center then re-scales to your export size with high-quality (lanczos) scaling — never stretched or pixelated.</p>
        <div class="pan-hint">🖱 When zoomed in (&gt;1.00x), <b>drag directly on the video preview</b> to move/pan which part stays in frame.</div>
      </div>

      <div class="tabpanel" id="panel-audio">
        <div class="checkrow"><input type="radio" name="amode" value="original" checked onchange="onAudioMode()"> Keep original audio</div>
        <div class="checkrow"><input type="radio" name="amode" value="mute" onchange="onAudioMode()"> Mute</div>
        <div class="checkrow"><input type="radio" name="amode" value="replace" onchange="onAudioMode()"> Replace with file</div>
        <div class="checkrow"><input type="radio" name="amode" value="tts" onchange="onAudioMode()"> AI Voiceover</div>

        <div id="replaceWrap" class="hidden">
          <label>🎵 Pick from your audio library</label>
          <div style="display:flex; gap:8px; margin:6px 0;">
            <button type="button" onclick="rescanAudioLibrary()">📱 Rescan device for audio/video</button>
            <button type="button" onclick="syncGithubAudio()">🔗 Sync library from GitHub</button>
          </div>
          <div class="grid" id="audioLibGrid" style="grid-template-columns:repeat(auto-fill,minmax(140px,1fr));"></div>
          <p class="sub">Shows files from the <code>audio/</code> folder, PLUS music/video already on this device (Music, Downloads, etc). Play each to check the fit, then hit Add to use it.</p>
          <hr style="border-color:var(--border);margin:14px 0">
          <label>...or upload your own audio file</label>
          <input type="file" id="audioFile" accept="audio/*" onchange="uploadAudio()">
          <div id="chosenAudioRow" class="hidden" style="margin-top:8px">
            <span class="badge">Selected: <span id="chosenAudioName"></span></span>
          </div>
        </div>

        <div id="ttsWrap" class="hidden">
          <label>Voice</label>
          <select id="ttsVoice">
            <option value="hi_male">Hindi — Male (Madhur, Microsoft)</option>
            <option value="hi_female">Hindi — Female (Swara, Microsoft)</option>
            <option value="gtts_hi">Hindi — Female (Google TTS, zyada natural)</option>
            <option value="en_in_male">English (India) — Male</option>
            <option value="en_in_female">English (India) — Female</option>
            <option value="en_us_male">English (US) — Male</option>
            <option value="en_us_female">English (US) — Female</option>
            <option value="gtts_en_in">English — Google TTS</option>
          </select>
          <label style="margin-top:10px">Script</label>
          <textarea id="ttsText" rows="4" placeholder="Yahan apna script likhiye..."></textarea>
          <div class="row" style="margin-top:8px">
            <button onclick="generateTTS()">🎙 Generate &amp; Preview</button>
            <div class="checkrow"><input type="checkbox" id="ttsMix"> Mix with lowered original audio</div>
          </div>
          <audio id="ttsAudio" controls class="hidden" style="width:100%;margin-top:8px"></audio>
        </div>
      </div>

      <div class="tabpanel" id="panel-text">
        <div class="flex-between"><label style="margin:0">Text layers</label>
          <button onclick="addTextLayer()">+ Add text</button></div>
        <div id="textLayersWrap"></div>
        <p class="sub">Drag any text directly on the preview to position it. Add as many as you need (titles, captions, callouts).</p>
        <hr style="border-color:var(--border);margin:14px 0">
        <div class="flex-between"><label style="margin:0">Logo / watermark image</label>
          <div class="checkrow" style="margin:0"><input type="checkbox" id="logoEnabled" checked onchange="renderLogo()"> Show on video</div></div>
        <input type="file" id="logoFile" accept="image/*" onchange="uploadLogo()">
        <div class="row" style="margin-top:8px">
          <div style="flex:1"><label>Width % <span class="val" id="logoWVal">18</span></label>
            <input type="range" id="logoW" min="5" max="50" value="18" oninput="renderLogo()"></div>
          <div style="flex:1"><label>Opacity % <span class="val" id="logoOVal">100</span></label>
            <input type="range" id="logoO" min="10" max="100" value="100" oninput="renderLogo()"></div>
        </div>
        <p class="sub">Drag the logo on the preview to position it.</p>
      </div>

      <div class="tabpanel" id="panel-shapes">
        <p class="sub">Pick a tool, then drag on the preview to draw. Blur/Black/Emoji hide something. Rect/Circle/Arrow highlight something.</p>
        <div class="tool-row">
          <button class="tool-btn active" data-k="blur" onclick="setTool('blur')">Blur</button>
          <button class="tool-btn" data-k="black" onclick="setTool('black')">Black</button>
          <button class="tool-btn" data-k="emoji" onclick="setTool('emoji')">Emoji/Sticker</button>
          <button class="tool-btn" data-k="rect" onclick="setTool('rect')">Rectangle</button>
          <button class="tool-btn" data-k="circle" onclick="setTool('circle')">Circle</button>
          <button class="tool-btn" data-k="arrow" onclick="setTool('arrow')">Arrow</button>
        </div>
        <div id="emojiUploadWrap" class="hidden">
          <label>Emoji/sticker image</label>
          <input type="file" id="emojiFile" accept="image/*" onchange="uploadEmoji()">
        </div>
        <div class="row">
          <div style="width:90px"><label>Shape color</label><input type="color" id="shapeColor" value="#ff3b30"></div>
          <button onclick="clearRegions()">Clear all regions</button>
        </div>
      </div>

      <div class="tabpanel" id="panel-color">
        <label>CapCut-style one-click look</label>
        <select id="colorPreset" onchange="onColorPresetChange()">
          <option value="none">None</option>
          <option value="vivid">Vivid Pop</option>
          <option value="cinematic">Cinematic</option>
          <option value="moody">Moody</option>
          <option value="vintage_vhs">Vintage VHS</option>
          <option value="warm_glow">Warm Glow</option>
          <option value="cool_blue">Cool Blue</option>
        </select>
        <div class="slider-row" style="margin-top:14px"><label>Contrast <span class="val" id="contrastVal">1.12</span></label>
          <input type="range" id="contrast" min="0.5" max="2" step="0.01" value="1.12" oninput="currentPresetName='none'; document.getElementById('colorPreset').value='none'; onColor()"></div>
        <div class="slider-row"><label>Saturation <span class="val" id="satVal">1.25</span></label>
          <input type="range" id="saturation" min="0" max="2" step="0.01" value="1.25" oninput="currentPresetName='none'; document.getElementById('colorPreset').value='none'; onColor()"></div>
        <div class="slider-row"><label>Brightness <span class="val" id="brightVal">0.02</span></label>
          <input type="range" id="brightness" min="-0.3" max="0.3" step="0.01" value="0.02" oninput="currentPresetName='none'; document.getElementById('colorPreset').value='none'; onColor()"></div>
        <div class="checkrow"><input type="checkbox" id="sharpen" onchange="onColor()" checked> Sharpen (clarity)</div>
        <div class="checkrow"><input type="checkbox" id="enhance" onchange="onColor()" checked> HD Enhance (denoise + detail pass — keeps quality, stops pixelation on zoom/upscale)</div>
        



        <div style="border-top:1px solid var(--border); margin:14px 0; padding-top:14px;">
          <h4 style="margin:0 0 10px 0; font-size:13px; color:var(--text);">🔄 Transformations</h4>
          <div class="row" style="margin-top:6px; gap:10px;">
            <div style="flex:1">
              <label>Rotate</label>
              <select id="rotate" onchange="onTransform()">
                <option value="0">0° (Normal)</option>
                <option value="90">90° Clockwise</option>
                <option value="180">180°</option>
                <option value="270">270°</option>
              </select>
            </div>
            <div style="flex:1; display:flex; align-items:flex-end;">
              <div class="checkrow" style="margin:0; padding-bottom:8px;"><input type="checkbox" id="hflip" onchange="onTransform()" checked> Mirror (Horizontal Flip)</div>
            </div>
          </div>
        </div>
        
        <button onclick="resetColor()" style="margin-top:12px;">Reset</button>
      </div>

      <div class="tabpanel" id="panel-export">
        <label>Resolution</label>
        <select id="resolution">
          <option value="1080x1920">1080x1920 (Shorts 9:16)</option>
          <option value="1080x1080">1080x1080 (Square)</option>
          <option value="1920x1080">1920x1080 (Landscape)</option>
          <option value="2160x3840">2160x3840 (Ultra 4K Vertical 9:16)</option>
          <option value="3840x2160">3840x2160 (Ultra 4K Landscape 16:9)</option>
          <option value="original">Keep original</option>
        </select>
        <div class="row" style="margin-top:10px">
          <div style="flex:1"><label>Format</label><select id="format"><option value="mp4">MP4 (H.264/AAC)</option>
            <option value="mov">MOV</option><option value="webm">WEBM (VP9/Opus)</option></select></div>
          <div style="flex:1"><label>Quality (CRF)</label><input type="number" id="crf" value="18" min="12" max="30"></div>
          <div style="flex:1"><label>Speed preset</label><select id="preset"><option value="ultrafast">ultrafast</option>
            <option value="fast" selected>fast</option><option value="medium">medium</option>
            <option value="slow">slow</option></select></div>
        </div>
        <p class="sub">If you don't change anything else (speed, zoom, color, regions, text, logo, audio), Save just copies the file instantly instead of re-encoding.</p>
        <div class="export-actions">
          <button class="btn-grad" id="saveBtn" onclick="saveVideo()">💾 Save Final Video</button>
        </div>
        <div class="progress-container hidden" id="exportProgressWrap">
          <div class="progress-fill" id="exportProgressFill"></div>
          <div class="progress-text" id="exportProgressText">0%</div>
        </div>
        <div class="log" id="exportLog"></div>
      </div>
    </div>
  </div>

</div>

<div class="wrap hidden" id="downloaderView">
  <div class="card" id="dlFetchCard">
    <div class="hero-row">
      <div class="hero-box" id="dlUrlHeroBox" style="width:100%;">
        <div class="hero-icon">⬇️</div>
        <div class="hero-text">
          <label style="margin-bottom:4px;">Paste Video URL to Download</label>
          <span class="hero-sub">YouTube, Instagram, TikTok, Facebook, X/Twitter, Vimeo &amp; 1000+ more sites</span>
        </div>
        <input type="text" id="dlUrl" class="hero-input" placeholder="https://...">
      </div>
    </div>
    <button class="fetch-cta" id="dlFetchBtn" onclick="fetchDownloadInfo()">🔎 &nbsp;Fetch Video Details</button>
    <div class="dl-inline-status hidden" id="dlLog"></div>
  </div>

  <div class="card hidden" id="dlInfoCard">
    <div class="dl-info-row">
      <div class="dl-thumb-wrap">
        <img id="dlThumbMain" class="dl-thumb-main" src="" alt="thumbnail">
        <div class="dl-thumb-strip" id="dlThumbStrip"></div>
      </div>
      <div class="dl-meta">
        <div class="dl-title-row">
          <h3 id="dlTitle" class="dl-title"></h3>
          <button class="dl-copy-icon-btn" title="Copy title" onclick="copyDlValue(document.getElementById('dlTitle').textContent, this)">📋</button>
        </div>
        <div class="dl-meta-badges" id="dlMetaBadges"></div>
        <div class="dl-copy-row">
          <input type="text" id="dlPageUrl" readonly>
          <button class="clip-card-btn" onclick="copyDlText('dlPageUrl')">📋 Copy Link</button>
        </div>
      </div>
    </div>

    <h4 class="dl-section-title">Full Video Details</h4>
    <div class="dl-details-grid" id="dlDetailsGrid"></div>

    <div class="dl-desc-wrap" id="dlDescWrap" style="display:none;">
      <div class="dl-desc-head">
        <span>Description</span>
        <div style="display:flex; gap:6px;">
          <button class="dl-copy-icon-btn" title="Copy description" id="dlDescCopyBtn">📋</button>
          <button class="dl-copy-icon-btn" title="Expand / collapse" id="dlDescToggleBtn">⬇️</button>
        </div>
      </div>
      <div class="dl-desc-text collapsed" id="dlDescText"></div>
    </div>

    <div class="dl-chips-wrap" id="dlCategoriesWrap" style="display:none;">
      <span class="dl-chips-label">Categories</span>
      <div class="dl-chips" id="dlCategoriesChips"></div>
    </div>
    <div class="dl-chips-wrap" id="dlTagsWrap" style="display:none;">
      <span class="dl-chips-label">Tags</span>
      <div class="dl-chips" id="dlTagsChips"></div>
    </div>

    <h4 class="dl-section-title">Available Formats &amp; Quality</h4>
    <div class="dl-formats-table-wrap">
      <table class="dl-formats-table" id="dlFormatsTable">
        <thead>
          <tr>
            <th>Type</th><th>Quality</th><th>Format</th><th>Codec</th><th>Size</th><th></th>
          </tr>
        </thead>
        <tbody id="dlFormatsBody"></tbody>
      </table>
    </div>
  </div>

  <div class="card hidden" id="dlProgressCard">
    <h4 class="dl-section-title" style="margin-top:0;" id="dlProgressTitle">Downloading…</h4>

    <div class="dl-stepper" id="dlStepper">
      <div class="dl-step" data-step="connect"><div class="dl-step-ico">🔗</div><div class="dl-step-label">Connecting</div></div>
      <div class="dl-step-line" data-line="1"></div>
      <div class="dl-step" data-step="download"><div class="dl-step-ico">⬇️</div><div class="dl-step-label">Downloading</div></div>
      <div class="dl-step-line" data-line="2"></div>
      <div class="dl-step" data-step="merge"><div class="dl-step-ico">🔀</div><div class="dl-step-label">Merging</div></div>
      <div class="dl-step-line" data-line="3"></div>
      <div class="dl-step" data-step="done"><div class="dl-step-ico">✅</div><div class="dl-step-label">Ready</div></div>
    </div>

    <div class="dl-progress-stats">
      <div class="dl-stat"><span class="dl-stat-label">Progress</span><span class="dl-stat-val" id="dlPercentVal">0%</span></div>
      <div class="dl-stat"><span class="dl-stat-label">Downloaded</span><span class="dl-stat-val" id="dlSizeVal">0 MB / 0 MB</span></div>
      <div class="dl-stat"><span class="dl-stat-label">Speed</span><span class="dl-stat-val" id="dlSpeedVal">– MB/s</span></div>
      <div class="dl-stat"><span class="dl-stat-label">Time Left</span><span class="dl-stat-val" id="dlEtaVal">–</span></div>
    </div>
    <div class="progress-container" id="dlProgressWrap">
      <div class="progress-fill" id="dlProgressFill" style="width:0%"></div>
      <div class="progress-text" id="dlProgressText">0%</div>
    </div>
    <div class="dl-status-line" id="dlStatusLine">Getting things ready…</div>
    <div class="dl-error-banner hidden" id="dlErrorBanner"></div>
  </div>
</div>

<script>
// ── Theme system ─────────────────────────────────────────────────────────
(function(){
  const saved = localStorage.getItem('shortsStudioTheme') || 'dark-violet';
  if(saved !== 'dark-violet') document.documentElement.setAttribute('data-theme', saved);
})();
function toggleThemeMenu(){
  document.getElementById('themeMenu').classList.toggle('hidden');
  markActiveTheme();
}
function setTheme(name){
  if(name === 'dark-violet'){
    document.documentElement.removeAttribute('data-theme'); // it's the default :root palette
  } else {
    document.documentElement.setAttribute('data-theme', name);
  }
  localStorage.setItem('shortsStudioTheme', name);
  document.getElementById('themeMenu').classList.add('hidden');
}
function markActiveTheme(){
  const current = localStorage.getItem('shortsStudioTheme') || 'dark-violet';
  document.querySelectorAll('.theme-opt').forEach(el=>{
    el.classList.toggle('active', el.getAttribute('data-t') === current);
  });
}
document.addEventListener('click', function(e){
  const picker = document.querySelector('.theme-picker');
  const menu = document.getElementById('themeMenu');
  if(picker && menu && !picker.contains(e.target)) menu.classList.add('hidden');
});

let currentClipId = null, ttsUrl = null, audioFileUrl = null, logoUrl = null;
let regions = [], logoState = {x:0.78,y:0.04};
let textLayers = []; // {id, content, x, y, size, color, box}
let tool = 'blur';
let panX = 0, panY = 0; // manual drag-to-pan, -1..1 each axis, only used when zoom>1
let clipSettingsMap = {};

let audioLibraryFiles = null;
let exportQueue = [];
let exportQueueActive = false;
let currentPresetName = 'none';
let allClips = [];

const JS_COLOR_PRESETS = {
  none: {},
  vivid: {contrast: 1.15, saturation: 1.35, brightness: 0.02},
  cinematic: {contrast: 1.2, saturation: 0.85, brightness: -0.02},
  moody: {contrast: 1.25, saturation: 0.7, brightness: -0.05},
  vintage_vhs: {contrast: 0.95, saturation: 0.8, brightness: 0.0},
  warm_glow: {contrast: 1.08, saturation: 1.2, brightness: 0.03},
  cool_blue: {contrast: 1.1, saturation: 1.05, brightness: 0.0}
};

function toggleMode(){
  const m = document.getElementById('mode').value;
  document.getElementById('autoLenWrap').classList.toggle('hidden', m!=='auto');
  document.getElementById('manualWrap').classList.toggle('hidden', m!=='manual');
}

function log(el, msg){ const l=document.getElementById(el); l.innerHTML += msg+"<br>"; l.scrollTop=l.scrollHeight; }

function addClipCard(c){
  document.getElementById('clipsCard').classList.remove('hidden');
  const grid = document.getElementById('clipGrid');
  
  // Ensure we don't duplicate card elements if called twice for some reason
  let div = document.getElementById('card_' + c.clip_id);
  if (div) {
    return;
  }
  
  // Track all clips for batch operations
  if (!allClips.some(x => x.clip_id === c.clip_id)) {
    allClips.push(c);
  }
  document.getElementById('clipCount').innerText = allClips.length + ' clips';

  // Initialize clipSettingsMap for this clip
  if (!clipSettingsMap[c.clip_id]) {
    // 1. Color variation
    let selectedPreset = 'none';
    let contrastVal = 1.12;
    let saturationVal = 1.25;
    let brightnessVal = 0.02;
    
    const colorsChecked = document.getElementById('automodColorVary') ? document.getElementById('automodColorVary').checked : true;
    if (colorsChecked) {
      const presets = ['vivid', 'cinematic', 'moody', 'warm_glow', 'cool_blue'];
      selectedPreset = presets[Math.floor(Math.random() * presets.length)];
      const vals = JS_COLOR_PRESETS[selectedPreset];
      contrastVal = vals.contrast;
      saturationVal = vals.saturation;
      brightnessVal = vals.brightness;
    }
    
    // 2. Watermark / Logo text
    const watermarkText = document.getElementById('automodWatermark') ? document.getElementById('automodWatermark').value : 'FondPeace.com';
    const watermarkSize = document.getElementById('automodFontSize') ? parseInt(document.getElementById('automodFontSize').value) : 36;
    
    const defaultTexts = [];
    if (watermarkText) {
      defaultTexts.push({
        id: 'txt_watermark',
        content: watermarkText,
        x: 0.55, // Center right x-coordinate
        y: 0.45, // Center y-coordinate
        size: watermarkSize,
        color: '#ffffff',
        box: false,
        enabled: true
      });
    }
    
    // 3. Mirroring
    const mirrorChecked = document.getElementById('automodMirror') ? document.getElementById('automodMirror').checked : true;
    // Alternate mirroring or always on? Let's make it so if mirror is checked, we alternate or apply it
    // Let's make it alternate: odd indexed clips are mirrored, even are normal, to make them non-similar
    const isMirrored = mirrorChecked ? (c.index % 2 === 1) : false;
    
    // 4. Background Audio selection round-robin
    const replaceAudioChecked = document.getElementById('automodAudioReplace') ? document.getElementById('automodAudioReplace').checked : true;
    let chosenAudioUrl = null;
    if (replaceAudioChecked && audioLibraryFiles && audioLibraryFiles.length > 0) {
      chosenAudioUrl = audioLibraryFiles[(c.index - 1) % audioLibraryFiles.length].url;
    }

    const grainChecked = document.getElementById('automodFilmGrain') ? document.getElementById('automodFilmGrain').checked : true;
    const pitchChecked = document.getElementById('automodAudioPitch') ? document.getElementById('automodAudioPitch').checked : true;
    const vignetteChecked = document.getElementById('automodVignette') ? document.getElementById('automodVignette').checked : true;
    
    clipSettingsMap[c.clip_id] = {
      speed: 0.75,
      zoom: 1.20,
      pan_x: 0,
      pan_y: 0,
      contrast: contrastVal,
      saturation: saturationVal,
      brightness: brightnessVal,
      sharpen: true,
      enhance: true,
      film_grain: grainChecked,
      audio_pitch: pitchChecked,
      vignette: vignetteChecked,
      color_preset: selectedPreset,
      resolution: '1080x1920',
      format: 'mp4',
      crf: 18,
      preset: 'fast',
      regions: [],
      audio_mode: chosenAudioUrl ? 'replace' : 'original',
      audio_file_url: chosenAudioUrl,
      tts_url: null,
      tts_mix: false,
      mute: false,
      texts: defaultTexts,
      logo: null,
      rotate: '0',
      hflip: isMirrored,
      stage_w: 360,
      stage_h: 640
    };
  }

  const s = clipSettingsMap[c.clip_id];

  div = document.createElement('div');
  div.className = 'clip-card';
  div.id = 'card_' + c.clip_id;
  div.dataset.index = c.index;
  
  // Set direct CSS mirror transform on card video if active
  const mirrorStyle = s.hflip ? 'transform: scaleX(-1);' : '';
  
  div.innerHTML = `
    <div class="clip-preview-wrap">
      <video src="/media/${c.clip_id}" muted style="${mirrorStyle}" loop></video>
      <div class="clip-status-overlay" id="status_overlay_${c.clip_id}">
        <div class="spinner"></div>
        <div class="status-text" id="status_txt_${c.clip_id}">Waiting to export...</div>
      </div>
    </div>
    <div class="clip-info" style="padding: 10px;">
      <div class="lbl" style="padding:0; margin-bottom:4px; font-weight:700; color:var(--text); font-size:13px;">${c.label}</div>
      
      <!-- Automated Settings Badges -->
      <div id="badges_${c.clip_id}"></div>
      
      <!-- Actions Grid -->
      <div class="clip-actions" id="actions_${c.clip_id}" style="margin-top: 10px; display: flex; flex-direction: column; gap: 6px;">
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 6px;">
          <button class="clip-card-btn edit-btn" style="padding: 6px 4px; font-size:11px;" onclick="event.stopPropagation(); openEditor('${c.clip_id}')">⚙️ Edit Settings</button>
          <button class="clip-card-btn mirror-btn" style="padding: 6px 4px; font-size:11px; background:#434348; color:#fff;" onclick="event.stopPropagation(); toggleCardMirror('${c.clip_id}')">🪞 Toggle Mirror</button>
        </div>
        <button class="clip-card-btn export-single-btn" style="width:100%; padding: 6px 4px; font-size:11px; background:var(--grad); color:#000;" onclick="event.stopPropagation(); exportSingleClip('${c.clip_id}')">🚀 Export Video</button>
      </div>
    </div>
  `;
  
  // Custom video play/pause on click
  const videoEl = div.querySelector('video');
  videoEl.onclick = (e) => {
    e.stopPropagation();
    if (videoEl.paused) {
      document.querySelectorAll('.clip-card video').forEach(v => {
        if (v !== videoEl) v.pause();
      });
      videoEl.play();
    } else {
      videoEl.pause();
    }
  };
  
  div.onclick = () => openEditor(c.clip_id);
  grid.appendChild(div);

  // Dynamic DOM sorting: keep the clips strictly sequential (Short 1, Short 2, Short 3...)
  const cards = Array.from(grid.children);
  cards.sort((a, b) => parseInt(a.dataset.index || 0) - parseInt(b.dataset.index || 0));
  cards.forEach(card => grid.appendChild(card));
  
  // Render settings badges inside the card
  updateClipCardBadge(c.clip_id);
}

async function uploadDeviceVideo(file){
  if(!file) return;
  setFetchBtnLoading(true, 'Uploading your video…');
  log('fetchLog', '⏳ Uploading your video from this device (stays local, no external server)...');
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch('/api/upload', {method:'POST', body: fd});
  const data = await res.json();
  if(!data.url){ log('fetchLog', '❌ Upload failed'); setFetchBtnLoading(false); return; }
  document.getElementById('ytUrl').value = ''; // visually clear the URL field, we're using the upload instead
  await fetchAndCut(data.url);
}

// Toggles the big "Fetch & Cut" button between its normal state and a
// disabled, spinning, "working on it" state — so the user always has a
// clear, immediate visual signal that something is happening the moment
// they add a URL/device video, without needing to click anything else.
function setFetchBtnLoading(isLoading, label){
  const btn = document.querySelector('.fetch-cta');
  if(!btn) return;
  if(isLoading){
    if(!btn.dataset.origHtml) btn.dataset.origHtml = btn.innerHTML;
    btn.disabled = true;
    btn.style.opacity = '0.85';
    btn.style.cursor = 'wait';
    btn.innerHTML = `<span class="btn-spinner"></span>&nbsp;${label || 'Working…'}`;
  } else {
    btn.disabled = false;
    btn.style.opacity = '';
    btn.style.cursor = '';
    if(btn.dataset.origHtml) btn.innerHTML = btn.dataset.origHtml;
  }
}

// Minimal video-details panel below Automod Settings — powered entirely by
// THIS file's own /api/main_video_info + /api/main_download/* routes (see
// the Python section above), not the separate downloader.py module. Same
// caching under the hood as the cutting pipeline, so this is a true,
// self-contained "is resolution working / how fast is it" indicator.
let mvdCurrentUrl = null;

async function loadMainVideoDetails(url){
  mvdCurrentUrl = url;
  const card = document.getElementById('mainVideoDetailsCard');
  card.style.display = '';
  document.getElementById('mvdTitle').textContent = '⏳ Loading video details…';
  document.getElementById('mvdUploader').textContent = '';
  document.getElementById('mvdDuration').textContent = '';
  document.getElementById('mvdViews').textContent = '';
  document.getElementById('mvdDesc').textContent = '';
  document.getElementById('mvdTags').innerHTML = '';
  document.getElementById('mvdThumb').style.display = 'none';
  document.getElementById('mvdBestLabel').textContent = '–';
  document.getElementById('mvdDlStatus').style.display = 'none';

  const t0 = performance.now();
  let res, data;
  try {
    res = await fetch('/api/main_video_info', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({url})
    });
    data = await res.json();
  } catch(e) {
    document.getElementById('mvdTitle').textContent = '❌ Could not load video details';
    return;
  }
  const secs = ((performance.now() - t0) / 1000).toFixed(1);
  if (data.error) {
    document.getElementById('mvdTitle').textContent = '❌ ' + data.error;
    return;
  }

  document.getElementById('mvdTitle').textContent = data.title || 'Untitled';
  document.getElementById('mvdUploader').textContent = data.uploader ? `👤 ${data.uploader}` : '';
  document.getElementById('mvdDuration').textContent = data.duration_str ? `⏱ ${data.duration_str}` : '';
  document.getElementById('mvdViews').textContent = data.view_count_str ? `👁 ${data.view_count_str} views` : '';

  const desc = (data.description || '').trim();
  document.getElementById('mvdDesc').textContent = desc
    ? (desc.length > 220 ? desc.slice(0, 220) + '…' : desc)
    : 'No description.';

  const tagWrap = document.getElementById('mvdTags');
  tagWrap.innerHTML = '';
  (data.tags || []).slice(0, 8).forEach(t => {
    const s = document.createElement('span');
    s.textContent = t;
    s.style.cssText = 'background:rgba(255,159,10,0.12); color:#ff9f0a; padding:2px 8px; border-radius:10px; font-size:11px;';
    tagWrap.appendChild(s);
  });

  if (data.thumbnail) {
    const img = document.getElementById('mvdThumb');
    img.src = data.thumbnail;
    img.style.display = '';
  }

  // Download always merges video+audio into a single output file (backend
  // defaults to bestvideo+bestaudio/best -> merged mp4), so show the true
  // best resolution/size rather than a possibly-lower native combined format.
  document.getElementById('mvdBestLabel').textContent =
    `${data.resolution || 'Best available'} • ${data.best_filesize_str || '~unknown'} (audio included)`;

  log('fetchLog', `📋 Video details loaded in ${secs}s`);
}

async function startMainDownload(){
  if (!mvdCurrentUrl) return;
  const statusEl = document.getElementById('mvdDlStatus');
  statusEl.style.display = '';
  statusEl.textContent = '⏳ Starting download…';

  let res, data;
  try {
    // Backend always does bestvideo+bestaudio/best, merged into a single
    // mp4 — exactly the "one high-quality file" being asked for.
    res = await fetch('/api/main_download/start', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({url: mvdCurrentUrl})
    });
    data = await res.json();
  } catch(e) {
    statusEl.textContent = '❌ Network error starting download';
    return;
  }
  if (data.error) { statusEl.textContent = '❌ ' + data.error; return; }

  const dlId = data.dl_id;
  let done = false;
  while (!done) {
    await new Promise(r => setTimeout(r, 700));
    let pd;
    try {
      const st = await fetch(`/api/main_download/progress/${dlId}`);
      pd = await st.json();
    } catch(e) { continue; }
    if (pd.error) { statusEl.textContent = '❌ ' + pd.error; return; }

    const pct = pd.percent != null ? pd.percent : 0;
    if (pd.status === 'downloading') {
      statusEl.textContent = `⬇ Downloading… ${pct}% (${pd.speed_str || ''})`;
    } else if (pd.status === 'processing') {
      statusEl.textContent = '⚙️ Merging audio & video…';
    } else if (pd.status === 'done') {
      done = true;
      statusEl.textContent = '✅ Done — saving to your device…';
      triggerInlineDownload(`/api/main_download/file/${dlId}`, pd.filename);
    } else if (pd.status === 'error') {
      done = true;
      statusEl.textContent = '❌ ' + (pd.error || 'Download failed');
    }
  }
}

async function fetchAndCut(localPath){
  const url = document.getElementById('ytUrl').value.trim();
  if(!localPath && !url){ alert('Paste a video URL first, or use "Upload from PC/Device"'); return; }
  
  setFetchBtnLoading(true, localPath ? 'Preparing uploaded video…' : 'Fetching video…');

  // Preload audio library upfront so card generation can use tracks round-robin immediately
  if (!audioLibraryFiles) {
    try {
      const audioRes = await fetch('/api/audio_library');
      const audioData = await audioRes.json();
      audioLibraryFiles = audioData.files || [];
    } catch(e) {
      console.warn("Could not preload audio library upfront", e);
    }
  }

  const mode = document.getElementById('mode').value;
  const startFromOneVal = document.getElementById('automodStartFromOne') ? document.getElementById('automodStartFromOne').checked : true;
  const payload = { 
    url, 
    local_path: localPath || '',
    quality: document.getElementById('quality').value, 
    mode,
    clip_len: document.getElementById('clipLen').value,
    start_from_one: startFromOneVal
  };
  if(mode === 'manual'){
    payload.ranges = document.getElementById('ranges').value.trim().split('\n').map(l=>l.split('-').map(Number)).filter(r=>r.length===2);
  }
  document.getElementById('clipGrid').innerHTML = '';
  document.getElementById('clipsCard').classList.add('hidden');

  // Show minimal video details (title/description/tags/best single-file
  // quality) right below the Automod settings — same fast cached-auth path
  // as the Downloader tab uses, fired in parallel so it never blocks cutting.
  if (!localPath && url) {
    loadMainVideoDetails(url);
  }
  
  // Reset all state for new batch
  allClips = [];
  exportQueue = [];
  exportQueueActive = false;
  const t0 = performance.now();
  log('fetchLog', localPath ? '⏳ Preparing your uploaded video...' : '⏳ Resolving video...');
  let res, data;
  try{
    res = await fetch('/api/fetch_and_cut', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
    data = await res.json();
  } catch(e){
    log('fetchLog', '❌ Network error while starting fetch'); setFetchBtnLoading(false); return;
  }
  if(data.error){ log('fetchLog', '❌ '+data.error); setFetchBtnLoading(false); return; }
  const jobId = data.job_id;
  const processedClipIds = new Set();
  let done = false, total = 0;
  setFetchBtnLoading(true, 'Cutting shorts…');
  while(!done){
    await new Promise(r=>setTimeout(r, 700));
    const st = await fetch(`/api/cut_status/${jobId}`);
    const sd = await st.json();
    if(sd.error){ log('fetchLog', '❌ '+sd.error); setFetchBtnLoading(false); return; }
    total = sd.total;
    sd.clips.forEach(c=>{
      if (!processedClipIds.has(c.clip_id)) {
        processedClipIds.add(c.clip_id);
        addClipCard(c); // each short appears the moment it's ready, no waiting for the rest
        log('fetchLog', `✅ Short ${c.index}/${total||'?'} ready — "${c.label}"`);
        setFetchBtnLoading(true, `Cutting… ${processedClipIds.size}/${total||'?'} ready`);
        // Add to automatic queue for background export if Automod is enabled!
        if (document.getElementById('autoMode') && document.getElementById('autoMode').checked) {
          exportQueue.push(c);
          pumpExportQueue();
        }
      }
    });
    done = sd.done;
  }
  const secs = ((performance.now()-t0)/1000).toFixed(1);
  log('fetchLog', `🎉 All ${total} short(s) from "${jobId}" ready in ${secs}s — click any to edit & save.`);
  loadAudioLibrary();
  setFetchBtnLoading(false);
}

// Pressing Enter in the URL field acts exactly like clicking "Fetch & Cut Video" —
// works the same on PC, tablet, or phone keyboards.
document.addEventListener('DOMContentLoaded', () => {
  const ytUrlInput = document.getElementById('ytUrl');
  if(ytUrlInput){
    ytUrlInput.addEventListener('keydown', (e) => {
      if(e.key === 'Enter'){
        e.preventDefault();
        fetchAndCut();
      }
    });
  }
});


function openEditor(clipId){
  currentClipId = clipId;
  const s = clipSettingsMap[clipId] || {
    speed: 0.75, zoom: 1.20, pan_x: 0, pan_y: 0,
    contrast: 1.12, saturation: 1.25, brightness: 0.02,
    sharpen: true, enhance: true, color_preset: 'none',
    resolution: '1080x1920', format: 'mp4', crf: 18, preset: 'fast',
    regions: [], audio_mode: 'original', audio_file_url: null,
    tts_url: null, tts_mix: false, texts: [], logo: null, rotate: '0', hflip: true
  };
  
  regions = s.regions || [];
  ttsUrl = s.tts_url;
  audioFileUrl = s.audio_file_url;
  logoUrl = s.logo ? s.logo.url : null;
  panX = s.pan_x || 0;
  panY = s.pan_y || 0;
  
  // Clone text layers
  textLayers = s.texts ? s.texts.map(t => ({
    id: t.id || 'txt'+Date.now()+'_'+Math.random(),
    content: t.content,
    x: t.x,
    y: t.y,
    size: t.size,
    color: t.color,
    box: t.box,
    enabled: t.enabled !== false
  })) : [];
  
  document.getElementById('overlayLayer').innerHTML='';
  document.getElementById('textLayersWrap').innerHTML='';
  
  // Render each text layer
  textLayers.forEach(l => {
    renderTextPanelRow(l);
    renderTextOnStage(l);
  });
  
  if (audioFileUrl) {
    document.getElementById('chosenAudioRow').classList.remove('hidden');
    document.getElementById('chosenAudioName').innerText = audioFileUrl.split('/').pop();
  } else {
    document.getElementById('chosenAudioRow').classList.add('hidden');
  }
  
  document.getElementById('colorPreset').value = s.color_preset || 'none';
  document.getElementById('enhance').checked = s.enhance;
  document.getElementById('sharpen').checked = s.sharpen;
  
  if (s.logo) {
    document.getElementById('logoEnabled').checked = true;
    document.getElementById('logoW').value = Math.round(s.logo.w * 100);
    document.getElementById('logoO').value = Math.round(s.logo.opacity * 100);
    logoUrl = s.logo.url;
    logoState = { x: s.logo.x, y: s.logo.y };
    renderLogo();
  } else {
    document.getElementById('logoEnabled').checked = false;
    const logoImg = document.getElementById('ovLogo');
    if (logoImg) logoImg.style.display = 'none';
  }
  
  document.getElementById('editorCard').classList.add('active');
  const player = document.getElementById('player');
  player.src = '/media/'+clipId;
  player.style.objectPosition = '50% 50%';
  player.muted = false;
  
  // Select matching audio mode radio
  const amodeRadios = document.querySelectorAll('input[name=amode]');
  amodeRadios.forEach(r => {
    r.checked = (r.value === s.audio_mode);
  });
  onAudioMode();
  
  // Set values and trigger callbacks
  document.getElementById('contrast').value = s.contrast;
  document.getElementById('saturation').value = s.saturation;
  document.getElementById('brightness').value = s.brightness;
  onColor();
  
  document.getElementById('speed').value = s.speed;
  onSpeed();
  
  document.getElementById('zoom').value = s.zoom;
  onZoom();
  
  document.getElementById('rotate').value = s.rotate;
  document.getElementById('hflip').checked = s.hflip;
  onTransform();
  
  window.scrollTo({top: document.getElementById('editorCard').offsetTop-20, behavior:'smooth'});
}
function closeEditor(){ document.getElementById('editorCard').classList.remove('active'); document.getElementById('player').pause(); }

function togglePlay(){
  const p = document.getElementById('player');
  if(p.paused){ p.play(); document.getElementById('playBtn').innerText='⏸ Pause'; }
  else { p.pause(); document.getElementById('playBtn').innerText='▶ Play'; }
}

document.querySelectorAll('.tab').forEach(t=>{
  t.onclick = ()=>{
    document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
    document.querySelectorAll('.tabpanel').forEach(x=>x.classList.remove('active'));
    t.classList.add('active');
    document.getElementById('panel-'+t.dataset.t).classList.add('active');
  };
});

function onSpeed(){
  const v = parseFloat(document.getElementById('speed').value);
  document.getElementById('speedVal').innerText = v.toFixed(2)+'x';
  document.getElementById('player').playbackRate = v;
  saveCurrentSettingsToMap();
}
function onZoom(){
  const v = parseFloat(document.getElementById('zoom').value);
  document.getElementById('zoomVal').innerText = v.toFixed(2)+'x';
  applyZoomPan(v);
  saveCurrentSettingsToMap();
}
function updatePreviewTransforms() {
  const v = parseFloat(document.getElementById('zoom').value || 1.0);
  const rotate = document.getElementById('rotate').value || '0';
  const hflip = document.getElementById('hflip').checked;
  const player = document.getElementById('player');
  
  const tx = panX * 50 * (v-1)/Math.max(v,1.001);
  const ty = panY * 50 * (v-1)/Math.max(v,1.001);
  
  let transformStr = `scale(${v}) translate(${tx}%, ${ty}%) `;
  if (hflip) transformStr += "scaleX(-1) ";
  if (rotate !== "0") transformStr += `rotate(${rotate}deg) `;
  
  player.style.transform = transformStr.trim();
}
function applyZoomPan(v){
  updatePreviewTransforms();
}
(function initPanDrag(){
  const player = document.getElementById('player');
  player.addEventListener('mousedown', (e)=>{
    const v = parseFloat(document.getElementById('zoom').value);
    if(v <= 1.001) return; // nothing to pan when not zoomed
    e.preventDefault(); e.stopPropagation();
    const stage = document.getElementById('stage');
    const rect = stage.getBoundingClientRect();
    const startX = e.clientX, startY = e.clientY, startPanX = panX, startPanY = panY;
    function move(ev){
      panX = Math.max(-1, Math.min(1, startPanX - (ev.clientX-startX)/rect.width*2));
      panY = Math.max(-1, Math.min(1, startPanY - (ev.clientY-startY)/rect.height*2));
      applyZoomPan(parseFloat(document.getElementById('zoom').value));
    }
    function up(){ document.removeEventListener('mousemove', move); document.removeEventListener('mouseup', up); }
    document.addEventListener('mousemove', move); document.addEventListener('mouseup', up);
  });
})();
function onColor(){
  const c = document.getElementById('contrast').value, s = document.getElementById('saturation').value, b = document.getElementById('brightness').value;
  document.getElementById('contrastVal').innerText = parseFloat(c).toFixed(2);
  document.getElementById('satVal').innerText = parseFloat(s).toFixed(2);
  document.getElementById('brightVal').innerText = parseFloat(b).toFixed(2);
  const brightPct = 1 + parseFloat(b);
  document.getElementById('player').style.filter = `contrast(${c}) saturate(${s}) brightness(${brightPct})`;
  saveCurrentSettingsToMap();
}
function resetColor(){
  document.getElementById('contrast').value=1.12; document.getElementById('saturation').value=1.25;
  document.getElementById('brightness').value=0.02; document.getElementById('sharpen').checked=true;
  document.getElementById('enhance').checked=true;
  document.getElementById('colorPreset').value='none';
  onColor();
}

function onAudioMode(){
  const mode = document.querySelector('input[name=amode]:checked').value;
  document.getElementById('replaceWrap').classList.toggle('hidden', mode!=='replace');
  document.getElementById('ttsWrap').classList.toggle('hidden', mode!=='tts');
  document.getElementById('player').muted = (mode==='mute');
  if(mode === 'replace') loadAudioLibrary();
  saveCurrentSettingsToMap();
}

let audioLibCache = null;
async function loadAudioLibrary(){
  const grid = document.getElementById('audioLibGrid');
  if(audioLibCache){ renderAudioLibrary(); return; }
  const res = await fetch('/api/audio_library');
  const data = await res.json();
  audioLibCache = data.files || [];
  renderAudioLibrary();
}

async function rescanAudioLibrary(){
  audioLibCache = null; // force a fresh fetch, which re-scans device folders too
  await loadAudioLibrary();
}

async function syncGithubAudio(){
  const manifestUrl = prompt(
    "Paste the raw GitHub URL of your audio manifest JSON\n" +
    "(a file listing [{name,url}, ...] pointing at your .mp3 files on GitHub):"
  );
  if(!manifestUrl) return;
  const res = await fetch('/api/sync_github_audio', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({manifest_url: manifestUrl})
  });
  const data = await res.json();
  if(data.error){ alert("Sync failed: " + data.error); return; }
  alert(`Added ${data.added.length} new track(s) from GitHub.`);
  await rescanAudioLibrary();
}

function renderAudioLibrary(){
  const grid = document.getElementById('audioLibGrid'); grid.innerHTML='';
  if(!audioLibCache.length){
    grid.innerHTML = '<p class="sub">No .mp3 files found — drop some into the <code>audio/</code> folder next to the script and reopen this panel.</p>';
    return;
  }
  audioLibCache.forEach(f=>{
    const card = document.createElement('div'); card.className='audio-card';
    card.innerHTML = `<div class="name">🎵 ${f.name}</div>
      <audio id="prev_${f.filename}" src="${f.url}" style="display:none"></audio>
      <div class="arow">
        <button onclick="previewAudio('${f.filename}')">▶ Play</button>
        <button id="sel_${f.filename}" onclick="selectLibAudio('${f.url}','${f.name}','${f.filename}')">+ Add</button>
      </div>`;
    grid.appendChild(card);
  });
}
let currentPreview = null;
function previewAudio(fname){
  if(currentPreview && currentPreview !== fname){
    const prev = document.getElementById('prev_'+currentPreview);
    if(prev){ prev.pause(); prev.currentTime = 0; }
  }
  const a = document.getElementById('prev_'+fname);
  if(a.paused){ a.play(); currentPreview = fname; } else { a.pause(); }
}
function selectLibAudio(url, name, fname){
  audioFileUrl = url;
  document.querySelectorAll('.audio-card button.sel').forEach(b=>b.classList.remove('sel'));
  document.getElementById('sel_'+fname).classList.add('sel');
  document.getElementById('chosenAudioRow').classList.remove('hidden');
  document.getElementById('chosenAudioName').innerText = name;
  saveCurrentSettingsToMap();
}

async function uploadAudio(){
  const f = document.getElementById('audioFile').files[0]; if(!f) return;
  const fd = new FormData(); fd.append('file', f);
  const res = await fetch('/api/upload', {method:'POST', body: fd});
  const data = await res.json(); audioFileUrl = data.url;
  document.querySelectorAll('.audio-card button.sel').forEach(b=>b.classList.remove('sel'));
  document.getElementById('chosenAudioRow').classList.remove('hidden');
  document.getElementById('chosenAudioName').innerText = f.name + ' (uploaded)';
  saveCurrentSettingsToMap();
}
async function uploadLogo(){
  const f = document.getElementById('logoFile').files[0]; if(!f) return;
  const fd = new FormData(); fd.append('file', f);
  const res = await fetch('/api/upload', {method:'POST', body: fd});
  const data = await res.json(); logoUrl = data.url;
  renderLogo();
}
let pendingEmojiUrl = null;
async function uploadEmoji(){
  const f = document.getElementById('emojiFile').files[0]; if(!f) return;
  const fd = new FormData(); fd.append('file', f);
  const res = await fetch('/api/upload', {method:'POST', body: fd});
  const data = await res.json(); pendingEmojiUrl = data.url;
}

async function generateTTS(){
  const voice = document.getElementById('ttsVoice').value;
  const text = document.getElementById('ttsText').value.trim();
  if(!text){ alert('Type a script first'); return; }
  const res = await fetch('/api/tts', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({voice, text})});
  const data = await res.json();
  if(data.error){ alert(data.error); return; }
  ttsUrl = data.url;
  const a = document.getElementById('ttsAudio'); a.src = data.url; a.classList.remove('hidden'); a.play();
}

function addTextLayer(){
  const layer = {id: 'txt'+Date.now(), content: 'Your text', x: 0.1, y: 0.75 - textLayers.length*0.08,
                 size: 36, color: '#ffffff', box: true, enabled: true};
  textLayers.push(layer);
  renderTextPanelRow(layer);
  renderTextOnStage(layer);
}
function renderTextPanelRow(layer){
  const wrap = document.getElementById('textLayersWrap');
  const row = document.createElement('div'); row.className='text-row'; row.id='row_'+layer.id;
  row.innerHTML = `
    <div class="top">
      <input type="checkbox" ${layer.enabled?'checked':''} title="Show on video" onchange="updateTextLayer('${layer.id}','enabled',this.checked)">
      <input type="text" value="${layer.content}" oninput="updateTextLayer('${layer.id}','content',this.value)">
      <span class="del" onclick="removeTextLayer('${layer.id}')">✕</span>
    </div>
    <div class="row" style="margin-top:8px">
      <div style="flex:1"><label>Size <span class="val">${layer.size}</span></label>
        <input type="range" min="14" max="90" value="${layer.size}" oninput="updateTextLayer('${layer.id}','size',this.value,true)"></div>
      <div style="width:70px"><label>Color</label><input type="color" value="${layer.color}" oninput="updateTextLayer('${layer.id}','color',this.value)"></div>
    </div>
    <div class="checkrow"><input type="checkbox" ${layer.box?'checked':''} onchange="updateTextLayer('${layer.id}','box',this.checked)"> Background box</div>`;
  wrap.appendChild(row);
}
function updateTextLayer(id, key, val, isNum){
  const layer = textLayers.find(l=>l.id===id); if(!layer) return;
  layer[key] = isNum ? parseInt(val) : val;
  renderTextOnStage(layer);
}
function removeTextLayer(id){
  textLayers = textLayers.filter(l=>l.id!==id);
  const row = document.getElementById('row_'+id); if(row) row.remove();
  const el = document.getElementById('stg_'+id); if(el) el.remove();
}
function renderTextOnStage(layer){
  let el = document.getElementById('stg_'+layer.id);
  if(!el){
    el = document.createElement('div'); el.className='ov-text'; el.id='stg_'+layer.id;
    makeDraggable(el, layer);
    document.getElementById('overlayLayer').appendChild(el);
  }
  el.innerText = layer.content;
  el.style.fontSize = layer.size+'px';
  el.style.color = layer.color;
  el.style.background = layer.box ? 'rgba(0,0,0,.45)' : 'transparent';
  el.style.left = (layer.x*100)+'%';
  el.style.top = (layer.y*100)+'%';
  el.style.display = layer.enabled ? '' : 'none';
}

function renderLogo(){
  if(!logoUrl) return;
  let el = document.getElementById('ovLogo');
  if(!el){
    el = document.createElement('img'); el.className='ov-logo'; el.id='ovLogo';
    makeDraggable(el, logoState);
    document.getElementById('overlayLayer').appendChild(el);
  }
  el.src = logoUrl;
  el.style.width = document.getElementById('logoW').value+'%';
  el.style.opacity = document.getElementById('logoO').value/100;
  el.style.left = (logoState.x*100)+'%';
  el.style.top = (logoState.y*100)+'%';
  el.style.display = document.getElementById('logoEnabled').checked ? '' : 'none';
  document.getElementById('logoWVal').innerText = document.getElementById('logoW').value;
  document.getElementById('logoOVal').innerText = document.getElementById('logoO').value;
}

function makeDraggable(el, state){
  el.onmousedown = (e)=>{
    e.preventDefault();
    const stage = document.getElementById('stage');
    const rect = stage.getBoundingClientRect();
    const elRect = el.getBoundingClientRect();
    const offsetX = e.clientX - elRect.left;
    const offsetY = e.clientY - elRect.top;
    function move(ev){
      let x = (ev.clientX - offsetX - rect.left)/rect.width;
      let y = (ev.clientY - offsetY - rect.top)/rect.height;
      x = Math.max(0, Math.min(0.95, x)); y = Math.max(0, Math.min(0.95, y));
      state.x = x; state.y = y;
      el.style.left = (x*100)+'%'; el.style.top = (y*100)+'%';
    }
    function up(){ document.removeEventListener('mousemove', move); document.removeEventListener('mouseup', up); }
    document.addEventListener('mousemove', move); document.addEventListener('mouseup', up);
  };
}

function setTool(k){
  tool = k;
  document.querySelectorAll('.tool-btn').forEach(b=>b.classList.toggle('active', b.dataset.k===k));
  document.getElementById('emojiUploadWrap').classList.toggle('hidden', k!=='emoji');
}

(function initDrawing(){
  const stage = document.getElementById('stage');
  let start = null, liveEl = null;
  stage.addEventListener('mousedown', (e)=>{
    if(e.target.closest('.ov-region') || e.target.closest('.ov-text') || e.target.closest('.ov-logo')) return;
    const rect = stage.getBoundingClientRect();
    start = {x:(e.clientX-rect.left)/rect.width, y:(e.clientY-rect.top)/rect.height};
    liveEl = document.createElement('div'); liveEl.className='ov-region kind-'+tool;
    liveEl.style.border = '2px dashed #6e5bff';
    document.getElementById('overlayLayer').appendChild(liveEl);
  });
  stage.addEventListener('mousemove', (e)=>{
    if(!start) return;
    const rect = stage.getBoundingClientRect();
    let x = (e.clientX-rect.left)/rect.width, y = (e.clientY-rect.top)/rect.height;
    const x0=Math.min(start.x,x), y0=Math.min(start.y,y), w=Math.abs(x-start.x), h=Math.abs(y-start.y);
    liveEl.style.left=(x0*100)+'%'; liveEl.style.top=(y0*100)+'%';
    liveEl.style.width=(w*100)+'%'; liveEl.style.height=(h*100)+'%';
  });
  stage.addEventListener('mouseup', (e)=>{
    if(!start) return;
    const rect = stage.getBoundingClientRect();
    let x = (e.clientX-rect.left)/rect.width, y = (e.clientY-rect.top)/rect.height;
    const x0=Math.min(start.x,x), y0=Math.min(start.y,y), w=Math.abs(x-start.x), h=Math.abs(y-start.y);
    start = null;
    if(w<0.02 || h<0.02){ liveEl.remove(); return; }
    if(tool === 'emoji' && !pendingEmojiUrl){
      alert('Upload an emoji/sticker image first.'); liveEl.remove(); return;
    }
    const color = document.getElementById('shapeColor').value;
    const region = {kind: tool, x:x0, y:y0, w, h, color, emoji_url: tool==='emoji'?pendingEmojiUrl:null};
    regions.push(region);
    liveEl.classList.add('kind-'+tool);
    liveEl.style.border = '';
    if(tool==='blur' || tool==='black'){
      liveEl.classList.add('kind-'+tool);
    }
    if(tool==='emoji'){ liveEl.style.backgroundImage = `url(${pendingEmojiUrl})`; }
    if(tool==='rect' || tool==='circle' || tool==='arrow'){ liveEl.style.borderColor = color; }
    const del = document.createElement('div'); del.className='del'; del.innerText='✕';
    del.onclick = (ev)=>{ ev.stopPropagation(); liveEl.remove(); regions = regions.filter(r=>r!==region); };
    liveEl.appendChild(del);
  });
})();

// Hook aspect ratio change events and transformation on load
document.getElementById('resolution').addEventListener('change', updateStageAspectRatio);
document.getElementById('player').addEventListener('loadedmetadata', updateStageAspectRatio);

function clearRegions(){
  regions = [];
  document.querySelectorAll('.ov-region').forEach(e=>e.remove());
}

async function saveVideo(){
  if(!currentClipId){ return; }
  const saveBtn = document.getElementById('saveBtn');
  if(saveBtn) saveBtn.disabled = true;

  const stage = document.getElementById('stage');
  const stageRect = stage.getBoundingClientRect();

  const amode = document.querySelector('input[name=amode]:checked').value;
  const settings = {
    speed: parseFloat(document.getElementById('speed').value),
    zoom: parseFloat(document.getElementById('zoom').value),
    pan_x: panX, pan_y: panY,
    contrast: parseFloat(document.getElementById('contrast').value),
    saturation: parseFloat(document.getElementById('saturation').value),
    brightness: parseFloat(document.getElementById('brightness').value),
    sharpen: document.getElementById('sharpen').checked,
    enhance: document.getElementById('enhance').checked,
    color_preset: document.getElementById('colorPreset').value,
    resolution: document.getElementById('resolution').value,
    format: document.getElementById('format').value,
    crf: parseInt(document.getElementById('crf').value),
    preset: document.getElementById('preset').value,
    regions: regions,
    audio_mode: amode,
    audio_file_url: audioFileUrl,
    tts_url: ttsUrl,
    tts_mix: document.getElementById('ttsMix').checked,
    mute: amode === 'mute',
    texts: textLayers.filter(l=>l.enabled).map(l=>({content:l.content, x:l.x, y:l.y, size:l.size, color:l.color, box:l.box})),
    logo: (logoUrl && document.getElementById('logoEnabled').checked) ? {
      url: logoUrl, x: logoState.x, y: logoState.y,
      w: document.getElementById('logoW').value/100,
      opacity: document.getElementById('logoO').value/100
    } : null,
    rotate: document.getElementById('rotate').value,
    hflip: document.getElementById('hflip').checked,
    stage_w: stageRect.width || 360,
    stage_h: stageRect.height || 640
  };
  const t0 = performance.now();
  
  const pWrap = document.getElementById('exportProgressWrap');
  const pFill = document.getElementById('exportProgressFill');
  const pText = document.getElementById('exportProgressText');
  
  if(pWrap) pWrap.classList.remove('hidden');
  if(pFill) pFill.style.width = '0%';
  if(pText) pText.innerText = '0%';

  log('exportLog', '⏳ Exporting final video...');
  
  try {
    const res = await fetch('/api/export', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({clip_id: currentClipId, settings})
    });
    const data = await res.json();
    if(data.error){
      log('exportLog', '❌ '+data.error);
      if(saveBtn) saveBtn.disabled = false;
      if(pWrap) pWrap.classList.add('hidden');
      return;
    }
    
    const exportId = data.export_id;
    let done = false;
    while(!done){
      await new Promise(r=>setTimeout(r, 1000));
      const statusRes = await fetch(`/api/export_status/${exportId}`);
      const sd = await statusRes.json();
      if(sd.error){
        log('exportLog', '❌ '+sd.error);
        if(saveBtn) saveBtn.disabled = false;
        if(pWrap) pWrap.classList.add('hidden');
        return;
      }
      
      const progress = sd.progress || 0;
      if(pFill) pFill.style.width = progress + '%';
      if(pText) pText.innerText = progress + '%';
      
      if(sd.status === 'done'){
        done = true;
        if(pFill) pFill.style.width = '100%';
        if(pText) pText.innerText = '100%';
        const secs = ((performance.now()-t0)/1000).toFixed(1);
        log('exportLog', `✅ Saved in ${secs}s! <a class="dl-link" href="javascript:void(0)" onclick="triggerInlineDownload('${sd.url}', '${sd.url.split('/').pop()}')">Download / open file</a> (also saved on disk at ${sd.path})`);
        if(saveBtn) saveBtn.disabled = false;
      } else if(sd.status === 'failed'){
        done = true;
        log('exportLog', '❌ Export failed: ' + sd.error);
        if(saveBtn) saveBtn.disabled = false;
        if(pWrap) pWrap.classList.add('hidden');
      }
    }
  } catch(e) {
    log('exportLog', '❌ Connection error: ' + e.message);
    if(saveBtn) saveBtn.disabled = false;
    if(pWrap) pWrap.classList.add('hidden');
  }
}

function onColorPresetChange() {
  const preset = document.getElementById('colorPreset').value;
  currentPresetName = preset;
  if(preset && preset !== 'none' && JS_COLOR_PRESETS[preset]){
    const p = JS_COLOR_PRESETS[preset];
    document.getElementById('contrast').value = p.contrast;
    document.getElementById('saturation').value = p.saturation;
    document.getElementById('brightness').value = p.brightness;
  }
  onColor();
}

async function applyToAllAndExport() {
  if (allClips.length === 0) {
    alert("No clips available to export!");
    return;
  }
  
  log('fetchLog', `🚀 Triggering batch export of all ${allClips.length} clips with current settings...`);
  
  allClips.forEach(c => {
    const statusOverlay = document.getElementById(`status_overlay_${c.clip_id}`);
    const statusTxt = document.getElementById(`status_txt_${c.clip_id}`);
    if (statusOverlay) {
      statusOverlay.className = 'clip-status-overlay active';
    }
    if (statusTxt) {
      statusTxt.innerText = 'Waiting in queue...';
    }
    const actions = document.getElementById(`actions_${c.clip_id}`);
    if (actions) {
      actions.innerHTML = `
        <button class="clip-card-btn edit-btn" onclick="event.stopPropagation(); openEditor('${c.clip_id}')">⚙️ Edit</button>
      `;
    }
  });

  exportQueue = [...allClips];
  pumpExportQueue();
}

function getAutoSettingsForClip(clipId, index, audioFiles, stageWidth, stageHeight) {
  let speed = 0.75;
  let zoom = 1.20;
  let contrast = 1.12;
  let saturation = 1.25;
  let brightness = 0.02;
  let sharpen = true;
  let enhance = true;
  let color_preset = 'none';
  let resolution = '1080x1920';
  let format = 'mp4';
  let crf = 18;
  let preset = 'fast';
  let rotate = '0';
  let hflip = true;
  let amode = 'original';
  let defaultAudioUrl = null;
  let ttsMix = false;
  let texts = [];
  let logo = null;
  let stage_w = stageWidth || 360;
  let stage_h = stageHeight || 640;
  let film_grain = true;
  let audio_pitch = true;
  let vignette = true;

  const speedEl = document.getElementById('speed');
  if (speedEl) {
    speed = parseFloat(speedEl.value);
    zoom = parseFloat(document.getElementById('zoom').value);
    contrast = parseFloat(document.getElementById('contrast').value);
    saturation = parseFloat(document.getElementById('saturation').value);
    brightness = parseFloat(document.getElementById('brightness').value);
    sharpen = document.getElementById('sharpen').checked;
    enhance = document.getElementById('enhance').checked;
    color_preset = currentPresetName;
    resolution = document.getElementById('resolution').value;
    format = document.getElementById('format').value;
    crf = parseInt(document.getElementById('crf').value);
    preset = document.getElementById('preset').value;
    rotate = document.getElementById('rotate').value;
    hflip = document.getElementById('hflip').checked;
    const amodeEl = document.querySelector('input[name=amode]:checked');
    if (amodeEl) amode = amodeEl.value;
    defaultAudioUrl = audioFileUrl;
    ttsMix = document.getElementById('ttsMix').checked;
    texts = textLayers.filter(l=>l.enabled).map(l=>({content:l.content, x:l.x, y:l.y, size:l.size, color:l.color, box:l.box}));
    logo = (logoUrl && document.getElementById('logoEnabled').checked) ? {
      url: logoUrl, x: logoState.x, y: logoState.y,
      w: document.getElementById('logoW').value/100,
      opacity: document.getElementById('logoO').value/100
    } : null;
    const stage = document.getElementById('stage');
    if (stage) {
      const stageRect = stage.getBoundingClientRect();
      stage_w = stageRect.width || 360;
      stage_h = stageRect.height || 640;
    }
    film_grain = document.getElementById('automodFilmGrain') ? document.getElementById('automodFilmGrain').checked : true;
    audio_pitch = document.getElementById('automodAudioPitch') ? document.getElementById('automodAudioPitch').checked : true;
    vignette = document.getElementById('automodVignette') ? document.getElementById('automodVignette').checked : true;
  }

  const settings = {
    speed,
    zoom,
    pan_x: panX,
    pan_y: panY,
    contrast,
    saturation,
    brightness,
    sharpen,
    enhance,
    color_preset,
    resolution,
    format,
    crf,
    preset,
    regions: regions,
    audio_mode: amode,
    audio_file_url: defaultAudioUrl,
    tts_url: ttsUrl,
    tts_mix: ttsMix,
    mute: amode === 'mute',
    texts,
    logo,
    rotate,
    hflip,
    stage_w,
    stage_h,
    film_grain,
    audio_pitch,
    vignette,
    clip_index: index
  };

  // Automatically replace audio file round-robin line-by-line if replaced file mode is active or Automod is checked
  const isAutoMode = document.getElementById('autoMode') && document.getElementById('autoMode').checked;
  if ((amode === 'replace' || isAutoMode) && audioFiles && audioFiles.length > 0) {
    const chosenAudio = audioFiles[index % audioFiles.length];
    settings.audio_mode = 'replace';
    settings.audio_file_url = chosenAudio.url;
  }

  return settings;
}

// How many exports run at once. Each export is a real ffmpeg re-encode
// (speed/zoom/color/watermark/noise/vignette/audio-pitch/etc filters), so
// this is CPU-bound — matches the backend's own concurrency cap.
const MAX_CONCURRENT_EXPORTS = 4;
let activeExportWorkers = 0;

function pumpExportQueue() {
  while (activeExportWorkers < MAX_CONCURRENT_EXPORTS && exportQueue.length > 0) {
    const c = exportQueue.shift();
    activeExportWorkers++;
    exportQueueActive = true;
    runOneExport(c).finally(() => {
      activeExportWorkers--;
      if (exportQueue.length === 0 && activeExportWorkers === 0) {
        exportQueueActive = false;
      }
      pumpExportQueue();
    });
  }
}

async function runOneExport(c) {
  const index = c.index - 1; // 0-based

  const statusOverlay = document.getElementById(`status_overlay_${c.clip_id}`);
  const statusTxt = document.getElementById(`status_txt_${c.clip_id}`);
  
  if (statusTxt) statusTxt.innerText = '⚙️ Exporting...';
  if (statusOverlay) statusOverlay.classList.add('active');
  
  try {
    if (!audioLibraryFiles) {
      const res = await fetch('/api/audio_library');
      const data = await res.json();
      audioLibraryFiles = data.files || [];
    }
    
    // Prefer card-specific settings if they exist, otherwise fallback to global/auto settings
    let settings = clipSettingsMap[c.clip_id];
    if (!settings) {
      settings = getAutoSettingsForClip(c.clip_id, index, audioLibraryFiles, 360, 640);
    } else {
      settings.clip_index = index;
    }
    
    const res = await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ clip_id: c.clip_id, settings })
    });
    const data = await res.json();
    if (data.error) {
      throw new Error(data.error);
    }
    
    const exportId = data.export_id;
    let done = false;
    while (!done) {
      await new Promise(r => setTimeout(r, 1200));
      const statusRes = await fetch(`/api/export_status/${exportId}`);
      const sd = await statusRes.json();
      if (sd.error) {
        throw new Error(sd.error);
      }
      
      const progress = sd.progress || 0;
      if (statusTxt) statusTxt.innerText = `⚙️ Exporting ${progress}%`;
      
      if (sd.status === 'done') {
        done = true;
        if (statusTxt) statusTxt.innerText = '✅ Exported';
        if (statusOverlay) {
          statusOverlay.classList.remove('active');
          statusOverlay.classList.add('done');
        }
        const videoEl = document.querySelector(`#card_${c.clip_id} video`);
        if (videoEl) {
          videoEl.src = sd.url;
          videoEl.controls = true;
          videoEl.muted = false;
        }
        const actions = document.getElementById(`actions_${c.clip_id}`);
        if (actions) {
          actions.innerHTML = `
            <button class="clip-card-btn edit-btn" onclick="event.stopPropagation(); openEditor('${c.clip_id}')">⚙️ Edit</button>
            <button class="clip-card-btn dl-btn" onclick="event.stopPropagation(); triggerInlineDownload('${sd.url}', '${sd.url.split('/').pop()}')">📥 Save to PC</button>
          `;
        }
        // Add to our modern Exported Downloads Manager list
        addExportToDownloadsList(c.clip_id, c.label, sd.url, settings);
      } else if (sd.status === 'failed') {
        done = true;
        throw new Error(sd.error);
      }
    }
  } catch (e) {
    console.error(e);
    if (statusTxt) statusTxt.innerText = '❌ Failed';
    if (statusOverlay) {
      statusOverlay.className = 'clip-status-overlay failed';
    }
  }
}


function updateStageAspectRatio() {
  const res = document.getElementById('resolution').value;
  const stage = document.getElementById('stage');
  const player = document.getElementById('player');
  if (res === '1080x1920' || res === '2160x3840') {
    stage.style.aspectRatio = '9/16';
  } else if (res === '1080x1080') {
    stage.style.aspectRatio = '1/1';
  } else if (res === '1920x1080' || res === '3840x2160') {
    stage.style.aspectRatio = '16/9';
  } else if (res === 'original') {
    if (player.videoWidth && player.videoHeight) {
      stage.style.aspectRatio = `${player.videoWidth}/${player.videoHeight}`;
    } else {
      stage.style.aspectRatio = '9/16';
    }
  }
}

function onTransform() {
  updatePreviewTransforms();
  saveCurrentSettingsToMap();
}

function saveCurrentSettingsToMap() {
  if (!currentClipId) return;
  const amode = document.querySelector('input[name=amode]:checked') ? document.querySelector('input[name=amode]:checked').value : 'original';
  const stage = document.getElementById('stage');
  const stageRect = stage ? stage.getBoundingClientRect() : {width: 360, height: 640};
  
  // Clean text layers to be formatted correctly
  const cleanTexts = textLayers.filter(l => l.enabled).map(l => ({
    id: l.id,
    content: l.content,
    x: l.x,
    y: l.y,
    size: l.size,
    color: l.color,
    box: l.box,
    enabled: l.enabled !== false
  }));

  clipSettingsMap[currentClipId] = {
    speed: parseFloat(document.getElementById('speed').value),
    zoom: parseFloat(document.getElementById('zoom').value),
    pan_x: panX,
    pan_y: panY,
    contrast: parseFloat(document.getElementById('contrast').value),
    saturation: parseFloat(document.getElementById('saturation').value),
    brightness: parseFloat(document.getElementById('brightness').value),
    sharpen: document.getElementById('sharpen').checked,
    enhance: document.getElementById('enhance').checked,
    color_preset: document.getElementById('colorPreset').value,
    resolution: document.getElementById('resolution').value,
    format: document.getElementById('format').value,
    crf: parseInt(document.getElementById('crf').value),
    preset: document.getElementById('preset').value,
    regions: regions,
    audio_mode: amode,
    audio_file_url: audioFileUrl,
    tts_url: ttsUrl,
    tts_mix: document.getElementById('ttsMix').checked,
    mute: amode === 'mute',
    texts: cleanTexts,
    logo: (logoUrl && document.getElementById('logoEnabled').checked) ? {
      url: logoUrl, x: logoState.x, y: logoState.y,
      w: document.getElementById('logoW').value/100,
      opacity: document.getElementById('logoO').value/100
    } : null,
    rotate: document.getElementById('rotate').value,
    hflip: document.getElementById('hflip').checked,
    stage_w: stageRect.width || 360,
    stage_h: stageRect.height || 640
  };
  
  // Update card visual representation live!
  updateClipCardBadge(currentClipId);
  
  // Set card video scale transform live based on hflip
  const cardVid = document.querySelector(`#card_${currentClipId} video`);
  if (cardVid) {
    if (document.getElementById('hflip').checked) {
      cardVid.style.transform = 'scaleX(-1)';
    } else {
      cardVid.style.transform = '';
    }
  }
}

function updateClipCardBadge(clipId) {
  const s = clipSettingsMap[clipId];
  if (!s) return;
  const badgeWrap = document.getElementById(`badges_${clipId}`);
  if (badgeWrap) {
    let presetName = s.color_preset || 'none';
    presetName = presetName.charAt(0).toUpperCase() + presetName.slice(1);
    
    let audioName = s.audio_file_url ? s.audio_file_url.split('/').pop() : 'None';
    if (audioName.length > 18) audioName = audioName.slice(0, 15) + '...';
    
    badgeWrap.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:4px; margin-top:6px; font-size:11px; color:#a0a0a0; background:rgba(255,255,255,0.03); padding:6px; border-radius:6px; border:1px solid rgba(255,255,255,0.05);">
        <div style="display:flex; justify-content:space-between;"><span>⚡ Speed:</span> <strong style="color:#ffc107">${s.speed}x</strong></div>
        <div style="display:flex; justify-content:space-between;"><span>🔍 Zoom:</span> <strong style="color:#17a2b8">${s.zoom}x</strong></div>
        <div style="display:flex; justify-content:space-between;"><span>🎨 Color:</span> <strong style="color:#20c997">${presetName}</strong></div>
        <div style="display:flex; justify-content:space-between;"><span>🔤 Watermark:</span> <strong style="color:#e83e8c">"FondPeace.com"</strong></div>
        <div style="display:flex; justify-content:space-between;"><span>🪞 Mirror:</span> <strong style="color:#fd7e14">${s.hflip ? 'Yes' : 'No'}</strong></div>
        <div style="display:flex; justify-content:space-between; align-items:center; gap:4px;">
          <span>🎵 Audio:</span>
          <span style="color:#6f42c1; max-width:110px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-weight:bold;" title="${s.audio_file_url ? s.audio_file_url.split('/').pop() : ''}">${audioName}</span>
        </div>
      </div>
    `;
  }
}

function toggleCardMirror(clipId) {
  const s = clipSettingsMap[clipId];
  if (!s) return;
  s.hflip = !s.hflip;
  updateClipCardBadge(clipId);
  
  // Also apply CSS transform to the card's video element live so the user sees the mirroring immediately!
  const videoEl = document.querySelector(`#card_${clipId} video`);
  if (videoEl) {
    if (s.hflip) {
      videoEl.style.transform = 'scaleX(-1)';
    } else {
      videoEl.style.transform = '';
    }
  }
  
  // If the editor is open with this clip, update the editor's mirror checkbox too
  if (currentClipId === clipId) {
    document.getElementById('hflip').checked = s.hflip;
    onTransform();
  }
}



async function exportSingleClip(clipId) {
  const c = allClips.find(x => x.clip_id === clipId);
  if (!c) return;
  
  if (exportQueue.some(x => x.clip_id === clipId)) {
    alert("This clip is already in the export queue!");
    return;
  }
  
  const statusOverlay = document.getElementById(`status_overlay_${clipId}`);
  const statusTxt = document.getElementById(`status_txt_${clipId}`);
  if (statusTxt) statusTxt.innerText = '⚙️ Exporting...';
  if (statusOverlay) statusOverlay.classList.add('active');
  
  exportQueue.push(c);
  pumpExportQueue();
}

// ──────────────────────── Exported Downloads & Batch Manager ────────────────────────
let exportedVideos = []; // array of {clipId, label, url, settings, filename}
let allSelectedExports = true;

function addExportToDownloadsList(clipId, label, url, settings) {
  document.getElementById('downloadsCard').classList.remove('hidden');
  const emptyRow = document.getElementById('emptyExportRow');
  if (emptyRow) {
    emptyRow.remove();
  }
  
  // Prevent duplicate items in list
  if (exportedVideos.some(v => v.clipId === clipId)) {
    const idx = exportedVideos.findIndex(v => v.clipId === clipId);
    exportedVideos[idx] = { clipId, label, url, settings, filename: url.split('/').pop() };
    renderExportedVideosTable();
    return;
  }
  
  exportedVideos.push({
    clipId,
    label,
    url,
    settings,
    filename: url.split('/').pop()
  });
  
  renderExportedVideosTable();
}

function renderExportedVideosTable() {
  const tbody = document.getElementById('exportedVideosList');
  if (exportedVideos.length === 0) {
    tbody.innerHTML = `
      <tr id="emptyExportRow">
        <td colspan="4" style="padding: 20px; text-align: center; color: var(--dim);">No videos successfully exported yet. Click "Export Video" on a card or run a batch export!</td>
      </tr>
    `;
    return;
  }
  
  tbody.innerHTML = '';
  exportedVideos.forEach(v => {
    let presetName = v.settings.color_preset || 'none';
    presetName = presetName.charAt(0).toUpperCase() + presetName.slice(1);
    
    let audioName = v.settings.audio_file_url ? v.settings.audio_file_url.split('/').pop() : 'Original';
    if (audioName.length > 20) audioName = audioName.slice(0, 17) + '...';
    
    const row = document.createElement('tr');
    row.style.borderBottom = '1px solid var(--border)';
    row.style.background = 'rgba(255,255,255,0.01)';
    row.innerHTML = `
      <td style="padding: 10px 8px; vertical-align: middle;">
        <input type="checkbox" class="export-download-chk" checked data-url="${v.url}" data-fname="${v.filename}" style="width:16px; height:16px; cursor:pointer;">
      </td>
      <td style="padding: 10px 8px; font-weight: 600; color: #fff; vertical-align: middle;">
        <div style="display:flex; align-items:center; gap:8px;">
          <span>🎬</span>
          <div>
            <div style="font-size:13px; color:#fff;">${v.label}</div>
            <div style="font-size:11px; color:var(--dim); font-weight:normal;">File: ${v.filename}</div>
          </div>
        </div>
      </td>
      <td style="padding: 10px 8px; vertical-align: middle;">
        <div style="display:flex; flex-wrap:wrap; gap:6px; font-size:11px;">
          <span style="background:rgba(255,193,7,0.15); color:#ffc107; padding:2px 6px; border-radius:4px; font-weight:bold;">⚡ ${v.settings.speed}x</span>
          <span style="background:rgba(23,162,184,0.15); color:#17a2b8; padding:2px 6px; border-radius:4px; font-weight:bold;">🔍 ${v.settings.zoom}x</span>
          <span style="background:rgba(32,201,151,0.15); color:#20c997; padding:2px 6px; border-radius:4px; font-weight:bold;">🎨 ${presetName}</span>
          <span style="background:rgba(253,126,20,0.15); color:#fd7e14; padding:2px 6px; border-radius:4px; font-weight:bold;">🪞 Mirror: ${v.settings.hflip ? 'Yes' : 'No'}</span>
          <span style="background:rgba(111,66,193,0.15); color:#6f42c1; padding:2px 6px; border-radius:4px; font-weight:bold; max-width:150px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${v.settings.audio_file_url ? v.settings.audio_file_url.split('/').pop() : ''}">🎵 ${audioName}</span>
        </div>
      </td>
      <td style="padding: 10px 8px; text-align: right; vertical-align: middle;">
        <div style="display:flex; justify-content:flex-end; gap:6px;">
          <button class="clip-card-btn" style="padding: 4px 8px; font-size:11px; background:var(--grad); color:#000; font-weight:bold; cursor:pointer;" onclick="triggerInlineDownload('${v.url}', '${v.filename}')">📥 Download</button>
          <button class="clip-card-btn" style="padding: 4px 8px; font-size:11px; background:#434348; color:#fff; cursor:pointer;" onclick="playExportedVideo('${v.url}')">▶ Play</button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });
}

function triggerInlineDownload(url, filename) {
  const a = document.createElement('a');
  a.href = url;
  a.setAttribute('download', filename || '');
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function playExportedVideo(url) {
  const modal = document.createElement('div');
  modal.style.position = 'fixed';
  modal.style.top = '0';
  modal.style.left = '0';
  modal.style.width = '100vw';
  modal.style.height = '100vh';
  modal.style.background = 'rgba(0,0,0,0.85)';
  modal.style.zIndex = '99999';
  modal.style.display = 'flex';
  modal.style.flexDirection = 'column';
  modal.style.alignItems = 'center';
  modal.style.justifyContent = 'center';
  modal.style.gap = '15px';
  modal.id = 'temp_video_modal';
  
  modal.innerHTML = `
    <div style="position:relative; width:90%; max-width:400px; aspect-ratio:9/16; background:#000; border-radius:12px; overflow:hidden; border:2px solid var(--border); box-shadow:0 0 30px rgba(0,0,0,0.5);">
      <video src="${url}" controls autoplay loop style="width:100%; height:100%; object-fit:contain;"></video>
      <button onclick="document.getElementById('temp_video_modal').remove()" style="position:absolute; top:12px; right:12px; width:32px; height:32px; border-radius:50%; background:rgba(0,0,0,0.7); color:#fff; border:1px solid rgba(255,255,255,0.2); cursor:pointer; font-size:16px; font-weight:bold; display:flex; align-items:center; justify-content:center; transition:0.2s;">✕</button>
    </div>
    <div style="display:flex; gap:10px;">
      <button class="btn-grad" onclick="triggerInlineDownload('${url}', '${url.split('/').pop()}'); document.getElementById('temp_video_modal').remove();" style="padding:8px 16px; font-size:13px; color:#000; font-weight:bold; border-radius:6px; cursor:pointer;">📥 Download Video</button>
      <button onclick="document.getElementById('temp_video_modal').remove()" style="padding:8px 16px; background:#333; color:#fff; border:1px solid #444; border-radius:6px; cursor:pointer; font-size:13px;">Close Preview</button>
    </div>
  `;
  document.body.appendChild(modal);
}

function toggleSelectAllExports() {
  allSelectedExports = !allSelectedExports;
  document.querySelectorAll('.export-download-chk').forEach(chk => {
    chk.checked = allSelectedExports;
  });
}

async function downloadSelectedVideos() {
  const selectedCheckboxes = document.querySelectorAll('.export-download-chk:checked');
  if (selectedCheckboxes.length === 0) {
    alert("Please select at least one exported video to download.");
    return;
  }
  for (let i = 0; i < selectedCheckboxes.length; i++) {
    const url = selectedCheckboxes[i].dataset.url;
    const fname = selectedCheckboxes[i].dataset.fname;
    
    triggerInlineDownload(url, fname);
    
    // Wait slightly between downloads to avoid browser block
    await new Promise(r => setTimeout(r, 1000));
  }
}

// ──────────────────────── Downloader (Top-right feature) ────────────────────────
// A fully separate video downloader, in the same page/port as the Shorts
// Studio. Paste any link, see full details (thumbnails, title, uploader,
// duration, every available quality/format with its size), copy the link,
// and download with a live percent / MB / speed / ETA readout — no need to
// go anywhere else.

function showStudioView(){
  document.getElementById('studioView').classList.remove('hidden');
  document.getElementById('downloaderView').classList.add('hidden');
  document.getElementById('studioTabBtn').classList.add('active');
  document.getElementById('downloaderTabBtn').classList.remove('active');
}
function showDownloaderView(){
  document.getElementById('studioView').classList.add('hidden');
  document.getElementById('downloaderView').classList.remove('hidden');
  document.getElementById('studioTabBtn').classList.remove('active');
  document.getElementById('downloaderTabBtn').classList.add('active');
}

function setDlBtnLoading(isLoading, label){
  const btn = document.getElementById('dlFetchBtn');
  if(!btn) return;
  if(isLoading){
    if(!btn.dataset.origHtml) btn.dataset.origHtml = btn.innerHTML;
    btn.disabled = true;
    btn.style.opacity = '0.85';
    btn.style.cursor = 'wait';
    btn.innerHTML = `<span class="btn-spinner"></span>&nbsp;${label || 'Working…'}`;
  } else {
    btn.disabled = false;
    btn.style.opacity = '';
    btn.style.cursor = '';
    if(btn.dataset.origHtml) btn.innerHTML = btn.dataset.origHtml;
  }
}

function fmtDuration(sec){
  if(!sec && sec !== 0) return '–';
  sec = Math.round(sec);
  const h = Math.floor(sec/3600), m = Math.floor((sec%3600)/60), s = sec%60;
  return h>0 ? `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}` : `${m}:${String(s).padStart(2,'0')}`;
}

function setDlInlineStatus(msg, isError){
  const el = document.getElementById('dlLog');
  el.classList.remove('hidden');
  el.textContent = msg;
  el.style.color = isError ? '#ff6b7a' : '';
  el.style.borderColor = isError ? 'rgba(220,53,69,0.4)' : '';
}

async function fetchDownloadInfo(){
  const url = document.getElementById('dlUrl').value.trim();
  if(!url){ alert('Paste a video URL first'); return; }
  document.getElementById('dlInfoCard').classList.add('hidden');
  document.getElementById('dlProgressCard').classList.add('hidden');
  setDlBtnLoading(true, 'Fetching details…');
  setDlInlineStatus('⏳ Resolving video & fetching every detail…', false);
  let res, data;
  try{
    res = await fetch('/api/downloader/info', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({url})});
    data = await res.json();
  } catch(e){
    setDlInlineStatus('❌ Network error', true); setDlBtnLoading(false); return;
  }
  setDlBtnLoading(false);
  if(data.error){ setDlInlineStatus('❌ '+data.error, true); return; }
  setDlInlineStatus(`✅ Found "${data.title}" — ${(data.formats||[]).length} format(s) available.`, false);
  renderDownloadInfo(data, url);
}

function copyDlValue(text, btnEl){
  if(!text) return;
  navigator.clipboard && navigator.clipboard.writeText(text).catch(()=>{});
  if(btnEl){
    const orig = btnEl.textContent;
    btnEl.textContent = '✅';
    setTimeout(()=>{ btnEl.textContent = orig; }, 1200);
  }
}

function addDetailItem(grid, label, value){
  if(value === null || value === undefined || value === '') return;
  const item = document.createElement('div');
  item.className = 'dl-detail-item';
  item.innerHTML = `
    <span class="dl-detail-label">${label}</span>
    <span class="dl-detail-val">${value}</span>
    <button class="dl-copy-icon-btn" title="Copy" onclick="copyDlValue(${JSON.stringify(String(value)).replace(/"/g,'&quot;')}, this)">📋</button>
  `;
  grid.appendChild(item);
}

function renderDownloadInfo(data, originalUrl){
  document.getElementById('dlInfoCard').classList.remove('hidden');
  document.getElementById('dlTitle').textContent = data.title || 'Untitled video';
  document.getElementById('dlThumbMain').src = data.thumbnail || '';
  document.getElementById('dlPageUrl').value = data.webpage_url || originalUrl;

  // thumbnail preview strip in multiple sizes/formats
  const strip = document.getElementById('dlThumbStrip');
  strip.innerHTML = '';
  (data.thumbnails||[]).forEach(t=>{
    const img = document.createElement('img');
    img.src = t.url;
    img.title = t.width && t.height ? `${t.width}x${t.height}` : 'thumbnail';
    img.onclick = () => { document.getElementById('dlThumbMain').src = t.url; };
    strip.appendChild(img);
  });

  // quick-glance badges
  const badges = document.getElementById('dlMetaBadges');
  badges.innerHTML = '';
  const badgeVals = [];
  if(data.uploader) badgeVals.push(`👤 ${data.uploader}`);
  if(data.duration_str) badgeVals.push(`⏱ ${data.duration_str}`);
  if(data.view_count_str) badgeVals.push(`👁 ${data.view_count_str} views`);
  if(data.extractor) badgeVals.push(`🌐 ${data.extractor}`);
  if(data.is_live) badgeVals.push(`🔴 LIVE`);
  badgeVals.forEach(v=>{ const s=document.createElement('span'); s.textContent=v; badges.appendChild(s); });

  // full details grid — everything meaningful yt-dlp gives us, not just a few picks
  const grid = document.getElementById('dlDetailsGrid');
  grid.innerHTML = '';
  addDetailItem(grid, 'Uploader / Channel', data.uploader);
  addDetailItem(grid, 'Subscribers', data.channel_follower_count_str);
  addDetailItem(grid, 'Upload Date', data.upload_date_str);
  addDetailItem(grid, 'Duration', data.duration_str);
  addDetailItem(grid, 'Views', data.view_count_str);
  addDetailItem(grid, 'Likes', data.like_count_str);
  addDetailItem(grid, 'Comments', data.comment_count_str);
  addDetailItem(grid, 'Best Resolution', data.resolution);
  addDetailItem(grid, 'Largest File Size', data.best_filesize_str);
  addDetailItem(grid, 'Total Formats', data.format_count);
  addDetailItem(grid, 'Language', data.language);
  addDetailItem(grid, 'Age Limit', data.age_limit ? data.age_limit+'+' : (data.age_limit === 0 ? 'None' : null));
  addDetailItem(grid, 'Availability', data.availability);
  addDetailItem(grid, 'License', data.license);
  addDetailItem(grid, 'Subtitles', data.subtitle_langs && data.subtitle_langs.length ? `${data.subtitle_langs.length} language(s)` : null);
  addDetailItem(grid, 'Auto Captions', data.auto_caption_langs_count ? `${data.auto_caption_langs_count} language(s)` : null);
  addDetailItem(grid, 'Chapters', data.chapters_count || null);
  addDetailItem(grid, 'Source Site', data.extractor);

  // description
  const descWrap = document.getElementById('dlDescWrap');
  const descText = document.getElementById('dlDescText');
  if(data.description){
    descWrap.style.display = '';
    descText.textContent = data.description;
    descText.classList.add('collapsed');
    document.getElementById('dlDescToggleBtn').textContent = '⬇️';
    document.getElementById('dlDescToggleBtn').onclick = () => {
      descText.classList.toggle('collapsed');
      document.getElementById('dlDescToggleBtn').textContent = descText.classList.contains('collapsed') ? '⬇️' : '⬆️';
    };
    document.getElementById('dlDescCopyBtn').onclick = (e) => copyDlValue(data.description, e.currentTarget);
  } else {
    descWrap.style.display = 'none';
  }

  // categories & tags chips
  const catWrap = document.getElementById('dlCategoriesWrap');
  const catChips = document.getElementById('dlCategoriesChips');
  catChips.innerHTML = '';
  if(data.categories && data.categories.length){
    catWrap.style.display = '';
    data.categories.forEach(c=>{ const s=document.createElement('span'); s.textContent=c; catChips.appendChild(s); });
  } else { catWrap.style.display = 'none'; }

  const tagWrap = document.getElementById('dlTagsWrap');
  const tagChips = document.getElementById('dlTagsChips');
  tagChips.innerHTML = '';
  if(data.tags && data.tags.length){
    tagWrap.style.display = '';
    data.tags.forEach(t=>{ const s=document.createElement('span'); s.textContent=t; tagChips.appendChild(s); });
    if(data.tags_more > 0){ const s=document.createElement('span'); s.textContent = `+${data.tags_more} more`; tagChips.appendChild(s); }
  } else { tagWrap.style.display = 'none'; }

  // formats table, each row with its own copy button too
  const tbody = document.getElementById('dlFormatsBody');
  tbody.innerHTML = '';
  (data.formats||[]).forEach(f=>{
    const codec = [f.vcodec, f.acodec].filter(Boolean).join(' / ') || '–';
    const summary = `${f.label||''} ${f.ext?.toUpperCase()||''} — ${f.filesize_str}`.trim();
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${f.kind}</td>
      <td><strong>${f.label||'—'}</strong></td>
      <td style="text-transform:uppercase;">${f.ext||'–'}</td>
      <td style="font-size:11.5px; color:var(--dim);">${codec}</td>
      <td>${f.filesize_str}</td>
      <td style="text-align:right; white-space:nowrap;">
        <button class="dl-copy-icon-btn" title="Copy quality info" onclick="copyDlValue(${JSON.stringify(summary).replace(/"/g,'&quot;')}, this)">📋</button>
        <button class="dl-fmt-btn" onclick="startDownload('${(originalUrl+"").replace(/'/g,"\\'")}','${f.format_id}')">⬇ Download</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function copyDlText(elId){
  const el = document.getElementById(elId);
  el.select();
  el.setSelectionRange(0, 99999);
  navigator.clipboard && navigator.clipboard.writeText(el.value).catch(()=>{ document.execCommand('copy'); });
  setDlInlineStatus('📋 Link copied to clipboard.', false);
}

// Moves the little step-tracker (Connecting → Downloading → Merging → Ready)
// forward based on the job's current stage — a clean, modern replacement
// for a raw scrolling console/cmd-style log that most users find confusing.
const DL_STAGE_ORDER = ['connect', 'download', 'merge', 'done'];
function setDlStepperStage(stage){
  const idx = DL_STAGE_ORDER.indexOf(stage);
  document.querySelectorAll('#dlStepper .dl-step').forEach(el=>{
    const stepIdx = DL_STAGE_ORDER.indexOf(el.dataset.step);
    el.classList.remove('active','complete');
    if(stepIdx < idx) el.classList.add('complete');
    else if(stepIdx === idx) el.classList.add('active');
  });
  document.querySelectorAll('#dlStepper .dl-step-line').forEach(el=>{
    const lineIdx = parseInt(el.dataset.line, 10); // line 1 sits between step0/step1, etc.
    el.classList.toggle('complete', lineIdx <= idx);
  });
}

async function startDownload(url, formatId){
  document.getElementById('dlProgressCard').classList.remove('hidden');
  document.getElementById('dlProgressCard').scrollIntoView({behavior:'smooth', block:'nearest'});
  document.getElementById('dlErrorBanner').classList.add('hidden');
  document.getElementById('dlPercentVal').textContent = '0%';
  document.getElementById('dlSizeVal').textContent = '0 MB / 0 MB';
  document.getElementById('dlSpeedVal').textContent = '– MB/s';
  document.getElementById('dlEtaVal').textContent = '–';
  document.getElementById('dlProgressFill').style.width = '0%';
  document.getElementById('dlProgressText').textContent = '0%';
  document.getElementById('dlStatusLine').textContent = 'Connecting…';
  setDlStepperStage('connect');

  let res, data;
  try{
    res = await fetch('/api/downloader/start', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({url, format_id: formatId})});
    data = await res.json();
  } catch(e){
    showDlError('Network error starting download'); return;
  }
  if(data.error){ showDlError(data.error); return; }
  const dlId = data.dl_id;

  let done = false;
  while(!done){
    await new Promise(r=>setTimeout(r, 600));
    let pd;
    try{
      const st = await fetch(`/api/downloader/progress/${dlId}`);
      pd = await st.json();
    } catch(e){ continue; }
    if(pd.error){ showDlError(pd.error); return; }

    setDlStepperStage(pd.stage || 'connect');

    const pct = (pd.percent != null) ? pd.percent : 0;
    document.getElementById('dlPercentVal').textContent = pct + '%';
    document.getElementById('dlProgressFill').style.width = pct + '%';
    document.getElementById('dlProgressText').textContent = pct + '%';
    document.getElementById('dlSizeVal').textContent = `${pd.downloaded_str||'0 B'} / ${pd.total_str||'~unknown'}`;
    document.getElementById('dlSpeedVal').textContent = pd.speed_str || '– MB/s';
    document.getElementById('dlEtaVal').textContent = (pd.eta != null) ? fmtDuration(pd.eta) + ' left' : '–';

    if(pd.status === 'downloading'){
      document.getElementById('dlStatusLine').textContent = 'Downloading your video…';
    } else if(pd.status === 'processing'){
      document.getElementById('dlStatusLine').textContent = 'Merging audio & video…';
    }

    if(pd.status === 'done'){
      done = true;
      setDlStepperStage('done');
      document.getElementById('dlPercentVal').textContent = '100%';
      document.getElementById('dlProgressFill').style.width = '100%';
      document.getElementById('dlProgressText').textContent = '100%';
      document.getElementById('dlStatusLine').textContent = '🎉 Done! Saving to your device…';
      triggerInlineDownload(`/api/downloader/file/${dlId}`, pd.filename);
    } else if(pd.status === 'error'){
      done = true;
      showDlError(pd.error || 'Download failed');
    }
  }
}

function showDlError(msg){
  const banner = document.getElementById('dlErrorBanner');
  banner.textContent = '❌ ' + msg;
  banner.classList.remove('hidden');
  document.getElementById('dlStatusLine').textContent = '';
}

// Enter key in the downloader URL field works exactly like clicking "Fetch Video Details"
document.addEventListener('DOMContentLoaded', () => {
  const dlUrlInput = document.getElementById('dlUrl');
  if(dlUrlInput){
    dlUrlInput.addEventListener('keydown', (e) => {
      if(e.key === 'Enter'){
        e.preventDefault();
        fetchDownloadInfo();
      }
    });
  }
});
</script>
</body>
</html>
"""


def upgrade_yt_dlp_silently():
    import sys
    import subprocess
    try:
        print("[Auto-Update] Checking and upgrading yt-dlp to the latest version to prevent bot-detection issues...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[Auto-Update] yt-dlp has been updated to the latest secure version.")
    except Exception as e:
        print(f"[Auto-Update Warning] Could not auto-upgrade yt-dlp: {e}")


def main():
    # Upgrade yt-dlp silently on startup in a separate thread so it doesn't block Flask booting
    threading.Thread(target=upgrade_yt_dlp_silently, daemon=True).start()
    # threading.Thread(target=preload_ai_models, daemon=True).start()
    port = 5783
    url = f"http://127.0.0.1:{port}/"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"AutoShortAi running at {url}")
    print(f"Parallel clip-cutting workers: {MAX_CUT_WORKERS}")
    print(f"Audio library folder: {AUDIO_LIB_DIR} (drop .mp3 files here)")
    if not EDGE_TTS_OK:
        print("NOTE: edge-tts not installed — Microsoft AI voiceover will be disabled. Run: pip install edge-tts")
    if not GTTS_OK:
        print("NOTE: gTTS not installed — Google AI voiceover will be disabled. Run: pip install gTTS")
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()