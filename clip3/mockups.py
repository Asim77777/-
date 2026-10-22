#!/usr/bin/env python3
"""Storyboard mockups for three alternative clip concepts for the mashup.

  A  "מגילה ודיו"    – ink written onto a burning parchment scroll
  B  "ניאון ירושלים" – synthwave neon Jerusalem skyline, VHS glitches
  C  "כזוהר הרקיע"  – cosmic nebula, lyrics drawn as star constellations

Each concept renders four key frames (opening, verse, drop/chorus, ending)
at 1920x1080 plus a labelled contact sheet.

Usage: python3 mockups.py OUT_DIR
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
VERSE_312 = "וְהַמַּשְׂכִּלִים יַזְהִרוּ כְּזֹהַר הָרָקִיעַ"

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


# ---------------------------------------------------------------- helpers

def noise(scale, seed, size=(H, W)):
    return periodic_noise(size[0], size[1], scale, np.random.default_rng(seed))


def blur(a, r):
    """Gaussian blur of a float field (PIL only blurs 8-bit images, so normalise around it)."""
    m = float(a.max())
    if m <= 0:
        return np.zeros_like(a, np.float32)
    im = Image.fromarray(np.clip(a / m * 255, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im, np.float32) * (m / 255)


def text_mask(lines, size, cy, gap=1.5, cx=W / 2, light=False):
    """Float mask (H, W) of centred RTL lines."""
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    fnt = font(size, light)
    n = len(lines)
    for i, line in enumerate(lines):
        y = cy + (i - (n - 1) / 2) * size * gap
        d.text((cx, y), line, font=fnt, fill=255, anchor="mm", direction="rtl")
    return np.asarray(m, np.float32) / 255


def line_masks(lines, size, cy, gap=1.5):
    return [text_mask([l], size, cy + (i - (len(lines) - 1) / 2) * size * gap) for i, l in enumerate(lines)]


def reveal_rtl(mask, frac):
    """Keep the right-hand `frac` of the mask's ink (text written right to left)."""
    cols = np.flatnonzero(mask.max(0) > 0.1)
    if not len(cols) or frac >= 1:
        return mask
    x_cut = cols[-1] - (cols[-1] - cols[0]) * frac
    return mask * np.clip((xx - x_cut) / 12, 0, 1)


def hexagram(d, cx, cy, R, width, fill=None, outline=255):
    for rot in (0, np.pi):
        pts = [(cx + R * np.sin(rot + k * 2 * np.pi / 3), cy - R * np.cos(rot + k * 2 * np.pi / 3)) for k in range(3)]
        d.polygon(pts, fill=fill, outline=outline, width=width)


