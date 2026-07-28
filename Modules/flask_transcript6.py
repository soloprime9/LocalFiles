#!/usr/bin/env python3
# app_hooks.py — 2-stage Hook Detector, Flask version, with a LIVE key-pool
# dashboard + auto quota-protection.
#
# Ye file pehle wali "hooks_pool.py" (jisme multi-key rotation + cache tha)
# ko doosri wali "app_hooks.py" (Flask + UI) jaisa bana deti hai — aur upar
# se teen naye cheeze add karti hai jo tumhare 429 / 403 wale problem ko
# seedha target karti hain:
#
#   1) LIVE STATUS PANEL (/status, jise UI har 2s me poll karta hai):
#      - har API key ka real-time status: Idle / Busy / Cooldown (countdown
#        ke saath)
#      - har key par pichle 60 second me kitni calls hui, aur RPM limit ke
#        against kitna quota bacha hai
#      - ek "activity log" jo dikhata hai abhi Stage 1 chal rahi hai ya
#        Stage 2, kis key/model se, aur agar koi rate-limit/403 laga to
#        wahan bhi ek line print hoti hai
#
#   2) SELF-THROTTLING (RPM_LIMITS): pehle wala code sirf 429 aane ke BAAD
#      react karta tha (reactive). Ab hum khud track karte hain ki har key
#      ne pichle 60s me kitni calls maari hain, aur agar limit ke paas
#      pahuch rahe hain to request bhejne se PEHLE hi thoda wait kar lete
#      hain — isse 429 aata hi kam hai.
#
#   3) DUPLICATE-CALL PROTECTION (in-flight dedup): agar same video ke liye
#      do requests ek saath aa jaayein (double-click, ya browser retry), to
#      pehle wala code Gemini ko 2 baar call kar deta — seedha quota waste.
#      Ab dusri request Gemini ko call hi nahi karti, wo bas pehli wali ka
#      result wait karke use kar leti hai.
#
#   4) MODEL FALLBACK ON 403: "model unavailable" (403) zyadatar 2 wajah se
#      aata hai — (a) model ka naam is API key ke project me enabled nahi,
#      ya (b) us model ka free-tier access hata diya gaya. Isliye har stage
#      ke liye ek MODEL CANDIDATES list di hai — 403 milte hi wahi key
#      agle candidate model par try karti hai, sirf crash nahi hoti.
#
# ⚠️ ZAROORI BAAT (please read): Gemini API free tier ke rate-limits
# PER-PROJECT hote hain, per-key nahi. Matlab agar tumhari saari
# API_KEYS ek hi Google Cloud project ke andar bani hain, to unhe rotate
# karne se quota nahi badhega — sabki cooldown saath me lagegi. Multi-key
# rotation TABHI kaam karta hai jab har key ek ALAG Google account /
# ALAG project se ho. (Jaisa tumne comment me likha bhi tha — "2-3 alag
# Google accounts se" — bas isko strictly follow karna.)
#
# pip install flask google-genai pydantic youtube_transcript_api

import re
import os
import json
import time
import hashlib
import threading
import itertools
from collections import deque

from flask import Flask, request, render_template_string, jsonify
from pydantic import BaseModel, Field
from google import genai
from google.genai import errors as genai_errors
from youtube_transcript_api import YouTubeTranscriptApi

# ── Apni saari free API keys yahan daalo (2-3 ALAG Google accounts se!) ────
API_KEYS = [
    "AQ.Ab8RN6IQSmyub6dyT3gUb5GaeU2_ERDaM0eZW-A64Yd-mROsbg",
    "AQ.Ab8RN6LaUL4o0weWHLQ9F6cW__Ko_qEZLNX1PGJk-VuquywNmQ",
    "AQ.Ab8RN6ISugABRVrHSOaniSVy8TT3wl1uwzaESmiijtn8aSo_aw",
]

# Har stage ke liye "candidate" models — pehla wala try hota hai, 403 aane
# par usi key se agla candidate try hota hai. Free-tier me model names/aliases
# kabhi-kabhi hat jaate hain, isliye ek se zyada rakhna safer hai.
STAGE1_MODEL_CANDIDATES = [
    "gemini-flash-lite-latest",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
]
STAGE2_MODEL_CANDIDATES = [
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]

