#!/usr/bin/env python3
# app_hooks.py — chhoti Flask UI, transcript.py ki working logic ke upar hi
# banaya hai (transcript fetch / gemini call kuch nahi chheda).
# pip install flask google-genai pydantic youtube_transcript_api

import re
import json
from flask import Flask, request, render_template_string, jsonify
from pydantic import BaseModel, Field
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi

GEMINI_API_KEY = "AQ.Ab8RN6IQSmyub6dyT3gUb5GaeU2_ERDaM0eZW-A64Yd-mROsbg"

app = Flask(__name__)


class HookMoment(BaseModel):
    start: str = Field(description="Timestamp MM:SS format")
    end: str = Field(description="Timestamp MM:SS format")
    dialogue: str = Field(description="The key dialogue/line at this moment")
    hook_reason: str = Field(description="Why this moment will hook viewers")
    score: int = Field(description="Virality score 1-10")


def extract_video_id(url):
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
    return match.group(1) if match else None


def get_transcript_data(video_id):
    yt_api = YouTubeTranscriptApi()
    raw_data = yt_api.fetch(video_id, languages=['hi', 'en', 'en-IN'])
    lines = []
    for segment in raw_data:
        start = int(segment.start)
        lines.append(f"[{start // 60:02d}:{start % 60:02d}] {segment.text}")
    return "\n".join(lines)


def analyze_video_hooks(url):
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")

    transcript = get_transcript_data(video_id)
    if not transcript:
        raise ValueError("Transcript nahi mili")

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""इस टाइमस्टैम्प वाली यूट्यूब ट्रांसक्रिप्ट में से 5 सबसे ज्यादा viral/hook-worthy
moments nikaalo. Har moment ke start/end timestamp exact transcript se lena hai.

Transcript Data:
{transcript}
"""
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": list[HookMoment],
        },
    )
    return json.loads(response.text)


PAGE = """
<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<title>Hook Detector</title>
<style>
  body{background:#0b0d12;color:#eef0f6;font-family:'Segoe UI',sans-serif;padding:30px;max-width:800px;margin:0 auto;}
  h1{background:linear-gradient(135deg,#6e5bff,#22d3c4);-webkit-background-clip:text;color:transparent;}
  input{width:70%;padding:12px;border-radius:8px;border:1px solid #262a36;background:#191c25;color:#fff;}
  button{padding:12px 20px;border-radius:8px;border:none;background:linear-gradient(135deg,#6e5bff,#22d3c4);color:#0a0a0f;font-weight:700;cursor:pointer;}
  .card{background:#13151c;border:1px solid #262a36;border-radius:14px;padding:16px;margin-top:14px;}
  .ts{color:#22d3c4;font-weight:700;}
  .score{float:right;background:#191c25;padding:4px 10px;border-radius:999px;font-size:12px;}
  .dim{color:#8a90a4;font-size:13px;margin-top:6px;}
  #status{margin-top:12px;color:#8a90a4;}
</style>
</head>
<body>
  <h1>🔥 YouTube Hook Detector</h1>
  <form id="f">
    <input id="url" placeholder="Paste YouTube URL" required>
    <button type="submit">Analyze</button>
  </form>
  <div id="status"></div>
  <div id="results"></div>

<script>
document.getElementById('f').onsubmit = async (e) => {
  e.preventDefault();
  const url = document.getElementById('url').value;
  document.getElementById('results').innerHTML = '';
  document.getElementById('status').innerText = '⏳ Analyzing...';
  try {
    const res = await fetch('/analyze', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({url})});
    const data = await res.json();
    if (data.error) { document.getElementById('status').innerText = '❌ ' + data.error; return; }
    document.getElementById('status').innerText = `✅ ${data.moments.length} moments found`;
    document.getElementById('results').innerHTML = data.moments.map(m => `
      <div class="card">
        <span class="score">${m.score}/10</span>
        <span class="ts">${m.start} – ${m.end}</span>
        <div style="margin-top:8px">${m.dialogue}</div>
        <div class="dim">${m.hook_reason}</div>
      </div>
    `).join('');
  } catch(err) {
    document.getElementById('status').innerText = '❌ Network error: ' + err.message;
  }
};
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/analyze", methods=["POST"])
def analyze():
    url = (request.json or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL given"}), 400
    try:
        moments = analyze_video_hooks(url)
        return jsonify({"moments": moments})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5050)