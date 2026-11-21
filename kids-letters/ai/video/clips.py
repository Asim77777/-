"""Animate the 4K stills into short shots with LTX-Video 2B 0.9.8 distilled, on the CPU.

Memory plan (15 GB): the T5-XXL text encoder (~9.5 GB in bf16) encodes every prompt first and is
freed; only then is the 2B video transformer loaded. Distilled settings: 8 fixed timesteps, no CFG.

Usage:
  python3 clips.py smoke                 # 25 frames at 320x576 to measure speed
  python3 clips.py [shot ...] [--seed N] # shots: noam tamar pair (default: all)"""
import os
import gc
import sys
import json
import time
import subprocess

import torch
from PIL import Image
from huggingface_hub import hf_hub_download
from diffusers import (AutoencoderKLLTXVideo, FlowMatchEulerDiscreteScheduler, LTXConditionPipeline,
                       LTXVideoTransformer3DModel)
from diffusers.pipelines.ltx.pipeline_ltx_condition import LTXVideoCondition
from transformers import T5EncoderModel, T5TokenizerFast

HERE = os.path.dirname(os.path.abspath(__file__))
FINAL = os.path.join(os.path.dirname(HERE), 'out', 'final')
OUT = os.path.join(HERE, 'out')
BASE_REPO = 'Lightricks/LTX-Video-0.9.5'          # diffusers layout: T5 encoder, tokenizer, scheduler
WEIGHTS = ('Lightricks/LTX-Video', 'ltxv-2b-0.9.8-distilled.safetensors')
TIMESTEPS = [1000, 993, 987, 981, 975, 909, 725, 0.03]   # Lightricks' distilled schedule
FPS = 24

STYLE = ('Cinematic 3D animated film, warm golden hour sunlight, shallow depth of field, '
         'smooth natural motion, highly detailed.')
SHOTS = {
    'noam': dict(image='hero_noam_base.png', frames=81, prompt=(
        'A cheerful little boy with curly brown hair and an orange hoodie stands in a sunny stone courtyard, '
        'smiles, waves his hand at the camera and talks happily while the camera slowly pushes in. ' + STYLE)),
    'tamar': dict(image='hero_tamar_base.png', frames=73, prompt=(
        'A cheerful little girl with two puffy curly pigtails and pink and yellow overalls stands by pink flowers '
        'in a sunny stone courtyard, smiles, tilts her head and talks to the camera. ' + STYLE)),
    'pair': dict(image='pair_base.png', frames=97, prompt=(
        'A little boy in an orange hoodie and a little girl in pink walk hand in hand toward the camera down a sunny '
        'stone alley with pink bougainvillea, smiling and swinging their arms. ' + STYLE)),
}


def encode(prompts):
    tok = T5TokenizerFast.from_pretrained(BASE_REPO, subfolder='tokenizer')
    enc = T5EncoderModel.from_pretrained(BASE_REPO, subfolder='text_encoder', torch_dtype=torch.bfloat16)
    out = {}
    with torch.inference_mode():
        for key, text in prompts.items():
            t = tok(text, padding='max_length', max_length=128, truncation=True, return_tensors='pt')
            emb = enc(t.input_ids, attention_mask=t.attention_mask)[0]
            out[key] = (emb, t.attention_mask)
    del enc
    gc.collect()
    return out


def load_pipe():
    path = hf_hub_download(*WEIGHTS)
    transformer = LTXVideoTransformer3DModel.from_single_file(path, torch_dtype=torch.bfloat16)
    vae = AutoencoderKLLTXVideo.from_single_file(path, torch_dtype=torch.bfloat16)
    sched = FlowMatchEulerDiscreteScheduler.from_pretrained(BASE_REPO, subfolder='scheduler')
    pipe = LTXConditionPipeline(scheduler=sched, vae=vae, text_encoder=None, tokenizer=None, transformer=transformer)
    pipe.vae.enable_tiling()
    pipe.set_progress_bar_config(disable=True)
    return pipe


def save_mp4(frames, path, fps=FPS):
    """frames: list of PIL images -> H.264 mp4 (lossless-ish, for later editing)."""
    w, h = frames[0].size
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}',
                          '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p', path],
                         stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(f.convert('RGB').tobytes())
    p.stdin.close()
    p.wait()


def render(pipe, emb, image, frames, w, h, seed):
    pe, pm = emb
    cond = LTXVideoCondition(image=image.convert('RGB').resize((w, h), Image.LANCZOS), frame_index=0)
    with torch.inference_mode():
        res = pipe(conditions=[cond], prompt_embeds=pe, prompt_attention_mask=pm,
                   negative_prompt_embeds=torch.zeros_like(pe), negative_prompt_attention_mask=pm,
                   width=w, height=h, num_frames=frames, frame_rate=FPS, timesteps=TIMESTEPS,
                   guidance_scale=1.0, decode_timestep=0.05, decode_noise_scale=0.025, image_cond_noise_scale=0.0,
                   generator=torch.Generator('cpu').manual_seed(seed), output_type='pil')
    return res.frames[0]


def main():
    torch.set_num_threads(os.cpu_count() or 4)
    os.makedirs(OUT, exist_ok=True)
    args = sys.argv[1:]
    seed = 7
    if '--seed' in args:
        i = args.index('--seed')
        seed = int(args[i + 1])
        del args[i:i + 2]
    smoke = args[:1] == ['smoke']
    shots = ['noam'] if smoke else (args or list(SHOTS))
    t0 = time.time()
    embs = encode({k: SHOTS[k]['prompt'] for k in shots})
    print(f'prompts encoded in {time.time() - t0:.0f}s', flush=True)
    t1 = time.time()
    pipe = load_pipe()
    print(f'video model loaded in {time.time() - t1:.0f}s', flush=True)
    log = []
    for k in shots:
        s = SHOTS[k]
        frames, (w, h) = (25, (320, 576)) if smoke else (s['frames'], (512, 896))
        t = time.time()
        out = render(pipe, embs[k], Image.open(os.path.join(FINAL, s['image'])), frames, w, h, seed)
        path = os.path.join(OUT, f'shot_{k}{"_smoke" if smoke else ""}_s{seed}.mp4')
        save_mp4(out, path)
        secs = time.time() - t
        log.append(dict(shot=k, seed=seed, frames=frames, size=[w, h], seconds=round(secs), prompt=s['prompt'],
                        image=s['image'], model=f'{WEIGHTS[0]}/{WEIGHTS[1]}'))
        print(f'{path}: {frames} frames {w}x{h} in {secs:.0f}s', flush=True)
    lp = os.path.join(OUT, 'clips_log.json')
    old = json.load(open(lp)) if os.path.exists(lp) else []
    json.dump(old + log, open(lp, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
