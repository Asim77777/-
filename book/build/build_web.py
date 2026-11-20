"""Build the digital book: sefer/index.html (static, self-contained apart from Google Fonts)."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse import load_book, heb_number  # noqa: E402
from render_html import (BOOK_TITLE, BOOK_SUBTITLE, BOOK_SPAN, INTRO_HTML,  # noqa: E402
                         esc, render_drasha)

REPO = pathlib.Path(__file__).resolve().parents[2]

CSS = r"""
:root{
  --bg:#f7f3ea; --paper:#fffdf8; --ink:#2a2420; --muted:#7a6e62; --line:#e4dccd;
  --accent:#8a5a2b; --accent-soft:#f1e6d6; --add:#9a7b5a; --unc:#b3541e; --ref:#5b6f86; --note:#6f7f5c;
  --hl:#ffe58a; --shadow:0 1px 3px rgba(60,40,20,.08),0 6px 24px rgba(60,40,20,.06);
  --fs:19px;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#16130f; --paper:#1e1a15; --ink:#ece4d8; --muted:#a89c8c; --line:#3a332a;
    --accent:#d6a46a; --accent-soft:#2c241b; --add:#c4a582; --unc:#ef8a52; --ref:#93abc6; --note:#a9bb93;
    --hl:#6b5a1a; --shadow:none;
  }
}
:root[data-theme="dark"]{
  --bg:#16130f; --paper:#1e1a15; --ink:#ece4d8; --muted:#a89c8c; --line:#3a332a;
  --accent:#d6a46a; --accent-soft:#2c241b; --add:#c4a582; --unc:#ef8a52; --ref:#93abc6; --note:#a9bb93;
  --hl:#6b5a1a; --shadow:none;
}
*{box-sizing:border-box}
html{scroll-padding-top:72px}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Frank Ruhl Libre",FreeSerif,serif;
  font-size:var(--fs);line-height:1.85;-webkit-text-size-adjust:100%}
a{color:var(--accent)}
.ui{font-family:"Assistant","Heebo",system-ui,sans-serif}
.bar{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 92%,transparent);
  backdrop-filter:blur(6px);border-bottom:1px solid var(--line)}
.bar-in{max-width:1180px;margin:0 auto;display:flex;align-items:center;gap:10px;padding:10px 16px}
.brand{font-weight:700;font-size:18px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1;min-width:0}
.brand a{color:var(--ink);text-decoration:none}
.search{position:relative;flex:0 1 300px;min-width:120px}
.search input{width:100%;font:inherit;font-size:15px;padding:8px 12px;border-radius:10px;border:1px solid var(--line);
  background:var(--paper);color:var(--ink)}
.btn{font:inherit;font-size:15px;border:1px solid var(--line);background:var(--paper);color:var(--ink);
  border-radius:10px;padding:7px 10px;cursor:pointer;line-height:1}
.btn:hover{border-color:var(--accent)}
#results{position:absolute;top:44px;left:0;right:0;max-height:60vh;overflow:auto;background:var(--paper);
  border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);display:none;font-size:15px;line-height:1.5}
#results.open{display:block}
#results .r{display:block;padding:10px 12px;border-bottom:1px solid var(--line);color:var(--ink);text-decoration:none}
#results .r:hover{background:var(--accent-soft)}
#results .rt{color:var(--accent);font-weight:700;font-size:13px}
#results .empty{padding:12px;color:var(--muted)}
mark{background:var(--hl);color:inherit;border-radius:3px}
.layout{max-width:1180px;margin:0 auto;display:grid;grid-template-columns:290px minmax(0,1fr);gap:32px;padding:0 16px}
nav.toc{position:sticky;top:64px;align-self:start;max-height:calc(100vh - 80px);overflow:auto;padding:24px 0 40px;
  font-size:15px;line-height:1.45}
.toc h4{margin:18px 0 6px;font-size:13px;color:var(--muted);font-weight:700;letter-spacing:.02em}
.toc a{display:block;padding:5px 10px;border-radius:8px;color:var(--ink);text-decoration:none}
.toc a:hover,.toc a.on{background:var(--accent-soft);color:var(--accent)}
.toc .tn{color:var(--muted);margin-inline-end:6px}
main{min-width:0;padding:8px 0 80px}
.cover{text-align:center;padding:56px 12px 36px;border-bottom:1px solid var(--line);margin-bottom:24px}
.cover h1{font-size:clamp(30px,6vw,46px);margin:0 0 8px;line-height:1.25}
.cover .sub{font-size:20px;color:var(--muted)}
.cover .span{font-size:15px;color:var(--muted);margin-top:10px}
.intro{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:18px 22px;font-size:16px;
  line-height:1.7;box-shadow:var(--shadow)}
