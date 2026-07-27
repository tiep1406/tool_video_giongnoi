import os
import requests

def clone_voice_elevenlabs(sample_audio_path: str, text: str, output_path: str, api_key: str):
    """
    Uses ElevenLabs Instant Voice Cloning API to clone voice from sample_audio_path
    and synthesize text with 95-98% voice similarity.
    """
    if not api_key or not api_key.strip():
        raise ValueError("Thiếu ElevenLabs API Key.")
        
    if not os.path.exists(sample_audio_path):
        raise FileNotFoundError(f"File mẫu không tồn tại: {sample_audio_path}")

    headers = {
        "xi-api-key": api_key.strip()
    }

    # 1. Add voice sample to ElevenLabs Instant Voice Cloning
    voice_name = f"Clone_{os.path.basename(sample_audio_path)[:10]}_{os.urandom(2).hex()}"
    add_voice_url = "https://api.elevenlabs.io/v1/voices/add"
    
    with open(sample_audio_path, "rb") as f:
        files = {
            'files': (os.path.basename(sample_audio_path), f, 'audio/mpeg')
        }
        data = {
            'name': voice_name,
            'description': 'Cloned voice from user sample audio'
        }
        res = requests.post(add_voice_url, headers=headers, data=data, files=files)
        
    if res.status_code != 200:
        raise Exception(f"Lỗi tạo giọng ElevenLabs ({res.status_code}): {res.text}")
        
    voice_data = res.json()
    voice_id = voice_data.get("voice_id")
    
    if not voice_id:
        raise Exception("Không nhận được voice_id từ ElevenLabs.")

    # 2. Synthesize TTS with the cloned voice_id
    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",  # Best multilingual model for Vietnamese & English
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.85,
            "style": 0.2,
            "use_speaker_boost": True
        }
    }
    
    tts_res = requests.post(tts_url, headers={**headers, "Content-Type": "application/json"}, json=payload)
    if tts_res.status_code != 200:
        raise Exception(f"Lỗi đọc TTS ElevenLabs ({tts_res.status_code}): {tts_res.text}")

    with open(output_path, "wb") as f_out:
        f_out.write(tts_res.content)

    return output_path
