import os
import shutil
import subprocess

def get_ffmpeg_bin():
    bundled = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bin', 'ffmpeg-master-latest-win64-gpl', 'bin', 'ffmpeg.exe'))
    if os.path.exists(bundled):
        return bundled
    return 'ffmpeg'

def clone_voice_hf_space(sample_audio_path: str, text: str, output_path: str, language: str = "vi"):
    """
    Uses 100% FREE open-source HuggingFace Space 'cosmichackerx/voice-cloner' / 'k2-fsa/OmniVoice'
    for zero-shot voice cloning without any API key or payment limits.
    """
    if not os.path.exists(sample_audio_path):
        raise FileNotFoundError(f"Sample audio not found: {sample_audio_path}")

    try:
        from gradio_client import Client, handle_file
    except ImportError:
        print("[Voice Cloner Engine] gradio_client not installed.")
        return None

    spaces_to_try = [
        ("cosmichackerx/voice-cloner", "/predict"),
        ("k2-fsa/OmniVoice", "/predict"),
        ("k2-fsa/OmniVoice", "/generate_audio")
    ]

    for space_id, api_endpoint in spaces_to_try:
        try:
            print(f"[Voice Cloner Engine] Connecting to 100% Free HF Space '{space_id}' ({api_endpoint})...")
            client = Client(space_id)
            
            # Predict using HuggingFace Gradio Client
            try:
                res = client.predict(
                    ref_audio=handle_file(sample_audio_path),
                    gen_text=text,
                    language="vi" if "vi" in language.lower() else "en",
                    api_name=api_endpoint
                )
            except Exception:
                res = client.predict(
                    handle_file(sample_audio_path),
                    text,
                    api_name=api_endpoint
                )

            # Process output audio path
            output_audio = None
            if isinstance(res, (list, tuple)) and len(res) > 0:
                output_audio = res[0]
            elif isinstance(res, str):
                output_audio = res
            elif isinstance(res, dict):
                output_audio = res.get("name") or res.get("path")

            if output_audio and os.path.exists(output_audio):
                print(f"[Voice Cloner Engine] Successfully generated cloned audio from '{space_id}'!")
                ffmpeg_bin = get_ffmpeg_bin()
                subprocess.run([ffmpeg_bin, "-y", "-i", output_audio, "-acodec", "libmp3lame", "-q:a", "2", output_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return output_path
        except Exception as e:
            print(f"[Voice Cloner Engine] Endpoint '{space_id}' ({api_endpoint}) warning: {e}")

    return None
