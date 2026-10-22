#!/usr/bin/env python3
""""Sealed Light" (אור חתום): full lyric video for the remastered mashup.

Editorial, studio-grade motion typography in carbon, paper and ochre.
Words are timed to the sung syllables: singer A's verse was located from
the centre-panned vocal (mid minus side) onsets; singer B repeats the same
structure 46.34s later (verified by the chorus melody match); choruses and
the finale use the track's embedded timings. Cuts and pulses sit on a
tracked 124.3 BPM beat grid.

Usage:
    python3 make_clip5.py AUDIO OUT.mp4 [--start S --end S] [--jobs N]
    python3 make_clip5.py AUDIO frames_dir --stills 5,30,60
"""
import argparse
import functools
import os
import subprocess
import sys
import tempfile
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "clip2"))
from make_clip2 import analyse  # noqa: E402
from make_clip import duration  # noqa: E402
from keyframes import CARBON, MONO, OCHRE, PAPER, SANS_LIGHT, SANS_THIN, SERIF_BLACK, SERIF_LIGHT, SERIF_MED  # noqa: E402
from keyframes import FONTS, SKILL_FONTS  # noqa: E402

FPS = 30
W, H = 1920, 1080
B_SHIFT = 46.34  # singer B = singer A + this offset

# ---------------------------------------------------------------- lyrics & timing

VERSE_WORDS = ["יִתְבָּרְרוּ", "וְיִתְלַבְּנוּ", "וְיִצָּרְפוּ", "רַבִּים", "וְהִרְשִׁיעוּ", "רְשָׁעִים",
               "וְלֹא", "יָבִינוּ", "כָּל", "רְשָׁעִים"]
VERSE_LINES = [[0, 1, 2, 3], [4, 5], [6, 7, 8, 9]]           # word indices per transcript line
# onsets measured on the centre-channel harmonic vocal envelope (rising edges)
VERSE_A_TIMES = [23.00, 24.78, 26.74, 28.75, 30.57, 32.36, 34.05, 34.70, 35.39, 35.89]
# singer B: A's word windows cross-correlated against B (+46.34s), checked against B's own rises
VERSE_B_TIMES = [69.23, 71.10, 73.10, 74.60, 76.78, 78.70, 80.30, 81.00, 81.95, 82.25]
VERSE_A_END = 37.55
WISE = ["וְהַמַּשְׂכִּלִים", "יָבִינוּ"]
CHORUS_A = [(37.84, 39.24, 45.25), (45.44, 46.86, 52.70)]     # (word1, word2, end)
CHORUS_B = [(84.00, 85.29, 91.25), (91.40, 92.53, 103.80)]
SEALED = [["כִּי", "סְתֻמִים", "וַחֲתֻמִים"], ["הַדְּבָרִים", "עַד", "עֵת", "קֵץ"]]
# the closing line is sung twice, 8 bars each, in two-bar phrases (vocal rises measured)
SEALED_TIMES = [[132.42, 133.87, 136.24, 140.00, 144.08, 144.35, 144.82],
                [147.60, 149.05, 151.74, 155.07, 159.35, 159.62, 160.09]]
TITLE = "וְהַמַּשְׂכִּלִים יָבִינוּ"
# source reference in Hebrew letters (the font subset has no comma/dash, so spacing and a maqaf)
REF_FULL = "דָּנִיֵּאל  י״ב  ט׳־י׳"
REF_END = "דָּנִיֵּאל  י״ב  ט׳"

T_DROP = 52.90
T_BUILD = 104.0
T_FINAL = 131.25
T_HIT = 176.1
T_END = 180.8


@functools.lru_cache(maxsize=None)
def fnt(name, size):
    path = os.path.join(FONTS, name) if name.endswith(".woff") else os.path.join(SKILL_FONTS, name)
    return ImageFont.truetype(path, int(size), layout_engine=ImageFont.Layout.RAQM)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- sprites

