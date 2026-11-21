"""Turn out/final/*_4k.png into page assets: a 4K JPEG to download and a light preview.
Usage: python3 make_final_assets.py"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'out', 'final')
DST = os.path.join(HERE, 'showcase', 'final')
os.makedirs(os.path.join(DST, '4k'), exist_ok=True)
for f in sorted(os.listdir(SRC)):
    if not f.endswith('_4k.png'):
        continue
    name = f[:-len('_4k.png')]
    im = Image.open(os.path.join(SRC, f)).convert('RGB')
    big = os.path.join(DST, '4k', name + '.jpg')
    im.save(big, quality=92, optimize=True, progressive=True)
    small = im.resize((900, round(im.height * 900 / im.width)), Image.LANCZOS)
    prev = os.path.join(DST, name + '.jpg')
    small.save(prev, quality=86, optimize=True, progressive=True)
    print(f'{name}: {im.size[0]}x{im.size[1]} -> 4k/{name}.jpg {os.path.getsize(big) // 1024} KB, preview {os.path.getsize(prev) // 1024} KB')
