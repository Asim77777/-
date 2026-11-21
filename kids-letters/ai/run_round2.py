"""Round 2: the final 4K set built on the user's picks (out/chosen.json).

Jobs (each one: generate at ~768x1344 with the picked face as IP-Adapter reference, then the
4K detail pass from refine.py):
  hero_<who>        the picked image itself, taken to 4K
  <who>_<expr>      close-ups: happy, surprised, laugh
  pair              both kids together; each face reference is limited to its half of the frame
Two phases, each in its own process so memory stays under the limit:
  python3 run_round2.py bases [job ...]   generate *_base.png (face adapter loaded)
  python3 run_round2.py 4k                take every *_base.png without a *_4k.png to 4K (no adapter)"""
import os
import sys
import time
import json

import torch
from PIL import Image
from diffusers.image_processor import IPAdapterMaskProcessor

from characters import STYLE, SETTING, NOAM, TAMAR, NEGATIVE
from generate import Generator, log_entry, PORTRAIT
from refine import make_4k

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'final')
LOG = os.path.join(HERE, 'out', 'log.json')
CHOSEN = json.load(open(os.path.join(HERE, 'out', 'chosen.json')))
IDENTITY = {'noam': NOAM, 'tamar': TAMAR}
FACE = {w: Image.open(os.path.join(OUT, f'{w}_face_ref.png')).convert('RGB') for w in IDENTITY}
EXPR = {
    'happy': 'big happy smile',
    'surprised': 'surprised face, mouth open in an o, raised eyebrows, wide eyes',
    'laugh': 'laughing out loud, eyes squeezed shut, wide open mouth',
}

MODE = sys.argv[1] if len(sys.argv) > 1 else 'bases'
jobs = sys.argv[2:] or (['hero_noam', 'hero_tamar'] + [f'{w}_{e}' for w in IDENTITY for e in EXPR] + ['pair'])
os.makedirs(OUT, exist_ok=True)
torch.set_num_threads(os.cpu_count() or 4)

if MODE == '4k':
    gen = Generator(face_adapter=False)
    for f in sorted(os.listdir(OUT)):
        if not f.endswith('_base.png'):
            continue
        name = f[:-len('_base.png')]
        path = os.path.join(OUT, f'{name}_4k.png')
        if os.path.exists(path):
            continue
        t = time.time()
        big = make_4k(gen, Image.open(os.path.join(OUT, f)).convert('RGB'), strength=0.3)
        big.save(path)
        log_entry(LOG, file=os.path.relpath(path, HERE), source=f'out/final/{f}', detail_seconds=round(time.time() - t))
        print(f'{path} {big.size[0]}x{big.size[1]} (4K pass {time.time() - t:.0f}s)', flush=True)
    sys.exit(0)

gen = Generator(face_adapter=True)


def finish(name, base, info):
    """Save the base image and log it; the 4K pass runs later in its own process."""
    path = os.path.join(OUT, f'{name}_base.png')
    base.save(path)
    log_entry(LOG, file=os.path.relpath(path, HERE), **info)
    print(f'{path}', flush=True)


def pair_image(seed):
    p = (f'{STYLE}, full body, two small kids side by side, on the left a 4 year old boy with curly brown hair in an '
         f'orange hoodie and jeans, on the right a 5 year old girl with brown skin and two puffy pigtails in pink and '
         f'yellow overalls, {SETTING}')
    w, h = PORTRAIT
    left = Image.new('L', (w, h), 0)
    left.paste(255, (0, 0, w // 2, h))
    right = Image.new('L', (w, h), 0)
    right.paste(255, (w // 2, 0, w, h))
    masks = IPAdapterMaskProcessor().preprocess([left, right], height=h, width=w)
    masks = [masks.reshape(1, masks.shape[0], masks.shape[2], masks.shape[3])]
    gen.pipe.set_ip_adapter_scale([[0.6, 0.6]])
    g = torch.Generator('cpu').manual_seed(seed)
    with torch.inference_mode():
        lat = gen.pipe(prompt=p, negative_prompt=NEGATIVE + ', third child, crowd', width=w, height=h,
                       num_inference_steps=8, guidance_scale=2.0, generator=g, output_type='latent',
                       ip_adapter_image=[[FACE['noam'], FACE['tamar']]],
                       cross_attention_kwargs={'ip_adapter_masks': masks}).images
        vae = gen.pipe.vae
        dec = vae.decode(lat.float() / vae.config.scaling_factor).sample
    return gen.pipe.image_processor.postprocess(dec, output_type='pil')[0], p


for job in jobs:
    if os.path.exists(os.path.join(OUT, f'{job}_base.png')):
        continue
    t = time.time()
    if job.startswith('hero_'):
        who = job[5:]
        base = Image.open(os.path.join(HERE, CHOSEN[who]['file'])).convert('RGB')
        finish(job, base, dict(job=job, source=CHOSEN[who]['file']))
    elif job == 'pair':
        seed = 77
        base, p = pair_image(seed)
        finish(job, base, dict(job=job, seed=seed, prompt=p, ref='both faces, masked halves', ref_scale=0.6,
                               gen_seconds=round(time.time() - t)))
    else:
        who, expr = job.split('_', 1)
        p = f'{STYLE}, close-up portrait, {IDENTITY[who]}, {EXPR[expr]}, {SETTING}'
        seed = CHOSEN[who]['seed']
        base, secs = gen(p, NEGATIVE, seed, size=PORTRAIT, ref=FACE[who], ref_scale=0.65)
        finish(job, base, dict(job=job, seed=seed, prompt=p, ref=f'out/final/{who}_face_ref.png', ref_scale=0.65,
                               gen_seconds=round(secs)))
