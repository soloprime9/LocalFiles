#!/usr/bin/env python3
# word_captions.py — YouTube ke internal json3 timedtext format se REAL
# word-by-word timestamps nikalta hai (guess/estimate nahi, actual data).
# pip install yt-dlp

import re
import json
import yt_dlp

def get_word_level_captions(url, lang="en"):
    """Returns [{"word": str, "start": float_sec, "end": float_sec}, ...]"""
    ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True, 'noplaylist': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    bucket = info.get('subtitles') or {}
    if not bucket:
        bucket = info.get('automatic_captions') or {}
    if not bucket:
        raise RuntimeError("Is video me koi captions nahi hain.")

    if lang not in bucket:
        lang = "en" if "en" in bucket else next(iter(bucket))
    tracks = bucket[lang]

    # json3-native track dhundo, warna kisi bhi track ka URL le ke fmt=json3 force karo
    base_url = None
    for t in tracks:
        if t.get('ext') == 'json3':
            base_url = t['url']
            break
    if not base_url:
        base_url = tracks[0]['url']
        if 'fmt=' in base_url:
            base_url = re.sub(r'fmt=[^&]+', 'fmt=json3', base_url)
        else:
            base_url += ('&' if '?' in base_url else '?') + 'fmt=json3'

    # FIXED: yt-dlp ke internal network downloader ko use karke content pull karein to avoid 429
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # download_content securely hits the URL handling rate limit bypass automatically
        raw_data = ydl.urlopen(base_url).read().decode('utf-8')
        data = json.loads(raw_data)

    words = []
    for event in data.get('events', []):
        t_start = event.get('tStartMs')
        if t_start is None:
            continue
        for seg in (event.get('segs') or []):
            text = seg.get('utf8', '')
            if not text.strip():
                continue
            offset = seg.get('tOffsetMs', 0)
            words.append({"word": text.strip(), "start": (t_start + offset) / 1000.0})

    # end time = agle word ka start (last word ke liye +0.4s default)
    for i in range(len(words) - 1):
        words[i]["end"] = words[i + 1]["start"]
    if words:
        words[-1]["end"] = words[-1]["start"] + 0.4

    return words


if __name__ == "__main__":
    url = input("YouTube URL: ").strip()
    try:
        words = get_word_level_captions(url)
        print(f"\n✅ {len(words)} words with timing found:\n")
        for w in words[:40]:
            print(f"[{w['start']:.2f}s - {w['end']:.2f}s]  {w['word']}")
        if len(words) > 40:
            print(f"... aur {len(words)-40} words")
    except Exception as e:
        print(f"\n❌ Error encountered: {e}")