def to_img(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------- A: scroll & ink

INK = np.array([38, 24, 16], np.float32)


def parchment(seed=1, light=1.0):
    n1, n2, n3 = noise(70, seed), noise(10, seed + 1), noise(3, seed + 2)
    base = np.array([228, 206, 166], np.float32)
    shade = 0.80 + 0.22 * n1 + 0.07 * n2 + 0.04 * n3
    col = base * shade[..., None]
    # fibres
    fib = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(fib)
    rng = np.random.default_rng(seed)
    for _ in range(900):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        ln, an = rng.uniform(20, 90), rng.normal(0, 0.25)
        d.line([(x, y), (x + ln * np.cos(an), y + ln * np.sin(an))], fill=int(rng.uniform(20, 60)), width=1)
    col *= 1 - (np.asarray(fib, np.float32) / 255 * 0.25)[..., None]
    # stains
    stain = np.clip((noise(40, seed + 3) - 0.62) * 4, 0, 1)
    col *= 1 - (stain * 0.22)[..., None]

    # page between the rollers, with burnt top/bottom edges
    x0, x1 = 250, W - 250
    en = noise(14, seed + 4) * 46
    edge = np.minimum(np.minimum(yy - 40, H - 40 - yy) + en - 23, np.minimum(xx - x0, x1 - xx) + 60)
    burn = np.clip(edge / 55, 0, 1)
    ember = np.exp(-((edge - 3) / 5) ** 2) * (edge > -6)
    col *= (0.15 + 0.85 * burn)[..., None]
    col += ember[..., None] * np.array([255, 120, 20], np.float32) * 0.9
    page = (edge > -4).astype(np.float32)
    bg = np.array([22, 13, 8], np.float32) * (0.6 + 0.6 * noise(30, seed + 5))[..., None]
    col = col * page[..., None] + bg * (1 - page[..., None])

    # wooden rollers (atzei chayim)
    grain = 0.8 + 0.3 * noise(6, seed + 7)
    for cx in (x0 - 20, x1 + 20):
        u = np.clip(1 - ((xx - cx) / 46) ** 2, 0, 1)
        on = (np.abs(xx - cx) < 46) & (yy > 10) & (yy < H - 10)
        wood = np.array([105, 58, 28], np.float32) * (0.25 + 0.95 * u ** 0.6 * grain)[..., None]
        wood += (np.exp(-((xx - cx + 18) / 7) ** 2) * 50)[..., None]  # specular stripe
        col = np.where(on[..., None], wood, col)
        for ky in (10, H - 10):  # carved knobs
            kn = np.clip((62 - np.sqrt((xx - cx) ** 2 + ((yy - ky) * 2.2) ** 2)) / 2, 0, 1)
            col = col * (1 - kn[..., None]) + np.array([150, 95, 40], np.float32) * kn[..., None] * \
                (0.6 + 0.6 * u)[..., None]
    # candle light from upper left
    r = np.sqrt((xx - W * 0.2) ** 2 + (yy - H * 0.1) ** 2) / W
    col *= (np.clip(1.25 - r * 0.9, 0.25, 1.2) * light)[..., None]
    return col


def ink_text(col, mask, seed=0, amount=1.0, color=INK):
    n = noise(2.5, 50 + seed)
    m = blur(mask, 1.1)
    ink = np.clip((m - 0.45 + (n - 0.5) * 0.4) * 4, 0, 1) * amount
    bleed = blur(ink, 4) * 0.35
    col *= (1 - bleed)[..., None]
    col *= (1 - ink * 0.95)[..., None]
    col += color * ink[..., None] * 0.95
    return col


def ink_blot(col, cx, cy, R, seed, amount=1.0):
    rng = np.random.default_rng(seed)
    dx, dy = xx - cx, yy - cy
    rr, an = np.sqrt(dx * dx + dy * dy), np.arctan2(dy, dx)
    mod = sum(rng.uniform(0.04, 0.14) * np.sin(k * an + rng.uniform(0, 6.3)) for k in range(2, 12))
    blot = np.clip((R * (1 + mod) - rr) / 3, 0, 1)
    for _ in range(26):  # satellite splatter
        a, dist = rng.uniform(0, 2 * np.pi), R * rng.uniform(1.1, 2.6)
        rs = R * rng.uniform(0.02, 0.09)
        sx, sy = cx + np.cos(a) * dist, cy + np.sin(a) * dist
        blot = np.maximum(blot, np.clip((rs - np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2)) / 2, 0, 1))
    halo = blur(blot, 6) * 0.35
    col *= (1 - halo * amount)[..., None]
    col *= (1 - blot * 0.93 * amount)[..., None]
    col += INK * (blot * amount)[..., None]
    return col


def gold_fill(col, mask, top=None, bottom=None, sparkle_seed=None):
    top = np.array([255, 236, 150], np.float32) if top is None else top
    bottom = np.array([170, 105, 25], np.float32) if bottom is None else bottom
    ys = np.flatnonzero(mask.max(1) > 0.1)
    y0, y1 = (ys[0], ys[-1]) if len(ys) else (0, H)
    u = np.clip((yy - y0) / max(1, y1 - y0), 0, 1)
    u = 0.5 + 0.5 * np.sin(u * np.pi * 2.2)  # metallic banding
    g = top * u[..., None] + bottom * (1 - u[..., None])
    emb = np.clip(mask - np.roll(np.roll(mask, 3, 0), 3, 1), 0, 1)
    shadow = np.roll(np.roll(blur(mask, 3), 5, 0), 5, 1)
    col *= (1 - shadow * 0.45)[..., None]
    col = col * (1 - mask[..., None]) + g * mask[..., None]
    col += emb[..., None] * 90
    if sparkle_seed is not None:
        rng = np.random.default_rng(sparkle_seed)
        ys_, xs_ = np.nonzero(mask > 0.8)
        for i in rng.choice(len(xs_), 18, replace=False):
            sx, sy = xs_[i], ys_[i]
            r = np.sqrt((xx - sx) ** 2 + ((yy - sy) * 7) ** 2)
            r2 = np.sqrt(((xx - sx) * 7) ** 2 + (yy - sy) ** 2)
            col += (np.exp(-r / 5) + np.exp(-r2 / 5))[..., None] * 230
    return col


