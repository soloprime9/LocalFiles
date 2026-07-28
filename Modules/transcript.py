import re
import time
import sys
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi

def print_progress(message):
    sys.stdout.write(f"\r⏳ {message}...")
    sys.stdout.flush()

def print_success(message):
    print(f"\r✅ {message}")

def extract_video_id(url):
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
    return match.group(1) if match else None

def get_transcript_data(video_id):
    print_progress("YouTube Server se transcript fetch ho rahi hai")
    try:
        yt_api = YouTubeTranscriptApi()
        raw_data = yt_api.fetch(video_id, languages=['hi', 'en', 'en-IN'])
        
        formatted_script = []
        for segment in raw_data:
            start = int(segment.start)
            timestamp = f"[{start // 60:02d}:{start % 60:02d}]"
            formatted_script.append(f"{timestamp} {segment.text}")
        
        print_success(f"Transcript successfully fetch ho gayi!")
        return "\n".join(formatted_script)
    except Exception as e:
        print(f"\n❌ Transcript Fetch Error: {str(e)}")
        return None

def analyze_video_hooks(url):
    video_id = extract_video_id(url)
    if not video_id:
        return "❌ Error: Invalid YouTube URL format."
        
    transcript = get_transcript_data(video_id)
    if not transcript:
        return "❌ Process Stopped: Transcript nahi mil payi."

    print_progress("Google GenAI Client initialize ho raha hai")
    try:
        # FIX: Yahan brackets ke andar apni key direct paste kar dijiye string format me
        client = genai.Client(api_key="AQ.Ab8RN6IQSmyub6dyT3gUb5GaeU2_ERDaM0eZW-A64Yd-mROsbg")
        print_success("AI Client ready hai.")
    except Exception as e:
        return f"\n❌ Client Initialization Failed: {str(e)}"
    
    print("\n🚀 Google Gemini Server ko query bhej di hai. Please wait...")
    start_time = time.time()
    
    prompt = f"""
    इस टाइमस्टैम्प वाली यूट्यूब ट्रांसक्रिप्ट का गहराई से विश्लेषण करें और मुझे निम्नलिखित डेटा दें:
    1. TIMELINE & DIALOGUES: महत्वपूर्ण क्षणों का विवरण।
    2. VIRAL MOMENTS: कौन से संवाद सबसे अधिक ड्रामाटिक हैं जिन्हें दर्शक पसंद करेंगे?
    3. COMMENT HOOKS: लोग कमेंट सेक्शन में किस टाइमस्टैम्प को सबसे ज्यादा कोट करेंगे?

    Transcript Data:
    {transcript}
    """
    
    try:
        # SPEED FIX: gemini-2.5-flash use kiya hai jo 1000+ words ko 1 second me parse karta hai
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt
        )
        end_time = time.time()
        print_success(f"AI Analysis complete! (Time taken: {end_time - start_time:.2f} seconds)")
        return response.text
    except Exception as e:
        return f"\n❌ AI Generation Failed: {str(e)}"

if __name__ == "__main__":
    print("="*50)
    print("🎬 STARTING AUTOMATED VIDEO HOOK DETECTOR")
    print("="*50)
    
    url = "https://youtu.be/pbo2a-0TAyc?si=JETKqLRegcWScU1U"
    print(f"Target URL: {url}\n")
    
    result = analyze_video_hooks(url)
    
    print("\n" + "="*45 + "\n🔥 GOOGLE AI ANALYSIS RESULT\n" + "="*45)
    print(result)