.intro summary{cursor:pointer;font-weight:700;font-size:17px}
.theme-title{text-align:center;margin:64px 0 8px;font-size:15px;color:var(--muted);letter-spacing:.04em}
.theme-title b{display:block;font-size:30px;color:var(--accent);letter-spacing:0;margin-top:4px}
.drasha{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:28px clamp(16px,4vw,44px);
  margin:24px 0;box-shadow:var(--shadow)}
.dh{text-align:center;border-bottom:1px solid var(--line);padding-bottom:16px;margin-bottom:18px}
.dnum{font-size:14px;color:var(--muted)}
.dtitle{font-size:clamp(23px,3.6vw,30px);line-height:1.35;margin:4px 0 10px}
.dmeta{display:flex;gap:14px;justify-content:center;flex-wrap:wrap;font-size:15px;color:var(--muted);font-family:"Assistant",sans-serif}
.dvideo{text-decoration:none;font-weight:700}
.sh{font-size:20px;color:var(--accent);margin:28px 0 6px;font-family:"Assistant",sans-serif;font-weight:700}
.drasha p{margin:0 0 14px;text-align:justify}
.ts{font-family:"Assistant",sans-serif;font-size:12px;color:var(--muted);text-decoration:none;border:1px solid var(--line);
  border-radius:6px;padding:0 5px;margin-inline-end:8px;vertical-align:2px;direction:ltr;display:inline-block;line-height:1.6}
