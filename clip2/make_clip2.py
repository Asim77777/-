#!/usr/bin/env python3
"""Beat-synced lyric video for "והמשכילים יבינו" (Remastered Mashup).

Concept, "the refiner's crucible": a dark void of floating Hebrew letters
condenses into the title; singer A burns in a world of fire, the drop
throws us into singer B's white-hot ice-and-lightning world, a hexagonal
tunnel rushes through the instrumentals, both worlds merge in the chorus,
and the closing line is sealed by a rotating ring of scripture and a stamp.

Usage:
    python3 make_clip2.py AUDIO OUT.mp4 [--start S --end S] [--jobs N]
    python3 make_clip2.py AUDIO frames_dir --stills 5,30,60
"""
import argparse
import os
import subprocess
import sys
import tempfile
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "clip"))
from make_clip import FIRE_STOPS, FONT, FONT_LIGHT, duration, periodic_noise, scroll_y, smoothstep  # noqa: E402

FPS = 30
W, H = 1920, 1080
w, h = W // 2, H // 2

# Tempo found by grid search over onset strength; beats are then snapped
# to the nearest onset so the grid follows the track's small drift.
BPM = 124.32
PHASE = 0.125

VERSE = ["יִתְבָּרְרוּ וְיִתְלַבְּנוּ וְיִצָּרְפוּ רַבִּים",
         "וְהִרְשִׁיעוּ רְשָׁעִים",
         "וְלֹא יָבִינוּ כָּל רְשָׁעִים"]
WISE = ["וְהַמַּשְׂכִּלִים יָבִינוּ"]
SEALED = ["כִּי סְתֻמִים וַחֲתֻמִים", "הַדְּבָרִים עַד עֵת קֵץ"]
TITLE = "וְהַמַּשְׂכִּלִים יָבִינוּ"
SOURCE = "דָּנִיֵּאל י״ב"
LETTERS = "אבגדהוזחטיכלמנסעפצקרשתךםןףץ"

ICE_STOPS = [
    (0.00, (0, 0, 0)),
    (0.25, (2, 8, 30)),
    (0.45, (10, 40, 110)),
    (0.65, (40, 120, 220)),
    (0.80, (120, 200, 255)),
    (0.92, (210, 240, 255)),
    (1.00, (255, 255, 255)),
]

GOLD = np.array([255, 205, 110], np.float32)
EMBER = np.array([255, 120, 30], np.float32)
ICE = np.array([140, 200, 255], np.float32)
WHITE = np.array([255, 250, 240], np.float32)
WHITE_GOLD = np.array([255, 246, 225], np.float32)
BOLT = np.array([190, 215, 255], np.float32)

# Scene tracks: (time, value) keys, linearly interpolated.
TRACKS = {
    "fire": [(0, .05), (12, .15), (20, .3), (22.5, .9), (37.5, .85), (38.5, .6), (52.5, .6), (52.9, 0),
             (83.5, 0), (84.2, .75), (103.5, .75), (105, .45), (130, .55), (131.5, .6), (160, .6),
             (163, .2), (175.8, .2), (176.2, 1), (179, .6), (180.8, 0)],
    "ice": [(0, 0), (52.6, 0), (52.9, 1), (83.5, 1), (84.2, .7), (103.5, .7), (105, .6), (130, .7),
            (131.5, .15), (163, 0)],
    "letters": [(0, .5), (4, 1), (14, 1), (18, 0), (54, 0), (56, 1), (67.5, 1), (69, 0), (104, 0),
                (105, 1), (130.5, 1), (131.5, 0), (163, 0), (165, .45), (175, .45), (176.5, 0)],
    "tunnel": [(0, 0), (54, 0), (56, 1), (67.5, 1), (69, 0), (104, 0), (105.5, 1), (130.5, 1), (131.5, 0)],
    "mandala": [(0, 0), (37.5, 0), (38.3, 1), (52.5, 1), (52.9, 0), (84, 0), (84.6, 1), (103.5, 1), (105, 0)],
    "rays": [(0, 0), (37.5, 0), (38.5, .8), (52.5, .8), (52.9, 0), (84, 0), (84.5, 1), (103.5, 1), (105, .2),
             (131, .2), (132, .5), (160, .5), (163, 0), (176, 0), (176.3, 1), (180, 0)],
    "spectrum": [(0, 0), (104, 0), (105, .7), (130.5, .7), (131.5, 0)],
    "lightning": [(0, 0), (52.8, 0), (52.9, 1), (83.5, 1), (84.2, .6), (103.5, .6), (105, .8), (130.5, .8),
                  (131.5, 0)],
    "seal": [(0, 0), (131.3, 0), (135.5, 1)],
    "sealglow": [(0, 0), (131, 0), (132, 1), (162, 1), (165, .45), (175.8, .45), (176.2, 0)],
    "intensity": [(0, .15), (22, .2), (22.7, .6), (37.5, .6), (38, .8), (52.5, .8), (52.9, 1), (68, 1),
                  (69, .8), (83.5, .9), (84.2, 1), (103.5, 1), (105, .7), (130, 1), (131.3, .75),
                  (160, .8), (163, .1), (175.9, .1), (176.1, 1), (180.8, .3)],
    "letterbox": [(0, 1), (21.5, 1), (22.7, 0), (162, 0), (164, 1), (180.8, 1)],
    "speed": [(0, .25), (18, .25), (21, 0), (53, 0), (55, 1.2), (68, 1.8), (69, 0), (104, 0), (105, 1),
              (130, 3), (131, 0), (163, 0), (165, .2)],
    "master": [(0, 0), (1.5, 1), (179, 1), (180.8, 0)],
}


def track(name, t):
    k = np.array(TRACKS[name], np.float64)
    return np.interp(t, k[:, 0], k[:, 1])


def make_lut(stops):
    x = np.linspace(0, 1, 256)
    s = np.array([p[0] for p in stops])
    c = np.array([p[1] for p in stops], np.float32)
    return np.stack([np.interp(x, s, c[:, i]) for i in range(3)], 1).astype(np.float32)


# ---------------------------------------------------------------- audio

