import av
import os
import sys

def convert_webm_to_mp3_fast(input_file, output_file=None):
    """
    Ultra-fast .webm to .mp3 conversion using PyAV with Multi-Threading.
    Requires ZERO FFmpeg binaries on your machine.
    """
    if not os.path.exists(input_file):
        print(f"❌ Error: The file '{input_file}' was not found.")
        return False

    if not output_file:
        output_file = os.path.splitext(input_file)[0] + "dd.mp3"

    try:
        print(f"Opening container for {input_file}...")
        container_in = av.open(input_file, mode="r")
        
        # Look for the audio stream
        audio_stream_in = next((s for s in container_in.streams if s.type == 'audio'), None)
        if not audio_stream_in:
            print("❌ Error: No audio track found inside the WebM file.")
            container_in.close()
            return False

        # 🔥 SPEED BOOST: Enable multi-threaded decoding across CPU cores
        audio_stream_in.thread_type = "AUTO"

        # Calculate total duration for progress
        total_duration = float(container_in.duration or 0) / av.time_base
        if total_duration <= 0 and audio_stream_in.duration:
            total_duration = float(audio_stream_in.duration * audio_stream_in.time_base)

        # Open target MP3 file
        container_out = av.open(output_file, mode="w", format="mp3")
        audio_stream_out = container_out.add_stream("mp3", rate=44100)
        
        print(f"Transcoding audio to {output_file} (Multi-threaded active)...")
        
        # Processing loop
        for frame in container_in.decode(audio_stream_in):
            if total_duration > 0 and frame.time is not None:
                percent = min(100.0, (frame.time / total_duration) * 100)
                bar_length = int(percent / 4)
                bar = "█" * bar_length + "-" * (25 - bar_length)
                sys.stdout.write(f"\r|{bar}| {percent:.1f}% ({frame.time:.1f}s / {total_duration:.1f}s)")
                sys.stdout.flush()

            frame.pts = None  # Reset timestamps for re-muxing
            for packet in audio_stream_out.encode(frame):
                container_out.mux(packet)
                
        # Flush the leftover encoder buffers
        for packet in audio_stream_out.encode(None):
            container_out.mux(packet)

        container_in.close()
        container_out.close()
        
        sys.stdout.write(f"\r|{'█'*25}| 100.0% ({total_duration:.1f}s / {total_duration:.1f}s)\n")
        print("✅ Finished at maximum speed!")
        return True

    except Exception as e:
        print(f"\n❌ Transcoding failed: {e}")
        return False

if __name__ == "__main__":
    target_file = "solo.webm"
    convert_webm_to_mp3_fast(target_file)