def illuminated_initial(col, letter, cx, cy, S=150):
    box = np.zeros((H, W), np.float32)
    box[int(cy - S / 2):int(cy + S / 2), int(cx - S / 2):int(cx + S / 2)] = 1
    col = col * (1 - box[..., None]) + np.array([28, 45, 105], np.float32) * box[..., None]
    fr = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(fr)
    for k, wd in ((0, 6), (12, 2)):
        d.rectangle([cx - S / 2 + k, cy - S / 2 + k, cx + S / 2 - k, cy + S / 2 - k], outline=255, width=wd)
    for sx in (-1, 1):
        for sy in (-1, 1):
            d.ellipse([cx + sx * S / 2 - 14, cy + sy * S / 2 - 14, cx + sx * S / 2 + 14, cy + sy * S / 2 + 14],
                      outline=255, width=4)
    for k in range(5):  # vine dots
        d.ellipse([cx - S / 2 + 22 + k * 26 - 3, cy + S / 2 - 26, cx - S / 2 + 22 + k * 26 + 3, cy + S / 2 - 20], fill=255)
    col = gold_fill(col, np.asarray(fr, np.float32) / 255)
    lm = Image.new("L", (W, H), 0)
    ImageDraw.Draw(lm).text((cx, cy - 4), letter, font=font(150), fill=255, anchor="mm")
    return gold_fill(col, np.asarray(lm, np.float32) / 255)


def wax_seal(col, cx, cy, R, seed=9):
    rng = np.random.default_rng(seed)
    dx, dy = xx - cx, yy - cy
    rr, an = np.sqrt(dx * dx + dy * dy), np.arctan2(dy, dx)
    mod = sum(rng.uniform(0.01, 0.05) * np.sin(k * an + rng.uniform(0, 6.3)) for k in range(3, 14))
    m = np.clip((R * (1 + mod) - rr) / 2, 0, 1)
    shade = np.clip(1.15 - ((dx + R * 0.4) ** 2 + (dy + R * 0.4) ** 2) ** 0.5 / (R * 2.4), 0.45, 1.2)
    wax = np.array([150, 18, 22], np.float32) * shade[..., None]
    sh = np.roll(np.roll(blur(m, 10), 12, 0), 10, 1)
    col *= (1 - sh * 0.5)[..., None]
    col = col * (1 - m[..., None]) + wax * m[..., None]
    em = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(em)
    d.ellipse([cx - R * .72, cy - R * .72, cx + R * .72, cy + R * .72], outline=255, width=6)
    hexagram(d, cx, cy, R * .6, 7)
    e = np.asarray(em, np.float32) / 255
    hi = np.clip(e - np.roll(np.roll(e, 3, 0), 3, 1), 0, 1)
    lo = np.clip(e - np.roll(np.roll(e, -3, 0), -3, 1), 0, 1)
    col += (hi * 120 - lo * 70)[..., None] * m[..., None]
    col += np.exp(-(((dx + R * .35) / (R * .25)) ** 2 + ((dy + R * .4) / (R * .15)) ** 2))[..., None] * 90 * m[..., None]
    return col


def embers(col, seed, n=120, region=(0, H)):
    rng = np.random.default_rng(seed)
    acc = np.zeros((H, W), np.float32)
    for _ in range(n):
        x, y = rng.uniform(0, W), rng.uniform(*region)
        r = rng.uniform(1, 3.5)
        acc += np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * r * r)) * rng.uniform(.4, 1)
    col += acc[..., None] * np.array([255, 140, 40], np.float32)
    return col


def concept_a():
    frames = []
    # 1 opening: candle-lit page, title being written, first ink drop on the beat
    c = parchment(1, light=0.75)
    c = ink_text(c, reveal_rtl(text_mask([TITLE], 130, H * 0.46), 0.62), 1)
    c = ink_blot(c, W * 0.66, H * 0.72, 34, 4)
    r = np.sqrt((xx - W * .45) ** 2 + (yy - H * .45) ** 2) / W
    c *= np.clip(1.15 - r * 1.6, 0.15, 1)[..., None]
    frames.append(c)
    # 2 verse: illuminated initial, verse written word by word
    c = parchment(2)
    ls = line_masks(VERSE, 66, H * 0.50, gap=1.75)
    lines_txt = [VERSE[0][2:]] + VERSE[1:]  # first letter (with its hiriq) becomes the illuminated initial
    ls[0] = text_mask([lines_txt[0]], 66, H * 0.50 - 66 * 1.75, cx=W / 2 - 45)
    for i, (m, frac) in enumerate(zip(ls, (1, 1, 0.55))):
        c = ink_text(c, reveal_rtl(m, frac), 10 + i)
    cols = np.flatnonzero(ls[0].max(0) > .1)
    c = illuminated_initial(c, "י", cols[-1] + 100, H * 0.50 - 66 * 1.75)
    c = ink_blot(c, W * 0.30, H * 0.83, 22, 7, 0.9)
    frames.append(c)
    # 3 chorus / drop: gold-leaf line over an exploding ink splash, burning edges
    c = parchment(3, light=1.05)
    c = ink_blot(c, W / 2, H * 0.48, 230, 11)
    c = gold_fill(c, text_mask(WISE, 150, H * 0.48), sparkle_seed=5)
    c = embers(c, 4, 160, (0, H * .25))
    c = embers(c, 5, 160, (H * .75, H))
    frames.append(c)
    # 4 ending: sealed in red wax
    c = parchment(4, light=0.95)
    c = ink_text(c, text_mask(SEALED, 70, H * 0.36, gap=1.6), 20)
    c = wax_seal(c, W / 2, H * 0.72, 125)
    frames.append(c)
    return frames


