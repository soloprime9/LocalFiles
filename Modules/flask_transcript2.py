#!/usr/bin/env python3
# app_hooks.py — better, Opus-Clip-style prompt: hook taxonomy, hook→build→payoff
# structure, standalone-clarity check, diversity constraint, multi-dimension
# scoring. Transcript-fetch logic same rakha hai (jo already fast/working hai).
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
    start: str = Field(description="Timestamp MM:SS, must match transcript exactly")
    end: str = Field(description="Timestamp MM:SS, must match transcript exactly")
    dialogue: str = Field(description="The exact key line(s) from the transcript at this moment")
    hook_type: str = Field(description="One of: tonal_shift, direct_address, hidden_knowledge, pattern_interrupt, controversial_claim, shocking_stat, story_climax, punchline, emotional_peak, strong_question, before_after, myth_bust")
    structure_check: str = Field(description="One sentence confirming the Hook→Build→Payoff arc: what's the opening hook, what builds tension, what's the payoff")
    standalone_clarity: int = Field(description="1-10: can a viewer understand this WITHOUT having watched anything before it?")
    hook_strength: int = Field(description="1-10: how strong is the first 3 seconds at stopping a scroll?")
    emotional_intensity: int = Field(description="1-10: how strong is the emotional pull (shock, curiosity, tension, satisfaction)?")
    quotability: int = Field(description="1-10: how likely is this to be quoted/commented on?")
    virality_score: int = Field(description="0-100 overall score, weighted: standalone_clarity and hook_strength matter most, then emotional_intensity, then quotability")
    reason: str = Field(description="2-3 sentences: why this will hook viewers, referencing the specific line")


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


HOOK_PROMPT_TEMPLATE = """You are an expert short-form video editor, trained on the same
principles professional AI clipping tools (Opus Clip, ClipAnything) use to find
viral moments in long-form video. You will analyze a timestamped transcript and
find the {num_clips} strongest standalone clips for YouTube Shorts / Reels / TikTok.

## STEP 1 — Understand the video
Read the full transcript below. Identify the overall topic, tone, and where the
emotional/narrative peaks are.

## STEP 2 — Find candidates using this hook taxonomy
Look specifically for these patterns (a strong clip usually matches 1-2 of these):
- **tonal_shift**: the speaker's tone/energy suddenly changes (calm → intense, joking → serious)
- **direct_address**: speaker turns to camera/audience with "you", "here's the thing", "let me tell you"
- **hidden_knowledge**: promises information most people don't know ("what nobody tells you about...")
- **pattern_interrupt**: says something that contradicts what the viewer expects
- **controversial_claim**: a statement people will disagree with or debate in comments
- **shocking_stat**: a surprising number or fact
- **story_climax**: the turning point of a story being told
- **punchline**: a joke or witty payoff
- **emotional_peak**: raw emotion — anger, vulnerability, triumph, grief
- **strong_question**: a question posed that makes the viewer want the answer
- **before_after**: a clear transformation or contrast is described
- **myth_bust**: correcting a common misconception

## STEP 3 — For EVERY candidate, verify structure (reject if it fails this)
Each clip MUST have a Hook→Build→Payoff arc within its own boundaries:
- **Hook** (first ~3 seconds of the clip): the line that stops a scroll
- **Build**: tension, curiosity, or context that keeps them watching
- **Payoff**: resolution — an answer, a punchline, a reveal, an emotional release
If a moment is just one good line with no build/payoff around it, EXTEND the
clip boundaries to include the setup and resolution, or reject it if none exists
in the transcript.

## STEP 4 — Standalone-clarity filter (reject if it fails this)
A viewer who has NOT watched anything before this clip must be able to fully
understand it. If the clip depends on knowing who a person is, what happened
earlier, or unexplained pronouns/references — either the clip's start must move
earlier to include that context, or it must be rejected.

## STEP 5 — Diversity
The {num_clips} clips must come from DIFFERENT parts of the video and should not
all make the same point — spread them across the timeline, cover different
topics/emotional beats if the video has more than one.

## STEP 6 — Score
For each surviving candidate, score standalone_clarity, hook_strength,
emotional_intensity, and quotability (each 1-10), then compute virality_score
(0-100) weighted roughly: 35% standalone_clarity, 35% hook_strength, 20%
emotional_intensity, 10% quotability.

## RULES
- start/end MUST be real timestamps that appear in the transcript below — never invent times.
- Each clip should be roughly {min_len}-{max_len} seconds long (extend for Hook→Build→Payoff if needed, within reason).
- Clips must not overlap.
- Only return clips that pass BOTH the structure check and the standalone-clarity filter.

TRANSCRIPT:
{transcript}
"""


