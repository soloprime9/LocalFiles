import os
import requests

def download_confirmed_file():
    # Wikipedia ka official test video link (No stream parsing, absolute direct download)
    video_url = "https://upload.wikimedia.org/wikipedia/commons/c/c4/Provo_River_Falls_at_Uinta_National_Forest.webm"
    output_filename = "test_wikipedia.webm"
    
    print("[*] Directly connecting to Wikipedia media servers...")
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(video_url, headers=headers, stream=True)
        if response.status_code == 200:
            print("[+] Connection Successful! Saving file data blocks...")
            with open(output_filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024*1024): # 1MB chunks
                    if chunk:
                        f.write(chunk)
                        print(".", end="", flush=True)
            print(f"\n[+] Hogaya! File save ho gayi hai: {os.path.abspath(output_filename)}")
        else:
            print(f"[-] Server returned error code: {response.status_code}")
    except Exception as e:
        print(f"[-] Network layer error: {e}")

if __name__ == "__main__":
    download_confirmed_file()