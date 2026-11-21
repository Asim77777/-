"""Detail pass for 4K: upscale, then let the image model repaint fine texture tile by tile.

Plain upscalers can only sharpen what is in the ~768px source. A light image-to-image pass
(low strength) over overlapping 1024px tiles adds real skin, hair and fabric detail while keeping
composition and identity. Tiles get a generic "detail" prompt so no tile invents a new face.

Usage: python3 refine.py <in.png> <out.png> [strength=0.3] [work_long_side=2688]"""
import os
import sys
import time

import numpy as np
import torch
from PIL import Image
from diffusers import StableDiffusionXLImg2ImgPipeline

from upscale import upscale4, to_4k, release

TILE_PROMPT = ('cinematic 3d animated film still, hyperrealistic, sharp focus, highly detailed skin texture, '
               'detailed hair strands, detailed fabric, volumetric light')
TILE_NEGATIVE = 'blurry, lowres, text, watermark, extra face, extra eyes, deformed, jpeg artifacts'


def _ramp(n, overlap, at_start, at_end):
    w = np.ones(n, dtype=np.float32)
    if overlap > 0:
        r = np.linspace(0, 1, overlap + 2, dtype=np.float32)[1:-1]
        if not at_start:
            w[:overlap] = r
        if not at_end:
            w[-overlap:] = r[::-1]
    return w


def _starts(total, tile, overlap):
    if total <= tile:
        return [0]
    step = tile - overlap
    s = list(range(0, total - tile, step)) + [total - tile]
    return sorted(set(s))


@torch.inference_mode()
def detail(gen, img, strength=0.3, tile=1024, overlap=256, steps=8, seed=7):
    pipe = StableDiffusionXLImg2ImgPipeline(**gen.pipe.components)  # shares the modules; from_pipe copied them (OOM)
    pipe.set_progress_bar_config(disable=True)
    vae = gen.pipe.vae
    sf = vae.config.scaling_factor
    W, H = img.size
    src = np.asarray(img.convert('RGB'), dtype=np.float32) / 255.0
    acc = np.zeros((H, W, 3), dtype=np.float32)
    wsum = np.zeros((H, W, 1), dtype=np.float32)
    ys, xs = _starts(H, tile, overlap), _starts(W, tile, overlap)
    extra = {}
    if getattr(gen, 'face_adapter', False):  # an adapter-equipped UNet still needs an (ignored) image input
        from generate import _blank
        pipe.set_ip_adapter_scale(0.0)
        extra['ip_adapter_image'] = _blank()
    for y0 in ys:
        for x0 in xs:
            th, tw = min(tile, H), min(tile, W)
            crop = src[y0:y0 + th, x0:x0 + tw]
            t = torch.from_numpy(crop).permute(2, 0, 1)[None] * 2 - 1
            lat = vae.encode(t.float()).latent_dist.mean * sf
            out = pipe(prompt=TILE_PROMPT, negative_prompt=TILE_NEGATIVE, image=lat.to(torch.bfloat16),
                       strength=strength, num_inference_steps=steps, guidance_scale=2.0,
                       generator=torch.Generator('cpu').manual_seed(seed), output_type='latent', **extra).images
            dec = vae.decode(out.float() / sf).sample[0]
            dec = ((dec.clamp(-1, 1) + 1) / 2).permute(1, 2, 0).numpy()
            wy = _ramp(th, overlap, y0 == 0, y0 + th >= H)
            wx = _ramp(tw, overlap, x0 == 0, x0 + tw >= W)
            w = (wy[:, None] * wx[None, :])[..., None]
            acc[y0:y0 + th, x0:x0 + tw] += dec * w
            wsum[y0:y0 + th, x0:x0 + tw] += w
    res = acc / np.maximum(wsum, 1e-6)
    return Image.fromarray((res.clip(0, 1) * 255 + 0.5).astype(np.uint8))


def make_4k(gen, src_img, strength=0.3, work_long=2688):
    """source (~768x1344) -> 4x UltraSharp -> working size (long side work_long) -> detail pass -> exact 4K."""
    big = upscale4(src_img)
    release()
    w, h = big.size
    k = work_long / max(w, h)
    work = big.resize((round(w * k / 8) * 8, round(h * k / 8) * 8), Image.LANCZOS)
    refined = detail(gen, work, strength=strength)
    return to_4k(refined)


if __name__ == '__main__':
    from generate import Generator
    torch.set_num_threads(os.cpu_count() or 4)
    strength = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3
    work_long = int(sys.argv[4]) if len(sys.argv) > 4 else 2688
    t = time.time()
    gen = Generator()
    out = make_4k(gen, Image.open(sys.argv[1]), strength, work_long)
    out.save(sys.argv[2])
    print(f'wrote {sys.argv[2]} {out.size[0]}x{out.size[1]} in {time.time() - t:.0f}s')
