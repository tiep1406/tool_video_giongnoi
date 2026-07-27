"""
Crash-safe, CPU-only audio polish inspired by RVC inference knobs.

References (concepts only — no neural RVC stack loaded):
- Annotated RVC: F0 shift, index_rate fusion, protect-style consonant care
  https://gudgud96.github.io/2024/09/26/annotated-rvc/
- RVC WebUI params: f0_up_key, index_rate (~0.3–0.8), protect (~0.33)

All functions swallow errors and return the input (or a safe fallback).
No HuBERT / RMVPE / faiss / .pth models — ZeroGPU-safe beside OmniVoice.
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

import numpy as np

logger = logging.getLogger("voice-cloner.enhance")


def as_float_mono(audio_np: np.ndarray | None) -> np.ndarray:
    if audio_np is None:
        return np.zeros(1, dtype=np.float32)
    wav = np.asarray(audio_np, dtype=np.float32).reshape(-1)
    if wav.size == 0:
        return np.zeros(1, dtype=np.float32)
    peak = float(np.max(np.abs(wav)))
    if peak > 1.05:
        wav = wav / peak
    return np.clip(wav, -1.0, 1.0).astype(np.float32)


def peak_normalize(wav: np.ndarray, peak: float = 0.95) -> np.ndarray:
    try:
        wav = as_float_mono(wav)
        p = float(np.max(np.abs(wav)))
        if p < 1e-8:
            return wav
        return (wav * (peak / p)).astype(np.float32)
    except Exception:  # noqa: BLE001
        return as_float_mono(wav)


def soft_noise_gate(wav: np.ndarray, sr: int, floor_db: float = -42.0) -> np.ndarray:
    """Simple energy gate — Demucs-free reference cleanup."""
    try:
        wav = as_float_mono(wav)
        if wav.size < sr // 10:
            return wav
        frame = max(1, int(sr * 0.02))
        energy = np.convolve(np.abs(wav), np.ones(frame) / frame, mode="same")
        # Adaptive threshold from quietest 20%
        quiet = float(np.percentile(energy, 20))
        thresh = max(quiet * 3.0, 10 ** (floor_db / 20.0))
        gain = np.clip((energy - thresh * 0.5) / max(thresh, 1e-6), 0.0, 1.0)
        win = max(1, int(sr * 0.05))
        gain = np.convolve(gain, np.ones(win) / win, mode="same")
        return (wav * gain.astype(np.float32)).astype(np.float32)
    except Exception:  # noqa: BLE001
        logger.exception("soft_noise_gate failed")
        return as_float_mono(wav)


def best_speech_window(
    wav: np.ndarray,
    sr: int,
    target_sec: float = 6.0,
    min_sec: float = 3.0,
    max_sec: float = 10.0,
) -> np.ndarray:
    """
    Pick the densest speech window (3–10s) — RVC / OmniVoice quality tip:
    short clean refs beat long noisy ones.
    """
    try:
        wav = as_float_mono(wav)
        n = wav.size
        dur = n / float(sr)
        if dur <= max_sec:
            return wav
        target = int(np.clip(target_sec, min_sec, max_sec) * sr)
        target = min(target, n)
        frame = max(1, int(sr * 0.05))
        energy = np.convolve(np.abs(wav), np.ones(frame) / frame, mode="same")
        # Integral image for fast window sums
        csum = np.cumsum(energy, dtype=np.float64)
        best_i, best_s = 0, -1.0
        step = max(1, frame)
        for i in range(0, n - target + 1, step):
            s = float(csum[i + target - 1] - (csum[i - 1] if i > 0 else 0.0))
            if s > best_s:
                best_s, best_i = s, i
        return wav[best_i : best_i + target].astype(np.float32)
    except Exception:  # noqa: BLE001
        logger.exception("best_speech_window failed")
        return as_float_mono(wav)


def prepare_reference(
    path: str | None,
    sr: int,
    enable: bool = True,
    gate: bool = True,
) -> tuple[str | None, str]:
    """
    Load → best window → optional gate → peak norm → write temp wav.
    Returns (path_or_original, status_note). Never raises.
    """
    if not path or not os.path.isfile(path):
        return path, "No reference file."
    if not enable:
        return path, "Reference prep skipped."
    try:
        import soundfile as sf

        data, file_sr = sf.read(path, always_2d=False)
        wav = np.asarray(data, dtype=np.float32)
        if wav.ndim > 1:
            wav = wav.mean(axis=-1)
        file_sr = int(file_sr)
        if file_sr != sr and wav.size > 0:
            try:
                import librosa

                wav = librosa.resample(wav, orig_sr=file_sr, target_sr=sr)
            except Exception:  # noqa: BLE001
                duration = wav.size / float(file_sr)
                new_len = max(1, int(duration * sr))
                x_old = np.linspace(0.0, 1.0, num=wav.size, endpoint=False)
                x_new = np.linspace(0.0, 1.0, num=new_len, endpoint=False)
                wav = np.interp(x_new, x_old, wav).astype(np.float32)
        before = wav.size / float(sr)
        wav = best_speech_window(wav, sr)
        if gate:
            wav = soft_noise_gate(wav, sr)
        wav = peak_normalize(wav, 0.95)
        after = wav.size / float(sr)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav", prefix="ref_prep_")
        tmp.close()
        sf.write(tmp.name, wav, sr)
        note = f"Ref prepped: {before:.1f}s → {after:.1f}s clean window."
        return tmp.name, note
    except Exception:  # noqa: BLE001
        logger.exception("prepare_reference failed; using original")
        return path, "Reference prep failed — using original clip."


def estimate_f0_hz(wav: np.ndarray, sr: int) -> float | None:
    """Lightweight median F0 estimate (librosa.pyin → autocorrelation fallback)."""
    try:
        wav = as_float_mono(wav)
        if wav.size < sr // 2:
            return None
        try:
            import librosa

            f0, _, _ = librosa.pyin(
                wav,
                fmin=librosa.note_to_hz("C2"),
                fmax=librosa.note_to_hz("C7"),
                sr=sr,
            )
            vals = f0[~np.isnan(f0)] if f0 is not None else np.array([])
            if vals.size > 0:
                return float(np.median(vals))
        except Exception:  # noqa: BLE001
            pass
        # Autocorrelation fallback on a mid segment
        seg = wav[len(wav) // 4 : 3 * len(wav) // 4]
        if seg.size < 1024:
            seg = wav
        seg = seg - float(np.mean(seg))
        corr = np.correlate(seg, seg, mode="full")
        corr = corr[corr.size // 2 :]
        min_lag = int(sr / 400)  # 400 Hz
        max_lag = int(sr / 60)  # 60 Hz
        if max_lag <= min_lag or max_lag >= corr.size:
            return None
        lag = int(np.argmax(corr[min_lag:max_lag]) + min_lag)
        if lag <= 0:
            return None
        return float(sr / lag)
    except Exception:  # noqa: BLE001
        logger.exception("estimate_f0_hz failed")
        return None


def pitch_shift_semitones(wav: np.ndarray, sr: int, semitones: float) -> np.ndarray:
    """RVC-style f0_up_key analogue (librosa; no-op on failure)."""
    try:
        wav = as_float_mono(wav)
        st = float(semitones)
        if abs(st) < 0.05 or wav.size < 64:
            return wav
        st = float(np.clip(st, -12.0, 12.0))
        try:
            import librosa

            out = librosa.effects.pitch_shift(wav, sr=sr, n_steps=st)
            return as_float_mono(out)
        except Exception:  # noqa: BLE001
            # Crude resample pitch shift (duration changes — stretch back)
            factor = 2 ** (st / 12.0)
            new_len = max(1, int(wav.size / factor))
            x_old = np.linspace(0.0, 1.0, num=wav.size, endpoint=False)
            x_new = np.linspace(0.0, 1.0, num=new_len, endpoint=False)
            shifted = np.interp(x_new, x_old, wav).astype(np.float32)
            # Time-stretch back to original length
            x_s = np.linspace(0.0, 1.0, num=shifted.size, endpoint=False)
            x_t = np.linspace(0.0, 1.0, num=wav.size, endpoint=False)
            return np.interp(x_t, x_s, shifted).astype(np.float32)
    except Exception:  # noqa: BLE001
        logger.exception("pitch_shift_semitones failed")
        return as_float_mono(wav)


def _spectral_envelope(mag: np.ndarray, smooth: int = 32) -> np.ndarray:
    env = np.maximum(mag, 1e-8)
    # Log-domain moving average
    log_env = np.log(env)
    k = max(3, smooth | 1)
    kernel = np.ones(k, dtype=np.float64) / k
    if log_env.ndim == 1:
        sm = np.convolve(log_env, kernel, mode="same")
    else:
        sm = np.apply_along_axis(lambda m: np.convolve(m, kernel, mode="same"), 0, log_env)
    return np.exp(sm).astype(np.float32)


def timbre_blend(
    voice: np.ndarray,
    reference: np.ndarray,
    sr: int,
    index_rate: float = 0.35,
) -> np.ndarray:
    """
    Lightweight analogue of RVC index_rate fusion:
    morph voice magnitude envelope toward the reference speaker envelope.
    α=0 → dry TTS; α≈0.3–0.6 → more target timbre (per annotated RVC guidance).
    """
    try:
        voice = as_float_mono(voice)
        reference = as_float_mono(reference)
        alpha = float(np.clip(index_rate, 0.0, 0.85))
        if alpha < 0.02 or voice.size < 512 or reference.size < 512:
            return voice

        n_fft = 1024
        hop = 256
        # STFT via numpy rfft frames (no torch needed)
        def stft(x: np.ndarray) -> np.ndarray:
            # pad
            pad = (hop - (len(x) - n_fft) % hop) % hop
            x = np.pad(x, (0, pad + n_fft))
            frames = []
            window = np.hanning(n_fft).astype(np.float32)
            for i in range(0, len(x) - n_fft + 1, hop):
                frames.append(np.fft.rfft(x[i : i + n_fft] * window))
            return np.stack(frames, axis=1)

        def istft(S: np.ndarray) -> np.ndarray:
            window = np.hanning(n_fft).astype(np.float32)
            n_frames = S.shape[1]
            out_len = n_fft + hop * (n_frames - 1)
            out = np.zeros(out_len, dtype=np.float32)
            win_sum = np.zeros(out_len, dtype=np.float32)
            for i in range(n_frames):
                frame = np.fft.irfft(S[:, i], n=n_fft).astype(np.float32) * window
                start = i * hop
                out[start : start + n_fft] += frame
                win_sum[start : start + n_fft] += window**2
            win_sum = np.maximum(win_sum, 1e-8)
            return out / win_sum

        # Match lengths roughly for envelope stats
        ref = reference
        if ref.size > voice.size * 2:
            ref = best_speech_window(ref, sr, target_sec=min(6.0, voice.size / sr))

        V = stft(voice)
        R = stft(ref)
        V_mag = np.abs(V)
        R_mag = np.abs(R)
        V_env = _spectral_envelope(V_mag.mean(axis=1), smooth=40)
        R_env = _spectral_envelope(R_mag.mean(axis=1), smooth=40)
        # Broadcast envelope ratio
        ratio = (R_env / np.maximum(V_env, 1e-6))[:, None]
        ratio = np.clip(ratio, 0.25, 4.0)
        blended_mag = V_mag * ((1.0 - alpha) + alpha * ratio)
        phase = np.angle(V)
        S = blended_mag * np.exp(1j * phase)
        out = istft(S)[: voice.size]
        return peak_normalize(out, 0.95)
    except Exception:  # noqa: BLE001
        logger.exception("timbre_blend failed")
        return as_float_mono(voice)


def protect_consonants(
    dry: np.ndarray,
    wet: np.ndarray,
    sr: int,
    protect: float = 0.33,
    cutoff_hz: float = 3500.0,
) -> np.ndarray:
    """
    RVC protect analogue: keep more of the dry signal's high band (breath/sibilants)
    so conversion/polish doesn't smear consonants into robotic hum.
    """
    try:
        dry = as_float_mono(dry)
        wet = as_float_mono(wet)
        p = float(np.clip(protect, 0.0, 0.5))
        if p < 0.02:
            return wet
        n = min(dry.size, wet.size)
        dry, wet = dry[:n], wet[:n]
        # One-pole high-shelf blend via spectral split
        # FFT-based crossover
        n_fft = 1 << int(np.ceil(np.log2(max(n, 4))))
        D = np.fft.rfft(dry, n=n_fft)
        W = np.fft.rfft(wet, n=n_fft)
        freqs = np.fft.rfftfreq(n_fft, d=1.0 / sr)
        high = (freqs >= cutoff_hz).astype(np.float32)
        low = 1.0 - high
        # Low from wet, high = mix dry/wet by protect
        mag_mix = W * low + (W * (1.0 - p) + D * p) * high
        out = np.fft.irfft(mag_mix, n=n_fft)[:n].astype(np.float32)
        return peak_normalize(out, 0.95)
    except Exception:  # noqa: BLE001
        logger.exception("protect_consonants failed")
        return as_float_mono(wet)


def loudness_normalize(wav: np.ndarray, target_rms: float = 0.08) -> np.ndarray:
    try:
        wav = as_float_mono(wav)
        rms = float(np.sqrt(np.mean(wav**2) + 1e-12))
        if rms < 1e-8:
            return wav
        scaled = wav * (target_rms / rms)
        return peak_normalize(scaled, 0.98)
    except Exception:  # noqa: BLE001
        return as_float_mono(wav)


def apply_rvc_inspired_polish(
    voice: np.ndarray,
    reference: np.ndarray | None,
    sr: int,
    f0_semitones: float = 0.0,
    index_rate: float = 0.0,
    protect: float = 0.33,
    loud_norm: bool = True,
) -> tuple[np.ndarray, str]:
    """
    Full polish chain. Always returns audio; notes what ran.
    """
    notes: list[str] = []
    try:
        voice = as_float_mono(voice)
        dry = voice.copy()
        if abs(float(f0_semitones or 0)) >= 0.05:
            voice = pitch_shift_semitones(voice, sr, float(f0_semitones))
            notes.append(f"F0 {float(f0_semitones):+.1f} st")
        if reference is not None and float(index_rate or 0) >= 0.02:
            voice = timbre_blend(voice, reference, sr, float(index_rate))
            notes.append(f"timbre α={float(index_rate):.2f}")
        if float(protect or 0) >= 0.02:
            voice = protect_consonants(dry, voice, sr, float(protect))
            notes.append(f"protect={float(protect):.2f}")
        if loud_norm:
            voice = loudness_normalize(voice)
            notes.append("loud-norm")
        return voice, ("Polish: " + ", ".join(notes)) if notes else "Polish: off"
    except Exception:  # noqa: BLE001
        logger.exception("apply_rvc_inspired_polish failed")
        return as_float_mono(voice), "Polish skipped (recovered)."


def analyze_reference(path: str | None, sr: int) -> str:
    """Human-readable ref QC report."""
    if not path or not os.path.isfile(path):
        return "Upload a reference clip to analyze."
    try:
        import soundfile as sf

        data, file_sr = sf.read(path, always_2d=False)
        wav = np.asarray(data, dtype=np.float32)
        if wav.ndim > 1:
            wav = wav.mean(axis=-1)
        file_sr = int(file_sr)
        if file_sr != sr:
            try:
                import librosa

                wav = librosa.resample(wav, orig_sr=file_sr, target_sr=sr)
            except Exception:  # noqa: BLE001
                pass
        wav = as_float_mono(wav)
        dur = wav.size / float(sr)
        peak = float(np.max(np.abs(wav)))
        rms = float(np.sqrt(np.mean(wav**2) + 1e-12))
        f0 = estimate_f0_hz(wav, sr)
        tips = []
        if dur < 2.5:
            tips.append("Short clip — aim for 3–10s.")
        elif dur > 12:
            tips.append("Long clip — enable Ref prep to auto-crop densest 6s.")
        if peak < 0.1:
            tips.append("Very quiet — re-record louder or closer.")
        if rms > 0 and peak / rms < 3:
            tips.append("Possibly compressed/noisy — prefer clean dry vocal.")
        f0_txt = f"{f0:.0f} Hz" if f0 else "n/a"
        tip_txt = " ".join(tips) if tips else "Looks usable for zero-shot cloning."
        return (
            f"Duration {dur:.1f}s · peak {peak:.2f} · RMS {rms:.3f} · "
            f"est. F0 {f0_txt}. {tip_txt}"
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("analyze_reference failed")
        return f"Analyze failed: {type(exc).__name__}: {exc}"


def write_wav(path: str, wav: np.ndarray, sr: int) -> str | None:
    try:
        import soundfile as sf

        sf.write(path, as_float_mono(wav), sr)
        return path
    except Exception:  # noqa: BLE001
        logger.exception("write_wav failed")
        return None


QUALITY_PRESETS: dict[str, dict[str, Any]] = {
    "Fast": {"num_step": 16, "guidance_scale": 1.8, "t_shift": 0.15},
    "Balanced": {"num_step": 32, "guidance_scale": 2.0, "t_shift": 0.1},
    "High fidelity": {"num_step": 48, "guidance_scale": 2.2, "t_shift": 0.08},
    "Max quality": {"num_step": 64, "guidance_scale": 2.4, "t_shift": 0.05},
}
