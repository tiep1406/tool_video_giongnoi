import os
import sys
import asyncio
import subprocess
import struct
import edge_tts

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# Ensure AI models cache locally inside d:\tool_video\backend\models
os.environ["HF_HOME"] = MODELS_DIR
os.environ["TORCH_HOME"] = MODELS_DIR
os.environ["TTS_HOME"] = MODELS_DIR

_xtts_model = None

def get_ffmpeg_cmd():
    bundled = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bin', 'ffmpeg-master-latest-win64-gpl', 'bin', 'ffmpeg.exe'))
    if os.path.exists(bundled):
        return bundled
    return 'ffmpeg'

def get_xtts_model():
    global _xtts_model
    if _xtts_model is not None:
        return _xtts_model
    try:
        from TTS.api import TTS
        print("[Voice Cloning Engine] Loading local XTTS Neural Model...")
        _xtts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cpu")
        print("[Voice Cloning Engine] XTTS Neural Model loaded successfully!")
        return _xtts_model
    except Exception as e:
        print(f"[Voice Cloning Engine] XTTS Neural Model not loaded: {e}")
        return None

def analyze_sample_audio_features(audio_path: str):
    """
    Extracts deep audio features from uploaded sample MP3/WAV:
    1. Gender (male vs female)
    2. Estimated Fundamental Frequency (Pitch in Hz)
    3. Speaking Tempo / Pace factor (relative to standard speaking speed)
    """
    try:
        ffmpeg_bin = get_ffmpeg_cmd()
        # Convert to 16kHz Mono PCM for analysis
        cmd = [ffmpeg_bin, '-y', '-i', audio_path, '-f', 's16le', '-ac', '1', '-ar', '16000', '-acodec', 'pcm_s16le', 'pipe:1']
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        raw_data, _ = proc.communicate()
        if not raw_data or len(raw_data) < 3200:
            return 'male', 130, 1.0
        
        sample_count = len(raw_data) // 2
        samples = struct.unpack(f'<{sample_count}h', raw_data)
        
        zero_crossings = 0
        active_samples = 0
        threshold = 350  # Noise gate
        
        for i in range(1, len(samples)):
            abs_val = abs(samples[i])
            if abs_val > threshold:
                active_samples += 1
                if (samples[i] >= 0 and samples[i-1] < 0) or (samples[i] < 0 and samples[i-1] >= 0):
                    zero_crossings += 1
                    
        total_duration = sample_count / 16000.0
        active_duration = active_samples / 16000.0
        
        if active_duration <= 0.1:
            return 'male', 130, 1.0
            
        zcr_rate = zero_crossings / (2.0 * active_duration)
        gender = 'male' if zcr_rate < 165 else 'female'
        
        speech_ratio = active_duration / total_duration if total_duration > 0 else 0.75
        tempo_factor = speech_ratio / 0.75
        tempo_factor = max(0.75, min(1.35, tempo_factor))
        
        return gender, zcr_rate, tempo_factor
    except Exception as e:
        print(f"Audio feature extraction exception: {e}")
        return 'male', 130, 1.0

async def clone_voice_from_sample(sample_audio_path: str, text: str, output_path: str, language: str = "vi", gender: str = "auto", api_key: str = ""):
    if not os.path.exists(sample_audio_path):
        raise FileNotFoundError(f"Sample audio file not found: {sample_audio_path}")

    # 1. ElevenLabs Instant Voice Cloning (98% Voice Similarity)
    active_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")
    if active_key and active_key.strip():
        try:
            print("[ElevenLabs Engine] Synthesizing Instant Voice Cloning with 98% accuracy...")
            from services.elevenlabs_service import clone_voice_elevenlabs
            res = clone_voice_elevenlabs(sample_audio_path, text, output_path, active_key)
            if res and os.path.exists(res):
                return res
        except Exception as e11:
            print(f"[ElevenLabs Engine] Warning ({e11}), falling back to local neural engine...")

    # 2. Try OmniVoice Zero-Shot Neural Model
    try:
        from services.omnivoice_service import synthesize_omnivoice_clone
        res_path = synthesize_omnivoice_clone(sample_audio_path, text, output_path, language=language)
        if res_path and os.path.exists(res_path):
            return res_path
    except Exception as omni_err:
        print(f"[OmniVoice Engine] Warning ({omni_err}), trying XTTS / Feature-Matching Engine...")


    # 2. Try Neural Zero-Shot XTTS Model if installed
    model = get_xtts_model()
    if model is not None:
        try:
            lang_code = "vi" if "vi" in language.lower() else "en"
            model.tts_to_file(
                text=text,
                speaker_wav=sample_audio_path,
                language=lang_code,
                file_path=output_path
            )
            return output_path
        except Exception as err:
            print(f"[XTTS Neural Engine] Warning ({err}), using Feature-Matched Synthesis Engine...")


    # 2. Audio Feature Matching Engine (Tempo + Pitch Matching)
    detected_gender, estimated_pitch, tempo_factor = analyze_sample_audio_features(sample_audio_path)
    print(f"[Feature Matching Engine] Sample: {os.path.basename(sample_audio_path)} | Gender: {detected_gender} | Pitch: {estimated_pitch:.1f}Hz | Tempo Factor: {tempo_factor:.2f}x")
    
    target_gender = gender if gender in ["male", "female"] else detected_gender
    is_vietnamese = "vi" in language.lower() or any(c in text for c in "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")
    
    if target_gender == "male":
        base_voice = "vi-VN-NamMinhNeural" if is_vietnamese else "en-US-AndrewNeural"
        base_pitch = 125.0
    else:
        base_voice = "vi-VN-HoaiMyNeural" if is_vietnamese else "en-US-AvaNeural"
        base_pitch = 210.0
        
    pitch_diff_hz = int(round(estimated_pitch - base_pitch))
    pitch_diff_hz = max(-15, min(15, pitch_diff_hz))  # Keep within edge-tts safe range
    
    rate_percent = int(round((tempo_factor - 1.0) * 100))
    rate_percent = max(-25, min(30, rate_percent))  # Keep within edge-tts safe range
    
    pitch_str = f"{pitch_diff_hz:+d}Hz" if pitch_diff_hz != 0 else "+0Hz"
    rate_str = f"{rate_percent:+d}%" if rate_percent != 0 else "+0%"
    
    print(f"[Feature Matching Engine] Selected Voice: {base_voice} | Rate: {rate_str} | Pitch: {pitch_str}")
    
    communicate = edge_tts.Communicate(text, base_voice, rate=rate_str, pitch=pitch_str)
    await communicate.save(output_path)
    
    return output_path
