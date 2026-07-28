"""
AI Smart Text Converter — production pipeline
================================================
Audio/Video -> faster-whisper (CTranslate2 + built-in Silero VAD) -> TXT / SRT / VTT / JSON

Install:
    pip install flask faster-whisper av numpy

Run:
    python text_converter.py
"""

import os
import json
import uuid
import hashlib
import logging
import subprocess
from pathlib import Path
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import av
from flask import Flask, request, jsonify, render_template_string, send_from_directory

try:
    from faster_whisper import WhisperModel
    import ctranslate2
except ImportError:
    print("[Error] Kripya run karein: pip install faster-whisper")
    raise SystemExit(1)

# ══════════════════════════════ Config ══════════════════════════════
class Config:
    UPLOAD_FOLDER = Path('./uploaded_media')
    OUTPUT_FOLDER = Path('./transcription_output')
    CHECKPOINT_FOLDER = Path('./checkpoints')

    SAMPLE_RATE = 16000
    DEFAULT_MODEL_SIZE = 'base'

    # Files longer than this get automatically split into chunks so memory use
    # stays bounded and progress/crash-resume become possible. Short/medium
    # files (the common case) skip chunking entirely and get the highest-quality
    # single-pass decode (no chunk-boundary artifacts).
    CHUNK_THRESHOLD_SECONDS = 1 * 60
    CHUNK_LENGTH_SECONDS = 20 * 60

    # How many transcription jobs run at the same time. Extra uploads queue
    # instead of all launching at once and fighting over RAM/CPU.
    MAX_CONCURRENT_JOBS = 2


for folder in (Config.UPLOAD_FOLDER, Config.OUTPUT_FOLDER, Config.CHECKPOINT_FOLDER):
    folder.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("text_converter")

# ══════════════════════════════ FFmpeg / device setup ══════════════════════════════
# Same rule as before: never call a bare "ffmpeg" string, always the exact
# resolved binary path. This is what avoids "[WinError 2] system cannot find
# the file specified" on Windows.
try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    logger.info(f"FFmpeg resolved at: {FFMPEG}")
except ImportError:
    FFMPEG = None
    logger.warning("imageio-ffmpeg not installed -- chunked mode for long files will be unavailable "
                    "(pip install imageio-ffmpeg to enable it). Normal-length files still work fine, "
                    "faster-whisper decodes those via PyAV directly.")

CUDA_AVAILABLE = ctranslate2.get_cuda_device_count() > 0
DEVICE = "cuda" if CUDA_AVAILABLE else "cpu"
COMPUTE_TYPE = "float16" if CUDA_AVAILABLE else "int8"
logger.info(f"faster-whisper device: {DEVICE} ({COMPUTE_TYPE})")

app = Flask(__name__)
TRANSCRIBE_JOBS = {}
JOB_EXECUTOR = ThreadPoolExecutor(max_workers=Config.MAX_CONCURRENT_JOBS)

_MODEL_CACHE = {}
_MODEL_LOCK = Lock()

LANGUAGE_OPTIONS = {"auto": None, "hi": "hi", "en": "en", "ur": "ur"}


def get_model(model_size):
    """Loads a Whisper model once and reuses it for every future request of
    the same size, instead of reloading weights from disk every job."""
    with _MODEL_LOCK:
        if model_size not in _MODEL_CACHE:
            logger.info(f"Loading model '{model_size}' into memory (first use)...")
            _MODEL_CACHE[model_size] = WhisperModel(model_size, device=DEVICE, compute_type=COMPUTE_TYPE)
        return _MODEL_CACHE[model_size]


def console_log(job, message):
    logger.info(f"[{job.get('id', '----')}] {message}")
    job["logs"].append(message)


def _no_console_kwargs():
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


# ══════════════════════════════ Duration probing & file hashing ══════════════════════════════
def get_media_duration(path):
    """Cheap container-level duration read via PyAV -- no full decode needed."""
    container = av.open(str(path))
    duration = None
    if container.duration is not None:
        duration = float(container.duration) / av.time_base
    container.close()
    return duration


