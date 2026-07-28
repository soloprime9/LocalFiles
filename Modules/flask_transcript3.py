#!/usr/bin/env python3
# app_hooks.py — ADVANCED 2-stage pipeline:
#   Stage 1: free-form candidate discovery (over-generate, chain-of-thought)
#   Stage 2: structured selection + strict filtering
#   + deterministic scoring, overlap removal, timestamp snapping (all in Python,
#     not trusted to the model) — this is what actually closes the gap with
#     tools like Opus Clip, more than prompt wording alone.
#
# pip install flask google-genai pydantic youtube_transcript_api

import re
import json
from flask import Flask, request, render_template_string, jsonify
from pydantic import BaseModel, Field
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi

GEMINI_API_KEY = "AQ.Ab8RN6IQSmyub6dyT3gUb5GaeU2_ERDaM0eZW-A64Yd-mROsbg"
MODEL = "gemini-flash-latest"

app = Flask(__name__)


# ── Stage 2 output schema ───────────────────────────────────────────────
class HookMoment(BaseModel):
    start: str = Field(description="Timestamp MM:SS, must match transcript exactly")
    end: str = Field(description="Timestamp MM:SS, must match transcript exactly")
    dialogue: str = Field(description="The exact key line(s) from the transcript at this moment")
    hook_type: str = Field(description="One of: tonal_shift, direct_address, hidden_knowledge, pattern_interrupt, controversial_claim, shocking_stat, story_climax, punchline, emotional_peak, strong_question, before_after, myth_bust")
    structure_check: str = Field(description="One sentence: what's the Hook, what's the Build, what's the Payoff")
    standalone_clarity: int = Field(description="1-10: understandable with ZERO prior context")
    hook_strength: int = Field(description="1-10: strength of first 3 seconds")
    emotional_intensity: int = Field(description="1-10: strength of emotional pull")
    quotability: int = Field(description="1-10: likely to be quoted/commented on")


# ── helpers ──────────────────────────────────────────────────────────────

def extract_video_id(url):
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
    return match.group(1) if match else None


def get_cues(video_id):
    """Returns list of {start, end, text} in seconds — used both for the
    transcript text AND for snapping final timestamps to real boundaries."""
    yt_api = YouTubeTranscriptApi()
    raw_data = yt_api.fetch(video_id, languages=['hi', 'en', 'en-IN'])
    cues = []
    items = list(raw_data)
    for i, seg in enumerate(items):
        start = float(seg.start)
        dur = float(getattr(seg, "duration", 2.0) or 2.0)
        end = start + dur
        cues.append({"start": start, "end": end, "text": seg.text})
    return cues


def cues_to_transcript_text(cues):
    lines = []
    for c in cues:
        m, s = divmod(int(c["start"]), 60)
        lines.append(f"[{m:02d}:{s:02d}] {c['text']}")
    return "\n".join(lines)


def mmss_to_sec(ts):
    parts = ts.strip().split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0.0


def snap_to_cue(t, cues, prefer="start"):
    if not cues:
        return t
    best = min(cues, key=lambda c: abs((c["start"] if prefer == "start" else c["end"]) - t))
    return best["start"] if prefer == "start" else best["end"]


# ── Stage 1: free-form candidate discovery (chain-of-thought, over-generate) ──

STAGE1_PROMPT = """You are an expert short-form video editor with the same eye for
viral moments as professional AI clipping tools (Opus Clip, ClipAnything). Think
step by step, out loud, in prose (not JSON yet).

TRANSCRIPT (timestamped):
{transcript}

Do this analysis:
1. Summarize the video's overall topic/arc in 2-3 sentences.
2. Identify EVERY moment that could work as a short-form hook — over-generate,
   find at least {overgenerate} candidates even if some are weak. For each,
   note: timestamp range, what type of hook it is (tonal shift, direct address,
   hidden-knowledge promise, pattern interrupt, controversial claim, shocking
   stat, story climax, punchline, emotional peak, strong question, before/after,
   myth-bust), and whether it has a clear Hook→Build→Payoff arc within its own
   boundaries.
3. For each candidate, critically note ONE weakness (e.g. "needs earlier context
   to make sense", "hook is strong but no real payoff", "similar to candidate #2").
4. Explicitly flag which candidates overlap with each other or repeat the same
   point — we only want to keep distinct ones.

Be thorough and critical — this is a working analysis, not the final answer.
"""


def stage1_analysis(transcript, num_clips):
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = STAGE1_PROMPT.format(transcript=transcript, overgenerate=num_clips * 3)
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={"temperature": 0.5, "max_output_tokens": 4096},
    )
    return response.text


