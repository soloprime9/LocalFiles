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

# Emotion presets approximate vocal "feeling" via Edge-TTS prosody (rate/pitch),
# since Communicate doesn't expose SSML express-as styles directly.
EMOTION_PRESETS = {
    "neutral":   {"rate": "+0%",  "pitch": "+0Hz"},
    "cheerful":  {"rate": "+15%", "pitch": "+25Hz"},
    "excited":   {"rate": "+25%", "pitch": "+35Hz"},
    "calm":      {"rate": "-10%", "pitch": "-5Hz"},
    "sad":       {"rate": "-15%", "pitch": "-20Hz"},
    "serious":   {"rate": "-5%",  "pitch": "-10Hz"},
    "angry":     {"rate": "+10%", "pitch": "-15Hz"},
    "whisper":   {"rate": "-20%", "pitch": "-30Hz"},
    "dramatic":  {"rate": "-8%",  "pitch": "+10Hz"},
}

async def generate_edge_tts(text, voice, output_path, rate="+0%", pitch="+0Hz"):
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)

def render_text_to_speech(text, engine, voice_or_lang, output_path, emotion="neutral"):
    """
    Renders text to speech using either Microsoft Edge-TTS or Google gTTS.
    `emotion` (edge engine only) adjusts rate/pitch to approximate an emotional tone.
    """
    if engine == "edge":
        if edge_tts is None:
            raise ImportError("Microsoft Edge TTS library is not installed.")
        preset = EMOTION_PRESETS.get(emotion, EMOTION_PRESETS["neutral"])
        # Run async function in synchronous wrapper
        asyncio.run(generate_edge_tts(text, voice_or_lang, output_path, rate=preset["rate"], pitch=preset["pitch"]))
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
            'format': 'best[ext=mp4]/best',
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
                effect = item.get("effect", "none") # e.g. "none", "fade", "rotate", "kenburns", "blur", "grayscale", ...
                speed = float(item.get("speed", 1.0) or 1.0)
                brightness = float(item.get("brightness", 0) or 0)   # -1.0 .. 1.0
                contrast = float(item.get("contrast", 1) or 1)       # 0.0 .. 2.0
                saturation = float(item.get("saturation", 1) or 1)   # 0.0 .. 3.0
                text_overlay = (item.get("text_overlay") or "").strip()
                text_position = item.get("text_position", "bottom")  # top, center, bottom

                media_path = os.path.join(UPLOAD_FOLDER, filename)
                if not os.path.exists(media_path):
                    continue

                update_progress(10 + int((idx / total_items) * 50), f"Encoding clip {idx+1}/{total_items}: {filename}...")

                clip_output = os.path.join(temp_dir, f"clip_{idx:04d}.mp4")

                def build_modern_filter_chain(base_filter, dur, fx, spd, br, ct, sat, txt, txt_pos):
                    """Appends modern CapCut-style effect/color-grade/text-overlay filters onto a base scale/pad chain."""
                    chain = base_filter
                    if fx == "fade":
                        chain += f",fade=in:st=0:d=0.5,fade=out:st={max(0, dur-0.5)}:d=0.5"
                    elif fx == "rotate":
                        chain += ",rotate=PI"
                    elif fx == "kenburns":
                        frames = max(int(dur * 30), 1)
                        chain += f",scale=8000:-1,zoompan=z='min(zoom+0.0015,1.3)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height},fps=30"
                    elif fx == "zoomin":
                        frames = max(int(dur * 30), 1)
                        chain += f",zoompan=z='min(zoom+0.002,1.4)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}"
                    elif fx == "blur":
                        chain += ",gblur=sigma=6"
                    elif fx == "grayscale":
                        chain += ",hue=s=0"
                    elif fx == "sepia":
                        chain += ",colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131"
                    elif fx == "vignette":
                        chain += ",vignette=PI/4"
                    elif fx == "mirror":
                        chain += ",hflip"
                    elif fx == "shake":
                        chain += ",crop=iw-20:ih-20:10*sin(n/5):10*cos(n/5)"
                    elif fx == "glitch":
                        chain += ",rgbashift=rh=4:bv=-4"

                    if spd and abs(spd - 1.0) > 0.01:
                        chain += f",setpts=PTS/{spd}"

                    if (br and abs(br) > 0.001) or (ct and abs(ct - 1.0) > 0.001) or (sat and abs(sat - 1.0) > 0.001):
                        chain += f",eq=brightness={br}:contrast={ct}:saturation={sat}"

                    if txt:
                        safe_txt = txt.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
                        y_expr = {"top": "h*0.08", "center": "(h-text_h)/2", "bottom": "h*0.85"}.get(txt_pos, "h*0.85")
                        chain += (
                            f",drawtext=text='{safe_txt}':fontcolor=white:fontsize=h*0.045:"
                            f"x=(w-text_w)/2:y={y_expr}:box=1:boxcolor=black@0.45:boxborderw=14:line_spacing=4"
                        )
                    return chain

                # Setup FFmpeg command for this specific clip
                # We scale and pad perfectly to match width & height, enforce 30fps, and force stereo 44100Hz audio.
                if ftype == "image":
                    # Image input: loop it, add null audio
                    cmd = [
                        ffmpeg_bin, "-y",
                        "-loop", "1", "-t", str(duration), "-i", media_path,
                        "-f", "lavfi", "-i", "anullsrc=cl=stereo:r=44100",
                    ]
                    # Filter: scale to decrease, pad, set sar, and apply modern effect/color/text chain
                    v_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
                    v_filter = build_modern_filter_chain(v_filter, duration, effect, speed, brightness, contrast, saturation, text_overlay, text_position)

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
                    v_filter = build_modern_filter_chain(v_filter, duration, effect, speed, brightness, contrast, saturation, text_overlay, text_position)
                    a_filter = "aformat=sample_rates=44100:channel_layouts=stereo"
                    if speed and abs(speed - 1.0) > 0.01:
                        remaining = speed
                        stages = []
                        while remaining > 2.0:
                            stages.append(2.0)
                            remaining /= 2.0
                        while remaining < 0.5:
                            stages.append(0.5)
                            remaining /= 0.5
                        stages.append(remaining)
                        a_filter += "".join(f",atempo={s:.4f}" for s in stages)

                    if has_aud:
                        # Video has audio: scale video, standardise audio
                        cmd = [
                            ffmpeg_bin, "-y",
                            "-ss", "0", "-t", str(duration), "-i", media_path,
                            "-filter_complex", f"[0:v]{v_filter}[v];[0:a]{a_filter}[a]",
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

            # 2. Assemble clips - either plain concat (fast, default) or true cross-clip
            #    crossfade transitions (re-encoded, smoother CapCut-style blending between clips)
            update_progress(70, "Assembling video sequence tracks...")
            use_crossfade = bool(settings.get("crossfade_transitions")) and len(temp_clips) > 1
            temp_concat_video = os.path.join(temp_dir, "concat_output.mp4")

            if use_crossfade:
                try:
                    xfade_dur = float(settings.get("crossfade_duration", 0.6) or 0.6)
                    xfade_dur = max(0.1, min(xfade_dur, 2.0))
                    xfade_style = settings.get("crossfade_style", "fade")  # fade, wipeleft, slideleft, circleopen, dissolve, etc.

                    clip_durations = [max(get_audio_duration(c), xfade_dur + 0.05) for c in temp_clips]

                    inputs = []
                    for c in temp_clips:
                        inputs += ["-i", c]

                    v_chain_parts = []
                    a_chain_parts = []
                    running_total = clip_durations[0]
                    prev_v_label = "0:v"
                    prev_a_label = "0:a"

                    for i in range(1, len(temp_clips)):
                        out_v = f"v{i:02d}"
                        out_a = f"a{i:02d}"
                        offset = max(running_total - xfade_dur, 0)
                        v_chain_parts.append(
                            f"[{prev_v_label}][{i}:v]xfade=transition={xfade_style}:duration={xfade_dur}:offset={offset:.3f}[{out_v}]"
                        )
                        a_chain_parts.append(
                            f"[{prev_a_label}][{i}:a]acrossfade=d={xfade_dur}[{out_a}]"
                        )
                        running_total = running_total + clip_durations[i] - xfade_dur
                        prev_v_label = out_v
                        prev_a_label = out_a

                    filter_complex = ";".join(v_chain_parts + a_chain_parts)
                    xfade_cmd = [
                        ffmpeg_bin, "-y", *inputs,
                        "-filter_complex", filter_complex,
                        "-map", f"[{prev_v_label}]", "-map", f"[{prev_a_label}]",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                        "-c:a", "aac",
                        temp_concat_video
                    ]
                    proc = subprocess.run(xfade_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if proc.returncode != 0 or not os.path.exists(temp_concat_video):
                        print(f"[XFADE WARN] Crossfade assembly failed, falling back to plain concat: {proc.stderr}")
                        use_crossfade = False
                except Exception as xfade_err:
                    print(f"[XFADE WARN] Crossfade setup failed, falling back to plain concat: {xfade_err}")
                    use_crossfade = False

            if not use_crossfade:
                concat_list_file = os.path.join(temp_dir, "concat.txt")
                with open(concat_list_file, "w") as f:
                    for clip in temp_clips:
                        f.write(f"file '{clip}'\n")

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

                    # Crop video to exact audio length, mix audio
                    mix_cmd = [
                        ffmpeg_bin, "-y",
                        "-t", str(audio_duration), "-i", temp_concat_video,
                        "-i", audio_file,
                        "-filter_complex", "[1:a]volume=0.45[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[a]",
                        "-map", "0:v", "-map", "[a]",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                        "-c:a", "aac",
                        output_path
                    ]
                else:
                    # Video duration is master
                    if loop_audio and audio_duration < video_duration:
                        # Loop soundtrack to fit video duration
                        mix_cmd = [
                            ffmpeg_bin, "-y",
                            "-i", temp_concat_video,
                            "-stream_loop", "-1", "-i", audio_file,
                            "-filter_complex", f"[1:a]volume=0.45,atrim=0:{video_duration}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[a]",
                            "-map", "0:v", "-map", "[a]",
                            "-c:v", "copy", "-c:a", "aac", "-t", str(video_duration),
                            output_path
                        ]
                    else:
                        # Trim soundtrack to fit video
                        mix_cmd = [
                            ffmpeg_bin, "-y",
                            "-i", temp_concat_video,
                            "-i", audio_file,
                            "-filter_complex", f"[1:a]volume=0.45,atrim=0:{video_duration}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[a]",
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
    Renders the high-performance video dashboard UI, embedded directly in this Python
    file (HTML_DASHBOARD) - no external template file needed.
    """
    return render_template_string(HTML_DASHBOARD)

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
    emotion = data.get("emotion", "neutral")  # edge engine only: neutral, cheerful, excited, calm, sad, serious, angry, whisper, dramatic

    if not text:
        return jsonify({"error": "Speech transcription text is empty."}), 400

    unique_id = uuid.uuid4().hex[:8]
    output_filename = f"tts_{unique_id}.mp3"
    output_path = os.path.join(TTS_FOLDER, output_filename)

    try:
        render_text_to_speech(text, engine, voice_or_lang, output_path, emotion=emotion)
        return jsonify({
            "success": True,
            "filename": output_filename,
            "text": text,
            "engine": engine,
            "voice": voice_or_lang,
            "emotion": emotion if engine == "edge" else None,
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
            background: radial-gradient(circle at 50% 0%, #0d2b2e 0%, #061018 50%, #03060b 100%) fixed;
            background-color: #03060b;
            color: #f3f4f6;
            min-height: 100vh;
            transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
        }
        body.theme-purple {
            background: radial-gradient(circle at 50% 0%, #1e113a 0%, #0e071e 50%, #05020c 100%) fixed;
            background-color: #05020c;
        }
        body.theme-sunset {
            background: radial-gradient(circle at 50% 0%, #3a0d2e 0%, #1b0616 50%, #0a0108 100%) fixed;
            background-color: #0a0108;
        }
        body.theme-ocean {
            background: radial-gradient(circle at 50% 0%, #082845 0%, #041424 50%, #020810 100%) fixed;
            background-color: #020810;
        }
        body.theme-emerald {
            background: radial-gradient(circle at 50% 0%, #092e1e 0%, #04160e 50%, #010805 100%) fixed;
            background-color: #010805;
        }
        body.theme-crimson {
            background: radial-gradient(circle at 50% 0%, #3a0d0d 0%, #1e0606 50%, #0c0202 100%) fixed;
            background-color: #0c0202;
        }
        body.theme-gold {
            background: radial-gradient(circle at 50% 0%, #2e1e0a 0%, #170f05 50%, #080502 100%) fixed;
            background-color: #080502;
        }
        body.theme-mono {
            background: radial-gradient(circle at 50% 0%, #1f2326 0%, #111315 50%, #08090a 100%) fixed;
            background-color: #08090a;
        }
        .mono {
            font-family: 'JetBrains Mono', monospace;
        }
        .glass-panel {
            background: linear-gradient(160deg, rgba(22,32,38,0.75) 0%, rgba(10,16,22,0.85) 100%);
            border: 1px solid rgba(255,255,255,0.05);
            box-shadow: 0 10px 40px -10px rgba(0,0,0,0.7);
            backdrop-filter: blur(12px);
        }
        .accent-glow {
            box-shadow: 0 0 0 1px rgba(45,212,191,0.25), 0 4px 18px -6px rgba(20,184,166,0.35);
        }
        /* Custom scrollbars */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #03060b;
        }
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(180deg, #1e293b, #0f172a);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #2dd4bf;
        }
        /* Custom scrollbar for horizontal tracks */
        .overflow-x-auto::-webkit-scrollbar {
            height: 6px;
        }
        .overflow-x-auto::-webkit-scrollbar-track {
            background: #03060b;
        }
        .overflow-x-auto::-webkit-scrollbar-thumb {
            background: #1e293b;
            border-radius: 4px;
        }
        .overflow-x-auto::-webkit-scrollbar-thumb:hover {
            background: #2dd4bf;
        }
        /* CapCut-style icon toolbar */
        .cc-tool-tab {
            display: flex; flex-direction: column; align-items: center; gap: 4px;
            padding: 8px 14px; border-radius: 12px; cursor: pointer;
            color: #9ca3af; font-size: 11px; font-weight: 500;
            transition: all .15s ease; border: 1px solid transparent;
            user-select: none;
        }
        .cc-tool-tab:hover {
            color: #2dd4bf; background: rgba(45,212,191,0.06);
        }
        .cc-tool-tab.active {
            color: #2dd4bf; background: rgba(45,212,191,0.12);
            border-color: rgba(45,212,191,0.3);
            box-shadow: 0 0 12px rgba(45,212,191,0.08);
        }
        .cc-tool-tab svg { width: 19px; height: 19px; }
        /* Effect tile grid */
        .fx-tile {
            position: relative; aspect-ratio: 1/1; border-radius: 10px; overflow: hidden;
            cursor: pointer; border: 2px solid #1f2937;
            display: flex; align-items: center; justify-content: center;
            font-size: 22px; transition: all .15s ease;
            background: linear-gradient(150deg, #111827, #030712);
        }
        .fx-tile:hover { border-color: #2dd4bf; transform: translateY(-1px); }
        .fx-tile.selected {
            border-color: #2dd4bf;
            box-shadow: 0 0 0 2px rgba(45,212,191,0.35);
        }
        .fx-tile .fx-label {
            position: absolute; bottom: 0; left: 0; right: 0;
            font-size: 8px; text-align: center; padding: 3px 2px;
            background: rgba(0,0,0,0.65); color: #d1d5db;
            text-transform: uppercase; letter-spacing: .03em; font-weight: 600;
        }
    </style>
</head>
<body class="min-h-screen py-6 px-4 sm:px-6 lg:px-8">
    <div class="max-w-7xl mx-auto">
        <!-- CapCut-style icon toolbar -->
        <div class="glass-panel rounded-2xl px-3 py-2 mb-4 flex items-center gap-1 overflow-x-auto">
            <div class="cc-tool-tab active" onclick="ccScrollTo('panelImport')">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 16V4m0 0L8 8m4-4l4 4M4 20h16"/></svg>
                Import
            </div>
            <div class="cc-tool-tab" onclick="ccScrollTo('panelTTS')">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 11-14 0m7 7v3m-3 0h6M12 14a3 3 0 003-3V5a3 3 0 10-6 0v6a3 3 0 003 3z"/></svg>
                Audio / TTS
            </div>
            <div class="cc-tool-tab" onclick="ccScrollTo('panelTimeline')">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7"/></svg>
                Text
            </div>
            <div class="cc-tool-tab" onclick="ccScrollTo('panelTimeline')">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.1-1.34 2-3 2s-3-.9-3-2 1.34-2 3-2 3 .9 3 2zm12-3c0 1.1-1.34 2-3 2s-3-.9-3-2 1.34-2 3-2 3 .9 3 2z"/></svg>
                Stickers
            </div>
            <div class="cc-tool-tab" onclick="ccScrollTo('panelEffectsGrid')">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                Effects
            </div>
            <div class="cc-tool-tab" onclick="ccScrollTo('panelTimeline')">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 8v8m0 0l4-4m-4 4l-4-4M7 20v-4m10-12v4"/></svg>
                Transitions
            </div>
            <div class="cc-tool-tab" onclick="ccScrollTo('panelTimeline')">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M7 12h10M10 18h4"/></svg>
                Filters
            </div>
            <div class="cc-tool-tab" onclick="ccScrollTo('panelTimeline')">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v2m0 14v2m9-9h-2M5 12H3m15.36-6.36l-1.42 1.42M7.05 16.95l-1.42 1.42m12.73 0l-1.42-1.42M7.05 7.05L5.64 5.64M12 8a4 4 0 100 8 4 4 0 000-8z"/></svg>
                Adjustment
            </div>
        </div>
        <!-- Header -->
        <header class="flex flex-col md:flex-row justify-between items-center mb-6 pb-5 border-b border-gray-800 gap-4">
            <div>
                <h1 class="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-teal-400 via-emerald-400 to-indigo-500 bg-clip-text text-transparent">
                    TTS & Pro Video Studio
                </h1>
                <p class="mt-1 text-gray-400 text-xs font-medium">
                    Synthesize life-like voices, import links, arrange media, sync audios, loop overlays, and export up to 4K.
                </p>
            </div>
            <div class="flex flex-wrap items-center gap-3 bg-slate-950/60 border border-slate-800/80 px-4 py-2 rounded-2xl shadow-lg">
                <span class="text-[10px] font-extrabold uppercase tracking-widest text-teal-400 flex items-center gap-1.5">
                    <span class="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse"></span>
                    Live Background:
                </span>
                <div class="flex items-center gap-1.5">
                    <!-- Midnight Teal -->
                    <button onclick="selectTheme('', 'Midnight Teal', '#2dd4bf')" class="w-6 h-6 rounded-full bg-teal-500 border-2 border-teal-400/80 hover:scale-110 active:scale-95 transition-all shadow-[0_0_8px_rgba(45,212,191,0.3)]" title="Midnight Teal"></button>
                    <!-- Cosmic Amethyst -->
                    <button onclick="selectTheme('theme-purple', 'Cosmic Amethyst', '#a78bfa')" class="w-6 h-6 rounded-full bg-purple-500 border border-purple-400/80 hover:scale-110 active:scale-95 transition-all shadow-[0_0_8px_rgba(167,139,250,0.3)]" title="Cosmic Amethyst"></button>
                    <!-- Cyberpunk Neon -->
                    <button onclick="selectTheme('theme-sunset', 'Cyberpunk Neon', '#f472b6')" class="w-6 h-6 rounded-full bg-pink-500 border border-pink-400/80 hover:scale-110 active:scale-95 transition-all shadow-[0_0_8px_rgba(244,114,182,0.3)]" title="Cyberpunk Neon"></button>
                    <!-- Oceanic Abyss -->
                    <button onclick="selectTheme('theme-ocean', 'Oceanic Abyss', '#38bdf8')" class="w-6 h-6 rounded-full bg-sky-500 border border-sky-400/80 hover:scale-110 active:scale-95 transition-all shadow-[0_0_8px_rgba(56,189,248,0.3)]" title="Oceanic Abyss"></button>
                    <!-- Emerald Forest -->
                    <button onclick="selectTheme('theme-emerald', 'Emerald Forest', '#34d399')" class="w-6 h-6 rounded-full bg-emerald-500 border border-emerald-400/80 hover:scale-110 active:scale-95 transition-all shadow-[0_0_8px_rgba(52,211,153,0.3)]" title="Emerald Forest"></button>
                    <!-- Crimson Volcano -->
                    <button onclick="selectTheme('theme-crimson', 'Crimson Volcano', '#f87171')" class="w-6 h-6 rounded-full bg-rose-500 border border-rose-400/80 hover:scale-110 active:scale-95 transition-all shadow-[0_0_8px_rgba(248,113,113,0.3)]" title="Crimson Volcano"></button>
                    <!-- Golden Hour -->
                    <button onclick="selectTheme('theme-gold', 'Golden Hour', '#fbbf24')" class="w-6 h-6 rounded-full bg-amber-500 border border-amber-400/80 hover:scale-110 active:scale-95 transition-all shadow-[0_0_8px_rgba(251,191,36,0.3)]" title="Golden Hour"></button>
                    <!-- Slate Stealth -->
                    <button onclick="selectTheme('theme-mono', 'Slate Stealth', '#9ca3af')" class="w-6 h-6 rounded-full bg-gray-500 border border-gray-400/80 hover:scale-110 active:scale-95 transition-all shadow-[0_0_8px_rgba(156,156,156,0.3)]" title="Slate Stealth"></button>
                </div>
                <span id="themeLabelDisplay" class="text-[10px] font-mono text-gray-300 bg-gray-950 px-2.5 py-0.5 rounded-xl border border-gray-900">Midnight Teal</span>
            </div>
        </header>

        <!-- Main Dashboard Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
            
            <!-- COLUMN 1: Speech Composer & TTS Generator (4 Cols) -->
            <div class="lg:col-span-4 space-y-6">
                <!-- TTS Generation Card -->
                <div id="panelTTS" class="glass-panel rounded-2xl p-5 shadow-xl">
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
                            <!-- Microsoft Neural options (filled programmatically in JS to save bytes) -->
                            <select id="ttsVoiceEdge" class="w-full bg-gray-950 border border-gray-800 rounded-xl px-3 py-2 text-xs text-gray-100 focus:outline-none focus:ring-1 focus:ring-violet-500 transition">
                            </select>
                            <!-- Google TTS fallback option (filled programmatically in JS) -->
                            <select id="ttsVoiceGtts" class="hidden w-full bg-gray-950 border border-gray-800 rounded-xl px-3 py-2 text-xs text-gray-100 focus:outline-none focus:ring-1 focus:ring-violet-500 transition">
                            </select>
                        </div>

                        <!-- Emotion / Vocal Tone Selection as custom cards -->
                        <div id="ttsEmotionWrap">
                            <label class="block text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Vocal Emotion Preset</label>
                            <select id="ttsEmotion" onchange="updateEmotionWaveform()" class="w-full bg-gray-950 border border-gray-800 rounded-xl px-3 py-2 text-xs text-gray-100 focus:outline-none focus:ring-1 focus:ring-violet-500 transition mb-3">
                                <option value="neutral" selected>😐 Neutral</option>
                                <option value="cheerful">😄 Cheerful</option>
                                <option value="excited">🤩 Excited</option>
                                <option value="calm">😌 Calm</option>
                                <option value="sad">😢 Sad</option>
                                <option value="serious">🧐 Serious</option>
                                <option value="angry">😠 Angry</option>
                                <option value="whisper">🤫 Whisper</option>
                                <option value="dramatic">🎭 Dramatic</option>
                            </select>
                            
                            <!-- Emotion voice modulator preview visualizer -->
                            <div class="bg-gray-950 rounded-xl p-3 border border-gray-900">
                                <div class="flex items-center justify-between mb-1">
                                    <span class="text-[8px] text-gray-500 uppercase font-bold tracking-wider">Voice Wave Modulation</span>
                                    <span id="emotionWaveformLabel" class="text-[9px] text-teal-400 font-medium">😐 Balanced voice modulation</span>
                                </div>
                                <div id="emotionWaveformBars" class="flex items-center gap-1 justify-center h-8">
                                    <!-- waves generated dynamically -->
                                </div>
                            </div>
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
                <div class="glass-panel rounded-2xl p-5 shadow-xl">
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

            <!-- COLUMN 2: Media Asset Bank & Live Theater (5 Cols) -->
            <div class="lg:col-span-5 space-y-6">
                <!-- Live Theater & Playback Sequencer -->
                <div id="previewTheater" class="glass-panel rounded-2xl p-5 shadow-xl space-y-4">
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
                            <button id="btnPlaySeq" onclick="playLiveSequence()" class="px-3 py-2 bg-rose-600 hover:bg-rose-500 text-white font-bold rounded-xl transition flex items-center gap-1 text-[10px] active:scale-[0.98]">
                                <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd"></path></svg>
                                <span>Play Sequence</span>
                            </button>
                            <button id="btnStopSeq" onclick="stopLiveSequence()" class="px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-255 font-bold rounded-xl transition flex items-center gap-1 text-[10px] active:scale-[0.98]">
                                <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"></path></svg>
                                <span>Stop</span>
                            </button>
                        </div>
                        <div class="text-[10px] text-gray-500 font-mono flex items-center gap-2">
                            <span class="truncate" id="seqDurationVal">0.0s</span>
                        </div>
                    </div>
                    
                    <audio id="timelinePreviewAudio" class="hidden"></audio>
                </div>

                <!-- Media Importer and Gallery -->
                <div id="panelImport" class="glass-panel rounded-2xl p-5 shadow-xl">
                    <div class="grid grid-cols-2 gap-4">
                        <!-- PC Drag & Drop -->
                        <div id="dropZone" class="border border-dashed border-gray-800 hover:border-teal-500/50 rounded-2xl p-4 text-center transition cursor-pointer bg-gray-950/40 relative">
                            <input type="file" id="fileInput" class="hidden" accept="image/*,video/*,audio/*" onchange="handleFileSelect(event)">
                            <svg class="w-6 h-6 text-gray-500 mx-auto mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
                            <p class="text-[10px] text-gray-300 font-medium">Upload File</p>
                            <div id="uploadSpinner" class="hidden absolute inset-0 bg-gray-950/80 rounded-2xl flex items-center justify-center flex-col gap-1.5">
                                <div class="w-4 h-4 border-2 border-teal-500/30 border-t-teal-500 rounded-full animate-spin"></div>
                                <span class="text-[8px] text-teal-400 font-semibold">Uploading...</span>
                            </div>
                        </div>
                        
                        <!-- YT Url Fetch -->
                        <div class="flex flex-col justify-center">
                            <span class="block text-[8px] font-extrabold text-gray-500 uppercase tracking-widest mb-1.5">Fetch Link (yt-dlp)</span>
                            <div class="flex gap-1.5">
                                <input type="url" id="ytUrl" placeholder="Youtube URL..." class="flex-1 bg-gray-950 border border-gray-800 rounded-xl px-2.5 py-1.5 text-[10px] text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500">
                                <button onclick="fetchYtUrl()" class="px-2.5 bg-gray-800 hover:bg-gray-700 text-[10px] text-gray-200 rounded-xl border border-gray-700 active:scale-95 transition flex items-center gap-1">
                                    <span>Fetch</span>
                                    <div id="ytSpinner" class="hidden w-2.5 h-2.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Asset Library Inventory Gallery -->
                <div class="glass-panel rounded-2xl p-5 shadow-xl">
                    <div class="flex justify-between items-center mb-3">
                        <h2 class="text-xs font-extrabold uppercase tracking-widest text-gray-400">Workspace Assets</h2>
                        <!-- Tabs -->
                        <div class="flex gap-0.5 bg-gray-950 p-0.5 rounded-lg border border-gray-900">
                            <button id="tabAll" onclick="filterGallery('all')" class="px-2 py-0.5 text-[8px] font-bold bg-gray-900 text-teal-400 rounded">All</button>
                            <button id="tabVideo" onclick="filterGallery('video')" class="px-2 py-0.5 text-[8px] font-bold text-gray-500 rounded">Video</button>
                            <button id="tabImage" onclick="filterGallery('image')" class="px-2 py-0.5 text-[8px] font-bold text-gray-500 rounded">Image</button>
                            <button id="tabAudio" onclick="filterGallery('audio')" class="px-2 py-0.5 text-[8px] font-bold text-gray-500 rounded">Audio</button>
                        </div>
                    </div>
                    <div id="galleryList" class="space-y-2 max-h-[200px] overflow-y-auto pr-1">
                        <!-- empty state -->
                        <div class="text-center py-6 text-xs text-gray-600">No media assets in workspace library.</div>
                    </div>
                </div>
            </div>

            <!-- COLUMN 3: Clip Properties Inspector Panel (3 Cols) -->
            <div class="lg:col-span-3">
                <div class="glass-panel rounded-2xl p-5 shadow-xl h-full flex flex-col min-h-[300px]">
                    <h2 class="text-sm font-bold flex items-center gap-1.5 text-teal-400 border-b border-gray-900 pb-2.5 mb-3">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/></svg>
                        ⚙️ Clip Properties Inspector
                    </h2>
                    
                    <div id="inspectorPanelContent" class="flex-grow flex flex-col justify-center">
                        <div class="text-center py-12 px-4 text-gray-500">
                            <div class="text-4xl mb-3">⚙️</div>
                            <h4 class="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">No Clip Selected</h4>
                            <p class="text-[11px] text-gray-600 max-w-[180px] mx-auto">Click a clip on the horizontal tracks below to view and edit properties, speeds, effects, captions, and color grades.</p>
                        </div>
                    </div>
                </div>
            </div>

        </div> <!-- End of Top row Grid -->

        <!-- FULL WIDTH BOTTOM SECTION: HORIZONTAL MULTI-TRACK TIMELINE -->
        <div class="grid grid-cols-1 mb-6">
            <div class="glass-panel rounded-2xl p-5 shadow-xl">
                <div class="flex justify-between items-center mb-3 border-b border-gray-900 pb-2.5">
                    <div class="flex items-center gap-3">
                        <h2 class="text-sm font-bold flex items-center gap-2 text-teal-400">
                            <svg class="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                            Sequence Timeline Tracks (CapCut Style)
                        </h2>
                    </div>
                    <div class="flex items-center gap-4">
                        <button onclick="clearTimeline()" class="text-[10px] font-bold text-gray-500 hover:text-red-400 uppercase tracking-wider transition">✕ Clear Sequence</button>
                    </div>
                </div>

                <!-- Master Audio Soundtrack Bar & Settings -->
                <div class="grid grid-cols-1 md:grid-cols-12 gap-4 mb-4 bg-gray-950/80 p-3.5 rounded-2xl border border-gray-900 text-xs">
                    <div class="md:col-span-6 space-y-1.5">
                        <label class="block text-[9px] font-extrabold text-gray-400 uppercase tracking-widest">Master Background Audio Soundtrack</label>
                        <select id="masterAudio" onchange="renderTimeline()" class="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-gray-200 focus:outline-none">
                            <option value="">-- No Soundtrack (Silent) --</option>
                        </select>
                    </div>
                    <div class="md:col-span-6 flex flex-wrap gap-x-4 gap-y-2 items-center justify-start md:justify-end pt-4">
                        <label class="flex items-center gap-1.5 cursor-pointer text-[10px] font-medium text-gray-400">
                            <input type="checkbox" id="loopAudio" class="rounded border-gray-800 bg-gray-900 text-teal-500 focus:ring-0">
                            Loop Audio
                        </label>
                        <label class="flex items-center gap-1.5 cursor-pointer text-[10px] font-medium text-gray-400">
                            <input type="checkbox" id="matchAudio" class="rounded border-gray-800 bg-gray-900 text-teal-500 focus:ring-0">
                            Fit Clip Length
                        </label>
                        <label class="flex items-center gap-1.5 cursor-pointer text-[10px] font-medium text-gray-400">
                            <input type="checkbox" id="crossfadeTransitions" class="rounded border-gray-800 bg-gray-900 text-teal-500 focus:ring-0">
                            Crossfade Clips
                        </label>
                        <select id="crossfadeStyle" class="bg-slate-900 border border-slate-800 rounded-lg px-2 py-1 text-[10px] text-gray-300 focus:outline-none">
                            <option value="fade" selected>Dissolve</option>
                            <option value="dissolve">Crossfade</option>
                            <option value="wipeleft">Wipe Left</option>
                            <option value="wiperight">Wipe Right</option>
                            <option value="slideleft">Slide Left</option>
                            <option value="slideright">Slide Right</option>
                        </select>
                    </div>
                </div>

                <!-- CapCut-style Timeline Ruler & Playhead Track -->
                <div class="bg-gray-950 border border-gray-900 rounded-xl p-2.5 mb-3.5">
                    <div class="flex items-center justify-between mb-1 text-[9px] font-extrabold uppercase tracking-widest text-gray-500">
                        <span class="flex items-center gap-1 text-teal-400">
                            <span class="w-1.5 h-1.5 rounded-full bg-teal-400"></span> Playhead: <span id="rulerCurrentTime" class="mono font-mono">00:00</span>
                        </span>
                        <span>Total: <span id="rulerTotalTime" class="mono font-mono">00:00</span></span>
                    </div>
                    <div id="timelineRuler" class="relative h-9 rounded-lg bg-gray-900/40 overflow-hidden border border-gray-900">
                        <!-- tick ruler segments -->
                    </div>
                </div>

                <!-- Pro Horizontal Multi-Track container -->
                <div id="timelineList" class="space-y-3 mb-4">
                    <!-- Dynamic horizontal tracks (Visual clips, text, effects, audio tracks) -->
                    <div class="text-center py-10 text-xs text-gray-500 border border-dashed border-gray-800 rounded-xl bg-gray-950/20">
                        Drag or click library assets with "+" to populate the chronological multi-track timeline below!
                    </div>
                </div>

                <!-- Export Parameter Selects and Render HD Export -->
                <div class="flex flex-col md:flex-row gap-4 items-center justify-between pt-4 border-t border-gray-900 text-xs">
                    <div class="flex gap-4 w-full md:w-auto">
                        <div class="flex-grow md:flex-initial">
                            <label class="block text-[8px] font-extrabold text-gray-500 uppercase tracking-widest mb-1">Canvas Aspect Format</label>
                            <select id="canvasFormat" class="bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-gray-200 focus:outline-none">
                                <option value="9:16">Portrait 9:16 (Shorts/TikTok)</option>
                                <option value="16:9" selected>Landscape 16:9 (YouTube/PC)</option>
                            </select>
                        </div>
                        <div class="flex-grow md:flex-initial">
                            <label class="block text-[8px] font-extrabold text-gray-500 uppercase tracking-widest mb-1">Export Render Quality</label>
                            <select id="exportQuality" class="bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-gray-200 focus:outline-none">
                                <option value="720p">720p HD</option>
                                <option value="1080p" selected>1080p Full HD</option>
                                <option value="4k">4K Ultra HD (Cinematic)</option>
                            </select>
                        </div>
                    </div>
                    
                    <button id="btnExportVideo" onclick="exportComposition()" class="w-full md:w-56 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold py-2.5 px-4 rounded-xl text-xs active:scale-[0.97] transition flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/20">
                        <svg class="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                        <span>Render HD Export</span>
                    </button>
                </div>
                
                <!-- CapCut-style Effects Selection List (hidden since we upgraded) -->
                <div id="panelEffectsGrid" class="hidden">
                    <div id="fxTileGrid"></div>
                </div>
            </div>

            <!-- Export Progress Card -->
            <div id="exportProgressCard" class="hidden bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-xl space-y-3 mt-4">
                <div class="flex justify-between items-center text-xs">
                    <span class="font-bold text-emerald-400 flex items-center gap-1.5">
                        <span class="w-2 h-2 bg-emerald-500 rounded-full animate-ping"></span>
                        Exporting Video Composition...
                    </span>
                    <span id="exportProgressPct" class="font-mono text-gray-400">0%</span>
                </div>
                <div class="w-full bg-gray-950 h-2.5 rounded-full overflow-hidden border border-gray-800">
                    <div id="exportProgressBar" class="bg-gradient-to-r from-emerald-500 to-teal-400 h-full w-[0%] transition-all duration-300"></div>
                </div>
                <p id="exportStage" class="text-[10px] text-gray-400 leading-relaxed italic">Initiating rendering threads...</p>
            </div>

            <!-- Completed Exports / Library -->
            <div class="glass-panel rounded-2xl p-5 shadow-xl mt-4">
                <h2 class="text-sm font-bold mb-3 text-gray-300">Compiled Downloads Library</h2>
                <div id="exportsList" class="space-y-3 max-h-[180px] overflow-y-auto pr-1">
                    <!-- empty state -->
                    <div class="text-center py-6 text-xs text-gray-600">No exports compiled yet. Select a timeline sequence to start.</div>
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
        let selectedClipId = null;

        // Live Sequencer State
        let sequenceTimer = null;
        let currentSeqIndex = 0;
        let isSequencePlaying = false;

        // Premium Voices configurations
        const EDGE_VOICES = [
            { value: "en-US-AriaNeural", text: "🇺🇸 English (US) - Female (Aria) - Premium Realistic" },
            { value: "en-US-JennyNeural", text: "🇺🇸 English (US) - Female (Jenny) - Warm Conversational" },
            { value: "en-US-EmmaNeural", text: "🇺🇸 English (US) - Female (Emma) - Narrative Storyteller" },
            { value: "en-US-MichelleNeural", text: "🇺🇸 English (US) - Female (Michelle) - Corporate/News" },
            { value: "en-US-GuyNeural", text: "🇺🇸 English (US) - Male (Guy) - Deep Cinematic" },
            { value: "en-US-BrianNeural", text: "🇺🇸 English (US) - Male (Brian) - Friendly" },
            { value: "en-US-SteffanNeural", text: "🇺🇸 English (US) - Male (Steffan) - Narrative" },
            { value: "en-GB-SoniaNeural", text: "🇬🇧 English (UK) - Female (Sonia) - Professional" },
            { value: "en-GB-LibbyNeural", text: "🇬🇧 English (UK) - Female (Libby) - Warm Voice" },
            { value: "en-GB-RyanNeural", text: "🇬🇧 English (UK) - Male (Ryan) - Clear RP Accent" },
            { value: "en-GB-ThomasNeural", text: "🇬🇧 English (UK) - Male (Thomas) - Narrative" },
            { value: "en-IN-NeerjaNeural", text: "🇮🇳 English (India) - Female (Neerja) - Authentic Voice" },
            { value: "en-IN-AaravNeural", text: "🇮🇳 English (India) - Male (Aarav)" },
            { value: "hi-IN-MadhuramNeural", text: "🇮🇳 Hindi (India) - Female (Madhuram) - Deeply Expressive" },
            { value: "hi-IN-KaranNeural", text: "🇮🇳 Hindi (India) - Male (Karan) - Smooth" },
            { value: "es-ES-ElviraNeural", text: "🇪🇸 Spanish (Spain) - Female (Elvira)" },
            { value: "es-MX-DaliaNeural", text: "🇲🇽 Spanish (Mexico) - Female (Dalia)" },
            { value: "es-ES-AlvaroNeural", text: "🇪🇸 Spanish (Spain) - Male (Alvaro)" },
            { value: "fr-FR-DeniseNeural", text: "🇫🇷 French (France) - Female (Denise)" },
            { value: "fr-FR-HenriNeural", text: "🇫🇷 French (France) - Male (Henri)" },
            { value: "de-DE-KatjaNeural", text: "🇩🇪 German (Germany) - Female (Katja)" },
            { value: "de-DE-ConradNeural", text: "🇩🇪 German (Germany) - Male (Conrad)" },
            { value: "ur-PK-UzmaNeural", text: "🇵🇰 Urdu (Pakistan) - Female (Uzma)" },
            { value: "ur-PK-AsadNeural", text: "🇵🇰 Urdu (Pakistan) - Male (Asad)" }
        ];

        const GTTS_VOICES = [
            { value: "en", text: "🇺🇸 English (US) - Female (Google Standard)" },
            { value: "en-uk", text: "🇬🇧 English (UK) - Female (Google Standard)" },
            { value: "en-au", text: "🇦🇺 English (Australia) - Female" },
            { value: "en-in", text: "🇮🇳 English (India) - Female" },
            { value: "hi", text: "🇮🇳 Hindi (India) - Female" },
            { value: "es", text: "🇪🇸 Spanish (Spain) - Female" },
            { value: "fr", text: "🇫🇷 French (France) - Female" },
            { value: "de", text: "🇩🇪 German (Germany) - Female" },
            { value: "ur", text: "🇵🇰 Urdu (Pakistan) - Female" }
        ];

        // On Load Page
        window.addEventListener('DOMContentLoaded', () => {
            populateVoiceSelects();
            fetchMediaCatalog();
            updateEmotionWaveform();
            
            // Setup Drag and Drop events for local asset uploader
            const dropZone = document.getElementById('dropZone');
            
            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.classList.add('border-teal-500', 'bg-teal-950/10');
            });
            
            dropZone.addEventListener('dragleave', () => {
                dropZone.classList.remove('border-teal-500', 'bg-teal-950/10');
            });
            
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('border-teal-500', 'bg-teal-950/10');
                if (e.dataTransfer.files.length > 0) {
                    uploadFile(e.dataTransfer.files[0]);
                }
            });

            dropZone.addEventListener('click', () => {
                document.getElementById('fileInput').click();
            });

            // Close workspace dropdowns on clicking outside
            document.addEventListener('click', (e) => {
                const themeContainer = document.getElementById('themeDropdownContainer');
                const themeMenu = document.getElementById('themeDropdownMenu');
                if (themeContainer && !themeContainer.contains(e.target)) {
                    themeMenu.classList.add('hidden');
                }
            });
        });

        // Populate programmatically to save file bytes
        function populateVoiceSelects() {
            const edgeSel = document.getElementById('ttsVoiceEdge');
            const gttsSel = document.getElementById('ttsVoiceGtts');
            
            edgeSel.innerHTML = EDGE_VOICES.map(v => `<option value="${v.value}">${v.text}</option>`).join('');
            gttsSel.innerHTML = GTTS_VOICES.map(v => `<option value="${v.value}">${v.text}</option>`).join('');
        }

        // Animated Emotion modulation preview
        function updateEmotionWaveform() {
            const emotion = document.getElementById('ttsEmotion').value;
            const container = document.getElementById('emotionWaveformBars');
            const label = document.getElementById('emotionWaveformLabel');
            if (!container) return;

            let barCount = 18;
            let speedClass = "animate-bounce";
            let heights = [3, 5, 2, 6, 4, 1, 7, 3, 5, 2, 6, 4, 1, 7, 3, 5, 2, 4];
            let hue = "bg-teal-400";

            switch (emotion) {
                case 'cheerful':
                    label.innerHTML = "😄 Cheerful: Elevated pitch & energetic rhythm";
                    heights = [6, 8, 5, 7, 8, 4, 7, 6, 8, 5, 7, 8, 4, 7, 6, 8, 5, 7];
                    hue = "bg-emerald-400";
                    break;
                case 'excited':
                    label.innerHTML = "🤩 Excited: Dynamic peaks & speed boost";
                    heights = [8, 10, 7, 9, 10, 6, 9, 8, 10, 7, 9, 10, 6, 9, 8, 10, 7, 9];
                    hue = "bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.6)]";
                    break;
                case 'calm':
                    label.innerHTML = "😌 Calm: Low frequency, warm soothing tones";
                    heights = [2, 3, 2, 4, 3, 2, 3, 2, 3, 2, 4, 3, 2, 3, 2, 3, 2, 2];
                    hue = "bg-sky-400";
                    break;
                case 'sad':
                    label.innerHTML = "😢 Sad: Melancholic decay & slow trailing curves";
                    heights = [2, 1, 3, 2, 1, 3, 2, 1, 3, 2, 1, 3, 2, 1, 3, 2, 1, 1];
                    hue = "bg-violet-400";
                    break;
                case 'serious':
                    label.innerHTML = "🧐 Serious: Steady, flat clinical frequency";
                    heights = [4, 4, 5, 4, 4, 5, 4, 4, 5, 4, 4, 5, 4, 4, 5, 4, 4, 4];
                    hue = "bg-indigo-400";
                    break;
                case 'angry':
                    label.innerHTML = "😠 Angry: Harsh saturation, compressed acoustic waves";
                    heights = [7, 9, 8, 9, 8, 7, 9, 8, 9, 8, 7, 9, 8, 9, 8, 7, 9, 8];
                    hue = "bg-amber-500";
                    break;
                case 'whisper':
                    label.innerHTML = "🤫 Whisper: Soft breathy voice, minimal amplitude";
                    heights = [1, 2, 1, 2, 1, 1, 2, 1, 2, 1, 1, 2, 1, 2, 1, 1, 2, 1];
                    hue = "bg-teal-200/50";
                    break;
                case 'dramatic':
                    label.innerHTML = "🎭 Dramatic: Sweeping delays & high theatrical dynamics";
                    heights = [3, 9, 2, 8, 4, 10, 1, 9, 3, 8, 2, 10, 4, 9, 1, 8, 3, 5];
                    hue = "bg-fuchsia-400 shadow-[0_0_8px_rgba(232,121,249,0.5)]";
                    break;
                default:
                    label.innerHTML = "😐 Neutral: Default standard narrative curves";
                    hue = "bg-teal-400";
            }

            container.innerHTML = heights.map((h, i) => {
                const delay = (i * 0.08).toFixed(2);
                const heightPx = h * 3;
                return `<span class="w-1 rounded-full ${hue} ${speedClass}" style="height:${heightPx}px; animation-delay:${delay}s"></span>`;
            }).join('');
        }

        // Toggle voices menu based on engine choice
        function toggleEngineVoices() {
            const engine = document.getElementById('ttsEngine').value;
            const edgeVoices = document.getElementById('ttsVoiceEdge');
            const gttsVoices = document.getElementById('ttsVoiceGtts');
            const emotionWrap = document.getElementById('ttsEmotionWrap');
            if (engine === 'edge') {
                edgeVoices.classList.remove('hidden');
                gttsVoices.classList.add('hidden');
                emotionWrap.classList.remove('hidden');
            } else {
                edgeVoices.classList.add('hidden');
                gttsVoices.classList.remove('hidden');
                emotionWrap.classList.add('hidden');
            }
        }

        // Fetch Workspace Catalog from API
        async function fetchMediaCatalog() {
            try {
                const res = await fetch('/api/media');
                const data = await res.json();
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
            const emotion = document.getElementById('ttsEmotion').value;

            if (!text) return alert("Speech script transcription can't be empty.");

            const spinner = document.getElementById('ttsSpinner');
            spinner.classList.remove('hidden');

            try {
                const res = await fetch('/api/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text, engine: engine, voice_or_lang: voice, emotion: emotion })
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
                if (!tab) return;
                if (tabId === 'tab' + type.charAt(0).toUpperCase() + type.slice(1)) {
                    tab.classList.add('bg-gray-900', 'text-teal-400');
                    tab.classList.remove('text-gray-500');
                } else {
                    tab.classList.remove('bg-gray-900', 'text-teal-400');
                    tab.classList.add('text-gray-500');
                }
            });
            renderGallery();
        }

        function renderGallery() {
            const list = document.getElementById('galleryList');
            if (!list) return;

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
                    <div class="bg-gray-950/70 border border-gray-900 rounded-xl p-3 flex flex-col justify-between gap-3 hover:border-gray-800 transition">
                        <div class="flex items-center gap-3">
                            <div class="w-10 h-10 bg-gray-900 rounded-lg flex items-center justify-center border border-gray-800">
                                ${item.type === 'image' ? `
                                    <img src="${item.url}" class="w-full h-full object-cover rounded-lg" />
                                ` : (item.type === 'video' ? `
                                    <svg class="w-5 h-5 text-indigo-400" fill="currentColor" viewBox="0 0 20 20"><path d="M2 6a2 2 0 012-2h12a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"></path></svg>
                                ` : `
                                    <svg class="w-5 h-5 text-emerald-400" fill="currentColor" viewBox="0 0 20 20"><path d="M18 3a1 1 0 00-1.196-.98l-10 2A1 1 0 006 5v9.114A4.369 4.369 0 005 14c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V7.82l8-1.6v5.894A4.369 4.369 0 0015 12c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V3z"></path></svg>
                                `)}
                            </div>
                            <div class="min-w-0 flex-1">
                                <h4 class="text-[11px] font-bold text-gray-200 truncate break-all" title="${item.filename}">
                                    ${item.filename.split('_').slice(1).join('_') || item.filename}
                                </h4>
                                <span class="px-1.5 py-0.5 rounded text-[7px] font-extrabold ${badgeColor} uppercase tracking-wider mt-0.5 inline-block">
                                    ${displayType}
                                </span>
                            </div>
                        </div>

                        <div class="flex justify-between items-center gap-2 pt-2 border-t border-gray-900">
                            <div class="flex gap-2">
                                <button onclick="deleteAsset('${item.filename}', 'uploads')" class="text-[9px] text-gray-500 hover:text-rose-400 transition flex items-center gap-0.5">
                                    Delete
                                </button>
                                <button onclick="previewAsset('${item.url}', '${item.type}', '${item.filename}')" class="text-[9px] text-violet-400 hover:text-violet-300 font-bold transition flex items-center gap-0.5">
                                    👁️ Preview
                                </button>
                            </div>
                            <div class="flex gap-1.5">
                                ${item.type !== 'audio' ? `
                                    <button onclick="addToTimeline('${item.filename}', '${item.type}')" class="px-2 py-1 bg-teal-600 hover:bg-teal-500 text-white font-extrabold rounded text-[9px] active:scale-95 transition">
                                        + Track
                                    </button>
                                ` : `
                                    <button onclick="setAsMasterAudio('${item.filename}', 'upload')" class="px-2 py-1 bg-violet-600 hover:bg-violet-500 text-white font-extrabold rounded text-[9px] active:scale-95 transition">
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
            if (!list) return;
            document.getElementById('ttsCount').textContent = availableMedia.tts.length;

            if (availableMedia.tts.length === 0) {
                list.innerHTML = `<div class="text-center py-6 text-xs text-gray-600">No tracks synthesized yet.</div>`;
                return;
            }

            list.innerHTML = availableMedia.tts.map((item, idx) => `
                <div class="bg-gray-950/70 border border-gray-900 rounded-xl p-3 space-y-2">
                    <div class="flex items-center justify-between gap-2">
                        <span class="text-[9px] font-mono text-gray-400">Speech Clip #${idx + 1}</span>
                        <button onclick="deleteAsset('${item.filename}', 'tts_audio')" class="text-[8px] text-gray-500 hover:text-red-400">Delete</button>
                    </div>
                    <audio src="${item.url}" controls class="w-full h-7 rounded-lg bg-gray-900 opacity-85 hover:opacity-100 transition"></audio>
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
            if (!list) return;
            if (availableMedia.exports.length === 0) {
                list.innerHTML = `<div class="text-center py-6 text-xs text-gray-650">No exports compiled yet. Select a timeline sequence to start.</div>`;
                return;
            }

            list.innerHTML = availableMedia.exports.map((item, idx) => `
                <div class="bg-gray-950/70 border border-gray-900 rounded-xl p-3 flex justify-between items-center gap-2">
                    <div class="min-w-0 flex-1">
                        <span class="text-[9px] text-gray-500 font-bold uppercase tracking-wider">Video MP4 HD</span>
                        <h4 class="text-xs font-semibold text-gray-200 truncate">${item.filename}</h4>
                    </div>
                    <div class="flex gap-2">
                        <a href="${item.url}" download class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded text-[9px] active:scale-95 transition">
                            Download
                        </a>
                        <button onclick="deleteAsset('${item.filename}', 'exports')" class="px-1.5 py-1 text-gray-500 hover:text-red-400 rounded text-[9px] transition">
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
            if (!select) return;
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
            if (!select) return;
            const targetJSON = JSON.stringify({ filename: filename, source: source === 'tts' ? 'tts' : 'uploads' });
            select.value = targetJSON;
            renderTimeline();
        }

        // ================= BACKGROUND WORKSPACE THEME CHANGER =================

        function toggleThemeDropdown(event) {
            event.stopPropagation();
            const menu = document.getElementById('themeDropdownMenu');
            menu.classList.toggle('hidden');
        }

        function selectTheme(className, label, colorHex) {
            // Remove current theme classes
            const themes = ['theme-purple', 'theme-sunset', 'theme-ocean', 'theme-emerald', 'theme-crimson', 'theme-gold', 'theme-mono'];
            themes.forEach(t => document.body.classList.remove(t));
            
            // Add selected
            if (className) {
                document.body.classList.add(className);
            }
            
            // Update button UI
            document.getElementById('themeLabel').textContent = label;
            document.getElementById('activeThemeDot').style.backgroundColor = colorHex;
            document.getElementById('activeThemeDot').style.boxShadow = `0 0 10px ${colorHex}`;
            
            // Hide dropdown
            document.getElementById('themeDropdownMenu').classList.add('hidden');
        }

        // ================= TIMELINE TRACK OPERATIONS =================

        let defaultEffect = 'none';

        function addToTimeline(filename, type) {
            const newId = uuid();
            timeline.push({
                id: newId,
                filename: filename,
                type: type,
                duration: 5, // Default 5s
                effect: defaultEffect,
                speed: 1,
                brightness: 0,
                contrast: 1,
                saturation: 1,
                text_overlay: 'Awesome transition caption overlay',
                text_position: 'bottom'
            });
            selectedClipId = newId; // Select the newly added clip
            renderTimeline();
        }

        function uuid() {
            return Math.random().toString(36).substring(2, 9);
        }

        function selectClipForInspector(id) {
            selectedClipId = id;
            renderTimeline();
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

        function removeTimelineItem(id) {
            const index = timeline.findIndex(x => x.id === id);
            if (index !== -1) {
                timeline.splice(index, 1);
                if (selectedClipId === id) {
                    selectedClipId = timeline.length > 0 ? timeline[0].id : null;
                }
                renderTimeline();
            }
        }

        function clearTimeline() {
            timeline = [];
            selectedClipId = null;
            renderTimeline();
        }

        function updateTimelineItemProp(id, prop, val) {
            const index = timeline.findIndex(x => x.id === id);
            if (index !== -1) {
                timeline[index][prop] = val;
                if (prop === 'duration' || prop === 'speed') {
                    renderTimelineRuler();
                }
                // Refresh UI components asynchronously to maintain smooth slider focus
                renderTimelineTracksOnly();
                renderInspectorOnly();
            }
        }

        // Drag and drop sorting on Horizontal Tracks
        function onDragStart(e, idx) {
            dragSrcIndex = idx;
            e.dataTransfer.effectAllowed = 'move';
            e.currentTarget.classList.add('opacity-40', 'border-teal-500');
        }

        function onDragOver(e) {
            if (e.preventDefault) {
                e.preventDefault();
            }
            return false;
        }

        function onDrop(e, targetIdx) {
            e.stopPropagation();
            if (dragSrcIndex !== null && dragSrcIndex !== targetIdx) {
                const dragItem = timeline[dragSrcIndex];
                timeline.splice(dragSrcIndex, 1);
                timeline.splice(targetIdx, 0, dragItem);
                renderTimeline();
            }
            dragSrcIndex = null;
        }

        function onDragEnd(e) {
            e.currentTarget.classList.remove('opacity-40', 'border-teal-500');
        }

        function renderTimeline() {
            renderTimelineTracksOnly();
            renderTimelineRuler();
            renderInspectorOnly();
        }

        function renderInspectorOnly() {
            const inspector = document.getElementById('inspectorPanelContent');
            if (!inspector) return;

            if (timeline.length === 0 || !selectedClipId) {
                inspector.innerHTML = `
                    <div class="text-center py-12 px-4 text-gray-500">
                        <div class="text-4xl mb-3">⚙️</div>
                        <h4 class="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">No Clip Selected</h4>
                        <p class="text-[11px] text-gray-600 max-w-[180px] mx-auto">Click a clip on the horizontal tracks below to view and edit properties, speeds, effects, captions, and color grades.</p>
                    </div>`;
                return;
            }

            const item = timeline.find(x => x.id === selectedClipId);
            if (!item) {
                inspector.innerHTML = `
                    <div class="text-center py-12 px-4 text-gray-500">
                        <div class="text-4xl mb-3">⚙️</div>
                        <h4 class="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">No Clip Selected</h4>
                    </div>`;
                return;
            }

            const cleanFilename = item.filename.split('_').slice(1).join('_') || item.filename;

            inspector.innerHTML = `
                <div class="space-y-4 flex flex-col justify-start h-full">
                    <!-- Miniature visual card -->
                    <div class="bg-gray-950/90 rounded-2xl p-3 border border-gray-900">
                        <div class="flex items-center gap-2.5 mb-2.5">
                            <span class="w-2.5 h-2.5 rounded-full ${item.type === 'video' ? 'bg-indigo-400' : 'bg-amber-400'}"></span>
                            <span class="text-[10px] uppercase font-bold text-gray-400 tracking-wider">${item.type} Clip</span>
                        </div>
                        <p class="text-xs font-bold text-gray-200 truncate mb-2" title="${item.filename}">${cleanFilename}</p>
                        
                        <div class="flex gap-2 justify-between">
                            <button onclick="previewAsset('/api/files/uploads/${item.filename}', '${item.type}', '${item.filename}')" class="flex-1 py-1.5 bg-slate-900 border border-slate-800 text-[10px] font-bold text-violet-400 rounded-xl hover:bg-slate-800 transition">
                                👁️ Play Clip
                            </button>
                            <button onclick="removeTimelineItem('${item.id}')" class="px-3 py-1.5 bg-red-950/50 border border-red-900/30 text-[10px] font-bold text-red-400 rounded-xl hover:bg-red-900 hover:text-white transition">
                                Delete
                            </button>
                        </div>
                    </div>

                    <!-- Speed & Duration Parameters -->
                    <div class="space-y-3 pt-1 border-t border-gray-900">
                        <div class="grid grid-cols-2 gap-2">
                            <div>
                                <label class="block text-[8px] text-gray-500 uppercase font-extrabold tracking-wider mb-1">Duration (s)</label>
                                <input type="number" min="1" max="120" value="${item.duration}" 
                                       oninput="updateTimelineItemProp('${item.id}', 'duration', this.value)" 
                                       class="w-full bg-gray-950 border border-gray-850 rounded-lg px-2 py-1 text-xs text-white focus:outline-none">
                            </div>
                            <div>
                                <label class="block text-[8px] text-gray-500 uppercase font-extrabold tracking-wider mb-1">Speed Multiplier</label>
                                <input type="number" step="0.05" min="0.25" max="3" value="${item.speed ?? 1}"
                                       oninput="updateTimelineItemProp('${item.id}', 'speed', this.value)"
                                       class="w-full bg-gray-950 border border-gray-850 rounded-lg px-2 py-1 text-xs text-white focus:outline-none">
                            </div>
                        </div>

                        <div>
                            <label class="block text-[8px] text-gray-500 uppercase font-extrabold tracking-wider mb-1">Cinematic Filter Effect</label>
                            <select onchange="updateTimelineItemProp('${item.id}', 'effect', this.value)" 
                                    class="w-full bg-gray-950 border border-gray-850 rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none">
                                <option value="none" ${item.effect === 'none' ? 'selected' : ''}>🚫 None</option>
                                <option value="fade" ${item.effect === 'fade' ? 'selected' : ''}>🌅 Dissolve Transition</option>
                                <option value="rotate" ${item.effect === 'rotate' ? 'selected' : ''}>🔄 Rotate Frame</option>
                                <option value="kenburns" ${item.effect === 'kenburns' ? 'selected' : ''}>🎬 Ken Burns Zoom</option>
                                <option value="zoomin" ${item.effect === 'zoomin' ? 'selected' : ''}>🔍 Zoom In Punch</option>
                                <option value="blur" ${item.effect === 'blur' ? 'selected' : ''}>🌫️ Soft Blur</option>
                                <option value="grayscale" ${item.effect === 'grayscale' ? 'selected' : ''}>⚫ Grayscale Filter</option>
                                <option value="sepia" ${item.effect === 'sepia' ? 'selected' : ''}>🟤 Sepia Tone</option>
                                <option value="vignette" ${item.effect === 'vignette' ? 'selected' : ''}>🌑 Vignette</option>
                                <option value="mirror" ${item.effect === 'mirror' ? 'selected' : ''}>🪞 Mirror Flip</option>
                                <option value="shake" ${item.effect === 'shake' ? 'selected' : ''}>📳 Camera Shake</option>
                                <option value="glitch" ${item.effect === 'glitch' ? 'selected' : ''}>⚡ RGB Glitch</option>
                            </select>
                        </div>
                    </div>

                    <!-- On-Screen Caption Editor -->
                    <div class="space-y-2 pt-1.5 border-t border-gray-900">
                        <label class="block text-[8px] text-gray-500 uppercase font-extrabold tracking-wider">Subtitles Caption overlay</label>
                        <input type="text" maxlength="120" placeholder="Add captions..." value="${item.text_overlay ? item.text_overlay.replace(/"/g, '&quot;') : ''}"
                               oninput="updateTimelineItemProp('${item.id}', 'text_overlay', this.value)"
                               class="w-full bg-gray-950 border border-gray-850 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none placeholder-gray-700">
                        
                        <div class="flex items-center justify-between text-[9px] text-gray-400">
                            <span>Text Alignment</span>
                            <select onchange="updateTimelineItemProp('${item.id}', 'text_position', this.value)"
                                    class="bg-gray-950 border border-gray-850 rounded-md px-1.5 py-0.5 text-[9px]">
                                <option value="top" ${item.text_position === 'top' ? 'selected' : ''}>Top</option>
                                <option value="center" ${item.text_position === 'center' ? 'selected' : ''}>Center</option>
                                <option value="bottom" ${(item.text_position || 'bottom') === 'bottom' ? 'selected' : ''}>Bottom</option>
                            </select>
                        </div>
                    </div>

                    <!-- Cinematic Color Grading Sliders -->
                    <div class="space-y-2.5 pt-2 border-t border-gray-900 flex-grow">
                        <span class="block text-[8px] text-gray-500 uppercase font-extrabold tracking-wider">Cinematic Color Grading</span>
                        
                        <div class="space-y-1">
                            <div class="flex justify-between text-[9px] text-gray-400">
                                <span>Brightness</span>
                                <span class="mono">${item.brightness ?? 0}</span>
                            </div>
                            <input type="range" min="-1" max="1" step="0.05" value="${item.brightness ?? 0}"
                                   oninput="updateTimelineItemProp('${item.id}', 'brightness', parseFloat(this.value))"
                                   class="w-full accent-teal-400 cursor-pointer h-1 bg-gray-900 rounded-lg appearance-none">
                        </div>

                        <div class="space-y-1">
                            <div class="flex justify-between text-[9px] text-gray-400">
                                <span>Contrast</span>
                                <span class="mono">${item.contrast ?? 1}x</span>
                            </div>
                            <input type="range" min="0" max="2" step="0.05" value="${item.contrast ?? 1}"
                                   oninput="updateTimelineItemProp('${item.id}', 'contrast', parseFloat(this.value))"
                                   class="w-full accent-teal-400 cursor-pointer h-1 bg-gray-900 rounded-lg appearance-none">
                        </div>

                        <div class="space-y-1">
                            <div class="flex justify-between text-[9px] text-gray-400">
                                <span>Saturation</span>
                                <span class="mono">${item.saturation ?? 1}x</span>
                            </div>
                            <input type="range" min="0" max="3" step="0.05" value="${item.saturation ?? 1}"
                                   oninput="updateTimelineItemProp('${item.id}', 'saturation', parseFloat(this.value))"
                                   class="w-full accent-teal-400 cursor-pointer h-1 bg-gray-900 rounded-lg appearance-none">
                        </div>
                    </div>
                </div>`;
        }

        function renderTimelineTracksOnly() {
            const container = document.getElementById('timelineList');
            if (!container) return;

            if (timeline.length === 0) {
                container.innerHTML = `
                    <div class="text-center py-10 text-xs text-gray-500 border border-dashed border-gray-800 rounded-xl bg-gray-950/20">
                        Drag or click library assets with "+" to populate the chronological timeline below!
                    </div>`;
                return;
            }

            let trackItems = [];
            let totalDur = timeline.reduce((sum, it) => sum + (parseFloat(it.duration) || 5), 0);

            timeline.forEach((item, index) => {
                const cleanName = item.filename.split('_').slice(1).join('_') || item.filename;
                const activeBorder = item.id === selectedClipId 
                    ? 'border-teal-500 ring-2 ring-teal-500/30 bg-teal-950/20' 
                    : 'border-gray-800 bg-gray-950/80 hover:border-gray-700';
                
                const pctWidth = ((parseFloat(item.duration) || 5) / totalDur) * 100;
                
                // Build caption pill inside the clip block
                let captionHTML = '';
                if (item.text_overlay) {
                    captionHTML = `
                        <div class="mt-1.5 text-[8px] font-mono text-violet-300 bg-violet-950/35 border border-violet-800/30 rounded px-1.5 py-0.5 truncate max-w-full" title="Caption: ${item.text_overlay}">
                            💬 "${item.text_overlay}"
                        </div>`;
                } else {
                    captionHTML = `
                        <div class="mt-1.5 text-[8px] text-gray-500 hover:text-teal-400 border border-dashed border-gray-900 rounded px-1.5 py-0.5 text-center italic transition-colors">
                            + Add Caption
                        </div>`;
                }

                // Build FX badge
                let fxHTML = '';
                if (item.effect && item.effect !== 'none') {
                    fxHTML = `
                        <span class="absolute bottom-1 right-1.5 text-[8px] font-bold text-teal-400 bg-teal-950/90 px-1 rounded border border-teal-800/40">⚡ ${item.effect}</span>
                    `;
                }

                // Build Speed badge
                let speedHTML = '';
                if (parseFloat(item.speed) !== 1) {
                    speedHTML = `
                        <span class="absolute bottom-1 left-1.5 text-[7px] font-mono font-bold text-emerald-400 bg-gray-950/90 px-0.5 rounded border border-emerald-900/20">${item.speed}x</span>
                    `;
                }

                trackItems.push(`
                    <div draggable="true" 
                         ondragstart="onDragStart(event, ${index})" 
                         ondragover="onDragOver(event)" 
                         ondrop="onDrop(event, ${index})" 
                         ondragend="onDragEnd(event)"
                         onclick="selectClipForInspector('${item.id}')"
                         style="width: ${pctWidth}%; min-width: 140px;"
                         class="h-24 rounded-2xl border ${activeBorder} p-3 flex flex-col justify-between cursor-pointer transition-all select-none flex-shrink-0 relative overflow-hidden group">
                        
                        <!-- Header with Type & Duration -->
                        <div class="flex items-center justify-between gap-1 border-b border-gray-900/30 pb-1">
                            <span class="text-[8px] font-extrabold uppercase tracking-widest ${item.type === 'video' ? 'text-indigo-400' : 'text-amber-400'} flex items-center gap-1">
                                <span>${item.type === 'video' ? '🎥' : '🖼️'}</span>
                                <span>${item.type}</span>
                            </span>
                            <span class="text-[8px] font-mono text-gray-400 font-bold bg-gray-900/60 px-1 rounded">${item.duration}s</span>
                        </div>
                        
                        <!-- Filename -->
                        <p class="text-[10px] font-bold text-gray-200 truncate mt-1 leading-tight">${cleanName}</p>
                        
                        <!-- Subtitle Area -->
                        ${captionHTML}
                        
                        <!-- Badges -->
                        ${fxHTML}
                        ${speedHTML}
                    </div>
                `);
            });

            // Handle Master Soundtrack
            const audioSelect = document.getElementById('masterAudio');
            let audioTrackHTML = '';
            if (audioSelect && audioSelect.value) {
                let trackName = "Master Background Soundtrack";
                try {
                    const parsed = JSON.parse(audioSelect.value);
                    trackName = parsed.filename.split('_').slice(1).join('_') || parsed.filename;
                } catch(e){}

                audioTrackHTML = `
                    <!-- MASTER BACKGROUND SOUNDTRACK ROW -->
                    <div class="flex items-center gap-3 bg-gray-950/45 p-3 rounded-2xl border border-emerald-950/30 mt-3 animate-fadeIn">
                        <div class="w-16 flex-shrink-0 text-left">
                            <span class="text-[9px] font-extrabold uppercase tracking-widest text-emerald-400 flex items-center gap-1">
                                <span class="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse"></span>
                                Audio
                            </span>
                        </div>
                        <div class="flex-1 overflow-hidden">
                            <div class="w-full bg-gradient-to-r from-emerald-950/25 via-teal-950/35 to-emerald-950/25 h-10 rounded-xl border border-emerald-900/25 flex items-center justify-between px-4 relative">
                                <div class="flex items-center gap-1.5 z-10">
                                    <svg class="w-4 h-4 text-emerald-400 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"></path></svg>
                                    <span class="text-[9px] font-bold text-emerald-200 truncate max-w-[250px]">${trackName}</span>
                                </div>
                                <div class="absolute inset-x-0 bottom-1 flex items-end justify-center h-5 gap-0.5 opacity-20 select-none pointer-events-none">
                                    <span class="w-[2px] h-3 bg-emerald-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></span>
                                    <span class="w-[2px] h-4 bg-emerald-400 rounded-full animate-bounce" style="animation-delay: 0.3s"></span>
                                    <span class="w-[2px] h-2 bg-emerald-400 rounded-full animate-bounce" style="animation-delay: 0.5s"></span>
                                    <span class="w-[2px] h-5 bg-emerald-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></span>
                                    <span class="w-[2px] h-3 bg-emerald-400 rounded-full animate-bounce" style="animation-delay: 0.4s"></span>
                                    <span class="w-[2px] h-1 bg-emerald-400 rounded-full animate-bounce" style="animation-delay: 0.6s"></span>
                                </div>
                                <span class="text-[8px] font-mono font-bold text-emerald-500 z-10">${totalDur.toFixed(1)}s</span>
                            </div>
                        </div>
                    </div>`;
            }

            container.innerHTML = `
                <div class="space-y-3">
                    <!-- UNIFIED TIMELINE SEQUENCE TRACK -->
                    <div class="flex items-center gap-3">
                        <div class="w-16 flex-shrink-0 text-left">
                            <span class="text-[9px] font-extrabold uppercase tracking-widest text-indigo-400 flex items-center gap-1">
                                <span class="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-pulse"></span>
                                Clips
                            </span>
                        </div>
                        <div class="flex-1 bg-gray-950/40 rounded-3xl border border-gray-900/60 p-3 overflow-x-auto">
                            <div class="flex gap-3 w-full">
                                ${trackItems.join('')}
                            </div>
                        </div>
                    </div>

                    ${audioTrackHTML}
                </div>`;
        }

        function formatTimeMMSS(totalSeconds) {
            totalSeconds = Math.max(0, Math.round(totalSeconds || 0));
            const m = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
            const s = (totalSeconds % 60).toString().padStart(2, '0');
            return `${m}:${s}`;
        }

        function renderTimelineRuler(currentSeconds) {
            const ruler = document.getElementById('timelineRuler');
            const totalEl = document.getElementById('rulerTotalTime');
            const curEl = document.getElementById('rulerCurrentTime');
            if (!ruler) return;

            const totalDuration = timeline.reduce((sum, it) => sum + (parseFloat(it.duration) || 5), 0);
            if (totalEl) totalEl.textContent = formatTimeMMSS(totalDuration);
            if (curEl) curEl.textContent = formatTimeMMSS(currentSeconds || 0);

            if (timeline.length === 0 || totalDuration <= 0) {
                ruler.innerHTML = `<div class="flex items-center justify-center w-full h-full text-[9px] text-gray-600">Add clips to see the sequence timeline ticks</div>`;
                return;
            }

            // Build proportional segment blocks with visual tick lines
            let cumulative = 0;
            const segHtml = timeline.map((item, idx) => {
                const dur = parseFloat(item.duration) || 5;
                const widthPct = (dur / totalDuration) * 100;
                const startLabel = formatTimeMMSS(cumulative);
                cumulative += dur;
                const activeColor = item.id === selectedClipId ? 'bg-teal-950/30' : 'bg-gray-900/10';
                
                return `
                    <div onclick="selectClipForInspector('${item.id}')"
                         class="relative h-full ${activeColor} border-r border-gray-800/40 flex items-end justify-between cursor-pointer group" 
                         style="width:${widthPct}%">
                        <!-- tick line markers -->
                        <span class="absolute left-1 top-1 text-[8px] font-mono text-gray-500 font-bold tracking-tight">${startLabel}</span>
                        <div class="flex items-end w-full h-1/2 px-1 gap-1 justify-around select-none">
                            <span class="w-[1px] h-2 bg-gray-800"></span>
                            <span class="w-[1px] h-1 bg-gray-800"></span>
                            <span class="w-[1px] h-1 bg-gray-800"></span>
                            <span class="w-[1px] h-2 bg-gray-800"></span>
                        </div>
                    </div>
                `;
            }).join('');

            // Horizontal visual sliding playhead marker bar!
            const playheadLeft = currentSeconds ? (currentSeconds / totalDuration) * 100 : 0;
            const playheadHTML = `
                <div class="absolute top-0 bottom-0 w-[2px] bg-red-500 z-30 transition-all pointer-events-none" style="left: ${playheadLeft}%">
                    <span class="absolute top-0 -translate-x-1/2 w-2 h-2 rounded-full bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.8)]"></span>
                </div>`;

            ruler.innerHTML = segHtml + playheadHTML;
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
            const crossfade_transitions = document.getElementById('crossfadeTransitions').checked;
            const crossfade_style = document.getElementById('crossfadeStyle').value;

            const format = document.getElementById('canvasFormat').value;
            const quality = document.getElementById('exportQuality').value;

            const payload = {
                timeline: timeline,
                audio_track: audio_track,
                settings: {
                    format: format,
                    quality: quality,
                    loop_audio: loop_audio,
                    match_audio_length: match_audio_length,
                    crossfade_transitions: crossfade_transitions,
                    crossfade_style: crossfade_style,
                    crossfade_duration: 0.6
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
            
            if (audioSelect && audioSelect.value) {
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

            // Update the ruler's current-time readout to match playback position
            const elapsedSoFar = timeline.slice(0, currentSeqIndex).reduce((sum, it) => sum + (parseFloat(it.duration) || 5), 0);
            renderTimelineRuler(elapsedSoFar);
            
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
            selectedClipId = item.id;
            renderTimelineTracksOnly();
            renderInspectorOnly();
            
            // Set timeout for next item
            sequenceTimer = setTimeout(() => {
                currentSeqIndex++;
                playNextTimelineItem();
            }, durationMs);
        }
        
        function stopLiveSequence() {
            isSequencePlaying = false;
            if (sequenceTimer) {
                clearTimeout(sequenceTimer);
                sequenceTimer = null;
            }
            
            // Reset Play button
            const btnPlay = document.getElementById('btnPlaySeq');
            if (btnPlay) {
                btnPlay.classList.remove('bg-emerald-600', 'hover:bg-emerald-500');
                btnPlay.classList.add('bg-rose-600', 'hover:bg-rose-500');
                btnPlay.innerHTML = `
                    <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd"></path></svg>
                    <span>Play Sequence</span>`;
            }
            
            // Stop preview master audio
            const timelineAudio = document.getElementById('timelinePreviewAudio');
            if (timelineAudio) {
                timelineAudio.pause();
                timelineAudio.src = "";
            }
            
            // Stop viewport elements
            const videoEl = document.getElementById('viewportVideo');
            if (videoEl) {
                videoEl.pause();
                videoEl.src = "";
                videoEl.classList.add('hidden');
            }
            
            const imageEl = document.getElementById('viewportImage');
            if (imageEl) {
                imageEl.src = "";
                imageEl.classList.add('hidden');
            }
            
            // Hide overlay
            const overlay = document.getElementById('viewportSequenceOverlay');
            if (overlay) overlay.classList.add('hidden');
            
            // Reset viewport to default placeholder
            const placeholder = document.getElementById('viewportPlaceholder');
            if (placeholder) placeholder.classList.remove('hidden');
            
            const audioVis = document.getElementById('viewportAudioVisualizer');
            if (audioVis) audioVis.classList.add('hidden');
            
            const durationVal = document.getElementById('seqDurationVal');
            if (durationVal) durationVal.textContent = "0.0s";

            renderTimelineRuler(0);
            renderTimelineTracksOnly();
        }
    </script>
</body>
</html>
"""

# Serve execution
if __name__ == '__main__':
    # Configured to run strictly on external proxy port 3000
    app.run(host='0.0.0.0', port=1000, debug=True)