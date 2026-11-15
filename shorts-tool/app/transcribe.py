"""Local speech-to-text with word-level timestamps (faster-whisper)."""
from __future__ import annotations

import threading
import wave
from pathlib import Path

MODELS = {
    "hebrew": "ivrit-ai/whisper-large-v3-turbo-ct2",
    "turbo": "large-v3-turbo",
    "medium": "medium",
    "small": "small",
    "tiny": "tiny",
}

_cache: dict[str, object] = {}
_lock = threading.Lock()


def _load(model_key: str):
    name = MODELS.get(model_key, model_key)
    with _lock:
        if name in _cache:
            return _cache[name]
        from faster_whisper import WhisperModel

        try:
            import ctranslate2

            has_gpu = ctranslate2.get_cuda_device_count() > 0
        except Exception:
            has_gpu = False
        model = None
        if has_gpu:
            try:
                model = WhisperModel(name, device="cuda", compute_type="float16")
            except Exception:
                model = None
        if model is None:
            model = WhisperModel(name, device="cpu", compute_type="int8")
        _cache.clear()  # keep a single model in memory
        _cache[name] = model
        return model


def transcribe(wav: Path, model_key: str = "hebrew", language: str | None = "he",
               on_progress=None) -> dict:
    """Returns {language, words: [{t, s, e}]} with times in seconds."""
    import numpy as np

    model = _load(model_key)
    # Read the 16 kHz mono PCM wav ourselves (avoids depending on PyAV decoding)
    with wave.open(str(wav), "rb") as wf:
        pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    audio = pcm.astype(np.float32) / 32768.0
    segments, info = model.transcribe(
        audio,
        language=language or None,
        word_timestamps=True,
        vad_filter=True,
        beam_size=5,
        condition_on_previous_text=False,
    )
    total = info.duration or 1.0
    words: list[dict] = []
    for seg in segments:
        seg_started = False
        for w in seg.words or []:
            text = w.word.strip()
            # a token without a leading space continues the previous word ("7" + ",000")
            if words and text and not w.word[:1].isspace() and seg_started:
                words[-1]["t"] += text
                words[-1]["e"] = round(max(float(w.end), words[-1]["e"]), 3)
                continue
            seg_started = True
            if not any(ch.isalnum() for ch in text):
                continue  # stray punctuation such as "..."
            s = round(float(w.start), 3)
            e = round(max(float(w.end), s + 0.05), 3)
            if words and s < words[-1]["s"]:
                s = words[-1]["s"]
                e = max(e, s + 0.05)
            words.append({"t": text, "s": s, "e": e})
        if on_progress:
            on_progress(min(seg.end / total, 1.0))
    return {"language": info.language, "words": words}