def analyse(path, n_frames):
    sr = 22050
    x = np.frombuffer(subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
        check=True, capture_output=True).stdout, np.float32)
    # onset envelope for beat snapping
    hop, win = 256, 1024
    frames = np.lib.stride_tricks.sliding_window_view(x, win)[::hop]
    S = np.abs(np.fft.rfft(frames * np.hanning(win), axis=1))
    L = np.log1p(S * 10)
    flux = np.r_[0, np.maximum(L[1:] - L[:-1], 0).sum(1)]
    onset = np.maximum(flux - np.convolve(flux, np.ones(32) / 32, "same"), 0)
    ot = np.arange(len(onset)) * hop / sr
    T = 60 / BPM
    grid = PHASE + np.arange(int((ot[-1] - PHASE) / T) + 1) * T
    offs = np.full(len(grid), np.nan)
    thr = np.percentile(onset, 80)
    for i, b in enumerate(grid):
        lo, hi = np.searchsorted(ot, [b - 0.06, b + 0.06])
        if hi > lo and onset[lo:hi].max() > thr:
            offs[i] = ot[lo + np.argmax(onset[lo:hi])] - b
    good = ~np.isnan(offs)
    offs = np.interp(np.arange(len(grid)), np.flatnonzero(good), offs[good])
    sm = np.array([np.median(offs[max(0, i - 6):i + 7]) for i in range(len(offs))])
    beats = grid + sm

    # per video frame: loudness, bass punch and spectrum bands
    vh = sr // FPS
    win = 2048
    pad = np.pad(x, (win, win + vh * n_frames))
    hann = np.hanning(win).astype(np.float32)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    edges = np.geomspace(40, 9000, 37)
    band_idx = [np.flatnonzero((freqs >= edges[i]) & (freqs < edges[i + 1])) for i in range(36)]
    rms = np.zeros(n_frames, np.float32)
    bass = np.zeros(n_frames, np.float32)
    bands = np.zeros((n_frames, 36), np.float32)
    for f in range(n_frames):
        c = win + f * vh
        seg = pad[c - win // 2:c + win // 2]
        rms[f] = np.sqrt(np.mean(seg * seg))
        sp = np.abs(np.fft.rfft(seg * hann))
        bass[f] = sp[(freqs > 30) & (freqs < 150)].mean()
        bands[f] = [np.log1p(sp[ix].mean() * 4) if len(ix) else 0 for ix in band_idx]
    rms = np.clip(rms / np.percentile(rms, 97), 0, 1.3)
    bass = np.clip(bass / np.percentile(bass, 97), 0, 1.3)
    bands /= np.percentile(bands, 98, axis=0) + 1e-6
    bands = np.clip(bands, 0, 1.2)
    env = np.zeros_like(rms)
    e = 0.0
    for f in range(n_frames):
        e += (rms[f] - e) * (0.5 if rms[f] > e else 0.06)
        env[f] = e
    # smooth band motion a little
    for f in range(1, n_frames):
        bands[f] = np.maximum(bands[f], bands[f - 1] * 0.82)
    return beats, env, bass, bands


# ---------------------------------------------------------------- text

_fonts = {}


def font(size, light=False):
    key = (size, light)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT_LIGHT if light else FONT, size,
                                         layout_engine=ImageFont.Layout.RAQM)
    return _fonts[key]


class Sprite:
    """A text (or drawn) mask with precomputed glow and dark halo, full resolution."""

    def __init__(self, mask_img, size):
        self.img = mask_img
        self.sharp = np.asarray(mask_img, np.float32) / 255
        self.glow = np.asarray(mask_img.filter(ImageFilter.GaussianBlur(size * 0.25)), np.float32) / 255
        self.halo = np.asarray(mask_img.filter(ImageFilter.GaussianBlur(size * 0.8)), np.float32) / 255

    def scaled(self, s):
        if abs(s - 1) < 0.01:
            return self.sharp, self.glow, self.halo
        hh, ww = self.sharp.shape
        nw, nh = max(1, int(ww * s)), max(1, int(hh * s))
        out = []
        for a in (self.sharp, self.glow, self.halo):
            out.append(np.asarray(Image.fromarray(a).resize((nw, nh), Image.BILINEAR)))
        return out


_sprites = {}


def text_sprite(text, size, light=False):
    key = (text, size, light)
    if key not in _sprites:
        fnt = font(size, light)
        tw = int(fnt.getlength(text, direction="rtl"))
        pad = int(size * 0.9)
        m = Image.new("L", (tw + pad * 2, int(size * 1.6) + pad * 2), 0)
        ImageDraw.Draw(m).text((m.width / 2, m.height / 2), text, font=fnt, fill=255,
                               anchor="mm", direction="rtl")
        _sprites[key] = Sprite(m, size)
    return _sprites[key]


def stamp_sprite():
    key = ("__stamp__",)
    if key not in _sprites:
        S = 620
        m = Image.new("L", (S + 200, S + 200), 0)
        d = ImageDraw.Draw(m)
        c = m.width / 2
        R = S / 2
        d.ellipse([c - R, c - R, c + R, c + R], outline=255, width=10)
        d.ellipse([c - R * 0.9, c - R * 0.9, c + R * 0.9, c + R * 0.9], outline=200, width=4)
        for k in range(36):  # ring of beads
            a = k * 2 * np.pi / 36
            bx, by = c + R * 0.8 * np.sin(a), c - R * 0.8 * np.cos(a)
            d.ellipse([bx - 6, by - 6, bx + 6, by + 6], fill=255)
        d.ellipse([c - R * 0.7, c - R * 0.7, c + R * 0.7, c + R * 0.7], outline=230, width=5)
        fnt = font(84)
        d.text((c, c), "עַד עֵת קֵץ", font=fnt, fill=255, anchor="mm", direction="rtl")
        _sprites[key] = Sprite(m, 90)
    return _sprites[key]


def layout_words(lines, size, cy, line_gap=1.5):
    """RTL layout: returns [(word, cx, cy)] in reading order, full-res coords."""
    fnt = font(size)
    space = fnt.getlength(" ")
    out = []
    n = len(lines)
    for li, line in enumerate(lines):
        words = line.split()
        lens = [fnt.getlength(wd, direction="rtl") for wd in words]
        total = sum(lens) + space * (len(words) - 1)
        x = W / 2 + total / 2
        y = cy + (li - (n - 1) / 2) * size * line_gap
        for wd, ln in zip(words, lens):
            out.append((wd, x - ln / 2, y))
            x -= ln + space
    return out


