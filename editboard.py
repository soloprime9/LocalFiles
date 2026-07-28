import os
import sys
import re
import math
import uuid
import json
import asyncio
import threading
import subprocess
import tempfile
import shutil
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from werkzeug.utils import secure_filename

# Third-party imports handled gracefully
try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

try:
    import edge_tts
except ImportError:
    edge_tts = None

# Initialize Flask App
app = Flask(__name__)

# Configure storage directories
BASE_DIR = os.getcwd()
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
EXPORT_FOLDER = os.path.join(BASE_DIR, "exports")
TTS_FOLDER = os.path.join(BASE_DIR, "tts_audio")

for folder in [UPLOAD_FOLDER, EXPORT_FOLDER, TTS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Global compilation task statuses
export_tasks = {}
tasks_lock = threading.Lock()

# Define allowed upload file types
ALLOWED_EXTENSIONS = {
    'video': {'mp4', 'mkv', 'webm', 'mov', 'avi'},
    'image': {'png', 'jpg', 'jpeg', 'webp', 'gif'},
    'audio': {'mp3', 'wav', 'ogg', 'm4a'}
}

def get_file_type(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    for ftype, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return ftype
    return None

# ================= TTS SPEECH GENERATORS =================

async def generate_edge_tts(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def render_text_to_speech(text, engine, voice_or_lang, output_path):
    """
    Renders text to speech using either Microsoft Edge-TTS or Google gTTS.
    """
    if engine == "edge":
        if edge_tts is None:
            raise ImportError("Microsoft Edge TTS library is not installed.")
        # Run async function in synchronous wrapper
        asyncio.run(generate_edge_tts(text, voice_or_lang, output_path))
    else:
        # Fallback to Google TTS
        if gTTS is None:
            raise ImportError("Google gTTS library is not installed.")
        tts = gTTS(text=text, lang=voice_or_lang)
        tts.save(output_path)

# ================= YT-DLP DOWNLOADER =================

def extract_media_from_url(url, media_type="video"):
    """
    Downloads media streams from video webpages (e.g. YouTube) using yt-dlp.
    """
    if yt_dlp is None:
        raise ImportError("yt-dlp library is not available.")

    unique_id = uuid.uuid4().hex[:6]
    out_tmpl = os.path.join(UPLOAD_FOLDER, f"yt_media_{unique_id}_%(title)s.%(ext)s")

    ydl_opts = {
        'outtmpl': out_tmpl,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'quiet': True,
        'no_warnings': True,
    }

    if media_type == "audio":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        ydl_opts.update({
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
    'merge_output_format': 'mp4',
})

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if not info:
            raise ValueError("Could not extract media info or download the URL stream.")
        
        # Determine the exact output file
        if '_type' in info and info['_type'] == 'playlist':
            entries = info.get('entries', [])
            if not entries:
                raise ValueError("Playlist contains no downloadable entries.")
            info = entries[0]
            
        filename = ydl.prepare_filename(info)
        
        if media_type == "audio":
            # Postprocessor converts file to mp3
            filename = os.path.splitext(filename)[0] + ".mp3"
        else:
            # Confirm standard mp4 extension or look for actual file
            if not os.path.exists(filename):
                base, _ = os.path.splitext(filename)
                for ext in ['mp4', 'mkv', 'webm']:
                    if os.path.exists(base + "." + ext):
                        filename = base + "." + ext
                        break

        # Check if file was saved
        if not os.path.exists(filename):
            # Fallback search of latest created file in uploads matching ID
            files = os.listdir(UPLOAD_FOLDER)
            matched = [f for f in files if f"yt_media_{unique_id}" in f]
            if matched:
                filename = os.path.join(UPLOAD_FOLDER, matched[0])
            else:
                raise FileNotFoundError("Downloaded file could not be verified on disk.")

        return os.path.basename(filename)

# ================= VIDEO EDITING COMPILATION WORKER =================

def compile_video_background(task_id, timeline, audio_track, settings):
    """
    Processes the timeline sequence and compiles the final video.
    Supports real-time rendering, image and video joining, audio syncing, loops, and custom resolution layouts.
    Uses an extremely robust, sequential, high-speed pure FFmpeg rendering pipeline.
    """
    try:
        def update_progress(percent, stage, file_url=None, err=None):
            with tasks_lock:
                export_tasks[task_id] = {
                    "progress": percent,
                    "stage": stage,
                    "download_url": file_url,
                    "error": err
                }

        update_progress(5, "Analyzing project sequence structure...")

        # Dynamically detect ffmpeg executable path (especially critical for Windows or custom environments)
        ffmpeg_bin = "ffmpeg"
        try:
            if shutil.which("ffmpeg"):
                ffmpeg_bin = shutil.which("ffmpeg")
            else:
                # Attempt to use imageio_ffmpeg (which moviepy installs)
                import imageio_ffmpeg
                img_ff = imageio_ffmpeg.get_ffmpeg_exe()
                if img_ff and os.path.exists(img_ff):
                    ffmpeg_bin = img_ff
        except Exception as e:
            print(f"[FFMPEG SEARCH WARN] Failed to find via imageio: {e}")

        # Fallback to moviepy's ffmpeg if still default
        if ffmpeg_bin == "ffmpeg":
            try:
                from moviepy.config import get_setting
                mv_ff = get_setting("FFMPEG_BINARY")
                if mv_ff and os.path.exists(mv_ff):
                    ffmpeg_bin = mv_ff
            except Exception:
                pass

        print(f"[COMPILER INFO] Resolved ffmpeg executable path: {ffmpeg_bin}")

        def check_has_audio(filepath):
            try:
                cmd = [ffmpeg_bin, "-i", filepath]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="ignore")
                return "Audio:" in res.stderr
            except Exception:
                return False

        def get_audio_duration(filepath):
            try:
                cmd = [ffmpeg_bin, "-i", filepath]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="ignore")
                import re
                match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
                if match:
                    hours = int(match.group(1))
                    minutes = int(match.group(2))
                    seconds = float(match.group(3))
                    return hours * 3600 + minutes * 60 + seconds
            except Exception as e:
                print(f"[COMPILER INFO] Failed to parse duration with ffmpeg: {e}")
            return 5.0

        # Setup dimension resolutions
        is_portrait = settings.get("format") == "9:16"
        quality = settings.get("quality", "1080p")

        if quality == "4k":
            width, height = (2160, 3840) if is_portrait else (3840, 2160)
        elif quality == "720p":
            width, height = (720, 1280) if is_portrait else (1280, 720)
        else: # 1080p Default
            width, height = (1080, 1920) if is_portrait else (1920, 1080)

        # Resolve Audio Stream
        audio_file = None
        loop_audio = settings.get("loop_audio", False)
        match_audio_length = settings.get("match_audio_length", False)

        if audio_track and audio_track.get("filename"):
            folder_src = TTS_FOLDER if audio_track.get("source") == "tts" else UPLOAD_FOLDER
            audio_file = os.path.join(folder_src, audio_track["filename"])
            if not os.path.exists(audio_file):
                audio_file = None

        output_filename = f"compiled_video_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join(EXPORT_FOLDER, output_filename)

        # Create temporary directory for clip rendering
        temp_dir = os.path.join(EXPORT_FOLDER, f"temp_{uuid.uuid4().hex[:8]}")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            temp_clips = []
            total_items = len(timeline)
            
            for idx, item in enumerate(timeline):
                filename = item.get("filename")
                ftype = item.get("type")
                duration = float(item.get("duration", 5.0))
                effect = item.get("effect", "none") # e.g. "none", "fade", "rotate"

                media_path = os.path.join(UPLOAD_FOLDER, filename)
                if not os.path.exists(media_path):
                    continue

                update_progress(10 + int((idx / total_items) * 50), f"Encoding clip {idx+1}/{total_items}: {filename}...")

                clip_output = os.path.join(temp_dir, f"clip_{idx:04d}.mp4")

                # Setup FFmpeg command for this specific clip
                # We scale and pad perfectly to match width & height, enforce 30fps, and force stereo 44100Hz audio.
                if ftype == "image":
                    # Image input: loop it, add null audio
                    cmd = [
                        ffmpeg_bin, "-y",
                        "-loop", "1", "-t", str(duration), "-i", media_path,
                        "-f", "lavfi", "-i", "anullsrc=cl=stereo:r=44100",
                    ]
                    # Filter: scale to decrease, pad, set sar, and set fade if requested
                    v_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
                    if effect == "fade":
                        v_filter += f",fade=in:st=0:d=0.5,fade=out:st={duration-0.5}:d=0.5"
                    elif effect == "rotate":
                        v_filter += ",rotate=PI"

                    cmd += [
                        "-filter_complex", f"[0:v]{v_filter}[v]",
                        "-map", "[v]", "-map", "1:a",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                        "-c:a", "aac", "-shortest",
                        clip_output
                    ]
                else: # video
                    # Check if video has audio stream
                    has_aud = check_has_audio(media_path)

                    v_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
                    if effect == "fade":
                        v_filter += f",fade=in:st=0:d=0.5,fade=out:st={duration-0.5}:d=0.5"
                    elif effect == "rotate":
                        v_filter += ",rotate=PI"

                    if has_aud:
                        # Video has audio: scale video, standardise audio
                        cmd = [
                            ffmpeg_bin, "-y",
                            "-ss", "0", "-t", str(duration), "-i", media_path,
                            "-filter_complex", f"[0:v]{v_filter}[v];[0:a]aformat=sample_rates=44100:channel_layouts=stereo[a]",
                            "-map", "[v]", "-map", "[a]",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                            "-c:a", "aac",
                            clip_output
                        ]
                    else:
                        # Video has NO audio: add null audio
                        cmd = [
                            ffmpeg_bin, "-y",
                            "-ss", "0", "-t", str(duration), "-i", media_path,
                            "-f", "lavfi", "-i", "anullsrc=cl=stereo:r=44100",
                            "-filter_complex", f"[0:v]{v_filter}[v]",
                            "-map", "[v]", "-map", "1:a",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                            "-c:a", "aac", "-shortest",
                            clip_output
                        ]

                # Run process
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if proc.returncode == 0 and os.path.exists(clip_output):
                    temp_clips.append(clip_output)
                else:
                    print(f"Clip rendering failed for {filename}: {proc.stderr}")
                    # Fallback copy if ffmpeg transcode fails
                    shutil.copy(media_path, clip_output)
                    temp_clips.append(clip_output)

            if not temp_clips:
                raise ValueError("No clips were successfully rendered.")

            # 2. Concat all rendered clips
            update_progress(70, "Assembling video sequence tracks...")
            concat_list_file = os.path.join(temp_dir, "concat.txt")
            with open(concat_list_file, "w") as f:
                for clip in temp_clips:
                    f.write(f"file '{clip}'\n")

            temp_concat_video = os.path.join(temp_dir, "concat_output.mp4")
            concat_cmd = [
                ffmpeg_bin, "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_list_file,
                "-c", "copy",
                temp_concat_video
            ]
            proc = subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode != 0 or not os.path.exists(temp_concat_video):
                raise RuntimeError(f"Video assembly failed: {proc.stderr}")

            # 3. Add background soundtrack or handle duration constraints
            update_progress(85, "Mixing audio tracks and finishing render...")
            
            # Determine total video duration
            video_duration = sum(float(item.get("duration", 5.0)) for item in timeline)

            if audio_file:
                # We have a soundtrack! Let's mix it
                # Get soundtrack duration
                audio_duration = get_audio_duration(audio_file)

                if match_audio_length:
                    # Loop video sequence or cut video to fit audio length
                    if video_duration < audio_duration:
                        # Video is shorter, loop the video to match audio
                        num_loops = int(math.ceil(audio_duration / video_duration))
                        loop_list = os.path.join(temp_dir, "loop_list.txt")
                        with open(loop_list, "w") as f:
                            for _ in range(num_loops):
                                f.write(f"file '{temp_concat_video}'\n")
                        
                        temp_looped_video = os.path.join(temp_dir, "looped_video.mp4")
                        loop_cmd = [ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", loop_list, "-c", "copy", temp_looped_video]
                        subprocess.run(loop_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        temp_concat_video = temp_looped_video

                    # Crop video to exact audio length, mix audio (FIXED VOLUME)
                    mix_cmd = [
                        ffmpeg_bin, "-y",
                        "-t", str(audio_duration), "-i", temp_concat_video,
                        "-i", audio_file,
                        "-filter_complex", "[1:a]volume=1.0[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[a]",
                        "-map", "0:v", "-map", "[a]",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                        "-c:a", "aac",
                        output_path
                    ]
                else:
                    # Video duration is master
                    if loop_audio and audio_duration < video_duration:
                        # Loop soundtrack to fit video duration (FIXED VOLUME)
                        mix_cmd = [
                            ffmpeg_bin, "-y",
                            "-i", temp_concat_video,
                            "-stream_loop", "-1", "-i", audio_file,
                            "-filter_complex", f"[1:a]volume=1.0,atrim=0:{video_duration}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[a]",
                            "-map", "0:v", "-map", "[a]",
                            "-c:v", "copy", "-c:a", "aac", "-t", str(video_duration),
                            output_path
                        ]
                    else:
                        # Trim soundtrack to fit video (FIXED VOLUME)
                        mix_cmd = [
                            ffmpeg_bin, "-y",
                            "-i", temp_concat_video,
                            "-i", audio_file,
                            "-filter_complex", f"[1:a]volume=1.0,atrim=0:{video_duration}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[a]",
                            "-map", "0:v", "-map", "[a]",
                            "-c:v", "copy", "-c:a", "aac", "-t", str(video_duration),
                            output_path
                        ]
            else:
                # No soundtrack, just output the concatenated clips!
                # Copy directly since it has identical formats
                mix_cmd = [
                    ffmpeg_bin, "-y",
                    "-i", temp_concat_video,
                    "-c", "copy",
                    output_path
                ]

            subprocess.run(mix_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
                raise RuntimeError("Failed to output final mixed video file.")

            update_progress(100, "Completed", file_url=f"/api/files/exports/{output_filename}")

        finally:
            # Clean up the temporary clip directory
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    except Exception as general_err:
        print(f"[COMPILER CRITICAL ERROR] {general_err}")
        update_progress(100, "Failed", err=f"Rendering Pipeline Crash: {str(general_err)}")

# ================= FLASK CONTROLLER ENDPOINTS =================

@app.route('/')
def index_dashboard():
    """
    Renders the magnificent high-performance video dashboard from the template file.
    """
    try:
        with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
            template_content = f.read()
        return render_template_string(template_content)
    except Exception as e:
        return f"Dashboard template loading failed: {str(e)}", 500

@app.route('/api/upload', methods=['POST'])
def api_upload_media():
    """
    Endpoint to receive uploaded images, videos, or audio soundtracks.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    ftype = get_file_type(file.filename)
    if not ftype:
        return jsonify({"error": "Unsupported file format. Upload videos, images, or audios."}), 400

    filename = secure_filename(file.filename)
    # Ensure unique file naming
    filename_uuid = f"{uuid.uuid4().hex[:6]}_{filename}"
    save_path = os.path.join(UPLOAD_FOLDER, filename_uuid)
    file.save(save_path)

    return jsonify({
        "success": True,
        "filename": filename_uuid,
        "original_name": filename,
        "type": ftype,
        "url": f"/api/files/uploads/{filename_uuid}"
    })

@app.route('/api/yt-fetch', methods=['POST'])
def api_yt_fetch():
    """
    Fetches videos/soundtracks from YouTube URLs using yt-dlp.
    """
    data = request.get_json() or {}
    url = data.get("url")
    media_type = data.get("type", "video") # video or audio

    if not url:
        return jsonify({"error": "Target web URL is required."}), 400

    if yt_dlp is None:
        return jsonify({"error": "yt-dlp is not loaded on server."}), 500

    try:
        saved_filename = extract_media_from_url(url, media_type)
        return jsonify({
            "success": True,
            "filename": saved_filename,
            "original_name": saved_filename,
            "type": media_type,
            "url": f"/api/files/uploads/{saved_filename}"
        })
    except Exception as e:
        return jsonify({"error": f"Failed to fetch stream: {str(e)}"}), 500

@app.route('/api/tts', methods=['POST'])
def api_tts_generator():
    """
    Generates premium speech tracks via gTTS or Microsoft Edge-TTS.
    """
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    engine = data.get("engine", "edge") # edge or gtts
    voice_or_lang = data.get("voice_or_lang", "en-US-AriaNeural")

    if not text:
        return jsonify({"error": "Speech transcription text is empty."}), 400

    unique_id = uuid.uuid4().hex[:8]
    output_filename = f"tts_{unique_id}.mp3"
    output_path = os.path.join(TTS_FOLDER, output_filename)

    try:
        render_text_to_speech(text, engine, voice_or_lang, output_path)
        return jsonify({
            "success": True,
            "filename": output_filename,
            "text": text,
            "engine": engine,
            "voice": voice_or_lang,
            "url": f"/api/files/tts_audio/{output_filename}"
        })
    except Exception as e:
        # If Edge TTS fails, attempt immediate gTTS English fallback
        try:
            render_text_to_speech(text, "gtts", "en", output_path)
            return jsonify({
                "success": True,
                "filename": output_filename,
                "text": text,
                "engine": "gtts (Fallback)",
                "voice": "en",
                "url": f"/api/files/tts_audio/{output_filename}"
            })
        except Exception as fallback_err:
            return jsonify({"error": f"Speech Synthesis Failed: {str(e)}. Fallback failed: {str(fallback_err)}"}), 500

@app.route('/api/media', methods=['GET'])
def api_list_media():
    """
    Retrieves lists of available uploads, speech audio, and exported items.
    """
    uploads = []
    for f in os.listdir(UPLOAD_FOLDER):
        ftype = get_file_type(f)
        if ftype:
            uploads.append({
                "filename": f,
                "type": ftype,
                "url": f"/api/files/uploads/{f}"
            })

    tts_items = []
    for f in os.listdir(TTS_FOLDER):
        if f.endswith('.mp3'):
            tts_items.append({
                "filename": f,
                "type": "audio",
                "url": f"/api/files/tts_audio/{f}"
            })

    exports = []
    for f in os.listdir(EXPORT_FOLDER):
        if f.endswith('.mp4'):
            exports.append({
                "filename": f,
                "type": "video",
                "url": f"/api/files/exports/{f}"
            })

    return jsonify({
        "uploads": uploads,
        "tts": tts_items,
        "exports": exports
    })

@app.route('/api/media/delete', methods=['POST'])
def api_delete_media():
    data = request.get_json() or {}
    filename = data.get("filename")
    folder = data.get("folder") # uploads, tts_audio, exports

    if not filename or not folder:
        return jsonify({"error": "Missing params"}), 400

    target_dir = {
        "uploads": UPLOAD_FOLDER,
        "tts_audio": TTS_FOLDER,
        "exports": EXPORT_FOLDER
    }.get(folder)

    if not target_dir:
        return jsonify({"error": "Invalid folder"}), 400

    target_file = os.path.join(target_dir, secure_filename(filename))
    if os.path.exists(target_file):
        os.remove(target_file)
        return jsonify({"success": True})
    return jsonify({"error": "File not found"}), 404

@app.route('/api/export', methods=['POST'])
def api_schedule_export():
    """
    Schedules background rendering pipeline.
    """
    data = request.get_json() or {}
    timeline = data.get("timeline", [])
    audio_track = data.get("audio_track", None)
    settings = data.get("settings", {})

    if not timeline:
        return jsonify({"error": "Editing timeline sequence is empty. Add elements first."}), 400

    task_id = uuid.uuid4().hex[:12]
    with tasks_lock:
        export_tasks[task_id] = {
            "progress": 0,
            "stage": "Scheduling render thread...",
            "download_url": None,
            "error": None
        }

    # Spawn thread
    thread = threading.Thread(
        target=compile_video_background,
        args=(task_id, timeline, audio_track, settings),
        daemon=True
    )
    thread.start()

    return jsonify({
        "success": True,
        "task_id": task_id
    })

@app.route('/api/export/status/<task_id>', methods=['GET'])
def api_export_status(task_id):
    with tasks_lock:
        task = export_tasks.get(task_id)
    if not task:
        return jsonify({"error": "Rendering task not found."}), 404
    return jsonify(task)

@app.route('/api/files/<folder>/<filename>', methods=['GET'])
def api_serve_files(folder, filename):
    """
    Serves static files dynamically from media folders.
    """
    target_dir = {
        "uploads": UPLOAD_FOLDER,
        "exports": EXPORT_FOLDER,
        "tts_audio": TTS_FOLDER
    }.get(folder)

    if not target_dir or not os.path.exists(target_dir):
        return "Directory not found", 404

    return send_from_directory(target_dir, filename)

# ================= DASHBOARD UI HTML TEMPLATE =================

HTML_DASHBOARD = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TTS & Video Editor Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Space Grotesk', sans-serif;
            background-color: #030712;
            color: #f3f4f6;
        }
        .mono {
            font-family: 'JetBrains Mono', monospace;
        }
        /* Custom scrollbars */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #030712;
        }
        ::-webkit-scrollbar-thumb {
            background: #1f2937;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #374151;
        }
    </style>
</head>
<body class="min-h-screen py-6 px-4 sm:px-6 lg:px-8">
    <div class="max-w-7xl mx-auto">
        <!-- Header -->
        <header class="flex flex-col md:flex-row justify-between items-center mb-6 pb-5 border-b border-gray-800 gap-4">
            <div>
                <h1 class="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-violet-400 via-pink-500 to-rose-500 bg-clip-text text-transparent">
                    TTS & HD Video Editor Dashboard
                </h1>
                <p class="mt-1 text-gray-400 text-xs">
                    Synthesize life-like voices, import links, arrange media, sync audios, loop overlays, and export up to 4K.
                </p>
            </div>
            <div class="flex items-center gap-2">
                <span class="px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-400 text-[10px] font-bold tracking-wider uppercase animate-pulse">
                    Ffmpeg Renderer Active
                </span>
                <span class="px-2.5 py-1 rounded-full bg-violet-500/10 text-violet-400 text-[10px] font-bold tracking-wider uppercase">
                    Multithreading Enabled
                </span>
            </div>
        </header>

        <!-- Main Dashboard Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            <!-- COLUMN 1: Speech Composer & TTS Generator (4 Cols) -->
            <div class="lg:col-span-4 space-y-6">
                <!-- TTS Generation Card -->
                <div class="bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-xl">
                    <h2 class="text-lg font-bold mb-3 flex items-center gap-2 text-violet-400">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"></path></svg>
                        TTS Speech Synthesizer
                    </h2>
                    
                    <div class="space-y-4">
                        <div>
                            <label class="block text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">TTS Voice Engine</label>
                            <select id="ttsEngine" onchange="toggleEngineVoices()" class="w-full bg-gray-950 border border-gray-800 rounded-xl px-3 py-2 text-xs text-gray-100 focus:outline-none focus:ring-1 focus:ring-violet-500 transition">
                                <option value="edge" selected>Microsoft Edge Premium (Neural)</option>
                                <option value="gtts">Google Standard TTS</option>
                            </select>
                        </div>

                        <div>
                            <label class="block text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Target Voice & Gender</label>
                            <!-- Microsoft Neural options -->
                            <select id="ttsVoiceEdge" class="w-full bg-gray-950 border border-gray-800 rounded-xl px-3 py-2 text-xs text-gray-100 focus:outline-none focus:ring-1 focus:ring-violet-500 transition">
                                <!-- English US -->
                                <option value="en-US-AriaNeural" selected>🇺🇸 English (US) - Female (Aria) - Premium Realistic</option>
                                <option value="en-US-JennyNeural">🇺🇸 English (US) - Female (Jenny) - Warm Conversational</option>
                                <option value="en-US-EmmaNeural">🇺🇸 English (US) - Female (Emma) - Narrative</option>
                                <option value="en-US-MichelleNeural">🇺🇸 English (US) - Female (Michelle) - Professional</option>
                                <option value="en-US-GuyNeural">🇺🇸 English (US) - Male (Guy)</option>
                                <option value="en-US-BrianNeural">🇺🇸 English (US) - Male (Brian)</option>
                                <option value="en-US-SteffanNeural">🇺🇸 English (US) - Male (Steffan)</option>
                                <!-- English UK -->
                                <option value="en-GB-SoniaNeural">🇬🇧 English (UK) - Female (Sonia) - Realism</option>
                                <option value="en-GB-LibbyNeural">🇬🇧 English (UK) - Female (Libby)</option>
                                <option value="en-GB-RyanNeural">🇬🇧 English (UK) - Male (Ryan)</option>
                                <option value="en-GB-ThomasNeural">🇬🇧 English (UK) - Male (Thomas)</option>
                                <!-- English India / India Languages -->
                                <option value="en-IN-NeerjaNeural">🇮🇳 English (India) - Female (Neerja) - Premium Realistic</option>
                                <option value="en-IN-AaravNeural">🇮🇳 English (India) - Male (Aarav)</option>
                                <option value="en-IN-PrabhatNeural">🇮🇳 English (India) - Male (Prabhat)</option>
                                <option value="hi-IN-MadhuramNeural">🇮🇳 Hindi (India) - Female (Madhuram) - Premium Realistic</option>
                                <option value="hi-IN-KaranNeural">🇮🇳 Hindi (India) - Male (Karan)</option>
                                <option value="hi-IN-SwararaajNeural">🇮🇳 Hindi (India) - Male (Swararaaj)</option>
                                <!-- Spanish -->
                                <option value="es-ES-ElviraNeural">🇪🇸 Spanish (Spain) - Female (Elvira)</option>
                                <option value="es-MX-DaliaNeural">🇲🇽 Spanish (Mexico) - Female (Dalia)</option>
                                <option value="es-ES-AlvaroNeural">🇪🇸 Spanish (Spain) - Male (Alvaro)</option>
                                <!-- French -->
                                <option value="fr-FR-DeniseNeural">🇫🇷 French (France) - Female (Denise)</option>
                                <option value="fr-FR-EloiseNeural">🇫🇷 French (France) - Female (Eloise)</option>
                                <option value="fr-FR-HenriNeural">🇫🇷 French (France) - Male (Henri)</option>
                                <!-- German -->
                                <option value="de-DE-KatjaNeural">🇩🇪 German (Germany) - Female (Katja)</option>
                                <option value="de-DE-ConradNeural">🇩🇪 German (Germany) - Male (Conrad)</option>
                                <!-- Urdu/Arabic/Other Asian -->
                                <option value="ur-PK-UzmaNeural">🇵🇰 Urdu (Pakistan) - Female (Uzma) - Premium</option>
                                <option value="ur-PK-AsadNeural">🇵🇰 Urdu (Pakistan) - Male (Asad)</option>
                            </select>
                            <!-- Google TTS fallback option -->
                            <select id="ttsVoiceGtts" class="hidden w-full bg-gray-950 border border-gray-800 rounded-xl px-3 py-2 text-xs text-gray-100 focus:outline-none focus:ring-1 focus:ring-violet-500 transition">
                                <option value="en">🇺🇸 English (US) - Female (Standard)</option>
                                <option value="en-uk">🇬🇧 English (UK) - Female (Standard)</option>
                                <option value="en-au">🇦🇺 English (Australia) - Female</option>
                                <option value="en-in">🇮🇳 English (India) - Female</option>
                                <option value="hi">🇮🇳 Hindi (India) - Female</option>
                                <option value="es">🇪🇸 Spanish (Spain) - Female</option>
                                <option value="fr">🇫🇷 French (France) - Female</option>
                                <option value="de">🇩🇪 German (Germany) - Female</option>
                                <option value="ur">🇵🇰 Urdu (Pakistan) - Female</option>
                            </select>
                        </div>

                        <div>
                            <label class="block text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Enter Speech Script</label>
                            <textarea id="ttsText" rows="3" placeholder="Paste or type script..." class="w-full bg-gray-950 border border-gray-800 rounded-xl p-3 text-xs text-gray-100 placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-violet-500 transition">This is an automated 4K high quality voice over track generated perfectly inside the editor.</textarea>
                        </div>

                        <button id="btnGenerateTts" onclick="generateSpeech()" class="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-semibold py-2.5 px-4 rounded-xl text-xs active:scale-[0.98] transition flex items-center justify-center gap-2">
                            <span>Render Audio Speech</span>
                            <div id="ttsSpinner" class="hidden w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                        </button>
                    </div>
                </div>

                <!-- Generated Soundtracks List -->
                <div class="bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-xl">
                    <h2 class="text-sm font-bold mb-3 text-gray-300 flex items-center justify-between">
                        <span>Speech Soundtracks</span>
                        <span id="ttsCount" class="text-[10px] px-2 py-0.5 bg-gray-950 rounded text-gray-400 font-mono">0</span>
                    </h2>
                    <div id="ttsList" class="space-y-3 max-h-[220px] overflow-y-auto pr-1">
                        <!-- empty state -->
                        <div class="text-center py-6 text-xs text-gray-600">No tracks synthesized yet.</div>
                    </div>
                </div>
            </div>

            <!-- COLUMN 2: Media Asset Bank & URL Fetcher (4 Cols) -->
            <div class="lg:col-span-4 space-y-6">
                <!-- Local Media Import -->
                <div class="bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-xl">
                    <h2 class="text-lg font-bold mb-3 flex items-center gap-2 text-rose-400">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                        Media Asset Bank
                    </h2>

                    <!-- Drag & Drop Uploader -->
                    <div id="dropZone" class="border-2 border-dashed border-gray-800 hover:border-rose-500/50 rounded-2xl p-6 text-center transition cursor-pointer bg-gray-950/40 relative">
                        <input type="file" id="fileInput" class="hidden" accept="image/*,video/*,audio/*" onchange="handleFileSelect(event)">
                        <svg class="w-8 h-8 text-gray-500 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
                        <p class="text-xs text-gray-300 font-medium">Drag & Drop PC Files</p>
                        <p class="text-[10px] text-gray-500 mt-1">Videos, Images, or Audio sound clips</p>
                        <div id="uploadSpinner" class="hidden absolute inset-0 bg-gray-950/80 rounded-2xl flex items-center justify-center flex-col gap-2">
                            <div class="w-6 h-6 border-2 border-rose-500/30 border-t-rose-500 rounded-full animate-spin"></div>
                            <span class="text-[10px] text-rose-400 font-semibold">Uploading PC file...</span>
                        </div>
                    </div>

                    <!-- YT URL Fetcher -->
                    <div class="mt-4 pt-4 border-t border-gray-800">
                        <label class="block text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Import from Youtube/Web (yt-dlp)</label>
                        <div class="flex gap-2">
                            <input type="url" id="ytUrl" placeholder="https://www.youtube.com/watch?v=..." class="flex-1 bg-gray-950 border border-gray-800 rounded-xl px-3 py-2 text-xs text-gray-100 placeholder-gray-700 focus:outline-none focus:ring-1 focus:ring-rose-500">
                            <button onclick="fetchYtUrl()" class="px-3 py-2 bg-gray-800 hover:bg-gray-700 text-xs text-gray-200 rounded-xl border border-gray-700 active:scale-95 transition flex items-center gap-1">
                                <span>Fetch</span>
                                <div id="ytSpinner" class="hidden w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Asset Inventory Gallery -->
                <div class="bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-xl">
                    <div class="flex justify-between items-center mb-3">
                        <h2 class="text-sm font-bold text-gray-300">Workspace Library</h2>
                        <!-- Tabs -->
                        <div class="flex gap-1 bg-gray-950 p-1 rounded-lg border border-gray-800">
                            <button id="tabAll" onclick="filterGallery('all')" class="px-2 py-0.5 text-[9px] font-semibold bg-gray-900 text-rose-400 rounded">All</button>
                            <button id="tabVideo" onclick="filterGallery('video')" class="px-2 py-0.5 text-[9px] font-semibold text-gray-400 rounded">Video</button>
                            <button id="tabImage" onclick="filterGallery('image')" class="px-2 py-0.5 text-[9px] font-semibold text-gray-400 rounded">Image</button>
                            <button id="tabAudio" onclick="filterGallery('audio')" class="px-2 py-0.5 text-[9px] font-semibold text-gray-400 rounded">Audio</button>
                        </div>
                    </div>
                    <div id="galleryList" class="space-y-3 max-h-[290px] overflow-y-auto pr-1">
                        <!-- empty state -->
                        <div class="text-center py-6 text-xs text-gray-600">No media assets in workspace library.</div>
                    </div>
                </div>
            </div>

            <!-- COLUMN 3: Visual Timeline, Config & Rendering Progress (4 Cols) -->
            <div class="lg:col-span-4 space-y-6">
                <!-- Live Theater & Playback Sequencer -->
                <div id="previewTheater" class="bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-xl space-y-4">
                    <h2 class="text-sm font-bold flex items-center gap-2 text-violet-400">
                        <svg class="w-4 h-4 text-rose-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                        Live Theater & Playback Sequencer
                    </h2>
                    
                    <!-- Viewport Container -->
                    <div id="viewportContainer" class="relative aspect-video w-full bg-black rounded-xl overflow-hidden border border-gray-950 flex items-center justify-center">
                        <!-- 1. Video Element -->
                        <video id="viewportVideo" class="hidden w-full h-full object-contain" controls></video>
                        <!-- 2. Image Element -->
                        <img id="viewportImage" class="hidden w-full h-full object-contain" />
                        <!-- 3. Audio / Waveform Visualizer -->
                        <div id="viewportAudioVisualizer" class="hidden flex flex-col items-center justify-center space-y-3">
                            <svg class="w-10 h-10 text-emerald-400 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"></path></svg>
                            <div class="flex items-center gap-1 justify-center h-6">
                                <span class="w-1 h-3 bg-emerald-500 rounded-full animate-bounce" style="animation-delay: 0s"></span>
                                <span class="w-1 h-5 bg-emerald-400 rounded-full animate-bounce" style="animation-delay: 0.15s"></span>
                                <span class="w-1 h-4 bg-emerald-500 rounded-full animate-bounce" style="animation-delay: 0.3s"></span>
                                <span class="w-1 h-6 bg-emerald-400 rounded-full animate-bounce" style="animation-delay: 0.45s"></span>
                                <span class="w-1 h-2 bg-emerald-500 rounded-full animate-bounce" style="animation-delay: 0.6s"></span>
                            </div>
                            <span class="text-[10px] text-gray-400 font-mono" id="audioPreviewName">Audio Previewing...</span>
                        </div>
                        <!-- 4. Default / Placeholder -->
                        <div id="viewportPlaceholder" class="flex flex-col items-center justify-center text-center p-4">
                            <svg class="w-10 h-10 text-gray-750 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                            <span class="text-[10px] text-gray-500">Select an asset or click Play Sequence below</span>
                        </div>
                        
                        <!-- Live sequence visual overlay metadata -->
                        <div id="viewportSequenceOverlay" class="hidden absolute top-2 left-2 bg-black/90 px-2 py-0.5 rounded border border-gray-800 text-[9px] font-mono text-gray-200 flex items-center gap-1.5">
                            <span class="w-1.5 h-1.5 bg-rose-500 rounded-full animate-ping"></span>
                            <span>LIVE SEQUENCER: CLIP <span id="seqClipIndex">1</span>/<span id="seqClipTotal">5</span></span>
                        </div>
                    </div>
                    
                    <!-- Controls Bar -->
                    <div class="flex items-center justify-between gap-3 text-xs pt-1">
                        <div class="flex items-center gap-1.5">
                            <button id="btnPlaySeq" onclick="playLiveSequence()" class="px-2.5 py-1.5 bg-rose-600 hover:bg-rose-500 text-white font-bold rounded-lg transition flex items-center gap-1 text-[10px] active:scale-[0.98]">
                                <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd"></path></svg>
                                <span>Play Sequence</span>
                            </button>
                            <button id="btnStopSeq" onclick="stopLiveSequence()" class="px-2.5 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 font-bold rounded-lg transition flex items-center gap-1 text-[10px] active:scale-[0.98]">
                                <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"></path></svg>
                                <span>Stop</span>
                            </button>
                        </div>
                        <div class="text-[9px] text-gray-500 font-mono flex items-center gap-2">
                            <span class="truncate max-w-[120px]" id="seqDurationVal">0.0s</span>
                        </div>
                    </div>
                    
                    <!-- Hidden element to play the Master soundtrack in client-side preview -->
                    <audio id="timelinePreviewAudio" class="hidden"></audio>
                </div>

                <!-- Video Timeline Sequencer -->
                <div class="bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-xl">
                    <div class="flex justify-between items-center mb-3 border-b border-gray-800 pb-2">
                        <h2 class="text-lg font-bold flex items-center gap-2 text-emerald-400">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                            Timeline Track
                        </h2>
                        <button onclick="clearTimeline()" class="text-[10px] text-gray-500 hover:text-red-400 transition">Clear All</button>
                    </div>

                    <!-- Master Audio selection -->
                    <div class="mb-4 bg-gray-950 p-3 rounded-xl border border-gray-850">
                        <label class="block text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1 flex justify-between items-center">
                            <span>Master Audio Soundtrack</span>
                            <span class="text-[9px] text-violet-400">Sync Audio</span>
                        </label>
                        <select id="masterAudio" class="w-full bg-gray-900 border border-gray-800 rounded-lg px-2 py-1.5 text-xs text-gray-200 focus:outline-none">
                            <option value="">-- No Soundtrack (Silent) --</option>
                        </select>
                        <div class="mt-2 flex items-center justify-between text-[10px] text-gray-500">
                            <label class="flex items-center gap-1.5 cursor-pointer">
                                <input type="checkbox" id="loopAudio" class="rounded border-gray-800 bg-gray-900 text-emerald-600 focus:ring-0">
                                Loop Audio Track
                            </label>
                            <label class="flex items-center gap-1.5 cursor-pointer">
                                <input type="checkbox" id="matchAudio" class="rounded border-gray-800 bg-gray-900 text-emerald-600 focus:ring-0">
                                Match Video Length to Audio
                            </label>
                        </div>
                    </div>

                    <!-- Timeline Item list -->
                    <div id="timelineList" class="space-y-2 max-h-[220px] overflow-y-auto pr-1 mb-4">
                        <!-- Empty timeline state -->
                        <div class="text-center py-8 text-xs text-gray-600 border border-dashed border-gray-800 rounded-xl">
                            Drag or click assets in your library to add them to the video composition timeline!
                        </div>
                    </div>

                    <!-- Video Dimensions and Render Quality -->
                    <div class="grid grid-cols-2 gap-3 pt-3 border-t border-gray-800 text-xs">
                        <div>
                            <label class="block text-[9px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Canvas Aspect Ratio</label>
                            <select id="canvasFormat" class="w-full bg-gray-950 border border-gray-800 rounded-lg p-1.5 text-xs focus:outline-none">
                                <option value="9:16">Portrait 9:16 (Shorts/Reels)</option>
                                <option value="16:9" selected>Landscape 16:9 (YouTube/PC)</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-[9px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Export Resolution</label>
                            <select id="exportQuality" class="w-full bg-gray-950 border border-gray-800 rounded-lg p-1.5 text-xs focus:outline-none">
                                <option value="720p">720p HD</option>
                                <option value="1080p" selected>1080p Full HD</option>
                                <option value="4k">4K Ultra HD (High Bitrate)</option>
                            </select>
                        </div>
                    </div>

                    <button id="btnExportVideo" onclick="exportComposition()" class="w-full mt-4 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold py-3 px-4 rounded-xl text-xs active:scale-[0.97] transition flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/20">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                        <span>Render HD Export</span>
                    </button>
                </div>

                <!-- Export Progress Card -->
                <div id="exportProgressCard" class="hidden bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-xl space-y-3">
                    <div class="flex justify-between items-center text-xs">
                        <span class="font-bold text-emerald-400 flex items-center gap-1.5">
                            <span class="w-2 h-2 bg-emerald-500 rounded-full animate-ping"></span>
                            Exporting...
                        </span>
                        <span id="exportProgressPct" class="font-mono text-gray-400">0%</span>
                    </div>
                    <div class="w-full bg-gray-950 h-2.5 rounded-full overflow-hidden border border-gray-800">
                        <div id="exportProgressBar" class="bg-gradient-to-r from-emerald-500 to-teal-400 h-full w-[0%] transition-all duration-300"></div>
                    </div>
                    <p id="exportStage" class="text-[10px] text-gray-400 leading-relaxed italic">Initiating rendering threads...</p>
                </div>

                <!-- Completed Exports / Library -->
                <div class="bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-xl">
                    <h2 class="text-sm font-bold mb-3 text-gray-300">Compiled Downloads Library</h2>
                    <div id="exportsList" class="space-y-3 max-h-[180px] overflow-y-auto pr-1">
                        <!-- empty state -->
                        <div class="text-center py-6 text-xs text-gray-600">No exports compiled yet. Select a timeline sequence to start.</div>
                    </div>
                </div>
            </div>

        </div>
    </div>

    <!-- Interactive Javascript Logic -->
    <script>
        // Global variables
        let availableMedia = { uploads: [], tts: [], exports: [] };
        let timeline = [];
        let currentFilter = 'all';
        let dragSrcIndex = null;

        // Live Sequencer State
        let sequenceTimer = null;
        let currentSeqIndex = 0;
        let isSequencePlaying = false;

        // On Load Page
        window.addEventListener('DOMContentLoaded', () => {
            fetchMediaCatalog();
            // Setup Drag and Drop events
            const dropZone = document.getElementById('dropZone');
            
            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.classList.add('border-rose-500', 'bg-rose-950/10');
            });
            
            dropZone.addEventListener('dragleave', () => {
                dropZone.classList.remove('border-rose-500', 'bg-rose-950/10');
            });
            
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('border-rose-500', 'bg-rose-950/10');
                if (e.dataTransfer.files.length > 0) {
                    uploadFile(e.dataTransfer.files[0]);
                }
            });

            dropZone.addEventListener('click', () => {
                document.getElementById('fileInput').click();
            });
        });

        // Toggle voices menu based on engine choice
        function toggleEngineVoices() {
            const engine = document.getElementById('ttsEngine').value;
            const edgeVoices = document.getElementById('ttsVoiceEdge');
            const gttsVoices = document.getElementById('ttsVoiceGtts');
            if (engine === 'edge') {
                edgeVoices.classList.remove('hidden');
                gttsVoices.classList.add('hidden');
            } else {
                edgeVoices.classList.add('hidden');
                gttsVoices.classList.remove('hidden');
            }
        }

        // Fetch Workspace Catalog from API
        // Fetch Workspace Catalog from API
        async function fetchMediaCatalog() {
            try {
                const res = await fetch('/api/media');
                const data = await res.json();
                
                // Reverse uploads so the newest items show up first
                if (data.uploads && Array.isArray(data.uploads)) {
                    data.uploads.reverse();
                }
                
                availableMedia = data;
                renderGallery();
                renderTtsList();
                renderExportsList();
                updateAudioOptions();
            } catch (err) {
                console.error("Error fetching library catalog:", err);
            }
        }

        // Upload Media File
        async function uploadFile(file) {
            const formData = new FormData();
            formData.append('file', file);

            const spinner = document.getElementById('uploadSpinner');
            spinner.classList.remove('hidden');

            try {
                const res = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                if (data.success) {
                    await fetchMediaCatalog();
                } else {
                    alert(data.error || "File upload failed.");
                }
            } catch (err) {
                alert("Upload network error: " + err.message);
            } finally {
                spinner.classList.add('hidden');
            }
        }

        function handleFileSelect(e) {
            if (e.target.files.length > 0) {
                uploadFile(e.target.files[0]);
            }
        }

        // Fetch Youtube Stream via URL
        async function fetchYtUrl() {
            const urlInput = document.getElementById('ytUrl');
            const url = urlInput.value.trim();
            if (!url) return alert("Please specify a URL stream path.");

            const spinner = document.getElementById('ytSpinner');
            spinner.classList.remove('hidden');

            try {
                const res = await fetch('/api/yt-fetch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url, type: "video" })
                });
                const data = await res.json();
                if (data.success) {
                    urlInput.value = '';
                    await fetchMediaCatalog();
                } else {
                    alert(data.error || "Extraction pipeline failure.");
                }
            } catch (err) {
                alert("Extraction error: " + err.message);
            } finally {
                spinner.classList.add('hidden');
            }
        }

        // Synthesize Text to Speech Speech
        async function generateSpeech() {
            const text = document.getElementById('ttsText').value.trim();
            const engine = document.getElementById('ttsEngine').value;
            const voice = (engine === 'edge') ? document.getElementById('ttsVoiceEdge').value : document.getElementById('ttsVoiceGtts').value;

            if (!text) return alert("Speech script transcription can't be empty.");

            const spinner = document.getElementById('ttsSpinner');
            spinner.classList.remove('hidden');

            try {
                const res = await fetch('/api/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text, engine: engine, voice_or_lang: voice })
                });
                const data = await res.json();
                if (data.success) {
                    document.getElementById('ttsText').value = '';
                    await fetchMediaCatalog();
                } else {
                    alert(data.error || "Synthesis failure.");
                }
            } catch (err) {
                alert("Synthesis network error: " + err.message);
            } finally {
                spinner.classList.add('hidden');
            }
        }

        // Filter and Render Media Library Gallery
        function filterGallery(type) {
            currentFilter = type;
            ['tabAll', 'tabVideo', 'tabImage', 'tabAudio'].forEach(tabId => {
                const tab = document.getElementById(tabId);
                if (tabId === 'tab' + type.charAt(0).toUpperCase() + type.slice(1)) {
                    tab.classList.add('bg-gray-900', 'text-rose-400');
                    tab.classList.remove('text-gray-400');
                } else {
                    tab.classList.remove('bg-gray-900', 'text-rose-400');
                    tab.classList.add('text-gray-400');
                }
            });
            renderGallery();
        }

        function renderGallery() {
            const list = document.getElementById('galleryList');
            const filtered = availableMedia.uploads.filter(item => {
                if (currentFilter === 'all') return true;
                return item.type === currentFilter;
            });

            if (filtered.length === 0) {
                list.innerHTML = `<div class="text-center py-6 text-xs text-gray-600">No ${currentFilter} assets found.</div>`;
                return;
            }

            list.innerHTML = filtered.map(item => {
                let badgeColor = item.type === 'video' ? 'bg-indigo-500/10 text-indigo-400' : (item.type === 'image' ? 'bg-amber-500/10 text-amber-400' : 'bg-emerald-500/10 text-emerald-400');
                let displayType = item.type.toUpperCase();
                
                return `
                    <div class="bg-gray-950 border border-gray-800 rounded-xl p-3 flex flex-col gap-3 hover:border-gray-700 transition">
                        <!-- BIG THUMBNAIL DISPLAY LAYER -->
                        <div class="w-full aspect-video bg-black/50 rounded-lg flex items-center justify-center border border-gray-850 overflow-hidden relative group">
                            ${item.type === 'image' ? `
                                <img src="${item.url}" class="w-full h-full object-cover" />
                            ` : (item.type === 'video' ? `
                                <!-- Small video preview element to render its absolute frame -->
                                <video src="${item.url}" class="w-full h-full object-cover opacity-80" muted preload="metadata" onmouseenter="this.play()" onmouseleave="this.pause(); this.currentTime=0;"></video>
                                <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
                                    <span class="p-2 rounded-full bg-black/60 text-indigo-400 border border-indigo-500/20">
                                        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path d="M2 6a2 2 0 012-2h12a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"></path></svg>
                                    </span>
                                </div>
                            ` : `
                                <div class="flex flex-col items-center justify-center gap-1.5 p-4 text-emerald-400">
                                    <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 20 20"><path d="M18 3a1 1 0 00-1.196-.98l-10 2A1 1 0 006 5v9.114A4.369 4.369 0 005 14c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V7.82l8-1.6v5.894A4.369 4.369 0 0015 12c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V3z"></path></svg>
                                    <span class="text-[9px] font-mono text-gray-500">Audio Track</span>
                                </div>
                            `)}
                        </div>

                        <!-- METADATA INFORMATION LAYER -->
                        <div class="min-w-0">
                            <h4 class="text-xs font-semibold text-gray-200 truncate break-all" title="${item.filename}">
                                ${item.filename.split('_').slice(1).join('_') || item.filename}
                            </h4>
                            <span class="px-1.5 py-0.5 rounded text-[8px] font-bold ${badgeColor} uppercase tracking-wider mt-1 inline-block">
                                ${displayType}
                            </span>
                        </div>

                        <!-- ACTION CONTROLS LAYER -->
                        <div class="flex justify-between items-center gap-2 pt-2 border-t border-gray-900">
                            <div class="flex gap-2">
                                <button onclick="deleteAsset('${item.filename}', 'uploads')" class="text-[9px] text-gray-500 hover:text-rose-400 transition flex items-center gap-0.5">
                                    Delete
                                </button>
                                <button onclick="previewAsset('${item.url}', '${item.type}', '${item.filename}')" class="text-[9px] text-violet-400 hover:text-violet-300 font-semibold transition flex items-center gap-0.5">
                                    👁️ Preview
                                </button>
                            </div>
                            <div class="flex gap-1.5">
                                ${item.type !== 'audio' ? `
                                    <button onclick="addToTimeline('${item.filename}', '${item.type}')" class="px-2 py-1 bg-rose-600 hover:bg-rose-500 text-white font-bold rounded text-[9px] active:scale-95 transition">
                                        + Timeline
                                    </button>
                                ` : `
                                    <button onclick="setAsMasterAudio('${item.filename}', 'upload')" class="px-2 py-1 bg-violet-600 hover:bg-violet-500 text-white font-bold rounded text-[9px] active:scale-95 transition">
                                        Use soundtrack
                                    </button>
                                `}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Render Generated TTS Tracklist
        function renderTtsList() {
            const list = document.getElementById('ttsList');
            document.getElementById('ttsCount').textContent = availableMedia.tts.length;

            if (availableMedia.tts.length === 0) {
                list.innerHTML = `<div class="text-center py-6 text-xs text-gray-600">No tracks synthesized yet.</div>`;
                return;
            }

            list.innerHTML = availableMedia.tts.map((item, idx) => `
                <div class="bg-gray-950 border border-gray-800 rounded-xl p-3 space-y-2">
                    <div class="flex items-center justify-between gap-2">
                        <span class="text-[9px] font-mono text-gray-400">Speech Clip #${idx + 1}</span>
                        <button onclick="deleteAsset('${item.filename}', 'tts_audio')" class="text-[8px] text-gray-500 hover:text-red-400">Delete</button>
                    </div>
                    <audio src="${item.url}" controls class="w-full h-7 rounded-lg bg-gray-900 opacity-80 hover:opacity-100 transition"></audio>
                    <div class="flex justify-between items-center text-[10px]">
                        <a href="${item.url}" download class="text-violet-400 hover:underline">Download MP3</a>
                        <button onclick="setAsMasterAudio('${item.filename}', 'tts')" class="px-2 py-0.5 bg-violet-900 hover:bg-violet-800 text-white text-[9px] rounded transition">
                            Use Soundtrack
                        </button>
                    </div>
                </div>
            `).join('');
        }

        // Render Exports Downloads list
        function renderExportsList() {
            const list = document.getElementById('exportsList');
            if (availableMedia.exports.length === 0) {
                list.innerHTML = `<div class="text-center py-6 text-xs text-gray-600">No exports compiled yet. Select a timeline sequence to start.</div>`;
                return;
            }

            list.innerHTML = availableMedia.exports.map((item, idx) => `
                <div class="bg-gray-950 border border-gray-850 rounded-xl p-3 flex justify-between items-center gap-2">
                    <div class="min-w-0 flex-1">
                        <span class="text-[9px] text-gray-500">Video MP4 HD</span>
                        <h4 class="text-xs font-semibold text-gray-200 truncate">${item.filename}</h4>
                    </div>
                    <div class="flex gap-2">
                        <a href="${item.url}" download class="px-2 py-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded text-[9px] active:scale-95 transition">
                            Download
                        </a>
                        <button onclick="deleteAsset('${item.filename}', 'exports')" class="px-1 py-1 text-gray-500 hover:text-red-400 rounded text-[9px] transition">
                            ✕
                        </button>
                    </div>
                </div>
            `).join('');
        }

        // Delete File Wrapper
        async function deleteAsset(filename, folder) {
            try {
                const res = await fetch('/api/media/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename: filename, folder: folder })
                });
                await fetchMediaCatalog();
            } catch (err) {
                alert("Deletion error: " + err.message);
            }
        }

        // Manage Audio selectors
        function updateAudioOptions() {
            const select = document.getElementById('masterAudio');
            const selectedVal = select.value;
            select.innerHTML = `<option value="">-- No Soundtrack (Silent) --</option>`;

            // Add uploads
            availableMedia.uploads.filter(x => x.type === 'audio').forEach(item => {
                const opt = document.createElement('option');
                opt.value = JSON.stringify({ filename: item.filename, source: "uploads" });
                opt.textContent = `📁 PC: ${item.filename.split('_').slice(1).join('_') || item.filename}`;
                select.appendChild(opt);
            });

            // Add TTS
            availableMedia.tts.forEach((item, idx) => {
                const opt = document.createElement('option');
                opt.value = JSON.stringify({ filename: item.filename, source: "tts" });
                opt.textContent = `🎙️ TTS: Speech Clip #${idx + 1}`;
                select.appendChild(opt);
            });

            // Keep selection if exists
            if (selectedVal) select.value = selectedVal;
        }

        function setAsMasterAudio(filename, source) {
            const select = document.getElementById('masterAudio');
            const targetJSON = JSON.stringify({ filename: filename, source: source === 'tts' ? 'tts' : 'uploads' });
            select.value = targetJSON;
        }

        // ================= TIMELINE TRACK OPERATIONS =================

        function addToTimeline(filename, type) {
            timeline.push({
                id: uuid(),
                filename: filename,
                type: type,
                duration: 5, // Default 5s
                effect: 'none'
            });
            renderTimeline();
        }

        function uuid() {
            return Math.random().toString(36).substring(2, 9);
        }

        function moveTimelineItem(index, dir) {
            const targetIdx = index + dir;
            if (targetIdx < 0 || targetIdx >= timeline.length) return;
            // Swap
            const temp = timeline[index];
            timeline[index] = timeline[targetIdx];
            timeline[targetIdx] = temp;
            renderTimeline();
        }

        function removeTimelineItem(index) {
            timeline.splice(index, 1);
            renderTimeline();
        }

        function clearTimeline() {
            timeline = [];
            renderTimeline();
        }

        function updateTimelineItemProp(index, prop, val) {
            timeline[index][prop] = val;
        }

        function renderTimeline() {
            const list = document.getElementById('timelineList');
            if (timeline.length === 0) {
                list.innerHTML = `
                    <div class="text-center py-8 text-xs text-gray-600 border border-dashed border-gray-800 rounded-xl">
                        Drag or click assets in your library to add them to the video composition timeline!
                    </div>`;
                return;
            }

            list.innerHTML = timeline.map((item, index) => {
                let badgeColor = item.type === 'video' ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-900/40' : 'bg-amber-500/10 text-amber-400 border border-amber-900/40';
                return `
                    <div class="bg-gray-950 border border-gray-850 rounded-xl p-3 flex flex-col gap-2 relative">
                        <!-- Top details -->
                        <div class="flex items-center justify-between gap-2">
                            <div class="flex items-center gap-2 min-w-0">
                                <span class="px-1.5 py-0.5 rounded text-[8px] font-bold ${badgeColor} uppercase tracking-wider">
                                    ${item.type.toUpperCase()}
                                </span>
                                <h4 class="text-xs font-semibold text-gray-300 truncate" title="${item.filename}">
                                    ${item.filename.split('_').slice(1).join('_') || item.filename}
                                </h4>
                            </div>
                            <!-- Ordering & Removal -->
                            <div class="flex items-center gap-1">
                                <button onclick="previewAsset('/api/files/uploads/${item.filename}', '${item.type}', '${item.filename}')" class="text-[10px] p-1 text-violet-400 hover:text-violet-300 font-semibold mr-1.5" title="Preview Clip">👁️ Preview</button>
                                <button onclick="moveTimelineItem(${index}, -1)" class="text-xs p-1 text-gray-500 hover:text-gray-300">▲</button>
                                <button onclick="moveTimelineItem(${index}, 1)" class="text-xs p-1 text-gray-500 hover:text-gray-300">▼</button>
                                <button onclick="removeTimelineItem(${index})" class="text-xs p-1 text-gray-500 hover:text-rose-400 ml-1">✕</button>
                            </div>
                        </div>

                        <!-- Trimming duration and Effects -->
                        <div class="grid grid-cols-2 gap-2 text-[10px] text-gray-400">
                            <div>
                                <label class="block text-[8px] text-gray-500 uppercase font-semibold">Clip Duration (s)</label>
                                <input type="number" min="1" max="120" value="${item.duration}" 
                                       onchange="updateTimelineItemProp(${index}, 'duration', this.value)" 
                                       class="w-full bg-gray-900 border border-gray-800 rounded px-2 py-1 text-xs focus:outline-none">
                            </div>
                            <div>
                                <label class="block text-[8px] text-gray-500 uppercase font-semibold">Transition/Effect</label>
                                <select onchange="updateTimelineItemProp(${index}, 'effect', this.value)" 
                                        class="w-full bg-gray-900 border border-gray-800 rounded px-2 py-1 text-xs focus:outline-none">
                                    <option value="none" ${item.effect === 'none' ? 'selected' : ''}>None</option>
                                    <option value="fade" ${item.effect === 'fade' ? 'selected' : ''}>Cross Fade</option>
                                    <option value="rotate" ${item.effect === 'rotate' ? 'selected' : ''}>Rotate Frame</option>
                                </select>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // ================= EXPORT COMPOSITION PIPELINE =================

        async function exportComposition() {
            if (timeline.length === 0) {
                return alert("Timeline sequence is empty. Add elements first.");
            }

            const audioSelect = document.getElementById('masterAudio');
            let audio_track = null;
            if (audioSelect.value) {
                audio_track = JSON.parse(audioSelect.value);
            }

            const loop_audio = document.getElementById('loopAudio').checked;
            const match_audio_length = document.getElementById('matchAudio').checked;

            const format = document.getElementById('canvasFormat').value;
            const quality = document.getElementById('exportQuality').value;

            const payload = {
                timeline: timeline,
                audio_track: audio_track,
                settings: {
                    format: format,
                    quality: quality,
                    loop_audio: loop_audio,
                    match_audio_length: match_audio_length
                }
            };

            const progressCard = document.getElementById('exportProgressCard');
            const progressPct = document.getElementById('exportProgressPct');
            const progressBar = document.getElementById('exportProgressBar');
            const exportStage = document.getElementById('exportStage');
            const btnExportVideo = document.getElementById('btnExportVideo');

            // Disable export trigger
            btnExportVideo.disabled = true;
            btnExportVideo.classList.add('opacity-50');

            progressCard.classList.remove('hidden');
            progressPct.textContent = "0%";
            progressBar.style.width = "0%";
            exportStage.textContent = "Starting render threads...";

            try {
                const res = await fetch('/api/export', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                
                if (data.error) {
                    alert(data.error);
                    btnExportVideo.disabled = false;
                    btnExportVideo.classList.remove('opacity-50');
                    progressCard.classList.add('hidden');
                    return;
                }

                // Start polling status
                pollExportStatus(data.task_id);

            } catch (err) {
                alert("Export submission error: " + err.message);
                btnExportVideo.disabled = false;
                btnExportVideo.classList.remove('opacity-50');
                progressCard.classList.add('hidden');
            }
        }

        function pollExportStatus(taskId) {
            const progressPct = document.getElementById('exportProgressPct');
            const progressBar = document.getElementById('exportProgressBar');
            const exportStage = document.getElementById('exportStage');
            const progressCard = document.getElementById('exportProgressCard');
            const btnExportVideo = document.getElementById('btnExportVideo');

            const interval = setInterval(async () => {
                try {
                    const res = await fetch(`/api/export/status/${taskId}`);
                    const data = await res.json();

                    if (data.error) {
                        clearInterval(interval);
                        alert("Rendering Crash: " + data.error);
                        btnExportVideo.disabled = false;
                        btnExportVideo.classList.remove('opacity-50');
                        progressCard.classList.add('hidden');
                        return;
                    }

                    // Update UI progress
                    progressPct.textContent = data.progress + "%";
                    progressBar.style.width = data.progress + "%";
                    exportStage.textContent = data.stage;

                    if (data.progress >= 100) {
                        clearInterval(interval);
                        btnExportVideo.disabled = false;
                        btnExportVideo.classList.remove('opacity-50');
                        setTimeout(() => {
                            progressCard.classList.add('hidden');
                        }, 1000);
                        await fetchMediaCatalog();
                    }

                } catch (err) {
                    console.error("Polling error:", err);
                }
            }, 1500);
        }

        // ================= CLIENT-SIDE LIVE PREVIEW THEATER & PLAYBACK SEQUENCER =================

        function previewAsset(url, type, filename) {
            // Stop active sequence if playing
            if (isSequencePlaying) {
                stopLiveSequence();
            }
            
            // Get viewports
            const videoEl = document.getElementById('viewportVideo');
            const imageEl = document.getElementById('viewportImage');
            const audioVis = document.getElementById('viewportAudioVisualizer');
            const placeholder = document.getElementById('viewportPlaceholder');
            const audioPreviewName = document.getElementById('audioPreviewName');
            const timelineAudio = document.getElementById('timelinePreviewAudio');
            const seqOverlay = document.getElementById('viewportSequenceOverlay');
            
            // Hide everything
            videoEl.classList.add('hidden');
            imageEl.classList.add('hidden');
            audioVis.classList.add('hidden');
            placeholder.classList.add('hidden');
            seqOverlay.classList.add('hidden');
            
            // Stop any playing audio/video
            videoEl.pause();
            videoEl.src = "";
            timelineAudio.pause();
            timelineAudio.src = "";
            
            const displayName = filename ? (filename.split('_').slice(1).join('_') || filename) : "Asset Preview";
            document.getElementById('seqDurationVal').textContent = displayName;
            
            if (type === 'video') {
                videoEl.classList.remove('hidden');
                videoEl.src = url;
                videoEl.muted = false;
                videoEl.play().catch(e => console.log("Video auto play prevented:", e));
            } else if (type === 'image') {
                imageEl.classList.remove('hidden');
                imageEl.src = url;
            } else if (type === 'audio' || type === 'tts') {
                audioVis.classList.remove('hidden');
                audioPreviewName.textContent = displayName;
                timelineAudio.src = url;
                timelineAudio.play().catch(e => console.log("Audio auto play prevented:", e));
            } else {
                placeholder.classList.remove('hidden');
            }
        }

        function playLiveSequence() {
            if (timeline.length === 0) {
                return alert("Timeline sequence is empty. Please add elements to the timeline first.");
            }
            
            // Stop any previous playing sequence or asset
            stopLiveSequence();
            
            isSequencePlaying = true;
            currentSeqIndex = 0;
            
            const btnPlay = document.getElementById('btnPlaySeq');
            btnPlay.classList.add('bg-emerald-600', 'hover:bg-emerald-500');
            btnPlay.classList.remove('bg-rose-600', 'hover:bg-rose-500');
            btnPlay.innerHTML = `
                <svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Playing...</span>
            `;
            
            // Setup master audio soundtrack if selected
            const audioSelect = document.getElementById('masterAudio');
            const timelineAudio = document.getElementById('timelinePreviewAudio');
            timelineAudio.pause();
            timelineAudio.src = "";
            
            if (audioSelect.value) {
                try {
                    const audio_track = JSON.parse(audioSelect.value);
                    const folder = audio_track.source === 'tts' ? 'tts_audio' : 'uploads';
                    timelineAudio.src = `/api/files/${folder}/${audio_track.filename}`;
                    timelineAudio.loop = document.getElementById('loopAudio').checked;
                    timelineAudio.currentTime = 0;
                    timelineAudio.play().catch(e => console.log("Master audio preview prevented:", e));
                } catch (e) {
                    console.error("Failed to parse or play soundtrack:", e);
                }
            }
            
            document.getElementById('viewportSequenceOverlay').classList.remove('hidden');
            
            // Play through the timeline items recursively
            playNextTimelineItem();
        }
        
        function playNextTimelineItem() {
            if (!isSequencePlaying) return;
            
            if (currentSeqIndex >= timeline.length) {
                // Done playing!
                stopLiveSequence();
                return;
            }
            
            const item = timeline[currentSeqIndex];
            const durationMs = (parseFloat(item.duration) || 5) * 1000;
            
            // Update overlay numbers
            document.getElementById('seqClipIndex').textContent = currentSeqIndex + 1;
            document.getElementById('seqClipTotal').textContent = timeline.length;
            
            const displayName = item.filename.split('_').slice(1).join('_') || item.filename;
            document.getElementById('seqDurationVal').textContent = `${displayName} (${item.duration}s)`;
            
            // Get viewports
            const videoEl = document.getElementById('viewportVideo');
            const imageEl = document.getElementById('viewportImage');
            const audioVis = document.getElementById('viewportAudioVisualizer');
            const placeholder = document.getElementById('viewportPlaceholder');
            
            // Hide everything first
            videoEl.classList.add('hidden');
            imageEl.classList.add('hidden');
            audioVis.classList.add('hidden');
            placeholder.classList.add('hidden');
            
            // Stop current viewport video
            videoEl.pause();
            videoEl.src = "";
            
            // Prepare media URL
            const url = `/api/files/uploads/${item.filename}`;
            
            // Display item based on type
            if (item.type === 'video') {
                videoEl.classList.remove('hidden');
                videoEl.src = url;
                videoEl.muted = true; // Mute preview so it doesn't clash with master audio soundtrack
                videoEl.currentTime = 0;
                videoEl.play().catch(e => console.log("Video track playback prevented:", e));
            } else if (item.type === 'image') {
                imageEl.classList.remove('hidden');
                imageEl.src = url;
            } else {
                placeholder.classList.remove('hidden');
            }
            
            // Highlight current active item in timeline visual track list
            highlightTimelineItem(currentSeqIndex);
            
            // Set timeout for next item
            sequenceTimer = setTimeout(() => {
                currentSeqIndex++;
                playNextTimelineItem();
            }, durationMs);
        }
        
        function highlightTimelineItem(activeIndex) {
            const timelineList = document.getElementById('timelineList');
            const cards = timelineList.children;
            for (let i = 0; i < cards.length; i++) {
                if (i === activeIndex) {
                    cards[i].classList.add('ring-2', 'ring-rose-500', 'border-rose-500');
                    cards[i].classList.remove('border-gray-850');
                    cards[i].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                } else {
                    cards[i].classList.remove('ring-2', 'ring-rose-500', 'border-rose-500');
                    cards[i].classList.add('border-gray-850');
                }
            }
        }
        
        function stopLiveSequence() {
            isSequencePlaying = false;
            if (sequenceTimer) {
                clearTimeout(sequenceTimer);
                sequenceTimer = null;
            }
            
            // Reset Play button
            const btnPlay = document.getElementById('btnPlaySeq');
            btnPlay.classList.remove('bg-emerald-600', 'hover:bg-emerald-500');
            btnPlay.classList.add('bg-rose-600', 'hover:bg-rose-500');
            btnPlay.innerHTML = `
                <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd"></path></svg>
                <span>Play Sequence</span>
            `;
            
            // Stop preview master audio
            const timelineAudio = document.getElementById('timelinePreviewAudio');
            timelineAudio.pause();
            timelineAudio.src = "";
            
            // Stop viewport elements
            const videoEl = document.getElementById('viewportVideo');
            videoEl.pause();
            videoEl.src = "";
            
            const imageEl = document.getElementById('viewportImage');
            imageEl.src = "";
            
            // Hide overlay
            document.getElementById('viewportSequenceOverlay').classList.add('hidden');
            
            // Reset viewport to default placeholder
            videoEl.classList.add('hidden');
            imageEl.classList.add('hidden');
            document.getElementById('viewportAudioVisualizer').classList.add('hidden');
            document.getElementById('viewportPlaceholder').classList.remove('hidden');
            
            document.getElementById('seqDurationVal').textContent = "0.0s";
            
            // Remove highlight ring from timeline cards
            const timelineList = document.getElementById('timelineList');
            const cards = timelineList.children;
            for (let i = 0; i < cards.length; i++) {
                cards[i].classList.remove('ring-2', 'ring-rose-500', 'border-rose-500');
                cards[i].classList.add('border-gray-850');
            }
        }
    </script>
</body>
</html>
"""

# Serve execution
if __name__ == '__main__':
    # Configured to run strictly on external proxy port 3000
    app.run(host='0.0.0.0', port=21000, debug=True)