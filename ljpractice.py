import os
import sys
import re
import getpass
import yt_dlp
from playwright.sync_api import sync_playwright

def progress_hook(d):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0.0%')
        speed = d.get('_speed_str', 'N/A')
        print(f"\r[+] Downloading: {percent} | Speed: {speed}", end="", flush=True)
    elif d['status'] == 'finished':
        print("\n[+] Download complete! Stitching audio/video...")

def get_chrome_profile_path():
    """Aapke system ke hisab se automatic Chrome Profile ka path dhoodhta hai."""
    username = getpass.getuser()
    if sys.platform == "win32":
        return f"C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data"
    elif sys.platform == "darwin": # Mac ke liye
        return f"/Users/{username}/Library/Application Support/Google/Chrome"
    else: # Linux ke liye
        return f"/home/{username}/.config/google-chrome"

def login_safe_sniff_and_download(webpage_url, output_filename="final_video"):
    user_data_dir = get_chrome_profile_path()
    print(f"[+] Using your REAL Chrome Profile Path: {user_data_dir}")
    print("[!] IMPORTANT: Agar normal Chrome window khuli hai, toh use abhi CLOSE kar dein!")
    
    stream_url = None
    browser_headers = {}

    with sync_playwright() as p:
        try:
            # launch_persistent_context aapke real logins, sessions aur cookies ko load karta hai
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False, # Visual rakhna zaroori hai taaki login work kare
                channel="chrome", # Specifying real Google Chrome instead of chromium
                no_viewport=True
            )
        except Exception as browser_err:
            print(f"\n[-] Browser Error: Apna normal Chrome browser fully CLOSE karke is script ko firse chalayein. Details: {browser_err}")
            return

        page = context.new_page()

        # Intercepting network traffic
        def intercept_requests(request):
            nonlocal stream_url, browser_headers
            url = request.url
            if re.search(r'\.(m3u8|mpd)(\?|$)', url) and "analytics" not in url:
                if not stream_url:
                    stream_url = url
                    browser_headers = request.headers
                    print(f"\n[🎉] SUCCESS! Hooked Stream with Active Login: {stream_url}")

        page.on("request", intercept_requests)
        
        try:
            print(f"[+] Navigating to: {webpage_url}")
            page.goto(webpage_url, wait_until="load", timeout=60000)
            
            print("\n[⏱️] Waiting 15 Seconds Window...")
            print("[->] Agar aap logged in hain, toh abhi video ke PLAY button par click karein.")
            print("[->] Agar login nahi hai, toh jaldi se login karein, video play karein, script automatic link capture kar legi!")
            
            # 15 seconds ka time taaki aap click kar sakein ya login bypass ho sake
            page.wait_for_timeout(15000) 
        except Exception as e:
            print(f"[!] Browser process note: {e}")
        finally:
            context.close()

    if not stream_url:
        print("\n[-] Failed: Stream URL nahi mil paya. Kya aapne sahi se video play ki thi?")
        return

    # ==========================================
    # DOWNLOAD PHASE WITH LOGGED-IN HEADERS
    # ==========================================
    print("[+] Forwarding active logged-in session to yt-dlp...")
    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{output_filename}.%(ext)s',
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
        'http_headers': browser_headers, # Active logged-in session headers pass ho gaye
        'nocheckcertificate': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([stream_url])
        print(f"\n[=======] 🎉 PERFECT! Video '{output_filename}' bina login/signup block ke download ho gayi. [=======]")
    except Exception as e:
        print(f"\n[-] Download Error: {e}")

if __name__ == "__main__":
    web_url = input("Enter the Website Page URL: ").strip()
    file_name = input("Enter output file name: ").strip() or "premium_download"

    if web_url:
        login_safe_sniff_and_download(web_url, file_name)
    else:
        print("URL khali nahi ho sakta.")