# ── Stage 2: structured selection from stage-1 analysis ────────────────────

STAGE2_PROMPT = """You previously did this analysis of a video transcript:

--- YOUR ANALYSIS ---
{analysis}
--- END ANALYSIS ---

Original timestamped transcript (for exact wording/timestamps):
{transcript}

Now select the FINAL {num_clips} best clips, applying these hard filters:
- REJECT any candidate without a real Hook→Build→Payoff arc (extend its
  boundaries to include the build/payoff if the transcript allows, otherwise drop it).
- REJECT any candidate that isn't understandable with ZERO prior context
  (unexplained names/pronouns/references = reject or extend to include the context).
- REJECT redundant candidates that overlap in time or repeat the same point as
  a stronger candidate — keep only the best one per idea.
- The final {num_clips} clips must be spread across DIFFERENT parts of the
  video/topic, not clustered in one section.
- Each clip should be roughly {min_len}-{max_len} seconds (extend for a full
  Hook→Build→Payoff arc if genuinely needed).
- start/end MUST be real timestamps from the transcript — never invent times.
- Clips must not overlap each other.

Score each surviving clip honestly on the 4 dimensions (1-10 each) — don't
inflate scores, most real clips are 5-8, reserve 9-10 for truly exceptional moments.
"""


def stage2_select(analysis, transcript, num_clips, min_len, max_len):
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = STAGE2_PROMPT.format(
        analysis=analysis, transcript=transcript,
        num_clips=num_clips, min_len=min_len, max_len=max_len,
    )
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": list[HookMoment],
            "temperature": 0.15,  # low — this is extraction/filtering, not creativity
        },
    )
    return json.loads(response.text)


# ── deterministic post-processing (Python, not the model) ──────────────────

WEIGHTS = {"standalone_clarity": 0.35, "hook_strength": 0.35,
           "emotional_intensity": 0.20, "quotability": 0.10}


def compute_virality_score(m):
    raw = sum(m[k] * w for k, w in WEIGHTS.items())  # each sub-score is 1-10
    return round(raw * 10)  # scale to 0-100


def postprocess(moments, cues, total_duration):
    cleaned = []
    for m in moments:
        start = snap_to_cue(mmss_to_sec(m["start"]), cues, "start")
        end = snap_to_cue(mmss_to_sec(m["end"]), cues, "end")
        if total_duration:
            end = min(end, total_duration)
        if end - start < 5:
            continue
        m["start_sec"] = round(start, 2)
        m["end_sec"] = round(end, 2)
        m["virality_score"] = compute_virality_score(m)
        cleaned.append(m)

    # Overlap removal: greedy by score, skip anything overlapping an already-kept clip
    cleaned.sort(key=lambda m: m["virality_score"], reverse=True)
    final = []
    for m in cleaned:
        overlaps = any(not (m["end_sec"] <= f["start_sec"] or m["start_sec"] >= f["end_sec"]) for f in final)
        if not overlaps:
            final.append(m)
    final.sort(key=lambda m: m["start_sec"])  # chronological for display
    return final


def analyze_video_hooks(url, num_clips=5, min_len=15, max_len=60):
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")

    cues = get_cues(video_id)
    if not cues:
        raise ValueError("Transcript nahi mili")
    transcript = cues_to_transcript_text(cues)
    total_duration = cues[-1]["end"]

    analysis = stage1_analysis(transcript, num_clips)
    raw_moments = stage2_select(analysis, transcript, num_clips, min_len, max_len)
    final_moments = postprocess(raw_moments, cues, total_duration)
    return final_moments, analysis


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
  <h1>🔥 YouTube Hook Detector (2-stage)</h1>
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
  document.getElementById('status').innerText = '⏳ Stage 1: candidates dhundh rahe hain...';
  try {
    const res = await fetch('/analyze', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({url})});
    const data = await res.json();
    if (data.error) { document.getElementById('status').innerText = '❌ ' + data.error; return; }
    document.getElementById('status').innerText = `✅ ${data.moments.length} final moments (after filtering + overlap removal)`;
    document.getElementById('results').innerHTML = data.moments.map(m => `
      <div class="card">
        <span class="score">${m.virality_score}/100</span>
        <span class="ts">${m.start} – ${m.end}</span>
        <div class="htype">${m.hook_type}</div>
        <div style="margin-top:8px">${m.dialogue}</div>
        <div class="dim">${m.reason || ''}</div>
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
        moments, _analysis = analyze_video_hooks(url)
        return jsonify({"moments": moments})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5001)