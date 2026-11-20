"""Generate the fill-in page for the unclear spots ([?mm:ss]) – published as a claude.ai artifact with a db.

Each spot: its context in the edited text, a link that opens the recording 5 seconds before it, and a field
for what is said there. Answers are stored in the artifact's db (collection "answers", one doc per spot)
and read back with ArtifactData to be written into book/drashot/*.md.

usage: python3 -I book/build/build_fill.py   ->  book/fill/hashlama.html, book/fill/spots.json
"""
import html
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import book as B  # noqa: E402

BOOK = HERE.parent
OUT = BOOK / "fill"


def clean(t):
    t = re.sub(r"⟦[^|⟧]*\|([^⟧]*)⟧", r"\1", t)
    t = re.sub(r"\{\{[^}]*\}\}|\[\[[0-9:]+\]\]", "", t)
    t = re.sub(r"\[\?[0-9:]*\]", "[…]", t)
    return re.sub(r"\s+", " ", t).replace("...", "…")


def spots():
    items = json.loads((BOOK / "data" / "drashot.json").read_text(encoding="utf-8"))
    order = {it["id"]: i for i, it in enumerate(items)}
    out = []
    files = sorted((BOOK / "drashot").glob("*.md"), key=lambda f: order.get(f.stem, 999))
    for num, f in enumerate(files, 1):
        meta, body = B.read_md(f)
        for para in re.split(r"\n\s*\n", body):
            pm = re.match(r"\s*\[\[(\d{1,3}:\d{2})\]\]", para)
            psec = B.to_sec(pm.group(1)) if pm else 0
            for m in re.finditer(r"\[\?(\d{1,3}:\d{2})?\]", para):
                sec = B.to_sec(m.group(1)) if m.group(1) else psec
                before = clean(para[:m.start()]).strip()
                after = clean(para[m.end():]).strip()
                if len(before) > 150:
                    before = "…" + before[-150:].split(" ", 1)[-1]
                if len(after) > 110:
                    after = after[:110].rsplit(" ", 1)[0] + "…"
                out.append({"id": f"s{len(out) + 1:03d}", "d": f.stem, "n": B.heb_numeral(num), "title": meta["title"].strip('"'),
                            "sec": sec, "ts": B.fmt_ts(sec), "b": before, "a": after})
    return out