# ---------------------------------------------------------------- timeline

class Timeline:
    def __init__(self, beats):
        self.beats = beats

    def snap(self, t):
        return int(np.argmin(np.abs(self.beats - t)))

    def build(self):
        B = self.beats
        ev = []      # text events
        shocks = []  # (t, x_half, y_half, strength)
        flashes = []  # (t, strength)

        def words(lines, t, step, off, style, size, cy, slam=False):
            b0 = self.snap(t)
            for i, (wd, x, y) in enumerate(layout_words(lines, size, cy)):
                ton = B[b0 + i * step]
                ev.append(dict(sprite=text_sprite(wd, size), x=x, y=y, t0=ton, t1=off, style=style,
                               anim="slam" if slam else "pop", size=size))
                if slam:
                    shocks.append((ton, x / 2, y / 2, 0.7))
                    flashes.append((ton, 0.22))

        # intro title (assembled from particles, shatters on the first sung beat)
        self.t_vocal = B[self.snap(22.74)]
        ev.append(dict(sprite=text_sprite(TITLE, 150), x=W / 2, y=H * 0.47, t0=18.3, t1=self.t_vocal,
                       style="title", anim="fade_hard_out", size=150))
        flashes.append((self.t_vocal, 0.5))
        shocks.append((self.t_vocal, w / 2, h * 0.47, 1.0))

        words(VERSE, 22.74, 2, 37.4, "fire", 80, H * 0.45)
        words(WISE, 37.9, 4, 45.3, "gold", 140, H * 0.47, slam=True)
        words(WISE, 45.56, 4, 52.6, "white", 140, H * 0.47, slam=True)

        self.t_drop = B[self.snap(52.9)]
        flashes.append((self.t_drop, 1.0))
        shocks.append((self.t_drop, w / 2, h / 2, 1.4))
        # singer B's verse starts after the instrumental drop (~1:09), 15.2s before the chorus as in A
        words(VERSE, 69.1, 2, 83.8, "ice", 80, H * 0.45)
        words(WISE, 84.18, 4, 91.6, "merge", 140, H * 0.47, slam=True)
        words(WISE, 91.9, 4, 103.8, "merge", 150, H * 0.47, slam=True)

        # build: one huge echo word per bar, every downbeat a pulse
        echo = " ".join(VERSE).split()
        b = self.snap(104.3)
        while b % 4:
            b += 1
        k = 0
        while B[b] < 130.0:
            ev.append(dict(sprite=text_sprite(echo[k % len(echo)], 260), x=W / 2, y=H * 0.5, t0=B[b],
                           t1=B[b + 4], style="echo", anim="echo", size=260))
            shocks.append((B[b], w / 2, h / 2, 0.5))
            flashes.append((B[b], 0.12))
            b += 4
            k += 1

        words(SEALED, 131.25, 2, 138.7, "gold", 76, H * 0.5)
        self.t_stamp = B[self.snap(149.0)]
        words(SEALED, 138.99, 2, self.t_stamp - 0.05, "white_gold", 76, H * 0.5)
        ev.append(dict(sprite=stamp_sprite(), x=W / 2, y=H / 2, t0=self.t_stamp, t1=176.0,
                       style="stamp", anim="stamp", size=300))
        flashes.append((self.t_stamp, 0.8))
        shocks.append((self.t_stamp, w / 2, h / 2, 1.3))
        ev.append(dict(sprite=text_sprite(SOURCE, 46, light=True), x=W / 2, y=H * 0.825, t0=164.5, t1=175.5,
                       style="caption", anim="fade", size=46))

        self.t_hit = B[self.snap(176.1)]
        flashes.append((self.t_hit, 1.0))
        shocks.append((self.t_hit, w / 2, h / 2, 1.4))
        ev.append(dict(sprite=text_sprite(TITLE, 150), x=W / 2, y=H * 0.47, t0=self.t_hit, t1=180.2,
                       style="title", anim="slam", size=150))
        self.events, self.shocks, self.flashes = ev, shocks, flashes
        return self


# ---------------------------------------------------------------- renderer

