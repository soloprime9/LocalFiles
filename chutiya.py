import av
import os
import time

def instant_remux_webm(input_file, output_file=None):
    """
    Instantly extracts the raw audio track from .webm and saves it.
    Bypasses decoding/encoding entirely. Takes less than a second.
    """
    if not os.path.exists(input_file):
        print(f"❌ Error: The file '{input_file}' was not found.")
        return False

    try:
        start_time = time.time()
        container_in = av.open(input_file, mode="r")
        
        # Find the audio stream
        audio_stream_in = next((s for s in container_in.streams if s.type == 'audio'), None)
        if not audio_stream_in:
            print("❌ Error: No audio track found inside the WebM file.")
            container_in.close()
            return False

        # Detect the internal codec name (usually 'opus' or 'vorbis' for webm)
        codec_name = audio_stream_in.codec_context.name
        print(f"⚡ Detected audio codec: {codec_name}")

        # Map codec to the correct container extension automatically
        if not output_file:
            ext = "sdfsdf.mp3" if codec_name == "mp3" else f".{codec_name}"
            if ext == ".opus": 
                ext = ".ogg"  # Opus matches perfectly inside an OGG container
            output_file = os.path.splitext(input_file)[0] + ext

        print(f"🚀 Instantly remuxing packets to {output_file}...")
        container_out = av.open(output_file, mode="w")
        
        # FIX: Pass the codec name directly as a positional argument
        audio_stream_out = container_out.add_stream(codec_name)

        # Demux packets from input and instantly mux them into the output wrapper
        for packet in container_in.demux(audio_stream_in):
            if packet.dts is None:
                continue
            packet.stream = audio_stream_out
            container_out.mux(packet)

        container_in.close()
        container_out.close()
        
        elapsed = time.time() - start_time
        print(f"✅ Done! Completed in exactly {elapsed:.3f} seconds!")
        return True

    except Exception as e:
        print(f"❌ Instant copy failed: {e}")
        return False

if __name__ == "__main__":
    target_file = "solo.webm"
    instant_remux_webm(target_file)