#!/usr/bin/env python3
"""Animated "fire & gold" lyric video for the single (Daniel 12:9-10).

Usage:
    python3 make_clip.py AUDIO OUT.mp4 --aspect 16x9|9x16 [--start S --end S] [--jobs N]
    python3 make_clip.py AUDIO frames_dir --aspect 16x9 --stills 5,40,100,140

Background, sparks and light are rendered at half resolution and upscaled;
the lyrics are composited at full resolution so they stay crisp.
"""
import argparse
import os
import subprocess
import sys
import tempfile
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FPS = 30
FONT = "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf"
FONT_LIGHT = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"

# Lyrics: (show_from, show_until, lines, kind). Times come from the timed
# lyrics embedded in the track, extended so a line stays until the next one.
VERSE = ["יִתְבָּרְרוּ וְיִתְלַבְּנוּ וְיִצָּרְפוּ רַבִּים",
         "וְהִרְשִׁיעוּ רְשָׁעִים",
         "וְלֹא יָבִינוּ כָּל רְשָׁעִים"]
WISE = ["וְהַמַּשְׂכִּלִים יָבִינוּ"]
SEALED = ["כִּי סְתֻמִים וַחֲתֻמִים", "הַדְּבָרִים עַד עֵת קֵץ"]
SOURCE = ["דָּנִיֵּאל י״ב"]
TITLE = ["וְהַמַּשְׂכִּלִים יָבִינוּ"]

LYRICS = [
    (6.0, 27.0, TITLE, "title"),
    (8.5, 27.0, SOURCE, "subtitle"),
    (33.4, 48.6, VERSE, "verse"),
    (49.07, 63.0, WISE, "wise"),
    (81.38, 96.7, VERSE, "verse"),
    (97.18, 104.6, WISE, "wise"),
    (105.08, 121.0, WISE, "wise"),
    (137.15, 155.0, SEALED, "sealed"),
    (156.5, 166.5, SOURCE, "caption"),
]

# Scene keyframes: time -> (heat, white, seal, master)
KEYS = [
    (0.0, (0.02, 0.0, 0.0, 0.0)),
    (2.5, (0.10, 0.0, 0.0, 1.0)),
    (20.0, (0.35, 0.0, 0.0, 1.0)),
    (32.0, (0.50, 0.0, 0.0, 1.0)),
    (34.0, (0.85, 0.0, 0.0, 1.0)),
    (48.0, (0.85, 0.0, 0.0, 1.0)),
    (50.0, (0.70, 0.45, 0.0, 1.0)),
    (60.0, (0.70, 0.45, 0.0, 1.0)),
    (64.0, (0.55, 0.10, 0.0, 1.0)),
    (79.0, (0.60, 0.05, 0.0, 1.0)),
    (82.0, (0.95, 0.0, 0.0, 1.0)),
    (95.0, (1.00, 0.15, 0.0, 1.0)),
    (97.5, (0.80, 0.90, 0.0, 1.0)),
    (120.0, (0.80, 0.90, 0.0, 1.0)),
    (125.0, (0.60, 0.40, 0.0, 1.0)),
    (135.0, (0.55, 0.30, 0.0, 1.0)),
    (138.0, (0.50, 0.35, 0.0, 1.0)),
    (152.0, (0.35, 0.35, 1.0, 1.0)),
    (160.0, (0.20, 0.20, 1.0, 1.0)),
    (168.0, (0.05, 0.05, 1.0, 0.6)),
    (171.2, (0.00, 0.00, 1.0, 0.0)),
]

FIRE_STOPS = [
    (0.00, (0, 0, 0)),
    (0.22, (30, 3, 0)),
    (0.42, (120, 20, 0)),
    (0.62, (220, 80, 8)),
    (0.78, (255, 160, 35)),
    (0.90, (255, 220, 120)),
    (1.00, (255, 250, 230)),
]

EMBER = np.array([255, 120, 30], np.float32)
GOLD = np.array([255, 215, 120], np.float32)
WHITE_GOLD = np.array([255, 246, 225], np.float32)


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def scene(t):
    times = [k[0] for k in KEYS]
    vals = np.array([k[1] for k in KEYS], np.float32)
    i = np.searchsorted(times, t, side="right")
    if i == 0:
        return vals[0]
    if i >= len(times):
        return vals[-1]
    t0, t1 = times[i - 1], times[i]
    u = float(smoothstep((t - t0) / (t1 - t0)))
    return vals[i - 1] * (1 - u) + vals[i] * u


# ---------------------------------------------------------------- audio