# ---------------------------------------------------------------- B: neon Jerusalem

MAGENTA = np.array([255, 40, 170], np.float32)
CYAN = np.array([0, 235, 255], np.float32)
PURPLE = np.array([150, 60, 255], np.float32)
HORIZON = int(H * 0.60)


def neon(col, mask, color, core=0.9, inner=1.6, outer=1.1, flicker=1.0):
    col += color * (blur(mask, 18) * outer * flicker)[..., None]
    col += color * (blur(mask, 5) * inner * flicker)[..., None]
    white = np.array([255, 250, 255], np.float32) * 0.6 + color * 0.4
    col = col * (1 - (mask * core * flicker)[..., None]) + white * (mask * core * flicker)[..., None]
    return col


def outline_mask(mask, width=4):
    b = blur(mask, width)
    return np.clip((b - 0.15) * 3, 0, 1) * np.clip((0.85 - b) * 3, 0, 1) * 2


def skyline():
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    hz = HORIZON
    pts = [(0, hz)]
    x = 0
    rng = np.random.default_rng(3)

    def wall(x0, x1, top):
        p = [(x0, top)]
        for cx in np.arange(x0, x1, 22):
            p += [(cx, top), (cx, top - 12), (cx + 12, top - 12), (cx + 12, top)]
        return p + [(x1, top)]

    pts += wall(0, 330, hz - 60)
    pts += [(330, hz - 60), (330, hz - 210), (345, hz - 210), (345, hz - 225), (375, hz - 225), (375, hz - 210),
            (390, hz - 210), (390, hz - 60)]  # Tower of David
    pts += wall(390, 640, hz - 75)
    # houses with small domes
    x = 640
    for wd, ht in ((70, 110), (90, 95), (60, 125)):
        pts += [(x, hz - ht)]
        for a in np.linspace(np.pi, 0, 9):
            pts.append((x + wd / 2 + np.cos(a) * wd * 0.3, hz - ht - np.sin(a) * wd * 0.3))
        pts += [(x + wd, hz - ht)]
        x += wd
    # Dome of the Rock
    x0 = 870
    pts += [(x0, hz - 80), (x0, hz - 150), (x0 + 30, hz - 165), (x0 + 220, hz - 165), (x0 + 250, hz - 150),
            (x0 + 250, hz - 80)]
    pts = pts[:-1] + [(x0 + 70, hz - 165), (x0 + 70, hz - 195)]
    for a in np.linspace(np.pi, 0, 25):
        pts.append((x0 + 125 + np.cos(a) * 58, hz - 195 - np.sin(a) * 75))
    pts += [(x0 + 180, hz - 195), (x0 + 180, hz - 165), (x0 + 250, hz - 150), (x0 + 250, hz - 80)]
    pts += wall(x0 + 250, 1400, hz - 70)
    pts += [(1400, hz - 70), (1400, hz - 170), (1415, hz - 185), (1430, hz - 170), (1430, hz - 70)]  # minaret-ish tower
    pts += wall(1430, 1650, hz - 58)
    x = 1650
    while x < W:
        wd, ht = rng.uniform(50, 90), rng.uniform(70, 120)
        pts += [(x, hz - ht), (x + wd, hz - ht)]
        x += wd
    pts += [(W, hz), (0, hz)]
    d.polygon(pts, fill=255)
    sil = np.asarray(m, np.float32) / 255
    dome = Image.new("L", (W, H), 0)
    ImageDraw.Draw(dome).pieslice([x0 + 67, hz - 270, x0 + 183, hz - 120], 180, 360, fill=255)
    dm = np.asarray(dome, np.float32) / 255
    # spire on the dome
    sp = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sp).line([(x0 + 125, hz - 270), (x0 + 125, hz - 300)], fill=255, width=4)
    return sil, dm, np.asarray(sp, np.float32) / 255


