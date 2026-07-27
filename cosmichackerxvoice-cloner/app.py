#!/usr/bin/env python3
"""
OmniVoice Multilingual Voice Cloner
Space: cosmichackerx/voice-cloner

Zero-shot voice cloning & multilingual TTS powered by k2-fsa/OmniVoice.
Crash-hardened: long-form, multi-speaker, voice profiles, BGM ducking,
RVC-inspired polish (F0 / timbre / protect), OmniVoice advanced decoding.
"""

from __future__ import annotations

import dataclasses
import logging
import os
import re
import tempfile
import traceback
from typing import Any

import gradio as gr
import numpy as np

try:
    import spaces

except ImportError:
    class spaces:
        @staticmethod
        def GPU(*args, **kwargs):
            def decorator(fn):
                return fn
            if len(args) == 1 and callable(args[0]):
                return args[0]
            return decorator

import torch


import audio_enhance as ax

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
)
logger = logging.getLogger("voice-cloner")

CHECKPOINT = os.environ.get("OMNIVOICE_MODEL", "k2-fsa/OmniVoice")

MAX_CHARS_PER_CHUNK = 280
MAX_TOTAL_CHARS = 8000
MAX_CHUNKS = 24
MAX_DIALOGUE_TURNS = 20
CROSSFADE_MS = 40
SILENCE_GAP_MS = 180

FEATURED = [
    "Auto",
    "English",
    "Spanish",
    "French",
    "German",
    "Portuguese",
    "Italian",
    "Russian",
    "Chinese",
    "Japanese",
    "Korean",
    "Standard Arabic",
    "Hindi",
    "Turkish",
    "Indonesian",
    "Malay",
    "Vietnamese",
    "Thai",
    "Bengali",
    "Persian",
    "Urdu",
    "Dutch",
    "Polish",
    "Ukrainian",
    "Swahili",
]

STYLE_PRESETS: dict[str, str] = {
    "Neutral": "",
    "Laughing intro": "[laughter] ",
    "Sigh then speak": "[sigh] ",
    "Surprised": "[surprise-oh] ",
    "Questioning tone": "[question-en] ",
    "Confirmation tone": "[confirmation-en] ",
    "Dissatisfied": "[dissatisfaction-hnn] ",
}

NONVERBAL_HELP = (
    "Inline tags: [laughter] [sigh] [confirmation-en] [question-en] "
    "[question-ah] [question-oh] [surprise-ah] [surprise-oh] [dissatisfaction-hnn]"
)

# One-click demo scripts — upload voice → click prompt → generate
TRY_PROMPTS: dict[str, dict[str, str]] = {
    "YouTube intro": {
        "text": (
            "Hey everyone, welcome back to the channel. Today I'm breaking down "
            "something that actually changed how I create content — stay until the end."
        ),
        "language": "English",
        "mode": "Voice clone",
        "style": "Neutral",
        "instruct": "",
    },
    "Audiobook narrator": {
        "text": (
            "The old lighthouse stood against the storm, its lamp cutting through fog "
            "like a promise. She climbed the spiral stairs, heart steady, knowing the "
            "letter in her coat would change everything."
        ),
        "language": "English",
        "mode": "Voice clone",
        "style": "Neutral",
        "instruct": "",
    },
    "Podcast cold open": {
        "text": (
            "You're listening to Signal Check. I'm your host, and in the next twenty minutes "
            "we'll unpack the story nobody expected — and what it means for all of us."
        ),
        "language": "English",
        "mode": "Voice clone",
        "style": "Neutral",
        "instruct": "",
    },
    "Product ad read": {
        "text": (
            "Meet Clarity Buds — all-day comfort, studio-clean sound, and a battery that "
            "keeps up with your life. Free shipping this week. Tap the link and hear the difference."
        ),
        "language": "English",
        "mode": "Voice clone",
        "style": "Confirmation tone",
        "instruct": "",
    },
    "Meditation guide": {
        "text": (
            "Take a slow breath in… and gently release. Soften your shoulders. "
            "There is nowhere else you need to be. Just this moment, just this breath."
        ),
        "language": "English",
        "mode": "Voice clone",
        "style": "Neutral",
        "instruct": "",
    },
    "News bulletin": {
        "text": (
            "Good evening. In tonight's top story, researchers released new findings on "
            "multilingual speech synthesis, marking a major step for accessible AI voice technology worldwide."
        ),
        "language": "English",
        "mode": "Voice clone",
        "style": "Neutral",
        "instruct": "",
    },
    "Customer support": {
        "text": (
            "Thanks for calling. I can help with that. Please confirm the email on your account, "
            "and I'll walk you through the next steps carefully."
        ),
        "language": "English",
        "mode": "Voice clone",
        "style": "Neutral",
        "instruct": "",
    },
    "Gaming character": {
        "text": (
            "[surprise-oh] The gate is open! Stay close — if we lose the map now, "
            "the whole quest falls apart. Move!"
        ),
        "language": "English",
        "mode": "Voice clone",
        "style": "Surprised",
        "instruct": "",
    },
    "Laugh + punchline": {
        "text": (
            "[laughter] Okay, that was not in the script. But seriously — if your AI voice "
            "can laugh with you, you're already winning."
        ),
        "language": "English",
        "mode": "Voice clone",
        "style": "Laughing intro",
        "instruct": "",
    },
    "Spanish demo": {
        "text": (
            "Hola, este es un demo de clonación de voz. Puedo hablar con naturalidad "
            "en español usando solo unos segundos de audio de referencia."
        ),
        "language": "Spanish",
        "mode": "Voice clone",
        "style": "Neutral",
        "instruct": "",
    },
    "French demo": {
        "text": (
            "Bonjour ! Voici une démonstration de clonage vocal. Avec quelques secondes "
            "d'audio, on peut générer une voix naturelle en français."
        ),
        "language": "French",
        "mode": "Voice clone",
        "style": "Neutral",
        "instruct": "",
    },
    "Chinese demo": {
        "text": "大家好，这是零样本声音克隆演示。只需几秒参考音频，就能用中文自然地说出新的内容。",
        "language": "Chinese",
        "mode": "Voice clone",
        "style": "Neutral",
        "instruct": "",
    },
    "Arabic demo": {
        "text": "مرحبًا، هذا عرض لنسخ الصوت بالذكاء الاصطناعي. يمكنني التحدث بالعربية بصوت قريب من المرجع.",
        "language": "Standard Arabic",
        "mode": "Voice clone",
        "style": "Neutral",
        "instruct": "",
    },
    "Hindi demo": {
        "text": "नमस्ते! यह एक मुफ़्त एआई वॉइस क्लोन डेमो है। कुछ सेकंड के ऑडियो से नई हिंदी स्पीच बनाई जा सकती है।",
        "language": "Hindi",
        "mode": "Voice clone",
        "style": "Neutral",
        "instruct": "",
    },
    "Japanese demo": {
        "text": "こんにちは。これはゼロショット音声クローンのデモです。短い参考音声から、自然な日本語を生成できます。",
        "language": "Japanese",
        "mode": "Voice clone",
        "style": "Neutral",
        "instruct": "",
    },
    "Multi-speaker dialogue": {
        "text": (
            "[Speaker 1]: Did you try the new free AI voice cloner yet?\n"
            "[Speaker 2]: Yes — I uploaded ten seconds of audio and it already sounds like me.\n"
            "[Speaker 1]: Perfect for podcasts and YouTube voiceovers."
        ),
        "language": "English",
        "mode": "Multi-speaker dialogue",
        "style": "Neutral",
        "instruct": "",
    },
    "Voice design · British": {
        "text": (
            "This voice was designed from text attributes only — no reference clip required. "
            "Ideal when you need a consistent narrator fast."
        ),
        "language": "English",
        "mode": "Voice design (no reference)",
        "style": "Neutral",
        "instruct": "female, young adult, low pitch, british accent",
    },
    "Voice design · Whisper": {
        "text": "Come closer. Some secrets are meant to be whispered, not shouted.",
        "language": "English",
        "mode": "Voice design (no reference)",
        "style": "Neutral",
        "instruct": "male, middle-aged, low pitch, whisper",
    },
    "Long-form sample": {
        "text": (
            "Welcome to this long-form narration test. First, we set the scene with a calm introduction. "
            "Next, we explain why clean reference audio matters for voice cloning quality. "
            "Finally, we finish with a clear call to action: like the Space, try another prompt, "
            "and share your best clone with creators who need multilingual text to speech."
        ),
        "language": "English",
        "mode": "Voice clone",
        "style": "Neutral",
        "instruct": "",
    },
}

