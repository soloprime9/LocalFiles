import av
import os
import sys

def convert_webm_to_mp3_pure(input_file, output_file=None):
    """
    Converts a .webm file to .mp3 using PyAV bindings with a real-time progress bar.
    Requires ZERO ffmpeg binaries installed on your system.
    """
    if not os.path.exists(input_file):
        print(f"❌ Error: The file '{input_file}' was not found.")
        return False

    if not output_file:
        output_file = os.path.splitext(input_file)[0] + ".mp3"

    try:
        print(f"Opening container for {input_file}...")
        container_in = av.open(input_file, mode="r")
        
        # Look for the audio stream inside the webm file
        audio_stream_in = next((s for s in container_in.streams if s.type == 'audio'), None)
        if not audio_stream_in:
            print("❌ Error: No audio track found inside the WebM file.")
            container_in.close()
            return False

        # Get total duration in seconds (fallback to 1 if undetected to prevent division by zero)
        total_duration = float(container_in.duration or 0) / av.time_base
        if total_duration <= 0 and audio_stream_in.duration:
            total_duration = float(audio_stream_in.duration * audio_stream_in.time_base)

        # Open the target MP3 file
        container_out = av.open(output_file, mode="w", format="mp3")
        
        # Add a high-quality mp3 stream
        audio_stream_out = container_out.add_stream("mp3", rate=44100)
        
        print(f"Transcoding audio to {output_file}...")
        
        # Decode individual frames and show progress
        for frame in container_in.decode(audio_stream_in):
            # Calculate and print progress bar
            if total_duration > 0 and frame.time is not None:
                percent = min(100.0, (frame.time / total_duration) * 100)
                bar_length = int(percent / 4)  # 25 character long bar
                bar = "█" * bar_length + "-" * (25 - bar_length)
                # \r moves the cursor to the beginning of the line to update it live
                sys.stdout.write(f"\r|{bar}| {percent:.1f}% ({frame.time:.1f}s / {total_duration:.1f}s)")
                sys.stdout.flush()

            frame.pts = None  # Clear timestamps to allow container recalculation
            for packet in audio_stream_out.encode(frame):
                container_out.mux(packet)
                
        # Flush the encoder buffer to finalize remaining audio packets
        for packet in audio_stream_out.encode(None):
            container_out.mux(packet)

        container_in.close()
        container_out.close()
        
        # Print a final clean line
        sys.stdout.write(f"\r|{'█'*25}| 100.0% ({total_duration:.1f}s / {total_duration:.1f}s)\n")
        print("✅ Pure Python conversion completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Transcoding failed: {e}")
        return False

if __name__ == "__main__":
    target_file = "anime.mkv"
    convert_webm_to_mp3_pure(target_file)