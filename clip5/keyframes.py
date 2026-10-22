#!/usr/bin/env python3
"""Key frames for the "Sealed Light" (אור חתום) lyric-video concept.

Studio-grade editorial motion design: carbon black, unbleached paper and a
single gilded ochre; a classical Hebrew serif at monumental scale; light
admitted through narrow apertures; hairline fields that settle from
trembling to still. Frames are drawn at 2x and downsampled, then finished
with film grain, halation and a faint anamorphic streak.

Usage: python3 keyframes.py OUT_DIR
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
SKILL_FONTS = "/root/.claude/skills/synced/8852199b-0193-4c47-8313-1b6abe44134b_44f53d87-c3b6-4f49-9b0f-035c322d54d0/canvas-design/canvas-fonts"

W, H = 1920, 1080
S = 2                      # supersampling
SW, SH = W * S, H * S

CARBON = np.array([11, 11, 12], np.float32)
PAPER = np.array([237, 230, 216], np.float32)
OCHRE = np.array([200, 161, 90], np.float32)


def fnt(name, size):
    path = os.path.join(FONTS, name) if name.endswith(".woff") else os.path.join(SKILL_FONTS, name)
    return ImageFont.truetype(path, int(size * S), layout_engine=ImageFont.Layout.RAQM)


SERIF_LIGHT = "frank-ruhl-libre-hebrew-300-normal.woff"
SERIF_MED = "frank-ruhl-libre-hebrew-500-normal.woff"
SERIF_BLACK = "frank-ruhl-libre-hebrew-900-normal.woff"
SANS_THIN = "heebo-hebrew-100-normal.woff"
SANS_LIGHT = "heebo-hebrew-300-normal.woff"
MONO = "DMMono-Regular.ttf"


# ---------------------------------------------------------------- canvas helpers

class Canvas:
    def __init__(self, bg):
        self.c = np.ones((SH, SW, 3), np.float32) * bg

    def layer(self, draw_fn):
        m = Image.new("L", (SW, SH), 0)
        draw_fn(ImageDraw.Draw(m))
        return np.asarray(m, np.float32) / 255

    def paint(self, mask, color, alpha=1.0):
        a = (mask * alpha)[..., None]
        self.c = self.c * (1 - a) + np.asarray(color, np.float32) * a

    def add(self, mask, color, k=1.0):
        self.c += (mask * k)[..., None] * np.asarray(color, np.float32)

    def text(self, s, font, xy, color, alpha=1.0, anchor="mm", rtl=True):
        x, y = xy
        m = self.layer(lambda d: d.text((x * S, y * S), s, font=font, fill=255, anchor=anchor,
                                        direction="rtl" if rtl else None))
        self.paint(m, color, alpha)
        return m

    def hline(self, x0, x1, y, color, alpha=1.0, width=1.0):
        m = self.layer(lambda d: d.line([(x0 * S, y * S), (x1 * S, y * S)], fill=255, width=max(1, int(width * S))))
        self.paint(m, color, alpha)

    def vline(self, x, y0, y1, color, alpha=1.0, width=1.0):
        m = self.layer(lambda d: d.line([(x * S, y0 * S), (x * S, y1 * S)], fill=255, width=max(1, int(width * S))))
        self.paint(m, color, alpha)

    def finish(self, grain=5.0, halation=0.22, streak=0.0, vignette=0.22, seed=0):
        img = Image.fromarray(np.clip(self.c, 0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)
        c = np.asarray(img, np.float32)
        lum = c.mean(-1)
        bright = np.clip((lum - 150) / 105, 0, 1)[..., None] * c
        if halation:
            hb = np.asarray(Image.fromarray(np.clip(bright, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(18)),
                            np.float32)
            c += hb * np.array([1.0, 0.78, 0.55]) * halation
        if streak:
            sm = Image.fromarray(np.clip(bright, 0, 255).astype(np.uint8)).resize((W // 24, H), Image.BILINEAR)
            st = np.asarray(sm.filter(ImageFilter.GaussianBlur(1.5)).resize((W, H), Image.BILINEAR), np.float32)
            c += st * np.array([0.75, 0.82, 1.0]) * streak
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        vx, vy = (xx / W - .5) * 2, (yy / H - .5) * 2
        c *= np.clip(1 - vignette * (vx * vx * .5 + vy * vy * .7), 0, 1)[..., None]
        rng = np.random.default_rng(seed)
        g = rng.normal(0, 1, (H, W)).astype(np.float32)
        g = (g + np.roll(g, 1, 0) * 0.5 + np.roll(g, 1, 1) * 0.5) / 1.6
        c += g[..., None] * grain * (0.6 + 0.4 * (1 - lum[..., None] / 255))
        return Image.fromarray(np.clip(c, 0, 255).astype(np.uint8))


def feather_box(x0, x1, y0, y1, fx, fy):
    yy, xx = np.mgrid[0:SH, 0:SW].astype(np.float32) / S
    ax = np.clip((xx - x0) / fx, 0, 1) * np.clip((x1 - xx) / fx, 0, 1)
    ay = np.clip((yy - y0) / fy, 0, 1) * np.clip((y1 - yy) / fy, 0, 1)
    return ax * ay


def ticks(cv, color, alpha=0.55, inset=56, size=14):
    """Registration marks in the four corners."""
    for cx, sx in ((inset, 1), (W - inset, -1)):
        for cy, sy in ((inset, 1), (H - inset, -1)):
            cv.hline(cx, cx + sx * size, cy, color, alpha)
            cv.vline(cx, cy, cy + sy * size, color, alpha)


# ---------------------------------------------------------------- frames

def frame_aperture():
    """Opening: the title revealed as a shadow inside a single horizontal slit of light."""
    cv = Canvas(CARBON)
    y0, y1 = H * 0.5 - 150, H * 0.5 + 150
    band = feather_box(W * 0.10, W * 0.90, y0, y1, 260, 3)
    yy = np.mgrid[0:SH, 0:SW][0].astype(np.float32) / S
    falloff = 0.86 + 0.14 * np.cos((yy - H / 2) / 150 * np.pi / 2)
    cv.paint(band, PAPER, 1.0)
    cv.c *= (1 - band * (1 - falloff))[..., None]
    cv.text("וְהַמַּשְׂכִּלִים יָבִינוּ", fnt(SERIF_MED, 168), (W / 2, H * 0.5 + 6), CARBON)
    cv.text("דָּנִיֵּאל", fnt(SANS_THIN, 30), (W / 2 + 70, H * 0.5 - 214), PAPER, alpha=0.82)
    cv.text("12 : 9—10", fnt(MONO, 19), (W / 2 - 62, H * 0.5 - 212), PAPER, alpha=0.6, rtl=False)
    cv.hline(W * 0.10, W * 0.90, H * 0.5 + 214, PAPER, 0.28)
    for i in range(0, 41):
        x = W * 0.10 + i * (W * 0.80) / 40
        cv.vline(x, H * 0.5 + 214, H * 0.5 + 214 + (10 if i % 5 == 0 else 5), PAPER, 0.35)
    cv.text("00:00:18:12", fnt(MONO, 16), (W * 0.10, H * 0.5 + 250), PAPER, 0.5, anchor="lm", rtl=False)
    cv.text("01 / 06", fnt(MONO, 16), (W * 0.90, H * 0.5 + 250), PAPER, 0.5, anchor="rm", rtl=False)
    return cv.finish(halation=0.30, streak=0.55, seed=1)


def frame_refinement():
    """Verse: a monumental word; a field of hairlines settles from trembling to still."""
    cv = Canvas(CARBON)
    # hairline field: purification as process
    fx0, fx1, fy0, fy1, n = 128, 620, 250, 820, 46
    rng = np.random.default_rng(4)
    for i in range(n):
        y = fy0 + i * (fy1 - fy0) / (n - 1)
        amp = (1 - i / (n - 1)) ** 1.6 * 9
        xs = np.linspace(fx0, fx1, 160)
        ph = rng.uniform(0, 6.3, 3)
        ys = y + amp * (0.6 * np.sin(xs * 0.045 + ph[0]) + 0.3 * np.sin(xs * 0.13 + ph[1])
                        + 0.25 * rng.normal(0, 1, len(xs)) * (amp > 0.4))
        last = i == n - 1
        pts = [(float(a) * S, float(b) * S) for a, b in zip(xs, ys)]
        m = cv.layer(lambda d: d.line(pts, fill=255, width=S if not last else 2 * S))
        cv.paint(m, OCHRE if last else PAPER, 1.0 if last else 0.18 + 0.32 * i / n)
    cv.text("01", fnt(MONO, 15), (fx0, fy0 - 34), PAPER, 0.5, anchor="lm", rtl=False)
    cv.text("46", fnt(MONO, 15), (fx0, fy1 + 34), OCHRE, 0.9, anchor="lm", rtl=False)
    cv.vline(fx1 + 90, 180, 900, PAPER, 0.16)
    # monumental word, right aligned (reading start)
    cv.text("יִתְבָּרְרוּ", fnt(SERIF_BLACK, 300), (W - 128, 470), PAPER, anchor="rm")
    cv.hline(W - 128 - 120, W - 128, 668, OCHRE, 1.0, 2)
    lines = ["וְיִתְלַבְּנוּ וְיִצָּרְפוּ רַבִּים", "וְהִרְשִׁיעוּ רְשָׁעִים", "וְלֹא יָבִינוּ כָּל רְשָׁעִים"]
    for i, l in enumerate(lines):
        cv.text(l, fnt(SANS_LIGHT, 40), (W - 128, 730 + i * 66), PAPER, 0.92, anchor="rm")
    cv.text("00:01:09:04", fnt(MONO, 16), (W - 128, 975), PAPER, 0.45, anchor="rm", rtl=False)
    return cv.finish(halation=0.18, seed=2)


def frame_inversion():
    """Drop / chorus: the frame flips to paper; the line lands with a stepped motion trace."""
    cv = Canvas(PAPER)
    yy, xx = np.mgrid[0:SH, 0:SW].astype(np.float32)
    fibre = np.random.default_rng(7).normal(0, 1, (SH // 8, SW // 8)).astype(np.float32)
    fibre = np.asarray(Image.fromarray(fibre).resize((SW, SH), Image.BICUBIC))
    cv.c *= (1 - 0.018 * fibre)[..., None]
    word = "וְהַמַּשְׂכִּלִים"
    f = fnt(SERIF_BLACK, 330)
    cy = 430
    for k in range(4, 0, -1):  # stepped echoes rising above the word: a frozen trace of the slam
        cv.text(word, f, (W / 2, cy - k * 52), CARBON, alpha=0.075 * (5 - k) / 4)
    cv.text(word, f, (W / 2, cy), CARBON)
    cv.text("יָבִינוּ", fnt(SERIF_LIGHT, 170), (W / 2, 790), OCHRE)
    cv.hline(W / 2 - 40, W / 2 + 40, 912, CARBON, 0.7)
    cv.text("00:01:24:07", fnt(MONO, 16), (W / 2, 950), CARBON, 0.55, rtl=False)
    ticks(cv, CARBON, 0.5)
    return cv.finish(grain=4.0, halation=0.0, vignette=0.12, seed=3)


def frame_sealed():
    """Ending: two plates close over the light; a single slit remains between the lines."""
    cv = Canvas(CARBON)
    yy, xx = np.mgrid[0:SH, 0:SW].astype(np.float32) / S
    gap = 5
    plate = (np.abs(yy - H / 2) > gap).astype(np.float32)
    brushed = np.random.default_rng(9).normal(0, 1, (SH, 1)).astype(np.float32)
    tone = 17 + 3 * brushed + 4 * np.clip(1 - np.abs(yy - H / 2) / 300, 0, 1)
    cv.c = cv.c * (1 - plate[..., None]) + tone[..., None] * np.array([1, 1, 1.04]) * plate[..., None]
    slit = np.exp(-((yy - H / 2) / 2.2) ** 2) * np.clip(1 - np.abs(xx - W / 2) / (W * 0.46), 0, 1) ** 0.7
    cv.add(slit, PAPER, 1.25)
    cv.add(np.exp(-((yy - H / 2) / 14) ** 2) * slit.max(0)[None, :], OCHRE, 0.55)
    cv.text("כִּי סְתֻמִים וַחֲתֻמִים", fnt(SERIF_LIGHT, 92), (W / 2, H / 2 - 120), PAPER)
    cv.text("הַדְּבָרִים עַד עֵת קֵץ", fnt(SERIF_LIGHT, 92), (W / 2, H / 2 + 112), PAPER)
    cv.text("דָּנִיֵּאל", fnt(SANS_THIN, 26), (W / 2 + 52, H - 104), PAPER, 0.7)
    cv.text("12 : 9", fnt(MONO, 16), (W / 2 - 50, H - 102), PAPER, 0.5, rtl=False)
    return cv.finish(halation=0.35, streak=0.9, seed=4)


# ---------------------------------------------------------------- presentation sheet

def seg_text(d, x_right, y, segments, font, color, dot=(200, 161, 90), gap=26):
    """RTL segments separated by small drawn dots (the Hebrew font subsets carry no punctuation)."""
    x = x_right
    for i, seg in enumerate(segments):
        if i:
            d.ellipse([x - gap / 2 - 3, y - 3, x - gap / 2 + 3, y + 3], fill=dot)
            x -= gap
        wdt = font.getlength(seg, direction="rtl")
        d.text((x, y), seg, font=font, fill=color, anchor="rm", direction="rtl")
        x -= wdt


def sheet(frames, path):
    tw, th = 930, 523
    sheet_bg = (16, 16, 17)
    Sh = Image.new("RGB", (1920, 168 + 2 * (th + 76)), sheet_bg)
    d = ImageDraw.Draw(Sh)
    big = ImageFont.truetype(os.path.join(FONTS, SERIF_LIGHT), 66, layout_engine=ImageFont.Layout.RAQM)
    sub = ImageFont.truetype(os.path.join(FONTS, SANS_LIGHT), 28, layout_engine=ImageFont.Layout.RAQM)
    lab = ImageFont.truetype(os.path.join(FONTS, SANS_LIGHT), 27, layout_engine=ImageFont.Layout.RAQM)
    mono = ImageFont.truetype(os.path.join(SKILL_FONTS, MONO), 17)
    d.text((1900, 34), "אור חתום", font=big, fill=tuple(PAPER.astype(int)), anchor="ra", direction="rtl")
    d.text((1900 - big.getlength("אור חתום", direction="rtl") - 22, 64), "05", font=ImageFont.truetype(
        os.path.join(SKILL_FONTS, MONO), 30), fill=(200, 161, 90), anchor="rm")
    seg_text(d, 1900, 134, ["עיצוב טיפוגרפי קולנועי", "שחור נייר וזהב אוקר", "אור שנכנס דרך סדק",
                            "קווים שמזדככים עד שקט"], sub, (190, 185, 175))
    d.line([(20, 156), (1900, 156)], fill=(60, 58, 55), width=1)
    labels = [["פתיחה", "הכותרת כצל בתוך סדק של אור"], ["בית", "מילה מונומנטלית וקווים שמזדככים"],
              ["פזמון", "היפוך לנייר ועקבות תנועה"], ["סיום", "הלוחות נסגרים על האור"]]
    for i, (fr, lb) in enumerate(zip(frames, labels)):
        c, r = 1 - i % 2, i // 2
        x, y = 20 + c * (tw + 20), 176 + r * (th + 76)
        Sh.paste(fr.resize((tw, th), Image.LANCZOS), (x, y))
        seg_text(d, x + tw, y + th + 34, lb, lab, (205, 200, 190))
        d.text((x, y + th + 20), f"0{i + 1}", font=mono, fill=(200, 161, 90), anchor="la")
    Sh.save(path, quality=94)


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    frames = []
    for i, fn in enumerate((frame_aperture, frame_refinement, frame_inversion, frame_sealed)):
        fr = fn()
        fr.save(os.path.join(out, f"e{i + 1}.png"))
        frames.append(fr)
        print("frame", i + 1, flush=True)
    sheet(frames, os.path.join(out, "mockup_e.jpg"))


if __name__ == "__main__":
    main()
