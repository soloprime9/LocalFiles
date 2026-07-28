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
    pip install flask yt-dlp imageio-ffmpeg edge-tts
    python shortvideo.py
"""

import os
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

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

BASE = Path(__file__).resolve().parent
PROXY_DIR = BASE / "proxy_clips"
UPLOAD_DIR = BASE / "uploads"
OUTPUT_DIR = BASE / "shorts_final"
for d in (PROXY_DIR, UPLOAD_DIR, OUTPUT_DIR):
    d.mkdir(exist_ok=True)

TTS_VOICES = {
    "hi_male": "hi-IN-MadhurNeural",
    "hi_female": "hi-IN-SwaraNeural",
    "en_in_male": "en-IN-PrabhatNeural",
    "en_in_female": "en-IN-NeerjaNeural",
    "en_us_male": "en-US-GuyNeural",
    "en_us_female": "en-US-AriaNeural",
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
                           stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
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


def resolve_stream(url, max_height):
    ydl_opts = {
        'format': f'bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={max_height}][ext=mp4]/best',
        'quiet': True, 'no_warnings': True, 'noplaylist': True,
        'socket_timeout': 15, 'retries': 2, 'extractor_retries': 1,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        video_url = audio_url = None
        if info.get('requested_formats'):
            for f in info['requested_formats']:
                if f.get('vcodec') != 'none' and f.get('acodec') == 'none':
                    video_url = f['url']
                elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    audio_url = f['url']
        if not video_url:
            video_url = info.get('url')
        if not audio_url:
            audio_url = video_url
        title = info.get('title', 'video')
        safe = re.sub(r'[^\w\-]+', '_', title)[:40]
        return video_url, audio_url, safe, info.get('duration')


def cut_proxy(video_url, audio_url, start, end, height, out_path):
    """Cut a fast scratch/preview proxy. ultrafast preset because this file
    is only used for in-browser editing + as the source for the final
    export — it doesn't need to be pretty, it needs to exist quickly."""
    duration = end - start
    if video_url == audio_url:
        cmd = [FFMPEG, "-y",
               "-ss", str(start), "-i", video_url,
               "-t", str(duration),
               "-vf", "crop=ih*9/16:ih,scale=720:1280",
               "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
               "-c:a", "aac", "-b:a", "128k",
               "-threads", "0", "-movflags", "+faststart", str(out_path)]
    else:
        cmd = [FFMPEG, "-y",
               "-ss", str(start), "-i", video_url,
               "-ss", str(start), "-i", audio_url,
               "-t", str(duration),
               "-filter_complex", "[0:v]crop=ih*9/16:ih,scale=720:1280[v]",
               "-map", "[v]", "-map", "1:a",
               "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
               "-c:a", "aac", "-b:a", "128k",
               "-threads", "0", "-movflags", "+faststart", str(out_path)]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path.exists() and out_path.stat().st_size > 1000


def compute_auto_ranges(total_dur, clip_len):
    ranges = []
    t = 0
    while t + 5 < total_dur:
        e = min(t + clip_len, total_dur)
        ranges.append((int(t), int(e)))
        t += clip_len
    return ranges


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

