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
# The expression goes before the outfit, and the face reference is weaker (0.45) than for a plain
# likeness: at 0.65 it copied the picked image's expression into every close-up.
EXPR = {
    'happy': 'beaming with a huge happy open-mouth smile, sparkling eyes',
    'surprised': 'shocked surprised face, mouth wide open in an o shape, eyebrows raised high, eyes wide open',
    'laugh': 'laughing hysterically, eyes squeezed shut, head tilted back, mouth wide open',
}
OUTFIT = {
    'noam': 'small 4 year old boy, curly brown hair, chubby cheeks, orange hoodie with red cuffs',
    'tamar': 'small 5 year old girl, brown skin, dark curly hair in two puffy pigtails with pink ties, pink and yellow overalls',
}
CLOSEUP_NEG = NEGATIVE + ', full body, legs, shoes, denim jacket, blue sleeves'

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
    p = (f'{STYLE}, full body, only two kids holding hands, a curly haired little boy in an orange hoodie '
         f'and a little girl with two puffy pigtails in pink and yellow overalls, {SETTING}')
    w, h = PORTRAIT
    left = Image.new('L', (w, h), 0)
    left.paste(255, (0, 0, w // 2, h))
    right = Image.new('L', (w, h), 0)
    right.paste(255, (w // 2, 0, w, h))
    masks = IPAdapterMaskProcessor().preprocess([left, right], height=h, width=w)
    masks = [masks.reshape(1, masks.shape[0], masks.shape[2], masks.shape[3])]
    gen.pipe.set_ip_adapter_scale([[0.4, 0.4]])
    g = torch.Generator('cpu').manual_seed(seed)
    with torch.inference_mode():
        lat = gen.pipe(prompt=p, negative_prompt=NEGATIVE + ', third child, three kids, crowd, adult, pink hoodie', width=w, height=h,
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
    elif job.startswith('pair'):
        seed = int(job[5:]) if job[5:] else 77
        base, p = pair_image(seed)
        finish(job, base, dict(job=job, seed=seed, prompt=p, ref='both faces, masked halves', ref_scale=0.4,
                               gen_seconds=round(time.time() - t)))
    else:
        who, expr = job.split('_', 1)
        p = f'{STYLE}, head and shoulders close-up, {EXPR[expr]}, {OUTFIT[who]}, {SETTING}'
        seed = CHOSEN[who]['seed']
        base, secs = gen(p, CLOSEUP_NEG, seed, size=PORTRAIT, ref=FACE[who], ref_scale=0.45)
        finish(job, base, dict(job=job, seed=seed, prompt=p, negative=CLOSEUP_NEG, ref=f'out/final/{who}_face_ref.png',
                               ref_scale=0.45, gen_seconds=round(secs)))