class Sprite:
    def __init__(self, text, font_name, size, rtl=True):
        f = fnt(font_name, size)
        bbox = f.getbbox(text, direction="rtl" if rtl else None, anchor="ls")
        pad = int(size * 0.12) + 4
        w_, h_ = bbox[2] - bbox[0] + pad * 2, bbox[3] - bbox[1] + pad * 2
        im = Image.new("L", (w_, h_), 0)
        ImageDraw.Draw(im).text((pad - bbox[0], pad - bbox[1]), text, font=f, fill=255, anchor="ls",
                                direction="rtl" if rtl else None)
        self.m = np.asarray(im, np.float32) / 255
        self.ox, self.oy = pad - bbox[0], pad - bbox[1]   # baseline origin inside the sprite
        self.adv = f.getlength(text, direction="rtl" if rtl else None)
        self.size = size


_cache = {}


def sprite(text, font_name, size, rtl=True):
    key = (text, font_name, int(size), rtl)
    if key not in _cache:
        _cache[key] = Sprite(text, font_name, int(size), rtl)
    return _cache[key]


@functools.lru_cache(maxsize=None)
def fitted(text, font_name, size, max_w, max_h):
    """Largest sprite (<= size) whose full ink, niqqud included, fits max_w x max_h."""
    while size > 20:
        sp = sprite(text, font_name, size)
        if sp.m.shape[1] <= max_w and sp.m.shape[0] <= max_h:
            return sp
        size = int(size * 0.95)
    return sprite(text, font_name, size)


@functools.lru_cache(maxsize=None)
def fit_size(text, font_name, size, max_w):
    while fnt(font_name, size).getlength(text, direction="rtl") > max_w and size > 20:
        size = int(size * 0.95)
    return size


# ---------------------------------------------------------------- frame canvas

class Frame:
    def __init__(self, bg):
        self.c = np.empty((H, W, 3), np.float32)
        self.c[:] = bg

    def blit(self, sp, x, y, color, alpha=1.0, anchor="r", wipe=1.0, scale=1.0):
        """Place sprite with its baseline at y; anchor r/l/c on x. wipe reveals right-to-left."""
        if alpha <= 0.003:
            return
        m = sp.m
        ox, oy = sp.ox, sp.oy
        if abs(scale - 1) > 0.004:
            hh, ww = m.shape
            nw, nh = max(1, int(ww * scale)), max(1, int(hh * scale))
            m = np.asarray(Image.fromarray(m).resize((nw, nh), Image.BILINEAR))
            ox, oy = ox * scale, oy * scale
        hh, ww = m.shape
        adv = sp.adv * scale
        if anchor == "r":
            x0 = x - adv - ox
        elif anchor == "l":
            x0 = x - ox
        else:
            x0 = x - adv / 2 - ox
        x0, y0 = int(round(x0)), int(round(y - oy))
        if wipe < 1.0:
            cols = np.arange(ww, dtype=np.float32)
            edge = ww * (1 - wipe)
            m = m * np.clip((cols - edge) / 18 + 0.5, 0, 1)[None, :]
        X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x0 + ww), min(H, y0 + hh)
        if X1 <= X0 or Y1 <= Y0:
            return
        a = m[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0][..., None] * alpha
        reg = self.c[Y0:Y1, X0:X1]
        reg *= 1 - a
        reg += np.asarray(color, np.float32) * a

    def rect(self, x0, y0, x1, y1, color, alpha=1.0):
        x0, y0, x1, y1 = int(max(0, x0)), int(max(0, y0)), int(min(W, x1)), int(min(H, y1))
        if x1 > x0 and y1 > y0:
            reg = self.c[y0:y1, x0:x1]
            reg *= 1 - alpha
            reg += np.asarray(color, np.float32) * alpha

    def lines_layer(self, draw_fn, x0, y0, x1, y1, color, alpha=1.0):
        """Draw with PIL into a local L image (antialiased lines) and composite."""
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        im = Image.new("L", (x1 - x0, y1 - y0), 0)
        draw_fn(ImageDraw.Draw(im), x0, y0)
        m = np.asarray(im, np.float32) / 255
        X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        a = m[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0][..., None] * alpha
        reg = self.c[Y0:Y1, X0:X1]
        reg *= 1 - a
        reg += np.asarray(color, np.float32) * a


# ---------------------------------------------------------------- renderer

