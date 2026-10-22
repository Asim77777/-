#!/usr/bin/env python3
"""Mockup frames for a "liquid 3D" lyric clip.

Everything is a height field shaded like polished liquid metal: surface
normals from the height gradient, reflections looked up in a procedural
studio environment (soft boxes and coloured strips), Fresnel, specular
highlights and a thin-film iridescence. Lyrics become molten chrome that
wobbles and drips; the floor is a reflective liquid that ripples on the beat.

Usage: python3 liquid_mockup.py OUT_DIR
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "clip2"))
from make_clip2 import SEALED, TITLE, VERSE, WISE, font  # noqa: E402
from make_clip import periodic_noise  # noqa: E402

W, H = 1920, 1080
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


def noise(scale, seed):
    return periodic_noise(H, W, scale, np.random.default_rng(seed))


def blur(a, r):
    m = float(np.abs(a).max())
    if m <= 0:
        return np.zeros_like(a, np.float32)
    im = Image.fromarray(np.clip(a / m * 255, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im, np.float32) * (m / 255)


def blur_rgb(c, r):
    return np.stack([blur(c[..., i], r) for i in range(3)], -1)


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def hsv(h, s, v):
    h = (h % 1.0) * 6
    i = np.floor(h).astype(int) % 6
    f = h - np.floor(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], -1)


# ---------------------------------------------------------------- shading

def environment(rx, ry, warm=(255, 190, 150), cool=(140, 190, 255)):
    """Procedural studio: bright sky above a soft horizon, dark ground below, soft box and coloured strips.
    Flat tops reflect the lower sky (readable), down-facing bevels catch the dark ground (crisp contours)."""
    sky_t = np.clip(-ry * 0.8 + 0.5, 0, 1)
    sky = (np.array([120, 130, 165], np.float32) * (1 - sky_t[..., None])
           + np.array([215, 222, 245], np.float32) * sky_t[..., None])
    ground = np.array([18, 14, 28], np.float32) + np.clip(ry - 0.3, 0, 1)[..., None] * np.array([60, 30, 80], np.float32)
    g = smoothstep((ry - 0.18) / 0.08)[..., None]
    col = sky * (1 - g) + ground * g
    box = np.exp(-((ry + 0.72) / 0.13) ** 2) * smoothstep((0.75 - np.abs(rx)) / 0.15)
    col += box[..., None] * np.array([255, 255, 255], np.float32) * 0.9
    left = np.exp(-((rx + 0.72) / 0.07) ** 2) * smoothstep((0.6 - ry) / 0.4)
    col += left[..., None] * np.array(cool, np.float32) * 1.1
    right = np.exp(-((rx - 0.78) / 0.05) ** 2) * smoothstep((0.7 - np.abs(ry)) / 0.3)
    col += right[..., None] * np.array(warm, np.float32) * 1.1
    floor = np.exp(-((ry - 0.8) / 0.18) ** 2)
    col += floor[..., None] * np.array([120, 60, 160], np.float32) * 0.6
    return col


def shade(h, tint, irid=0.0, bump=1.0, env_kw=None, spec=1.0):
    gy, gx = np.gradient(h)
    nx, ny = -gx * bump, -gy * bump
    inv = 1 / np.sqrt(nx * nx + ny * ny + 1)
    nx, ny, nz = nx * inv, ny * inv, inv
    rx, ry = 2 * nz * nx, 2 * nz * ny
    col = environment(rx, ry, **(env_kw or {}))
    fres = 0.35 + 0.65 * (1 - nz) ** 2.5
    col *= (np.array(tint, np.float32) / 255) * fres[..., None] * 1.6
    if irid:
        hn = h / (h.max() + 1e-6)
        film = hsv(0.55 + 2.2 * (1 - nz) + 0.35 * hn, 0.55, 1.0)
        col *= (1 - irid) + irid * film * 1.25
    for lx, ly, lz, p, k in ((-0.45, -0.65, 0.62, 140, 1.0), (0.55, -0.2, 0.8, 60, 0.35)):
        hx, hy, hz = lx, ly, lz + 1
        hl = np.sqrt(hx * hx + hy * hy + hz * hz)
        ndh = np.clip((nx * hx + ny * hy + nz * hz) / hl, 0, 1)
        col += (ndh ** p * 255 * k * spec)[..., None]
    return col


# ---------------------------------------------------------------- geometry

def text_mask(lines, size, cy, gap=1.45):
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    fnt = font(size)
    n = len(lines)
    for i, line in enumerate(lines):
        d.text((W / 2, cy + (i - (n - 1) / 2) * size * gap), line, font=fnt, fill=255, anchor="mm", direction="rtl")
    return np.asarray(m, np.float32) / 255


def warp(a, amp, seed, scale=60):
    dx = (noise(scale, seed) - 0.5) * 2 * amp
    dy = (noise(scale, seed + 1) - 0.5) * 2 * amp
    xs = np.clip(xx + dx, 0, W - 1).astype(np.int32)
    ys = np.clip(yy + dy, 0, H - 1).astype(np.int32)
    return a[ys, xs]


def drips(mask, seed, n=12, max_len=110):
    """Molten drips hanging from the lowest ink of random columns."""
    rng = np.random.default_rng(seed)
    cols = np.flatnonzero(mask.max(0) > 0.5)
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    for x in rng.choice(cols, min(n, len(cols)), replace=False):
        ys = np.flatnonzero(mask[:, x] > 0.5)
        y0 = ys[-1] - 4
        ln = rng.uniform(0.2, 1.0) * max_len
        wd = rng.uniform(4, 8)
        d.polygon([(x - wd / 2, y0), (x + wd / 2, y0), (x + wd * 0.25, y0 + ln), (x - wd * 0.25, y0 + ln)], fill=255)
        r = wd * 0.55
        d.ellipse([x - r, y0 + ln - r * 0.6, x + r, y0 + ln + r * 1.4], fill=255)
    return np.maximum(mask, np.asarray(img, np.float32) / 255)


def molten_height(mask, depth=34):
    """Rounded bevel: stacked blurs give a soft, liquid cross-section."""
    hm = blur(mask, 1.2) * 0.45 + blur(mask, 3) * 0.4 + blur(mask, 6) * 0.15
    return np.clip(hm, 0, 1) ** 0.6 * depth


def metaballs(balls):
    f = np.zeros((H, W), np.float32)
    for (x, y, r) in balls:
        f += r * r / ((xx - x) ** 2 + (yy - y) ** 2 + 1)
    return np.sqrt(np.clip(1 - 1 / np.maximum(f, 1e-3), 0, 1)) * 60 * (f > 1)


def spheres(drops):
    h = np.zeros((H, W), np.float32)
    for (x, y, r) in drops:
        h = np.maximum(h, np.sqrt(np.clip(r * r - (xx - x) ** 2 - (yy - y) ** 2, 0, None)))
    return h


def smooth_union(a, b, k=0.15):
    return np.log(np.exp(a * k) + np.exp(b * k)) / k - np.log(2) / k * (1 - np.clip((a + b) / 20, 0, 1))


def ripples(cx, cy, R, wl=40, amp=6, width=120):
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    return np.sin((r - R) / wl * 2 * np.pi) * np.exp(-((r - R) / width) ** 2) * amp


# ---------------------------------------------------------------- scene

def liquid_floor(seed, tint, irid=0.35, ripple=None, flow=8.0):
    n = noise(160, seed) * 0.6 + noise(60, seed + 1) * 0.3 + noise(20, seed + 2) * 0.1
    h = warp(n, 40, seed + 3, 120) * flow
    if ripple is not None:
        h = h + ripple
    return shade(h, tint, irid=irid, bump=1.0, spec=0.6)


def bokeh(col, seed, n=40, palette=((255, 120, 200), (120, 200, 255), (255, 210, 140))):
    rng = np.random.default_rng(seed)
    acc = np.zeros((H, W, 3), np.float32)
    for _ in range(n):
        x, y, r = rng.uniform(0, W), rng.uniform(0, H * 0.7), rng.uniform(8, 40)
        disc = np.clip((r - np.sqrt((xx - x) ** 2 + (yy - y) ** 2)) / 2, 0, 1) * rng.uniform(0.15, 0.5)
        acc += disc[..., None] * np.array(palette[rng.integers(len(palette))], np.float32)
    return col + blur_rgb(acc, 3)


def composite(bg, h_obj, tint, irid, reflect_line=None, shadow=(28, 40), env_kw=None):
    alpha = smoothstep(h_obj / 3.0)
    obj = shade(h_obj, tint, irid=irid, bump=1.4, env_kw=env_kw)
    sh = blur(alpha, 18)
    sh = np.roll(np.roll(sh, shadow[1], 0), shadow[0], 1)
    bg = bg * (1 - 0.65 * sh)[..., None]
    if reflect_line is not None:  # mirror on the liquid floor, rippled and faded
        y0 = int(reflect_line)
        ref_a = np.zeros_like(alpha)
        ref_c = np.zeros_like(obj)
        span = min(y0, H - y0)
        src = slice(y0 - span, y0)
        dst = slice(y0, y0 + span)
        ref_a[dst] = alpha[src][::-1]
        ref_c[dst] = obj[src][::-1]
        ref_a = warp(ref_a, 6, 77, 30)
        ref_c = np.stack([warp(ref_c[..., i], 6, 77, 30) for i in range(3)], -1)
        fade = np.clip(1 - (yy - y0) / (span * 0.7), 0, 1) * 0.35 * (yy > y0)
        bg = bg * (1 - (ref_a * fade)[..., None]) + ref_c * (ref_a * fade)[..., None]
    return bg * (1 - alpha[..., None]) + obj * alpha[..., None]


def finish(col, bloom=0.8):
    hi = np.clip(col - 200, 0, None)
    col = col + blur_rgb(hi, 14) * bloom + blur_rgb(hi, 40) * bloom * 0.6
    vx, vy = (xx / W - .5) * 2, (yy / H - .5) * 2
    col *= np.clip(1 - 0.35 * (vx * vx * .6 + vy * vy * .9), 0, 1)[..., None]
    col += np.random.default_rng(1).normal(0, 3, (H, W, 1)).astype(np.float32)
    return np.clip(col, 0, 255).astype(np.uint8)


CHROME = (235, 240, 255)
GOLD = (255, 200, 105)


def frame_opening():
    bg = liquid_floor(1, (90, 60, 160), irid=0.6, ripple=ripples(W / 2, H * 0.5, 380, amp=4))
    bg = bokeh(bg * 0.45, 1)
    m = warp(text_mask([TITLE], 165, H * 0.47), 5, 5, 40)
    ht = molten_height(m, 30)
    hb = metaballs([(W * .27, H * .50, 95), (W * .21, H * .58, 70), (W * .74, H * .46, 90),
                    (W * .80, H * .36, 60), (W * .78, H * .58, 55), (W * .50, H * .74, 48),
                    (W * .56, H * .80, 36), (W * .44, H * .22, 40)])
    h = np.maximum(smooth_union(ht, hb * 0.7), 0)
    return finish(composite(bg, h, CHROME, 0.75, env_kw=dict(cool=(120, 170, 255), warm=(255, 120, 200))))


def frame_verse():
    bg = liquid_floor(2, (60, 110, 190), irid=0.6, ripple=ripples(W / 2, H * 0.45, 520, wl=50, amp=7, width=160))
    bg = bokeh(bg * 0.45, 2)
    m = drips(warp(text_mask(VERSE, 92, H * 0.40), 2.5, 9, 50), 3, n=22, max_len=90)
    h = molten_height(m, 32)
    return finish(composite(bg, h, CHROME, 0.8, reflect_line=H * 0.40 + 92 * 1.45 + 70))


def frame_drop():
    rip = ripples(W / 2, H / 2, 300, wl=45, amp=9, width=130) + ripples(W / 2, H / 2, 640, wl=60, amp=6, width=170)
    bg = liquid_floor(3, (130, 40, 120), irid=0.7, ripple=rip, flow=10)
    bg = bokeh(bg * 0.5, 3, 60)
    m = warp(text_mask(WISE, 190, H * 0.48), 4, 11, 45)
    ht = molten_height(m, 40)
    rng = np.random.default_rng(4)
    drops = []
    for _ in range(60):
        a, dist = rng.uniform(0, 2 * np.pi), rng.uniform(380, 900)
        drops.append((W / 2 + np.cos(a) * dist, H / 2 + np.sin(a) * dist * 0.55, rng.uniform(5, 22)))
    h = np.maximum(ht, spheres(drops) * 0.9)
    col = composite(bg, h, CHROME, 0.9, env_kw=dict(cool=(90, 230, 255), warm=(255, 90, 190)))
    flash = np.exp(-(((xx - W / 2) / 700) ** 2 + ((yy - H / 2) / 250) ** 2))
    return finish(col + flash[..., None] * 60, bloom=1.0)


def frame_end():
    bg = liquid_floor(4, (110, 70, 40), irid=0.15, ripple=ripples(W / 2, H * 0.62, 260, wl=55, amp=3), flow=5)
    bg = bg * 0.35
    m = drips(warp(text_mask(SEALED, 110, H * 0.36), 2.5, 13, 60), 6, n=14, max_len=120)
    h = molten_height(m, 36)
    return finish(composite(bg, h, GOLD, 0.12, reflect_line=H * 0.36 + 110 * 0.75 + 150,
                            env_kw=dict(cool=(255, 230, 190), warm=(255, 170, 90))))


def sheet(frames, path):
    tw, th = 930, 523
    S = Image.new("RGB", (1920, 150 + 2 * (th + 70)), (12, 11, 16))
    d = ImageDraw.Draw(S)
    d.text((1880, 40), "ד. ליקוויד תלת־ממדי", font=font(64), fill=(235, 235, 250), anchor="ra", direction="rtl")
    d.text((1880, 112), "מילים מכרום נוזלי שנמס ומטפטף, משטח נוזלי מחזיר אור שמתגלגל בגלים על הביט, טיפות, השתקפויות ועומק",
           font=font(30, True), fill=(200, 200, 215), anchor="ra", direction="rtl")
    labels = ["פתיחה: טיפות כרום מתמזגות לכותרת", "בית: מילים מכרום נוזלי עם טפטופים והשתקפות",
              "דרופ: התזה, טיפות עפות וגלי הדף", "סיום: זהב נוזלי נמס לאט"]
    for i, (fr, lab) in enumerate(zip(frames, labels)):
        c, r = 1 - i % 2, i // 2
        x, y = 20 + c * (tw + 20), 150 + r * (th + 70)
        S.paste(Image.fromarray(fr).resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + tw - 8, y + th + 12), lab, font=font(32, True), fill=(220, 220, 230), anchor="ra", direction="rtl")
    S.save(path, quality=92)


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    frames = []
    for i, fn in enumerate((frame_opening, frame_verse, frame_drop, frame_end)):
        fr = fn()
        Image.fromarray(fr).save(os.path.join(out, f"d{i + 1}.png"))
        frames.append(fr)
        print("frame", i + 1, flush=True)
    sheet(frames, os.path.join(out, "mockup_d.jpg"))


if __name__ == "__main__":
    main()
