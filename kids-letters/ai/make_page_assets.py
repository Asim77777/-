"""Copy chosen images into showcase/ as web-sized JPEGs.
Usage: python3 make_page_assets.py <dest_subdir> <src.png>[=name] ...   (max 900px wide)"""
import os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
dest = os.path.join(HERE, 'showcase', sys.argv[1])
os.makedirs(dest, exist_ok=True)
for spec in sys.argv[2:]:
    src, _, name = spec.partition('=')
    im = Image.open(src).convert('RGB')
    if im.width > 900:
        im = im.resize((900, round(im.height * 900 / im.width)), Image.LANCZOS)
    name = name or os.path.splitext(os.path.basename(src))[0]
    out = os.path.join(dest, name + '.jpg')
    im.save(out, quality=88, optimize=True, progressive=True)
    print(out, os.path.getsize(out) // 1024, 'KB')