def analyze_video_hooks(url, num_clips=5, min_len=15, max_len=60):
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")

    transcript = get_transcript_data(video_id)
    if not transcript:
        raise ValueError("Transcript nahi mili")

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = HOOK_PROMPT_TEMPLATE.format(
        num_clips=num_clips, min_len=min_len, max_len=max_len, transcript=transcript
    )

    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": list[HookMoment],
            "temperature": 0.3,  # lower = more consistent structure-following
        },
    )
    moments = json.loads(response.text)
    moments.sort(key=lambda m: m.get("virality_score", 0), reverse=True)
    return moments


PAGE = """
<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<title>Hook Detector</title>
<style>
  body{background:#0b0d12;color:#eef0f6;font-family:'Segoe UI',sans-serif;padding:30px;max-width:820px;margin:0 auto;}
  h1{background:linear-gradient(135deg,#6e5bff,#22d3c4);-webkit-background-clip:text;color:transparent;}
  input{width:65%;padding:12px;border-radius:8px;border:1px solid #262a36;background:#191c25;color:#fff;}
  button{padding:12px 20px;border-radius:8px;border:none;background:linear-gradient(135deg,#6e5bff,#22d3c4);color:#0a0a0f;font-weight:700;cursor:pointer;}
  .card{background:#13151c;border:1px solid #262a36;border-radius:14px;padding:16px;margin-top:14px;}
  .ts{color:#22d3c4;font-weight:700;}
  .score{float:right;background:linear-gradient(135deg,#6e5bff,#22d3c4);color:#0a0a0f;padding:4px 12px;border-radius:999px;font-size:13px;font-weight:800;}
  .dim{color:#8a90a4;font-size:13px;margin-top:6px;}
  .subscores{display:flex;gap:10px;margin-top:10px;flex-wrap:wrap;}
  .subscores span{background:#191c25;border:1px solid #262a36;padding:3px 9px;border-radius:8px;font-size:11px;color:#8a90a4;}
  .htype{display:inline-block;background:#191c25;color:#22d3c4;padding:2px 8px;border-radius:6px;font-size:11px;margin-top:6px;}
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
  document.getElementById('status').innerText = '⏳ Analyzing (deep pass, thoda time lagega)...';
  try {
    const res = await fetch('/analyze', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({url})});
    const data = await res.json();
    if (data.error) { document.getElementById('status').innerText = '❌ ' + data.error; return; }
    document.getElementById('status').innerText = `✅ ${data.moments.length} moments found`;
    document.getElementById('results').innerHTML = data.moments.map(m => `
      <div class="card">
        <span class="score">${m.virality_score}/100</span>
        <span class="ts">${m.start} – ${m.end}</span>
        <div class="htype">${m.hook_type}</div>
        <div style="margin-top:8px">${m.dialogue}</div>
        <div class="dim">${m.reason}</div>
        <div class="dim" style="font-style:italic">Structure: ${m.structure_check}</div>
        <div class="subscores">
          <span>Standalone: ${m.standalone_clarity}/10</span>
          <span>Hook: ${m.hook_strength}/10</span>
          <span>Emotion: ${m.emotional_intensity}/10</span>
          <span>Quotable: ${m.quotability}/10</span>
        </div>
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