import os
import re
import asyncio
import logging
import uuid
import subprocess
import shutil
from typing import Optional, List
from pathlib import Path
from flask import Flask, request, render_template_string, jsonify
from pydantic import BaseModel, HttpUrl, ValidationError
from playwright.async_api import async_playwright, Response, TimeoutError as PlaywrightTimeoutError
import httpx

# ==========================================
# LOGGING & CONFIGURATION
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("VideoDownloaderFlask")

TMP_DIR = Path("./tmp")
TMP_DIR.mkdir(exist_ok=True, parents=True)

CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

app = Flask(__name__)

# ==========================================
# DATA STRUCTS
# ==========================================
class DownloadRequest(BaseModel):
    url: HttpUrl

class MediaManifest:
    def __init__(self):
        self.video_url: Optional[str] = None
        self.audio_url: Optional[str] = None
        self.is_hls: bool = False
        self.is_dash: bool = False

    @property
    def is_complete(self) -> bool:
        if self.is_hls or self.is_dash:
            return self.video_url is not None
        return self.video_url is not None and self.audio_url is not None

# ==========================================
# MODULE A: STEALTH NETWORK INTERCEPTOR
# ==========================================
class AdaptiveScraper:
    def __init__(self, target_url: str):
        self.target_url = target_url
        self.manifest = MediaManifest()
        self.lock = asyncio.Lock()

    async def _handle_network_response(self, response: Response):
        url = response.url
        content_type = response.headers.get("content-type", "").lower()
        
        if url.startswith("blob:"):
            return

        async with self.lock:
            # 1. HLS & DASH Manifest Detection
            if ".m3u8" in url or "application/x-mpegurl" in content_type:
                if not self.manifest.video_url:
                    logger.info(f"[MANIFEST] HLS Found: {url[:80]}...")
                    self.manifest.video_url = url
                    self.manifest.is_hls = True
                return

            if ".mpd" in url or "application/dash+xml" in content_type:
                if not self.manifest.video_url:
                    logger.info(f"[MANIFEST] DASH Found: {url[:80]}...")
                    self.manifest.video_url = url
                    self.manifest.is_dash = True
                return

            # 2. STRICT VALIDATION: Audio vs Video Separation
            # Baaz dafa dono keywords match hote hain, isliye content-type aur explicit tags ko strict check karenge
            is_explicit_audio = "audio/" in content_type or "mime=audio" in url.lower() or "dash-audio" in url.lower()
            is_explicit_video = "video/" in content_type or "mime=video" in url.lower() or "dash-video" in url.lower()

            # Fallback string pattern checks agar content-type missing ho toh
            if not is_explicit_audio and not is_explicit_video:
                if "audio" in url.lower() and "video" not in url.lower():
                    is_explicit_audio = True
                elif "video" in url.lower() and "audio" not in url.lower():
                    is_explicit_video = True

            # Assigning to correct parameters without overwriting
            if is_explicit_audio and not self.manifest.audio_url:
                logger.info(f"[AUDIO CAPTURED] -> {url[:80]}...")
                self.manifest.audio_url = url
                return

            if is_explicit_video and not self.manifest.video_url:
                logger.info(f"[VIDEO CAPTURED] -> {url[:80]}...")
                self.manifest.video_url = url
                return

    async def _fallback_dom_parser(self, page) -> None:
        logger.info("Executing DOM extraction fallbacks...")
        video_srcs = await page.evaluate("""() => {
            const sources = [];
            document.querySelectorAll('video').forEach(v => {
                if (v.src) sources.push(v.src);
                v.querySelectorAll('source').forEach(s => { if (s.src) sources.push(s.src); });
            });
            return sources;
        }""")
        
        for src in video_srcs:
            if src and not self.manifest.video_url:
                if ".m3u8" in src:
                    self.manifest.video_url = src
                    self.manifest.is_hls = True
                elif "audio" in src.lower():
                    self.manifest.audio_url = src
                else:
                    self.manifest.video_url = src
                return

    async def run(self) -> MediaManifest:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-infobars"]
            )
            context = await browser.new_context(user_agent=CHROME_USER_AGENT, viewport={"width": 1280, "height": 720})
            page = await context.new_page()
            
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
            page.on("response", lambda res: asyncio.create_task(self._handle_network_response(res)))
            
            try:
                logger.info(f"Navigating to: {self.target_url}")
                await page.goto(self.target_url, wait_until="networkidle", timeout=30000)
                
                # Active interactions to force player loads
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3);")
                await asyncio.sleep(2.0)
                
                # Strict wait block until BOTH audio and video are locked
                max_wait_cycles = 40  # 40 * 0.5s = 20 seconds maximum polling loop
                for _ in range(max_wait_cycles):
                    async with self.lock:
                        if self.manifest.is_hls or self.manifest.is_dash:
                            break
                        # Agar video mil chuki hai aur hume lagta hai audio alag ho sakti hai, toh thoda rukenge
                        if self.manifest.video_url and self.manifest.audio_url:
                            break
                    await asyncio.sleep(0.5)
                    
                if not self.manifest.video_url:
                    await self._fallback_dom_parser(page)
                    
            except PlaywrightTimeoutError:
                if not self.manifest.video_url:
                    await self._fallback_dom_parser(page)
            finally:
                await context.close()
                await browser.close()
                
        if not self.manifest.video_url:
            raise RuntimeError("Could not find any streamable video layer on this page.")
            
        return self.manifest

