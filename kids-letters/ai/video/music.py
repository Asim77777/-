"""A short, cheerful music bed generated locally with MusicGen-small.
Usage: python3 music.py [seconds=11]  -> out/music.wav"""
import os
import sys
import time

import numpy as np
import torch
from transformers import AutoProcessor, MusicgenForConditionalGeneration

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'music.wav')
PROMPT = ("cheerful children's show theme, ukulele and glockenspiel, light hand claps, playful and bright, "
          "major key, 110 bpm, no vocals")


def main():
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 11.0
    torch.set_num_threads(os.cpu_count() or 4)
    torch.manual_seed(3)
    t = time.time()
    proc = AutoProcessor.from_pretrained('facebook/musicgen-small')
    model = MusicgenForConditionalGeneration.from_pretrained('facebook/musicgen-small')
    inputs = proc(text=[PROMPT], padding=True, return_tensors='pt')
    tokens = int(seconds * model.config.audio_encoder.frame_rate)
    with torch.inference_mode():
        audio = model.generate(**inputs, do_sample=True, guidance_scale=3.0, max_new_tokens=tokens)
    sr = model.config.audio_encoder.sampling_rate
    a = audio[0, 0].float().numpy()
    a = a / max(1e-6, np.abs(a).max()) * 0.9
    import wave
    with wave.open(OUT, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((a * 32767).astype(np.int16).tobytes())
    print(f'wrote {OUT}: {len(a) / sr:.1f}s at {sr} Hz in {time.time() - t:.0f}s')


if __name__ == '__main__':
    main()
