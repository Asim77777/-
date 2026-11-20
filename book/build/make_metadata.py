"""Build book/data/drashot.json from the site's video list + YouTube oEmbed titles."""
import json, re, sys, urllib.request, urllib.parse, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from themes_draft import THEMES

ROOT = pathlib.Path(__file__).resolve().parents[1]
MONTHS = ["תשרי", "חשוון", "כסלו", "טבת", "שבט", "אדר", "ניסן", "אייר", "סיוון", "תמוז", "אב", "אלול"]
GEM = {"א":1,"ב":2,"ג":3,"ד":4,"ה":5,"ו":6,"ז":7,"ח":8,"ט":9,"י":10,"כ":20,"ל":30}

def day_num(s):
    return sum(GEM.get(c, 0) for c in s)

def sort_key(date):
    m = re.match(r"(\S+) ב(\S+) ה׳תשפ״(\S)", date)
    day, month, yr = m.groups()
    return (day_num(yr), MONTHS.index(month), day_num(day))

def clean_title(t):
    t = re.sub(r'\s*\|?\s*-?\s*רבי חיים דרעי\s+שליט"א\s*-?\s*', " ", t)
    # remove trailing Hebrew date like  -ו' בכסלו ה'תשפ"ז / | ט׳ באלול ה׳תשפ״ה
    t = re.sub(r"[-–|\s]*[א-ת]{1,2}[\"'״׳]{0,2}[א-ת]?\s+ב(תשרי|חשוון|חשון|כסלו|טבת|שבט|אדר|ניסן|אייר|סיון|סיוון|תמוז|אב|אלול)\s+ה?[׳']?\s*ה?תשפ[\"״]?[א-ת]\s*", " ", t)
    t = re.sub(r"\s*\|\s*$", "", t.strip())
    t = re.sub(r"^\s*\|\s*", "", t)
    t = re.sub(r"\s*-\s*$", "", t)
    t = re.sub(r"\s{2,}", " ", t)
    return t.strip(" -|")

theme_of = {vid: (i, name) for i, (name, vids) in enumerate(THEMES) for vid in vids}
items = []
for line in (ROOT / "data/site_order.txt").read_text().splitlines():
    vid, date = line.split(" ", 1)
    url = "https://www.youtube.com/watch?v=" + vid
    with urllib.request.urlopen("https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(url), timeout=20) as r:
        o = json.load(r)
    ti, tname = theme_of[vid]
    items.append({"id": vid, "youtube_title": o["title"], "title": clean_title(o["title"]), "date": date,
                  "url": url, "theme_index": ti, "theme": tname, "sort": sort_key(date)})
missing = set(theme_of) ^ {i["id"] for i in items}
assert not missing, missing
items.sort(key=lambda x: (x["theme_index"], x["sort"]))
for i in items:
    del i["sort"]
(ROOT / "data/drashot.json").write_text(json.dumps(items, ensure_ascii=False, indent=1))
for i in items:
    print(i["theme_index"], i["date"], "|", i["title"])
print(len(items))