@app.route("/api/fetch_and_cut", methods=["POST"])
def api_fetch_and_cut():
    data = request.json
    url = data.get("url", "").strip()
    height = str(data.get("quality", "1080"))
    mode = data.get("mode", "auto")
    clip_len = int(data.get("clip_len", 30))

    if not url:
        return jsonify({"error": "No URL given"}), 400

    try:
        video_url, audio_url, title, total_dur = resolve_stream(url, height)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Could not resolve video: {e}"}), 400

    if mode == "auto":
        if not total_dur:
            return jsonify({"error": "Could not detect duration for auto mode"}), 400
        ranges = compute_auto_ranges(total_dur, clip_len)
    else:
        ranges = data.get("ranges", [])
        ranges = [(int(r[0]), int(r[1])) for r in ranges]

    if not ranges:
        return jsonify({"error": "No clip ranges to cut"}), 400

    # ---- cut all ranges in parallel instead of one-by-one ----
    jobs = []
    for i, (s, e) in enumerate(ranges, start=1):
        clip_id = uuid.uuid4().hex[:12]
        out_path = PROXY_DIR / f"{clip_id}.mp4"
        jobs.append((i, s, e, clip_id, out_path))

    results_by_index = {}

    def _do_job(job):
        i, s, e, clip_id, out_path = job
        ok = cut_proxy(video_url, audio_url, s, e, height, out_path)
        return job, ok

    with ThreadPoolExecutor(max_workers=MAX_CUT_WORKERS) as pool:
        futures = [pool.submit(_do_job, job) for job in jobs]
        for fut in as_completed(futures):
            (i, s, e, clip_id, out_path), ok = fut.result()
            if ok:
                w, h, dur = probe(out_path)
                CLIPS[clip_id] = {"path": str(out_path), "w": w, "h": h, "duration": dur,
                                   "title": f"{title}_{i:02d}", "start": s, "end": e}
                results_by_index[i] = {"clip_id": clip_id, "w": w, "h": h, "duration": dur,
                                        "label": f"Short {i} ({s}s–{e}s)"}

    # preserve original chronological order in the response
    results = [results_by_index[i] for i in sorted(results_by_index)]
    return jsonify({"title": title, "clips": results})


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
    if not EDGE_TTS_OK:
        return jsonify({"error": "edge-tts not installed. Run: pip install edge-tts"}), 400
    data = request.json
    voice_key = data.get("voice", "hi_male")
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text given"}), 400
    voice = TTS_VOICES.get(voice_key, TTS_VOICES["hi_male"])
    fname = f"tts_{uuid.uuid4().hex[:10]}.mp3"
    out_path = UPLOAD_DIR / fname

    async def _run():
        comm = edge_tts.Communicate(text, voice)
        await comm.save(str(out_path))

    try:
        asyncio.run(_run())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"url": f"/uploaded/{fname}"})


# ───────────────────────────── API: export ─────────────────────────────

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

    try:
        out_path = build_and_run_export(src, w, h, settings, info["title"])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"path": str(out_path), "url": f"/api/download/{out_path.name}"})


@app.route("/api/download/<fname>")
def api_download(fname):
    p = OUTPUT_DIR / fname
    if not p.exists():
        return "Not found", 404
    return send_file(p, as_attachment=True)


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
    if s.get("regions"):
        return False
    if s.get("text") and s["text"].get("content"):
        return False
    if s.get("logo") and s["logo"].get("url"):
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
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
    if not out_path.exists() or out_path.stat().st_size < 1000:
        raise RuntimeError("FFmpeg copy failed:\n" + result.stdout[-1500:])
    return out_path