def synth_scene(sun_rise=1.0, pulse=0.0, grid_phase=0.3, grid_flash=0.0, seed=0):
    t = np.clip(yy / HORIZON, 0, 1)
    sky = (np.array([8, 0, 22], np.float32) * (1 - t[..., None]) + np.array([90, 15, 100], np.float32) * t[..., None])
    col = sky.copy()
    rng = np.random.default_rng(seed)
    for _ in range(260):
        x, y = rng.uniform(0, W), rng.uniform(0, HORIZON * 0.8)
        col[int(y), int(x)] += rng.uniform(80, 220)
    # sun with stripes
    R = 250 * (1 + 0.04 * pulse)
    scx, scy = W / 2, HORIZON - 40 + (1 - sun_rise) * 260
    rr = np.sqrt((xx - scx) ** 2 + (yy - scy) ** 2)
    disk = np.clip((R - rr) / 2, 0, 1) * (yy < HORIZON)
    u = np.clip((yy - (scy - R)) / (2 * R), 0, 1)
    sun_col = np.array([255, 225, 90], np.float32) * (1 - u[..., None]) + np.array([255, 30, 140], np.float32) * u[..., None]
    k = np.clip((yy - (scy - R * 0.1)) / R, 0, 1)
    stripes = ((np.sin((yy - scy) * 0.16) * 0.5 + 0.5) > k * 0.85) | (yy < scy - R * 0.1)
    disk *= stripes
    col += blur(disk, 40)[..., None] * np.array([255, 60, 150], np.float32) * (0.8 + 0.6 * pulse)
    col = col * (1 - disk[..., None]) + sun_col * disk[..., None]
    # skyline
    sil, dm, sp = skyline()
    col = col * (1 - sil[..., None]) + np.array([10, 0, 20], np.float32) * sil[..., None]
    col = neon(col, outline_mask(sil, 2), CYAN, core=0.8, inner=1.2, outer=0.7)
    col = neon(col, outline_mask(dm, 2) + sp, np.array([255, 200, 60], np.float32), core=0.9, inner=1.4, outer=0.9)
    # perspective grid floor
    floor = yy >= HORIZON
    col[floor] = np.array([12, 0, 24], np.float32)
    g = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(g)
    vx = W / 2
    for i in range(-30, 31):
        d.line([(vx, HORIZON), (vx + i * 140, H + 400)], fill=255, width=2)
    for k in range(1, 40):
        z = (k - grid_phase) * 0.35
        if z <= 0:
            continue
        y = HORIZON + 140 / z
        if y > H:
            continue
        d.line([(0, y), (W, y)], fill=255, width=2 if y > HORIZON + 30 else 1)
    gm = np.asarray(g, np.float32) / 255 * floor
    fade = np.clip((yy - HORIZON) / 140, 0.25, 1)
    col = neon(col, gm * fade, MAGENTA, core=0.7, inner=1.5 + 2 * grid_flash, outer=0.9 + 1.5 * grid_flash)
    col += np.exp(-((yy - HORIZON) / 14) ** 2)[..., None] * MAGENTA * 0.9
    return col


def vhs(col, seed, glitch=0.0, osd=None):
    rng = np.random.default_rng(seed)
    out = col.copy()
    sh = int(3 + 14 * glitch)
    out[..., 0] = np.roll(col[..., 0], sh, 1)
    out[..., 2] = np.roll(col[..., 2], -sh, 1)
    for _ in range(int(3 + 12 * glitch)):
        y0 = int(rng.uniform(0, H - 40))
        hgt = int(rng.uniform(4, 40 * (0.3 + glitch)))
        out[y0:y0 + hgt] = np.roll(out[y0:y0 + hgt], int(rng.normal(0, 25 + 80 * glitch)), 1)
    out *= (1 - 0.18 * (np.arange(H) % 3 == 0))[:, None, None]
    out += rng.normal(0, 7, (H, W, 1)).astype(np.float32)
    if osd:
        im = to_img(out)
        d = ImageDraw.Draw(im)
        from PIL import ImageFont
        f = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf", 38)
        d.text((70, 60), osd, font=f, fill=(235, 235, 235))
        out = np.asarray(im, np.float32)
    return out


