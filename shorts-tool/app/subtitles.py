"""Turn subtitle lines + a style dict into an ASS file (1080x1920 canvas).

The same style dict drives the browser preview, so every px value here is in
1080x1920 canvas pixels and must be rendered identically by libass.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

W, H = 1080, 1920
MARGIN = 54  # 5% side margin, matches max-width: 90% in the preview
FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"

DEFAULT_STYLE = {
    "font": "Heebo Black",
    "size": 88,
    "color": "#FFFFFF",
    "outlineColor": "#000000",
    "outlineWidth": 7,
    "shadow": 0,
    "shadowColor": "#000000",
    "bgEnabled": False,
    "bgColor": "#000000",
    "bgOpacity": 0.7,
    "bgPadding": 16,
    "highlightEnabled": True,
    "highlightColor": "#FFE600",
    "letterSpacing": 0,
    "posY": 72,          # % from top, centre of the subtitle block
    "align": "center",   # left | center | right
    "animation": "pop",  # none | pop | fade | reveal
    "titleText": "",
    "titleFont": "Heebo Black",
    "titleSize": 64,
    "titleColor": "#000000",
    "titleBgColor": "#FFFFFF",
    "titlePosY": 12,
}


def load_fonts() -> dict[str, dict]:
    data = json.loads((FONTS_DIR / "fonts.json").read_text(encoding="utf-8"))
    return {f["name"]: f for f in data}


def _color(hex_color: str, opacity: float = 1.0) -> str:
    """#RRGGBB + opacity -> ASS &HAABBGGRR."""
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", hex_color or "")
    rgb = m.group(1) if m else "FFFFFF"
    r, g, b = rgb[0:2], rgb[2:4], rgb[4:6]
    alpha = int(round((1.0 - max(0.0, min(1.0, opacity))) * 255))
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def _inline(hex_color: str) -> str:
    return _color(hex_color)[4:]  # BBGGRR


def _ts(t: float) -> str:
    t = max(t, 0.0)
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _esc(text: str) -> str:
    return (text.replace("\\", "").replace("{", "(").replace("}", ")")
            .replace("\n", " ").strip())


def _num(style: dict, key: str, lo: float, hi: float) -> float:
    try:
        v = float(style.get(key, DEFAULT_STYLE[key]))
    except (TypeError, ValueError):
        v = float(DEFAULT_STYLE[key])
    return max(lo, min(hi, v))


def build_ass(lines: list[dict], style: dict | None, duration: float) -> str:
    """lines: [{s, e, words: [{t, s, e}]}] with times relative to clip start."""
    st = {**DEFAULT_STYLE, **(style or {})}
    fonts = load_fonts()
    font = st["font"] if st["font"] in fonts else DEFAULT_STYLE["font"]
    tfont = st["titleFont"] if st["titleFont"] in fonts else font

    size = _num(st, "size", 10, 400)
    outline = _num(st, "outlineWidth", 0, 40)
    shadow = _num(st, "shadow", 0, 40)
    spacing = _num(st, "letterSpacing", -10, 60)
    pad = _num(st, "bgPadding", 0, 80)
    tsize = _num(st, "titleSize", 10, 300)
    bg_on = bool(st["bgEnabled"])

    align = {"left": 4, "center": 5, "right": 6}.get(st["align"], 5)
    x = {4: MARGIN, 5: W // 2, 6: W - MARGIN}[align]
    y = round(H * _num(st, "posY", 0, 100) / 100)
    ty = round(H * _num(st, "titlePosY", 0, 100) / 100)

    def style_row(name, fname, px, primary, outline_c, back_c, border_style,
                  bord, shad, an, sp=0.0):
        ass_size = round(px * fonts[fname]["scale"], 2)
        return (f"Style: {name},{fname},{ass_size},{primary},{primary},"
                f"{outline_c},{back_c},0,0,0,0,100,100,{sp},0,{border_style},"
                f"{bord},{shad},{an},{MARGIN},{MARGIN},0,-1")

    clear = "&HFF000000"
    styles = [
        style_row("Sub", font, size, _color(st["color"]),
                  _color(st["outlineColor"]), _color(st["shadowColor"]),
                  1, outline, shadow, align, spacing),
        style_row("SubBox", font, size, clear,
                  _color(st["bgColor"], _num(st, "bgOpacity", 0, 1)), clear,
                  3, pad, 0, align, spacing),
        style_row("Title", tfont, tsize, _color(st["titleColor"]),
                  clear, clear, 1, 0, 0, 5),
        style_row("TitleBox", tfont, tsize, clear,
                  _color(st["titleBgColor"]), clear, 3, 18, 0, 5),
    ]

    events: list[str] = []

    def ev(layer, start, end, style_name, tags, text):
        if end - start < 0.02:
            return
        events.append(f"Dialogue: {layer},{_ts(start)},{_ts(end)},{style_name},"
                      f",0,0,0,,{{{tags}}}{text}")

    title = _esc(str(st.get("titleText") or ""))
    if title:
        pos = f"\\an5\\pos({W // 2},{ty})"
        # \\ybord0: boxes of wrapped lines must touch, not overlap
        ev(0, 0, duration, "TitleBox", pos + "\\ybord0", title)
        ev(1, 0, duration, "Title", pos, title)

    anim = st["animation"]
    hl = bool(st["highlightEnabled"])
    hl_c, base_c = _inline(st["highlightColor"]), _inline(st["color"])

    for line in lines:
        words = [dict(w, t=_esc(str(w["t"]))) for w in line.get("words", [])]
        words = [w for w in words if w["t"]]
        if not words:
            continue
        ls = max(float(line["s"]), 0.0)
        le = min(float(line["e"]), duration)
        if le <= ls:
            continue
        pos = f"\\pos({x},{y})"
        intro = ""
        if anim == "pop":
            intro = "\\fscx82\\fscy82\\t(0,110,\\fscx100\\fscy100)"
        elif anim == "fade":
            intro = "\\fad(140,0)"
        full = " ".join(w["t"] for w in words)

        if bg_on:
            ev(0, ls, le, "SubBox", pos + "\\ybord0" + intro, full)

        if not hl and anim != "reveal":
            ev(1, ls, le, "Sub", pos + intro, full)
            continue

        # one event per active word
        for i, w in enumerate(words):
            ws = ls if i == 0 else max(min(float(w["s"]), le), ls)
            we = le if i == len(words) - 1 else max(min(float(words[i + 1]["s"]), le), ls)
            parts = []
            for k, other in enumerate(words):
                if anim == "reveal" and k > i:
                    parts.append(f"{{\\alpha&HFF&}}{other['t']}")
                elif k == i and hl:
                    parts.append(f"{{\\1c&H{hl_c}&}}{other['t']}{{\\1c&H{base_c}&}}")
                else:
                    parts.append(other["t"])
            ev(1, ws, we, "Sub", pos + (intro if i == 0 else ""), " ".join(parts))

    header = "\n".join([
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "YCbCr Matrix: None", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
        "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding",
        *styles, "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text",
    ])
    return header + "\n" + "\n".join(events) + "\n"
