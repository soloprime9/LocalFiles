import os
import cv2
import uuid
import json
import subprocess
import urllib.request
import numpy as np
import threading
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string, send_from_directory

# ─── Robust Imageio-FFmpeg Resolver (Automatic & Crash Proof) ───
try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    print("Run: pip install imageio-ffmpeg")
    raise SystemExit(1)

app = Flask(__name__)
UPLOAD_FOLDER = Path('./uploaded_videos')
OUTPUT_FOLDER = Path('./rendered_output')
MODEL_FOLDER = Path('./models')
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)
MODEL_FOLDER.mkdir(exist_ok=True)

TRACKING_JOBS = {}

# ══════════════════════════════ Advanced DNN Face Detector ══════════════════════════════
PROTOTXT_URL = "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt"
MODEL_URL = "https://raw.githubusercontent.com/opencv/opencv_3rdparty/dnn_samples_face_detector_20180205_fp16/res10_300x300_ssd_iter_140000_fp16.caffemodel"
PROTOTXT_PATH = MODEL_FOLDER / "deploy.prototxt"
MODEL_PATH = MODEL_FOLDER / "res10_300x300_ssd_iter_140000_fp16.caffemodel"

_dnn_net = None
_haar_cascade = None


def console_log(job, message):
    """Prints to the terminal and updates in-browser console logs simultaneously."""
    print(f"[{job.get('id', '----')}] {message}", flush=True)
    job["logs"].append(message)


def get_face_detector(job):
    """Loads DNN ResNet-10 model with automatic download setup or Haar fallback."""
    global _dnn_net, _haar_cascade
    if _dnn_net is not None or _haar_cascade is not None:
        return

    try:
        if not PROTOTXT_PATH.exists():
            console_log(job, "Downloading face-detector network definition...")
            urllib.request.urlretrieve(PROTOTXT_URL, PROTOTXT_PATH)
        if not MODEL_PATH.exists():
            console_log(job, "Downloading face-detector weights (~5MB)...")
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        _dnn_net = cv2.dnn.readNetFromCaffe(str(PROTOTXT_PATH), str(MODEL_PATH))
        console_log(job, "DNN face detector (ResNet-10 SSD) loaded successfully.")
    except Exception as e:
        console_log(job, f"DNN backend failed ({e}); falling back to classic Haar cascade.")
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        _haar_cascade = cv2.CascadeClassifier(cascade_path)


def detect_faces(frame):
    h, w = frame.shape[:2]
    if _dnn_net is not None:
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
        _dnn_net.setInput(blob)
        out = _dnn_net.forward()
        faces = []
        for i in range(out.shape[2]):
            conf = float(out[0, 0, i, 2])
            if conf < 0.35:
                continue
            box = out[0, 0, i, 3:7] * np.array([w, h, w, h])
            x1, y1, x2, y2 = box.astype(int)
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(w, int(x2)), min(h, int(y2))
            if x2 - x1 < w * 0.015 or y2 - y1 < h * 0.015:
                continue 
            faces.append((x1, y1, x2 - x1, y2 - y1, conf))
        return faces
    else:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        found = _haar_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        return [(int(x), int(y), int(fw), int(fh), 0.75) for (x, y, fw, fh) in found]


def _no_console_kwargs():
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def run_ffmpeg(cmd, job, step_name):
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **_no_console_kwargs())
    if process.returncode != 0:
        raise RuntimeError(f"{step_name} failed: {process.stderr[-1500:]}")


# ══════════════════════════════ Codec-Safe Analysis Proxy ══════════════════════════════

def build_analysis_proxy(video_path, job, sample_fps, proxy_w=960):
    """Encodes a fast-to-read proxy to prevent AV1/HEVC decoding glitches inside OpenCV."""
    proxy_path = video_path.parent / f"{video_path.stem}_proxy.mp4"
    cmd = [
        FFMPEG, '-y', '-i', str(video_path),
        '-vf', f"fps={sample_fps},scale={proxy_w}:-2:flags=fast_bilinear",
        '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
        str(proxy_path)
    ]
    run_ffmpeg(cmd, job, "Building analysis proxy")
    return proxy_path