# Google ke free-tier RPM (requests-per-minute) — ye badalte rehte hain,
# apni AI Studio dashboard me exact number check kar lena aur yahan update
# kar dena. Thoda conservative rakha hai taaki 429 se pehle hi ruk jaayein.
RPM_LIMITS = {
    "gemini-flash-lite-latest": 12,
    "gemini-2.5-flash-lite": 12,
    "gemini-2.0-flash-lite": 12,
    "gemini-flash-latest": 8,
    "gemini-2.5-flash": 8,
    "gemini-2.0-flash": 8,
}
DEFAULT_RPM = 8

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 din


# ── Activity log: "abhi kya ho raha hai" wala live feed ───────────────────
_activity = deque(maxlen=60)
_activity_lock = threading.Lock()


def log_activity(msg):
    with _activity_lock:
        _activity.append({"t": time.strftime("%H:%M:%S"), "msg": msg})
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def get_activity():
    with _activity_lock:
        return list(_activity)[::-1]  # naya sabse upar


# ── Multi-key pool: per-key cooldown + RPM self-throttle + status ─────────
class KeyPool:
    def __init__(self, keys):
        if not keys or keys[0].startswith("KEY_"):
            raise RuntimeError("API_KEYS list me apni asli keys daalo (app_hooks.py ke top par).")
        self.keys = keys
        self.lock = threading.Lock()
        self._cycle = itertools.cycle(keys)

        self.cooldown_until = {k: 0.0 for k in keys}
        self.cooldown_reason = {k: None for k in keys}
        self.status = {k: "idle" for k in keys}          # idle | busy
        self.total_calls = {k: 0 for k in keys}
        # per key, per model: timestamps of calls in the last 60s
        self.call_log = {k: {} for k in keys}

    # -- RPM self-throttle: agar limit chhoone wale hain to wait time do --
    def _rpm_wait(self, key, model):
        limit = RPM_LIMITS.get(model, DEFAULT_RPM)
        dq = self.call_log[key].setdefault(model, deque())
        now = time.time()
        while dq and now - dq[0] > 60:
            dq.popleft()
        if len(dq) >= limit:
            return max(0.0, 60 - (now - dq[0]) + 0.5)
        return 0.0

    def _record_call(self, key, model):
        self.call_log[key].setdefault(model, deque()).append(time.time())
        self.total_calls[key] += 1

    def _best_key(self, model):
        """Sabse pehle koi bhi FREE key dhoondo (no cooldown, RPM room hai).
        Agar koi free nahi to jo sabse jaldi free hogi wahi lauta do."""
        with self.lock:
            now = time.time()
            free_candidates = []
            for _ in range(len(self.keys)):
                k = next(self._cycle)
                if self.cooldown_until[k] <= now and self._rpm_wait(k, model) == 0:
                    free_candidates.append(k)
                    break
            if free_candidates:
                return free_candidates[0], 0.0

            best_key, best_wait = None, None
            for k in self.keys:
                wait = max(0.0, self.cooldown_until[k] - now, self._rpm_wait(k, model))
                if best_wait is None or wait < best_wait:
                    best_key, best_wait = k, wait
            return best_key, best_wait

    def _mark_cooldown(self, key, seconds, reason):
        with self.lock:
            self.cooldown_until[key] = time.time() + seconds
            self.cooldown_reason[key] = reason

    def key_label(self, key):
        return f"...{key[-6:]}"

    def snapshot(self):
        """/status endpoint ke liye — har key ka live state."""
        now = time.time()
        rows = []
        for i, k in enumerate(self.keys, 1):
            cd_left = max(0.0, self.cooldown_until[k] - now)
            calls_60s = {m: len(dq) for m, dq in self.call_log[k].items()}
            rpm_room = {
                m: f"{len(dq)}/{RPM_LIMITS.get(m, DEFAULT_RPM)} used"
                for m, dq in self.call_log[k].items()
            }
            if cd_left > 0:
                state = "cooldown"
            elif self.status[k] == "busy":
                state = "busy"
            else:
                state = "idle"
            rows.append({
                "label": f"Key #{i} ({self.key_label(k)})",
                "state": state,
                "cooldown_seconds_left": round(cd_left, 1),
                "cooldown_reason": self.cooldown_reason[k],
                "total_calls": self.total_calls[k],
                "calls_last_60s": calls_60s,
                "rpm_usage": rpm_room,
            })
        return rows

    def call(self, model_candidates, fn, max_attempts=8):
        """fn(client, model) -> response. Rotates keys AND falls back across
        model_candidates. Self-throttles on RPM before ever hitting 429."""
        last_err = None
        model_idx = 0
        for attempt in range(max_attempts):
            model = model_candidates[min(model_idx, len(model_candidates) - 1)]
            key, wait = self._best_key(model)
            if wait > 0:
                log_activity(f"⏳ Saari keys busy/cooldown/RPM-limit me hain — {wait:.0f}s wait ({model})...")
                time.sleep(wait)
                key, _ = self._best_key(model)

            self.status[key] = "busy"
            log_activity(f"▶️  {self.key_label(key)} se call ja rahi hai — model={model}")
            client = genai.Client(api_key=key)
            try:
                self._record_call(key, model)
                result = fn(client, model)
                self.status[key] = "idle"
                log_activity(f"✅ {self.key_label(key)} ({model}) — response mil gaya")
                return result
            except genai_errors.APIError as e:
                self.status[key] = "idle"
                last_err = e
                code = getattr(e, "code", None)
                if code == 429:
                    cooldown = 60
                    m = re.search(r"retry in (\d+(?:\.\d+)?)s", str(e), re.IGNORECASE)
                    if m:
                        cooldown = float(m.group(1)) + 2
                    self._mark_cooldown(key, cooldown, f"429 rate-limit ({model})")
                    log_activity(f"🔁 {self.key_label(key)} rate-limited ({cooldown:.0f}s cooldown) — dusri key try karenge...")
                    continue
                if code == 403:
                    # Model ye key/project ke liye available nahi — isi key se
                    # agla candidate model try karo, dusri key waste mat karo.
                    self._mark_cooldown(key, 15, f"403 model unavailable ({model})")
                    model_idx += 1
                    log_activity(f"⚠️  {self.key_label(key)} par '{model}' 403 (unavailable) — agla model candidate try kar rahe hain...")
                    continue
                if code == 503:
                    log_activity("⚠️  Google server busy (503) — 5s baad retry...")
                    time.sleep(5)
                    continue
                log_activity(f"❌ {self.key_label(key)} par na-sambhalne wali error: {e}")
                raise
        raise last_err


