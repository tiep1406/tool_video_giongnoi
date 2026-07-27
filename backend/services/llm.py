import os
from dotenv import load_dotenv
import json
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

def generate_storyboard(content_data: dict, tone: str, prompt: str):
    if not api_key or api_key == "your_api_key_here":
        return {"error": "Missing GEMINI_API_KEY in .env file"}

    try:
        # Initialize client with api_key
        client = genai.Client(api_key=api_key)
        
        system_prompt = f"""
        Bạn là một Biên kịch & Đạo diễn video. 
        Dựa trên nội dung cung cấp, hãy tạo kịch bản video (storyboard) trả về ĐÚNG định dạng JSON.
        Giọng điệu (Tone): {tone}.
        Chỉ thị thêm: {prompt}.
        Nội dung nguồn:
        Tiêu đề: {content_data.get('title')}
        Nội dung: {content_data.get('content') or content_data.get('description')}
        
        Định dạng JSON yêu cầu:
        [
          {{
            "scene": 1,
            "script": "Lời thoại của MC",
            "visual_cue": "Mô tả hình ảnh nên hiện",
            "on_screen_text": "Chữ chạy dưới màn hình"
          }}
        ]
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=system_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        return json.loads(text.strip())
    except Exception as e:
        return {"error": f"Lỗi gọi Gemini API: {str(e)}"}
