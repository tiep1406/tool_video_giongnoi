import edge_tts
import asyncio
import os

VIETNAMESE_CUSTOM_VOICES = [
    {"id": "vi-VN-NamMinhNeural", "name": "🇻🇳 Nam Minh (Nam - Chuẩn Tiếng Việt)", "lang": "vi-VN", "gender": "Male", "rate": "+0%", "pitch": "+0Hz"},
    {"id": "vi-VN-HoaiMyNeural", "name": "🇻🇳 Hoài My (Nữ - Chuẩn Tiếng Việt)", "lang": "vi-VN", "gender": "Female", "rate": "+0%", "pitch": "+0Hz"},
    {"id": "vi-VN-NamMinh-ReviewPhim", "name": "🇻🇳 Nam Trầm Ấm (Review Phim / Phóng Sự)", "lang": "vi-VN", "gender": "Male", "real_voice": "vi-VN-NamMinhNeural", "rate": "-10%", "pitch": "-6Hz"},
    {"id": "vi-VN-NamMinh-ThoiSu", "name": "🇻🇳 Nam Thời Sự (Bản Tin Chính Luận VTV)", "lang": "vi-VN", "gender": "Male", "real_voice": "vi-VN-NamMinhNeural", "rate": "+5%", "pitch": "+0Hz"},
    {"id": "vi-VN-NamMinh-TheThao", "name": "🇻🇳 Nam Thể Thao / Công Nghệ (Sôi Nổi)", "lang": "vi-VN", "gender": "Male", "real_voice": "vi-VN-NamMinhNeural", "rate": "+20%", "pitch": "+2Hz"},
    {"id": "vi-VN-NamMinh-QuangCao", "name": "🇻🇳 Nam Quảng Cáo / Trailer (Mạnh Mẽ)", "lang": "vi-VN", "gender": "Male", "real_voice": "vi-VN-NamMinhNeural", "rate": "+0%", "pitch": "-10Hz"},
    {"id": "vi-VN-HoaiMy-TruyenCam", "name": "🇻🇳 Nữ Truyền Cảm (Đọc Truyện Đêm Khuya)", "lang": "vi-VN", "gender": "Female", "real_voice": "vi-VN-HoaiMyNeural", "rate": "-15%", "pitch": "-4Hz"},
    {"id": "vi-VN-HoaiMy-TikTok", "name": "🇻🇳 Nữ TikTok Viral (Reels / Short Video)", "lang": "vi-VN", "gender": "Female", "real_voice": "vi-VN-HoaiMyNeural", "rate": "+20%", "pitch": "+4Hz"},
    {"id": "vi-VN-HoaiMy-CoTich", "name": "🇻🇳 Nữ Kể Chuyện Cổ Tích (Thiếu Nhi)", "lang": "vi-VN", "gender": "Female", "real_voice": "vi-VN-HoaiMyNeural", "rate": "-8%", "pitch": "+6Hz"},
    {"id": "vi-VN-HoaiMy-BanTin", "name": "🇻🇳 Nữ Phát Thanh Viên Truyền Hình", "lang": "vi-VN", "gender": "Female", "real_voice": "vi-VN-HoaiMyNeural", "rate": "+0%", "pitch": "+0Hz"},
    
    # Multilingual AI Voices that read Vietnamese fluently
    {"id": "en-US-AndrewMultilingualNeural", "name": "🌐 Andrew AI (Nam - Multilingual Đọc Tiếng Việt)", "lang": "en-US", "gender": "Male"},
    {"id": "en-US-AvaMultilingualNeural", "name": "🌐 Ava AI (Nữ - Multilingual Đọc Tiếng Việt)", "lang": "en-US", "gender": "Female"},
    {"id": "en-US-BrianMultilingualNeural", "name": "🌐 Brian AI (Nam - Multilingual Đọc Tiếng Việt)", "lang": "en-US", "gender": "Male"},
    {"id": "en-US-EmmaMultilingualNeural", "name": "🌐 Emma AI (Nữ - Multilingual Đọc Tiếng Việt)", "lang": "en-US", "gender": "Female"},
    {"id": "de-DE-FlorianMultilingualNeural", "name": "🌐 Florian AI (Nam - Multilingual Đọc Tiếng Việt)", "lang": "de-DE", "gender": "Male"},
    {"id": "fr-FR-VivienneMultilingualNeural", "name": "🌐 Vivienne AI (Nữ - Multilingual Đọc Tiếng Việt)", "lang": "fr-FR", "gender": "Female"},
    {"id": "pt-BR-ThalitaMultilingualNeural", "name": "🌐 Thalita AI (Nữ - Multilingual Đọc Tiếng Việt)", "lang": "pt-BR", "gender": "Female"},
    {"id": "de-DE-SeraphinaMultilingualNeural", "name": "🌐 Seraphina AI (Nữ - Multilingual Đọc Tiếng Việt)", "lang": "de-DE", "gender": "Female"},
    {"id": "fr-FR-RemyMultilingualNeural", "name": "🌐 Remy AI (Nam - Multilingual Đọc Tiếng Việt)", "lang": "fr-FR", "gender": "Male"},
    {"id": "it-IT-GiuseppeMultilingualNeural", "name": "🌐 Giuseppe AI (Nam - Multilingual Đọc Tiếng Việt)", "lang": "it-IT", "gender": "Male"},
    {"id": "ko-KR-HyunsuMultilingualNeural", "name": "🌐 Hyunsu AI (Nam - Multilingual Đọc Tiếng Việt)", "lang": "ko-KR", "gender": "Male"},
    {"id": "en-AU-WilliamMultilingualNeural", "name": "🌐 William AI (Nam - Multilingual Đọc Tiếng Việt)", "lang": "en-AU", "gender": "Male"}
]

_cached_voices = []

async def fetch_all_voices():
    global _cached_voices
    if _cached_voices and len(_cached_voices) > 0:
        return _cached_voices
    try:
        raw_voices = await edge_tts.list_voices()
        formatted = list(VIETNAMESE_CUSTOM_VOICES)
        custom_ids = {v["id"] for v in VIETNAMESE_CUSTOM_VOICES}
        
        for v in raw_voices:
            short_name = v.get("ShortName", "")
            if short_name in custom_ids:
                continue
                
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
        
        _cached_voices = formatted
        return _cached_voices
    except Exception as e:
        print(f"Error fetching full voice list: {e}")
        return VIETNAMESE_CUSTOM_VOICES

def get_available_voices():
    if _cached_voices and len(_cached_voices) > 0:
        return _cached_voices
    return VIETNAMESE_CUSTOM_VOICES

async def generate_audio(text: str, output_path: str, voice: str = "vi-VN-HoaiMyNeural", rate: str = "+0%", pitch: str = "+0Hz"):
    if not voice:
        voice = "vi-VN-HoaiMyNeural"
        
    # Check if voice is one of our Vietnamese custom preset IDs
    custom = next((v for v in VIETNAMESE_CUSTOM_VOICES if v["id"] == voice), None)
    if custom and "real_voice" in custom:
        voice_id = custom["real_voice"]
        rate = custom.get("rate", rate)
        pitch = custom.get("pitch", pitch)
    else:
        voice_id = voice

    communicate = edge_tts.Communicate(text, voice_id, rate=rate, pitch=pitch)
    await communicate.save(output_path)
    return output_path



