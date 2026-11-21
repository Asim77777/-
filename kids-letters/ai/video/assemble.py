"""Assemble the 10-second intro: three shots with soft crossfades, kids' voices, music bed and
burned-in Hebrew subtitles (ASS through libass with fribidi/harfbuzz, so right-to-left is correct).
Usage: python3 assemble.py [--noam out/shot_noam_s7.mp4 --tamar ... --pair ...] -> showcase/video/intro_sample.mp4"""
import os
import sys
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
AI = os.path.dirname(HERE)
OUT_DIR = os.path.join(AI, 'showcase', 'video')
O = os.path.join(HERE, 'out')
FONT_DIR = os.path.join(HERE, 'fonts')
W, H, FPS = 1080, 1920, 24
XF = 0.25  # crossfade seconds


def dur(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                       capture_output=True, text=True, check=True)
    return float(r.stdout)


def ts(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f'{int(h)}:{int(m):02d}:{s:05.2f}'


def write_ass(path, lines):
    """lines: (start, end, text, color as ASS &HBBGGRR)"""
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Kid,Rubik,92,&H00FFFFFF,&H00FFFFFF,&H00301A10,&H64000000,-1,0,0,0,100,100,0,0,1,7,3,2,80,80,330,177

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    rlm = '\u200f'  # right-to-left marks: libass otherwise lays the line out left-to-right and moves the final '!'
    ev = ''.join(f'Dialogue: 0,{ts(a)},{ts(b)},Kid,,0,0,0,,{{\\fad(120,120)\\c{c}}}{rlm}{txt}{rlm}\n' for a, b, txt, c in lines)
    open(path, 'w', encoding='utf-8').write(head + ev)


def main():
    args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
    shots = [args.get('--noam', os.path.join(O, 'shot_noam_s7.mp4')),
             args.get('--tamar', os.path.join(O, 'shot_tamar_s7.mp4')),
             args.get('--pair', os.path.join(O, 'shot_pair_s7.mp4'))]
    d = [dur(s) for s in shots]
    starts = [0.0, d[0] - XF, d[0] + d[1] - 2 * XF]
    total = starts[2] + d[2]
    voices = json.load(open(os.path.join(O, 'voices.json')))['lines']
    # voice cues: shortly after each shot starts
    cues = [('noam', starts[0] + 0.45), ('tamar', starts[1] + 0.55), ('both', starts[2] + 0.6)]
    colors = {'noam': '&H3C9BFF&', 'tamar': '&HB98CFF&', 'both': '&HFFFFFF&'}  # orange, pink, white (ASS uses BGR)
    subs = []
    for i, (k, t) in enumerate(cues):
        end = min(total - 0.1, (starts[i + 1] + 0.1) if i < 2 else total - 0.15)
        subs.append((t - 0.1, max(end, t + voices[k]['seconds'] + 0.3), voices[k]['text'], colors[k]))
    ass = os.path.join(O, 'subs.ass')
    write_ass(ass, subs)

    music = os.path.join(O, 'music.wav')
    has_music = os.path.exists(music)
    inputs = []
    for s in shots:
        inputs += ['-i', s]
    for k, _ in cues:
        inputs += ['-i', os.path.join(O, f'voice_{k}.wav')]
    if has_music:
        inputs += ['-i', music]
    # video: upscale each shot to 1080x1920 (cover), gentle sharpen, crossfade
    vf = []
    for i in range(3):
        vf.append(f'[{i}:v]fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,'
                  f'crop={W}:{H},unsharp=5:5:0.5,setsar=1,format=yuv420p[v{i}]')
    vf.append(f'[v0][v1]xfade=transition=fade:duration={XF}:offset={starts[1]:.3f}[v01]')
    vf.append(f'[v01][v2]xfade=transition=fade:duration={XF}:offset={starts[2]:.3f}[vx]')
    fontdir = FONT_DIR.replace(':', r'\:')
    vf.append(f"[vx]subtitles='{ass}':fontsdir='{fontdir}'[vout]")
    # audio: voices at their cues, music underneath with fades
    af = []
    for j, (k, t) in enumerate(cues):
        ms = int(t * 1000)
        af.append(f'[{3 + j}:a]aresample=48000,adelay={ms}|{ms},apad[a{j}]')
    mix = '[a0][a1][a2]'
    n = 3
    if has_music:
        af.append(f'[6:a]aresample=48000,volume=0.16,afade=t=in:d=0.6,afade=t=out:st={total - 1.2:.2f}:d=1.2[m]')
        mix += '[m]'
        n = 4
    af.append(f'{mix}amix=inputs={n}:normalize=0:duration=longest,atrim=0:{total:.3f},alimiter=limit=0.95[aout]')
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, 'intro_sample.mp4')
    cmd = ['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', ';'.join(vf + af),
           '-map', '[vout]', '-map', '[aout]', '-t', f'{total:.3f}', '-r', str(FPS),
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p',
           '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out]
    subprocess.run(cmd, check=True)
    print(f'wrote {out}: {total:.2f}s, shots {[round(x, 2) for x in d]}, music={has_music}')


if __name__ == '__main__':
    main()
