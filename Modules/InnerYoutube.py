import yt_dlp
import json
import traceback
import sys
from yt_dlp.networking.impersonate import ImpersonateTarget

def get_youtube_json3_subtitles(video_url, cookie_file_path, lang='en'):
    ydl_opts = {
        'cookiefile': cookie_file_path,
        'skip_download': True,
        'writeautosub': True,
        'writesubtitles': True,
        
        # FIX 1: string ki jagah ImpersonateTarget object pass karo
        'impersonate': ImpersonateTarget.from_str('chrome'), 
        
        # FIX 2: format resolve na ho paye (n-challenge fail) toh bhi
        # crash na ho, sirf subtitles chahiye video nahi
        'ignoreerrors': 'only_download',
        'quiet': False,
        'no_warnings': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("[INFO] YouTube metadata extract ho raha hai...")
            # extract_info chalte hi terminal par real log dikhega
            info_dict = ydl.extract_info(video_url, download=False)
            
            if not info_dict:
                print("Error: Extract Info ne khali data (None) diya.")
                return None
                
            subtitles = info_dict.get('subtitles', {})
            auto_subtitles = info_dict.get('automatic_captions', {})
            requested_sub = subtitles.get(lang) or auto_subtitles.get(lang)
            
            if not requested_sub:
                print(f"Error: Language '{lang}' ke liye koi subtitle nahi mila.")
                return None
                
            json3_url = None
            for sub_format in requested_sub:
                if sub_format.get('ext') == 'json3' or 'json3' in sub_format.get('url', ''):
                    json3_url = sub_format.get('url')
                    break
            
            if not json3_url and requested_sub:
                if isinstance(requested_sub, list) and len(requested_sub) > 0:
                    base_url = requested_sub[0].get('url')
                else:
                    base_url = requested_sub.get('url')
                if base_url:
                    json3_url = base_url + "&fmt=json3" if "&fmt=" not in base_url else base_url
            
            if json3_url:
                print("\n[SUCCESS] JSON3 Subtitle URL Found!")
                response_bytes = ydl.urlopen(json3_url).read()
                return json.loads(response_bytes.decode('utf-8'))
            else:
                print("Error: Subtitle link toh mila, par use JSON3 format me badal nahi paye.")
                return None
                
    except Exception as e:
        print("\n--- DETAILED PYTHON ERROR START ---")
        # Yeh line batayegi ki problem kis line par aur kis wajah se aayi
        traceback.print_exc(file=sys.stdout)
        print("--- DETAILED PYTHON ERROR END ---\n")
        return None

if __name__ == "__main__":
    video_link = "https://youtu.be/Lp1tVH8VVl4?si=ntoWbg7S8Ri4L8-r"
    cookies_path = "www.youtube.com_cookies.txt" 
    
    json3_output = get_youtube_json3_subtitles(video_link, cookies_path, lang='en')
    if json3_output:
        print("\n--- Sample JSON3 Output Events ---")
        events = json3_output.get("events", [])
        print(json.dumps(events[:2], indent=4))