def hash_file(path, block_size=8 * 1024 * 1024):
    """Content hash used to key checkpoints, so re-uploading the same file
    after a crash can resume instead of restarting from zero."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(block_size):
            h.update(chunk)
    return h.hexdigest()[:24]


# ══════════════════════════════ Chunk splitting (long files only) ══════════════════════════════
def split_into_chunks(file_path, chunk_dir):
    """One-pass ffmpeg segment split into fixed-length mono 16kHz WAV chunks.
    Uses the segment muxer so the whole file is read once, not re-seeked per chunk."""
    chunk_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(chunk_dir / "chunk_%04d.wav")
    cmd = [
        FFMPEG, "-y", "-i", str(file_path),
        "-ar", str(Config.SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le",
        "-f", "segment", "-segment_time", str(Config.CHUNK_LENGTH_SECONDS),
        "-reset_timestamps", "1",
        pattern,
    ]
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **_no_console_kwargs())
    if process.returncode != 0:
        raise RuntimeError(f"Chunk splitting failed: {process.stderr.decode(errors='ignore')[-1500:]}")
    return sorted(chunk_dir.glob("chunk_*.wav"))


def load_manifest(manifest_path):
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_manifest(manifest_path, manifest):
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False)


# ══════════════════════════════ Output format writers ══════════════════════════════
def _srt_timestamp(seconds):
    td = timedelta(seconds=max(0, seconds))
    total_ms = int(td.total_seconds() * 1000)
    h, rem = divmod(total_ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _vtt_timestamp(seconds):
    td = timedelta(seconds=max(0, seconds))
    total_ms = int(td.total_seconds() * 1000)
    h, rem = divmod(total_ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def write_outputs(base_name, segments, language):
    """segments: list of dicts {start, end, text}. Writes txt/srt/vtt/json and
    returns the four filenames."""
    stem = f"{base_name}_{uuid.uuid4()}"
    files = {}

    txt_name = f"{stem}.txt"
    with open(Config.OUTPUT_FOLDER / txt_name, "w", encoding="utf-8") as f:
        f.write(" ".join(s["text"].strip() for s in segments).strip())
    files["txt"] = txt_name

    srt_name = f"{stem}.srt"
    with open(Config.OUTPUT_FOLDER / srt_name, "w", encoding="utf-8") as f:
        for i, s in enumerate(segments, start=1):
            f.write(f"{i}\n{_srt_timestamp(s['start'])} --> {_srt_timestamp(s['end'])}\n{s['text'].strip()}\n\n")
    files["srt"] = srt_name

    vtt_name = f"{stem}.vtt"
    with open(Config.OUTPUT_FOLDER / vtt_name, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for s in segments:
            f.write(f"{_vtt_timestamp(s['start'])} --> {_vtt_timestamp(s['end'])}\n{s['text'].strip()}\n\n")
    files["vtt"] = vtt_name

    json_name = f"{stem}.json"
    with open(Config.OUTPUT_FOLDER / json_name, "w", encoding="utf-8") as f:
        json.dump({"language": language, "segments": segments}, f, ensure_ascii=False, indent=2)
    files["json"] = json_name

    return files


# ══════════════════════════════ Transcription core ══════════════════════════════
def transcribe_audio(model, audio_path, language, job, progress_cb):
    """Runs faster-whisper on one (whole-file or chunk) audio path and streams
    real progress based on segment timestamps vs total duration."""
    duration = get_media_duration(audio_path) or 0
    segments_gen, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        condition_on_previous_text=False,
    )
    detected_language = info.language
    result = []
    for seg in segments_gen:
        result.append({"start": seg.start, "end": seg.end, "text": seg.text})
        if duration > 0:
            progress_cb(min(1.0, seg.end / duration))
    return result, detected_language


def run_pipeline(file_path, job_id, model_size, language_code):
    job = TRANSCRIBE_JOBS[job_id]
    job["id"] = job_id
    job["status"] = "processing"

    try:
        forced_language = LANGUAGE_OPTIONS.get(language_code)
        console_log(job, f"Loading model ({model_size}) on {DEVICE}...")
        job["percent"] = 5
        model = get_model(model_size)

        duration = get_media_duration(file_path) or 0
        console_log(job, f"Media duration: {duration/60:.1f} min")

        if forced_language:
            console_log(job, f"Language locked to '{forced_language}' (prevents script-switching).")
        else:
            console_log(job, "Auto-detecting language.")

        use_chunking = FFMPEG is not None and duration > Config.CHUNK_THRESHOLD_SECONDS

        if not use_chunking:
            # ── Normal path: single-pass, highest quality, real progress ──
            console_log(job, "Transcribing (voice-activity filtering skips music/silence)...")

            def progress_cb(frac):
                job["percent"] = 10 + int(frac * 85)

            segments, detected_lang = transcribe_audio(model, file_path, forced_language, job, progress_cb)
            language_used = forced_language or detected_lang
            if not forced_language:
                console_log(job, f"Detected language: {detected_lang}")

        else:
            # ── Long-file path: chunked + resumable via content-hash checkpoint ──
            file_hash = hash_file(file_path)
            job_checkpoint_dir = Config.CHECKPOINT_FOLDER / file_hash
            chunk_dir = job_checkpoint_dir / "chunks"
            manifest_path = job_checkpoint_dir / "manifest.json"

            manifest = load_manifest(manifest_path)
            same_config = (
                manifest
                and manifest.get("model_size") == model_size
                and manifest.get("language") == language_code
                and manifest.get("chunk_length") == Config.CHUNK_LENGTH_SECONDS
            )

            if same_config and chunk_dir.exists():
                console_log(job, f"Resuming previous run for this file "
                                  f"({len(manifest['completed_chunks'])} chunk(s) already done).")
                chunk_paths = sorted(chunk_dir.glob("chunk_*.wav"))
            else:
                console_log(job, f"Long file ({duration/60:.0f} min) -- splitting into "
                                  f"{Config.CHUNK_LENGTH_SECONDS//60}-minute chunks...")
                chunk_paths = split_into_chunks(file_path, chunk_dir)
                manifest = {
                    "model_size": model_size,
                    "language": language_code,
                    "chunk_length": Config.CHUNK_LENGTH_SECONDS,
                    "completed_chunks": [],
                    "segments": {},
                }
                save_manifest(manifest_path, manifest)

            total_chunks = len(chunk_paths)
            console_log(job, f"{total_chunks} chunk(s) total.")
            detected_lang = forced_language

            for idx, chunk_path in enumerate(chunk_paths):
                if idx in manifest["completed_chunks"]:
                    continue

                console_log(job, f"Transcribing chunk {idx + 1}/{total_chunks}...")

                def progress_cb(frac, idx=idx):
                    job["percent"] = 5 + int(((idx + frac) / total_chunks) * 90)

                chunk_segments, lang = transcribe_audio(model, chunk_path, forced_language, job, progress_cb)
                if not forced_language and detected_lang is None:
                    detected_lang = lang
                    console_log(job, f"Detected language: {detected_lang}")

                offset = idx * Config.CHUNK_LENGTH_SECONDS
                for s in chunk_segments:
                    s["start"] += offset
                    s["end"] += offset

                manifest["segments"][str(idx)] = chunk_segments
                manifest["completed_chunks"].append(idx)
                save_manifest(manifest_path, manifest)  # checkpoint after every chunk

            segments = []
            for idx in range(total_chunks):
                segments.extend(manifest["segments"][str(idx)])
            language_used = forced_language or detected_lang or "unknown"

            # Job finished successfully -- checkpoint no longer needed.
            for p in chunk_dir.glob("chunk_*.wav"):
                p.unlink(missing_ok=True)
            manifest_path.unlink(missing_ok=True)
            try:
                chunk_dir.rmdir()
                job_checkpoint_dir.rmdir()
            except OSError:
                pass

        job["percent"] = 95
        console_log(job, "Writing TXT / SRT / VTT / JSON outputs...")
        output_files = write_outputs(file_path.stem, segments, language_used)

        preview = " ".join(s["text"].strip() for s in segments)[:500]
        job["preview"] = preview + "..." if len(preview) == 500 else preview

        try:
            file_path.unlink()
        except OSError:
            pass

        job["percent"] = 100
        job["status"] = "done"
        console_log(job, "Transcription completed successfully!")
        job["result"] = {fmt: f"/api/download/{name}" for fmt, name in output_files.items()}

    except Exception as e:
        job["status"] = "error"
        console_log(job, f"Pipeline Execution Failed: {str(e)}")
        logger.exception(f"Job {job_id} failed")


# ══════════════════════════════ Web API Routing Control ══════════════════════════════
@app.route('/')
def index_ui():
    return render_template_string(HTML_UI_TEMPLATE)


@app.route('/api/upload-and-transcribe', methods=['POST'])
def handle_upload():
    if 'media' not in request.files:
        return jsonify({"error": "No media file field"}), 400

    file = request.files['media']
    model_size = request.form.get('model_size', Config.DEFAULT_MODEL_SIZE)
    language_code = request.form.get('language', 'hi')

    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    file_extension = Path(file.filename).suffix
    unique_name = f"{uuid.uuid4()}{file_extension}"
    save_path = Config.UPLOAD_FOLDER / unique_name
    file.save(str(save_path))

    job_id = str(uuid.uuid4())
    TRANSCRIBE_JOBS[job_id] = {
        "status": "queued",
        "percent": 0,
        "logs": ["Media uploaded successfully.", "Queued -- will start as soon as a worker is free..."],
        "preview": "",
        "result": None,
    }

    JOB_EXECUTOR.submit(run_pipeline, save_path, job_id, model_size, language_code)
    return jsonify({"job_id": job_id})


@app.route('/api/job-status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    job = TRANSCRIBE_JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Invalid identifier"}), 404
    return jsonify(job)


@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(Config.OUTPUT_FOLDER, filename, as_attachment=True)


# ══════════════════════════════ Frontend UI ══════════════════════════════
HTML_UI_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Audio/Video Text Converter</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0b1120; --panel: #131b2e; --panel-2: #1a2438; --border: #26314a;
            --text: #e7ecf7; --muted: #8a93a8; --accent: #6366f1; --accent-2: #8b5cf6;
            --success: #22c55e; --danger: #ef4444; --warn: #f59e0b;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            background:
                radial-gradient(1200px 600px at 15% -10%, rgba(99,102,241,0.18), transparent 60%),
                radial-gradient(1000px 500px at 110% 10%, rgba(139,92,246,0.14), transparent 55%),
                var(--bg);
            color: var(--text); font-family: 'Inter', system-ui, sans-serif;
            min-height: 100vh; padding: 48px 20px;
        }
        .wrap { max-width: 720px; margin: 0 auto; }
        .brand { display: flex; align-items: center; gap: 12px; margin-bottom: 28px; justify-content: center; }
        .brand-icon {
            width: 42px; height: 42px; border-radius: 12px;
            background: linear-gradient(135deg, var(--accent), var(--accent-2));
            display: flex; align-items: center; justify-content: center; font-size: 20px;
            box-shadow: 0 8px 24px rgba(99,102,241,0.35);
        }
        .brand h1 { font-size: 20px; font-weight: 700; margin: 0; }
        .brand p { margin: 0; color: var(--muted); font-size: 13px; }
        .card {
            background: var(--panel); border: 1px solid var(--border); border-radius: 18px;
            padding: 28px; margin-bottom: 20px; box-shadow: 0 20px 50px rgba(0,0,0,0.35);
        }
        .dropzone {
            border: 2px dashed var(--border); border-radius: 14px; padding: 32px 20px;
            text-align: center; cursor: pointer; transition: all 0.2s ease; background: var(--panel-2);
        }
        .dropzone:hover, .dropzone.dragover { border-color: var(--accent); background: rgba(99,102,241,0.08); }
        .dropzone .icon { font-size: 30px; margin-bottom: 8px; }
        .dropzone .primary-txt { font-weight: 600; font-size: 15px; }
        .dropzone .sub-txt { color: var(--muted); font-size: 13px; margin-top: 4px; }
        .file-chip {
            display: none; margin-top: 14px; align-items: center; gap: 10px;
            background: var(--panel-2); border: 1px solid var(--border); border-radius: 10px;
            padding: 10px 14px; font-size: 13px;
        }
        .file-chip.show { display: flex; }
        .file-chip .name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; }
        .file-chip .size { color: var(--muted); }
        .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
        .field-label { display: block; font-size: 13px; font-weight: 600; color: var(--muted); margin: 20px 0 8px; text-transform: uppercase; letter-spacing: 0.04em; }
        select.form-control {
            width: 100%; background: var(--panel-2); color: var(--text);
            border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; font-size: 14px; appearance: none;
        }
        .model-hint { font-size: 12px; color: var(--muted); margin-top: 6px; }
        button.submit-btn {
            width: 100%; margin-top: 22px; padding: 14px; border: none; border-radius: 12px;
            background: linear-gradient(135deg, var(--accent), var(--accent-2));
            color: white; font-weight: 700; font-size: 15px; cursor: pointer;
            transition: transform 0.15s ease, opacity 0.15s ease;
        }
        button.submit-btn:hover { transform: translateY(-1px); }
        button.submit-btn:disabled { opacity: 0.55; cursor: not-allowed; transform: none; }
        .status-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
        .status-header h3 { margin: 0; font-size: 16px; }
        .badge {
            font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
            padding: 5px 10px; border-radius: 999px; background: var(--panel-2); border: 1px solid var(--border);
        }
        .badge.processing { color: var(--warn); border-color: rgba(245,158,11,0.4); }
        .badge.done { color: var(--success); border-color: rgba(34,197,94,0.4); }
        .badge.error { color: var(--danger); border-color: rgba(239,68,68,0.4); }
        .badge.queued { color: var(--muted); }
        .progress-track { background: var(--panel-2); border-radius: 999px; height: 10px; overflow: hidden; margin-bottom: 20px; }
        .progress-fill { height: 100%; width: 0%; background: linear-gradient(90deg, var(--accent), var(--accent-2)); transition: width 0.4s ease; }
        .log-box {
            background: #060a14; border: 1px solid var(--border); color: #7dd3fc;
            font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12.5px;
            height: 190px; overflow-y: auto; padding: 14px; border-radius: 10px; white-space: pre-wrap; line-height: 1.6;
        }
        .preview-box {
            background: var(--panel-2); border: 1px dashed var(--border); padding: 16px;
            border-radius: 10px; color: #cbd5e1; font-size: 13.5px; max-height: 200px; overflow-y: auto; margin-top: 16px; line-height: 1.6;
        }
        .result-box { margin-top: 20px; }
        .result-box .title { color: var(--success); font-weight: 700; margin-bottom: 12px; text-align: center; }
        .download-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        a.download-btn {
            display: block; padding: 12px; border-radius: 10px;
            background: rgba(34,197,94,0.12); border: 1px solid rgba(34,197,94,0.4);
            color: var(--success); font-weight: 700; text-decoration: none; font-size: 13.5px; text-align: center;
        }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="wrap">
        <div class="brand">
            <div class="brand-icon">🎙️</div>
            <div>
                <h1>AI Smart Text Converter</h1>
                <p>Audio/video &rarr; text, subtitles &amp; JSON</p>
            </div>
        </div>

        <div class="card">
            <form id="uploadForm" enctype="multipart/form-data">
                <div class="dropzone" id="dropzone">
                    <div class="icon">📁</div>
                    <div class="primary-txt">Click to browse or drag a file here</div>
                    <div class="sub-txt">MP3, WAV, MP4, MKV, MOV, WEBM — any length</div>
                    <input type="file" id="fileInput" name="media" accept="video/*,audio/*" required style="display:none;">
                </div>
                <div class="file-chip" id="fileChip">
                    <span>🎵</span>
                    <span class="name" id="fileName"></span>
                    <span class="size" id="fileSize"></span>
                </div>

                <div class="two-col">
                    <div>
                        <label class="field-label">Spoken Language</label>
                        <select class="form-control" name="language" id="language">
                            <option value="hi" selected>Hindi</option>
                            <option value="en">English</option>
                            <option value="ur">Urdu</option>
                            <option value="auto">Auto-detect</option>
                        </select>
                    </div>
                    <div>
                        <label class="field-label">Model</label>
                        <select class="form-control" name="model_size" id="modelSize">
                            <option value="tiny">Tiny — fastest</option>
                            <option value="base" selected>Base — balanced</option>
                            <option value="small">Small — most accurate</option>
                        </select>
                    </div>
                </div>
                <div class="model-hint">Files over 45 minutes are automatically chunked and checkpointed — safe to re-upload after a crash, it resumes instead of restarting.</div>

                <button type="submit" class="submit-btn" id="submitBtn">Start Text Extraction</button>
            </form>
        </div>

        <div class="card hidden" id="statusPanel">
            <div class="status-header">
                <h3>Pipeline Status</h3>
                <span class="badge queued" id="statusBadge">Queued</span>
            </div>
            <div class="progress-track"><div class="progress-fill" id="progressBar"></div></div>
            <div class="log-box" id="logConsole"></div>
            <div class="preview-box hidden" id="previewContainer">
                <div style="color:#93c5fd; font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:8px;">Transcript preview</div>
                <div id="textPreview"></div>
            </div>
            <div class="result-box hidden" id="resultBox">
                <div class="title">🎉 Conversion complete!</div>
                <div class="download-grid">
                    <a href="#" class="download-btn" id="dlTxt">⬇️ TXT</a>
                    <a href="#" class="download-btn" id="dlSrt">⬇️ SRT</a>
                    <a href="#" class="download-btn" id="dlVtt">⬇️ VTT</a>
                    <a href="#" class="download-btn" id="dlJson">⬇️ JSON</a>
                </div>
            </div>
        </div>
    </div>

    <script>
        const dropzone = document.getElementById('dropzone');
        const fileInput = document.getElementById('fileInput');
        const fileChip = document.getElementById('fileChip');
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');
        const form = document.getElementById('uploadForm');
        const statusPanel = document.getElementById('statusPanel');
        const progressBar = document.getElementById('progressBar');
        const statusBadge = document.getElementById('statusBadge');
        const logConsole = document.getElementById('logConsole');
        const resultBox = document.getElementById('resultBox');
        const submitBtn = document.getElementById('submitBtn');
        const previewContainer = document.getElementById('previewContainer');
        const textPreview = document.getElementById('textPreview');

        dropzone.addEventListener('click', () => fileInput.click());
        ['dragenter', 'dragover'].forEach(evt => dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.add('dragover'); }));
        ['dragleave', 'drop'].forEach(evt => dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.remove('dragover'); }));
        dropzone.addEventListener('drop', e => { if (e.dataTransfer.files.length) { fileInput.files = e.dataTransfer.files; updateFileChip(); } });
        fileInput.addEventListener('change', updateFileChip);

        function updateFileChip() {
            if (fileInput.files.length) {
                const f = fileInput.files[0];
                fileName.innerText = f.name;
                fileSize.innerText = (f.size / (1024 * 1024)).toFixed(1) + ' MB';
                fileChip.classList.add('show');
            }
        }
        function setBadge(status) {
            statusBadge.className = 'badge ' + status;
            statusBadge.innerText = status.charAt(0).toUpperCase() + status.slice(1);
        }

        form.onsubmit = async (e) => {
            e.preventDefault();
            if (!fileInput.files.length) return;
            submitBtn.disabled = true;
            statusPanel.classList.remove('hidden');
            resultBox.classList.add('hidden');
            previewContainer.classList.add('hidden');
            logConsole.innerText = '';
            progressBar.style.width = '0%';
            setBadge('queued');

            let formData = new FormData(form);
            logConsole.innerText += "[System] Streaming media package to server...\\n";
            try {
                let res = await fetch('/api/upload-and-transcribe', { method: 'POST', body: formData });
                let data = await res.json();
                if (data.job_id) { trackJob(data.job_id); }
                else {
                    logConsole.innerText += `[Error] Upload failure: ${data.error}\\n`;
                    setBadge('error'); submitBtn.disabled = false;
                }
            } catch (err) {
                logConsole.innerText += `[Error] Failed to connect to server.\\n`;
                setBadge('error'); submitBtn.disabled = false;
            }
        };

        function trackJob(jobId) {
            let interval = setInterval(async () => {
                let res = await fetch(`/api/job-status/${jobId}`);
                let job = await res.json();
                setBadge(job.status);
                progressBar.style.width = job.percent + '%';
                logConsole.innerText = job.logs.map(l => `[Log] ${l}`).join('\\n');
                logConsole.scrollTop = logConsole.scrollHeight;

                if (job.status === 'done') {
                    clearInterval(interval);
                    submitBtn.disabled = false;
                    resultBox.classList.remove('hidden');
                    document.getElementById('dlTxt').href = job.result.txt;
                    document.getElementById('dlSrt').href = job.result.srt;
                    document.getElementById('dlVtt').href = job.result.vtt;
                    document.getElementById('dlJson').href = job.result.json;
                    if (job.preview) {
                        previewContainer.classList.remove('hidden');
                        textPreview.innerText = job.preview;
                    }
                } else if (job.status === 'error') {
                    clearInterval(interval);
                    submitBtn.disabled = false;
                }
            }, 1000);
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8084, debug=True)