def analyse_audio(path, n_frames):
    sr = 48000
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
        check=True, capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    hop = sr // FPS
    win = 4096
    pad = np.pad(x, (win, win + hop * n_frames))
    window = np.hanning(win).astype(np.float32)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    bass_bins = (freqs > 30) & (freqs < 160)
    rms = np.zeros(n_frames, np.float32)
    bass = np.zeros(n_frames, np.float32)
    for f in range(n_frames):
        c = win + f * hop
        seg = pad[c - win // 2:c + win // 2]
        rms[f] = np.sqrt(np.mean(seg * seg))
        spec = np.abs(np.fft.rfft(seg * window))
        bass[f] = spec[bass_bins].mean()

    def norm(a):
        return np.clip(a / (np.percentile(a, 97) + 1e-9), 0, 1.3)

    rms, bass = norm(rms), norm(bass)
    # attack/release envelope for the loudness, onset pulse for the bass
    env = np.zeros_like(rms)
    slow = np.zeros_like(bass)
    e = s = 0.0
    for f in range(n_frames):
        e = e + (rms[f] - e) * (0.5 if rms[f] > e else 0.06)
        s = s + (bass[f] - s) * 0.05
        env[f], slow[f] = e, s
    pulse = np.clip((bass - slow) * 2.5, 0, 1)
    p = 0.0
    for f in range(n_frames):
        p = max(pulse[f], p * 0.85)
        pulse[f] = p
    return env, pulse


# ---------------------------------------------------------------- background

def periodic_noise(h, w, scale, rng):
    """Smooth tileable noise in [0,1] via FFT low-pass of white noise."""
    n = rng.standard_normal((h, w)).astype(np.float32)
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    filt = np.exp(-(fx ** 2 + fy ** 2) * (scale ** 2))
    out = np.fft.irfft2(np.fft.rfft2(n) * filt, s=(h, w)).astype(np.float32)
    out -= out.min()
    out /= out.max()
    return out


def scroll_y(tex, offset, out_h):
    """Sample rows [offset, offset+out_h) of a vertically tileable texture with linear interp."""
    h = tex.shape[0]
    o = offset % h
    i = int(o)
    fr = o - i
    idx = (np.arange(out_h) + i) % h
    a = tex[idx]
    b = tex[(idx + 1) % h]
    return a * (1 - fr) + b * fr


class Renderer:
    def __init__(self, W, H, env, pulse):
        self.W, self.H = W, H
        self.w, self.h = W // 2, H // 2
        self.env, self.pulse = env, pulse
        rng = np.random.default_rng(7)
        w, h = self.w, self.h
        # Noise is generated at quarter res and sampled at half res for speed.
        self.nw, self.nh = w // 2, h // 2
        self.tex = [periodic_noise(self.nh * 2, self.nw, s, rng) for s in (28.0, 12.0, 5.0)]
        self.warp = periodic_noise(self.nh * 2, self.nw, 20.0, rng)
        lut_x = np.linspace(0, 1, 256)
        stops = np.array([s[0] for s in FIRE_STOPS])
        cols = np.array([s[1] for s in FIRE_STOPS], np.float32)
        self.lut = np.stack([np.interp(lut_x, stops, cols[:, c]) for c in range(3)], 1).astype(np.float32)

        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        self.yn = yy / h
        cx, cy = w / 2, h * (0.46 if W > H else 0.47)
        dx, dy = xx - cx, yy - cy
        self.r = np.sqrt(dx * dx + dy * dy) / min(w, h)
        self.ang = np.arctan2(dy, dx)
        ry_src = h * -0.15
        self.ray_ang = np.arctan2(yy - ry_src, xx - cx)
        self.ray_r = np.sqrt((xx - cx) ** 2 + (yy - ry_src) ** 2) / max(w, h)
        vx = (xx / w - 0.5) * 2
        vy = (yy / h - 0.5) * 2
        self.vignette = np.clip(1.0 - 0.45 * (vx * vx * 0.6 + vy * vy * 0.8), 0, 1)[..., None]
        self.kernels = {}
        for rad in (1, 2, 3, 5, 8):
            k = np.arange(-rad * 2, rad * 2 + 1, dtype=np.float32)
            g = np.exp(-(k[:, None] ** 2 + k[None, :] ** 2) / (2 * (rad * 0.7) ** 2))
            self.kernels[rad] = g.astype(np.float32)
        self.font_cache = {}
        self.blocks = [self.build_block(*l) for l in LYRICS]
        self.sparks = None

    # ------------------------------------------------------------ sparks
    def spark_step(self, f, heat, white, energy):
        """Advance particles one frame. Spawning is seeded by frame index so
        chunks rendered in parallel agree after a warm-up."""
        rng = np.random.default_rng(1000 + f)
        if self.sparks is None:
            self.sparks = np.zeros((0, 7), np.float32)  # x y vx vy life max size
        rate = 1.0 + 9.0 * heat + 10.0 * energy * heat + 5.0 * white
        n = rng.poisson(rate)
        if n:
            new = np.zeros((n, 7), np.float32)
            new[:, 0] = rng.uniform(0, 1, n)
            new[:, 1] = rng.uniform(0.85, 1.05, n)
            new[:, 2] = rng.normal(0, 0.0006, n)
            new[:, 3] = -rng.uniform(0.002, 0.007, n) * (0.7 + heat)
            new[:, 5] = rng.uniform(1.5, 4.0, n) * FPS
            new[:, 6] = rng.choice([1, 1, 1, 2, 2, 3], n)
            self.sparks = np.concatenate([self.sparks, new])
        s = self.sparks
        s[:, 2] += rng.normal(0, 0.00025, len(s)) + np.sin(s[:, 1] * 9 + f * 0.03) * 0.00006
        s[:, 0] += s[:, 2]
        s[:, 1] += s[:, 3]
        s[:, 4] += 1
        self.sparks = s[(s[:, 4] < s[:, 5]) & (s[:, 1] > -0.05)]

    def spark_layer(self, f):
        w, h = self.w, self.h
        buf = np.zeros((h, w), np.float32)
        rng = np.random.default_rng(5000 + f)
        flick = rng.uniform(0.6, 1.0, len(self.sparks))
        for (x, y, _, _, life, mx, size), fl in zip(self.sparks, flick):
            k = self.kernels[int(size)]
            kr = k.shape[0] // 2
            px, py = int(x * w), int(y * h)
            if px < -kr or py < -kr or px >= w + kr or py >= h + kr:
                continue
            u = life / mx
            a = fl * min(1.0, u * 8) * (1 - u) ** 1.2 * 1.6
            x0, y0 = max(0, px - kr), max(0, py - kr)
            x1, y1 = min(w, px + kr + 1), min(h, py + kr + 1)
            buf[y0:y1, x0:x1] += a * k[y0 - py + kr:y1 - py + kr, x0 - px + kr:x1 - px + kr]
        return buf

    # ------------------------------------------------------------ text
    def font(self, size, light=False):
        key = (size, light)
        if key not in self.font_cache:
            self.font_cache[key] = ImageFont.truetype(
                FONT_LIGHT if light else FONT, size, layout_engine=ImageFont.Layout.RAQM)
        return self.font_cache[key]

    def wrap(self, lines, font, max_w):
        out = []
        for line in lines:
            words, cur = line.split(), ""
            for wd in words:
                cand = (cur + " " + wd).strip()
                if cur and font.getlength(cand, direction="rtl") > max_w:
                    out.append(cur)
                    cur = wd
                else:
                    cur = cand
            out.append(cur)
        return out

    def build_block(self, t0, t1, lines, kind):
        W, H = self.W, self.H
        portrait = H > W
        base = {"verse": 74, "wise": 104, "sealed": 88, "caption": 46,
                "title": 120, "subtitle": 46}[kind]
        size = int(base * (W / 1920 if not portrait else 1.0 if kind != "verse" else 0.92))
        max_w = W * (0.86 if portrait else 0.8)
        light = kind in ("caption", "subtitle")
        font = self.font(size, light=light)
        wrapped = self.wrap(lines, font, max_w)
        while max(font.getlength(l, direction="rtl") for l in wrapped) > max_w:
            size = int(size * 0.94)
            font = self.font(size, light=light)
            wrapped = self.wrap(lines, font, max_w)
        line_h = int(size * 1.55)
        pad = int(size * 0.9)
        bw = int(max(font.getlength(l, direction="rtl") for l in wrapped)) + pad * 2
        bh = line_h * len(wrapped) + pad * 2
        masks = []
        for i, l in enumerate(wrapped):
            m = Image.new("L", (bw, bh), 0)
            ImageDraw.Draw(m).text((bw / 2, pad + line_h * i + line_h / 2), l, font=font,
                                   fill=255, anchor="mm", direction="rtl")
            masks.append(m)
        sharp = [np.asarray(m, np.float32) / 255 for m in masks]
        glow = [np.asarray(m.filter(ImageFilter.GaussianBlur(size * 0.28)), np.float32) / 255
                for m in masks]
        halo = [np.asarray(m.filter(ImageFilter.GaussianBlur(size * 0.9)), np.float32) / 255
                for m in masks]
        if kind == "caption":
            cy = H * 0.5
        elif kind == "title":
            cy = H * (0.44 if portrait else 0.42)
        elif kind == "subtitle":
            cy = H * (0.44 if portrait else 0.42) + size * 3.2
        elif kind == "sealed":
            cy = H * (0.47 if portrait else 0.46)
        else:
            cy = H * (0.46 if portrait else 0.45)
        return dict(t0=t0, t1=t1, kind=kind, sharp=sharp, glow=glow, halo=halo,
                    x=int(W / 2 - bw / 2), y=int(cy - bh / 2), size=size)

    def draw_text(self, img, t, f):
        pulse = float(self.pulse[f])
        for b in self.blocks:
            if t < b["t0"] - 0.1 or t > b["t1"] + 0.1:
                continue
            n = len(b["sharp"])
            dur = b["t1"] - b["t0"]
            for i in range(n):
                start = b["t0"] + i * 0.6
                a_in = smoothstep((t - start) / 1.1)
                a_out = smoothstep((b["t1"] - t) / 1.2)
                a = float(a_in * a_out)
                if a <= 0.003:
                    continue
                prog = float(np.clip((t - b["t0"]) / max(dur, 1), 0, 1))
                if b["kind"] == "verse":   # refined in the fire: ember -> white gold
                    col = EMBER * (1 - prog) + WHITE_GOLD * prog
                    gcol = np.array([255, 90, 10], np.float32) * (1 - prog) + GOLD * prog
                elif b["kind"] in ("caption", "subtitle"):
                    col, gcol = GOLD * 0.95, np.array([200, 110, 30], np.float32)
                elif b["kind"] == "title":   # glows up from ember to gold
                    u = float(smoothstep((t - b["t0"]) / 6.0))
                    col = EMBER * (1 - u) + GOLD * u
                    gcol = np.array([255, 90, 10], np.float32) * (1 - u) + GOLD * u
                else:
                    col, gcol = WHITE_GOLD, GOLD
                rise = int((1 - a_in) * b["size"] * 0.35)
                x, y = b["x"], b["y"] + rise
                sh, gl, ha = b["sharp"][i], b["glow"][i], b["halo"][i]
                hh, ww = sh.shape
                y0, x0 = max(0, y), max(0, x)
                y1, x1 = min(self.H, y + hh), min(self.W, x + ww)
                sy, sx = y0 - y, x0 - x
                sh = sh[sy:sy + y1 - y0, sx:sx + x1 - x0][..., None]
                gl = gl[sy:sy + y1 - y0, sx:sx + x1 - x0][..., None]
                ha = ha[sy:sy + y1 - y0, sx:sx + x1 - x0][..., None]
                reg = img[y0:y1, x0:x1]
                g_amt = (0.75 + 0.6 * pulse) * a
                reg *= 1 - 0.55 * ha * a          # darken behind text for legibility
                reg += gcol * (gl * 0.9 + ha * 0.35) * g_amt
                reg *= 1 - sh * a
                reg += col * sh * a

    # ------------------------------------------------------------ frame
    def frame(self, f):
        t = f / FPS
        heat, white, seal, master = (float(v) for v in scene(t))
        energy = float(self.env[f])
        pulse = float(self.pulse[f])
        w, h, nh = self.w, self.h, self.nh

        # fire field at quarter res, rising
        n1 = scroll_y(self.tex[0], t * 9.0, nh)
        n2 = scroll_y(self.tex[1], t * 22.0, nh)
        n3 = scroll_y(self.tex[2], t * 45.0, nh)
        wp = scroll_y(self.warp, t * 6.0, nh)
        turb = 0.5 * n1 + 0.32 * n2 + 0.18 * n3
        shift = ((wp - 0.5) * 18).astype(np.int32)
        cols = (np.arange(self.nw)[None, :] + shift) % self.nw
        turb = np.take_along_axis(turb, cols, 1)
        field = np.asarray(Image.fromarray(turb).resize((w, h), Image.BILINEAR))

        flame_h = 0.18 + 0.55 * heat + 0.12 * energy * heat
        prof = np.clip((self.yn - (1 - flame_h)) / flame_h, 0, 1) ** 1.3
        v = prof * (0.35 + 1.1 * field) + (field - 0.5) * 0.25 * heat
        v = v * (0.55 + 0.5 * heat + 0.25 * energy) + 0.1 * white
        idx = np.clip(v * 255, 0, 255).astype(np.uint8)
        img = self.lut[idx] * (0.35 + 0.65 * min(1.0, heat * 1.8 + white))

        # chorus light: rays + central bloom
        if white > 0.01:
            rays = 0.5 + 0.5 * np.sin(self.ray_ang * 22 + t * 0.35) * np.sin(self.ray_ang * 9 - t * 0.21)
            rays = rays ** 3 * np.exp(-self.ray_r * 1.6)
            bloom = np.exp(-(self.r / (0.42 + 0.05 * pulse)) ** 2)
            light = white * (rays * 0.55 + bloom * (0.45 + 0.25 * pulse))
            img += light[..., None] * np.array([255, 225, 170], np.float32)

        # seal ring that closes around the last line
        if seal > 0.001:
            R = 0.36 if self.W > self.H else 0.42
            ring = np.exp(-((self.r - R) / 0.008) ** 2) + 0.35 * np.exp(-((self.r - R) / 0.04) ** 2)
            ang01 = (self.ang + np.pi / 2) % (2 * np.pi) / (2 * np.pi)
            reveal = np.clip((seal * 1.05 - ang01) * 40, 0, 1)
            # taper the arc's starting end so its glow isn't cut by a hard radial edge
            reveal *= np.maximum(np.clip(ang01 * 25, 0, 1), smoothstep((seal - 0.9) / 0.1))
            inner = np.exp(-((self.r - R * 0.93) / 0.003) ** 2) * 0.5 * smoothstep(seal * 3 - 2)
            ringv = (ring * reveal + inner) * (0.8 + 0.4 * pulse)
            img += ringv[..., None] * np.array([255, 200, 100], np.float32)

        # sparks
        sp = self.spark_layer(f)
        img += sp[..., None] * np.array([255, 150, 45], np.float32)
        img += (sp ** 2)[..., None] * np.array([0, 60, 80], np.float32)

        img *= self.vignette
        np.clip(img, 0, 255, out=img)
        full = np.asarray(Image.fromarray(img.astype(np.uint8)).resize((self.W, self.H), Image.BILINEAR),
                          np.float32).copy()
        self.draw_text(full, t, f)
        full *= master
        return np.clip(full, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- driver

WARMUP = 5 * FPS


def render_chunk(args):
    W, H, env, pulse, f0, f1, out = args
    r = Renderer(W, H, env, pulse)
    for f in range(max(0, f0 - WARMUP), f0):
        t = f / FPS
        heat, white, _, _ = scene(t)
        r.spark_step(f, float(heat), float(white), float(env[f]))
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for f in range(f0, f1):
        t = f / FPS
        heat, white, _, _ = scene(t)
        r.spark_step(f, float(heat), float(white), float(env[f]))
        enc.stdin.write(r.frame(f).tobytes())
        if (f - f0) % 300 == 0:
            print(f"  [{os.path.basename(out)}] {f - f0}/{f1 - f0}", flush=True)
    enc.stdin.close()
    if enc.wait():
        raise RuntimeError("ffmpeg failed")
    return out


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    return float(out.stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("out")
    ap.add_argument("--aspect", default="16x9", choices=["16x9", "9x16"])
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float)
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    ap.add_argument("--stills", help="comma separated times; writes PNGs to OUT dir")
    a = ap.parse_args()

    W, H = (1920, 1080) if a.aspect == "16x9" else (1080, 1920)
    total = int(duration(a.audio) * FPS)
    print("analysing audio...", flush=True)
    env, pulse = analyse_audio(a.audio, total)

    if a.stills:
        os.makedirs(a.out, exist_ok=True)
        for ts in a.stills.split(","):
            f = int(float(ts) * FPS)
            r = Renderer(W, H, env, pulse)
            for g in range(max(0, f - WARMUP), f + 1):
                heat, white, _, _ = scene(g / FPS)
                r.spark_step(g, float(heat), float(white), float(env[g]))
            Image.fromarray(r.frame(f)).save(os.path.join(a.out, f"{a.aspect}_{float(ts):06.1f}.png"))
        return

    f0 = int(a.start * FPS)
    f1 = min(total, int(a.end * FPS)) if a.end else total
    tmp = tempfile.mkdtemp(prefix="clip_")
    bounds = np.linspace(f0, f1, a.jobs + 1).astype(int)
    jobs = [(W, H, env, pulse, bounds[i], bounds[i + 1], os.path.join(tmp, f"seg{i}.mp4"))
            for i in range(a.jobs) if bounds[i + 1] > bounds[i]]
    with Pool(len(jobs)) as p:
        segs = p.map(render_chunk, jobs)
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as fh:
        fh.writelines(f"file '{s}'\n" for s in segs)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-ss", str(f0 / FPS), "-t", str((f1 - f0) / FPS), "-i", a.audio,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                    "-shortest", "-movflags", "+faststart", a.out], check=True)
    print("wrote", a.out)


if __name__ == "__main__":
    sys.exit(main())