PAGE = """<title>השלמות לספר הדרשות</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Frank+Ruhl+Libre:wght@400;500;700&family=Assistant:wght@400;600&display=swap">
<style>
/* a working sheet for the editor: one line per unclear spot, the same black-and-red of the book */
:root{
  --paper:#ffffff; --ink:#1c1b1a; --ink-2:#615c56; --rule:#e2ded8; --adom:#8e1b1b; --gap:#fbefe9; --ok:#2f6b3a;
  --text:"Frank Ruhl Libre","Taamey Frank CLM","David",serif; --ui:"Assistant","Arial Hebrew",system-ui,sans-serif;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --paper:#141414; --ink:#ece7e0; --ink-2:#a39d95; --rule:#34312e; --adom:#e47767; --gap:#3a2420; --ok:#7cc48a; color-scheme:dark}}
:root[data-theme="dark"]{--paper:#141414; --ink:#ece7e0; --ink-2:#a39d95; --rule:#34312e; --adom:#e47767; --gap:#3a2420; --ok:#7cc48a; color-scheme:dark}
body{background:var(--paper);color:var(--ink);font-family:var(--ui);direction:rtl}
.wrap{max-width:52rem;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:0 4rem}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:10;background:var(--paper)}
header.top{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--paper);border-bottom:1px solid var(--rule);padding-block:14px 10px}
h1{font:700 1.7rem/1.25 var(--text);margin:0;text-wrap:balance}
.lead{margin:.3rem 0 .7rem;color:var(--ink-2);font-size:.98rem;line-height:1.5}
.bar{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;font-size:.95rem}
.progress{font-variant-numeric:tabular-nums;font-weight:600}
.meter{flex:1 1 140px;height:4px;background:var(--rule);min-width:120px}
.meter i{display:block;height:100%;width:0;background:var(--adom);transition:width .3s}
.filters{display:flex;flex-wrap:wrap;gap:6px}
.filters button{font:600 .9rem/1 var(--ui);color:var(--ink);background:none;border:1px solid var(--rule);padding:7px 10px;cursor:pointer}
.filters button[aria-pressed="true"]{border-color:var(--ink);background:var(--ink);color:var(--paper)}
.only{display:inline-flex;gap:6px;align-items:center;cursor:pointer}
.only input{accent-color:var(--adom)}
.state{font-size:.9rem;color:var(--ink-2);min-height:1.3em;margin-top:6px}
.state.warn{color:var(--adom)}
h2{font:700 1.15rem/1.4 var(--text);margin:2rem 0 .2rem;color:var(--adom)}
h2 small{display:block;font:400 .85rem/1.4 var(--ui);color:var(--ink-2)}
ol{list-style:none;margin:0;padding:0}
li.spot{display:grid;grid-template-columns:5.5rem minmax(0,1fr);gap:4px 16px;padding:14px 0;border-bottom:1px solid var(--rule)}
li.spot[hidden]{display:none}
.when{font-variant-numeric:tabular-nums;font-size:.95rem;padding-top:4px}
.when a{color:var(--adom);font-weight:600;text-decoration:none;display:inline-flex;align-items:center;gap:4px;direction:ltr}
.when a:hover{text-decoration:underline}
.when a svg{width:12px;height:12px;fill:currentColor}
.ctx{font:400 1.12rem/1.75 var(--text);margin:0}
.ctx .hole{background:var(--gap);color:var(--adom);padding:0 .3em;font-weight:700;white-space:nowrap}
.answer{grid-column:2;display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center}
.answer input[type=text]{flex:1 1 16rem;min-width:0;font:400 1.08rem/1.4 var(--text);color:var(--ink);background:transparent;border:0;border-bottom:1.5px solid var(--rule);padding:6px 2px}
.answer input[type=text]:focus{outline:none;border-bottom-color:var(--adom)}
.answer input:disabled{opacity:.55}
.answer label{font-size:.9rem;color:var(--ink-2);display:inline-flex;gap:5px;align-items:center;cursor:pointer}
.answer label input{accent-color:var(--adom)}
.saved{font-size:.85rem;color:var(--ok);min-width:3.5em}
.saved.err{color:var(--adom)}
@media (max-width:560px){header.top{position:static}li.spot{grid-template-columns:1fr}.answer{grid-column:1}.when{padding-top:0}}
@media (prefers-reduced-motion:reduce){.meter i{transition:none}}
</style>

<div class="wrap">
<header class="top">
  <h1>השלמות לספר הדרשות</h1>
  <p class="lead">בכל שורה מקום שלא נשמע היטב בתמלול. לחיצה על הזמן פותחת את ההקלטה ביוטיוב חמש שניות לפני המקום. כתבו את המילים החסרות כפי שהן נשמעות; כל שינוי נשמר מיד. אם גם בהקלטה אי אפשר לשמוע, סמנו „לא נשמע".</p>
  <div class="bar">
    <span class="progress" id="progress">טוען…</span>
    <span class="meter" aria-hidden="true"><i id="meter"></i></span>
    <label class="only"><input type="checkbox" id="only-open"> רק מה שטרם מולא</label>
  </div>
  <div class="filters" id="filters" role="group" aria-label="סינון לפי דרשה"></div>
  <div class="state" id="state" role="status"></div>
</header>
<main id="list"></main>
</div>

<script id="spots" type="application/json">__SPOTS__</script>
<script>
(function(){
  "use strict";
  const SPOTS = JSON.parse(document.getElementById("spots").textContent);
  const answers = {};          // id -> {text, unheard}
  let db = null, canWrite = true, current = "all";
  const $ = (id) => document.getElementById(id);
  const play = '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M2 1v8l7-4z"/></svg>';

  // ---- render the sheet once; the store only fills values in ----
  const groups = [];
  for (const s of SPOTS) {
    if (!groups.length || groups[groups.length - 1].d !== s.d) groups.push({ d: s.d, n: s.n, title: s.title, spots: [] });
    groups[groups.length - 1].spots.push(s);
  }
  const list = $("list");
  for (const g of groups) {
    const sec = document.createElement("section");
    sec.dataset.d = g.d;
    const h = document.createElement("h2");
    h.textContent = "דרשה " + g.n + " – " + g.title;
    const sm = document.createElement("small");
    sm.textContent = g.spots.length + " מקומות";
    h.appendChild(sm);
    sec.appendChild(h);
    const ol = document.createElement("ol");
    for (const s of g.spots) {
      const li = document.createElement("li");
      li.className = "spot"; li.id = s.id; li.dataset.d = s.d;
      const t = Math.max(0, s.sec - 5);
      li.innerHTML =
        '<div class="when"><a target="_blank" rel="noopener" href="https://www.youtube.com/watch?v=' + s.d + '&t=' + t + 's" aria-label="האזנה מן הרגע ' + s.ts + '">' + play + s.ts + '</a></div>' +
        '<p class="ctx"></p>' +
        '<div class="answer"><input type="text" id="a-' + s.id + '" autocomplete="off" aria-label="מה נאמר בדקה ' + s.ts + '" placeholder="מה נאמר כאן">' +
        '<label><input type="checkbox" id="u-' + s.id + '"> לא נשמע</label><span class="saved" aria-live="polite"></span></div>';
      const p = li.querySelector(".ctx");
      p.append(s.b + " ");
      const hole = document.createElement("span"); hole.className = "hole"; hole.textContent = "[ ? ]";
      p.append(hole, " " + s.a);
      ol.appendChild(li);
    }
    sec.appendChild(ol);
    list.appendChild(sec);
  }
  const fl = $("filters");
  const mk = (key, label) => { const b = document.createElement("button"); b.type = "button"; b.dataset.k = key; b.textContent = label; b.setAttribute("aria-pressed", String(key === current)); fl.appendChild(b); };
  mk("all", "כל הדרשות");
  for (const g of groups) mk(g.d, "דרשה " + g.n + " (" + g.spots.length + ")");
  fl.addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; current = b.dataset.k; fl.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); applyFilter(); });
  $("only-open").addEventListener("change", applyFilter);

  function filled(id) { const a = answers[id]; return !!(a && ((a.text || "").trim() || a.unheard)); }
  function applyFilter() {
    const only = $("only-open").checked;
    document.querySelectorAll("section[data-d]").forEach((sec) => {
      let shown = 0;
      sec.querySelectorAll("li.spot").forEach((li) => {
        const hide = (current !== "all" && li.dataset.d !== current) || (only && filled(li.id));
        li.hidden = hide; if (!hide) shown++;
      });
      sec.hidden = shown === 0;
    });
  }
  function progress() {
    const n = SPOTS.filter((s) => filled(s.id)).length;
    $("progress").textContent = "מולאו " + n + " מתוך " + SPOTS.length;
    $("meter").style.width = (100 * n / SPOTS.length) + "%";
  }

  // ---- saving: one write at a time per spot, only on change ----
  const timers = {}, busy = {}, again = {};
  function save(id) {
    if (!db || !canWrite) return;
    if (busy[id]) { again[id] = true; return; }
    const text = $("a-" + id).value.trim(), unheard = $("u-" + id).checked;
    const prev = answers[id] || {};
    if ((prev.text || "") === text && !!prev.unheard === unheard) return;
    const s = SPOTS.find((x) => x.id === id);
    const mark = document.querySelector("#" + id + " .saved");
    busy[id] = true; mark.className = "saved"; mark.textContent = "שומר…";
    db.collection("answers").doc(id).set({ text, unheard, drasha: s.d, sec: s.sec, at: Date.now() })
      .then(() => { answers[id] = { text, unheard }; mark.textContent = "נשמר"; progress(); })
      .catch((e) => {
        mark.className = "saved err";
        if (e && e.code === "invalid_argument") { canWrite = false; lockAll("אין לך הרשאה לשמור בדף הזה; אפשר לקרוא בלבד."); mark.textContent = ""; }
        else mark.textContent = "לא נשמר – נסו שוב";
      })
      .finally(() => { busy[id] = false; if (again[id]) { again[id] = false; save(id); } });
  }
  list.addEventListener("input", (e) => {
    const li = e.target.closest("li.spot"); if (!li) return;
    clearTimeout(timers[li.id]); timers[li.id] = setTimeout(() => save(li.id), e.target.type === "checkbox" ? 0 : 900);
  });
  list.addEventListener("focusout", (e) => { const li = e.target.closest("li.spot"); if (li && e.target.type === "text") { clearTimeout(timers[li.id]); save(li.id); } });

  function lockAll(msg) {
    document.querySelectorAll(".answer input").forEach((i) => { i.disabled = true; });
    const st = $("state"); st.textContent = msg; st.className = "state warn";
  }

  // ---- the store ----
  progress();
  $("progress").textContent = "טוען את ההשלמות…";
  const slow = setTimeout(() => { $("state").textContent = "הטעינה מתעכבת; ההשלמות יופיעו כשהחיבור יחזור."; }, 10000);
  window.claude && window.claude.use("db").then((d) => {
    db = d;
    if (!db) { clearTimeout(slow); progress(); lockAll("השמירה אינה זמינה בתצוגה זו. פתחו את הדף ב-claude.ai כשאתם מחוברים."); return; }
    db.collection("answers").onSnapshot((snap) => {
      clearTimeout(slow); $("state").textContent = "";
      snap.docs.forEach((doc) => {
        const v = doc.data() || {}; answers[doc.id] = { text: v.text || "", unheard: !!v.unheard };
        const ti = $("a-" + doc.id), cu = $("u-" + doc.id);
        if (ti && document.activeElement !== ti && !busy[doc.id]) ti.value = v.text || "";
        if (cu && !busy[doc.id]) cu.checked = !!v.unheard;
      });
      progress(); applyFilter();
    }, (e) => { clearTimeout(slow); if (e && e.code !== "revoked") lockAll("לא ניתן לטעון את ההשלמות כרגע. רעננו את הדף."); });
  });
  if (!window.claude) { clearTimeout(slow); progress(); lockAll("השמירה אינה זמינה בתצוגה זו. פתחו את הדף ב-claude.ai כשאתם מחוברים."); }
})();
</script>
"""


def main():
    sp = spots()
    OUT.mkdir(exist_ok=True)
    (OUT / "spots.json").write_text(json.dumps(sp, ensure_ascii=False, indent=0), encoding="utf-8")
    data = json.dumps(sp, ensure_ascii=False).replace("</", "<\\/")
    (OUT / "hashlama.html").write_text(PAGE.replace("__SPOTS__", data), encoding="utf-8")
    print(f"{OUT / 'hashlama.html'}: {len(sp)} spots, {len(data) // 1024} KB of data")


if __name__ == "__main__":
    main()
