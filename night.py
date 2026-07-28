import os
import requests
import re
from urllib.parse import urljoin

def download_free_stream(m3u8_url, output_filename="test_output.mp4"):
    print("[*] Manifest file ko read kiya ja raha hai...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    # Step 1: Main manifest file download karein
    response = requests.get(m3u8_url, headers=headers)
    if response.status_code != 200:
        print("[-] Error: Manifest URL tak nahi pahunch paaye.")
        return

    # Agar master playlist hai, toh pehle bandwidth profile select karein
    lines = response.text.splitlines()
    target_playlist_url = m3u8_url
    
    for line in lines:
        if line.endswith(".m3u8"):
            # Pehla available resolution profile uthayein
            target_playlist_url = urljoin(m3u8_url, line)
            break

    # Step 2: Actual segment playlist ko parse karein
    print("[*] Video segments ki list nikali ja rahi hai...")
    response = requests.get(target_playlist_url, headers=headers)
    lines = response.text.splitlines()
    
    # Saare .ts chunks ke URLs nikalna
    segment_urls = [urljoin(target_playlist_url, line) for line in lines if line and not line.startswith("#")]
    
    if not segment_urls:
        print("[-] Error: Koyi video segments nahi mile.")
        return
    
    print(f"[+] Total {len(segment_urls)} video chunks mile hain.")
    
    # Step 3: Har ek chunk ko download karke direct file mein write (append) karna
    print("[*] Downloading aur joining shuru ho gayi hai... Please wait.")
    
    with open(output_filename, "wb") as final_file:
        for index, seg_url in enumerate(segment_urls):
            # Sirf pehle 10 segments download karte hain test ke liye taaki jaldi ho jaye
            if index >= 10: 
                print("\n[*] Testing ke liye sirf pehle 10 chunks download kiye hain.")
                break
                
            seg_response = requests.get(seg_url, headers=headers)
            if seg_response.status_code == 200:
                # Binary concatenation: data ko purani file ke aage jodhna
                final_file.write(seg_response.content)
                print(f"\rDownloading chunk: {index + 1}/{min(10, len(segment_urls))}", end="")
            else:
                print(f"\n[-] Error downloading chunk {index + 1}")
                
    print(f"\n[+] Success! Aapki test video bina kisi DRM ke save ho gayi hai: {os.path.abspath(output_filename)}")

if __name__ == "__main__":
    # Ek open-source free HLS test URL
    test_url = "https://cph-p2p-msl.akamaized.net/hls/live/2000341/test/master.m3u8"
    download_free_stream(test_url)