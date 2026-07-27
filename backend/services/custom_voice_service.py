import os
import json
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUSTOM_VOICES_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "custom_voices"))
VOICES_JSON_PATH = os.path.join(CUSTOM_VOICES_DIR, "voices.json")

def ensure_custom_voices_dir():
    os.makedirs(CUSTOM_VOICES_DIR, exist_ok=True)
    if not os.path.exists(VOICES_JSON_PATH):
        with open(VOICES_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

def load_custom_voices():
    ensure_custom_voices_dir()
    try:
        with open(VOICES_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading custom voices: {e}")
        return []

def save_custom_voice_entry(name: str, gender: str, language: str, sample_file_path: str):
    ensure_custom_voices_dir()
    voices = load_custom_voices()
    
    voice_id = f"custom_voice_{uuid.uuid4().hex[:8]}"
    dest_filename = f"{voice_id}.mp3"
    dest_path = os.path.join(CUSTOM_VOICES_DIR, dest_filename)
    
    import shutil
    shutil.copyfile(sample_audio_path if 'sample_audio_path' in locals() else sample_file_path, dest_path)
    
    gender_label = "Nam" if gender.lower() == "male" else ("Nữ" if gender.lower() == "female" else "Tự chọn")
    entry = {
        "id": voice_id,
        "name": f"⭐ {name} ({gender_label} - Import)",
        "gender": gender,
        "lang": language,
        "sample_path": dest_path,
        "is_custom": True
    }
    
    voices.insert(0, entry)
    with open(VOICES_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(voices, f, ensure_ascii=False, indent=2)
        
    return entry

def delete_custom_voice_entry(voice_id: str):
    ensure_custom_voices_dir()
    voices = load_custom_voices()
    updated = [v for v in voices if v["id"] != voice_id]
    
    target_path = os.path.join(CUSTOM_VOICES_DIR, f"{voice_id}.mp3")
    if os.path.exists(target_path):
        try:
            os.remove(target_path)
        except Exception:
            pass
            
    with open(VOICES_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)
        
    return True
