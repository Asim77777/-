"""Hebrew voices for the intro, made locally and for free.

The voice is a Hebrew VITS (Piper) model from the Phonikud project, run with onnxruntime.
Its text front end (the `phonikud` library) is only on GitHub, which is blocked here, so the
three short lines are written directly in the model's phoneme alphabet (IPA with ˈ before the
stressed vowel, ʔ for alef, ʁ for resh, χ for het), following the project's own transcripts.
To sound like a child, each line is spoken slower by a factor r and then played r times faster
(resampling). That raises pitch and formants together, like a smaller vocal tract, keeps the
normal tempo, and sounds much cleaner than a phase-vocoder pitch shift: Whisper understood the
resampled lines word for word, while the rubberband versions came out garbled.

Usage: python3 voices.py   -> out/voice_<line>.wav and out/voices.json"""
import os
import json
import subprocess

import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
VOICE_REPO = 'Phoonnx/vits-he_il-shaul-phonikud'

# line id -> (hebrew text, phonemes, semitones up, length factor: >1 speaks slower, as small kids do)
LINES = {
    'noam':  ('שלום! אני נועם!', 'ʃalˈom! ʔanˈi noʔˈam!', 5.0, 1.35),
    'tamar': ('ואני תמר!', 'vaʔanˈi, tamˈaːʁ!', 7.0, 1.5),
    'both_noam':  ('בואו נלמד את כל האותיות!', 'bˈoʔu nilmˈad ʔˈet kˈol haʔotijˈot!', 5.0, 1.3),
    'both_tamar': ('בואו נלמד את כל האותיות!', 'bˈoʔu nilmˈad ʔˈet kˈol haʔotijˈot!', 7.0, 1.3),
}


class Piper:
    def __init__(self, repo):
        self.cfg = json.load(open(hf_hub_download(repo, 'config.json')))
        self.sess = ort.InferenceSession(hf_hub_download(repo, 'model.onnx'), providers=['CPUExecutionProvider'])
        # phoonnx stores one int per symbol; classic Piper configs store a list of ints
        self.map = {k: (v if isinstance(v, list) else [v]) for k, v in self.cfg['phoneme_id_map'].items()}
        self.sr = self.cfg['audio']['sample_rate']

    def ids(self, phonemes):
        blank, bos, eos = (self.map[c][0] for c in ('_', '^', '$'))
        seq = [bos, blank]
        for ch in phonemes:
            if ch not in self.map:
                raise ValueError(f'phoneme {ch!r} not in the voice alphabet')
            seq += [self.map[ch][0], blank]
        return seq + [eos]

    def speak(self, phonemes, speed=1.0, seed=0):
        np.random.seed(seed)
        x = np.array([self.ids(phonemes)], dtype=np.int64)
        inf = self.cfg['inference']
        scales = np.array([inf['noise_scale'], inf['length_scale'] * speed, inf['noise_w']], dtype=np.float32)
        audio = self.sess.run(None, {'input': x, 'input_lengths': np.array([x.shape[1]], dtype=np.int64),
                                     'scales': scales})[0].squeeze()
        return np.clip(audio, -1, 1)


def save_wav(path, audio, sr):
    import wave
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((audio * 32767).astype(np.int16).tobytes())


def duration(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def main():
    os.makedirs(OUT, exist_ok=True)
    tts = Piper(VOICE_REPO)
    info = {}
    for key, (text, ph, semis, speed) in LINES.items():
        raw = os.path.join(OUT, f'raw_{key}.wav')
        ratio = 2 ** (semis / 12)
        save_wav(raw, tts.speak(ph, speed * ratio), tts.sr)   # speak slower by ratio...
        wav = os.path.join(OUT, f'voice_{key}.wav')
        # ...play ratio times faster (pitch and formants up together); trim silence; even loudness
        af = (f'asetrate={int(tts.sr * ratio)},aresample=48000,'
              'silenceremove=start_periods=1:start_threshold=-55dB,'   # leading silence only: the tail holds a soft final consonant
              'loudnorm=I=-16:TP=-1.5:LRA=7')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-af', af, '-ar', '48000', '-ac', '1', wav], check=True)
        info[key] = {'text': text, 'phonemes': ph, 'semitones': semis, 'speed': speed, 'seconds': round(duration(wav), 2)}
        print(key, info[key], flush=True)
    both = os.path.join(OUT, 'voice_both.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(OUT, 'voice_both_noam.wav'),
                    '-i', os.path.join(OUT, 'voice_both_tamar.wav'),
                    '-filter_complex', '[1]adelay=35[b];[0][b]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=7',
                    '-ar', '48000', '-ac', '1', both], check=True)
    info['both'] = {'text': LINES['both_noam'][0], 'seconds': round(duration(both), 2)}
    print('both', info['both'])
    json.dump({'voice': VOICE_REPO, 'lines': info}, open(os.path.join(OUT, 'voices.json'), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
