import edge_tts
import asyncio
import os

DEFAULT_VOICES = [
    {"id": "vi-VN-HoaiMyNeural", "name": "Hoài My (Nữ - Tiếng Việt)", "lang": "vi-VN", "gender": "Female"},
    {"id": "vi-VN-NamMinhNeural", "name": "Nam Minh (Nam - Tiếng Việt)", "lang": "vi-VN", "gender": "Male"},
    {"id": "en-US-AvaNeural", "name": "Ava (Nữ - Tiếng Anh Mỹ)", "lang": "en-US", "gender": "Female"},
    {"id": "en-US-AndrewNeural", "name": "Andrew (Nam - Tiếng Anh Mỹ)", "lang": "en-US", "gender": "Male"},
    {"id": "en-US-EmmaNeural", "name": "Emma (Nữ - Tiếng Anh Mỹ)", "lang": "en-US", "gender": "Female"},
    {"id": "ja-JP-NanamiNeural", "name": "Nanami (Nữ - Tiếng Nhật)", "lang": "ja-JP", "gender": "Female"},
    {"id": "zh-CN-XiaoxiaoNeural", "name": "Xiaoxiao (Nữ - Tiếng Trung)", "lang": "zh-CN", "gender": "Female"}
]

_cached_voices = []

async def fetch_all_voices():
    global _cached_voices
    if _cached_voices and len(_cached_voices) > 0:
        return _cached_voices
    try:
        raw_voices = await edge_tts.list_voices()
        formatted = []
        for v in raw_voices:
            short_name = v.get("ShortName", "")
            gender = v.get("Gender", "")
            locale = v.get("Locale", "")
            
            name_parts = short_name.split("-")
            voice_code = name_parts[-1].replace("Neural", "") if len(name_parts) >= 3 else short_name
            gender_label = "Nữ" if gender.lower() == "female" else "Nam"
            friendly_name = f"{voice_code} ({gender_label} - {locale})"
            
            formatted.append({
                "id": short_name,
                "name": friendly_name,
                "lang": locale,
                "gender": gender
            })
        
        # Priority sort: Vietnamese first, English US second, then alphabetically
        formatted.sort(key=lambda x: (
            0 if "vi-" in x["lang"].lower() 
            else (1 if "en-us" in x["lang"].lower() 
            else (2 if "en-" in x["lang"].lower() else 3)),
            x["name"]
        ))
        _cached_voices = formatted
        return _cached_voices
    except Exception as e:
        print(f"Error fetching full voice list: {e}")
        return DEFAULT_VOICES

def get_available_voices():
    if _cached_voices and len(_cached_voices) > 0:
        return _cached_voices
    return DEFAULT_VOICES

async def generate_audio(text: str, output_path: str, voice: str = "vi-VN-HoaiMyNeural", rate: str = "+0%", pitch: str = "+0Hz"):
    if not voice:
        voice = "vi-VN-HoaiMyNeural"
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)
    return output_path