# ══════════════════════════════ Core Tracking & Smoothing Pass ══════════════════════════════

def analyze_video(proxy_path, job, sample_fps, orig_w, orig_h):
    get_face_detector(job)

    cap = cv2.VideoCapture(str(proxy_path))
    if not cap.isOpened():
        raise RuntimeError("Could not open analysis proxy for reading.")

    proxy_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    proxy_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    scale_x = orig_w / proxy_w
    scale_y = orig_h / proxy_h

    EMA_ALPHA_BASE = 0.45
    CUT_DIFF_THRESH = 35.0
    MAX_MISSES_BEFORE_DRIFT = int(sample_fps * 2) 

    ema_x = ema_y = ema_size = None
    prev_small_gray = None
    miss_count = 0
    tracking_points = []
    frame_index = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = round(frame_index / sample_fps, 3)
        small_gray = cv2.cvtColor(cv2.resize(frame, (64, 36)), cv2.COLOR_BGR2GRAY)
        is_cut = False
        if prev_small_gray is not None:
            diff = float(np.mean(cv2.absdiff(small_gray, prev_small_gray)))
            is_cut = diff > CUT_DIFF_THRESH
        prev_small_gray = small_gray

        faces = detect_faces(frame)
        chosen = None
        if faces:
            if ema_x is not None and not is_cut:
                def score(f):
                    fx, fy, fw, fh, conf = f
                    cx, cy = fx + fw / 2, fy + fh / 2
                    dist = ((cx - ema_x) ** 2 + (cy - ema_y) ** 2) ** 0.5
                    return conf * 400 - dist
                chosen = max(faces, key=score)
            else:
                chosen = max(faces, key=lambda f: f[2] * f[3] * (0.4 + f[4]))

        detected_this_frame = chosen is not None
        if chosen is not None:
            fx, fy, fw, fh, conf = chosen
            cx, cy, sz = fx + fw / 2.0, fy + fh / 2.0, max(fw, fh)

            if ema_x is None or is_cut:
                ema_x, ema_y, ema_size = cx, cy, sz
            else:
                a = EMA_ALPHA_BASE * min(1.0, conf + 0.2)
                ema_x = a * cx + (1 - a) * ema_x
                ema_y = a * cy + (1 - a) * ema_y
                ema_size = a * sz + (1 - a) * ema_size
            miss_count = 0
        else:
            miss_count += 1
            if ema_x is not None and miss_count > MAX_MISSES_BEFORE_DRIFT:
                ema_x = 0.9 * ema_x + 0.1 * (proxy_w / 2)
                ema_y = 0.9 * ema_y + 0.1 * (proxy_h / 2)

        if ema_x is not None:
            point = {
                "time": float(timestamp),
                "x": round(float(ema_x) * scale_x, 2),
                "y": round(float(ema_y) * scale_y, 2),
                "size": round(float(ema_size) * max(scale_x, scale_y), 2),
                "confidence": round(float(chosen[4]), 3) if chosen else 0.0,
                "detected": bool(detected_this_frame),
                "scene_cut": bool(is_cut),
            }
            tracking_points.append(point)
            print(json.dumps(point), flush=True)
            if frame_index % 5 == 0: 
                job["logs"].append(f"track {json.dumps(point)}")

        pct = min(85, int((frame_index / max(1, cap.get(cv2.CAP_PROP_FRAME_COUNT))) * 85))
        job["percent"] = pct
        frame_index += 1

    cap.release()
    return tracking_points


# ══════════════════════════════ Axis Window Expression Generator ══════════════════════════════

def _build_axis_expression(tracking_points, key, target_len, orig_len, default_pos, tolerance_px=12, max_segments=70, padding_frac=0.5):
    collapsed = []
    last_val = None
    for pt in tracking_points:
        t = pt["time"]
        center = pt[key]
        half = (pt["size"] * (1 + padding_frac)) / 2.0
        lo, hi = center - half, center + half

        ideal = center - target_len / 2
        if lo < ideal: ideal = lo
        if hi > ideal + target_len: ideal = hi - target_len

        safe = round(max(0, min(orig_len - target_len, ideal)), 1)
        if last_val is None or abs(safe - last_val) >= tolerance_px:
            collapsed.append((t, safe))
            last_val = safe

    if len(collapsed) > max_segments:
        step = len(collapsed) / max_segments
        collapsed = [collapsed[int(i * step)] for i in range(max_segments)]

    expr = f"{default_pos}"
    for t, val in reversed(collapsed):
        expr = f"if(gte(t,{t}),{val},{expr})"
    return expr.replace(',', '\\,')


