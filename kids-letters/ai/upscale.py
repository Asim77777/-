"""4x upscale with Real-ESRGAN (loaded through spandrel), then crop and resize to exact 4K.
Portrait -> 2160x3840, landscape -> 3840x2160, square -> 2160x2160.
Usage: python3 upscale.py <in.png> <out.jpg|png>"""
import os
import sys
import time

import numpy as np
import torch
from PIL import Image
from huggingface_hub import hf_hub_download
from spandrel import ModelLoader

_model = None


def model():
    global _model
    if _model is None:
        path = hf_hub_download('ai-forever/Real-ESRGAN', 'RealESRGAN_x4.pth')
        _model = ModelLoader().load_from_file(path).eval()
    return _model


@torch.inference_mode()
def upscale4(img, tile=256, pad=16):
    """Tiled 4x upscale so memory stays small on the CPU."""
    m = model().model
    x = torch.from_numpy(np.asarray(img.convert('RGB'), dtype=np.float32) / 255.0).permute(2, 0, 1)[None]
    _, _, H, W = x.shape
    out = torch.zeros((1, 3, H * 4, W * 4))
    for y0 in range(0, H, tile):
        for x0 in range(0, W, tile):
            ya, yb = max(0, y0 - pad), min(H, y0 + tile + pad)
            xa, xb = max(0, x0 - pad), min(W, x0 + tile + pad)
            with torch.autocast('cpu', dtype=torch.bfloat16):
                y = m(x[:, :, ya:yb, xa:xb]).float()
            ty, tx = (y0 - ya) * 4, (x0 - xa) * 4
            th, tw = min(tile, H - y0) * 4, min(tile, W - x0) * 4
            out[:, :, y0 * 4:y0 * 4 + th, x0 * 4:x0 * 4 + tw] = y[:, :, ty:ty + th, tx:tx + tw]
    arr = (out[0].clamp(0, 1).permute(1, 2, 0).numpy() * 255.0 + 0.5).astype(np.uint8)
    return Image.fromarray(arr)


def to_4k(img):
    w, h = img.size
    if abs(w - h) < 8:
        target = (2160, 2160)
    elif h > w:
        target = (2160, 3840)
    else:
        target = (3840, 2160)
    tw, th = target
    # crop to the target aspect ratio around the center, then resize
    if w / h > tw / th:
        nw = round(h * tw / th)
        img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = round(w * th / tw)
        img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    return img.resize(target, Image.LANCZOS)


def upscale_file(src, dst):
    t = time.time()
    big = to_4k(upscale4(Image.open(src)))
    if dst.lower().endswith(('.jpg', '.jpeg')):
        big.save(dst, quality=93, optimize=True, progressive=True)
    else:
        big.save(dst)
    return big.size, time.time() - t


if __name__ == '__main__':
    torch.set_num_threads(os.cpu_count() or 4)
    size, secs = upscale_file(sys.argv[1], sys.argv[2])
    print(f'wrote {sys.argv[2]} {size[0]}x{size[1]} in {secs:.0f}s')
