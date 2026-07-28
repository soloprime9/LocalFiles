import os
import sys
import re
import math
import uuid
import json
import random
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

# Each emotion maps to a *range* (not a fixed value) of prosody settings.
# Edge-TTS no longer honors <mstts:express-as> style tags (Microsoft locked
# custom SSML down to a single <prosody> tag), so genuine emotional color
# has to come from rate/pitch/volume -- and critically, from *varying* those
# values sentence-to-sentence. A single constant rate/pitch applied to an
# entire script is exactly what makes TTS sound like a flat robot; real
# human speech drifts up and down between sentences.
EMOTION_PRESETS = {
    "neutral":   {"rate": (-3, 3),    "pitch": (-5, 5),    "volume": (-2, 2)},
    "friendly":  {"rate": (0, 9),     "pitch": (4, 16),    "volume": (0, 8)},
    "cheerful":  {"rate": (9, 19),    "pitch": (15, 36),   "volume": (5, 16)},
    "excited":   {"rate": (16, 30),   "pitch": (26, 48),   "volume": (10, 22)},
    "calm":      {"rate": (-16, -5),  "pitch": (-16, -4),  "volume": (-10, -2)},
    "sad":       {"rate": (-24, -11), "pitch": (-32, -16), "volume": (-16, -6)},
    "serious":   {"rate": (-9, 0),    "pitch": (-11, -1),  "volume": (0, 6)},
    "whisper":   {"rate": (-22, -10), "pitch": (-10, 0),   "volume": (-42, -26)},
    "angry":     {"rate": (10, 23),   "pitch": (-6, 11),   "volume": (16, 30)},
}

def _split_into_sentences(text):
    # Keep punctuation attached so prosody breaks land at natural speech boundaries
    pieces = re.split(r'(?<=[.!?\u2026])\s+', text.strip())
    return [p.strip() for p in pieces if p.strip()]

async def _synthesize_segment(text, voice, rate_pct, pitch_hz, volume_pct, output_path):
    rate_str = f"{rate_pct:+d}%"
    volume_str = f"{volume_pct:+d}%"
    pitch_str = f"{pitch_hz:+d}Hz"
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate_str, volume=volume_str, pitch=pitch_str)
        await communicate.save(output_path)
    except Exception:
        # Some edge-tts versions deprecated the pitch argument -- retry without it
        communicate = edge_tts.Communicate(text, voice, rate=rate_str, volume=volume_str)
        await communicate.save(output_path)

