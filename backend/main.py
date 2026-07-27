from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import shutil

app = FastAPI(title="AI Video Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str
    tone: str
    prompt: str = ""

class TTSRequest(BaseModel):
    text: str
    voice: str = "vi-VN-HoaiMyNeural"
    rate: str = "+0%"
    pitch: str = "+0Hz"

class PresetTTSRequest(BaseModel):
    preset_id: str
    text: str

import uuid
from services.crawler import extract_content
from services.llm import generate_storyboard

@app.get("/")
def read_root():
    return {"status": "ok", "message": "AI Video Generator Backend is running"}

@app.get("/api/tts/voices")
async def get_tts_voices():
    from services.tts import fetch_all_voices
    voices = await fetch_all_voices()
    return {"status": "success", "voices": voices, "total": len(voices)}

@app.get("/api/tts/presets")
def get_tts_presets():
    from services.tts_presets import get_vietnamese_presets
    return {"status": "success", "presets": get_vietnamese_presets()}

@app.post("/api/tts/generate_preset")
async def generate_preset_tts(request: PresetTTSRequest):
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Văn bản không được để trống")
        
    tts_dir = os.path.join("..", "data", "tts")
    os.makedirs(tts_dir, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    output_path = os.path.join(tts_dir, f"{file_id}.mp3")
    
    from services.tts_presets import generate_preset_audio
    try:
        await generate_preset_audio(request.preset_id, request.text, output_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi sinh giọng mẫu: {str(e)}")
        
    return {
        "status": "success",
        "audio_url": f"http://localhost:8000/data/tts/{file_id}.mp3",
        "file_id": file_id
    }



@app.post("/api/tts/generate")
async def generate_tts(request: TTSRequest):
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Văn bản không được để trống")
    
    tts_dir = os.path.join("..", "data", "tts")
    os.makedirs(tts_dir, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    output_path = os.path.join(tts_dir, f"{file_id}.mp3")
    
    from services.tts import generate_audio
    try:
        await generate_audio(request.text, output_path, voice=request.voice, rate=request.rate, pitch=request.pitch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tạo giọng nói: {str(e)}")
        
    return {
        "status": "success",
        "audio_url": f"http://localhost:8000/data/tts/{file_id}.mp3",
        "file_id": file_id
    }

@app.post("/api/tts/preview_scene")
async def preview_scene_audio(request: TTSRequest):
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Văn bản không được để trống")
    
    tts_dir = os.path.join("..", "data", "tts_preview")
    os.makedirs(tts_dir, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    output_path = os.path.join(tts_dir, f"{file_id}.mp3")
    
    from services.tts import generate_audio
    try:
        await generate_audio(request.text, output_path, voice=request.voice, rate=request.rate, pitch=request.pitch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tạo âm thanh: {str(e)}")
        
    return {
        "status": "success",
        "audio_url": f"http://localhost:8000/data/tts_preview/{file_id}.mp3"
    }

@app.post("/api/tts/clone")
async def clone_tts_voice(
    text: str = Form(...),
    language: str = Form("vi"),
    gender: str = Form("auto"),
    api_key: str = Form(""),
    sample_file: UploadFile = File(...)
):
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Văn bản không được để trống")
    
    samples_dir = os.path.join("..", "data", "samples")
    os.makedirs(samples_dir, exist_ok=True)
    
    tts_dir = os.path.join("..", "data", "tts")
    os.makedirs(tts_dir, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    sample_ext = os.path.splitext(sample_file.filename)[1] or ".mp3"
    sample_path = os.path.join(samples_dir, f"{file_id}{sample_ext}")
    
    with open(sample_path, "wb") as buffer:
        shutil.copyfileobj(sample_file.file, buffer)
        
    output_path = os.path.join(tts_dir, f"cloned_{file_id}.mp3")
    
    from services.tts_local import clone_voice_from_sample
    try:
        await clone_voice_from_sample(sample_path, text, output_path, language=language, gender=gender, api_key=api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi nhái giọng nói: {str(e)}")


        
    return {
        "status": "success",
        "audio_url": f"http://localhost:8000/data/tts/cloned_{file_id}.mp3",
        "file_id": file_id
    }



@app.post("/api/generate")
async def generate_video(request: VideoRequest):
    try:
        content = extract_content(request.url)
        source_info = extract_content(request.url)
        if not source_info:
            raise HTTPException(status_code=400, detail="Failed to extract content")

        storyboard = generate_storyboard(source_info, request.tone, request.prompt)
        
        if isinstance(storyboard, dict) and "error" in storyboard:
            raise HTTPException(status_code=500, detail=storyboard["error"])

        session_id = str(uuid.uuid4())
        session_dir = os.path.join("..", "data", session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # Save metadata for history
        import json
        import datetime
        metadata = {
            "session_id": session_id,
            "url": request.url,
            "title": source_info.get("title", "Unknown Title"),
            "timestamp": datetime.datetime.now().isoformat(),
            "storyboard": storyboard,
            "source_info": source_info
        }
        with open(os.path.join(session_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "success",
            "session_id": session_id,
            "storyboard": storyboard,
            "source_info": {
                "thumbnail": content.get("thumbnail")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        with open("error_log.txt", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload_scene_image/{session_id}/{scene_index}")
async def upload_scene_image(session_id: str, scene_index: int, file: UploadFile = File(...)):
    session_dir = os.path.join("..", "data", session_id)
    os.makedirs(session_dir, exist_ok=True)
    file_ext = os.path.splitext(file.filename)[1] or ".jpg"
    file_path = os.path.join(session_dir, f"scene_{scene_index}{file_ext}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "success", "file_path": file_path}

@app.get("/api/history")
async def get_history():
    data_dir = os.path.join("..", "data")
    if not os.path.exists(data_dir):
        return {"history": []}
        
    history = []
    import json
    for session_id in os.listdir(data_dir):
        meta_path = os.path.join(data_dir, session_id, "metadata.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    history.append({
                        "session_id": meta["session_id"],
                        "title": meta.get("title", "Untitled"),
                        "timestamp": meta.get("timestamp", "")
                    })
            except Exception:
                pass
                
    history.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"history": history}

@app.get("/api/history/{session_id}")
async def get_history_detail(session_id: str):
    meta_path = os.path.join("..", "data", session_id, "metadata.json")
    if not os.path.exists(meta_path):
        raise HTTPException(status_code=404, detail="Session not found")
        
    import json
    import glob
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
        
    # Find existing uploaded images
    scene_images = {}
    for i in range(len(meta.get("storyboard", []))):
        uploaded = glob.glob(os.path.join("..", "data", session_id, f"scene_{i}.*"))
        uploaded = [p for p in uploaded if not p.endswith(".mp3")]
        if uploaded:
            scene_images[i] = f"http://localhost:8000/data/{session_id}/{os.path.basename(uploaded[0])}"
            
    meta["scene_images"] = scene_images
    
    if os.path.exists(os.path.join("..", "data", session_id, "final_video.mp4")):
        meta["video_url"] = f"http://localhost:8000/data/{session_id}/final_video.mp4"
        
    return meta

class RenderRequest(BaseModel):
    session_id: str
    storyboard: list
    source_info: dict
    voice: str = "vi-VN-HoaiMyNeural"

@app.post("/api/render")
async def render_final_video(request: RenderRequest):
    try:
        session_dir = os.path.join("..", "data", request.session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # Download fallback images
        fallback_images = []
        img_urls = request.source_info.get("images", [])
        if not img_urls and request.source_info.get("thumbnail"):
            img_urls = [request.source_info.get("thumbnail")]
            
        if img_urls:
            img_count = 1
            for url_candidate in img_urls:
                if url_candidate.startswith("http") and ".svg" not in url_candidate.lower() and ".gif" not in url_candidate.lower():
                    img_path = os.path.join(session_dir, f"fallback_{img_count:03d}.jpg")
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    try:
                        res = requests.get(url_candidate, headers=headers, timeout=5)
                        if res.status_code == 200:
                            with open(img_path, "wb") as f:
                                f.write(res.content)
                            fallback_images.append(img_path)
                            img_count += 1
                            if img_count > 5:
                                break
                    except:
                        continue
        
        # We don't raise an error if fallback_images is empty anymore.
        # We will use a black screen for scenes without any image.

        from services.tts import generate_audio
        scene_files = []
        
        import glob
        for i, scene in enumerate(request.storyboard):
            # Generate Audio for this specific scene
            scene_audio_path = os.path.join(session_dir, f"scene_{i}.mp3")
            script_text = scene.get("script", "")
            scene_voice = scene.get("voice") or request.voice or "vi-VN-HoaiMyNeural"
            if not script_text.strip() or len(script_text.strip()) < 2:
                script_text = "Chuyển cảnh."
                
            try:
                import asyncio
                # Try generating the original script
                try:
                    await generate_audio(script_text, scene_audio_path, voice=scene_voice)
                except Exception:
                    # Retry once after delay
                    await asyncio.sleep(1)
                    await generate_audio(script_text, scene_audio_path, voice=scene_voice)
            except Exception as e:
                # If it still fails, fallback to short text
                await asyncio.sleep(1)
                try:
                    await generate_audio("Chuyển cảnh.", scene_audio_path, voice=scene_voice)
                except Exception:
                    # If absolutely everything fails, generate a silent mp3 using ffmpeg
                    import subprocess
                    subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono', '-t', '2', '-q:a', '9', '-acodec', 'libmp3lame', scene_audio_path], check=True)

            
            # Find if user uploaded an image for this scene
            # We look for scene_i.* 
            uploaded_patterns = glob.glob(os.path.join(session_dir, f"scene_{i}.*"))
            # Filter out mp3s, we only want images
            uploaded_images = [p for p in uploaded_patterns if not p.endswith(".mp3")]
            
            if uploaded_images:
                scene_image_path = uploaded_images[0]
            elif fallback_images:
                # Use a fallback image
                scene_image_path = fallback_images[i % len(fallback_images)]
            else:
                scene_image_path = "BLACK"
                
            scene_files.append({"audio": scene_audio_path, "image": scene_image_path})
            
        output_path = os.path.join(session_dir, "final_video.mp4")
        from services.video import render_video
        
        result = render_video(scene_files, output_path, session_dir)
        
        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
            
        return {"status": "success", "video_url": f"http://localhost:8000/data/{request.session_id}/final_video.mp4"}
    except HTTPException as he:
        with open("error_log.txt", "w", encoding="utf-8") as f:
            f.write(f"HTTPException: {he.status_code} - {he.detail}")
        raise
    except Exception as e:
        import traceback
        with open("error_log.txt", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.staticfiles import StaticFiles
data_dir = os.path.join("..", "data")
os.makedirs(data_dir, exist_ok=True)
app.mount("/data", StaticFiles(directory=data_dir), name="data")