SPEAKER_RE = re.compile(
    r"^\s*\[?\s*(speaker\s*[12]|s\s*[12]|spk\s*[12])\s*\]?\s*[:\-–—]\s*(.+)$",
    re.IGNORECASE,
)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。！？…])\s+|(?<=[\n])\s*")

logger.info("Loading OmniVoice from %s ...", CHECKPOINT)
from omnivoice import OmniVoice, OmniVoiceGenerationConfig, VoiceClonePrompt

try:
    from omnivoice.utils.lang_map import LANG_NAMES, lang_display_name

    _ALL = sorted({lang_display_name(code) for code in LANG_NAMES})
except Exception:  # noqa: BLE001
    logger.warning("Language map unavailable; using featured list only.")
    _ALL = []

LANGUAGE_CHOICES = FEATURED + [name for name in _ALL if name not in FEATURED]

device_name = "cuda" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

model = OmniVoice.from_pretrained(
    CHECKPOINT,
    device_map=device_name,
    dtype=torch_dtype,
    load_asr=True,
)

SAMPLE_RATE = int(model.sampling_rate)
logger.info("Model ready (sample rate=%s).", SAMPLE_RATE)

try:
    _GEN_FIELDS = {f.name for f in dataclasses.fields(OmniVoiceGenerationConfig)}
except Exception:  # noqa: BLE001
    _GEN_FIELDS = {
        "num_step",
        "guidance_scale",
        "denoise",
        "preprocess_prompt",
        "postprocess_output",
    }


def _safe_str(value: Any, default: str = "") -> str:
    try:
        if value is None:
            return default
        return str(value)
    except Exception:  # noqa: BLE001
        return default


def _resolve_language(language: str | None) -> str | None:
    if not language or language == "Auto":
        return None
    return language


def _to_gradio_audio(audio_np: np.ndarray) -> str | tuple[int, np.ndarray]:
    try:
        wav = ax.as_float_mono(audio_np)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav", prefix="output_")
        tmp.close()
        res = ax.write_wav(tmp.name, wav, SAMPLE_RATE)
        if res and os.path.exists(res):
            return res
        return SAMPLE_RATE, (wav * 32767.0).astype(np.int16)
    except Exception:
        wav = ax.as_float_mono(audio_np)
        return SAMPLE_RATE, (wav * 32767.0).astype(np.int16)



def _as_float_mono(audio_np: np.ndarray) -> np.ndarray:
    return ax.as_float_mono(audio_np)


def _crossfade_concat(parts: list[np.ndarray], gap_ms: int = SILENCE_GAP_MS) -> np.ndarray:
    clean = [_as_float_mono(p) for p in parts if p is not None and np.asarray(p).size > 0]
    if not clean:
        return np.zeros(1, dtype=np.float32)
    if len(clean) == 1:
        return clean[0]
    gap = max(0, int(SAMPLE_RATE * gap_ms / 1000.0))
    fade = max(0, int(SAMPLE_RATE * CROSSFADE_MS / 1000.0))
    out = clean[0]
    for nxt in clean[1:]:
        if gap > 0:
            out = np.concatenate([out, np.zeros(gap, dtype=np.float32), nxt])
            continue
        if fade <= 0 or out.size < fade or nxt.size < fade:
            out = np.concatenate([out, nxt])
            continue
        fade_out = np.linspace(1.0, 0.0, fade, dtype=np.float32)
        fade_in = np.linspace(0.0, 1.0, fade, dtype=np.float32)
        mixed = out[-fade:] * fade_out + nxt[:fade] * fade_in
        out = np.concatenate([out[:-fade], mixed, nxt[fade:]])
    return out


