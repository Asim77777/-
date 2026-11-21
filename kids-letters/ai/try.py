"""Development aid: render several (who, seed[, extra]) quickly with one model load.
Usage: python3 try.py <outdir> who:seed[:extra] ..."""
import os, sys
from characters import prompt, NEGATIVE
from generate import Generator
from transformers import CLIPTokenizer
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
g = Generator()
tok = g.pipe.tokenizer
for spec in sys.argv[2:]:
    who, seed, *extra = spec.split(':')
    p = prompt(who, extra=extra[0] if extra else '')
    n = len(tok(p).input_ids)
    img, secs = g(p, NEGATIVE, int(seed))
    path = os.path.join(out, f'{who}_{seed}.png')
    img.save(path)
    print(f'{path} tokens={n} {secs:.0f}s', flush=True)