pool = KeyPool(API_KEYS)


# ── Cache (auto-expiry) ─────────────────────────────────────────────────
def _cache_path(video_id, num_clips, min_len, max_len):
    key = f"{video_id}_{num_clips}_{min_len}_{max_len}"
    h = hashlib.md5(key.encode()).hexdigest()[:10]
    return os.path.join(CACHE_DIR, f"{video_id}_{h}.json")


def cleanup_old_cache():
    now = time.time()
    removed = 0
    for fname in os.listdir(CACHE_DIR):
        fpath = os.path.join(CACHE_DIR, fname)
        try:
            if now - os.path.getmtime(fpath) > CACHE_TTL_SECONDS:
                os.remove(fpath)
                removed += 1
        except OSError:
            pass
    if removed:
        log_activity(f"🧹 {removed} purani cache file(s) delete ki (7+ din purani).")


def get_cached(video_id, num_clips, min_len, max_len):
    path = _cache_path(video_id, num_clips, min_len, max_len)
    if not os.path.exists(path):
        return None
    if time.time() - os.path.getmtime(path) > CACHE_TTL_SECONDS:
        os.remove(path)
        return None
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("moments")


def save_cache(video_id, num_clips, min_len, max_len, moments):
    path = _cache_path(video_id, num_clips, min_len, max_len)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"cached_at": time.time(), "moments": moments}, f, ensure_ascii=False, indent=2)


# ── Duplicate-call protection: same request 2 baar Gemini ko mat bhejo ────
_inflight_lock = threading.Lock()
_inflight_events = {}   # cache_key -> threading.Event
_inflight_results = {}  # cache_key -> result (ya exception)


def run_dedup(cache_key, work_fn):
    """Agar isi cache_key ke liye ek call pehle se chal rahi hai, to naya
    request Gemini ko dobara call NAHI karta — bas pehle wale ka result wait
    karta hai. Isse double-click / duplicate requests se quota waste nahi
    hoti."""
    with _inflight_lock:
        existing = _inflight_events.get(cache_key)
        if existing is not None:
            is_leader = False
        else:
            existing = threading.Event()
            _inflight_events[cache_key] = existing
            is_leader = True

    if not is_leader:
        log_activity(f"🟡 '{cache_key}' ke liye request already chal rahi hai — naya call skip, result wait kar rahe hain...")
        existing.wait()
        result = _inflight_results.get(cache_key)
        if isinstance(result, Exception):
            raise result
        return result

    try:
        result = work_fn()
        _inflight_results[cache_key] = result
        return result
    except Exception as e:
        _inflight_results[cache_key] = e
        raise
    finally:
        existing.set()
        with _inflight_lock:
            _inflight_events.pop(cache_key, None)
            _inflight_results.pop(cache_key, None)


