import os
import edge_tts
import asyncio

VIETNAMESE_PRESETS = [
    {
        "id": "preset_nam_review_phim",
        "name": "🎙️ Giọng Nam Trầm Ấm (Review Phim / Thuyết Minh)",
        "gender": "Male",
        "base_voice": "vi-VN-NamMinhNeural",
        "pitch": "-6Hz",
        "rate": "-10%",
        "description": "Giọng nam trầm ấm, độ hoãn vừa phải, cực kỳ cuốn hút khi làm video review phim, tài liệu."
    },
    {
        "id": "preset_nam_thoi_su",
        "name": "📰 Giọng Nam Thời Sự (Bản Tin Chính Luận)",
        "gender": "Male",
        "base_voice": "vi-VN-NamMinhNeural",
        "pitch": "+0Hz",
        "rate": "+5%",
        "description": "Giọng nam đọc chuẩn phát âm, dứt khoát, chuyên dùng cho bản tin thời sự VTV, tin tức nóng."
    },
    {
        "id": "preset_nu_truyen_cam",
        "name": "📻 Giọng Nữ Truyền Cảm (Đọc Truyện / Tâm Sự)",
        "gender": "Female",
        "base_voice": "vi-VN-HoaiMyNeural",
        "pitch": "-4Hz",
        "rate": "-15%",
        "description": "Giọng nữ dịu dàng, trầm lắng, rất hợp đọc truyện đêm khuya, podcast tâm sự, đọc thơ."
    },
    {
        "id": "preset_nu_tiktok",
        "name": "📱 Giọng Nữ TikTok Viral (Short Video / Trend)",
        "gender": "Female",
        "base_voice": "vi-VN-HoaiMyNeural",
        "pitch": "+4Hz",
        "rate": "+20%",
        "description": "Giọng nữ trẻ trung, nhịp điệu nhanh, năng động dành riêng cho video ngắn TikTok, Reels."
    },
    {
        "id": "preset_nam_the_thao",
        "name": "⚽ Giọng Nam Thể Thao / Công Nghệ (Sôi Nổi)",
        "gender": "Male",
        "base_voice": "vi-VN-NamMinhNeural",
        "pitch": "+2Hz",
        "rate": "+25%",
        "description": "Giọng nam dứt khoát, sôi nổi, thích hợp bình luận thể thao, tin công nghệ, xe hơi."
    },
    {
        "id": "preset_nu_co_tich",
        "name": "📖 Giọng Nữ Kể Chuyện Cổ Tích / Thiếu Nhi",
        "gender": "Female",
        "base_voice": "vi-VN-HoaiMyNeural",
        "pitch": "+6Hz",
        "rate": "-8%",
        "description": "Giọng nữ trong trẻo, âm sắc cao nhẹ, đọc chậm rãi cho truyện cổ tích thiếu nhi."
    },
    {
        "id": "preset_nam_quang_cao",
        "name": "📢 Giọng Nam Quảng Cáo / Trailer (Mạnh Mẽ)",
        "gender": "Male",
        "base_voice": "vi-VN-NamMinhNeural",
        "pitch": "-10Hz",
        "rate": "+0%",
        "description": "Giọng nam cực trầm, uy lực, thích hợp lồng tiếng quảng cáo, trailer phim giật gân."
    },
    {
        "id": "preset_nu_ban_tin",
        "name": "📺 Giọng Nữ Phát Thanh Viên Thời Sự",
        "gender": "Female",
        "base_voice": "vi-VN-HoaiMyNeural",
        "pitch": "+0Hz",
        "rate": "+0%",
        "description": "Giọng nữ phát thanh viên chuẩn mực, rõ từ tròn tiếng cho bản tin truyền hình."
    }
]

def get_vietnamese_presets():
    return VIETNAMESE_PRESETS

async def generate_preset_audio(preset_id: str, text: str, output_path: str):
    preset = next((p for p in VIETNAMESE_PRESETS if p["id"] == preset_id), None)
    if not preset:
        preset = VIETNAMESE_PRESETS[0]
        
    voice = preset["base_voice"]
    rate = preset["rate"]
    pitch = preset["pitch"]
    
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)
    return output_path