def concept_b():
    frames = []
    # 1 opening: sun rising, title flickering on
    c = synth_scene(sun_rise=0.55, grid_phase=0.1, seed=1)
    words = TITLE.split()
    c = neon(c, text_mask([words[0]], 140, H * 0.30, cx=W / 2 + 175), MAGENTA)
    c = neon(c, text_mask([words[1]], 140, H * 0.30, cx=W / 2 - 300), MAGENTA, flicker=0.35)
    frames.append(vhs(c, 1, 0.1, "PLAY ▶ 00:18"))
    # 2 verse: cyan neon words over the skyline
    c = synth_scene(sun_rise=1.0, pulse=0.6, grid_phase=0.55, seed=2)
    c *= 0.85
    c = neon(c, text_mask(VERSE, 66, H * 0.22, gap=1.45), CYAN)
    frames.append(vhs(c, 2, 0.05, "PLAY ▶ 01:12"))
    # 3 drop: grid flash, magenta slam, heavy glitch
    c = synth_scene(sun_rise=1.0, pulse=1.0, grid_phase=0.8, grid_flash=1.0, seed=3)
    c = neon(c, text_mask(WISE, 165, H * 0.30), MAGENTA, inner=2.2, outer=1.8)
    frames.append(vhs(c, 3, 1.0))
    # 4 ending: neon sign box with a Star of David
    c = synth_scene(sun_rise=0.8, pulse=0.3, grid_phase=0.2, seed=4) * 0.55
    box = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(box)
    d.rounded_rectangle([W / 2 - 520, H * 0.08, W / 2 + 520, H * 0.50], radius=40, outline=255, width=5)
    hexagram(d, W / 2, H * 0.14, 34, 4)
    c = neon(c, np.asarray(box, np.float32) / 255, PURPLE)
    c = neon(c, text_mask(SEALED, 76, H * 0.32, gap=1.5), CYAN)
    frames.append(vhs(c, 4, 0.15, "STOP ■ 02:58"))
    return frames


# ---------------------------------------------------------------- C: cosmic

def nebula(seed, bright=1.0):
    """Soft clouds with dark gaps: large smooth noise, shaped, with fine filaments only inside."""
    big, mid, fine, dust = noise(320, seed), noise(150, seed + 1), noise(45, seed + 2), noise(200, seed + 3)
    cloud = np.clip((big - 0.42) * 2.4, 0, 1) ** 1.6
    teal = np.clip((mid - 0.5) * 2.6, 0, 1) ** 2
    fil = cloud * (0.6 + 0.8 * fine)
    col = (np.array([120, 45, 190], np.float32) * fil[..., None] * 1.3
           + np.array([25, 160, 200], np.float32) * (teal * fil)[..., None] * 1.6
           + np.array([240, 80, 160], np.float32) * (np.clip(fil * fine - 0.3, 0, 1) ** 1.5)[..., None] * 1.4)
    col *= (0.3 + 0.8 * np.clip((dust - 0.3) * 2, 0, 1))[..., None] * bright
    col += np.array([3, 2, 10], np.float32)
    return col


def starfield(col, seed, n=2600, spikes=6):
    rng = np.random.default_rng(seed)
    acc = np.zeros((H, W), np.float32)
    xs, ys = rng.uniform(0, W, n).astype(int), rng.uniform(0, H, n).astype(int)
    np.add.at(acc, (ys, xs), rng.pareto(2.2, n).clip(0, 6) * 0.35 + 0.15)
    acc = acc + blur(acc, 1.2) * 2
    for _ in range(spikes):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        b = rng.uniform(0.5, 1.2)
        acc += b * (np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / 8)
                    + 0.4 * np.exp(-((xx - x) ** 2) / 1.5 - ((yy - y) ** 2) / 500)
                    + 0.4 * np.exp(-((yy - y) ** 2) / 1.5 - ((xx - x) ** 2) / 500))
    col += acc[..., None] * np.array([235, 240, 255], np.float32) * 255 / 4
    return col


