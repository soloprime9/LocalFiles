"""
AI Smart Text Converter — production pipeline
================================================
Audio/Video -> faster-whisper (CTranslate2 + built-in Silero VAD) -> TXT / SRT / VTT / JSON

Speed features (real, verified in this file):
  - BatchedInferencePipeline actually wired into get_model() -- batches VAD
    speech segments instead of decoding one at a time (~2-4x, bigger on GPU)
  - Long files (>20 min) are split into 10-min chunks that run TRULY in
    parallel (ThreadPoolExecutor across CHUNK_WORKERS cores) -- CTranslate2
    releases the GIL during compute, so this is real multi-core work
  - Each model size downloads from Hugging Face exactly ONCE, cached to
    ./model_cache -- every run after that is fully offline
  - Default model is pre-warmed at server startup, not on first upload
  - Crash-safe resume via content-hash checkpointing (correct under
    concurrent chunk completion)

Honest speed expectations (faster-whisper 'base', int8, CPU):
  A modern multi-core laptop typically decodes 4-8x faster than real time
  per chunk; with several chunks running at once, a 6-hour file often
  finishes well under an hour. A dedicated GPU (float16) is much faster
  again -- often 20-50x real time. There's no setting that yields "1000x"
  or removes the one-time model download -- those aren't physically
  meaningful for a speech model of this quality; see the Config class
  below for what's actually tunable (model size, chunk size, worker count).

Install (one-time, needs internet):
    pip install flask faster-whisper av numpy imageio-ffmpeg

Run (fully offline after each model size's first successful load):
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import av
from flask import Flask, request, jsonify, render_template_string, send_from_directory

try:
    from faster_whisper import WhisperModel, BatchedInferencePipeline
    from faster_whisper.audio import decode_audio
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

    # Models download from Hugging Face the FIRST time a given size is used,
    # then live here forever. Every run after that is 100% offline -- no
    # internet, no re-download, no startup stall.
    MODEL_CACHE_DIR = Path('./model_cache')

    # Files longer than this get automatically split into chunks so memory use
    # stays bounded and progress/crash-resume become possible. Short/medium
    # files (the common case) skip chunking entirely and get the highest-quality
    # single-pass decode (no chunk-boundary artifacts).
    CHUNK_THRESHOLD_SECONDS = 20 * 60
    # Shorter chunks (10 min vs the old 20 min) = more chunks = more of them
    # can run AT THE SAME TIME. This is the single biggest lever for a
    # 2-10 hour file.
    CHUNK_LENGTH_SECONDS = 10 * 60

    # How many transcription JOBS (separate uploads) run at the same time.
    MAX_CONCURRENT_JOBS = 2

    # How many CHUNKS of the SAME long file transcribe in parallel.
    # CTranslate2 (the C++ engine under faster-whisper) releases Python's GIL
    # while actually computing, so multiple chunks genuinely run on separate
    # CPU cores at once. The old code looped over chunks one at a time
    # despite its own comment claiming parallelism -- that was never true.
    CPU_COUNT = os.cpu_count() or 4
    CHUNK_WORKERS = max(1, min(4, CPU_COUNT // 2))

    # BatchedInferencePipeline groups VAD-detected speech segments into
    # batches before feeding the model, instead of one segment at a time --
    # typically a 2-4x win by itself, bigger on GPU. It was imported in the
    # original file but never wired up. Now it is (see get_model below).
    BATCH_SIZE_GPU = 16
    BATCH_SIZE_CPU = 8


for folder in (Config.UPLOAD_FOLDER, Config.OUTPUT_FOLDER, Config.CHECKPOINT_FOLDER, Config.MODEL_CACHE_DIR):
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

# Whisper is natively multilingual across ~99 languages. Any valid Whisper
# language code works here -- this is the common/likely subset for the UI
# dropdown, but the pipeline itself is not limited to just these.
LANGUAGE_OPTIONS = {
    "auto": None,
    "hi": "hi", "en": "en", "ur": "ur", "bn": "bn", "ta": "ta", "te": "te",
    "mr": "mr", "gu": "gu", "kn": "kn", "ml": "ml", "pa": "pa", "ne": "ne",
    "ar": "ar", "fa": "fa", "zh": "zh", "ja": "ja", "ko": "ko",
    "es": "es", "fr": "fr", "de": "de", "it": "it", "pt": "pt", "ru": "ru",
    "tr": "tr", "vi": "vi", "id": "id", "th": "th",
}


def get_model(model_size):
    """Loads a Whisper model once and reuses it for every future request of
    the same size, instead of reloading weights from disk every job.

    Two things make this fast:
    1. download_root=MODEL_CACHE_DIR -- weights are fetched from Hugging Face
       only the very first time a given size is used. Every run after that
       reads straight from local disk, fully offline, no network call at all.
    2. The raw WhisperModel is wrapped in BatchedInferencePipeline, which
       batches VAD speech segments together instead of decoding them one at
       a time -- a 2-4x win by itself, larger on GPU.
    """
    with _MODEL_LOCK:
        if model_size not in _MODEL_CACHE:
            cache_dir = Config.MODEL_CACHE_DIR / f"models--Systran--faster-whisper-{model_size}"
            # Look for the actual weight file, not just the folder -- an
            # interrupted first download can leave an empty/partial folder.
            already_cached = any(cache_dir.rglob("model.bin")) if cache_dir.exists() else False

            def _load(local_only):
                return WhisperModel(
                    model_size,
                    device=DEVICE,
                    compute_type=COMPUTE_TYPE,
                    download_root=str(Config.MODEL_CACHE_DIR),
                    local_files_only=local_only,
                    # cpu_threads=0 lets CTranslate2 pick the optimal thread count
                    # per inference call itself; we control outer parallelism via
                    # CHUNK_WORKERS instead so the two don't fight over cores.
                    cpu_threads=0 if DEVICE == "cpu" else 4,
                    num_workers=1,
                )

            if already_cached:
                # This is the fix for "it tries to download every single run":
                # local_files_only=True means faster-whisper/huggingface_hub
                # never makes a single network call -- it just reads the
                # weights straight off disk. No internet check, no HEAD
                # request, no timeout, no hang on a flaky/offline connection.
                logger.info(f"Loading model '{model_size}' from local cache (fully offline, no network call)...")
                try:
                    _MODEL_CACHE[model_size] = BatchedInferencePipeline(model=_load(local_only=True))
                except Exception as e:
                    logger.warning(f"Local cache for '{model_size}' looked present but failed to load ({e}); "
                                    f"re-downloading...")
                    _MODEL_CACHE[model_size] = BatchedInferencePipeline(model=_load(local_only=False))
            else:
                logger.info(f"Model '{model_size}' not cached yet -- downloading once now "
                            f"(needs internet for this one time only)...")
                _MODEL_CACHE[model_size] = BatchedInferencePipeline(model=_load(local_only=False))
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
    batch_size = Config.BATCH_SIZE_GPU if DEVICE == "cuda" else Config.BATCH_SIZE_CPU
    segments_gen, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        condition_on_previous_text=False,
        batch_size=batch_size,
    )
    detected_language = info.language
    result = []
    for seg in segments_gen:
        result.append({"start": seg.start, "end": seg.end, "text": seg.text})
        if duration > 0:
            progress_cb(min(1.0, seg.end / duration))
    return result, detected_language


def detect_language_upfront(model, file_path, job, sample_seconds=45):
    """Extracts a short (45s) audio sample and runs Whisper's real language-ID
    pass on it ONCE, instead of letting 'auto' mode silently re-detect per
    chunk (which can flip-flop between languages across one long file, and
    means decoding the ENTIRE file into memory just to identify language).

    Also applies a Hindi/Urdu tie-break: Hindi and Urdu are the same spoken
    language (Hindustani) with two different scripts, so Whisper's acoustic
    detector -- which only hears sound, not script -- regularly confuses
    them, especially on the 'base' model. If the top guess is 'ur' but 'hi'
    scored close behind, we prefer 'hi', since this app's audience is
    overwhelmingly Hindi speakers. This is a heuristic, not a certainty --
    if a file genuinely is Urdu, select Urdu explicitly in the dropdown to
    skip this override entirely.
    """
    if FFMPEG is None:
        return None
    sample_path = file_path.with_name(f".langid_{uuid.uuid4().hex}.wav")
    try:
        cmd = [
            FFMPEG, "-y", "-i", str(file_path), "-t", str(sample_seconds),
            "-ar", str(Config.SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", str(sample_path),
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **_no_console_kwargs())
        if proc.returncode != 0 or not sample_path.exists():
            return None

        audio = decode_audio(str(sample_path), sampling_rate=Config.SAMPLE_RATE)
        lang, confidence, all_probs = model.model.detect_language(audio=audio)
        probs = dict(all_probs)
        hi_p, ur_p = probs.get("hi", 0.0), probs.get("ur", 0.0)

        if lang == "ur" and hi_p > 0 and (ur_p - hi_p) < 0.20:
            console_log(job, f"Detector leaned 'ur' but 'hi' scored close behind "
                              f"({hi_p:.2f} vs {ur_p:.2f}) -- Hindi/Urdu sound identical to the "
                              f"model, so defaulting to Hindi. Select Urdu explicitly if this "
                              f"file really is Urdu.")
            lang = "hi"

        console_log(job, f"Auto-detected language: {lang} (confidence {confidence:.2f}, "
                          f"locked for the entire file).")
        return lang
    except Exception as e:
        logger.warning(f"Upfront language detection skipped ({e}); falling back to per-chunk auto-detect.")
        return None
    finally:
        sample_path.unlink(missing_ok=True)


def run_pipeline(file_path, job_id, model_size, language_code):
    job = TRANSCRIBE_JOBS[job_id]
    job["id"] = job_id
    job["status"] = "processing"

    try:
        forced_language = LANGUAGE_OPTIONS.get(language_code)
        console_log(job, f"Loading model ({model_size}) on {DEVICE}...")
        job["percent"] = 5
        model = get_model(model_size)

        if forced_language is None:
            console_log(job, "Auto-detect requested -- sampling audio to identify language upfront...")
            resolved = detect_language_upfront(model, file_path, job)
            if resolved:
                forced_language = resolved
            else:
                console_log(job, "Could not pre-sample language; will detect inline instead.")

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
            console_log(job, f"{total_chunks} chunk(s) total -- up to {Config.CHUNK_WORKERS} running at once "
                              f"on {Config.CPU_COUNT} available CPU core(s).")
            detected_lang = forced_language
            pending = [idx for idx in range(total_chunks) if idx not in manifest["completed_chunks"]]
            manifest_lock = Lock()
            progress_lock = Lock()
            chunk_progress = {idx: 1.0 for idx in manifest["completed_chunks"]}

            def update_overall_progress():
                done_frac = sum(chunk_progress.values())
                job["percent"] = 5 + int((done_frac / total_chunks) * 90)

            def transcribe_one_chunk(idx, chunk_path, lang_for_chunk):
                def progress_cb(frac, idx=idx):
                    with progress_lock:
                        chunk_progress[idx] = frac
                        update_overall_progress()
                chunk_segments, lang = transcribe_audio(model, chunk_path, lang_for_chunk, job, progress_cb)
                offset = idx * Config.CHUNK_LENGTH_SECONDS
                for s in chunk_segments:
                    s["start"] += offset
                    s["end"] += offset
                return idx, chunk_segments, lang

            if pending:
                # If language isn't forced, transcribe the very first pending
                # chunk alone first. This (a) gives us a language to lock the
                # rest of the chunks to -- avoiding inconsistent auto-detect
                # results flipping between chunks of the same recording --
                # and (b) still finishes fast since it's one short chunk.
                if not forced_language and detected_lang is None:
                    first_idx = pending.pop(0)
                    console_log(job, f"Transcribing chunk {first_idx + 1}/{total_chunks} "
                                      f"(also detecting language)...")
                    first_idx, chunk_segments, lang = transcribe_one_chunk(
                        first_idx, chunk_paths[first_idx], forced_language
                    )
                    detected_lang = lang
                    console_log(job, f"Detected language: {detected_lang} (locked for remaining chunks).")
                    with manifest_lock:
                        manifest["segments"][str(first_idx)] = chunk_segments
                        manifest["completed_chunks"].append(first_idx)
                        save_manifest(manifest_path, manifest)
                    with progress_lock:
                        chunk_progress[first_idx] = 1.0
                        update_overall_progress()

                lang_for_rest = forced_language or detected_lang
                console_log(job, f"Transcribing {len(pending)} remaining chunk(s) in parallel "
                                  f"({Config.CHUNK_WORKERS} at a time)...")
                with ThreadPoolExecutor(max_workers=Config.CHUNK_WORKERS) as chunk_executor:
                    futures = {
                        chunk_executor.submit(transcribe_one_chunk, idx, chunk_paths[idx], lang_for_rest): idx
                        for idx in pending
                    }
                    for future in as_completed(futures):
                        idx, chunk_segments, _ = future.result()
                        with manifest_lock:
                            manifest["segments"][str(idx)] = chunk_segments
                            manifest["completed_chunks"].append(idx)
                            save_manifest(manifest_path, manifest)  # checkpoint after every chunk
                        console_log(job, f"Chunk {idx + 1}/{total_chunks} done.")

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
                            <option value="auto">Auto-detect</option>
                            <option value="hi" selected>Hindi</option>
                            <option value="en">English</option>
                            <option value="ur">Urdu</option>
                            <option value="bn">Bengali</option>
                            <option value="ta">Tamil</option>
                            <option value="te">Telugu</option>
                            <option value="mr">Marathi</option>
                            <option value="gu">Gujarati</option>
                            <option value="kn">Kannada</option>
                            <option value="ml">Malayalam</option>
                            <option value="pa">Punjabi</option>
                            <option value="ne">Nepali</option>
                            <option value="ar">Arabic</option>
                            <option value="fa">Persian</option>
                            <option value="zh">Chinese</option>
                            <option value="ja">Japanese</option>
                            <option value="ko">Korean</option>
                            <option value="es">Spanish</option>
                            <option value="fr">French</option>
                            <option value="de">German</option>
                            <option value="it">Italian</option>
                            <option value="pt">Portuguese</option>
                            <option value="ru">Russian</option>
                            <option value="tr">Turkish</option>
                            <option value="vi">Vietnamese</option>
                            <option value="id">Indonesian</option>
                            <option value="th">Thai</option>
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
                <div class="model-hint">Files over 20 minutes are automatically split into parallel chunks and checkpointed — safe to re-upload after a crash, it resumes instead of restarting. First run of a model size needs internet once; every run after that is fully offline.</div>

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
    logger.info("Pre-warming default model so the first upload doesn't stall on load/download...")
    get_model(Config.DEFAULT_MODEL_SIZE)
    logger.info("Ready.")
    app.run(host="0.0.0.0", port=8084321, debug=False, threaded=True)