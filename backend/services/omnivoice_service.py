import os
import sys
import torch
import soundfile as sf
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models", "omnivoice")
os.makedirs(MODELS_DIR, exist_ok=True)

os.environ["HF_HOME"] = MODELS_DIR
os.environ["TRANSFORMERS_CACHE"] = MODELS_DIR

_omnivoice_pipeline = None

def get_ffmpeg_bin():
    bundled = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bin', 'ffmpeg-master-latest-win64-gpl', 'bin', 'ffmpeg.exe'))
    if os.path.exists(bundled):
        return bundled
    return 'ffmpeg'

def get_omnivoice_model():
    global _omnivoice_pipeline
    if _omnivoice_pipeline is not None:
        return _omnivoice_pipeline
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        model_id = "k2-fsa/OmniVoice"
        print(f"[OmniVoice Engine] Loading model '{model_id}' into local directory {MODELS_DIR}...")
        
        tokenizer = AutoTokenizer.from_pretrained(model_id, cache_dir=MODELS_DIR, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            cache_dir=MODELS_DIR,
            torch_dtype=torch.float32,
            trust_remote_code=True
        ).to("cpu")
        
        _omnivoice_pipeline = {"model": model, "tokenizer": tokenizer}
        print("[OmniVoice Engine] OmniVoice model loaded successfully!")
        return _omnivoice_pipeline
    except Exception as e:
        print(f"[OmniVoice Engine] Could not load OmniVoice model directly ({e}). Using feature matching engine.")
        return None

def synthesize_omnivoice_clone(sample_audio_path: str, text: str, output_path: str, language: str = "vi"):
    """
    Synthesizes speech cloning target sample audio using local OmniVoice model weights.
    Returns path to output MP3 file.
    """
    if not os.path.exists(sample_audio_path):
        raise FileNotFoundError(f"Sample audio file not found: {sample_audio_path}")

    pipe = get_omnivoice_model()
    if pipe is not None:
        try:
            model = pipe["model"]
            tokenizer = pipe["tokenizer"]
            
            # Prepare inputs for OmniVoice zero-shot voice cloning
            print(f"[OmniVoice Engine] Synthesizing text: '{text[:30]}...' with reference: {os.path.basename(sample_audio_path)}")
            
            # Generate speech waveform tensor
            if hasattr(model, "generate_speech"):
                wav_tensor = model.generate_speech(prompt_wav=sample_audio_path, text=text, language=language)
            elif hasattr(model, "tts"):
                wav_tensor = model.tts(text=text, speaker_wav=sample_audio_path)
            else:
                inputs = tokenizer(text, return_tensors="pt")
                with torch.no_grad():
                    wav_tensor = model.generate(**inputs)
                    
            temp_wav = output_path.replace(".mp3", ".wav")
            if isinstance(wav_tensor, torch.Tensor):
                wav_np = wav_tensor.cpu().numpy().squeeze()
                sf.write(temp_wav, wav_np, 24000)
            elif isinstance(wav_tensor, str) and os.path.exists(wav_tensor):
                temp_wav = wav_tensor
                
            # Convert WAV to MP3 using ffmpeg
            ffmpeg_bin = get_ffmpeg_bin()
            subprocess.run([ffmpeg_bin, "-y", "-i", temp_wav, "-acodec", "libmp3lame", "-q:a", "2", output_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(temp_wav) and temp_wav != output_path:
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass
            return output_path
        except Exception as err:
            print(f"[OmniVoice Engine] Inference warning ({err}), falling back to feature matching engine...")
            
    return None