# ── Schema ───────────────────────────────────────────────────────────────
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


# ── Transcript helpers ──────────────────────────────────────────────────
def extract_video_id(url):
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
    return match.group(1) if match else None


def get_cues(video_id):
    yt_api = YouTubeTranscriptApi()
    raw_data = yt_api.fetch(video_id, languages=['hi', 'en', 'en-IN'])
    cues = []
    for seg in raw_data:
        start = float(seg.start)
        dur = float(getattr(seg, "duration", 2.0) or 2.0)
        cues.append({"start": start, "end": start + dur, "text": seg.text})
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


# ── Stage 1: free-form candidate discovery ─────────────────────────────
STAGE1_PROMPT = """You are an expert short-form video editor with the same eye for
viral moments as professional AI clipping tools (Opus Clip, ClipAnything). Think
step by step, out loud, in prose (not JSON yet).

TRANSCRIPT (timestamped):
{transcript}

Do this analysis:
1. Summarize the video's overall topic/arc in 2-3 sentences.
2. Identify EVERY moment that could work as a short-form hook — over-generate,
   find at least {overgenerate} candidates even if some are weak. For each,
   note: timestamp range, hook type, whether it has a clear Hook->Build->Payoff arc.
3. For each candidate, critically note ONE weakness.
4. Flag which candidates overlap or repeat the same point.
"""


def stage1_analysis(transcript, num_clips):
    prompt = STAGE1_PROMPT.format(transcript=transcript, overgenerate=num_clips * 3)

    def _call(client, model):
        return client.models.generate_content(
            model=model,
            contents=prompt,
            config={"temperature": 0.5, "max_output_tokens": 2048},
        )

    return pool.call(STAGE1_MODEL_CANDIDATES, _call).text


# ── Stage 2: structured selection ──────────────────────────────────────
STAGE2_PROMPT = """You previously did this analysis of a video transcript:

--- YOUR ANALYSIS ---
{analysis}
--- END ANALYSIS ---

Original timestamped transcript (for exact wording/timestamps):
{transcript}

Now select the FINAL {num_clips} best clips, applying these hard filters:
- REJECT any candidate without a real Hook->Build->Payoff arc.
- REJECT any candidate that isn't understandable with ZERO prior context.
- REJECT redundant candidates that overlap or repeat a stronger candidate.
- The final {num_clips} clips must be spread across DIFFERENT parts of the video.
- Each clip should be roughly {min_len}-{max_len} seconds.
- start/end MUST be real timestamps from the transcript.
- Clips must not overlap each other.
Score each surviving clip honestly (1-10 each), don't inflate scores.
"""


def stage2_select(analysis, transcript, num_clips, min_len, max_len):
    prompt = STAGE2_PROMPT.format(
        analysis=analysis, transcript=transcript,
        num_clips=num_clips, min_len=min_len, max_len=max_len,
    )

    def _call(client, model):
        return client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": list[HookMoment],
                "temperature": 0.15,
            },
        )

    return json.loads(pool.call(STAGE2_MODEL_CANDIDATES, _call).text)


# ── Deterministic scoring + overlap removal ────────────────────────────
WEIGHTS = {"standalone_clarity": 0.35, "hook_strength": 0.35,
           "emotional_intensity": 0.20, "quotability": 0.10}


def compute_virality_score(m):
    raw = sum(m[k] * w for k, w in WEIGHTS.items())
    return round(raw * 10)


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

    cleaned.sort(key=lambda m: m["virality_score"], reverse=True)
    final = []
    for m in cleaned:
        overlaps = any(not (m["end_sec"] <= f["start_sec"] or m["start_sec"] >= f["end_sec"]) for f in final)
        if not overlaps:
            final.append(m)
    final.sort(key=lambda m: m["start_sec"])
    return final


# ── Main pipeline (cache + dedup + pool, sab combined) ─────────────────
def _do_analyze(video_id, num_clips, min_len, max_len):
    cues = get_cues(video_id)
    if not cues:
        raise ValueError("Transcript nahi mili")
    transcript = cues_to_transcript_text(cues)
    total_duration = cues[-1]["end"]

    log_activity(f"🚀 '{video_id}' ke liye Stage 1 (candidate discovery) shuru...")
    analysis = stage1_analysis(transcript, num_clips)

    log_activity(f"🚀 '{video_id}' ke liye Stage 2 (final selection) shuru...")
    raw_moments = stage2_select(analysis, transcript, num_clips, min_len, max_len)

    final_moments = postprocess(raw_moments, cues, total_duration)
    save_cache(video_id, num_clips, min_len, max_len, final_moments)
    log_activity(f"🏁 '{video_id}' — {len(final_moments)} final clips ready, cache me save ho gaye.")
    return final_moments