# ==========================================
# MODULE B: PROCESSING & SUBPROCESS MUXING
# ==========================================
class MediaProcessor:
    def __init__(self, manifest: MediaManifest):
        self.manifest = manifest
        self.session_id = uuid.uuid4().hex
        self.v_path = TMP_DIR / f"v_{self.session_id}.mp4"
        self.a_path = TMP_DIR / f"a_{self.session_id}.aac"
        self.output_path = TMP_DIR / f"final_{self.session_id}.mp4"
        self.use_shell = os.name == 'nt'

    async def _download_file(self, url: str, destination: Path) -> None:
        headers = {"User-Agent": CHROME_USER_AGENT}
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=60.0) as client:
            async with client.stream("GET", url) as response:
                if response.status_code != 200:
                    raise RuntimeError(f"HTTP Error {response.status_code} on download thread.")
                with open(destination, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        f.write(chunk)

    def _execute_ffmpeg(self, cmd: List[str]) -> None:
        logger.info(f"Executing: {' '.join(cmd)}")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=self.use_shell)
        if res.returncode != 0:
            logger.error(f"FFmpeg pipeline crashed: {res.stderr}")
            raise RuntimeError("FFmpeg processing failure.")

    async def process(self) -> Path:
        try:
            # 1. HLS Stream Muxing
            if self.manifest.is_hls:
                cmd = ["ffmpeg", "-i", self.manifest.video_url, "-c", "copy", "-bsf:a", "aac_adtstoasc", "-y", str(self.output_path)]
                await asyncio.to_thread(self._execute_ffmpeg, cmd)
                return self.output_path

            # 2. DASH Stream Muxing
            if self.manifest.is_dash:
                cmd = ["ffmpeg", "-i", self.manifest.video_url, "-c", "copy", "-y", str(self.output_path)]
                await asyncio.to_thread(self._execute_ffmpeg, cmd)
                return self.output_path

            # 3. Dual-Stream Muxing (Separated Video & Audio Assets Locked)
            if self.manifest.video_url and self.manifest.audio_url:
                logger.info("Executing parallel tracks extraction...")
                await asyncio.gather(
                    self._download_file(self.manifest.video_url, self.v_path),
                    self._download_file(self.manifest.audio_url, self.a_path)
                )
                logger.info("Muxing parallel layers into standard MP4 containment...")
                cmd = [
                    "ffmpeg", "-i", str(self.v_path), "-i", str(self.a_path),
                    "-c:v", "copy", "-c:a", "aac", "-strict", "experimental", "-y", str(self.output_path)
                ]
                await asyncio.to_thread(self._execute_ffmpeg, cmd)
                return self.output_path

            # 4. Singular Stream Asset Layout
            if self.manifest.video_url:
                logger.info("Single file structure detected, launching stream download...")
                await self._download_file(self.manifest.video_url, self.output_path)
                return self.output_path

        finally:
            self.cleanup()

        raise ValueError("Unknown stream structure allocation.")

    def cleanup(self) -> None:
        for p in [self.v_path, self.a_path]:
            if p.exists():
                try: os.remove(p)
                except: pass

# ==========================================
# MODULE C & D: FRONTEND TEMPLATE & FLASK
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Media Scraper Engine</title>
<style>
    body { font-family: sans-serif; background: #0f172a; color: #f8fafc; padding: 50px; text-align: center; }
    .box { background: #1e293b; max-width: 500px; margin: 0 auto; padding: 30px; border-radius: 8px; }
    input { width: 90%; padding: 10px; margin: 15px 0; background: #0f172a; border: 1px solid #334155; color: white; border-radius: 4px; }
    button { width: 94%; padding: 12px; background: #0284c7; border: none; color: white; font-weight: bold; cursor: pointer; border-radius: 4px; }
    button:hover { background: #0369a1; }
    #status { margin-top: 15px; color: #38bdf8; display: none; }
</style></head>
<body>
    <div class="box">
        <h2>Media Scraping Pipeline</h2>
        <form id="scrapForm">
            <input type="url" id="tgtUrl" placeholder="Paste target video URL here..." required>
            <button type="submit" id="btn">Process Video</button>
        </form>
        <div id="status">Intercepting networks, extracting streams... Please wait.</div>
    </div>
    <script>
        document.getElementById('scrapForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('btn');
            const status = document.getElementById('status');
            btn.disabled = true; status.style.display = 'block';
            
            try {
                const res = await fetch('/api/v1/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: document.getElementById('tgtUrl').value })
                });
                if(!res.ok) throw new Error('Failed to download.');
                const blob = await res.blob();
                const dl = document.createElement('a');
                dl.href = window.URL.createObjectURL(blob);
                dl.download = 'extracted_video.mp4';
                dl.click();
                status.innerText = 'Success!';
            } catch (err) {
                status.innerText = 'Error processing data.';
            } finally {
                btn.disabled = false;
            }
        });
    </script>
</body></html>
"""

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/v1/download', methods=['POST'])
def download_stream():
    data = request.get_json() or {}
    try:
        payload = DownloadRequest(url=data.get("url"))
    except ValidationError:
        return jsonify({"detail": "Invalid Request URL Format"}), 400

    scraper = AdaptiveScraper(str(payload.url))
    try:
        manifest = asyncio.run(scraper.run())
        processor = MediaProcessor(manifest)
        final_file = asyncio.run(processor.process())
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

    if not final_file.exists():
        return jsonify({"detail": "Failed to compile file output."}), 500

    def stream_and_purge():
        try:
            with open(final_file, "rb") as fh:
                while chunk := fh.read(65536):
                    yield chunk
        finally:
            if final_file.exists():
                try: os.remove(final_file)
                except: pass

    res = app.response_class(stream_and_purge(), mimetype="video/mp4")
    res.headers["Content-Disposition"] = "attachment; filename=video.mp4"
    return res

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)