def constellation(col, mask, seed, color=np.array([255, 225, 160], np.float32), step=17):
    """Lyrics as star constellations: stars sampled on the glyphs, linked to neighbours."""
    rng = np.random.default_rng(seed)
    # darken the sky behind the words, then a soft glow and a crisp pale core keep them readable
    col *= (1 - blur(mask, 22) * 0.75)[..., None]
    col += blur(mask, 12)[..., None] * color * 0.45
    col += blur(mask, 3)[..., None] * color * 0.5
    col = col * (1 - mask[..., None] * 0.6) + color * mask[..., None] * 0.6
    pts = []
    for y in range(0, H, step):
        for x in range(0, W, step):
            cell = mask[y:y + step, x:x + step]
            if cell.max() > 0.6 and rng.random() < 0.55:
                iy, ix = np.unravel_index(np.argmax(cell + rng.random(cell.shape) * 0.3), cell.shape)
                pts.append((x + ix, y + iy))
    pts = np.array(pts, np.float32)
    lines = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(lines)
    for i, p in enumerate(pts):
        dist = np.sqrt(((pts - p) ** 2).sum(1))
        j = np.argsort(dist)[1]
        if dist[j] < step * 2.2:
            d.line([tuple(p), tuple(pts[j])], fill=120, width=1)
    lm = np.asarray(lines, np.float32) / 255
    col += lm[..., None] * np.array([200, 220, 255], np.float32) * 0.5
    acc = np.zeros((H, W), np.float32)
    np.add.at(acc, (pts[:, 1].astype(int), pts[:, 0].astype(int)), rng.uniform(0.6, 1.4, len(pts)))
    col += (blur(acc, 1.2) * 7 + blur(acc, 4) * 10)[..., None] * np.array([255, 250, 235], np.float32)
    return col


def galaxy(col, cx, cy, R, rot, seed):
    rng = np.random.default_rng(seed)
    n = 220000
    arm = rng.integers(0, 3, n)
    r = (rng.random(n) ** 1.6) * 1.05
    th = np.log(r + 0.05) * 2.6 + arm * 2 * np.pi / 3 + rng.normal(0, 0.35, n) * (0.25 + r) + rot
    x = np.cos(th) * r * R
    y = np.sin(th) * r * R * 0.42
    ca, sa = np.cos(-0.3), np.sin(-0.3)
    px, py = cx + x * ca - y * sa, cy + x * sa + y * ca
    ok = (px >= 0) & (px < W) & (py >= 0) & (py < H)
    warm = np.array([255, 225, 175], np.float32)
    cool = np.array([120, 165, 255], np.float32)
    for colr, sel in ((warm, r < 0.3), (cool, r >= 0.3)):
        acc = np.zeros((H, W), np.float32)
        s = ok & sel
        np.add.at(acc, (py[s].astype(int), px[s].astype(int)), 1.0)
        col += (acc * 5 + blur(acc, 3) * 30 + blur(acc, 16) * 60)[..., None] * colr / 255
    core = np.exp(-(((xx - cx) / (R * 0.09)) ** 2 + ((yy - cy) / (R * 0.05)) ** 2))
    col += core[..., None] * np.array([255, 235, 200], np.float32) * 0.9
    return col


def supernova(col, cx, cy, R):
    rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    col += np.exp(-(rr / (R * 0.08)) ** 2)[..., None] * 255 * 1.5
    col += np.exp(-((rr - R) / (R * 0.04)) ** 2)[..., None] * np.array([150, 220, 255], np.float32) * 0.8
    col += np.exp(-((rr - R * 0.6) / (R * 0.08)) ** 2)[..., None] * np.array([255, 120, 200], np.float32) * 0.35
    col += (np.exp(-((xx - cx) ** 2) / 4 - ((yy - cy) ** 2) / (R * R * 0.6))
            + np.exp(-((yy - cy) ** 2) / 4 - ((xx - cx) ** 2) / (R * R * 0.6)))[..., None] * 255 * 0.8
    return col


def eclipse(col, cx, cy, R, seed):
    rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    an = np.arctan2(yy - cy, xx - cx)
    rng = np.random.default_rng(seed)
    streak = sum(rng.uniform(0.2, 1) * (0.5 + 0.5 * np.sin(k * an + rng.uniform(0, 6.3))) ** 6 for k in range(5, 40, 3))
    corona = np.exp(-np.clip(rr - R, 0, None) / (R * 0.35)) * (0.5 + 0.4 * streak / 5) * (rr > R)
    col += corona[..., None] * np.array([255, 235, 200], np.float32) * 1.4
    col *= (rr > R)[..., None]
    bx, by = cx + R * np.cos(-0.8), cy + R * np.sin(-0.8)  # diamond ring
    col += np.exp(-((xx - bx) ** 2 + (yy - by) ** 2) / 60)[..., None] * 255 * 2
    col += np.exp(-((yy - by) ** 2) / 3 - ((xx - bx) ** 2) / 20000)[..., None] * 255 * 0.6
    return col