def analyze_video_hooks(url, num_clips=5, min_len=15, max_len=60, force_refresh=False):
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")

    cache_key = f"{video_id}_{num_clips}_{min_len}_{max_len}"

    if not force_refresh:
        cached = get_cached(video_id, num_clips, min_len, max_len)
        if cached is not None:
            log_activity(f"✅ Cache hit for {video_id} — 0 API calls.")
            return cached

    # Dedup ke andar hi asli kaam hota hai — agar koi aur request isi
    # cache_key ke liye already chal rahi hai to Gemini dobara call nahi hoga.
    return run_dedup(cache_key, lambda: _do_analyze(video_id, num_clips, min_len, max_len))


# ── Flask app ────────────────────────────────────────────────────────────
app = Flask(__name__)

PAGE = """
<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<title>Hook Detector</title>
<style>
  *{box-sizing:border-box;}
  body{background:#0b0d12;color:#eef0f6;font-family:'Segoe UI',sans-serif;padding:24px;margin:0;}
  .wrap{max-width:1200px;margin:0 auto;display:grid;grid-template-columns:1.4fr 1fr;gap:22px;}
  @media (max-width:900px){.wrap{grid-template-columns:1fr;}}
  h1{background:linear-gradient(135deg,#6e5bff,#22d3c4);-webkit-background-clip:text;color:transparent;margin-bottom:4px;}
  h2{font-size:16px;color:#8a90a4;text-transform:uppercase;letter-spacing:.05em;margin:0 0 10px;}
  input{width:60%;padding:12px;border-radius:8px;border:1px solid #262a36;background:#191c25;color:#fff;}
  select,input[type=number]{padding:10px;border-radius:8px;border:1px solid #262a36;background:#191c25;color:#fff;margin-left:6px;}
  button{padding:12px 20px;border-radius:8px;border:none;background:linear-gradient(135deg,#6e5bff,#22d3c4);color:#0a0a0f;font-weight:700;cursor:pointer;}
  button:disabled{opacity:.5;cursor:not-allowed;}
  .card{background:#13151c;border:1px solid #262a36;border-radius:14px;padding:16px;margin-top:14px;}
  .ts{color:#22d3c4;font-weight:700;}
  .score{float:right;background:linear-gradient(135deg,#6e5bff,#22d3c4);color:#0a0a0f;padding:4px 12px;border-radius:999px;font-size:13px;font-weight:800;}
  .dim{color:#8a90a4;font-size:13px;margin-top:6px;}
  .subscores{display:flex;gap:10px;margin-top:10px;flex-wrap:wrap;}
  .subscores span{background:#191c25;border:1px solid #262a36;padding:3px 9px;border-radius:8px;font-size:11px;color:#8a90a4;}
  .htype{display:inline-block;background:#191c25;color:#22d3c4;padding:2px 8px;border-radius:6px;font-size:11px;margin-top:6px;}
  #status{margin-top:12px;color:#8a90a4;}
  .panel{background:#13151c;border:1px solid #262a36;border-radius:14px;padding:16px;margin-bottom:16px;}
  .keyrow{border:1px solid #262a36;border-radius:10px;padding:10px 12px;margin-bottom:10px;}
  .badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:11px;font-weight:800;text-transform:uppercase;}
  .badge.idle{background:#16351f;color:#3ecf6a;}
  .badge.busy{background:#2a2a4a;color:#8b8bff;}
  .badge.cooldown{background:#3a2416;color:#ff9d4d;}
  .keymeta{color:#8a90a4;font-size:12px;margin-top:6px;}
  .log{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:#8a90a4;max-height:260px;overflow-y:auto;}
  .log div{padding:3px 0;border-bottom:1px solid #1c1f29;}
  .log .t{color:#22d3c4;margin-right:6px;}
  .opts{margin-top:10px;color:#8a90a4;font-size:13px;}
</style>
</head>
<body>
<div class="wrap">
  <div>
    <h1>🔥 YouTube Hook Detector</h1>
    <form id="f">
      <input id="url" placeholder="Paste YouTube URL" required>
      <button type="submit" id="submitBtn">Analyze</button>
      <div class="opts">
        Clips: <input type="number" id="numClips" value="5" min="1" max="15" style="width:60px">
        Min len(s): <input type="number" id="minLen" value="15" min="5" style="width:70px">
        Max len(s): <input type="number" id="maxLen" value="60" min="10" style="width:70px">
      </div>
    </form>
    <div id="status"></div>
    <div id="results"></div>
  </div>

  <div>
    <div class="panel">
      <h2>🔑 Live Key Pool Status</h2>
      <div id="keys">Loading...</div>
    </div>
    <div class="panel">
      <h2>📜 Activity Log</h2>
      <div class="log" id="log">Loading...</div>
    </div>
  </div>
</div>

<script>
let busy = false;

document.getElementById('f').onsubmit = async (e) => {
  e.preventDefault();
  if (busy) return;
  busy = true;
  document.getElementById('submitBtn').disabled = true;
  const url = document.getElementById('url').value;
  const num_clips = parseInt(document.getElementById('numClips').value || '5');
  const min_len = parseInt(document.getElementById('minLen').value || '15');
  const max_len = parseInt(document.getElementById('maxLen').value || '60');
  document.getElementById('results').innerHTML = '';
  document.getElementById('status').innerText = '⏳ Analysis shuru ho rahi hai — status panel me live progress dekho...';
  try {
    const res = await fetch('/analyze', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({url, num_clips, min_len, max_len})});
    const data = await res.json();
    if (data.error) { document.getElementById('status').innerText = '❌ ' + data.error; return; }
    document.getElementById('status').innerText = `✅ ${data.moments.length} final moments (after filtering + overlap removal)`;
    document.getElementById('results').innerHTML = data.moments.map(m => `
      <div class="card">
        <span class="score">${m.virality_score}/100</span>
        <span class="ts">${m.start} – ${m.end}</span>
        <div class="htype">${m.hook_type}</div>
        <div style="margin-top:8px">${m.dialogue}</div>
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
  } finally {
    busy = false;
    document.getElementById('submitBtn').disabled = false;
  }
};

function badgeClass(state) {
  if (state === 'idle') return 'badge idle';
  if (state === 'busy') return 'badge busy';
  return 'badge cooldown';
}
function stateLabel(state) {
  if (state === 'idle') return 'Ready';
  if (state === 'busy') return 'Running now';
  return 'Cooldown';
}

async function pollStatus() {
  try {
    const res = await fetch('/status');
    const data = await res.json();

    document.getElementById('keys').innerHTML = data.keys.map(k => `
      <div class="keyrow">
        <b>${k.label}</b>
        <span class="${badgeClass(k.state)}" style="float:right">${stateLabel(k.state)}${k.state==='cooldown' ? ' · '+k.cooldown_seconds_left+'s' : ''}</span>
        <div class="keymeta">
          ${k.cooldown_reason ? 'Wajah: ' + k.cooldown_reason + '<br>' : ''}
          Total calls (session): ${k.total_calls}<br>
          ${Object.entries(k.rpm_usage).map(([model, usage]) => `${model}: ${usage}`).join('<br>') || 'Abhi tak koi call nahi'}
        </div>
      </div>
    `).join('') || '<div class="keymeta">Koi key configured nahi.</div>';

    document.getElementById('log').innerHTML = data.activity.map(a =>
      `<div><span class="t">${a.t}</span>${a.msg}</div>`
    ).join('') || '<div class="keymeta">Abhi tak koi activity nahi.</div>';
  } catch (e) {
    // status panel fail ho to bhi main app kaam karta rahe
  }
}
pollStatus();
setInterval(pollStatus, 2000);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/status")
def status():
    return jsonify({"keys": pool.snapshot(), "activity": get_activity()})


@app.route("/analyze", methods=["POST"])
def analyze():
    body = request.json or {}
    url = body.get("url", "").strip()
    num_clips = int(body.get("num_clips", 5))
    min_len = int(body.get("min_len", 15))
    max_len = int(body.get("max_len", 60))
    if not url:
        return jsonify({"error": "No URL given"}), 400
    try:
        moments = analyze_video_hooks(url, num_clips=num_clips, min_len=min_len, max_len=max_len)
        return jsonify({"moments": moments})
    except Exception as e:
        log_activity(f"❌ Analyze failed: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    cleanup_old_cache()
    app.run(debug=True, port=8080)