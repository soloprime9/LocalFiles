
import re
import os
import json
import time
import hashlib
import threading
import itertools

from pydantic import BaseModel, Field
from google import genai
from google.genai import errors as genai_errors
from youtube_transcript_api import YouTubeTranscriptApi

# ── Apni saari free API keys yahan daalo (2-3 alag Google accounts se) ─────
API_KEYS = [
    "AQ.Ab8RN6IQSmyub6dyT3gUb5GaeU2_ERDaM0eZW-A64Yd-mROsbg",
    "AQ.Ab8RN6LaUL4o0weWHLQ9F6cW__Ko_qEZLNX1PGJk-VuquywNmQ",
    "AQ.Ab8RN6ISugABRVrHSOaniSVy8TT3wl1uwzaESmiijtn8aSo_aw",
]

STAGE1_MODEL = "gemini-flash-lite-latest"
STAGE2_MODEL = "gemini-flash-latest"

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Cache files is se purane ho jayein to automatically delete ho jaate hain —
# taaki disk space faltu me bharta na rahe. Zaroorat ke hisaab se badal lo.
CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 din


# ── Multi-key pool: per-key cooldown tracking, auto-rotate on 429 ──────────
class KeyPool:
    def __init__(self, keys):
        if not keys or keys[0].startswith("KEY_"):
            raise RuntimeError("API_KEYS list me apni asli keys daalo (hooks_pool.py ke top par).")
        self.keys = keys
        self.cooldown_until = {k: 0.0 for k in keys}
        self.lock = threading.Lock()
        self._cycle = itertools.cycle(keys)

    def _next_available_key(self):
        with self.lock:
            now = time.time()
            for _ in range(len(self.keys)):
                k = next(self._cycle)
                if self.cooldown_until[k] <= now:
                    return k, 0
            # sab cooldown me hain — jo sabse jaldi free hogi, wahi lo
            k = min(self.cooldown_until, key=self.cooldown_until.get)
            wait = max(0.0, self.cooldown_until[k] - now)
            return k, wait

    def _mark_cooldown(self, key, seconds):
        with self.lock:
            self.cooldown_until[key] = time.time() + seconds

    def call(self, fn, max_attempts=6):
        """fn(client) -> response. Automatically rotates across keys on 429,
        waits only if ALL keys are on cooldown."""
        last_err = None
        for attempt in range(max_attempts):
            key, wait = self._next_available_key()
            if wait > 0:
                print(f"⏳ Saari keys busy hain, sabse jaldi free hone wali ke liye {wait:.0f}s wait...")
                time.sleep(wait)
            client = genai.Client(api_key=key)
            try:
                return fn(client)
            except genai_errors.APIError as e:
                last_err = e
                code = getattr(e, "code", None)
                if code == 429:
                    cooldown = 60
                    m = re.search(r"retry in (\d+(?:\.\d+)?)s", str(e), re.IGNORECASE)
                    if m:
                        cooldown = float(m.group(1)) + 2
                    self._mark_cooldown(key, cooldown)
                    print(f"🔁 Key ...{key[-6:]} rate-limited ({cooldown:.0f}s cooldown) — dusri key try kar rahe hain...")
                    continue
                if code == 503:
                    print(f"⚠️  Google server busy (503) — 5s baad retry...")
                    time.sleep(5)
                    continue
                raise
        raise last_err


pool = KeyPool(API_KEYS)


# ── Cache (with auto-expiry cleanup) ────────────────────────────────────
def _cache_path(video_id, num_clips, min_len, max_len):
    key = f"{video_id}_{num_clips}_{min_len}_{max_len}"
    h = hashlib.md5(key.encode()).hexdigest()[:10]
    return os.path.join(CACHE_DIR, f"{video_id}_{h}.json")


def cleanup_old_cache():
    """CACHE_TTL_SECONDS se purani cache files delete kar deta hai. Program
    start hote hi ek baar chalta hai, taaki disk space faltu me na bhare."""
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
        print(f"🧹 {removed} purani cache file(s) delete ki (7+ din purani).")


def get_cached(video_id, num_clips, min_len, max_len):
    path = _cache_path(video_id, num_clips, min_len, max_len)
    if not os.path.exists(path):
        return None
    # Expired ho chuki ho to delete karke miss treat karo
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

    def _call(client):
        return client.models.generate_content(
            model=STAGE1_MODEL,
            contents=prompt,
            config={"temperature": 0.5, "max_output_tokens": 2048},
        )

    return pool.call(_call).text


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

    def _call(client):
        return client.models.generate_content(
            model=STAGE2_MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": list[HookMoment],
                "temperature": 0.15,
            },
        )

    return json.loads(pool.call(_call).text)


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


# ── Main entry point (with caching) ────────────────────────────────────
def analyze_video_hooks(url, num_clips=5, min_len=15, max_len=60, force_refresh=False):
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")

    if not force_refresh:
        cached = get_cached(video_id, num_clips, min_len, max_len)
        if cached is not None:
            print(f"✅ Cache hit for {video_id} — 0 API calls.")
            return cached

    cues = get_cues(video_id)
    if not cues:
        raise ValueError("Transcript nahi mili")
    transcript = cues_to_transcript_text(cues)
    total_duration = cues[-1]["end"]

    analysis = stage1_analysis(transcript, num_clips)
    raw_moments = stage2_select(analysis, transcript, num_clips, min_len, max_len)
    final_moments = postprocess(raw_moments, cues, total_duration)

    save_cache(video_id, num_clips, min_len, max_len, final_moments)
    return final_moments


if __name__ == "__main__":
    cleanup_old_cache()
    url = input("YouTube URL: ").strip()
    moments = analyze_video_hooks(url)
    for i, m in enumerate(moments, 1):
        print(f"{i}. [{m['start']}-{m['end']}] score={m['virality_score']}/100  {m['hook_type']}")
        print(f"   {m['dialogue']}")
