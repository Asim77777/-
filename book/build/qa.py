"""Quality checks: compare edited word counts to the raw YouTube transcript and count markers."""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse import parse_file  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
raw = json.loads((ROOT / "data/raw_stats.json").read_text())
ids = [json.loads(l) for l in []]
rows = []
for f in sorted((ROOT / "drashot").glob("*.md")):
    d = parse_file(f)
    words = unclear = adds = refs = notes = 0
    for b in d["blocks"]:
        if b["type"] != "p":
            continue
        for kind, val in b["segs"]:
            if kind == "text":
                words += len([w for w in val.split() if re.search(r"[א-ת0-9A-Za-z]", w)])
            elif kind == "unclear":
                unclear += 1
            elif kind == "add":
                adds += 1
            elif kind == "ref":
                refs += 1
            elif kind == "note":
                notes += 1
    r = raw.get(f.stem, {})
    rw = r.get("raw_words")
    ratio = f"{words / rw:.0%}" if rw else "?"
    rows.append((f.stem, d["title"][:40], rw, words, ratio, unclear, adds, refs, notes))
print("id | title | raw words | edited words | ratio | [?] | [completions] | sources | notes")
for row in rows:
    print(" | ".join(str(x) for x in row))