def _chunk_text(text: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> list[str]:
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    pieces = [p.strip() for p in SENTENCE_SPLIT_RE.split(text) if p and p.strip()] or [text]
    chunks: list[str] = []
    buf = ""
    for piece in pieces:
        if len(piece) > max_chars:
            if buf:
                chunks.append(buf)
                buf = ""
            for i in range(0, len(piece), max_chars):
                chunks.append(piece[i : i + max_chars].strip())
            continue
        candidate = f"{buf} {piece}".strip() if buf else piece
        if len(candidate) <= max_chars:
            buf = candidate
        else:
            if buf:
                chunks.append(buf)
            buf = piece
    if buf:
        chunks.append(buf)
    return [c for c in chunks if c][:MAX_CHUNKS]


def _parse_dialogue(text: str) -> list[tuple[int, str]] | None:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return None
    turns: list[tuple[int, str]] = []
    tagged = 0
    for ln in lines:
        m = SPEAKER_RE.match(ln)
        if m:
            tagged += 1
            label = re.sub(r"\s+", "", m.group(1).lower())
            speaker = 2 if label[-1] == "2" else 1
            turns.append((speaker, m.group(2).strip()))
        else:
            turns.append((turns[-1][0] if turns else 1, ln))
    if tagged == 0:
        return None
    return turns[:MAX_DIALOGUE_TURNS]


def _apply_style(text: str, style: str | None) -> str:
    prefix = STYLE_PRESETS.get(_safe_str(style, "Neutral"), "")
    if not prefix or text.lstrip().startswith("["):
        return text
    return prefix + text


def _load_audio_file(path: str | None) -> np.ndarray | None:
    if not path or not os.path.isfile(path):
        return None
    try:
        import soundfile as sf

        data, sr = sf.read(path, always_2d=False)
        wav = np.asarray(data, dtype=np.float32)
        if wav.ndim > 1:
            wav = wav.mean(axis=-1)
        if int(sr) != SAMPLE_RATE and wav.size > 0:
            try:
                import librosa

                wav = librosa.resample(wav, orig_sr=int(sr), target_sr=SAMPLE_RATE)
            except Exception:  # noqa: BLE001
                duration = wav.size / float(sr)
                new_len = max(1, int(duration * SAMPLE_RATE))
                x_old = np.linspace(0.0, 1.0, num=wav.size, endpoint=False)
                x_new = np.linspace(0.0, 1.0, num=new_len, endpoint=False)
                wav = np.interp(x_new, x_old, wav).astype(np.float32)
        return _as_float_mono(wav)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to load audio: %s", path)
        return None


def _mix_with_bgm(
    voice: np.ndarray,
    bgm_path: str | None,
    bgm_volume: float = 0.18,
    duck_db: float = 8.0,
) -> np.ndarray:
    try:
        voice = _as_float_mono(voice)
        if not bgm_path:
            return voice
        bgm = _load_audio_file(bgm_path)
        if bgm is None or bgm.size == 0:
            return voice
        bgm_volume = float(np.clip(bgm_volume, 0.0, 1.0))
        duck_gain = 10 ** (-float(np.clip(duck_db, 0.0, 24.0)) / 20.0)
        if bgm.size < voice.size:
            bgm = np.tile(bgm, int(np.ceil(voice.size / bgm.size)))[: voice.size]
        else:
            bgm = bgm[: voice.size]
        frame = max(1, int(SAMPLE_RATE * 0.02))
        energy = np.convolve(np.abs(voice), np.ones(frame) / frame, mode="same")
        thresh = max(0.02, float(np.percentile(energy, 55)) * 0.6)
        gain = np.where(energy > thresh, duck_gain, 1.0).astype(np.float32)
        win = max(1, int(SAMPLE_RATE * 0.05))
        gain = np.convolve(gain, np.ones(win) / win, mode="same")
        mixed = voice + bgm * bgm_volume * gain
        peak = float(np.max(np.abs(mixed)))
        if peak > 0.98:
            mixed = mixed * (0.98 / peak)
        return mixed.astype(np.float32)
    except Exception:  # noqa: BLE001
        logger.exception("BGM mix failed; returning dry voice")
        return _as_float_mono(voice)


def _build_gen_config(
    num_step: float,
    guidance_scale: float,
    denoise: bool,
    preprocess_prompt: bool,
    postprocess_output: bool,
    t_shift: float | None = 0.1,
    position_temperature: float | None = 5.0,
    class_temperature: float | None = 0.0,
    pad_duration: float | None = 0.1,
    fade_duration: float | None = 0.1,
    audio_chunk_duration: float | None = 15.0,
    audio_chunk_threshold: float | None = 30.0,
    use_native_longform: bool = False,
) -> OmniVoiceGenerationConfig:
    steps = max(8, min(64, int(num_step or 32)))
    cfg = max(0.5, min(3.5, float(guidance_scale if guidance_scale is not None else 2.0)))
    payload: dict[str, Any] = {
        "num_step": steps,
        "guidance_scale": cfg,
        "denoise": bool(denoise),
        "preprocess_prompt": bool(preprocess_prompt),
        "postprocess_output": bool(postprocess_output),
        "t_shift": float(t_shift if t_shift is not None else 0.1),
        "position_temperature": float(position_temperature if position_temperature is not None else 5.0),
        "class_temperature": float(class_temperature if class_temperature is not None else 0.0),
        "pad_duration": float(pad_duration if pad_duration is not None else 0.1),
        "fade_duration": float(fade_duration if fade_duration is not None else 0.1),
    }
    if use_native_longform:
        payload["audio_chunk_duration"] = float(audio_chunk_duration or 15.0)
        payload["audio_chunk_threshold"] = float(audio_chunk_threshold or 30.0)
    filtered = {k: v for k, v in payload.items() if k in _GEN_FIELDS}
    try:
        return OmniVoiceGenerationConfig(**filtered)
    except Exception:  # noqa: BLE001
        logger.exception("GenConfig advanced fields failed; using minimal config")
        return OmniVoiceGenerationConfig(
            num_step=steps,
            guidance_scale=cfg,
            denoise=bool(denoise),
            preprocess_prompt=bool(preprocess_prompt),
            postprocess_output=bool(postprocess_output),
        )


def _make_prompt(ref_audio: str | None, ref_text: str | None) -> VoiceClonePrompt | None:
    if not ref_audio:
        return None
    try:
        return model.create_voice_clone_prompt(
            ref_audio=ref_audio,
            ref_text=(ref_text.strip() if ref_text and str(ref_text).strip() else None),
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to create voice clone prompt")
        return None


def _generate_one(
    text: str,
    language: str | None,
    gen_config: OmniVoiceGenerationConfig,
    prompt: VoiceClonePrompt | None,
    speed: float,
    duration: float | None,
    instruct: str | None,
    normalize_text: bool,
    blend_instruct: bool = False,
) -> np.ndarray | None:
    text = text.strip()
    if not text:
        return None
    kw: dict[str, Any] = {
        "text": text,
        "language": language,
        "generation_config": gen_config,
    }
    if prompt is not None:
        kw["voice_clone_prompt"] = prompt
        # OmniVoice tip: consistent instruct + ref improves dialect/style stability
        if blend_instruct and instruct and str(instruct).strip():
            kw["instruct"] = str(instruct).strip()
    elif instruct and str(instruct).strip():
        kw["instruct"] = str(instruct).strip()

    if speed is not None and abs(float(speed) - 1.0) > 1e-3:
        kw["speed"] = float(np.clip(speed, 0.7, 1.3))
    if duration is not None and float(duration) > 0:
        kw["duration"] = float(duration)
    if normalize_text:
        kw["normalize_text"] = True

    try:
        audio = model.generate(**kw)
        if not audio:
            return None
        return _as_float_mono(audio[0])
    except TypeError:
        for drop in ("normalize_text", "instruct"):
            kw.pop(drop, None)
            try:
                audio = model.generate(**kw)
                if audio:
                    return _as_float_mono(audio[0])
            except Exception:  # noqa: BLE001
                continue
        logger.exception("Generation failed for chunk")
        return None
    except Exception:  # noqa: BLE001
        logger.exception("Generation failed for chunk")
        return None


def _export_wav(wav: np.ndarray) -> str | None:
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav", prefix="clone_")
        tmp.close()
        return ax.write_wav(tmp.name, wav, SAMPLE_RATE)
    except Exception:  # noqa: BLE001
        return None


def _finalize(
    parts: list[np.ndarray],
    bgm_audio,
    bgm_volume,
    duck_db,
    ref_for_polish: np.ndarray | None,
    f0_semitones,
    index_rate,
    protect,
    loud_norm,
    enable_polish: bool,
) -> tuple[np.ndarray, str, str | None]:
    voice = _crossfade_concat(parts)
    polish_note = "Polish: off"
    if enable_polish:
        voice, polish_note = ax.apply_rvc_inspired_polish(
            voice,
            ref_for_polish,
            SAMPLE_RATE,
            f0_semitones=float(f0_semitones or 0),
            index_rate=float(index_rate or 0),
            protect=float(protect or 0),
            loud_norm=bool(loud_norm),
        )
    voice = _mix_with_bgm(voice, bgm_audio, float(bgm_volume or 0.18), float(duck_db or 8))
    return voice, polish_note, _export_wav(voice)


def _estimate_gpu_seconds(
    text,
    language,
    ref_audio,
    ref_text,
    num_step,
    guidance_scale,
    denoise,
    speed,
    duration,
    preprocess_prompt,
    postprocess_output,
    style,
    long_form,
    mode,
    ref_audio_2,
    ref_text_2,
    instruct,
    normalize_text,
    bgm_audio,
    bgm_volume,
    duck_db,
    *args,
    **kwargs,
) -> int:
    try:
        raw = _safe_str(text)
        n_chars = min(len(raw), MAX_TOTAL_CHARS)
        dialogue = _parse_dialogue(raw) if mode == "Multi-speaker dialogue" else None
        if dialogue:
            n_chunks = min(len(dialogue), MAX_DIALOGUE_TURNS)
        elif long_form or n_chars > 1200:
            n_chunks = max(1, min(MAX_CHUNKS, (n_chars // MAX_CHARS_PER_CHUNK) + 1))
        else:
            n_chunks = 1
        steps = int(num_step or 32)
        per = 8 + int(steps * 0.35)
        # Pitch/timbre polish is CPU — small buffer only
        total = 30 + n_chunks * per
        return int(min(280, max(45, total)))
    except Exception:  # noqa: BLE001
        return 120


# ---------------------------------------------------------------------------
# Voice library
# ---------------------------------------------------------------------------
def save_voice_profile(name, ref_audio, ref_text, library):
    library = dict(library or {})
    name = _safe_str(name).strip()
    if not name:
        return library, gr.update(), "Enter a profile name."
    if not ref_audio:
        return library, gr.update(), "Upload reference audio before saving a profile."
    if len(library) >= 12:
        return library, gr.update(choices=list(library.keys())), "Library full (max 12)."
    prompt = _make_prompt(ref_audio, ref_text)
    if prompt is None:
        return library, gr.update(choices=list(library.keys())), "Could not encode reference."
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pt", prefix=f"voice_{name}_")
        tmp.close()
        prompt.save(tmp.name)
        library[name] = {"path": tmp.name, "ref_text": _safe_str(ref_text).strip(), "ref_audio": ref_audio}
        return library, gr.update(choices=list(library.keys()), value=name), f"Saved “{name}”."
    except Exception as exc:  # noqa: BLE001
        return library, gr.update(choices=list(library.keys())), f"Save failed: {exc}"


def load_voice_profile(name, library):
    library = library or {}
    name = _safe_str(name).strip()
    if not name or name not in library:
        return None, "", None, "Select a saved profile."
    entry = library[name]
    path = entry.get("path")
    return entry.get("ref_audio"), entry.get("ref_text", ""), (path if path and os.path.isfile(path) else None), f"Loaded “{name}”."


def import_voice_pt(pt_file, name, library):
    library = dict(library or {})
    name = _safe_str(name).strip() or "Imported"
    if not pt_file or not os.path.isfile(pt_file):
        return library, gr.update(), "Upload a .pt voice prompt file."
    try:
        _ = VoiceClonePrompt.load(pt_file)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pt", prefix=f"voice_{name}_")
        tmp.close()
        with open(pt_file, "rb") as src, open(tmp.name, "wb") as dst:
            dst.write(src.read())
        library[name] = {"path": tmp.name, "ref_text": "", "ref_audio": None}
        return library, gr.update(choices=list(library.keys()), value=name), f"Imported “{name}”."
    except Exception as exc:  # noqa: BLE001
        return library, gr.update(choices=list(library.keys())), f"Import failed: {exc}"


def delete_voice_profile(name, library):
    library = dict(library or {})
    name = _safe_str(name).strip()
    if name in library:
        try:
            path = library[name].get("path")
            if path and os.path.isfile(path):
                os.remove(path)
        except Exception:  # noqa: BLE001
            pass
        del library[name]
        return library, gr.update(choices=list(library.keys()), value=None), f"Deleted “{name}”."
    return library, gr.update(choices=list(library.keys())), "Nothing to delete."


def _prompt_from_library_or_audio(profile_name, library, ref_audio, ref_text):
    library = library or {}
    name = _safe_str(profile_name).strip()
    if name and name in library:
        path = library[name].get("path")
        if path and os.path.isfile(path):
            try:
                return VoiceClonePrompt.load(path), f"Using saved profile “{name}”.", library[name].get("ref_audio")
            except Exception:  # noqa: BLE001
                logger.exception("Failed loading profile %s", name)
    if ref_audio:
        prompt = _make_prompt(ref_audio, ref_text)
        if prompt is not None:
            return prompt, "Using uploaded reference audio.", ref_audio
        return None, "Could not encode reference audio.", None
    return None, "No reference voice provided.", None


def apply_quality_preset(preset: str):
    cfg = ax.QUALITY_PRESETS.get(preset, ax.QUALITY_PRESETS["Balanced"])
    return cfg["num_step"], cfg["guidance_scale"], cfg["t_shift"]


def analyze_ref_ui(ref_audio):
    return ax.analyze_reference(ref_audio, SAMPLE_RATE)


def apply_try_prompt(prompt_name: str):
    """Fill text / language / mode / style / instruct from a curated try prompt."""
    entry = TRY_PROMPTS.get(_safe_str(prompt_name))
    if not entry:
        return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), "Pick a try prompt."
    return (
        entry["text"],
        entry.get("language", "Auto"),
        entry.get("mode", "Voice clone"),
        entry.get("style", "Neutral"),
        entry.get("instruct", ""),
        f"Loaded “{prompt_name}”. Upload/record your voice → enable consent → Generate.",
    )


# ---------------------------------------------------------------------------
# Core generation
# ---------------------------------------------------------------------------
@spaces.GPU(duration=_estimate_gpu_seconds)
def clone_voice(
    text,
    language,
    ref_audio,
    ref_text,
    num_step,
    guidance_scale,
    denoise,
    speed,
    duration,
    preprocess_prompt,
    postprocess_output,
    style,
    long_form,
    mode,
    ref_audio_2,
    ref_text_2,
    instruct,
    normalize_text,
    bgm_audio,
    bgm_volume,
    duck_db,
    profile_name,
    library,
    consent,
    ref_prep,
    blend_instruct,
    use_native_longform,
    t_shift,
    position_temperature,
    class_temperature,
    pad_duration,
    fade_duration,
    audio_chunk_duration,
    audio_chunk_threshold,
    enable_polish,
    f0_semitones,
    index_rate,
    protect,
    loud_norm,
    progress=gr.Progress(track_tqdm=False),
):
    try:
        yield from _clone_voice_impl(
            text, language, ref_audio, ref_text, num_step, guidance_scale, denoise,
            speed, duration, preprocess_prompt, postprocess_output, style, long_form,
            mode, ref_audio_2, ref_text_2, instruct, normalize_text, bgm_audio,
            bgm_volume, duck_db, profile_name, library, consent, ref_prep,
            blend_instruct, use_native_longform, t_shift, position_temperature,
            class_temperature, pad_duration, fade_duration, audio_chunk_duration,
            audio_chunk_threshold, enable_polish, f0_semitones, index_rate,
            protect, loud_norm, progress,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Unhandled clone_voice error:\n%s", traceback.format_exc())
        yield None, f"Unexpected error (recovered): {type(exc).__name__}: {exc}", None


def _clone_voice_impl(
    text, language, ref_audio, ref_text, num_step, guidance_scale, denoise,
    speed, duration, preprocess_prompt, postprocess_output, style, long_form,
    mode, ref_audio_2, ref_text_2, instruct, normalize_text, bgm_audio,
    bgm_volume, duck_db, profile_name, library, consent, ref_prep,
    blend_instruct, use_native_longform, t_shift, position_temperature,
    class_temperature, pad_duration, fade_duration, audio_chunk_duration,
    audio_chunk_threshold, enable_polish, f0_semitones, index_rate,
    protect, loud_norm, progress,
):
    if not consent:
        yield None, "Please confirm you have rights/consent to clone this voice.", None
        return

    raw = _safe_str(text).strip()
    if not raw:
        yield None, "Enter text to speak in any of 600+ supported languages.", None
        return
    if len(raw) > MAX_TOTAL_CHARS:
        yield None, f"Text too long. Keep under {MAX_TOTAL_CHARS} characters.", None
        return

    mode = _safe_str(mode, "Voice clone")
    lang = _resolve_language(language)
    gen_config = _build_gen_config(
        num_step, guidance_scale, denoise, preprocess_prompt, postprocess_output,
        t_shift, position_temperature, class_temperature, pad_duration, fade_duration,
        audio_chunk_duration, audio_chunk_threshold, bool(use_native_longform),
    )
    speed_f = float(speed) if speed is not None else 1.0
    dur_f = float(duration) if duration is not None and float(duration or 0) > 0 else None
    use_duration = dur_f if (not long_form and mode != "Multi-speaker dialogue") else None
    blend = bool(blend_instruct)
    polish_on = bool(enable_polish)

    # Optional reference preparation (RVC/OmniVoice quality tip: clean short ref)
    prep_notes = []
    if bool(ref_prep) and ref_audio:
        ref_audio, note = ax.prepare_reference(ref_audio, SAMPLE_RATE, enable=True, gate=True)
        prep_notes.append(note)
    if bool(ref_prep) and ref_audio_2:
        ref_audio_2, note2 = ax.prepare_reference(ref_audio_2, SAMPLE_RATE, enable=True, gate=True)
        prep_notes.append("S2: " + note2)

    def _done(parts, ref_path, msg):
        ref_wav = _load_audio_file(ref_path) if ref_path else None
        final, polish_note, wav_path = _finalize(
            parts, bgm_audio, bgm_volume, duck_db, ref_wav,
            f0_semitones, index_rate, protect, loud_norm, polish_on,
        )
        extra = " · ".join([x for x in prep_notes + [polish_note] if x])
        if bgm_audio:
            msg += " · BGM ducked"
        if extra:
            msg += f" · {extra}"
        yield _to_gradio_audio(final), msg, wav_path

    # -------- Voice design --------
    if mode == "Voice design (no reference)":
        instr = _safe_str(instruct).strip()
        if not instr:
            yield None, "Voice design needs instruct, e.g. “female, low pitch, british accent”.", None
            return
        styled = _apply_style(raw, style)
        # Prefer native OmniVoice chunking when enabled; else our splitter
        if use_native_longform and not long_form:
            chunks = [styled]
        else:
            chunks = _chunk_text(styled) if (long_form or len(styled) > 1200) else [styled]
        yield None, f"Voice design · {len(chunks)} chunk(s)…", None
        parts: list[np.ndarray] = []
        for i, chunk in enumerate(chunks):
            progress((i + 1) / len(chunks), desc=f"Design {i + 1}/{len(chunks)}")
            wav = _generate_one(
                chunk, lang, gen_config, None, speed_f,
                use_duration if len(chunks) == 1 else None, instr, bool(normalize_text), False,
            )
            if wav is None:
                if parts:
                    yield from _done(parts, None, f"Stopped at chunk {i + 1} (partial kept).")
                else:
                    yield None, f"Failed at chunk {i + 1}.", None
                return
            parts.append(wav)
            yield _to_gradio_audio(_crossfade_concat(parts)), f"Chunk {i + 1}/{len(chunks)}…", None
        yield from _done(parts, None, "Done — voice design ready.")
        return

    if mode == "Auto voice (random)":
        styled = _apply_style(raw, style)
        chunks = [styled] if (use_native_longform and not long_form) else (
            _chunk_text(styled) if (long_form or len(styled) > 1200) else [styled]
        )
        yield None, f"Auto voice · {len(chunks)} chunk(s)…", None
        parts = []
        for i, chunk in enumerate(chunks):
            progress((i + 1) / len(chunks), desc=f"Auto {i + 1}/{len(chunks)}")
            wav = _generate_one(
                chunk, lang, gen_config, None, speed_f,
                use_duration if len(chunks) == 1 else None, None, bool(normalize_text), False,
            )
            if wav is None:
                if parts:
                    yield from _done(parts, None, f"Stopped at chunk {i + 1} (partial kept).")
                else:
                    yield None, f"Failed at chunk {i + 1}.", None
                return
            parts.append(wav)
            yield _to_gradio_audio(_crossfade_concat(parts)), f"Chunk {i + 1}/{len(chunks)}…", None
        yield from _done(parts, None, "Done — auto voice ready.")
        return

    # -------- Multi-speaker --------
    if mode == "Multi-speaker dialogue":
        turns = _parse_dialogue(raw)
        if not turns:
            yield None, "Use lines like:\n[Speaker 1]: Hello!\n[Speaker 2]: Hi!", None
            return
        if not ref_audio and not (profile_name and library and _safe_str(profile_name) in (library or {})):
            yield None, "Speaker 1 needs a reference clip (or saved profile).", None
            return
        if not ref_audio_2:
            yield None, "Speaker 2 needs a second reference clip.", None
            return
        p1, note1, ref1_path = _prompt_from_library_or_audio(profile_name, library, ref_audio, ref_text)
        p2 = _make_prompt(ref_audio_2, ref_text_2)
        if p1 is None or p2 is None:
            yield None, f"Could not encode speaker prompts. {note1}", None
            return
        yield None, f"Dialogue · {len(turns)} turns. {note1}", None
        parts = []
        for i, (spk, line) in enumerate(turns):
            progress((i + 1) / len(turns), desc=f"Turn {i + 1}/{len(turns)}")
            prompt = p1 if spk == 1 else p2
            wav = _generate_one(
                _apply_style(line, style), lang, gen_config, prompt, speed_f, None,
                instruct if blend else None, bool(normalize_text), blend,
            )
            if wav is None:
                if parts:
                    yield from _done(parts, ref1_path, f"Stopped at turn {i + 1} (partial kept).")
                else:
                    yield None, f"Failed at turn {i + 1}.", None
                return
            parts.append(wav)
            yield _to_gradio_audio(_crossfade_concat(parts)), f"Turn {i + 1}/{len(turns)}…", None
        yield from _done(parts, ref1_path, "Done — multi-speaker dialogue ready.")
        return

    # -------- Standard / long-form clone --------
    prompt, note, ref_path = _prompt_from_library_or_audio(profile_name, library, ref_audio, ref_text)
    if prompt is None:
        yield None, note or "Upload a clear 3–10 second reference voice clip.", None
        return

    styled = _apply_style(raw, style)
    do_long = bool(long_form) or (len(styled) > 1200 and not use_native_longform)
    if len(styled) > 1200 and not do_long and not use_native_longform:
        yield None, "Text over ~1200 chars — enable Long-form or Native OmniVoice chunking.", None
        return

    if use_native_longform and not do_long:
        chunks = [styled]  # let OmniVoice split internally
    else:
        chunks = _chunk_text(styled) if do_long else [styled]
    if not chunks:
        yield None, "Nothing to speak after preprocessing.", None
        return

    yield None, f"{note} Generating {len(chunks)} chunk(s)…", None
    parts = []
    for i, chunk in enumerate(chunks):
        progress((i + 1) / len(chunks), desc=f"Chunk {i + 1}/{len(chunks)}")
        wav = _generate_one(
            chunk, lang, gen_config, prompt, speed_f,
            use_duration if len(chunks) == 1 else None,
            instruct if blend else None, bool(normalize_text), blend,
        )
        if wav is None:
            if parts:
                yield from _done(parts, ref_path, f"Stopped at chunk {i + 1} (partial kept).")
            else:
                yield None, f"Failed at chunk {i + 1}.", None
            return
        parts.append(wav)
        yield _to_gradio_audio(_crossfade_concat(parts)), f"Chunk {i + 1}/{len(chunks)}…", None

    msg = "Done — cloned speech ready."
    if len(chunks) > 1:
        msg = f"Done — long-form clone ({len(chunks)} chunks)."
    yield from _done(parts, ref_path, msg)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
.gradio-container {max-width: 1200px !important;}
#clone-btn {font-weight: 600;}
"""

with gr.Blocks(
    title="AI Voice Cloner — Free Zero-Shot TTS (600+ Languages) | OmniVoice",
    theme=gr.themes.Base(
        primary_hue="green",
        secondary_hue="indigo",
        neutral_hue="slate",
        font=[gr.themes.GoogleFont("DM Sans"), "system-ui", "sans-serif"],
    ),
    css=CUSTOM_CSS,
) as demo:
    voice_library = gr.State({})

    gr.Markdown(
        """
# AI Voice Cloner — Free Zero-Shot TTS (600+ Languages)
**Free online AI voice cloning** & **multilingual text-to-speech**. Upload **3–10 seconds** of audio → generate natural speech in **600+ languages**.

Zero-shot **voice clone** · cross-lingual TTS · long-form · multi-speaker · RVC-inspired polish · one-click **try prompts**.

Powered by [`k2-fsa/OmniVoice`](https://huggingface.co/k2-fsa/OmniVoice) on **ZeroGPU** · Weights **CC-BY-NC** · ⭐ **Like this Space** to boost discovery
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            consent = gr.Checkbox(
                value=False,
                label="I have rights / consent to use this voice (required)",
            )
            mode = gr.Radio(
                label="Mode",
                choices=[
                    "Voice clone",
                    "Multi-speaker dialogue",
                    "Voice design (no reference)",
                    "Auto voice (random)",
                ],
                value="Voice clone",
            )
            quality_preset = gr.Radio(
                label="Quality preset",
                choices=list(ax.QUALITY_PRESETS.keys()),
                value="Balanced",
            )
            ref_audio = gr.Audio(
                label="Reference voice — Speaker 1 (3–10 seconds) · upload or mic",
                type="filepath",
                sources=["upload", "microphone"],
            )
            with gr.Row():
                analyze_btn = gr.Button("Analyze reference", size="sm")
                ref_prep = gr.Checkbox(
                    value=True,
                    label="Auto-prep ref (best 3–10s + soft gate)",
                    info="Clean short refs beat long noisy ones",
                )
            ref_analysis = gr.Textbox(label="Reference QC", lines=2)
            ref_text = gr.Textbox(
                label="Reference transcript (optional)",
                lines=2,
                placeholder="Exact words in the reference clip. Empty = auto-transcribe.",
            )
            with gr.Accordion("Speaker 2 (dialogue mode)", open=False):
                ref_audio_2 = gr.Audio(
                    label="Reference voice — Speaker 2",
                    type="filepath",
                    sources=["upload", "microphone"],
                )
                ref_text_2 = gr.Textbox(label="Speaker 2 transcript (optional)", lines=2)

            with gr.Accordion("Try prompts — click to fill (upload voice first)", open=True):
                gr.Markdown(
                    "1) Upload / record your voice · 2) Click a prompt · 3) Consent · 4) **Generate**"
                )
                try_prompt = gr.Radio(
                    label="Prompt pack",
                    choices=list(TRY_PROMPTS.keys()),
                    value="YouTube intro",
                )
                load_prompt_btn = gr.Button("Load selected prompt into text box", variant="secondary")
                prompt_status = gr.Textbox(label="Prompt status", lines=1)

            text = gr.Textbox(
                label="Text to speak (any of 600+ languages)",
                lines=6,
                placeholder=(
                    "Paste your script — or click a Try prompt above.\n\n"
                    "[Speaker 1]: Hello!\n[Speaker 2]: Hi there!\n\n"
                    f"{NONVERBAL_HELP}"
                ),
            )
            language = gr.Dropdown(
                label="Language (Auto or pick from 600+)",
                choices=LANGUAGE_CHOICES,
                value="Auto",
                filterable=True,
            )
            style = gr.Dropdown(
                label="Expression preset",
                choices=list(STYLE_PRESETS.keys()),
                value="Neutral",
            )
            instruct = gr.Textbox(
                label="Instruct (voice design · optional clone blend)",
                lines=1,
                placeholder="female, low pitch, british accent  |  四川话",
                info="Required in Voice design mode. For clone: enable blend when consistent with ref.",
            )
            blend_instruct = gr.Checkbox(
                value=False,
                label="Blend instruct with clone (OmniVoice dialect/style tip)",
            )
            long_form = gr.Checkbox(
                value=False,
                label="Long-form (app chunker)",
                info=f"Up to {MAX_TOTAL_CHARS} chars / {MAX_CHUNKS} chunks",
            )
            use_native_longform = gr.Checkbox(
                value=False,
                label="Native OmniVoice long-form chunking",
                info="Uses audio_chunk_duration / threshold inside the model",
            )
            normalize_text = gr.Checkbox(value=False, label="Normalize numbers → words (EN/ZH)")

            with gr.Accordion("RVC-inspired polish (crash-safe DSP · no .pth)", open=False):
                gr.Markdown(
                    "Concepts from [Annotated RVC](https://gudgud96.github.io/2024/09/26/annotated-rvc/) "
                    "— lightweight spectral polish only (ZeroGPU-safe)."
                )
                enable_polish = gr.Checkbox(value=True, label="Enable polish chain")
                f0_semitones = gr.Slider(
                    -12, 12, value=0, step=1,
                    label="F0 shift (semitones) ≈ RVC f0_up_key",
                )
                index_rate = gr.Slider(
                    0.0, 0.8, value=0.35, step=0.05,
                    label="Timbre blend α ≈ RVC index_rate",
                )
                protect = gr.Slider(
                    0.0, 0.5, value=0.33, step=0.01,
                    label="Protect consonants ≈ RVC protect",
                )
                loud_norm = gr.Checkbox(value=True, label="Loudness normalize output")

            with gr.Accordion("Voice library (session + .pt)", open=False):
                profile_name = gr.Textbox(label="Profile name", placeholder="Narrator_A")
                profile_select = gr.Dropdown(label="Saved profiles", choices=[], value=None)
                with gr.Row():
                    save_profile_btn = gr.Button("Save", size="sm")
                    load_profile_btn = gr.Button("Load", size="sm")
                    delete_profile_btn = gr.Button("Delete", size="sm")
                import_pt = gr.File(label="Import .pt", file_types=[".pt"], type="filepath")
                import_btn = gr.Button("Import .pt", size="sm")
                profile_download = gr.File(label="Download profile (.pt)")
                library_status = gr.Textbox(label="Library status", lines=1)

            with gr.Accordion("Background music", open=False):
                bgm_audio = gr.Audio(label="Backing track", type="filepath", sources=["upload"])
                bgm_volume = gr.Slider(0.0, 0.6, value=0.18, step=0.02, label="BGM volume")
                duck_db = gr.Slider(0.0, 18.0, value=8.0, step=0.5, label="Duck (dB)")

            with gr.Accordion("Advanced OmniVoice decoding", open=False):
                speed = gr.Slider(0.7, 1.3, value=1.0, step=0.05, label="Speed")
                duration = gr.Number(value=None, label="Force duration (s, single-chunk)")
                num_step = gr.Slider(8, 64, value=32, step=1, label="Inference steps")
                guidance_scale = gr.Slider(0.5, 3.5, value=2.0, step=0.1, label="CFG guidance")
                t_shift = gr.Slider(0.01, 0.5, value=0.1, step=0.01, label="t_shift (noise schedule)")
                position_temperature = gr.Slider(0.0, 10.0, value=5.0, step=0.5, label="position_temperature")
                class_temperature = gr.Slider(0.0, 2.0, value=0.0, step=0.1, label="class_temperature")
                pad_duration = gr.Slider(0.0, 0.5, value=0.1, step=0.05, label="pad_duration (s)")
                fade_duration = gr.Slider(0.0, 0.5, value=0.1, step=0.05, label="fade_duration (s)")
                audio_chunk_duration = gr.Slider(5.0, 30.0, value=15.0, step=1.0, label="audio_chunk_duration")
                audio_chunk_threshold = gr.Slider(10.0, 60.0, value=30.0, step=1.0, label="audio_chunk_threshold")
                denoise = gr.Checkbox(value=True, label="Denoise output")
                preprocess_prompt = gr.Checkbox(value=True, label="Clean reference (model-side)")
                postprocess_output = gr.Checkbox(value=True, label="Trim output silences")

            generate_btn = gr.Button(
                "Generate cloned voice",
                variant="primary",
                elem_id="clone-btn",
            )

        with gr.Column(scale=1):
            output_audio = gr.Audio(
                label="Cloned speech output (streams per chunk · downloadable)",
                type="numpy",
            )
            output_file = gr.File(label="Download WAV")
            status = gr.Textbox(label="Status", lines=4)
            gr.Markdown(
                """
### Quick path to a viral demo
1. Upload a clean **6s** clip of *your* voice  
2. Load **YouTube intro** or **Audiobook narrator**  
3. Enable consent → **Generate** → share the WAV  

### SEO / product keywords this Space targets
`AI voice clone` · `free voice cloning` · `zero-shot TTS` · `multilingual text to speech` · `OmniVoice` · `clone voice from audio` · `AI voice generator` · `audiobook TTS` · `YouTube voiceover AI`
                """
            )

    quality_preset.change(
        fn=apply_quality_preset,
        inputs=[quality_preset],
        outputs=[num_step, guidance_scale, t_shift],
    )
    analyze_btn.click(fn=analyze_ref_ui, inputs=[ref_audio], outputs=[ref_analysis])
    load_prompt_btn.click(
        fn=apply_try_prompt,
        inputs=[try_prompt],
        outputs=[text, language, mode, style, instruct, prompt_status],
        api_name="load_try_prompt",
    )
    # Also load when user changes the radio (faster UX)
    try_prompt.change(
        fn=apply_try_prompt,
        inputs=[try_prompt],
        outputs=[text, language, mode, style, instruct, prompt_status],
    )

    gen_inputs = [
        text, language, ref_audio, ref_text, num_step, guidance_scale, denoise,
        speed, duration, preprocess_prompt, postprocess_output, style, long_form,
        mode, ref_audio_2, ref_text_2, instruct, normalize_text, bgm_audio,
        bgm_volume, duck_db, profile_select, voice_library, consent, ref_prep,
        blend_instruct, use_native_longform, t_shift, position_temperature,
        class_temperature, pad_duration, fade_duration, audio_chunk_duration,
        audio_chunk_threshold, enable_polish, f0_semitones, index_rate,
        protect, loud_norm,
    ]

    generate_btn.click(
        fn=clone_voice,
        inputs=gen_inputs,
        outputs=[output_audio, status, output_file],
        api_name="clone_voice",
    )
    save_profile_btn.click(
        fn=save_voice_profile,
        inputs=[profile_name, ref_audio, ref_text, voice_library],
        outputs=[voice_library, profile_select, library_status],
        api_name="save_voice_profile",
    )
    load_profile_btn.click(
        fn=load_voice_profile,
        inputs=[profile_select, voice_library],
        outputs=[ref_audio, ref_text, profile_download, library_status],
        api_name="load_voice_profile",
    )
    delete_profile_btn.click(
        fn=delete_voice_profile,
        inputs=[profile_select, voice_library],
        outputs=[voice_library, profile_select, library_status],
        api_name="delete_voice_profile",
    )
    import_btn.click(
        fn=import_voice_pt,
        inputs=[import_pt, profile_name, voice_library],
        outputs=[voice_library, profile_select, library_status],
        api_name="import_voice_pt",
    )

    demo.load(
        fn=lambda: apply_try_prompt("YouTube intro"),
        outputs=[text, language, mode, style, instruct, prompt_status],
    )

    gr.Markdown(
        """
### About — free AI voice cloner on Hugging Face
[`cosmichackerx/voice-cloner`](https://huggingface.co/spaces/cosmichackerx/voice-cloner) ·
Model [`OmniVoice`](https://huggingface.co/k2-fsa/OmniVoice) ·
RVC notes [gudgud96](https://gudgud96.github.io/2024/09/26/annotated-rvc/) ·
API `/clone_voice`

**Only clone voices you have consent to use.** ⭐ Like · share · duplicate to help this Space trend.
        """
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1).launch()
