"""Round 1: several full-body variants of each character, for the user to pick the definitive look.
Usage: python3 run_round1.py [seeds...]   (default: 6 seeds)
Writes out/round1/<who>_<seed>.png and appends every prompt/seed to out/log.json."""
import os
import sys
import time
from characters import prompt, NEGATIVE
from generate import Generator, log_entry, PORTRAIT

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'round1')
SEEDS = [int(s) for s in sys.argv[1:]] or [58, 77, 91, 105, 133, 150, 177, 202]

os.makedirs(OUT, exist_ok=True)
gen = Generator()
for who in ('noam', 'tamar'):
    for seed in SEEDS:
        path = os.path.join(OUT, f'{who}_{seed}.png')
        if os.path.exists(path):
            continue
        p = prompt(who)
        img, secs = gen(p, NEGATIVE, seed, size=PORTRAIT)
        img.save(path)
        log_entry(os.path.join(HERE, 'out', 'log.json'), file=os.path.relpath(path, HERE), who=who, seed=seed,
                  prompt=p, negative=NEGATIVE, size=list(PORTRAIT), steps=8, cfg=2.0, model='Lykon/dreamshaper-xl-lightning',
                  seconds=round(secs), time=time.strftime('%Y-%m-%d %H:%M'))
        print(f'{path} {secs:.0f}s', flush=True)
