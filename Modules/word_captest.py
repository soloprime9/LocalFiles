import json
import re
import http.cookiejar
from urllib.parse import parse_qs, urlparse
import requests


def extract_video_id(url):
    """URL se clean case-sensitive Video ID nikalne ka robust logic."""
    url = url.strip()
    if len(url) == 11 and "/" not in url and "?" not in url:
        return url
    parsed_url = urlparse(url)
    if parsed_url.hostname == "youtu.be":
        return parsed_url.path[1:]
    if parsed_url.hostname in ("www.youtube.com", "youtube.com"):
        if parsed_url.path == "/watch":
            query_params = parse_qs(parsed_url.query)
            if "v" in query_params:
                return query_params["v"][0]
        path_parts = [p for p in parsed_url.path.split("/") if p]
        if len(path_parts) >= 2 and path_parts[0] in (
            "embed",
            "v",
            "shorts",
            "live",
        ):
            return path_parts[1]
    regex_pattern = r"(?:v=|\/shorts\/|\/embed\/|\/live\/|\/v\/|youtu\.be\/|\/watch\?v=)([^#\&\?]{11})"
    match = re.search(regex_pattern, url)
    if match:
        return match.group(1)
    raise ValueError(f"Invalid YouTube link: {url}")


def fetch_youtube_json3_captions(video_url, cookie_file_path, lang_preference=["hi", "en"]):
    """cookies.txt file se cookies load karke native json3 format transcript fetch karta hai."""
    try:
        video_id = extract_video_id(video_url)
        print(f"[+] Processing Video ID: {video_id}")

        # FIX: browser_cookie3 auto-harvest ki jagah
        # Netscape-format cookies.txt file load karo (yt-dlp/browser-export wali)
        print(f"[+] Loading cookies from file: {cookie_file_path}")
        cj = http.cookiejar.MozillaCookieJar(cookie_file_path)
        cj.load(ignore_discard=True, ignore_expires=True)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
            "Referer": "https://www.youtube.com/",
        }

        # Step 1: Watch page parse karna
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        response = requests.get(
            watch_url, headers=headers, cookies=cj, timeout=10
        )

        if response.status_code != 200:
            return f"Error: YouTube page access blocked (Status {response.status_code})"

        # Step 2: captionTracks extract karna
        pattern = r'"captionTracks":\s*(\[.*?\])'
        match = re.search(pattern, response.text)

        if not match:
            return "Error: Subtitles/Captions are not available on this video track."

        caption_tracks = json.loads(match.group(1))

        # Step 3: Match user languages
        selected_track = None
        for lang in lang_preference:
            for track in caption_tracks:
                if track.get("languageCode") == lang:
                    selected_track = track
                    break
            if selected_track:
                break

        if not selected_track:
            selected_track = caption_tracks[0]

        base_caption_url = selected_track.get("baseUrl")
        is_asr = selected_track.get("kind") == "asr"

        print(
            f"[+] Selected Track: {selected_track.get('name', {}).get('simpleText', 'Default')}"
        )

        # Step 4: Formatting URLs for JSON3 stream extraction
        if "fmt=json3" not in base_caption_url:
            base_caption_url += "&fmt=json3"
        if is_asr and "kind=asr" not in base_caption_url:
            base_caption_url += "&kind=asr"

        # Step 5: Final request with injected session verification cookies
        json3_response = requests.get(
            base_caption_url, headers=headers, cookies=cj, timeout=10
        )

        response_text = json3_response.text.strip()
        if not response_text:
            return "Error: YouTube server dropped an empty response. Ensure your cookies.txt is fresh and you are logged into YouTube."

        if json3_response.status_code == 200:
            return json3_response.json()
        else:
            return (
                f"Error hitting timedtext endpoint (Status {json3_response.status_code})"
                f"\nResponse: {response_text[:100]}"
            )

    except FileNotFoundError:
        return f"Error: Cookie file not found at '{cookie_file_path}'"
    except Exception as e:
        return f"An operational error occurred: {str(e)}"


# --- RUN TESTING ---
input_url = "https://youtu.be/0BBjTyseobI?si=SzTqI9CUINzY_x80"
cookies_path = "www.youtube.com_cookies.txt"  # apni cookies.txt ka path yahan do

raw_json3_output = fetch_youtube_json3_captions(input_url, cookies_path)

if isinstance(raw_json3_output, dict) and "events" in raw_json3_output:
    print("\n[✓] SUCCESS! Internal JSON3 response mapping completed!")
    print("\n--- SAMPLE TIMEDTEXT DATA OUTPUT ---")
    print(json.dumps(raw_json3_output["events"][:3], indent=2, ensure_ascii=False))
else:
    print(f"\n[X] Process Failed: {raw_json3_output}")