"""Image generation on the CPU with DreamShaper XL Lightning (SDXL, 4-8 steps) in bfloat16.
The CPU here has AMX-BF16, which makes bfloat16 the fast path.

Use as a module (Generator) or from the command line:
    python3 generate.py <out.png> "<prompt>" [seed] [--ref ref.png --ref-scale 0.6] [--size 768x1344]"""
import os
import sys
import json
import time
import argparse

import torch
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

MODEL = 'Lykon/dreamshaper-xl-lightning'
IPA_REPO = 'h94/IP-Adapter'
IPA_WEIGHTS = 'ip-adapter-plus-face_sdxl_vit-h.safetensors'

PORTRAIT = (768, 1344)   # SDXL bucket closest to 9:16
LANDSCAPE = (1344, 768)
SQUARE = (1024, 1024)


class Generator:
    def __init__(self, face_adapter=False):
        torch.set_num_threads(os.cpu_count() or 4)
        t = time.time()
        self.pipe = StableDiffusionXLPipeline.from_pretrained(MODEL, torch_dtype=torch.bfloat16, variant='fp16')
        # DPM++ SDE Karras is the sampler DreamShaper Lightning is tuned for
        self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            self.pipe.scheduler.config, algorithm_type='sde-dpmsolver++', use_karras_sigmas=True)
        self.pipe.vae.to(torch.float32)  # decode in full precision: cleaner skin gradients
        self.face_adapter = False
        if face_adapter:
            self.enable_face_adapter()
        self.pipe.set_progress_bar_config(disable=True)
        print(f'model loaded in {time.time() - t:.0f}s', flush=True)

    def enable_face_adapter(self):
        if not self.face_adapter:
            self.pipe.load_ip_adapter(IPA_REPO, subfolder='sdxl_models', weight_name=IPA_WEIGHTS,
                                      image_encoder_folder='models/image_encoder', torch_dtype=torch.bfloat16)
            self.face_adapter = True

    @torch.inference_mode()
    def __call__(self, prompt, negative, seed, size=PORTRAIT, steps=7, cfg=2.0, ref=None, ref_scale=0.6):
        w, h = size
        kw = {}
        if ref is not None:
            self.enable_face_adapter()
            self.pipe.set_ip_adapter_scale(ref_scale)
            kw['ip_adapter_image'] = ref
        elif self.face_adapter:
            self.pipe.set_ip_adapter_scale(0.0)
            kw['ip_adapter_image'] = _blank()
        g = torch.Generator('cpu').manual_seed(seed)
        t = time.time()
        lat = self.pipe(prompt=prompt, negative_prompt=negative, width=w, height=h, num_inference_steps=steps,
                        guidance_scale=cfg, generator=g, output_type='latent', **kw).images
        # decode ourselves in float32 (the pipeline would hand bf16 latents to the fp32 VAE)
        vae = self.pipe.vae
        dec = vae.decode(lat.float() / vae.config.scaling_factor).sample
        img = self.pipe.image_processor.postprocess(dec, output_type='pil')[0]
        return img, time.time() - t


def _blank():
    from PIL import Image
    return Image.new('RGB', (224, 224), (128, 128, 128))


def log_entry(path, **info):
    """Append one record to out/log.json so every image can be reproduced."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = json.load(open(path)) if os.path.exists(path) else []
    data.append(info)
    json.dump(data, open(path, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    from PIL import Image
    from characters import NEGATIVE
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('prompt')
    ap.add_argument('seed', nargs='?', type=int, default=1)
    ap.add_argument('--ref')
    ap.add_argument('--ref-scale', type=float, default=0.6)
    ap.add_argument('--size', default='768x1344')
    ap.add_argument('--steps', type=int, default=7)
    a = ap.parse_args()
    size = tuple(int(v) for v in a.size.split('x'))
    gen = Generator(face_adapter=bool(a.ref))
    ref = Image.open(a.ref).convert('RGB') if a.ref else None
    img, secs = gen(a.prompt, NEGATIVE, a.seed, size=size, steps=a.steps, ref=ref, ref_scale=a.ref_scale)
    img.save(a.out)
    print(f'wrote {a.out} in {secs:.0f}s')