async def generate_edge_tts_natural(text, voice, output_path, emotion="friendly", natural_variation=True, ffmpeg_bin=None):
    """
    Generates expressive, non-robotic speech by varying rate/pitch/volume
    per sentence within the chosen emotion's natural range, then stitching
    the sentence clips back together. Falls back to a single steady pass
    (still emotion-colored, just without sentence-to-sentence drift) for
    very short scripts or if anything goes wrong.
    """
    preset = EMOTION_PRESETS.get(emotion, EMOTION_PRESETS["friendly"])
    sentences = _split_into_sentences(text) if natural_variation else [text]

    if len(sentences) <= 1:
        mid_rate = sum(preset["rate"]) // 2
        mid_pitch = sum(preset["pitch"]) // 2
        mid_volume = sum(preset["volume"]) // 2
        await _synthesize_segment(text, voice, mid_rate, mid_pitch, mid_volume, output_path)
        return

    with tempfile.TemporaryDirectory() as seg_dir:
        segment_paths = []
        for i, sentence in enumerate(sentences):
            r = random.randint(preset["rate"][0], preset["rate"][1])
            p = random.randint(preset["pitch"][0], preset["pitch"][1])
            v = random.randint(preset["volume"][0], preset["volume"][1])
            seg_path = os.path.join(seg_dir, f"seg_{i:04d}.mp3")
            try:
                await _synthesize_segment(sentence, voice, r, p, v, seg_path)
                if os.path.exists(seg_path) and os.path.getsize(seg_path) > 0:
                    segment_paths.append(seg_path)
            except Exception as e:
                print(f"[TTS WARN] Segment {i} failed, skipping: {e}")

        if not segment_paths:
            raise RuntimeError("All speech segments failed to synthesize.")

        if len(segment_paths) == 1:
            shutil.copy(segment_paths[0], output_path)
            return

        ffmpeg_bin = ffmpeg_bin or find_ffmpeg_binary()
        concat_list = os.path.join(seg_dir, "concat.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for sp in segment_paths:
                f.write(f"file '{sp}'\n")

        concat_cmd = [ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", output_path]
        proc = subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0 or not os.path.exists(output_path):
            # Stream copy can fail if segment headers differ slightly -- re-encode instead
            reencode_cmd = [ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c:a", "libmp3lame", "-q:a", "2", output_path]
            subprocess.run(reencode_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def apply_voice_enhancement(audio_path, ffmpeg_bin=None):
    """
    Light mastering pass that takes raw, slightly thin/digital TTS output and
    gives it warmth and presence: a gentle low-mid body boost, a presence
    lift around 3kHz for clarity, soft compression to even out word-to-word
    loudness (the other big "robotic" tell), and a final loudness normalize.
    Runs in place (writes to a temp file, then swaps it in).
    """
    ffmpeg_bin = ffmpeg_bin or find_ffmpeg_binary()
    tmp_out = audio_path + ".enh.mp3"
    af_chain = (
        "highpass=f=70,"
        "equalizer=f=220:t=q:w=1:g=2.5,"
        "equalizer=f=3000:t=q:w=1:g=2.5,"
        "acompressor=threshold=-20dB:ratio=2.5:attack=6:release=90:makeup=2,"
        "loudnorm=I=-16:TP=-1.5:LRA=11"
    )
    cmd = [ffmpeg_bin, "-y", "-i", audio_path, "-af", af_chain, "-c:a", "libmp3lame", "-q:a", "2", tmp_out]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode == 0 and os.path.exists(tmp_out) and os.path.getsize(tmp_out) > 0:
        shutil.move(tmp_out, audio_path)
    else:
        print(f"[TTS WARN] Voice enhancement pass failed, keeping raw synthesis: {proc.stderr[-400:]}")
        if os.path.exists(tmp_out):
            os.remove(tmp_out)

def render_text_to_speech(text, engine, voice_or_lang, output_path, emotion="friendly", natural_variation=True, enhance=True):
    """
    Renders text to speech using either Microsoft Edge-TTS (with emotional
    prosody + sentence-level natural variation) or Google gTTS (flatter by
    nature, but still gets the warmth/enhancement pass and a slow-speech
    option for calmer deliveries).
    """
    ffmpeg_bin = find_ffmpeg_binary()

    if engine == "edge":
        if edge_tts is None:
            raise ImportError("Microsoft Edge TTS library is not installed.")
        asyncio.run(generate_edge_tts_natural(text, voice_or_lang, output_path, emotion, natural_variation, ffmpeg_bin))
    else:
        # gTTS has no prosody controls -- "slow" is the only lever, used for calmer/sadder deliveries
        if gTTS is None:
            raise ImportError("Google gTTS library is not installed.")
        use_slow = emotion in ("calm", "sad", "whisper", "serious")
        tts = gTTS(text=text, lang=voice_or_lang, slow=use_slow)
        tts.save(output_path)

    if enhance:
        try:
            apply_voice_enhancement(output_path, ffmpeg_bin)
        except Exception as e:
            print(f"[TTS WARN] Enhancement skipped: {e}")

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

def find_ffmpeg_binary():
    """
    Dynamically detects the ffmpeg executable path (especially critical for
    Windows or custom environments). Shared by the TTS pipeline and the
    video compiler so both use the exact same resolved binary.
    """
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

    if ffmpeg_bin == "ffmpeg":
        try:
            from moviepy.config import get_setting
            mv_ff = get_setting("FFMPEG_BINARY")
            if mv_ff and os.path.exists(mv_ff):
                ffmpeg_bin = mv_ff
        except Exception:
            pass
    return ffmpeg_bin


def compile_video_background(task_id, timeline, audio_track, settings):
    """
    Processes the timeline sequence and compiles the final video.
    Supports real transitions (xfade/acrossfade), per-clip visual effects,
    auto-burned captions (from TTS script text), corrected audio mixing
    (no more silent volume-halving from amix auto-normalize), and
    high-quality H.264 export with faststart for instant playback/download.
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

        update_progress(3, "Analyzing project sequence structure...")

        ffmpeg_bin = find_ffmpeg_binary()
        print(f"[COMPILER INFO] Resolved ffmpeg executable path: {ffmpeg_bin}")

        def run_ff(cmd, label=""):
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode != 0:
                print(f"[FFMPEG WARN] {label} failed: {proc.stderr[-1500:]}")
            return proc

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
                match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
                if match:
                    hours = int(match.group(1))
                    minutes = int(match.group(2))
                    seconds = float(match.group(3))
                    return hours * 3600 + minutes * 60 + seconds
            except Exception as e:
                print(f"[COMPILER INFO] Failed to parse duration with ffmpeg: {e}")
            return 5.0

        def escape_drawtext(text):
            # Escape characters that break ffmpeg's drawtext filter argument parser
            text = text.replace("\\", "\\\\\\\\")
            text = text.replace(":", "\\:")
            text = text.replace("'", "\u2019")
            text = text.replace("%", "\\%")
            text = text.replace(",", "\\,")
            text = text.replace("[", "\\[").replace("]", "\\]")
            return text

        def build_caption_filter(text, total_duration, frame_height):
            """Splits TTS script text into time-synced caption chunks and returns a drawtext filter chain."""
            words = (text or "").split()
            if not words or total_duration <= 0:
                return None
            chunk_size = 6
            chunks = [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
            n = len(chunks)
            seg = total_duration / n
            font_size = max(20, int(frame_height * 0.042))
            parts = []
            for i, chunk in enumerate(chunks):
                start = i * seg
                end = total_duration if i == n - 1 else (start + seg)
                safe_text = escape_drawtext(chunk)
                parts.append(
                    "drawtext=text='%s':fontcolor=white:fontsize=%d:"
                    "box=1:boxcolor=black@0.55:boxborderw=14:"
                    "x=(w-text_w)/2:y=h-(h*0.14):"
                    "enable='between(t,%.3f,%.3f)'" % (safe_text, font_size, start, end)
                )
            return ",".join(parts)

        # ---- Visual effect filter builder (per-clip) ----
        def build_effect_filter(effect, duration):
            """Returns an additional video-filter fragment (string, may be empty) for the requested effect."""
            if effect == "fade":
                return f",fade=in:st=0:d=0.5,fade=out:st={max(duration - 0.5, 0):.2f}:d=0.5"
            elif effect == "rotate":
                return ",rotate=PI"
            elif effect == "grayscale":
                return ",hue=s=0"
            elif effect == "sepia":
                return ",colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131:0"
            elif effect == "mirror":
                return ",hflip"
            elif effect == "vignette":
                return ",vignette"
            elif effect == "blur":
                return ",gblur=sigma=10"
            elif effect == "sharpen":
                return ",unsharp=5:5:1.2:5:5:0.0"
            elif effect == "zoom_in":
                frames = max(int(duration * 30), 1)
                return f",zoompan=z='min(zoom+0.0018,1.4)':d={frames}:s={{W}}x{{H}}:fps=30"
            elif effect == "zoom_out":
                frames = max(int(duration * 30), 1)
                return f",zoompan=z='if(eq(on,1),1.4,max(1.0,pzoom-0.0018))':d={frames}:s={{W}}x{{H}}:fps=30"
            return ""

        # Setup dimension resolutions
        is_portrait = settings.get("format") == "9:16"
        quality = settings.get("quality", "1080p")

        if quality == "4k":
            width, height = (2160, 3840) if is_portrait else (3840, 2160)
        elif quality == "720p":
            width, height = (720, 1280) if is_portrait else (1280, 720)
        else:  # 1080p Default
            width, height = (1080, 1920) if is_portrait else (1920, 1080)

        # Quality -> encode bitrate/CRF map (higher quality = lower CRF, higher bitrate ceiling)
        encode_params = {
            "720p": {"crf": "20", "preset": "medium", "maxrate": "6M", "bufsize": "12M", "abitrate": "192k"},
            "1080p": {"crf": "18", "preset": "medium", "maxrate": "12M", "bufsize": "24M", "abitrate": "256k"},
            "4k": {"crf": "17", "preset": "slow", "maxrate": "45M", "bufsize": "90M", "abitrate": "320k"},
        }.get(quality, {"crf": "18", "preset": "medium", "maxrate": "12M", "bufsize": "24M", "abitrate": "256k"})

        # Resolve Audio Stream
        audio_file = None
        loop_audio = settings.get("loop_audio", False)
        match_audio_length = settings.get("match_audio_length", False)
        bg_volume = float(settings.get("bg_volume", 0.4))
        bg_volume = min(max(bg_volume, 0.0), 1.5)
        burn_captions = bool(settings.get("burn_captions", False))
        transition_style = settings.get("transition_style", "none")
        transition_duration = float(settings.get("transition_duration", 0.6))
        caption_text = (audio_track or {}).get("caption_text", "")

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
            clip_durations = []
            total_items = len(timeline)

            for idx, item in enumerate(timeline):
                filename = item.get("filename")
                ftype = item.get("type")
                duration = float(item.get("duration", 5.0))
                effect = item.get("effect", "none")  # none, fade, rotate, grayscale, sepia, mirror, vignette, blur, sharpen, zoom_in, zoom_out, slowmo, fastmo

                media_path = os.path.join(UPLOAD_FOLDER, filename)
                if not os.path.exists(media_path):
                    continue

                update_progress(5 + int((idx / max(total_items, 1)) * 45), f"Encoding clip {idx + 1}/{total_items}: {filename}...")

                clip_output = os.path.join(temp_dir, f"clip_{idx:04d}.mp4")
                base_scale = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1"

                effect_extra = build_effect_filter(effect, duration)
                # zoompan needs literal W/H substituted post-pad (output frame size)
                effect_extra = effect_extra.replace("{W}", str(width)).replace("{H}", str(height))

                speed_mode = effect in ("slowmo", "fastmo")
                speed_factor = 2.0 if effect == "slowmo" else (0.5 if effect == "fastmo" else 1.0)
                # For slowmo we need half as much source trimmed (then stretched to 2x length);
                # for fastmo we need 2x as much source trimmed (then compressed to 0.5x length).
                source_trim = duration / speed_factor if speed_mode else duration

                if ftype == "image":
                    cmd = [
                        ffmpeg_bin, "-y",
                        "-loop", "1", "-t", str(duration), "-i", media_path,
                        "-f", "lavfi", "-i", "anullsrc=cl=stereo:r=44100",
                    ]
                    v_filter = base_scale + effect_extra
                    cmd += [
                        "-filter_complex", f"[0:v]{v_filter}[v]",
                        "-map", "[v]", "-map", "1:a",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                        "-c:a", "aac", "-shortest",
                        clip_output
                    ]
                else:  # video
                    has_aud = check_has_audio(media_path)
                    v_filter = base_scale + effect_extra
                    if speed_mode:
                        v_filter += f",setpts={speed_factor:.3f}*PTS"

                    if has_aud:
                        a_filter = "aformat=sample_rates=44100:channel_layouts=stereo"
                        if speed_mode:
                            atempo = 1.0 / speed_factor
                            # atempo only accepts 0.5-2.0 per stage; our factors (0.5 / 2.0) are within range
                            a_filter += f",atempo={atempo:.3f}"
                        cmd = [
                            ffmpeg_bin, "-y",
                            "-ss", "0", "-t", str(source_trim), "-i", media_path,
                            "-filter_complex", f"[0:v]{v_filter}[v];[0:a]{a_filter}[a]",
                            "-map", "[v]", "-map", "[a]",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                            "-c:a", "aac", "-t", str(duration),
                            clip_output
                        ]
                    else:
                        cmd = [
                            ffmpeg_bin, "-y",
                            "-ss", "0", "-t", str(source_trim), "-i", media_path,
                            "-f", "lavfi", "-i", "anullsrc=cl=stereo:r=44100",
                            "-filter_complex", f"[0:v]{v_filter}[v]",
                            "-map", "[v]", "-map", "1:a",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                            "-c:a", "aac", "-shortest", "-t", str(duration),
                            clip_output
                        ]

                proc = run_ff(cmd, label=f"clip {idx}")
                if proc.returncode == 0 and os.path.exists(clip_output):
                    temp_clips.append(clip_output)
                    clip_durations.append(duration)
                else:
                    print(f"Clip rendering failed for {filename}, falling back to raw copy.")
                    shutil.copy(media_path, clip_output)
                    temp_clips.append(clip_output)
                    clip_durations.append(duration)

            if not temp_clips:
                raise ValueError("No clips were successfully rendered.")

            # 2. Assemble the sequence -- either a hard-cut concat, or a real
            #    crossfade/wipe/slide transition chain between every clip.
            update_progress(62, "Assembling video sequence tracks...")
            temp_concat_video = os.path.join(temp_dir, "concat_output.mp4")

            use_transitions = transition_style not in (None, "", "none", "cut") and len(temp_clips) > 1

            if use_transitions:
                # Clamp transition duration so it never exceeds the shortest clip
                safe_td = min(transition_duration, max(min(clip_durations) - 0.15, 0.15))
                inputs = []
                for clip in temp_clips:
                    inputs += ["-i", clip]

                cum_duration = clip_durations[0]
                last_v, last_a = "0:v", "0:a"
                filter_chunks = []
                for i in range(1, len(temp_clips)):
                    offset = max(cum_duration - safe_td, 0)
                    out_v, out_a = f"v{i}", f"a{i}"
                    filter_chunks.append(
                        f"[{last_v}][{i}:v]xfade=transition={transition_style}:duration={safe_td:.3f}:offset={offset:.3f}[{out_v}]"
                    )
                    filter_chunks.append(
                        f"[{last_a}][{i}:a]acrossfade=d={safe_td:.3f}[{out_a}]"
                    )
                    last_v, last_a = out_v, out_a
                    cum_duration += clip_durations[i] - safe_td

                filter_complex = ";".join(filter_chunks)
                trans_cmd = [
                    ffmpeg_bin, "-y", *inputs,
                    "-filter_complex", filter_complex,
                    "-map", f"[{last_v}]", "-map", f"[{last_a}]",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                    "-c:a", "aac",
                    temp_concat_video
                ]
                proc = run_ff(trans_cmd, label="transition chain")
                if proc.returncode != 0 or not os.path.exists(temp_concat_video):
                    # Fall back to a plain concat if the transition chain fails for any reason
                    use_transitions = False

            if not use_transitions:
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
                proc = run_ff(concat_cmd, label="concat")
                if proc.returncode != 0 or not os.path.exists(temp_concat_video):
                    raise RuntimeError(f"Video assembly failed: {proc.stderr}")

            # 3. Mix in the master soundtrack (if any) with corrected, non-destructive levels,
            #    then optionally burn in synced captions, then final encode.
            update_progress(82, "Mixing audio tracks and finishing render...")

            video_duration = sum(clip_durations) if not use_transitions else None
            if video_duration is None:
                # Recompute actual real duration of the (now transitioned) concatenated file
                video_duration = get_audio_duration(temp_concat_video)

            caption_filter = build_caption_filter(caption_text, video_duration, height) if burn_captions and caption_text else None

            # Build the final video-side filter (captions only, optional)
            vid_tail_filter = f"[0:v]{caption_filter}[vout]" if caption_filter else None

            if audio_file:
                audio_duration = get_audio_duration(audio_file)

                if match_audio_length:
                    if video_duration < audio_duration:
                        num_loops = int(math.ceil(audio_duration / video_duration))
                        loop_list = os.path.join(temp_dir, "loop_list.txt")
                        with open(loop_list, "w") as f:
                            for _ in range(num_loops):
                                f.write(f"file '{temp_concat_video}'\n")
                        temp_looped_video = os.path.join(temp_dir, "looped_video.mp4")
                        loop_cmd = [ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", loop_list, "-c", "copy", temp_looped_video]
                        run_ff(loop_cmd, label="audio-length loop")
                        temp_concat_video = temp_looped_video
                    target_t = audio_duration
                else:
                    target_t = video_duration

                audio_chain = (
                    f"[0:a]volume=1.0[main];[1:a]volume={bg_volume:.2f}"
                )
                if not match_audio_length:
                    if loop_audio and audio_duration < video_duration:
                        audio_chain = f"[1:a]volume={bg_volume:.2f},atrim=0:{target_t}[bgtrim];[0:a]volume=1.0[main];[main][bgtrim]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[mixed];[mixed]loudnorm=I=-16:TP=-1.5:LRA=11[a]"
                    else:
                        audio_chain = f"[1:a]volume={bg_volume:.2f},atrim=0:{target_t}[bgtrim];[0:a]volume=1.0[main];[main][bgtrim]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[mixed];[mixed]loudnorm=I=-16:TP=-1.5:LRA=11[a]"
                else:
                    audio_chain = f"[1:a]volume={bg_volume:.2f}[bg];[0:a]volume=1.0[main];[main][bg]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[mixed];[mixed]loudnorm=I=-16:TP=-1.5:LRA=11[a]"

                filter_complex_parts = [audio_chain]
                video_map = "0:v"
                if vid_tail_filter:
                    filter_complex_parts.append(vid_tail_filter)
                    video_map = "[vout]"

                mix_cmd = [
                    ffmpeg_bin, "-y",
                ]
                if match_audio_length:
                    mix_cmd += ["-t", str(audio_duration), "-i", temp_concat_video, "-i", audio_file]
                else:
                    if loop_audio and audio_duration < video_duration:
                        mix_cmd += ["-i", temp_concat_video, "-stream_loop", "-1", "-i", audio_file]
                    else:
                        mix_cmd += ["-i", temp_concat_video, "-i", audio_file]

                mix_cmd += [
                    "-filter_complex", ";".join(filter_complex_parts),
                    "-map", video_map, "-map", "[a]",
                    "-c:v", "libx264", "-preset", encode_params["preset"], "-crf", encode_params["crf"],
                    "-maxrate", encode_params["maxrate"], "-bufsize", encode_params["bufsize"],
                    "-pix_fmt", "yuv420p", "-r", "30",
                    "-c:a", "aac", "-b:a", encode_params["abitrate"],
                    "-t", str(target_t),
                    "-movflags", "+faststart",
                    output_path
                ]
            else:
                # No soundtrack -- still run a loudness-normalize pass on the original
                # clip audio so exports are never quieter than the source footage,
                # and still support caption burn-in if requested.
                filter_complex_parts = ["[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]"]
                video_map = "0:v"
                if vid_tail_filter:
                    filter_complex_parts.append(vid_tail_filter)
                    video_map = "[vout]"
                mix_cmd = [
                    ffmpeg_bin, "-y", "-i", temp_concat_video,
                    "-filter_complex", ";".join(filter_complex_parts),
                    "-map", video_map, "-map", "[a]",
                    "-c:v", "libx264", "-preset", encode_params["preset"], "-crf", encode_params["crf"],
                    "-maxrate", encode_params["maxrate"], "-bufsize", encode_params["bufsize"],
                    "-pix_fmt", "yuv420p", "-r", "30",
                    "-c:a", "aac", "-b:a", encode_params["abitrate"],
                    "-movflags", "+faststart",
                    output_path
                ]

            update_progress(92, "Final high-quality encode pass...")
            proc = run_ff(mix_cmd, label="final mix/encode")

            if proc.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
                # Last-resort fallback: encode without captions/filters so the user still gets a file
                fallback_cmd = [
                    ffmpeg_bin, "-y", "-i", temp_concat_video,
                    "-c:v", "libx264", "-preset", "medium", "-crf", encode_params["crf"],
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart",
                    output_path
                ]
                run_ff(fallback_cmd, label="fallback encode")

            if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
                raise RuntimeError("Failed to output final mixed video file.")

            update_progress(100, "Completed", file_url=f"/api/files/exports/{output_filename}")

        finally:
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
    Generates premium, emotionally-expressive speech tracks via gTTS or
    Microsoft Edge-TTS, with per-sentence prosody variation and a warmth
    enhancement pass so output doesn't sound flat or robotic.
    """
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    engine = data.get("engine", "edge") # edge or gtts
    voice_or_lang = data.get("voice_or_lang", "en-US-AvaMultilingualNeural")
    emotion = data.get("emotion", "friendly")
    if emotion not in EMOTION_PRESETS:
        emotion = "friendly"
    natural_variation = bool(data.get("natural_variation", True))
    enhance = bool(data.get("enhance", True))

    if not text:
        return jsonify({"error": "Speech transcription text is empty."}), 400

    unique_id = uuid.uuid4().hex[:8]
    output_filename = f"tts_{unique_id}.mp3"
    output_path = os.path.join(TTS_FOLDER, output_filename)

    def save_caption_sidecar(text_value):
        # Persist the exact script text next to the audio so it can later be
        # used to auto-generate perfectly time-synced burned-in captions.
        try:
            sidecar_path = os.path.splitext(output_path)[0] + ".txt"
            with open(sidecar_path, "w", encoding="utf-8") as cf:
                cf.write(text_value)
        except Exception as cap_err:
            print(f"[TTS WARN] Failed to save caption sidecar: {cap_err}")

    try:
        render_text_to_speech(text, engine, voice_or_lang, output_path, emotion, natural_variation, enhance)
        save_caption_sidecar(text)
        return jsonify({
            "success": True,
            "filename": output_filename,
            "text": text,
            "engine": engine,
            "voice": voice_or_lang,
            "emotion": emotion,
            "url": f"/api/files/tts_audio/{output_filename}"
        })
    except Exception as e:
        # If Edge TTS fails, attempt immediate gTTS English fallback
        try:
            render_text_to_speech(text, "gtts", "en", output_path, emotion, natural_variation, enhance)
            save_caption_sidecar(text)
            return jsonify({
                "success": True,
                "filename": output_filename,
                "text": text,
                "engine": "gtts (Fallback)",
                "voice": "en",
                "emotion": emotion,
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
            caption_text = ""
            sidecar_path = os.path.join(TTS_FOLDER, os.path.splitext(f)[0] + ".txt")
            if os.path.exists(sidecar_path):
                try:
                    with open(sidecar_path, "r", encoding="utf-8") as cf:
                        caption_text = cf.read()
                except Exception:
                    caption_text = ""
            tts_items.append({
                "filename": f,
                "type": "audio",
                "url": f"/api/files/tts_audio/{f}",
                "text": caption_text
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
        if folder == "tts_audio":
            sidecar_path = os.path.splitext(target_file)[0] + ".txt"
            if os.path.exists(sidecar_path):
                try:
                    os.remove(sidecar_path)
                except Exception:
                    pass
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
                                <!-- Most natural / conversational (Microsoft's newer expressive voices) -->
                                <option value="en-US-AvaMultilingualNeural" selected>✨ English (US) - Female (Ava) - Most Natural, Expressive</option>
                                <option value="en-US-AndrewMultilingualNeural">✨ English (US) - Male (Andrew) - Warm, Confident</option>
                                <option value="en-US-EmmaMultilingualNeural">✨ English (US) - Female (Emma) - Natural, Friendly</option>
                                <option value="en-US-BrianMultilingualNeural">✨ English (US) - Male (Brian) - Approachable, Casual</option>
                                <!-- English US -->
                                <option value="en-US-AriaNeural">🇺🇸 English (US) - Female (Aria) - Premium Realistic</option>
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
                            <p id="gttsHint" class="hidden text-[9px] text-amber-500/80 mt-1">Google TTS has no emotional range — it's flatter by nature. Use Edge Premium for expressive/emotional delivery.</p>
                        </div>

                        <div>
                            <label class="block text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1 flex justify-between items-center">
                                <span>Emotion / Delivery Style</span>
                                <span class="text-[9px] text-violet-400">Prosody-driven</span>
                            </label>
                            <select id="ttsEmotion" class="w-full bg-gray-950 border border-gray-800 rounded-xl px-3 py-2 text-xs text-gray-100 focus:outline-none focus:ring-1 focus:ring-violet-500 transition">
                                <option value="friendly" selected>🙂 Friendly / Warm (default)</option>
                                <option value="cheerful">😄 Cheerful / Upbeat</option>
                                <option value="excited">🤩 Excited / Energetic</option>
                                <option value="calm">😌 Calm / Soothing</option>
                                <option value="serious">🧐 Serious / Authoritative</option>
                                <option value="sad">😢 Sad / Somber</option>
                                <option value="angry">😠 Angry / Intense</option>
                                <option value="whisper">🤫 Whisper / Intimate</option>
                                <option value="neutral">😐 Neutral / News-style</option>
                            </select>
                        </div>

                        <div class="flex items-center justify-between gap-3 text-[10px] text-gray-400 bg-gray-950/60 rounded-xl px-3 py-2 border border-gray-850">
                            <label class="flex items-center gap-1.5 cursor-pointer">
                                <input type="checkbox" id="ttsNaturalVariation" checked class="rounded border-gray-800 bg-gray-900 text-violet-600 focus:ring-0">
                                Natural sentence variation
                            </label>
                            <label class="flex items-center gap-1.5 cursor-pointer">
                                <input type="checkbox" id="ttsEnhance" checked class="rounded border-gray-800 bg-gray-900 text-violet-600 focus:ring-0">
                                Voice warmth enhancement
                            </label>
                        </div>
                        <p class="text-[9px] text-gray-600 -mt-2">Sentence variation gives each sentence its own slight rate/pitch drift instead of one flat robotic tone. Warmth enhancement adds EQ + gentle compression so the voice sounds less thin/digital.</p>

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
                        <select id="masterAudio" onchange="onMasterAudioChange()" class="w-full bg-gray-900 border border-gray-800 rounded-lg px-2 py-1.5 text-xs text-gray-200 focus:outline-none">
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
                        <div class="mt-3">
                            <label class="flex justify-between text-[9px] text-gray-500 uppercase font-semibold mb-1">
                                <span>Background Music Volume</span>
                                <span id="bgVolumeVal" class="text-emerald-400 mono">40%</span>
                            </label>
                            <input type="range" id="bgVolume" min="0" max="100" value="40"
                                   oninput="document.getElementById('bgVolumeVal').textContent = this.value + '%'"
                                   class="w-full accent-emerald-500">
                            <p class="text-[9px] text-gray-600 mt-1">Original clip audio always stays at full, true volume — this only controls the soundtrack mixed underneath it. Final loudness is auto-normalized so exports never sound quieter than your preview.</p>
                        </div>
                        <div id="captionToggleWrap" class="hidden mt-3 pt-2 border-t border-gray-900">
                            <label class="flex items-center gap-1.5 cursor-pointer text-[10px] text-gray-400">
                                <input type="checkbox" id="burnCaptions" class="rounded border-gray-800 bg-gray-900 text-violet-600 focus:ring-0">
                                Auto-burn synced captions from this script
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

                    <!-- Transition style between clips -->
                    <div class="pt-3 border-t border-gray-800 text-xs mb-3">
                        <label class="block text-[9px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Clip Transition Style</label>
                        <div class="grid grid-cols-2 gap-2">
                            <select id="transitionStyle" class="w-full bg-gray-950 border border-gray-800 rounded-lg p-1.5 text-xs focus:outline-none">
                                <option value="none" selected>Hard Cut (None)</option>
                                <option value="fade">Cross Fade</option>
                                <option value="dissolve">Dissolve</option>
                                <option value="wipeleft">Wipe Left</option>
                                <option value="wiperight">Wipe Right</option>
                                <option value="slideup">Slide Up</option>
                                <option value="slidedown">Slide Down</option>
                                <option value="circleopen">Circle Open</option>
                                <option value="circleclose">Circle Close</option>
                                <option value="pixelize">Pixelize</option>
                                <option value="radial">Radial Wipe</option>
                            </select>
                            <select id="transitionDuration" class="w-full bg-gray-950 border border-gray-800 rounded-lg p-1.5 text-xs focus:outline-none">
                                <option value="0.4">0.4s (Snappy)</option>
                                <option value="0.6" selected>0.6s (Balanced)</option>
                                <option value="1.0">1.0s (Cinematic)</option>
                            </select>
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
            const gttsHint = document.getElementById('gttsHint');
            if (engine === 'edge') {
                edgeVoices.classList.remove('hidden');
                gttsVoices.classList.add('hidden');
                gttsHint.classList.add('hidden');
            } else {
                edgeVoices.classList.add('hidden');
                gttsVoices.classList.remove('hidden');
                gttsHint.classList.remove('hidden');
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
            const natural_variation = document.getElementById('ttsNaturalVariation').checked;
            const enhance = document.getElementById('ttsEnhance').checked;

            if (!text) return alert("Speech script transcription can't be empty.");

            const spinner = document.getElementById('ttsSpinner');
            spinner.classList.remove('hidden');

            try {
                const res = await fetch('/api/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: text, engine: engine, voice_or_lang: voice,
                        emotion: emotion, natural_variation: natural_variation, enhance: enhance
                    })
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
                    <div class="bg-gray-950 border border-gray-800 rounded-xl p-3 flex flex-col justify-between gap-3 hover:border-gray-700 transition">
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
                                <h4 class="text-xs font-semibold text-gray-200 truncate break-all" title="${item.filename}">
                                    ${item.filename.split('_').slice(1).join('_') || item.filename}
                                </h4>
                                <span class="px-1.5 py-0.5 rounded text-[8px] font-bold ${badgeColor} uppercase tracking-wider mt-1 inline-block">
                                    ${displayType}
                                </span>
                            </div>
                        </div>

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
        function buildAudioOptionValue(filename, source, captionText) {
            return JSON.stringify({
                filename: filename,
                source: source,
                caption_text: source === 'tts' ? (captionText || '') : ''
            });
        }

        function updateAudioOptions() {
            const select = document.getElementById('masterAudio');
            const selectedVal = select.value;
            select.innerHTML = `<option value="">-- No Soundtrack (Silent) --</option>`;

            // Add uploads
            availableMedia.uploads.filter(x => x.type === 'audio').forEach(item => {
                const opt = document.createElement('option');
                opt.value = buildAudioOptionValue(item.filename, "uploads", "");
                opt.textContent = `📁 PC: ${item.filename.split('_').slice(1).join('_') || item.filename}`;
                select.appendChild(opt);
            });

            // Add TTS (carries its original script text for auto-captions)
            availableMedia.tts.forEach((item, idx) => {
                const opt = document.createElement('option');
                opt.value = buildAudioOptionValue(item.filename, "tts", item.text || "");
                opt.textContent = `🎙️ TTS: Speech Clip #${idx + 1}`;
                select.appendChild(opt);
            });

            // Keep selection if exists
            if (selectedVal) select.value = selectedVal;
            onMasterAudioChange();
        }

        function onMasterAudioChange() {
            const select = document.getElementById('masterAudio');
            const wrap = document.getElementById('captionToggleWrap');
            let hasCaptionableText = false;
            if (select.value) {
                try {
                    const parsed = JSON.parse(select.value);
                    hasCaptionableText = parsed.source === 'tts' && parsed.caption_text && parsed.caption_text.trim().length > 0;
                } catch (e) { /* no-op */ }
            }
            wrap.classList.toggle('hidden', !hasCaptionableText);
            if (!hasCaptionableText) document.getElementById('burnCaptions').checked = false;
        }

        function setAsMasterAudio(filename, source) {
            const select = document.getElementById('masterAudio');
            let captionText = "";
            if (source === 'tts') {
                const match = availableMedia.tts.find(t => t.filename === filename);
                captionText = match ? (match.text || "") : "";
            }
            select.value = buildAudioOptionValue(filename, source === 'tts' ? 'tts' : 'uploads', captionText);
            onMasterAudioChange();
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
                                <label class="block text-[8px] text-gray-500 uppercase font-semibold">Clip Effect</label>
                                <select onchange="updateTimelineItemProp(${index}, 'effect', this.value)" 
                                        class="w-full bg-gray-900 border border-gray-800 rounded px-2 py-1 text-xs focus:outline-none">
                                    <option value="none" ${item.effect === 'none' ? 'selected' : ''}>None</option>
                                    <option value="fade" ${item.effect === 'fade' ? 'selected' : ''}>Fade In/Out</option>
                                    <option value="rotate" ${item.effect === 'rotate' ? 'selected' : ''}>Rotate Frame</option>
                                    <option value="zoom_in" ${item.effect === 'zoom_in' ? 'selected' : ''}>Zoom In (Ken Burns)</option>
                                    <option value="zoom_out" ${item.effect === 'zoom_out' ? 'selected' : ''}>Zoom Out (Ken Burns)</option>
                                    <option value="grayscale" ${item.effect === 'grayscale' ? 'selected' : ''}>Grayscale</option>
                                    <option value="sepia" ${item.effect === 'sepia' ? 'selected' : ''}>Sepia / Vintage</option>
                                    <option value="mirror" ${item.effect === 'mirror' ? 'selected' : ''}>Mirror Flip</option>
                                    <option value="vignette" ${item.effect === 'vignette' ? 'selected' : ''}>Vignette</option>
                                    <option value="blur" ${item.effect === 'blur' ? 'selected' : ''}>Soft Blur</option>
                                    <option value="sharpen" ${item.effect === 'sharpen' ? 'selected' : ''}>Sharpen / Crisp</option>
                                    <option value="slowmo" ${item.effect === 'slowmo' ? 'selected' : ''}>Slow Motion (0.5x)</option>
                                    <option value="fastmo" ${item.effect === 'fastmo' ? 'selected' : ''}>Fast Motion (2x)</option>
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
            const bg_volume = parseInt(document.getElementById('bgVolume').value, 10) / 100;
            const burn_captions = document.getElementById('burnCaptions').checked;
            const transition_style = document.getElementById('transitionStyle').value;
            const transition_duration = parseFloat(document.getElementById('transitionDuration').value);

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
                    bg_volume: bg_volume,
                    burn_captions: burn_captions,
                    transition_style: transition_style,
                    transition_duration: transition_duration
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
    app.run(host='0.0.0.0', port=25000, debug=True)