def build_and_run_export(src, w, h, s, title):
    fmt = s.get("format", "mp4")

    # ---- fast path: nothing was actually edited, just remux/copy ----
    if _is_trivial_export(s, src.suffix):
        return fast_copy_export(src, fmt, title)

    speed = float(s.get("speed", 1.0))
    zoom = float(s.get("zoom", 1.0))
    mute = bool(s.get("mute", False))
    contrast = float(s.get("contrast", 1.0))
    saturation = float(s.get("saturation", 1.0))
    brightness = float(s.get("brightness", 0.0))
    sharpen = bool(s.get("sharpen", False))
    resolution = s.get("resolution", "1080x1920")
    crf = int(s.get("crf", 18))
    preset = s.get("preset", "medium")
    regions = s.get("regions", [])
    text = s.get("text", None)
    logo = s.get("logo", None)
    audio_mode = s.get("audio_mode", "original")  # original | mute | replace | tts
    audio_file_url = s.get("audio_file_url")
    tts_url = s.get("tts_url")
    tts_mix = bool(s.get("tts_mix", False))

    out_w, out_h = (1080, 1920)
    if resolution == "1080x1080":
        out_w, out_h = 1080, 1080
    elif resolution == "1920x1080":
        out_w, out_h = 1920, 1080
    elif resolution == "original":
        out_w, out_h = w, h

    ext_codec = {"mp4": ("mp4", "libx264", "aac"), "mov": ("mov", "libx264", "aac"),
                 "webm": ("webm", "libvpx-vp9", "libopus")}[fmt]
    ext, vcodec, acodec = ext_codec

    eff_w = w / zoom if zoom > 1.0 else w
    eff_h = h / zoom if zoom > 1.0 else h
    crop_x_off = (w - eff_w) / 2
    crop_y_off = (h - eff_h) / 2
    scale_x = out_w / eff_w
    scale_y = out_h / eff_h

    vf = []
    if zoom > 1.0:
        vf.append(f"crop={int(eff_w)}:{int(eff_h)}")
    vf.append(f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase")
    vf.append(f"crop={out_w}:{out_h}")

    eq_parts = []
    if abs(contrast - 1.0) > 1e-3:
        eq_parts.append(f"contrast={contrast:.3f}")
    if abs(saturation - 1.0) > 1e-3:
        eq_parts.append(f"saturation={saturation:.3f}")
    if abs(brightness) > 1e-3:
        eq_parts.append(f"brightness={brightness:.3f}")
    if eq_parts:
        vf.append("eq=" + ":".join(eq_parts))
    if sharpen:
        vf.append("unsharp=5:5:0.6:5:5:0.0")
    if abs(speed - 1.0) > 1e-3:
        vf.append(f"setpts=PTS/{speed:.4f}")

    cmd = [FFMPEG, "-y", "-i", str(src)]
    extra_audio_idx = None
    input_count = 1

    if audio_mode == "tts" and tts_url:
        local_tts = UPLOAD_DIR / Path(tts_url).name
        cmd += ["-i", str(local_tts)]
        extra_audio_idx = input_count
        input_count += 1
    elif audio_mode == "replace" and audio_file_url:
        local_audio = UPLOAD_DIR / Path(audio_file_url).name
        cmd += ["-i", str(local_audio)]
        extra_audio_idx = input_count
        input_count += 1

    logo_idx = None
    if logo and logo.get("url"):
        local_logo = UPLOAD_DIR / Path(logo["url"]).name
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
                fc.append(f"[{iidx}:v]scale={bw}:{bh}[{nxt}e]")
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
        fc.append(f"[{logo_idx}:v]scale={int(lw)}:-1,format=rgba,colorchannelmixer=aa={lop:.2f}[logo]")
        fc.append(f"[{cur}][logo]overlay={int(lx)}:{int(ly)}[vlogo]")
        cur = "vlogo"

    if text and text.get("content"):
        esc = text["content"].replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        tx = int(float(text.get("x", 0.1)) * out_w)
        ty = int(float(text.get("y", 0.8)) * out_h)
        size = int(text.get("size", 56))
        color = (text.get("color") or "#ffffff").lstrip("#")
        box = ":box=1:boxcolor=black@0.45:boxborderw=14" if text.get("box", True) else ""
        fc.append(f"[{cur}]drawtext=text='{esc}':fontsize={size}:fontcolor=0x{color}:x={tx}:y={ty}{box}[vtext]")
        cur = "vtext"

    filter_complex = ";".join(fc)
    cmd += ["-filter_complex", filter_complex, "-map", f"[{cur}]"]

    if audio_mode == "mute":
        cmd += ["-an"]
    elif extra_audio_idx is not None:
        if audio_mode == "tts" and tts_mix:
            cmd += ["-filter_complex:a",
                    f"[0:a]volume=0.25[a0];[{extra_audio_idx}:a]volume=1.0[a1];[a0][a1]amix=inputs=2:duration=longest[aout]"]
            cmd += ["-map", "[aout]"]
        else:
            cmd += ["-map", f"{extra_audio_idx}:a"]
    else:
        cmd += ["-map", "0:a?"]

    if abs(speed - 1.0) > 1e-3 and audio_mode != "mute":
        cmd += ["-af", atempo_chain(speed)]

    out_name = f"{title}_final_{uuid.uuid4().hex[:6]}.{ext}"
    out_path = OUTPUT_DIR / out_name
    cmd += ["-c:v", vcodec, "-preset", preset, "-crf", str(crf), "-threads", "0"]
    if audio_mode != "mute":
        cmd += ["-c:a", acodec, "-b:a", "160k"]
    cmd += ["-movflags", "+faststart", str(out_path)]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
    if not out_path.exists() or out_path.stat().st_size < 1000:
        raise RuntimeError("FFmpeg failed:\n" + result.stdout[-1500:])
    return out_path


# ───────────────────────────── Frontend ─────────────────────────────

@app.route("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Shorts Studio</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
:root{
  --bg:#0b0d12; --panel:#13151c; --panel2:#191c25; --border:#262a36;
  --text:#eef0f6; --dim:#8a90a4; --accent:#6e5bff; --accent2:#22d3c4;
  --grad: linear-gradient(135deg,#6e5bff,#22d3c4);
  --danger:#ff5a6e; --warn:#ffb84d; --radius:16px;
}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;}
.topbar{display:flex;align-items:center;gap:14px;padding:18px 28px;border-bottom:1px solid var(--border);
  background:linear-gradient(180deg,#10121a,#0b0d12);}
.logo{font-weight:800;font-size:20px;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent;}
.sub{color:var(--dim);font-size:13px;}
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
.stage{position:relative;background:#000;border-radius:14px;overflow:hidden;max-width:380px;}
.stage video{display:block;width:100%;height:100%;}
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
</style>
</head>
<body>
<div class="topbar">
  <div class="logo">⚡ Shorts Studio</div>
  <div class="sub">Fetch → Cut → Live Edit → Save, all in one place</div>
</div>
<div class="wrap">

  <div class="card" id="fetchCard">
    <div class="row">
      <div style="flex:2;min-width:260px;">
        <label>YouTube URL</label>
        <input type="text" id="ytUrl" placeholder="https://www.youtube.com/watch?v=...">
      </div>
      <div style="min-width:140px;">
        <label>Quality</label>
        <select id="quality"><option value="2160">2160p</option><option value="1080" selected>1080p</option>
          <option value="720">720p</option><option value="480">480p</option></select>
      </div>
      <div style="min-width:140px;">
        <label>Mode</label>
        <select id="mode" onchange="toggleMode()"><option value="auto">Auto-split</option><option value="manual">Manual ranges</option></select>
      </div>
      <div id="autoLenWrap" style="min-width:140px;">
        <label>Clip length (s)</label>
        <input type="number" id="clipLen" value="30">
      </div>
      <div id="manualWrap" class="hidden" style="flex:2;min-width:240px;">
        <label>Ranges (start-end, one per line, seconds)</label>
        <textarea id="ranges" rows="2" placeholder="0-30
30-60"></textarea>
      </div>
      <button class="btn-grad" onclick="fetchAndCut()">🔻 Fetch &amp; Cut</button>
    </div>
    <div class="log" id="fetchLog"></div>
  </div>

  <div class="card hidden" id="clipsCard">
    <div class="flex-between"><h3 style="margin:0">Your Shorts</h3><span class="badge" id="clipCount"></span></div>
    <div class="grid" id="clipGrid"></div>
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
        <div class="slider-row"><label>Speed <span class="val" id="speedVal">1.00x</span></label>
          <input type="range" id="speed" min="0.25" max="4" step="0.05" value="1" oninput="onSpeed()"></div>
        <div class="slider-row"><label>Zoom <span class="val" id="zoomVal">1.00x</span></label>
          <input type="range" id="zoom" min="1" max="3" step="0.05" value="1" oninput="onZoom()"></div>
        <p class="sub">Zoom crops toward center then re-scales to your export size on save — never stretched.</p>
      </div>

      <div class="tabpanel" id="panel-audio">
        <div class="checkrow"><input type="radio" name="amode" value="original" checked onchange="onAudioMode()"> Keep original audio</div>
        <div class="checkrow"><input type="radio" name="amode" value="mute" onchange="onAudioMode()"> Mute</div>
        <div class="checkrow"><input type="radio" name="amode" value="replace" onchange="onAudioMode()"> Replace with file</div>
        <div class="checkrow"><input type="radio" name="amode" value="tts" onchange="onAudioMode()"> AI Voiceover</div>

        <div id="replaceWrap" class="hidden">
          <label>Upload audio file</label>
          <input type="file" id="audioFile" accept="audio/*" onchange="uploadAudio()">
        </div>

        <div id="ttsWrap" class="hidden">
          <label>Voice</label>
          <select id="ttsVoice">
            <option value="hi_male">Hindi — Male (Madhur)</option>
            <option value="hi_female">Hindi — Female (Swara)</option>
            <option value="en_in_male">English (India) — Male</option>
            <option value="en_in_female">English (India) — Female</option>
            <option value="en_us_male">English (US) — Male</option>
            <option value="en_us_female">English (US) — Female</option>
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
        <label>Overlay text</label>
        <input type="text" id="overlayText" placeholder="Your text..." oninput="renderText()">
        <div class="row" style="margin-top:8px">
          <div style="flex:1"><label>Size <span class="val" id="textSizeVal">36</span></label>
            <input type="range" id="textSize" min="14" max="90" value="36" oninput="renderText()"></div>
          <div style="width:90px"><label>Color</label><input type="color" id="textColor" value="#ffffff" oninput="renderText()"></div>
        </div>
        <div class="checkrow"><input type="checkbox" id="textBox" checked onchange="renderText()"> Background box</div>
        <p class="sub">Drag the text directly on the preview to position it.</p>
        <hr style="border-color:var(--border);margin:14px 0">
        <label>Logo / watermark image</label>
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
        <div class="slider-row"><label>Contrast <span class="val" id="contrastVal">1.00</span></label>
          <input type="range" id="contrast" min="0.5" max="2" step="0.01" value="1" oninput="onColor()"></div>
        <div class="slider-row"><label>Saturation <span class="val" id="satVal">1.00</span></label>
          <input type="range" id="saturation" min="0" max="2" step="0.01" value="1" oninput="onColor()"></div>
        <div class="slider-row"><label>Brightness <span class="val" id="brightVal">0.00</span></label>
          <input type="range" id="brightness" min="-0.3" max="0.3" step="0.01" value="0" oninput="onColor()"></div>
        <div class="checkrow"><input type="checkbox" id="sharpen"> Sharpen (clarity)</div>
        <button onclick="resetColor()">Reset</button>
      </div>

      <div class="tabpanel" id="panel-export">
        <label>Resolution</label>
        <select id="resolution"><option value="1080x1920">1080x1920 (Shorts 9:16)</option>
          <option value="1080x1080">1080x1080 (Square)</option><option value="1920x1080">1920x1080 (Landscape)</option>
          <option value="original">Keep original</option></select>
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
          <button class="btn-grad" onclick="saveVideo()">💾 Save Final Video</button>
        </div>
        <div class="log" id="exportLog"></div>
      </div>
    </div>
  </div>

</div>

<script>
let currentClipId = null, ttsUrl = null, audioFileUrl = null, logoUrl = null;
let regions = [], textState = {x:0.1,y:0.78}, logoState = {x:0.78,y:0.04};
let tool = 'blur';

function toggleMode(){
  const m = document.getElementById('mode').value;
  document.getElementById('autoLenWrap').classList.toggle('hidden', m!=='auto');
  document.getElementById('manualWrap').classList.toggle('hidden', m!=='manual');
}

function log(el, msg){ const l=document.getElementById(el); l.innerHTML += msg+"<br>"; l.scrollTop=l.scrollHeight; }

async function fetchAndCut(){
  const url = document.getElementById('ytUrl').value.trim();
  if(!url){ alert('Paste a YouTube URL first'); return; }
  const mode = document.getElementById('mode').value;
  const payload = { url, quality: document.getElementById('quality').value, mode,
    clip_len: document.getElementById('clipLen').value };
  if(mode === 'manual'){
    payload.ranges = document.getElementById('ranges').value.trim().split('\n').map(l=>l.split('-').map(Number)).filter(r=>r.length===2);
  }
  const t0 = performance.now();
  log('fetchLog', '⏳ Resolving & cutting (in parallel)...');
  const res = await fetch('/api/fetch_and_cut', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
  const data = await res.json();
  if(data.error){ log('fetchLog', '❌ '+data.error); return; }
  const secs = ((performance.now()-t0)/1000).toFixed(1);
  log('fetchLog', `✅ Cut ${data.clips.length} short(s) from "${data.title}" in ${secs}s`);
  document.getElementById('clipsCard').classList.remove('hidden');
  document.getElementById('clipCount').innerText = data.clips.length + ' clips';
  const grid = document.getElementById('clipGrid'); grid.innerHTML='';
  data.clips.forEach(c=>{
    const div = document.createElement('div'); div.className='clip-card';
    div.innerHTML = `<video src="/media/${c.clip_id}" muted></video><div class="lbl">${c.label}</div>`;
    div.onclick = ()=>openEditor(c.clip_id);
    grid.appendChild(div);
  });
}

function openEditor(clipId){
  currentClipId = clipId;
  regions = []; ttsUrl=null; audioFileUrl=null; logoUrl=null;
  document.getElementById('overlayLayer').innerHTML='';
  document.getElementById('overlayText') && (document.getElementById('overlayText').value='');
  document.getElementById('editorCard').classList.add('active');
  const player = document.getElementById('player');
  player.src = '/media/'+clipId;
  player.muted = false;
  document.querySelectorAll('input[name=amode]')[0].checked = true;
  onAudioMode();
  resetColor();
  document.getElementById('speed').value=1; onSpeed();
  document.getElementById('zoom').value=1; onZoom();
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
}
function onZoom(){
  const v = parseFloat(document.getElementById('zoom').value);
  document.getElementById('zoomVal').innerText = v.toFixed(2)+'x';
  document.getElementById('player').style.transform = `scale(${v})`;
}
function onColor(){
  const c = document.getElementById('contrast').value, s = document.getElementById('saturation').value, b = document.getElementById('brightness').value;
  document.getElementById('contrastVal').innerText = parseFloat(c).toFixed(2);
  document.getElementById('satVal').innerText = parseFloat(s).toFixed(2);
  document.getElementById('brightVal').innerText = parseFloat(b).toFixed(2);
  const brightPct = 1 + parseFloat(b);
  document.getElementById('player').style.filter = `contrast(${c}) saturate(${s}) brightness(${brightPct})`;
}
function resetColor(){
  document.getElementById('contrast').value=1; document.getElementById('saturation').value=1;
  document.getElementById('brightness').value=0; document.getElementById('sharpen').checked=false;
  onColor();
}

function onAudioMode(){
  const mode = document.querySelector('input[name=amode]:checked').value;
  document.getElementById('replaceWrap').classList.toggle('hidden', mode!=='replace');
  document.getElementById('ttsWrap').classList.toggle('hidden', mode!=='tts');
  document.getElementById('player').muted = (mode==='mute');
}

async function uploadAudio(){
  const f = document.getElementById('audioFile').files[0]; if(!f) return;
  const fd = new FormData(); fd.append('file', f);
  const res = await fetch('/api/upload', {method:'POST', body: fd});
  const data = await res.json(); audioFileUrl = data.url;
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

function renderText(){
  const text = document.getElementById('overlayText').value;
  let el = document.getElementById('ovText');
  if(!text){ if(el) el.remove(); return; }
  if(!el){
    el = document.createElement('div'); el.className='ov-text'; el.id='ovText';
    makeDraggable(el, textState);
    document.getElementById('overlayLayer').appendChild(el);
  }
  el.innerText = text;
  el.style.fontSize = document.getElementById('textSize').value+'px';
  el.style.color = document.getElementById('textColor').value;
  el.style.background = document.getElementById('textBox').checked ? 'rgba(0,0,0,.45)' : 'transparent';
  el.style.left = (textState.x*100)+'%';
  el.style.top = (textState.y*100)+'%';
  document.getElementById('textSizeVal').innerText = document.getElementById('textSize').value;
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
  document.getElementById('logoWVal').innerText = document.getElementById('logoW').value;
  document.getElementById('logoOVal').innerText = document.getElementById('logoO').value;
}

function makeDraggable(el, state){
  el.onmousedown = (e)=>{
    e.preventDefault();
    const stage = document.getElementById('stage');
    const rect = stage.getBoundingClientRect();
    function move(ev){
      let x = (ev.clientX - rect.left)/rect.width;
      let y = (ev.clientY - rect.top)/rect.height;
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

function clearRegions(){
  regions = [];
  document.querySelectorAll('.ov-region').forEach(e=>e.remove());
}

async function saveVideo(){
  if(!currentClipId){ return; }
  const amode = document.querySelector('input[name=amode]:checked').value;
  const settings = {
    speed: parseFloat(document.getElementById('speed').value),
    zoom: parseFloat(document.getElementById('zoom').value),
    contrast: parseFloat(document.getElementById('contrast').value),
    saturation: parseFloat(document.getElementById('saturation').value),
    brightness: parseFloat(document.getElementById('brightness').value),
    sharpen: document.getElementById('sharpen').checked,
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
    text: document.getElementById('overlayText').value ? {
      content: document.getElementById('overlayText').value,
      x: textState.x, y: textState.y,
      size: parseInt(document.getElementById('textSize').value),
      color: document.getElementById('textColor').value,
      box: document.getElementById('textBox').checked
    } : null,
    logo: logoUrl ? {
      url: logoUrl, x: logoState.x, y: logoState.y,
      w: document.getElementById('logoW').value/100,
      opacity: document.getElementById('logoO').value/100
    } : null
  };
  const t0 = performance.now();
  log('exportLog', '⏳ Exporting final video...');
  const res = await fetch('/api/export', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({clip_id: currentClipId, settings})});
  const data = await res.json();
  if(data.error){ log('exportLog', '❌ '+data.error); return; }
  const secs = ((performance.now()-t0)/1000).toFixed(1);
  log('exportLog', `✅ Saved in ${secs}s! <a class="dl-link" href="${data.url}" target="_blank">Download / open file</a> (also saved on disk at ${data.path})`);
}
</script>
</body>
</html>
"""


def main():
    port = 5757
    url = f"http://127.0.0.1:{port}/"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"Shorts Studio running at {url}")
    print(f"Parallel clip-cutting workers: {MAX_CUT_WORKERS}")
    if not EDGE_TTS_OK:
        print("NOTE: edge-tts not installed — AI voiceover will be disabled. Run: pip install edge-tts")
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()