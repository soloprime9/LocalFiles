import os
import uuid
import threading
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string, send_from_directory

# ─── Transcription Engine: faster-whisper (CTranslate2) ───
# WHY WE SWITCHED FROM openai-whisper:
#
# 1. GARBLED / SCRIPT-SWITCHING OUTPUT
#    openai-whisper re-guesses the spoken language on every ~30s chunk. Hindi and Urdu are
#    phonetically almost identical to the model, so it kept flip-flopping between them --
#    that's why the old output jumped between Devanagari, Urdu (Perso-Arabic) script, and
#    mangled English in the same paragraph. Locking `language=` once for the whole file
#    (below) fixes this completely.
#
# 2. REPEATED / LOOPING GARBAGE TEXT (e.g. "uv our house.. uv our house..")
#    This is a known Whisper failure mode: during background music or silence, it hallucinates
#    a short phrase and loops it. faster-whisper has a built-in voice-activity (VAD) filter
#    that skips non-speech stretches before they ever reach the model, which removes this
#    almost entirely.
#
# 3. SPEED (15 min for a 13MB file)
#    faster-whisper runs on CTranslate2 with int8 quantization on CPU (float16 on GPU if
#    available) -- typically 4x+ faster than plain openai-whisper for the same model size.
#    We also now cache the loaded model instead of reloading it from disk on every job.
#
# 4. NO MORE FFMPEG SUBPROCESS AT ALL
#    faster-whisper decodes audio/video internally via PyAV (bundled ffmpeg libraries, no
#    external .exe invoked), so the previous "[WinError 2] system cannot find the file
#    specified" failure mode can't happen here -- there's no "ffmpeg" command being looked
#    up on PATH anymore.
try:
    from faster_whisper import WhisperModel
    import ctranslate2
except ImportError:
    print("[Error] Kripya run karein: pip install faster-whisper")
    raise SystemExit(1)

app = Flask(__name__)
UPLOAD_FOLDER = Path('./uploaded_media')
OUTPUT_FOLDER = Path('./transcription_output')
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

TRANSCRIBE_JOBS = {}

# Device / precision auto-selection.
CUDA_AVAILABLE = ctranslate2.get_cuda_device_count() > 0
DEVICE = "cuda" if CUDA_AVAILABLE else "cpu"
COMPUTE_TYPE = "float16" if CUDA_AVAILABLE else "int8"
print(f"[System] faster-whisper will run on: {DEVICE} ({COMPUTE_TYPE})")

# Model cache so we don't reload weights from disk on every single request.
_MODEL_CACHE = {}
_MODEL_LOCK = threading.Lock()

# None = let Whisper auto-detect (only recommended for mixed/unknown-language files).
# Locking a language avoids the Hindi/Urdu/English script-flipping bug described above.
LANGUAGE_OPTIONS = {
    "auto": None,
    "hi": "hi",
    "en": "en",
    "ur": "ur",
}


def get_model(model_size):
    with _MODEL_LOCK:
        if model_size not in _MODEL_CACHE:
            _MODEL_CACHE[model_size] = WhisperModel(model_size, device=DEVICE, compute_type=COMPUTE_TYPE)
        return _MODEL_CACHE[model_size]


def console_log(job, message):
    print(f"[{job.get('id', '----')}] {message}", flush=True)
    job["logs"].append(message)


