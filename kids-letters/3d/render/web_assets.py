"""Copy finished renders into showcase/ in web-friendly sizes (JPEG for stills, MP4 as is).
Usage: python3 render/web_assets.py"""
import os
import shutil
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'renders')
DST = os.path.join(ROOT, 'showcase')
os.makedirs(DST, exist_ok=True)

for name in sorted(os.listdir(SRC)):
    src = os.path.join(SRC, name)
    if name.endswith('.png'):
        im = Image.open(src).convert('RGB')
        max_w = 1080 if im.width > im.height else 900
        if im.width == im.height:
            max_w = 600
        if im.width > max_w:
            im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
        out = os.path.join(DST, name[:-4] + '.jpg')
        im.save(out, quality=86, optimize=True, progressive=True)
    elif name.endswith('.mp4'):
        out = os.path.join(DST, name)
        shutil.copyfile(src, out)
    else:
        continue
    print(f'{name} -> {os.path.relpath(out, ROOT)} ({os.path.getsize(out) // 1024} KB)')