def render_cropped_video(video_path, tracking_points, target_format, output_path, orig_w, orig_h, job):
    if target_format == "916":
        target_w = int((9 / 16) * orig_h)
        target_h = orig_h
        if target_w > orig_w:
            target_w = orig_w
            target_h = int((16 / 9) * orig_w)
    elif target_format == "11":
        target_w = min(orig_w, orig_h)
        target_h = target_w
    else:
        target_w = orig_w
        target_h = orig_h

    default_x = (orig_w - target_w) / 2
    default_y = (orig_h - target_h) / 2

    if tracking_points:
        x_expr = _build_axis_expression(tracking_points, "x", target_w, orig_w, default_x)
        y_expr = _build_axis_expression(tracking_points, "y", target_h, orig_h, default_y)
    else:
        x_expr, y_expr = str(default_x), str(default_y)

    cmd = [
        FFMPEG, '-y',
        '-i', str(video_path),
        '-vf', f"crop={target_w}:{target_h}:{x_expr}:{y_expr}",
        '-c:v', 'libx264',
        '-crf', '18',
        '-preset', 'fast',
        '-c:a', 'copy',
        str(output_path)
    ]
    run_ffmpeg(cmd, job, "Final smart-crop render")
    return target_w, target_h


def render_debug_preview(proxy_path, tracking_points, sample_fps, proxy_w, proxy_h, target_w, target_h, orig_w, orig_h, output_path, job):
    cap = cv2.VideoCapture(str(proxy_path))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    tmp_out = proxy_path.parent / f"{proxy_path.stem}_debug_raw.mp4"
    writer = cv2.VideoWriter(str(tmp_out), fourcc, sample_fps, (proxy_w, proxy_h))

    scale_x, scale_y = proxy_w / orig_w, proxy_h / orig_h
    crop_w_p, crop_h_p = target_w * scale_x, target_h * scale_y

    idx = 0
    n = len(tracking_points)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        if idx < n:
            p = tracking_points[idx]
            px, py, psize = p["x"] * scale_x, p["y"] * scale_y, p["size"] * max(scale_x, scale_y)

            crop_x = min(max(0, px - crop_w_p / 2), proxy_w - crop_w_p)
            crop_y = min(max(0, py - crop_h_p / 2), proxy_h - crop_h_p)
            color = (0, 165, 255) if p["scene_cut"] else (0, 255, 0)
            if not p["detected"]: color = (0, 0, 255)

            cv2.rectangle(frame, (int(px - psize/2), int(py - psize/2)), (int(px + psize/2), int(py + psize/2)), color, 2)
            cv2.drawMarker(frame, (int(px), int(py)), color, cv2.MARKER_CROSS, 14, 2)
            cv2.rectangle(frame, (int(crop_x), int(crop_y)), (int(crop_x + crop_w_p), int(crop_y + crop_h_p)), (255, 220, 0), 2)
        writer.write(frame)
        idx += 1

    cap.release()
    writer.release()

    cmd = [FFMPEG, '-y', '-i', str(tmp_out), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', str(output_path)]
    run_ffmpeg(cmd, job, "Debug preview encode")
    try: tmp_out.unlink()
    except OSError: pass


# ══════════════════════════════ Async Processing Thread Orchestrator ══════════════════════════════

def analyze_and_render_pipeline(video_path, job_id, target_format, sample_fps=8.0):
    job = TRACKING_JOBS[job_id]
    job["id"] = job_id
    job["status"] = "processing"

    try:
        cap_probe = cv2.VideoCapture(str(video_path))
        orig_w = int(cap_probe.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
        orig_h = int(cap_probe.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080
        cap_probe.release()

        console_log(job, f"Source resolution detected: {orig_w}x{orig_h}")
        console_log(job, "Building dynamic analysis proxy...")
        proxy_path = build_analysis_proxy(video_path, job, sample_fps)

        console_log(job, "Running smart face tracking system...")
        tracking_points = analyze_video(proxy_path, job, sample_fps, orig_w, orig_h)

        job["percent"] = 88
        console_log(job, "Compiling final cropped sequence via lossless pipeline...")
        output_filename = f"reframe_{uuid.uuid4()}.mp4"
        output_path = OUTPUT_FOLDER / output_filename
        target_w, target_h = render_cropped_video(video_path, tracking_points, target_format, output_path, orig_w, orig_h, job)

        job["percent"] = 94
        console_log(job, "Generating verification preview window data...")
        debug_filename = f"debug_{uuid.uuid4()}.mp4"
        debug_path = OUTPUT_FOLDER / debug_filename
        cap_p = cv2.VideoCapture(str(proxy_path))
        proxy_w = int(cap_p.get(cv2.CAP_PROP_FRAME_WIDTH))
        proxy_h = int(cap_p.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap_p.release()
        render_debug_preview(proxy_path, tracking_points, sample_fps, proxy_w, proxy_h, target_w, target_h, orig_w, orig_h, debug_path, job)

        tracking_json_name = f"tracking_{uuid.uuid4()}.json"
        with open(OUTPUT_FOLDER / tracking_json_name, 'w') as f:
            json.dump(tracking_points, f, indent=2)

        try: proxy_path.unlink()
        except OSError: pass

        job["percent"] = 100
        job["status"] = "done"
        console_log(job, "Reframing Complete! Assets generated successfully.")
        job["result"] = {
            "download_url": f"/api/download/{output_filename}",
            "debug_url": f"/api/stream/{debug_filename}",
            "tracking_json_url": f"/api/download/{tracking_json_name}"
        }

    except Exception as e:
        job["status"] = "error"
        console_log(job, f"Pipeline Execution Failed: {str(e)}")


# ══════════════════════════════ Web API Routing Control ══════════════════════════════

@app.route('/')
def index_ui():
    return render_template_string(HTML_UI_TEMPLATE)


@app.route('/api/upload-and-track', methods=['POST'])
def handle_upload():
    if 'video' not in request.files:
        return jsonify({"error": "No file field detected"}), 400

    file = request.files['video']
    target_format = request.form.get('format', '916')

    if file.filename == '':
        return jsonify({"error": "Empty filename received"}), 400

    file_extension = Path(file.filename).suffix
    unique_name = f"{uuid.uuid4()}{file_extension}"
    save_path = UPLOAD_FOLDER / unique_name
    file.save(str(save_path))

    job_id = str(uuid.uuid4())
    TRACKING_JOBS[job_id] = {
        "status": "queued",
        "percent": 0,
        "logs": ["Video caching finished.", "Initializing background AI routine..."],
        "result": None
    }

    t = threading.Thread(target=analyze_and_render_pipeline, args=(save_path, job_id, target_format), daemon=True)
    t.start()
    return jsonify({"job_id": job_id})


@app.route('/api/job-status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    job = TRACKING_JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Invalid job identifier."}), 404
    return jsonify(job)


@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)


@app.route('/api/stream/<filename>', methods=['GET'])
def stream_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=False)

# HTML UI Template remains completely identical to the source for front-end rendering.
# ══════════════════════════════ Full Responsive Frontend UI ══════════════════════════════
HTML_UI_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Smart Reframer & Face Tracker</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: system-ui, sans-serif; }
        .card { background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; }
        .log-box { background-color: #020617; color: #38bdf8; font-family: monospace; height: 250px; overflow-y: auto; padding: 12px; border-radius: 6px; font-size: 13px; }
        .btn-primary { background-color: #2563eb; border: none; }
        .btn-primary:hover { background-color: #1d4ed8; }
    </style>
</head>
<body>
    <div class="container py-5">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card p-4 shadow-lg mb-4">
                    <h2 class="text-center mb-4 text-white fw-bold">🎬 Auto Video Reframer</h2>
                    
                    <form id="uploadForm" enctype="multipart/form-data">
                        <div class="mb-3">
                            <label class="form-label text-secondary">Select Video File</label>
                            <input type="file" class="form-control bg-dark text-white border-secondary" name="video" accept="video/*" required>
                        </div>
                        
                        <div class="mb-4">
                            <label class="form-label text-secondary">Target Aspect Ratio</label>
                            <select class="form-select bg-dark text-white border-secondary" name="format">
                                <option value="916">9:16 (Shorts/Reels)</option>
                                <option value="11">1:1 (Square Post)</option>
                            </select>
                        </div>
                        
                        <button type="submit" class="btn btn-primary w-100 fw-bold py-2" id="submitBtn">Start Smart Framing</button>
                    </form>
                </div>

                <!-- Progress & Logs Panel (Hidden by default) -->
                <div class="card p-4 shadow-lg d-none" id="statusPanel">
                    <h4 class="text-white mb-3">Processing Status: <span id="statusTxt" class="text-warning">Queued</span></h4>
                    
                    <div class="progress mb-3" style="height: 20px;">
                        <div id="progressBar" class="progress-bar progress-bar-striped progress-bar-animated bg-success" role="progressbar" style="width: 0%">0%</div>
                    </div>
                    
                    <h6 class="text-secondary mb-2">Live Pipeline Console Logs:</h6>
                    <div class="log-box mb-4" id="logConsole"></div>

                    <!-- Download Results -->
                    <div id="resultBox" class="d-none">
                        <h5 class="text-success mb-3">🎉 Video Reframed Successfully!</h5>
                        <div class="d-grid gap-2">
                            <a id="downloadBtn" href="#" class="btn btn-success fw-bold">⬇️ Download Reframed Video</a>
                            <a id="debugBtn" href="#" target="_blank" class="btn btn-outline-info">🔍 View Tracking Analytics Window</a>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    </div>

    <script>
        const form = document.getElementById('uploadForm');
        const statusPanel = document.getElementById('statusPanel');
        const progressBar = document.getElementById('progressBar');
        const statusTxt = document.getElementById('statusTxt');
        const logConsole = document.getElementById('logConsole');
        const resultBox = document.getElementById('resultBox');
        const submitBtn = document.getElementById('submitBtn');

        form.onsubmit = async (e) => {
            e.preventDefault();
            submitBtn.disabled = true;
            statusPanel.classList.remove('d-none');
            resultBox.classList.add('d-none');
            logConsole.innerHTML = '';
            
            let formData = new FormData(form);
            logConsole.innerHTML += "[System] Uploading video file to Flask server...\\n";
            
            try {
                let res = await fetch('/api/upload-and-track', { method: 'POST', body: formData });
                let data = await res.json();
                
                if(data.job_id) {
                    trackJob(data.job_id);
                } else {
                    logConsole.innerHTML += `[Error] Upload failed: ${data.error}\\n`;
                    submitBtn.disabled = false;
                }
            } catch (err) {
                logConsole.innerHTML += `[Error] Connection error.\\n`;
                submitBtn.disabled = false;
            }
        };

        function trackJob(jobId) {
            let interval = setInterval(async () => {
                let res = await fetch(`/api/job-status/${jobId}`);
                let job = await res.json();
                
                statusTxt.innerText = job.status.toUpperCase();
                progressBar.style.width = job.percent + '%';
                progressBar.innerText = job.percent + '%';
                
                // Update Console Logs
                logConsole.innerHTML = job.logs.map(l => l.startsWith('track') ? `⚡ Tracking: ${l.substring(6)}` : `[Info] ${l}`).join('\\n');
                logConsole.scrollTop = logConsole.scrollHeight;

                if(job.status === 'done') {
                    clearInterval(interval);
                    submitBtn.disabled = false;
                    resultBox.classList.remove('d-none');
                    document.getElementById('downloadBtn').href = job.result.download_url;
                    document.getElementById('debugBtn').href = job.result.debug_url;
                } else if(job.status === 'error') {
                    clearInterval(interval);
                    submitBtn.disabled = false;
                    statusTxt.classList.replace('text-warning', 'text-danger');
                }
            }, 1000);
        }
    </script>
</body>
</html>
"""
if __name__ == '__main__':
    app.run(debug=True, port=5000)