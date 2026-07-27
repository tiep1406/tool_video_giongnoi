import edge_tts
import asyncio
import os

AVAILABLE_VOICES = [
    {"id": "vi-VN-HoaiMyNeural", "name": "Hoài My (Nữ - Tiếng Việt)", "lang": "vi-VN", "gender": "Female"},
    {"id": "vi-VN-NamMinhNeural", "name": "Nam Minh (Nam - Tiếng Việt)", "lang": "vi-VN", "gender": "Male"},
    {"id": "en-US-AvaNeural", "name": "Ava (Nữ - Tiếng Anh Mỹ)", "lang": "en-US", "gender": "Female"},
    {"id": "en-US-AndrewNeural", "name": "Andrew (Nam - Tiếng Anh Mỹ)", "lang": "en-US", "gender": "Male"},
    {"id": "en-US-EmmaNeural", "name": "Emma (Nữ - Tiếng Anh Mỹ)", "lang": "en-US", "gender": "Female"},
    {"id": "ja-JP-NanamiNeural", "name": "Nanami (Nữ - Tiếng Nhật)", "lang": "ja-JP", "gender": "Female"},
    {"id": "zh-CN-XiaoxiaoNeural", "name": "Xiaoxiao (Nữ - Tiếng Trung)", "lang": "zh-CN", "gender": "Female"}
]

def get_available_voices():
    return AVAILABLE_VOICES

async def generate_audio(text: str, output_path: str, voice: str = "vi-VN-HoaiMyNeural", rate: str = "+0%", pitch: str = "+0Hz"):
    if not voice:
        voice = "vi-VN-HoaiMyNeural"
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)
    return output_path

