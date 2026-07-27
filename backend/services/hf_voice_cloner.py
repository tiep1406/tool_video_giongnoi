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
    Uses open-source HuggingFace Space 'cosmichackerx/voice-cloner' (OmniVoice engine)
    with exact parameter schema for zero-shot voice cloning.
    """
    if not os.path.exists(sample_audio_path):
        raise FileNotFoundError(f"Sample audio not found: {sample_audio_path}")

    try:
        from gradio_client import Client, handle_file
    except ImportError:
        print("[Voice Cloner Engine] gradio_client not installed.")
        return None

    try:
        print(f"[Voice Cloner Engine] Connecting to HF Space 'cosmichackerx/voice-cloner'...")
        client = Client("cosmichackerx/voice-cloner")
        
        # Exact 38-parameter call matching HuggingFace Gradio Space schema
        res = client.predict(
            text,                            # 0: Text to speak
            "Vietnamese" if "vi" in language.lower() else "English",  # 1: Language
            handle_file(sample_audio_path),  # 2: Speaker 1 ref audio
            "",                              # 3: Speaker 1 transcript
            32,                              # 4: n_steps
            3.0,                             # 5: cfg_guidance
            True,                            # 6: denoise
            1.0,                             # 7: speed
            0.0,                             # 8: force duration
            True,                            # 9: clean_ref
            True,                            # 10: trim_silence
            "Neutral",                       # 11: expression_preset
            False,                           # 12: long_form
            "Voice clone",                   # 13: mode
            None,                            # 14: speaker2_audio
            "",                              # 15: speaker2_transcript
            "",                              # 16: instruct
            True,                            # 17: normalize_num
            None,                            # 18: bgm_audio
            0.18,                            # 19: bgm_volume
            8.0,                             # 20: duck_db
            None,                            # 21: profile_name
            True,                            # 22: consent
            True,                            # 23: ref_prep
            False,                           # 24: blend_instruct
            False,                           # 25: use_native_longform
            0.1,                             # 26: t_shift
            5.0,                             # 27: position_temperature
            0.0,                             # 28: class_temperature
            0.1,                             # 29: pad_duration
            0.1,                             # 30: fade_duration
            15.0,                            # 31: audio_chunk_duration
            30.0,                            # 32: audio_chunk_threshold
            True,                            # 33: enable_polish
            0,                               # 34: f0_semitones
            0.35,                            # 35: index_rate
            0.33,                            # 36: protect
            True,                            # 37: loud_norm
            api_name="/clone_voice"
        )

        output_audio = None
        if isinstance(res, (list, tuple)) and len(res) > 0:
            output_audio = res[0]
        elif isinstance(res, str):
            output_audio = res

        if output_audio and os.path.exists(output_audio):
            print(f"[Voice Cloner Engine] Successfully generated cloned audio!")
            ffmpeg_bin = get_ffmpeg_bin()
            subprocess.run([ffmpeg_bin, "-y", "-i", output_audio, "-acodec", "libmp3lame", "-q:a", "2", output_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return output_path
    except Exception as e:
        print(f"[Voice Cloner Engine] Warning: {e}")

    return None