class Clip:
    def __init__(self, beats, env, n_frames):
        self.beats = np.asarray(beats)
        self.env = env
        self.n = n_frames
        t = np.arange(n_frames) / FPS
        bi = np.clip(np.searchsorted(self.beats, t, side="right") - 1, 0, len(self.beats) - 1)
        self.bi = bi
        self.beat_env = np.exp(-np.maximum(t - self.beats[bi], 0) * 6).astype(np.float32)
        bar0 = bi - (bi % 4)
        self.bar_env = np.exp(-np.maximum(t - self.beats[bar0], 0) * 3.5).astype(np.float32)

        snap = lambda x: float(self.beats[np.argmin(np.abs(self.beats - x))])  # noqa: E731
        self.snap = snap
        self.t_open = snap(18.3)
        self.t_drop = snap(T_DROP)
        self.t_seal = snap(162.9)   # after the last sung word, on the drop into the quiet
        self.t_hit = snap(T_HIT)
        self.verse_b = VERSE_B_TIMES
        self.chorus_b = CHORUS_B

        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        vx, vy = (xx / W - .5) * 2, (yy / H - .5) * 2
        self.vign = np.clip(1 - 0.22 * (vx * vx * .5 + vy * vy * .7), 0, 1)[..., None]
        rng = np.random.default_rng(3)
        self.grain = []
        for _ in range(8):
            g = rng.normal(0, 1, (H, W)).astype(np.float32)
            g = (g + np.roll(g, 1, 0) * .5 + np.roll(g, 1, 1) * .5) / 1.6
            self.grain.append(g[..., None])
        fib = rng.normal(0, 1, (H // 6, W // 6)).astype(np.float32)
        self.fibre = (1 - 0.02 * np.asarray(Image.fromarray(fib).resize((W, H), Image.BICUBIC)))[..., None]
        self.yy = yy[:, :1]
        self.xx = xx[:1, :]
        # build-section words: one per bar, cycling through the lyric
        self.build_words = VERSE_WORDS + WISE

    # ------------------------------------------------------------ shared elements
    def timecode(self, fr, t, x, y, color, alpha=0.5, anchor="lm"):
        f_ = int(round((t % 1) * FPS)) % FPS
        s = f"00:{int(t // 60):02d}:{int(t % 60):02d}:{f_:02d}"
        sp = sprite(s, MONO, 16, rtl=False)
        fr.blit(sp, x, y + 6, color, alpha, anchor="l" if anchor == "lm" else "r")

    def ruler(self, fr, t, y, color, alpha, x0=W * .10, x1=W * .90, head=None):
        def draw(d, ox, oy):
            d.line([(x0 - ox, y - oy), (x1 - ox, y - oy)], fill=255, width=1)
            for i in range(41):
                xx = x0 + i * (x1 - x0) / 40
                d.line([(xx - ox, y - oy), (xx - ox, y + (10 if i % 5 == 0 else 5) - oy)], fill=255, width=1)
        fr.lines_layer(draw, x0 - 2, y - 2, x1 + 2, y + 12, color, alpha * 0.4)
        if head is not None:
            hx = x0 + (x1 - x0) * head
            fr.rect(hx - 1, y - 14, hx + 1, y + 14, OCHRE, alpha)

    def ticks(self, fr, color, alpha=0.5, inset=56, size=14):
        for cx, sx in ((inset, 1), (W - inset, -1)):
            for cy, sy in ((inset, 1), (H - inset, -1)):
                fr.rect(min(cx, cx + sx * size), cy, max(cx, cx + sx * size) + 1, cy + 1, color, alpha)
                fr.rect(cx, min(cy, cy + sy * size), cx + 1, max(cy, cy + sy * size) + 1, color, alpha)

    def light_band(self, fr, cy, half_h, x0, x1, intensity=1.0, feather_x=260):
        """A horizontal aperture of warm paper light."""
        if half_h < 0.5 or intensity <= 0:
            return
        y0, y1 = int(max(0, cy - half_h - 3)), int(min(H, cy + half_h + 3))
        ys = np.arange(y0, y1, dtype=np.float32)
        prof_y = np.clip((half_h - np.abs(ys - cy)) / 2.5 + 0.5, 0, 1)
        prof_y *= 0.86 + 0.14 * np.cos(np.clip((ys - cy) / max(half_h, 1), -1, 1) * np.pi / 2)
        xs = np.arange(W, dtype=np.float32)
        prof_x = np.clip((xs - x0) / feather_x, 0, 1) * np.clip((x1 - xs) / feather_x, 0, 1)
        a = (prof_y[:, None] * prof_x[None, :] * intensity)[..., None]
        reg = fr.c[y0:y1]
        reg *= 1 - a
        reg += PAPER * a

    def hairlines(self, fr, x0, y0, x1, y1, n, settle, tremble_boost, seed, alpha=1.0, gold_last=True):
        """A field of hairlines; `settle` 0..1 calms them from the top line down to the last."""
        rng = np.random.default_rng(seed)
        phases = rng.uniform(0, 6.3, (n, 3))
        xs = np.linspace(0, 1, 120)

        def draw(d, ox, oy):
            for i in range(n):
                y = y0 + i * (y1 - y0) / (n - 1)
                calm = np.clip(settle * 1.4 - (1 - i / (n - 1)) * 0.4, 0, 1)
                amp = (1 - calm) * 9 * (1 + tremble_boost)
                if i == n - 1 and gold_last:
                    continue
                px = x0 + xs * (x1 - x0)
                py = y + amp * (0.6 * np.sin(px * 0.045 + phases[i, 0]) + 0.3 * np.sin(px * 0.13 + phases[i, 1])
                                + 0.2 * np.sin(px * 0.31 + phases[i, 2]))
                v = int(255 * (0.2 + 0.35 * i / n))
                d.line([(a - ox, b - oy) for a, b in zip(px, py)], fill=v, width=1)
        fr.lines_layer(draw, x0 - 4, y0 - 20, x1 + 4, y1 + 20, PAPER, alpha)
        if gold_last:
            fr.rect(x0, y1, x0 + (x1 - x0) * ease_out(settle * 1.2), y1 + 2, OCHRE, alpha)

    # ------------------------------------------------------------ scenes
    def scene_intro(self, fr, t, f):
        a_in = ease_io((t - 1.5) / 4)
        grow = ease_io((t - 3) / 14)
        cy = H / 2
        half_w = W * 0.40 * grow
        pulse = 0.55 + 0.45 * self.beat_env[f] * min(1, t / 12)
        if half_w > 2:
            self.light_band(fr, cy, 1.2 + 0.6 * self.beat_env[f], W / 2 - half_w, W / 2 + half_w, pulse,
                            feather_x=max(20, half_w * 0.6))
        lab = ease_io((t - 8) / 2.5)
        fr.blit(sprite(REF_FULL, SANS_THIN, 30), W / 2, cy - 200, PAPER, 0.82 * lab, anchor="c")
        self.ruler(fr, t, cy + 214, PAPER, a_in)
        self.timecode(fr, t, W * .10, cy + 244, PAPER, 0.5 * a_in)
        fr.blit(sprite("01 / 06", MONO, 16, rtl=False), W * .90, cy + 250, PAPER, 0.5 * a_in, anchor="r")

    def scene_aperture(self, fr, t, f, t0, t_close, title_alpha=1.0, idx="01 / 06"):
        open_ = ease_out((t - t0) / 1.1)
        close = ease_io((t - t_close) / 0.28) if t_close else 0
        half = 150 * open_ * (1 - close) + 1.2
        cy = H / 2
        self.light_band(fr, cy, half, W * .10, W * .90, 1.0)
        title = sprite(TITLE, SERIF_MED, 168)
        # the title is a shadow inside the light: clip it to the band
        sub = Frame(PAPER)
        sub.c = fr.c.copy()
        sub.blit(title, W / 2, cy + 64, CARBON, title_alpha, anchor="c")
        y0, y1 = int(cy - half), int(cy + half)
        fr.c[max(0, y0):min(H, y1)] = sub.c[max(0, y0):min(H, y1)]
        fr.blit(sprite(REF_FULL, SANS_THIN, 30), W / 2, cy - 200, PAPER, 0.82, anchor="c")
        self.ruler(fr, t, cy + 214, PAPER, 1.0, head=(t / T_END))
        self.timecode(fr, t, W * .10, cy + 244, PAPER, 0.5)
        fr.blit(sprite(idx, MONO, 16, rtl=False), W * .90, cy + 250, PAPER, 0.5, anchor="r")

    def scene_verse(self, fr, t, f, times, end, layout):
        """Monumental current word + karaoke transcript + hairlines that settle across the verse."""
        k = max(i for i in range(len(times)) if times[i] - 0.06 <= t) if t >= times[0] - 0.06 else 0
        prog = np.clip((t - times[0]) / (end - times[0]), 0, 1)
        exit_ = ease_io((t - (end - 0.35)) / 0.35)
        word = VERSE_WORDS[k]
        age = t - (times[k] - 0.06)
        wipe = ease_out(age / 0.32)
        rise = (1 - ease_out(age / 0.45)) * 24
        if layout == "A":
            self.hairlines(fr, 128, 250, 620, 820, 46, prog, self.beat_env[f] * 0.6 * (1 - prog), 4, 1 - exit_)
            fr.blit(sprite("01", MONO, 15, rtl=False), 128, 222, PAPER, 0.5 * (1 - exit_), anchor="l")
            size = fit_size(word, SERIF_BLACK, 300, 1040)
            sp = sprite(word, SERIF_BLACK, size)
            fr.blit(sp, W - 128, 560 + rise, PAPER, 1 - exit_, anchor="r", wipe=wipe)
            rule_w = 120 * ease_out(age / 0.6)
            fr.rect(W - 128 - rule_w, 667, W - 128, 669, OCHRE, 1 - exit_)
            ys, x_right, small = [744, 810, 876], W - 128, 40
            anchor_x = "r"
        else:
            self.hairlines(fr, 200, 820, W - 200, 960, 14, prog, self.beat_env[f] * 0.6 * (1 - prog), 9, 1 - exit_)
            size = fit_size(word, SERIF_BLACK, 290, 1500)
            sp = sprite(word, SERIF_BLACK, size)
            fr.blit(sp, W / 2, 470 + rise, PAPER, 1 - exit_, anchor="c", wipe=wipe)
            rule_w = 60 * ease_out(age / 0.6)
            fr.rect(W / 2 - rule_w, 548, W / 2 + rule_w, 550, OCHRE, 1 - exit_)
            ys, small = [618, 676, 734], 36
            anchor_x = "c"
        f_small = fnt(SANS_LIGHT, small)
        space = f_small.getlength(" ")
        for li, idxs in enumerate(VERSE_LINES):
            words = [VERSE_WORDS[i] for i in idxs]
            widths = [f_small.getlength(wd, direction="rtl") for wd in words]
            total = sum(widths) + space * (len(words) - 1)
            x = x_right if anchor_x == "r" else W / 2 + total / 2
            for i, wd, wdt in zip(idxs, words, widths):
                if i < k:
                    col, al = PAPER, 0.85
                elif i == k:
                    col, al = OCHRE, 1.0
                else:
                    col, al = PAPER, 0.16
                fr.blit(sprite(wd, SANS_LIGHT, small), x, ys[li], col, al * (1 - exit_), anchor="r")
                x -= wdt + space
        self.timecode(fr, t, (W - 128) if layout == "A" else W / 2 + 60, 985 if layout == "A" else 1010,
                      PAPER, 0.45 * (1 - exit_))

    def scene_chorus(self, fr, t, f, t1, t2, paper_bg, big=330, echoes=4):
        ink = CARBON if paper_bg else PAPER
        if paper_bg:
            fr.c *= self.fibre
        age = t - t1
        land = ease_out(age / 0.22)
        trace = np.exp(-age * 2.2) + 0.35 * self.beat_env[f]
        sp = sprite(WISE[0], SERIF_BLACK, fit_size(WISE[0], SERIF_BLACK, big, W - 220))
        cy = 520
        scale = 1.0 + 0.10 * (1 - land) + 0.006 * self.beat_env[f]
        for k_ in range(echoes, 0, -1):
            fr.blit(sp, W / 2, cy - k_ * 52 * trace, ink, 0.075 * (echoes + 1 - k_) / echoes * min(1, trace * 1.4),
                    anchor="c", scale=scale)
        fr.blit(sp, W / 2, cy, ink, min(1, age / 0.06), anchor="c", scale=scale)
        if t >= t2 - 0.06:
            a2 = t - (t2 - 0.06)
            fr.blit(sprite(WISE[1], SERIF_LIGHT, 170), W / 2, 850 + (1 - ease_out(a2 / 0.5)) * 20, OCHRE,
                    1.0, anchor="c", wipe=ease_out(a2 / 0.4))
        fr.rect(W / 2 - 40, 912, W / 2 + 40, 913, ink, 0.7)
        self.timecode(fr, t, W / 2 - 64, 944, ink, 0.55)
        self.ticks(fr, ink, 0.5)

    def scene_blinds(self, fr, t, f):
        """Instrumental after the drop: light through slats, opening and closing on the beat."""
        n = 9
        span = (t - self.t_drop) / (69.1 - self.t_drop)
        collapse = ease_io((t - 66.9) / 2.0)
        for i in range(n):
            cy = H * (0.18 + 0.64 * i / (n - 1)) * (1 - collapse) + H / 2 * collapse
            bi = self.bi[f]
            lit = ((bi + i) % 3 == 0) * 0.6 + 0.4
            half = (6 + 26 * self.beat_env[f] * lit * (0.4 + 0.6 * span)) * (1 - 0.8 * collapse) + 1.2
            x0 = W * 0.08 + (i % 2) * 40
            self.light_band(fr, cy, half, x0, W - x0, 0.55 + 0.45 * lit, feather_x=200)
        self.ruler(fr, t, H - 120, PAPER, 0.8, head=t / T_END)
        self.timecode(fr, t, W * .10, H - 90, PAPER, 0.5)
        fr.blit(sprite("02 / 06", MONO, 16, rtl=False), W * .90, H - 84, PAPER, 0.5, anchor="r")

    def scene_build(self, fr, t, f):
        """Instrumental build: an editorial montage cut on the bar (then every 2 beats, then every beat)."""
        b0 = int(np.argmin(np.abs(self.beats - T_BUILD)))
        b = self.bi[f]
        rel = b - b0
        late = self.beats[b] > 123.0
        step = 1 if self.beats[b] > 127.0 else (2 if late else 4)
        cut = (rel // step)
        variant = cut % 3
        word = self.build_words[cut % len(self.build_words)]
        prog = np.clip((t - T_BUILD) / (T_FINAL - T_BUILD), 0, 1)
        if variant == 0:     # giant word on paper, fitted inside the margins
            fr.c[:] = PAPER
            fr.c *= self.fibre
            sp = fitted(word, SERIF_BLACK, 560, W - 256, 700)
            fr.blit(sp, W - 128, (H - sp.m.shape[0]) / 2 - 20 + sp.oy, CARBON, 1.0, anchor="r")
            fr.rect(128, 880, 128 + 300 * self.bar_env[f], 882, OCHRE, 1)
            self.timecode(fr, t, 128, 930, CARBON, 0.55)
        elif variant == 1:   # carbon with settling field above a fitted word
            self.hairlines(fr, 128, 140, W - 128, 380, 22, prog, 1.5 * self.beat_env[f], 21 + cut % 5, 0.9)
            sp = fitted(word, SERIF_BLACK, 520, W - 256, 560)
            fr.blit(sp, W / 2, 450 + sp.oy, PAPER, 1.0, anchor="c")
        else:                # the aperture, word as shadow
            self.light_band(fr, H / 2, 150 + 20 * self.beat_env[f], W * .10, W * .90, 1.0)
            sub_sp = sprite(word, SERIF_MED, 190)
            sub = Frame(PAPER)
            sub.c = fr.c.copy()
            sub.blit(sub_sp, W / 2, H / 2 + 70, CARBON, 1.0, anchor="c")
            fr.c[int(H / 2 - 150):int(H / 2 + 150)] = sub.c[int(H / 2 - 150):int(H / 2 + 150)]
            self.ruler(fr, t, H / 2 + 214, PAPER, 1.0, head=t / T_END)
        fr.blit(sprite(f"{3:02d} / 06", MONO, 16, rtl=False), W - 128, 70, CARBON if variant == 0 else PAPER,
                0.5, anchor="r")
        return variant  # 0 paper, 1 carbon type, 2 aperture

    def scene_final(self, fr, t, f):
        """'Sealed and closed': lines arrive, then two plates slam shut on the beat, leaving one slit."""
        cy = H / 2
        seal = ease_out((t - self.t_seal) / 0.16)
        slit_w = (0.30 + 0.70 * ease_io((t - T_FINAL) / (self.t_seal - T_FINAL)))
        slit_w *= 1 - 0.6 * ease_io((t - self.t_seal - 0.5) / 2.5)
        fade_out = 1 - ease_io((t - (T_HIT - 1.2)) / 1.0)
        glow = 0.65 + 0.35 * self.beat_env[f] + 0.8 * np.exp(-max(0, t - self.t_seal) * 3) * (t >= self.t_seal)
        # text on the dark field (hidden by the plates once sealed)
        first, second = SEALED_TIMES
        k = 0
        for li, words in enumerate(SEALED):
            y = cy - 92 if li == 0 else cy + 140
            f92 = fnt(SERIF_LIGHT, 92)
            space = f92.getlength(" ")
            widths = [f92.getlength(w_, direction="rtl") for w_ in words]
            x = W / 2 + (sum(widths) + space * (len(words) - 1)) / 2
            for i, (wd, wdt) in enumerate(zip(words, widths)):
                tw, tw2 = first[k] - 0.04, second[k] - 0.04  # second rendition: each word glows ochre
                k += 1
                a = ease_out((t - tw) / 0.35)
                col = OCHRE if (t >= tw2 - 0.05 and t < tw2 + 0.6) else PAPER
                fr.blit(sprite(wd, SERIF_LIGHT, 92), x, y + (1 - a) * 16, col, a * (1 - seal), anchor="r")
                x -= wdt + space
        # plates closing
        if seal > 0:
            gap = 6 + (H / 2) * (1 - seal)
            tone = np.float32(17)
            fr.rect(0, 0, W, cy - gap, np.array([tone, tone, tone * 1.04]), 1.0)
            fr.rect(0, cy + gap, W, H, np.array([tone, tone, tone * 1.04]), 1.0)
        xs = np.arange(W, dtype=np.float32)
        prof = np.clip(1 - np.abs(xs - W / 2) / (W * 0.46 * max(slit_w, 0.01)), 0, 1) ** 0.7
        ys = np.arange(int(cy - 40), int(cy + 40), dtype=np.float32)
        core = np.exp(-((ys - cy) / 2.2) ** 2)[:, None] * prof[None, :] * 1.25 * glow
        halo = np.exp(-((ys - cy) / 14) ** 2)[:, None] * prof[None, :] * 0.55 * glow
        reg = fr.c[int(cy - 40):int(cy + 40)]
        reg += (core[..., None] * PAPER + halo[..., None] * OCHRE) * fade_out
        if t >= self.t_seal:
            lab = ease_io((t - (self.t_seal + 1.5)) / 2) * fade_out
            fr.blit(sprite(REF_END, SANS_THIN, 26), W / 2, H - 96, PAPER, 0.7 * lab, anchor="c")


    # ------------------------------------------------------------ frame assembly
    def frame(self, f):
        t = f / FPS
        streak, halation, bg = 0.0, 0.12, CARBON
        flash = 0.0
        vb = self.verse_b
        if t < self.t_open:
            fr = Frame(bg)
            self.scene_intro(fr, t, f)
            streak, halation = 0.6, 0.3
        elif t < VERSE_A_TIMES[0] - 0.06:
            fr = Frame(bg)
            self.scene_aperture(fr, t, f, self.t_open, VERSE_A_TIMES[0] - 0.36)
            streak, halation = 0.55, 0.30
        elif t < CHORUS_A[0][0] - 0.03:
            fr = Frame(bg)
            self.scene_verse(fr, t, f, VERSE_A_TIMES, VERSE_A_END, "A")
        elif t < CHORUS_A[1][0] - 0.03:
            fr = Frame(PAPER)
            self.scene_chorus(fr, t, f, CHORUS_A[0][0], CHORUS_A[0][1], True)
            halation = 0.0
        elif t < self.t_drop:
            fr = Frame(bg)
            self.scene_chorus(fr, t, f, CHORUS_A[1][0], CHORUS_A[1][1], False)
        elif t < vb[0] - 0.06:
            fr = Frame(bg)
            self.scene_blinds(fr, t, f)
            streak, halation = 0.7, 0.32
            flash = np.exp(-(t - self.t_drop) * 9) * 0.9
        elif t < self.chorus_b[0][0] - 0.03:
            fr = Frame(bg)
            self.scene_verse(fr, t, f, vb, VERSE_A_END + B_SHIFT, "B")
        elif t < T_BUILD:
            (c1, c2, _), (d1, d2, _) = self.chorus_b
            first = t < d1 - 0.03
            t1, t2 = (c1, c2) if first else (d1, d2)
            # alternate paper/carbon on every downbeat
            bars = int((self.bi[f] - int(np.argmin(np.abs(self.beats - t1)))) // 4)
            paper = (bars % 2 == 0) if first else (bars % 2 == 1)
            fr = Frame(PAPER if paper else bg)
            self.scene_chorus(fr, t, f, t1, t2, paper, big=350, echoes=5)
            halation = 0.0 if paper else 0.12
        elif t < T_FINAL - 0.06:
            fr = Frame(bg)
            variant = self.scene_build(fr, t, f)
            streak, halation = {0: (0.0, 0.0), 1: (0.0, 0.08), 2: (0.5, 0.2)}[variant]
        elif t < self.t_hit - 0.03:
            fr = Frame(bg)
            self.scene_final(fr, t, f)
            streak, halation = 0.9, 0.35
        else:
            fr = Frame(bg)
            self.scene_aperture(fr, t, f, self.t_hit - 0.6, 179.5, idx="06 / 06")
            streak, halation = 0.6, 0.3
            flash = np.exp(-(t - self.t_hit) * 8) * 0.6
        return self.finish(fr.c, t, f, streak, halation, flash)

    def finish(self, c, t, f, streak, halation, flash):
        lum = c.mean(-1, keepdims=True)
        if halation or streak:
            small = Image.fromarray(np.clip(np.clip((lum - 150) / 105, 0, 1) * c, 0, 255).astype(np.uint8))
            if halation:
                q = small.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5))
                c += np.asarray(q.resize((W, H), Image.BILINEAR), np.float32) * np.array([1, .78, .55]) * halation
            if streak:
                s_ = small.resize((W // 24, H // 2), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1.2))
                c += np.asarray(s_.resize((W, H), Image.BILINEAR), np.float32) * np.array([.75, .82, 1]) * streak
        if flash > 0.01:
            c += PAPER * flash
        c *= self.vign
        c += self.grain[f % 8] * (3.5 + 2.5 * (1 - lum / 255))
        # gentle push-in on the beat
        z = 1 + 0.004 * self.beat_env[f]
        img = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8))
        if z > 1.0005:
            bw, bh = W / z, H / z
            img = img.resize((W, H), Image.BILINEAR, box=((W - bw) / 2, (H - bh) / 2, (W + bw) / 2, (H + bh) / 2))
        fade = min(1.0, t / 0.8, max(0.0, (T_END - t) / 0.6))
        if fade < 1:
            return (np.asarray(img, np.float32) * fade).astype(np.uint8)
        return np.asarray(img)


# ---------------------------------------------------------------- driver

def render_chunk(args):
    data, f0, f1, out = args
    clip = Clip(*data)
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
         "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for f in range(f0, f1):
        enc.stdin.write(clip.frame(f).tobytes())
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
    ap.add_argument("--stills")
    a = ap.parse_args()
    total = int(duration(a.audio) * FPS)
    print("analysing audio...", flush=True)
    beats, env, _bass, _bands = analyse(a.audio, total)
    data = (beats, env, total)
    if a.stills:
        os.makedirs(a.out, exist_ok=True)
        clip = Clip(*data)
        for ts in a.stills.split(","):
            f = int(round(float(ts) * FPS))
            Image.fromarray(clip.frame(f)).save(os.path.join(a.out, f"s_{float(ts):06.2f}.png"))
        return
    f0 = int(a.start * FPS)
    f1 = min(total, int(a.end * FPS)) if a.end else total
    tmp = tempfile.mkdtemp(prefix="clip5_")
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