class Renderer:
    def __init__(self, beats, env, bass, bands, n_frames):
        self.n = n_frames
        self.env, self.bass, self.bands = env, bass, bands
        self.tl = Timeline(beats).build()
        self.beats = beats
        t = np.arange(n_frames) / FPS
        self.P = {k: track(k, t).astype(np.float32) for k in TRACKS}
        bi = np.clip(np.searchsorted(beats, t, side="right") - 1, 0, len(beats) - 1)
        age = np.maximum(t - beats[bi], 0)
        self.beat_idx = bi
        self.beat_env = np.exp(-age * 7).astype(np.float32)
        bar_start = bi - (bi % 4)
        self.bar_env = np.exp(-np.maximum(t - beats[bar_start], 0) * 4).astype(np.float32)
        spd = self.P["speed"] * (0.6 + 1.2 * self.beat_env)
        self.travel = np.cumsum(spd) / FPS
        self.rot = np.cumsum(0.12 + 0.7 * self.beat_env * (self.P["mandala"] + self.P["tunnel"])) / FPS
        self.seal_rot = np.cumsum(0.07 + 0.3 * self.beat_env) / FPS

        rng = np.random.default_rng(11)
        self.nw, self.nh = w // 2, h // 2
        self.tex = [periodic_noise(self.nh * 2, self.nw, s, rng) for s in (28.0, 12.0, 5.0)]
        self.warp = periodic_noise(self.nh * 2, self.nw, 20.0, rng)
        self.lut_fire = make_lut(FIRE_STOPS)
        self.lut_ice = make_lut(ICE_STOPS)

        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        self.xx, self.yy = xx, yy
        self.yn = yy / h
        cx, cy = w / 2, h / 2
        self.r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / h
        self.ang_cw = np.arctan2(xx - cx, -(yy - cy))  # clockwise from up
        ry = -0.15 * h
        self.ray_ang = np.arctan2(yy - ry, xx - cx)
        self.ray_r = np.sqrt((xx - cx) ** 2 + (yy - ry) ** 2) / w
        vx, vy = (xx / w - .5) * 2, (yy / h - .5) * 2
        self.vignette = np.clip(1 - 0.5 * (vx * vx * .6 + vy * vy * .8), 0, 1)[..., None]
        self.text_band = np.exp(-((yy - h * 0.47) / (h * 0.085)) ** 4) * np.exp(-((xx - cx) / (w * 0.3)) ** 4)
        grng = np.random.default_rng(3)
        self.grain = [grng.normal(0, 1, (h, w, 1)).astype(np.float32) for _ in range(6)]

        # 3D letter field
        lr = np.random.default_rng(21)
        N = 240
        self.lx = lr.uniform(-1.7, 1.7, N)
        self.ly = lr.uniform(-1.0, 1.0, N)
        self.lz = lr.uniform(0, 6, N)
        self.lid = lr.integers(0, len(LETTERS), N)
        self.glyph_sizes = np.array([8, 11, 15, 20, 27, 36, 48, 64, 86, 115])
        self.glyphs = {}
        for li, ch in enumerate(LETTERS):
            for s in self.glyph_sizes.tolist():
                fnt = font(s)
                m = Image.new("L", (int(s * 2), int(s * 2)), 0)
                ImageDraw.Draw(m).text((s, s), ch, font=fnt, fill=255, anchor="mm")
                a = np.asarray(m, np.float32) / 255
                g = np.asarray(m.filter(ImageFilter.GaussianBlur(max(1, s * 0.15))), np.float32) / 255
                self.glyphs[(li, int(s))] = a * 0.8 + g * 1.4

        # title particles: targets sampled from the title mask
        sp = text_sprite(TITLE, 150)
        mh, mw = sp.sharp.shape
        ys, xs = np.nonzero(sp.sharp > 0.5)
        pr = np.random.default_rng(5)
        pick = pr.choice(len(xs), min(5000, len(xs)), replace=False)
        self.pt_tx = (xs[pick] + W / 2 - mw / 2) / 2
        self.pt_ty = (ys[pick] + H * 0.47 - mh / 2) / 2
        ang = pr.uniform(0, 2 * np.pi, len(pick))
        rad = pr.uniform(0.3, 1.1, len(pick)) * w
        self.pt_sx = w / 2 + np.cos(ang) * rad
        self.pt_sy = h / 2 + np.sin(ang) * rad * 0.6
        self.pt_swirl = pr.uniform(1.5, 3.5, len(pick))
        self.pt_delay = pr.uniform(0, 0.25, len(pick))
        va = np.arctan2(self.pt_ty - h * 0.47, self.pt_tx - w / 2) + pr.normal(0, 0.4, len(pick))
        vs = pr.uniform(150, 650, len(pick))
        self.pt_vx, self.pt_vy = np.cos(va) * vs, np.sin(va) * vs - 120

        # circular scripture band around the seal (full resolution)
        self.ring_in, self.ring_out = 452, 506
        yy2, xx2 = np.mgrid[0:H, 0:W]
        rr2 = np.sqrt((xx2 - W / 2) ** 2 + (yy2 - H / 2) ** 2)
        sel = (rr2 >= self.ring_in) & (rr2 < self.ring_out)
        self.ring_pix = np.flatnonzero(sel)
        self.ring_theta = np.arctan2(xx2[sel] - W / 2, -(yy2[sel] - H / 2))
        self.ring_rad = rr2[sel]
        circ = 2 * np.pi * (self.ring_in + self.ring_out) / 2
        phrase = "כִּי סְתֻמִים וַחֲתֻמִים הַדְּבָרִים עַד עֵת קֵץ · וְהַמַּשְׂכִּלִים יָבִינוּ · "
        fnt = font(34)
        plen = fnt.getlength(phrase, direction="rtl")
        reps = max(1, int(round(circ / plen)))
        sh = self.ring_out - self.ring_in
        strip = Image.new("L", (int(plen * reps), sh), 0)
        ImageDraw.Draw(strip).text((strip.width / 2, sh / 2), phrase * reps, font=fnt, fill=255,
                                   anchor="mm", direction="rtl")
        self.strip = np.asarray(strip.resize((int(circ), sh), Image.BILINEAR), np.float32) / 255

        self.sparks = np.zeros((0, 8), np.float32)  # x y vx vy life max size kind
        self.kern = {}
        for rad in (1, 2, 3):
            k = np.arange(-rad * 2, rad * 2 + 1, dtype=np.float32)
            self.kern[rad] = np.exp(-(k[:, None] ** 2 + k[None, :] ** 2) / (2 * (rad * .7) ** 2))

    # ------------------------------------------------------------ particles
    def spark_step(self, f):
        t = f / FPS
        P = self.P
        rng = np.random.default_rng(1000 + f)
        heat = P["fire"][f] + P["ice"][f] * 0.7
        rate = 1 + 10 * heat * (0.5 + self.env[f]) + 10 * self.beat_env[f] * P["intensity"][f] * heat
        n = rng.poisson(rate)
        new = []
        if n:
            a = np.zeros((n, 8), np.float32)
            a[:, 0] = rng.uniform(0, 1, n)
            a[:, 1] = rng.uniform(0.85, 1.05, n)
            a[:, 2] = rng.normal(0, 0.0006, n)
            a[:, 3] = -rng.uniform(0.002, 0.008, n) * (0.7 + heat)
            a[:, 5] = rng.uniform(1.5, 4.0, n) * FPS
            a[:, 6] = rng.choice([1, 1, 1, 2, 2, 3], n)
            new.append(a)
        # bursts from slammed words and shockwaves landing in this frame
        for (ts, sx, sy, st) in self.tl.shocks:
            if t - 1 / FPS < ts <= t:
                m = int(60 * st)
                a = np.zeros((m, 8), np.float32)
                ang = rng.uniform(0, 2 * np.pi, m)
                sp = rng.uniform(0.004, 0.02, m) * st
                a[:, 0], a[:, 1] = sx / w, sy / h
                a[:, 2], a[:, 3] = np.cos(ang) * sp * h / w, np.sin(ang) * sp
                a[:, 5] = rng.uniform(0.6, 1.6, m) * FPS
                a[:, 6] = rng.choice([1, 2, 2, 3], m)
                a[:, 7] = 1
                new.append(a)
        if new:
            self.sparks = np.concatenate([self.sparks] + new)
        s = self.sparks
        burst = s[:, 7] > 0
        s[:, 2] += rng.normal(0, 0.00025, len(s)) * ~burst
        s[burst, 2] *= 0.94
        s[burst, 3] = s[burst, 3] * 0.94 + 0.0002
        s[:, 0] += s[:, 2]
        s[:, 1] += s[:, 3]
        s[:, 4] += 1
        self.sparks = s[(s[:, 4] < s[:, 5]) & (s[:, 1] > -0.05) & (s[:, 1] < 1.1)]

    def spark_layer(self, f):
        buf = np.zeros((h, w), np.float32)
        rng = np.random.default_rng(5000 + f)
        flick = rng.uniform(0.6, 1.0, len(self.sparks))
        for (x, y, _, _, life, mx, size, _k), fl in zip(self.sparks, flick):
            k = self.kern[int(size)]
            kr = k.shape[0] // 2
            px, py = int(x * w), int(y * h)
            if px < -kr or py < -kr or px >= w + kr or py >= h + kr:
                continue
            u = life / mx
            a = fl * min(1.0, u * 8) * (1 - u) ** 1.2 * 1.7
            x0, y0, x1, y1 = max(0, px - kr), max(0, py - kr), min(w, px + kr + 1), min(h, py + kr + 1)
            buf[y0:y1, x0:x1] += a * k[y0 - py + kr:y1 - py + kr, x0 - px + kr:x1 - px + kr]
        return buf

    # ------------------------------------------------------------ layers
    def fire_ice(self, t, f, img):
        P = self.P
        fire, ice = P["fire"][f], P["ice"][f]
        if fire < 0.01 and ice < 0.01:
            return
        nh = self.nh
        e = self.env[f]
        n1 = scroll_y(self.tex[0], t * 9.0, nh)
        n2 = scroll_y(self.tex[1], t * 22.0, nh)
        n3 = scroll_y(self.tex[2], t * 45.0, nh)
        wp = scroll_y(self.warp, t * 6.0, nh)
        turb = 0.5 * n1 + 0.32 * n2 + 0.18 * n3
        shift = ((wp - 0.5) * 18).astype(np.int32)
        cols = (np.arange(self.nw)[None, :] + shift) % self.nw
        turb = np.take_along_axis(turb, cols, 1)
        field = np.asarray(Image.fromarray(turb).resize((w, h), Image.BILINEAR))
        kick = self.beat_env[f] * P["intensity"][f]
        if fire > 0.01:
            fh = 0.18 + 0.5 * fire + 0.12 * e * fire + 0.06 * kick
            prof = np.clip((self.yn - (1 - fh)) / fh, 0, 1) ** 1.3
            v = (prof * (0.35 + 1.1 * field) + (field - .5) * .25 * fire) * (0.55 + 0.5 * fire + 0.25 * e)
            img += self.lut_fire[np.clip(v * 255, 0, 255).astype(np.uint8)] * min(1.0, fire * 1.6)
        if ice > 0.01:
            fl = field[::-1]
            ih = 0.25 + 0.45 * ice + 0.1 * kick
            prof = np.clip(((1 - self.yn) - (1 - ih)) / ih, 0, 1) ** 1.6
            v = (prof * (0.3 + 1.0 * fl) + (fl - .5) * .2 * ice) * (0.5 + 0.4 * ice + 0.3 * e)
            img += self.lut_ice[np.clip(v * 255, 0, 255).astype(np.uint8)] * min(1.0, ice * 1.4)

    def world_color(self, f):
        fire, ice = self.P["fire"][f], self.P["ice"][f]
        k = ice / (fire + ice + 1e-6)
        return GOLD * (1 - k) + ICE * k

    def letters3d(self, f, acc):
        a = self.P["letters"][f]
        if a < 0.01:
            return
        z = (self.lz - self.travel[f]) % 6 + 0.15
        fov = 0.55 * w
        sx = w / 2 + self.lx / z * fov
        sy = h / 2 + self.ly / z * fov
        size = 26 / z
        fog = np.clip((6 - z) / 2.5, 0, 1) * np.clip((z - 0.15) / 0.5, 0, 1) * a
        order = np.argsort(-z)
        for i in order:
            if fog[i] < 0.02 or size[i] < 6:
                continue
            si = int(self.glyph_sizes[np.argmin(np.abs(self.glyph_sizes - size[i]))])
            g = self.glyphs[(int(self.lid[i]), si)]
            gr = g.shape[0] // 2
            px, py = int(sx[i]), int(sy[i])
            x0, y0, x1, y1 = max(0, px - gr), max(0, py - gr), min(w, px + gr), min(h, py + gr)
            if x1 <= x0 or y1 <= y0:
                continue
            acc[y0:y1, x0:x1] += fog[i] * 0.8 * g[y0 - py + gr:y1 - py + gr, x0 - px + gr:x1 - px + gr]

    def line_art(self, f, t):
        """Tunnel, mandala and spectrum ring, drawn as glowing lines."""
        P = self.P
        tun, man, spc = P["tunnel"][f], P["mandala"][f], P["spectrum"][f]
        if tun < 0.01 and man < 0.01 and spc < 0.01:
            return None
        im = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(im)
        cx, cy = w / 2, h / 2
        be = self.beat_env[f]
        if tun > 0.01:
            fov = 0.5 * w
            rings = []
            for i in range(18):
                z = (i * 0.45 - self.travel[f] * 1.4) % (18 * 0.45) + 0.2
                rad = 0.9 / z * fov
                rot = z * 0.25 + self.rot[f] * 0.5
                pts = [(cx + rad * np.cos(rot + k * np.pi / 3), cy + rad * np.sin(rot + k * np.pi / 3) * 0.9)
                       for k in range(6)]
                fog = np.clip((8 - z) / 4, 0, 1) * np.clip((z - 0.2) / 0.6, 0, 1)
                rings.append((z, pts, fog))
            rings.sort(key=lambda r: r[0])
            for (z, pts, fog), nxt in zip(rings, rings[1:] + [None]):
                v = int(255 * tun * fog * (0.45 + 0.55 * be))
                if v < 4:
                    continue
                d.polygon(pts, outline=v, width=max(1, int(4 / z)))
                if nxt is not None:
                    for p, q in zip(pts, nxt[1]):
                        d.line([p, q], fill=int(v * 0.35), width=1)
        if man > 0.01:
            R = h * 0.42 * (1 + 0.06 * be)
            v = int(255 * man)
            a = self.rot[f]
            for rr, wd in ((1.0, 3), (0.93, 1), (0.62, 2), (0.3, 1)):
                d.ellipse([cx - R * rr, cy - R * rr, cx + R * rr, cy + R * rr], outline=v, width=wd)
            # "seed of life": six circles around a centre, counter-rotating inner set
            for sgn, rc, dist in ((1, 0.31, 0.31), (-1, 0.155, 0.155)):
                for k in range(6):
                    an = sgn * a + k * np.pi / 3
                    px, py = cx + R * dist * np.sin(an), cy - R * dist * np.cos(an)
                    d.ellipse([px - R * rc, py - R * rc, px + R * rc, py + R * rc], outline=v, width=2)
            for k in range(12):
                an = -a * 0.5 + k * np.pi / 6
                d.line([(cx + R * .3 * np.sin(an), cy - R * .3 * np.cos(an)),
                        (cx + R * .93 * np.sin(an), cy - R * .93 * np.cos(an))], fill=int(v * .5), width=1)
            for k in range(48):
                an = a * 0.3 + k * np.pi / 24
                r0 = R * (1.02 if k % 4 else 0.98)
                d.line([(cx + r0 * np.sin(an), cy - r0 * np.cos(an)),
                        (cx + R * 1.06 * np.sin(an), cy - R * 1.06 * np.cos(an))], fill=v, width=2)
        if spc > 0.01:
            b = self.bands[f]
            vals = np.r_[b, b[::-1]]
            r0 = h * 0.24 * (1 + 0.05 * be)
            v = int(255 * spc)
            for k, m in enumerate(vals):
                an = k * 2 * np.pi / len(vals) + self.rot[f] * 0.2
                ln = h * 0.16 * m
                d.line([(cx + r0 * np.sin(an), cy - r0 * np.cos(an)),
                        (cx + (r0 + ln) * np.sin(an), cy - (r0 + ln) * np.cos(an))], fill=v, width=3)
        return im

    def lightning(self, f, t):
        a = self.P["lightning"][f]
        if a < 0.01:
            return None
        i = self.beat_idx[f]
        im = None
        for b in range(i - 1, i + 1):
            if b < 0 or b % 2 == 0 and b % 8:
                continue
            age = t - self.beats[b]
            if age < 0 or age > 0.35:
                continue
            fade = a * (1.0 if age < 0.05 else np.exp(-(age - 0.05) * 9)) * (0.6 + 0.4 * (age < 0.12))
            rng = np.random.default_rng(777 + b)
            if im is None:
                im = Image.new("L", (w, h), 0)
            d = ImageDraw.Draw(im)
            for _ in range(rng.integers(1, 3)):
                x0 = rng.uniform(0.1, 0.9) * w
                pts = [(x0, -10.0), (x0 + rng.normal(0, 0.15) * w, rng.uniform(0.45, 0.9) * h)]
                disp = 0.12 * w
                for _lvl in range(7):
                    nxt = [pts[0]]
                    for p, q in zip(pts, pts[1:]):
                        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
                        nxt += [(mx + rng.normal(0, disp), my), q]
                    pts, disp = nxt, disp * 0.55
                v = int(255 * min(1, fade))
                d.line(pts, fill=v, width=2)
                br = int(rng.integers(len(pts) // 4, len(pts) // 2))
                bx, by = pts[br]
                bp = [(bx, by)]
                for _s in range(12):
                    bx += rng.normal(8, 10)
                    by += rng.uniform(6, 16)
                    bp.append((bx, by))
                d.line(bp, fill=int(v * 0.6), width=1)
        return im

    def title_particles(self, t, acc):
        if t < 10 or t > self.tl.t_vocal + 1.8:
            return
        tv = self.tl.t_vocal
        if t < tv:
            u = np.clip((t - 10.5 - self.pt_delay * 8) / 7.5, 0, 1)
            e = u * u * (3 - 2 * u)
            ang = (1 - e) * self.pt_swirl
            dx, dy = self.pt_sx - self.pt_tx, self.pt_sy - self.pt_ty
            x = self.pt_tx + (dx * np.cos(ang) - dy * np.sin(ang)) * (1 - e)
            y = self.pt_ty + (dx * np.sin(ang) + dy * np.cos(ang)) * (1 - e)
            bright = np.clip((t - 10) / 2, 0, 1) * (0.5 + 0.5 * e) * (1 - 0.6 * np.clip((t - 18.5) / 1.5, 0, 1))
        else:
            a = t - tv
            x = self.pt_tx + self.pt_vx * a
            y = self.pt_ty + self.pt_vy * a + 260 * a * a
            bright = np.clip(1 - a / 1.8, 0, 1) * 1.3
        xi, yi = x.astype(int), y.astype(int)
        ok = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
        np.add.at(acc, (yi[ok], xi[ok]), 0.9 * (bright if np.isscalar(bright) else bright[ok]))

    def seal_rings(self, f, img):
        P = self.P
        g = P["sealglow"][f]
        if g < 0.01:
            return
        seal = P["seal"][f]
        ang01 = (self.ang_cw % (2 * np.pi)) / (2 * np.pi)
        reveal = np.clip((seal * 1.05 - ang01) * 40, 0, 1)
        reveal *= np.maximum(np.clip(ang01 * 25, 0, 1), smoothstep((seal - 0.9) / 0.1))
        r = self.r
        ri, ro = self.ring_in / H, self.ring_out / H
        ring = (np.exp(-((r - ri) / 0.004) ** 2) + np.exp(-((r - ro) / 0.004) ** 2)
                + 0.25 * np.exp(-((r - (ri + ro) / 2) / 0.05) ** 2))
        ring = ring * reveal * g * (0.8 + 0.5 * self.beat_env[f])
        img += ring[..., None] * np.array([255, 200, 100], np.float32)

    def shockwaves(self, t, img):
        for (ts, sx, sy, st) in self.tl.shocks:
            a = t - ts
            if a < 0 or a > 0.9:
                continue
            R = a * 900 * (0.6 + 0.4 * st)
            rr = np.sqrt((self.xx - sx) ** 2 + (self.yy - sy) ** 2)
            ring = np.exp(-((rr - R) / (10 + 25 * a)) ** 2) * (1 - a / 0.9) ** 2 * st
            img += ring[..., None] * np.array([255, 235, 200], np.float32) * 0.9

    def flash(self, t):
        v = 0.0
        for (tf, st) in self.tl.flashes:
            a = t - tf
            if 0 <= a < 1.0:
                v += st * np.exp(-a * 7)
        return v

    # ------------------------------------------------------------ text
    def draw_events(self, full, t, f, ox, oy):
        P = self.P
        be = self.beat_env[f]
        master = P["master"][f]
        for ev in self.tl.events:
            if t < ev["t0"] or t > ev["t1"] + 0.7:
                continue
            age = t - ev["t0"]
            anim, style = ev["anim"], ev["style"]
            a_out = float(smoothstep((ev["t1"] - t) / 0.6))
            s = 1.0
            if anim == "pop":
                a_in = float(smoothstep(age / 0.18))
                s = 1 + 0.35 * np.exp(-age * 12)
            elif anim == "slam":
                a_in = float(smoothstep(age / 0.08))
                s = 1 + 1.4 * np.exp(-age * 14)
            elif anim == "fade":
                a_in = float(smoothstep(age / 1.2))
            elif anim == "fade_hard_out":
                a_in = float(smoothstep(age / 1.5))
                a_out = 1.0 if t < ev["t1"] else 0.0
            elif anim == "echo":
                dur = ev["t1"] - ev["t0"]
                a_in = float(smoothstep(age / 0.06))
                a_out = float(np.clip(1 - age / (dur + 0.3), 0, 1)) ** 1.5
                s = 0.85 + 0.45 * age / dur
            elif anim == "stamp":
                a_in = float(smoothstep(age / 0.06))
                s = 1 + 2.2 * np.exp(-age * 16)
                a_out = float(smoothstep((ev["t1"] - t) / 1.0))
            a = a_in * a_out * master
            if a < 0.004:
                continue
            hot = float(np.exp(-age * 5))  # white-hot on impact
            if style == "fire":
                prog = float(np.clip(age / 8, 0, 1))
                base, gcol = EMBER * (1 - prog) + WHITE_GOLD * prog, np.array([255, 90, 10], np.float32)
            elif style == "ice":
                base, gcol = np.array([215, 235, 255], np.float32), np.array([60, 140, 255], np.float32)
            elif style == "gold":
                base, gcol = GOLD, np.array([255, 140, 30], np.float32)
            elif style in ("white", "white_gold"):
                base, gcol = WHITE_GOLD, GOLD
            elif style == "merge":
                base, gcol = WHITE, np.array([150, 170, 255], np.float32) * 0.5 + GOLD * 0.5
            elif style == "echo":
                base, gcol = self.world_color(f), self.world_color(f)
                a *= 0.32
            elif style == "stamp":
                base, gcol = GOLD, np.array([255, 150, 40], np.float32)
            elif style == "caption":
                base, gcol = GOLD * 0.95, np.array([200, 110, 30], np.float32)
            else:  # title
                u = float(smoothstep((t - ev["t0"]) / 3.0))
                base, gcol = EMBER * (1 - u) + GOLD * u, GOLD
            col = base * (1 - hot * 0.7) + WHITE * hot * 0.7
            sh, gl, ha = ev["sprite"].scaled(s)
            hh, ww = sh.shape
            x = int(ev["x"] - ww / 2 + ox)
            y = int(ev["y"] - hh / 2 + oy)
            y0, x0, y1, x1 = max(0, y), max(0, x), min(H, y + hh), min(W, x + ww)
            if y1 <= y0 or x1 <= x0:
                continue
            sy, sx = y0 - y, x0 - x
            sh = sh[sy:sy + y1 - y0, sx:sx + x1 - x0][..., None]
            gl = gl[sy:sy + y1 - y0, sx:sx + x1 - x0][..., None]
            ha = ha[sy:sy + y1 - y0, sx:sx + x1 - x0][..., None]
            reg = full[y0:y1, x0:x1].astype(np.float32)
            if style != "echo":
                reg *= 1 - (0.8 if anim == "slam" else 0.5) * ha * a
            reg += gcol * (gl * 0.9 + ha * 0.3) * (0.7 + 0.6 * be + hot) * a
            reg *= 1 - sh * a
            reg += col * sh * a
            full[y0:y1, x0:x1] = np.clip(reg, 0, 255).astype(np.uint8)

    def ring_text(self, full, f):
        g = self.P["sealglow"][f] * self.P["master"][f]
        seal = self.P["seal"][f]
        if g < 0.01 or seal < 0.3:
            return
        a = g * float(smoothstep((seal - 0.3) / 0.7))
        Ls, sh = self.strip.shape[1], self.strip.shape[0]
        th = (self.ring_theta + self.seal_rot[f]) % (2 * np.pi)
        sx = (th / (2 * np.pi) * Ls).astype(np.int32) % Ls
        sy = np.clip(((self.ring_out - self.ring_rad) / (self.ring_out - self.ring_in) * sh).astype(np.int32),
                     0, sh - 1)
        m = self.strip[sy, sx] * a
        flat = full.reshape(-1, 3)
        px = flat[self.ring_pix].astype(np.float32)
        px = px * (1 - m[:, None]) + GOLD * 1.05 * m[:, None]
        flat[self.ring_pix] = np.clip(px, 0, 255).astype(np.uint8)

    # ------------------------------------------------------------ frame
    def frame(self, f):
        t = f / FPS
        P = self.P
        inten = P["intensity"][f]
        be, bar = self.beat_env[f], self.bar_env[f]
        img = np.zeros((h, w, 3), np.float32)

        self.fire_ice(t, f, img)

        rays = P["rays"][f]
        if rays > 0.01:
            rv = 0.5 + 0.5 * np.sin(self.ray_ang * 22 + t * 0.35) * np.sin(self.ray_ang * 9 - t * 0.21)
            rv = rv ** 3 * np.exp(-self.ray_r * 1.6)
            bloom = np.exp(-(self.r / (0.42 + 0.06 * be)) ** 2)
            light = rays * (rv * (0.5 + 0.3 * be) + bloom * (0.35 + 0.25 * be))
            img += light[..., None] * (self.world_color(f) * 0.4 + WHITE * 0.6)

        acc = np.zeros((h, w), np.float32)
        self.letters3d(f, acc)
        la = self.line_art(f, t)
        if la is not None:
            glow = la.filter(ImageFilter.GaussianBlur(4))
            acc += (np.asarray(la, np.float32) * 0.9 + np.asarray(glow, np.float32) * 2.0) / 255
        if P["mandala"][f] > 0.01:  # keep the chorus line readable over the mandala
            acc *= 1 - 0.75 * P["mandala"][f] * self.text_band
        img += acc[..., None] * self.world_color(f)

        bolt = self.lightning(f, t)
        if bolt is not None:
            bg = bolt.filter(ImageFilter.GaussianBlur(6))
            bv = (np.asarray(bolt, np.float32) * 1.4 + np.asarray(bg, np.float32) * 2.5) / 255
            img += bv[..., None] * BOLT
            img += min(0.25, float(bv.mean()) * 8) * BOLT  # the whole sky lights up

        gacc = np.zeros((h, w), np.float32)
        self.title_particles(t, gacc)
        if gacc.any():
            gimg = Image.fromarray(np.clip(gacc * 255, 0, 255).astype(np.uint8))
            gb = np.asarray(gimg.filter(ImageFilter.GaussianBlur(2.5)), np.float32) / 255
            img += (gacc + gb * 2.5)[..., None] * GOLD

        self.seal_rings(f, img)
        self.shockwaves(t, img)

        sp = self.spark_layer(f)
        k = P["ice"][f] / (P["fire"][f] + P["ice"][f] + 1e-6)
        scol = np.array([255, 150, 45], np.float32) * (1 - k) + ICE * k
        img += sp[..., None] * scol + (sp ** 2)[..., None] * np.array([0, 60, 80], np.float32)

        fl = self.flash(t)
        img += fl * 255 * np.exp(-self.r * 1.2)[..., None]

        # bloom
        small = Image.fromarray(np.clip(img - 110, 0, 255).astype(np.uint8)).resize((w // 4, h // 4), Image.BILINEAR)
        small = small.filter(ImageFilter.GaussianBlur(5)).resize((w, h), Image.BILINEAR)
        img += np.asarray(small, np.float32) * 0.9

        img *= self.vignette
        img += self.grain[f % 6] * (5 + 4 * inten)
        img *= P["master"][f]
        np.clip(img, 0, 255, out=img)

        # chromatic aberration on hits
        ca = int(round(1 + 7 * min(1.0, fl + inten * bar * 0.5)))
        u8 = img.astype(np.uint8)
        if ca > 1:
            u8[..., 0] = np.roll(u8[..., 0], -ca, axis=1)
            u8[..., 2] = np.roll(u8[..., 2], ca, axis=1)

        # camera: zoom punch on beats, shake on hits
        zoom = 1 + 0.03 * inten * be + 0.05 * inten * bar * (inten > 0.75) + 0.08 * min(1.0, fl)
        srng = np.random.default_rng(9000 + f)
        sh_amp = (3 * inten * be + 10 * min(1.0, fl)) * (inten > 0.3)
        sx, sy = srng.normal(0, 1, 2) * sh_amp
        bw, bh = w / zoom, h / zoom
        box = (w / 2 - bw / 2 + sx / 2, h / 2 - bh / 2 + sy / 2, w / 2 + bw / 2 + sx / 2, h / 2 + bh / 2 + sy / 2)
        full = np.array(Image.fromarray(u8).resize((W, H), Image.BILINEAR, box=box))

        self.ring_text(full, f)
        self.draw_events(full, t, f, -sx, -sy)

        lb = P["letterbox"][f]
        if lb > 0.01:
            bar_px = int(H * 0.11 * float(smoothstep(lb)))
            if bar_px:
                full[:bar_px] = 0
                full[H - bar_px:] = 0
        return full


# ---------------------------------------------------------------- driver

WARMUP = 5 * FPS


def render_chunk(args):
    data, f0, f1, out = args
    r = Renderer(*data)
    for f in range(max(0, f0 - WARMUP), f0):
        r.spark_step(f)
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for f in range(f0, f1):
        r.spark_step(f)
        enc.stdin.write(r.frame(f).tobytes())
        if (f - f0) % 300 == 0:
            print(f"  [{os.path.basename(out)}] {f - f0}/{f1 - f0}", flush=True)
    enc.stdin.close()
    if enc.wait():
        raise RuntimeError("ffmpeg failed")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("out")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float)
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    ap.add_argument("--stills", help="comma separated times; writes PNGs into OUT dir")
    a = ap.parse_args()

    total = int(duration(a.audio) * FPS)
    print("analysing audio...", flush=True)
    data = (*analyse(a.audio, total), total)

    if a.stills:
        os.makedirs(a.out, exist_ok=True)
        r = Renderer(*data)
        for ts in a.stills.split(","):
            f = int(float(ts) * FPS)
            r.sparks = np.zeros((0, 8), np.float32)
            for g in range(max(0, f - WARMUP), f + 1):
                r.spark_step(g)
            Image.fromarray(r.frame(f)).save(os.path.join(a.out, f"v2_{float(ts):06.2f}.png"))
        return

    f0 = int(a.start * FPS)
    f1 = min(total, int(a.end * FPS)) if a.end else total
    tmp = tempfile.mkdtemp(prefix="clip2_")
    bounds = np.linspace(f0, f1, a.jobs + 1).astype(int)
    jobs = [(data, bounds[i], bounds[i + 1], os.path.join(tmp, f"seg{i}.mp4"))
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