# ─── Async Whisper Processing Thread Orchestrator ───
def whisper_conversion_pipeline(file_path, job_id, model_size, language_code):
    job = TRANSCRIBE_JOBS[job_id]
    job["id"] = job_id
    job["status"] = "processing"

    try:
        console_log(job, f"Loading Whisper Model ({model_size}) on {DEVICE}...")
        job["percent"] = 20
        model = get_model(model_size)
        console_log(job, f"Whisper Model ({model_size}) ready.")
        job["percent"] = 35

        console_log(job, f"Processing media file: {file_path.name}")
        forced_language = LANGUAGE_OPTIONS.get(language_code)
        if forced_language:
            console_log(job, f"Language locked to '{forced_language}' (prevents script-switching).")
        else:
            console_log(job, "Auto-detecting language (only the first chunk is used to decide).")

        console_log(job, "Transcribing with voice-activity filtering (skips music/silence)...")

        segments, info = model.transcribe(
            str(file_path.resolve()),
            language=forced_language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            condition_on_previous_text=False,  # reduces repeat-loop hallucinations further
        )

        if not forced_language:
            console_log(job, f"Detected language: {info.language} (confidence {info.language_probability:.2f})")

        job["percent"] = 60

        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())
            # keep the UI feeling alive on long files without spamming every segment
            if len(text_parts) % 20 == 0:
                job["percent"] = min(85, 60 + len(text_parts) // 5)

        transcribed_text = " ".join(text_parts).strip()

        job["percent"] = 90
        console_log(job, "Saving transcription data...")

        output_filename = f"{file_path.stem}_{uuid.uuid4()}_transcription.txt"
        output_path = OUTPUT_FOLDER / output_filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(transcribed_text)

        job["preview"] = transcribed_text[:500] + "..." if len(transcribed_text) > 500 else transcribed_text

        try:
            file_path.unlink()
        except OSError:
            pass

        job["percent"] = 100
        job["status"] = "done"
        console_log(job, "Transcription completed successfully!")
        job["result"] = {
            "download_url": f"/api/download/{output_filename}"
        }

    except Exception as e:
        job["status"] = "error"
        console_log(job, f"Pipeline Execution Failed: {str(e)}")


# ─── Web API Routing Control ───
@app.route('/')
def index_ui():
    return render_template_string(HTML_UI_TEMPLATE)


@app.route('/api/upload-and-transcribe', methods=['POST'])
def handle_upload():
    if 'media' not in request.files:
        return jsonify({"error": "No media file field"}), 400

    file = request.files['media']
    model_size = request.form.get('model_size', 'base')
    language_code = request.form.get('language', 'hi')

    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    file_extension = Path(file.filename).suffix
    unique_name = f"{uuid.uuid4()}{file_extension}"
    save_path = UPLOAD_FOLDER / unique_name
    file.save(str(save_path))

    job_id = str(uuid.uuid4())
    TRANSCRIBE_JOBS[job_id] = {
        "status": "queued",
        "percent": 0,
        "logs": ["Media uploaded successfully.", "Starting AI engine pipeline..."],
        "preview": "",
        "result": None
    }

    t = threading.Thread(
        target=whisper_conversion_pipeline,
        args=(save_path, job_id, model_size, language_code),
        daemon=True,
    )
    t.start()
    return jsonify({"job_id": job_id})


@app.route('/api/job-status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    job = TRANSCRIBE_JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Invalid identifier"}), 404
    return jsonify(job)


@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)


# ══════════════════════════════ Premium Responsive Frontend UI ══════════════════════════════
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
            --bg: #0b1120;
            --panel: #131b2e;
            --panel-2: #1a2438;
            --border: #26314a;
            --text: #e7ecf7;
            --muted: #8a93a8;
            --accent: #6366f1;
            --accent-2: #8b5cf6;
            --success: #22c55e;
            --danger: #ef4444;
            --warn: #f59e0b;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            background:
                radial-gradient(1200px 600px at 15% -10%, rgba(99,102,241,0.18), transparent 60%),
                radial-gradient(1000px 500px at 110% 10%, rgba(139,92,246,0.14), transparent 55%),
                var(--bg);
            color: var(--text);
            font-family: 'Inter', system-ui, sans-serif;
            min-height: 100vh;
            padding: 48px 20px;
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
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 28px;
            margin-bottom: 20px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.35);
        }

        .dropzone {
            border: 2px dashed var(--border);
            border-radius: 14px;
            padding: 32px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s ease;
            background: var(--panel-2);
        }
        .dropzone:hover, .dropzone.dragover {
            border-color: var(--accent);
            background: rgba(99,102,241,0.08);
        }
        .dropzone .icon { font-size: 30px; margin-bottom: 8px; }
        .dropzone .primary-txt { font-weight: 600; font-size: 15px; }
        .dropzone .sub-txt { color: var(--muted); font-size: 13px; margin-top: 4px; }
        .file-chip {
            display: none;
            margin-top: 14px;
            align-items: center;
            gap: 10px;
            background: var(--panel-2);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 10px 14px;
            font-size: 13px;
        }
        .file-chip.show { display: flex; }
        .file-chip .name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; }
        .file-chip .size { color: var(--muted); }

        .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
        .field-label { display: block; font-size: 13px; font-weight: 600; color: var(--muted); margin: 20px 0 8px; text-transform: uppercase; letter-spacing: 0.04em; }
        select.form-control {
            width: 100%; background: var(--panel-2); color: var(--text);
            border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; font-size: 14px;
            appearance: none;
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
        .progress-fill {
            height: 100%; width: 0%;
            background: linear-gradient(90deg, var(--accent), var(--accent-2));
            transition: width 0.4s ease;
        }

        .log-box {
            background: #060a14; border: 1px solid var(--border); color: #7dd3fc;
            font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12.5px;
            height: 190px; overflow-y: auto; padding: 14px; border-radius: 10px;
            white-space: pre-wrap; line-height: 1.6;
        }
        .preview-box {
            background: var(--panel-2); border: 1px dashed var(--border); padding: 16px;
            border-radius: 10px; color: #cbd5e1; font-size: 13.5px; max-height: 200px;
            overflow-y: auto; margin-top: 16px; line-height: 1.6;
        }
        .result-box { margin-top: 20px; text-align: center; }
        .result-box .title { color: var(--success); font-weight: 700; margin-bottom: 12px; }
        a.download-btn {
            display: inline-block; width: 100%; padding: 13px; border-radius: 10px;
            background: rgba(34,197,94,0.12); border: 1px solid rgba(34,197,94,0.4);
            color: var(--success); font-weight: 700; text-decoration: none; font-size: 14px;
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
                <p>Turn any audio or video into a clean transcript</p>
            </div>
        </div>

        <div class="card">
            <form id="uploadForm" enctype="multipart/form-data">
                <div class="dropzone" id="dropzone">
                    <div class="icon">📁</div>
                    <div class="primary-txt">Click to browse or drag a file here</div>
                    <div class="sub-txt">MP3, WAV, MP4, MKV, MOV, WEBM and more</div>
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
                <div class="model-hint">Locking the language stops the transcript from randomly switching scripts mid-way. Use Auto-detect only if you genuinely don't know the language.</div>

                <button type="submit" class="submit-btn" id="submitBtn">Start Text Extraction</button>
            </form>
        </div>

        <div class="card hidden" id="statusPanel">
            <div class="status-header">
                <h3>Pipeline Status</h3>
                <span class="badge queued" id="statusBadge">Queued</span>
            </div>

            <div class="progress-track">
                <div class="progress-fill" id="progressBar"></div>
            </div>

            <div class="log-box" id="logConsole"></div>

            <div class="preview-box hidden" id="previewContainer">
                <div style="color:#93c5fd; font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:8px;">Transcript preview</div>
                <div id="textPreview"></div>
            </div>

            <div class="result-box hidden" id="resultBox">
                <div class="title">🎉 Conversion complete!</div>
                <a id="downloadBtn" href="#" class="download-btn">⬇️ Download Transcript (.txt)</a>
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
        ['dragenter', 'dragover'].forEach(evt =>
            dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.add('dragover'); })
        );
        ['dragleave', 'drop'].forEach(evt =>
            dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.remove('dragover'); })
        );
        dropzone.addEventListener('drop', e => {
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                updateFileChip();
            }
        });
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

                if (data.job_id) {
                    trackJob(data.job_id);
                } else {
                    logConsole.innerText += `[Error] Upload failure: ${data.error}\\n`;
                    setBadge('error');
                    submitBtn.disabled = false;
                }
            } catch (err) {
                logConsole.innerText += `[Error] Failed to connect to server.\\n`;
                setBadge('error');
                submitBtn.disabled = false;
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
                    document.getElementById('downloadBtn').href = job.result.download_url;

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
    app.run(host="0.0.0.0", port=5001, debug=True)