import os
import sys
import re
import yt_dlp
from playwright.sync_api import sync_playwright

def progress_hook(d):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0.0%')
        speed = d.get('_speed_str', 'N/A')
        print(f"\r[+] Downloading: {percent} | Speed: {speed}", end="", flush=True)
    elif d['status'] == 'finished':
        print("\n[+] Download complete! Saving file...")

def sniff_and_download_protected_video(webpage_url, output_filename="final_video"):
    print(f"[+] Launching browser to bypass security headers...")
    
    stream_url = None
    secure_headers = {}

    with sync_playwright() as p:
        # headless=True ko False kar sakte hain agar dekhna hai browser me kya ho raha hai
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Network traffic intercept karke authenticated headers nikalna
        def intercept_response(request):
            nonlocal stream_url, secure_headers
            url = request.url
            if re.search(r'\.(m3u8|mpd)(\?|$)', url) and "analytics" not in url:
                if not stream_url:
                    stream_url = url
                    # Us secure request ke saare headers copy kar rahe hain (Tokens ke sath)
                    secure_headers = request.headers
                    print(f"\n[🎉] Target Stream Found with Security Tokens!")

        page.on("request", intercept_response)
        
        try:
            page.goto(webpage_url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(5000) # 5 seconds wait taaki video load ho jaye
        except Exception as e:
            print(f"[!] Browser process note: {e}")
        finally:
            browser.close()

    if not stream_url:
        print("[-] Error: Stream link (.m3u8/.mpd) nahi mila. Kya video sahi me play hui thi?")
        return

    # Ab yt-dlp ko wahi headers denge jo asli browser ne use kiye the
    print("[+] Passing dynamic tokens to downloader engine...")
    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{output_filename}.%(ext)s',
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
        'http_headers': secure_headers, # Dynamic browser headers inject ho gaye
        'nocheckcertificate': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([stream_url])
        print(f"\n[=======] 🎉 SUCCESS! File '{output_filename}.mp4' successfully saved! [=======]")
    except Exception as e:
        print(f"\n[-] High Security Block Detected.\nDetails: {e}")

if __name__ == "__main__":
    # Ab aapko .m3u8/.mpd ka link nahi dalna hai! Direct WEBSITE ka URL daliye.
    web_url = input("Enter the Main Website Page URL: ").strip()
    file_name = input("Enter output file name: ").strip() or "secure_download"

    if web_url:
        sniff_and_download_protected_video(web_url, file_name)
    else:
        print("URL khali nahi ho sakta.")