# hooks.py
# Single file — sirf YouTube URL do, hook/viral segments milenge.
# pip install google-genai pydantic

import os
import json
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

GEMINI_MODEL = "gemini-flash-latest"
GEMINI_API_KEY = "sdgf"


class HookSegment(BaseModel):
    start: float = Field(description="Start time in seconds, real timestamp from the video")
    end: float = Field(description="End time in seconds, real timestamp from the video")
    hook_type: str = Field(description="One of: curiosity_gap, shocking_stat, story_climax, controversial, punchline, emotional_peak, strong_question")
    score: int = Field(description="Virality score 1-10, 10 = most likely to hook a scrolling viewer")
    reason: str = Field(description="One short sentence explaining why this moment works as a hook")


def find_hooks_from_youtube_url(url, num_clips=6, min_len=15, max_len=60, total_duration=None):
    if not GEMINI_API_KEY or GEMINI_API_KEY == "PASTE_YOUR_GEMINI_API_KEY_HERE":
        raise RuntimeError("Upar GEMINI_API_KEY line me apni asli key daalo.")

    dur_hint = f"\nVideo total length: ~{int(total_duration)} seconds." if total_duration else ""

    prompt = f"""Watch this video and find the {num_clips} strongest moments that would
work as standalone short-form vertical clips (YouTube Shorts / Reels / TikTok).
Each clip should be roughly {min_len}-{max_len} seconds long.

Look for:
- A strong opening line / curiosity gap
- A shocking stat or controversial statement
- An emotional peak, story climax, or punchline
- A question that stops someone from scrolling
- Also weigh visual energy (fast cuts, animated reactions, on-screen action) if relevant

Rules:
- start/end must be REAL timestamps (in seconds) from the actual video — watch it, don't guess.
- Clips must not overlap.
- Prefer moments that make sense on their own without earlier context.{dur_hint}
"""

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=types.Content(parts=[
            types.Part(file_data=types.FileData(file_uri=url)),
            types.Part(text=prompt),
        ]),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=list[HookSegment],
            temperature=0.4,
        ),
    )

    try:
        segments = json.loads(response.text)
    except (json.JSONDecodeError, TypeError):
        raise RuntimeError(f"Gemini returned non-JSON output: {response.text[:300]}")

    cleaned = []
    for seg in segments:
        start = max(0.0, float(seg["start"]))
        end = float(seg["end"])
        if total_duration:
            end = min(end, total_duration)
        if end - start < 3:
            continue
        cleaned.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "hook_type": seg.get("hook_type", "unknown"),
            "score": int(seg.get("score", 5)),
            "reason": seg.get("reason", ""),
        })

    cleaned.sort(key=lambda s: s["score"], reverse=True)
    return cleaned


if __name__ == "__main__":
    url = input("YouTube URL: ").strip()
    if not url:
        print("Koi URL nahi diya.")
    else:
        print("\n🤖 Gemini se seedha YouTube URL bhej rahe hain...")
        try:
            segments = find_hooks_from_youtube_url(url, num_clips=5)
        except Exception as e:
            print(f"❌ Failed: {e}")
        else:
            if not segments:
                print("⚠️  Koi segment nahi mila.")
            else:
                print("\n=== RESULTS ===")
                for i, s in enumerate(segments, 1):
                    m1, s1 = divmod(int(s["start"]), 60)
                    m2, s2 = divmod(int(s["end"]), 60)
                    print(f"{i}. [{m1:02d}:{s1:02d}–{m2:02d}:{s2:02d}]  score={s['score']}/10  type={s['hook_type']}")
                    print(f"   → {s['reason']}")







# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# """
# list_models.py — poochta hai Google se: mere API key ke liye kaunse models
# actually available hain, aur kaunse generateContent support karte hain.
# """

# from google import genai

# GEMINI_API_KEY = "AQ.Ab8RN6IQSmyub6dyT3gUb5GaeU2_ERDaM0eZW-A64Yd-mROsbg"

# client = genai.Client(api_key=GEMINI_API_KEY)

# print("Available models jo generateContent support karte hain:\n")
# for m in client.models.list():
#     actions = getattr(m, "supported_actions", None) or getattr(m, "supported_generation_methods", None) or []
#     if "generateContent" in actions or not actions:
#         print(f"  {m.name}")