.ts:hover{color:var(--accent);border-color:var(--accent)}
.add{color:var(--add)}
.unc{color:var(--unc);text-decoration:none;font-size:.78em;vertical-align:.25em;font-family:"Assistant",sans-serif;font-weight:700}
.ref{color:var(--ref);font-size:.86em}
.note{color:var(--note);font-style:italic;font-size:.9em}
.flash{animation:flash 2.2s ease-out}
@keyframes flash{0%{background:var(--hl)}100%{background:transparent}}
.mk{display:none}
#tocbtn{display:none}
footer{color:var(--muted);text-align:center;font-size:14px;padding:30px 0}
@media (max-width:900px){
  .layout{grid-template-columns:minmax(0,1fr);gap:0}
  nav.toc{position:fixed;inset:0 auto 0 0;width:min(86vw,340px);max-height:none;height:100vh;top:0;z-index:40;
    background:var(--paper);padding:20px 16px;transform:translateX(-105%);transition:transform .25s;box-shadow:var(--shadow)}
  nav.toc.open{transform:none}
  #tocbtn{display:inline-block}
  .bar-in{flex-wrap:wrap;row-gap:8px}
  .brand{font-size:16px}
  .search{order:5;flex:1 1 100%}
  #results{position:fixed;top:auto;left:12px;right:12px;max-height:65vh}
  :root{--fs:18px}
}
"""

JS = r"""
(function(){
  const root=document.documentElement;
  const store={get(k){try{return localStorage.getItem(k)}catch(e){return null}},set(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
  let fs=parseFloat(store.get('fs'))||null; if(fs) root.style.setProperty('--fs',fs+'px');
  const t=store.get('theme'); if(t) root.dataset.theme=t;
  document.getElementById('bigger').onclick=()=>{fs=(fs||parseFloat(getComputedStyle(root).getPropertyValue('--fs')))+1;fs=Math.min(fs,28);root.style.setProperty('--fs',fs+'px');store.set('fs',fs)};
  document.getElementById('smaller').onclick=()=>{fs=(fs||parseFloat(getComputedStyle(root).getPropertyValue('--fs')))-1;fs=Math.max(fs,14);root.style.setProperty('--fs',fs+'px');store.set('fs',fs)};
  document.getElementById('theme').onclick=()=>{const dark=root.dataset.theme?root.dataset.theme==='dark':matchMedia('(prefers-color-scheme: dark)').matches;root.dataset.theme=dark?'light':'dark';store.set('theme',root.dataset.theme)};
  const toc=document.querySelector('nav.toc');
  document.getElementById('tocbtn').onclick=e=>{e.stopPropagation();toc.classList.toggle('open')};
  document.addEventListener('click',e=>{if(toc.classList.contains('open')&&!toc.contains(e.target))toc.classList.remove('open')});
  toc.addEventListener('click',e=>{if(e.target.closest('a'))toc.classList.remove('open')});
  // highlight current drasha in TOC
  const links=[...toc.querySelectorAll('a[href^="#d-"]')];
  const obs=new IntersectionObserver(es=>{es.forEach(en=>{if(en.isIntersecting){links.forEach(a=>a.classList.toggle('on',a.getAttribute('href')==='#'+en.target.id))}})},{rootMargin:'-30% 0px -60% 0px'});
  document.querySelectorAll('section.drasha').forEach(s=>obs.observe(s));
  // search
  const strip=s=>s.replace(/[֑-ׇ]/g,'').replace(/[״"׳'’`]/g,'"').toLowerCase();
  const paras=[...document.querySelectorAll('section.drasha p')].map((p,i)=>{p.id=p.id||('p'+i);const sec=p.closest('section');
    return {p,sec,title:sec.querySelector('.dtitle').textContent,txt:p.textContent,norm:strip(p.textContent)}});
  const inp=document.getElementById('q'), res=document.getElementById('results');
  let timer;
  inp.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(run,180)});
  inp.addEventListener('focus',()=>{if(inp.value.trim().length>1)res.classList.add('open')});
  document.addEventListener('click',e=>{if(!e.target.closest('.search'))res.classList.remove('open')});
  inp.addEventListener('keydown',e=>{if(e.key==='Escape'){res.classList.remove('open');inp.blur()}});
  function snippet(txt,q){const n=strip(txt);const i=n.indexOf(q);const s=Math.max(0,i-50),e=Math.min(txt.length,i+q.length+70);
    const esc=x=>x.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
    return (s>0?'…':'')+esc(txt.slice(s,i))+'<mark>'+esc(txt.slice(i,i+q.length))+'</mark>'+esc(txt.slice(i+q.length,e))+(e<txt.length?'…':'')}
  function run(){const q=strip(inp.value.trim());res.innerHTML='';if(q.length<2){res.classList.remove('open');return}
    const hits=paras.filter(x=>x.norm.includes(q));
    if(!hits.length){res.innerHTML='<div class="empty">לא נמצאו תוצאות</div>'}
    else{res.innerHTML='<div class="empty">'+hits.length+' תוצאות</div>'+hits.slice(0,80).map(h=>'<a class="r" href="#'+h.p.id+'"><div class="rt">'+h.title.replace(/[&<>]/g,'')+'</div>'+snippet(h.txt,q)+'</a>').join('')}
    res.classList.add('open')}
  res.addEventListener('click',e=>{const a=e.target.closest('a.r');if(!a)return;e.preventDefault();const el=document.getElementById(a.getAttribute('href').slice(1));
    res.classList.remove('open');el.scrollIntoView({behavior:'smooth',block:'center'});el.classList.remove('flash');void el.offsetWidth;el.classList.add('flash')});
})();
"""


def build(out_path, only_ids=None):
    book = load_book(only_ids)
    toc, body = [], []
    for ti, (theme, ds) in enumerate(book, 1):
        toc.append(f"<h4>שער {heb_number(ti)} · {esc(theme)}</h4>")
        body.append(f'<div class="theme-title" id="t-{ti}">שער {heb_number(ti)}<b>{esc(theme)}</b></div>')
        for d in ds:
            toc.append(f'<a href="#d-{esc(d["id"])}"><span class="tn">{heb_number(d["num"])}.</span>{esc(d["title"])}</a>')
            body.append(render_drasha(d))
    count = sum(len(ds) for _, ds in book)
    page = f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(BOOK_TITLE)} – ספר דיגיטלי</title>
<meta name="description" content="{esc(BOOK_SUBTITLE)}. {count} דרשות מסודרות לפי נושאים.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&family=Frank+Ruhl+Libre:wght@400;700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="bar ui"><div class="bar-in">
  <button class="btn" id="tocbtn" aria-label="תוכן העניינים">☰</button>
  <div class="brand"><a href="#top">{esc(BOOK_TITLE)}</a></div>
  <div class="search"><input id="q" type="search" placeholder="חיפוש בספר…" aria-label="חיפוש בספר" autocomplete="off"><div id="results" role="listbox"></div></div>
  <button class="btn" id="smaller" aria-label="הקטנת גופן">א-</button>
  <button class="btn" id="bigger" aria-label="הגדלת גופן">א+</button>
  <button class="btn" id="theme" aria-label="מצב כהה/בהיר">◐</button>
</div></div>
<div class="layout">
<nav class="toc ui" aria-label="תוכן העניינים"><a href="#top"><b>פתח דבר ודרך העריכה</b></a>{''.join(toc)}</nav>
<main id="top">
<div class="cover"><h1>{esc(BOOK_TITLE)}</h1><div class="sub">{esc(BOOK_SUBTITLE)}</div><div class="span ui">{esc(BOOK_SPAN)} · {count} דרשות</div></div>
<details class="intro ui" open><summary>פתח דבר ודרך העריכה</summary>{INTRO_HTML}</details>
{''.join(body)}
<footer class="ui">{esc(BOOK_TITLE)} · נערך מתוך הדרשות המצולמות</footer>
</main>
</div>
<script>{JS}</script>
</body>
</html>"""
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    print("wrote", out_path, len(page), "bytes,", count, "drashot")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else REPO / "sefer/index.html")