def concept_c():
    frames = []
    # 1 opening: the verse that gives the concept its name, title as a constellation
    c = starfield(nebula(1, 0.8), 1)
    c = constellation(c, text_mask([TITLE], 150, H * 0.46), 1)
    small = text_mask([VERSE_312], 40, H * 0.66, light=True)
    c += (small + blur(small, 4))[..., None] * np.array([200, 210, 255], np.float32) * 0.8
    frames.append(c)
    # 2 verse: words appear as constellations
    c = starfield(nebula(2, 0.9), 2)
    c = constellation(c, text_mask(VERSE, 74, H * 0.47, gap=1.6), 2, np.array([170, 210, 255], np.float32), step=14)
    frames.append(c)
    # 3 chorus: rotating galaxy, supernova on the beat
    c = starfield(nebula(3, 0.7), 3, spikes=8)
    c = galaxy(c, W / 2, H * 0.40, 950, 0.4, 3)
    c = galaxy(c, W / 2, H * 0.40, 950, 0.4, 3)  # second pass doubles the arm brightness
    c = supernova(c, W * 0.84, H * 0.22, 150)
    c = constellation(c, text_mask(WISE, 140, H * 0.80), 3, step=16)
    frames.append(c)
    # 4 ending: the sealed sky – total eclipse
    c = starfield(nebula(4, 0.5), 4, spikes=6)
    c = eclipse(c, W / 2, H * 0.36, 150, 4)
    c = constellation(c, text_mask(SEALED, 64, H * 0.78, gap=1.55), 4, step=13)
    frames.append(c)
    return frames


# ---------------------------------------------------------------- contact sheet

def sheet(frames, title, subtitle, labels, path):
    tw, th = 930, 523
    S = Image.new("RGB", (1920, 150 + 2 * (th + 70)), (14, 12, 18))
    d = ImageDraw.Draw(S)
    d.text((1880, 40), title, font=font(64), fill=(245, 225, 180), anchor="ra", direction="rtl")
    d.text((1880, 112), subtitle, font=font(30, True), fill=(200, 200, 210), anchor="ra", direction="rtl")
    for i, (fr, lab) in enumerate(zip(frames, labels)):
        col, row = 1 - i % 2, i // 2  # right to left
        x, y = 20 + col * (tw + 20), 150 + row * (th + 70)
        S.paste(to_img(fr).resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + tw - 8, y + th + 12), lab, font=font(32, True), fill=(220, 220, 230), anchor="ra", direction="rtl")
    S.save(path, quality=92)


CONCEPTS = {
    "a": (concept_a, "א. מגילה ודיו",
          "קלף עתיק, המילים נכתבות בדיו אות אחר אות, טיפות דיו על הביט, זהב מאויר, וחותם שעווה בסוף",
          ["פתיחה: אור נר, הכותרת נכתבת", "בית: אות פתיחה מאוירת בזהב", "פזמון/דרופ: התפוצצות דיו ועלי זהב",
           "סיום: נחתם בשעווה אדומה"]),
    "b": (concept_b, "ב. ניאון ירושלים",
          "סינת'ווייב רטרו: קו הרקיע של ירושלים בניאון, שמש פועמת, רשת שזזה בקצב, גליץ' VHS על המכות",
          ["פתיחה: שמש עולה, הכותרת מהבהבת", "בית: מילים בניאון תכלת", "דרופ: הבזק רשת וגליץ' כבד",
           "סיום: שלט ניאון עם מגן דוד"]),
    "c": (concept_c, "ג. כזוהר הרקיע",
          "על פי דניאל יב, ג: ערפיליות וכוכבים, המילים נוצרות כקבוצות כוכבים, גלקסיה מסתובבת וליקוי בסוף",
          ["פתיחה: הכותרת כקבוצת כוכבים", "בית: מילים מכוכבים", "פזמון: גלקסיה וסופרנובה על הביט",
           "סיום: ליקוי חמה, הדברים נחתמים"]),
}


def main():
    out = sys.argv[1]
    which = sys.argv[2] if len(sys.argv) > 2 else "abc"
    os.makedirs(out, exist_ok=True)
    for k in which:
        fn, title, sub, labels = CONCEPTS[k]
        frames = fn()
        for i, fr in enumerate(frames):
            to_img(fr).save(os.path.join(out, f"{k}{i + 1}.png"))
        sheet(frames, title, sub, labels, os.path.join(out, f"mockup_{k}.jpg"))
        print("done", k, flush=True)


if __name__ == "__main__":
    main()
