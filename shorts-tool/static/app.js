/* Shorts Studio - client. The subtitle preview mirrors app/subtitles.py:
   every style value is in 1080x1920 canvas pixels. */
'use strict';

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const el = (tag, props = {}, ...kids) => {
  const n = Object.assign(document.createElement(tag), props);
  n.append(...kids);
  return n;
};
const api = async (path, opts) => {
  const r = await fetch(path, opts);
  if (r.status === 401) { location.href = '/login'; return new Promise(() => {}); }
  if (!r.ok) {
    let msg = r.statusText;
    try { const d = (await r.json()).detail; msg = typeof d === 'string' ? d : 'הנתונים שהוזנו לא תקינים'; } catch {}
    throw new Error(msg);
  }
  return r.json();
};
const fmt = (t) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;

const S = {
  fonts: [], fontMap: {}, defaults: null, job: null, clips: [], cur: 0,
  lines: null, lineIdx: -2, pollTimer: null,
};
const video = $('#video'), bgVideo = $('#bgVideo');
const subEl = $('#subEl'), titleEl = $('#titleEl');

const PRESETS = [
  { name: 'צהוב בולט', s: { font: 'Heebo Black', size: 92, color: '#FFFFFF', outlineColor: '#000000', outlineWidth: 8, shadow: 0, bgEnabled: false, highlightEnabled: true, highlightColor: '#FFE600', animation: 'pop', wordsPerLine: 3 } },
  { name: 'לבן נקי', s: { font: 'Assistant ExtraBold', size: 80, color: '#FFFFFF', outlineColor: '#000000', outlineWidth: 5, shadow: 4, shadowColor: '#000000', bgEnabled: false, highlightEnabled: false, animation: 'fade', wordsPerLine: 4 } },
  { name: 'תיבה שחורה', s: { font: 'Rubik Bold', size: 70, color: '#FFFFFF', outlineWidth: 0, shadow: 0, bgEnabled: true, bgColor: '#000000', bgOpacity: 0.75, bgPadding: 18, highlightEnabled: true, highlightColor: '#FFD60A', animation: 'none', wordsPerLine: 4 } },
  { name: 'ניאון', s: { font: 'Secular One', size: 88, color: '#00FFD1', outlineColor: '#0B0B14', outlineWidth: 7, shadow: 0, bgEnabled: false, highlightEnabled: true, highlightColor: '#FF3DF2', animation: 'pop', wordsPerLine: 3 } },
  { name: 'ירוק אנרגטי', s: { font: 'Rubik Black', size: 104, color: '#FFFFFF', outlineColor: '#000000', outlineWidth: 9, shadow: 5, shadowColor: '#000000', bgEnabled: false, highlightEnabled: true, highlightColor: '#39FF14', animation: 'pop', wordsPerLine: 2 } },
  { name: 'קלאסי', s: { font: 'Frank Ruhl Libre Bold', size: 82, color: '#FFF8E7', outlineColor: '#1A1205', outlineWidth: 4, shadow: 4, shadowColor: '#000000', bgEnabled: false, highlightEnabled: false, animation: 'fade', wordsPerLine: 4 } },
  { name: 'כתב יד', s: { font: 'Amatic SC Bold', size: 138, color: '#FFFFFF', outlineColor: '#000000', outlineWidth: 6, shadow: 0, bgEnabled: false, highlightEnabled: true, highlightColor: '#FF9F1C', animation: 'reveal', wordsPerLine: 3 } },
  { name: 'תיבה צהובה', s: { font: 'Heebo Black', size: 74, color: '#111111', outlineWidth: 0, shadow: 0, bgEnabled: true, bgColor: '#FFE600', bgOpacity: 1, bgPadding: 16, highlightEnabled: false, animation: 'pop', wordsPerLine: 3 } },
  { name: 'דרמטי', s: { font: 'Karantina Bold', size: 150, color: '#FFFFFF', outlineColor: '#000000', outlineWidth: 6, shadow: 6, shadowColor: '#7A0000', bgEnabled: false, highlightEnabled: true, highlightColor: '#FF2D2D', animation: 'reveal', wordsPerLine: 2 } },
];

/* ---------------- style -> CSS (shared by preview and preset thumbs) ---------------- */
function ring(r, color, dx = 0, dy = 0) {
  if (r <= 0) return dx || dy ? [`${dx}px ${dy}px 0 ${color}`] : [];
  const out = [], n = Math.max(12, Math.min(40, Math.round(r * 4)));
  for (const rr of r > 5 ? [r, r * 0.55] : [r]) {
    for (let i = 0; i < n; i++) {
      const a = (2 * Math.PI * i) / n;
      out.push(`${(Math.cos(a) * rr + dx).toFixed(2)}px ${(Math.sin(a) * rr + dy).toFixed(2)}px 0 ${color}`);
    }
  }
  return out;
}
const rgba = (hex, a) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`;
};
const fontOf = (name) => S.fontMap[name] || S.fontMap['Heebo Black'];

function textCss(node, st, k = 1) {
  const f = fontOf(st.font), size = st.size * k;
  Object.assign(node.style, {
    fontFamily: `"${f.name}"`, fontSize: `${size}px`, lineHeight: f.scale,
    letterSpacing: `${st.letterSpacing * k}px`, color: st.color,
    textShadow: [
      ...ring(st.outlineWidth * k, st.outlineColor),
      ...(st.shadow > 0 ? ring(st.outlineWidth * k, st.shadowColor, st.shadow * k, st.shadow * k) : []),
    ].join(',') || 'none',
  });
  return { f, size };
}
function boxCss(inner, f, size, color, pad) {
  Object.assign(inner.style, {
    background: color,
    // vertical extent = the libass line box; only the sides get extra padding (\ybord0)
    padding: `${Math.max(f.padTop * size, 0)}px ${pad}px ${Math.max(f.padBot * size, 0)}px`,
  });
}

/* ---------------- clip model ---------------- */
const disp = (w, st) => (st.stripPunct ? w.t.replace(/^[\s.,!?;:"'“”…\-–]+|[\s.,!?;:"'“”…\-–]+$/g, '') : w.t);
const clip = () => S.clips[S.cur];

function rechunk(c) {
  const n = c.style.wordsPerLine;
  let count = 0;
  c.words.forEach((w, i) => {
    const next = c.words[i + 1];
    count++;
    w.br = count >= n || /[.?!…]["'”]?$/.test(w.t) || !next || next.s - w.e > 0.5;
    if (w.br) count = 0;
  });
}
function initClip(c) {
  const padT = 20;
  const out = {
    id: c.id, title: c.title, score: c.score, reasons: c.reasons || [],
    start: c.start, end: c.end, orig: { start: c.start, end: c.end },
    words: S.job.words.filter((w) => w.e > c.start - padT && w.s < c.end + padT).map((w) => ({ ...w })),
    style: { ...S.defaults, wordsPerLine: 3, stripPunct: true },
    crop: { mode: 'fill', x: 0.5 }, exportId: null,
  };
  rechunk(out);
  return out;
}
function getLines(c = clip()) {
  const groups = [];
  let cur = [];
  for (const w of c.words) { cur.push(w); if (w.br) { groups.push(cur); cur = []; } }
  if (cur.length) groups.push(cur);
  const lines = groups.map((ws) => ({ words: ws, s: ws[0].s, e: ws[ws.length - 1].e }));
  lines.forEach((l, i) => { l.e = Math.min(lines[i + 1] ? lines[i + 1].s : Infinity, l.e + 0.35); });
  return lines
    .filter((l) => l.e > c.start && l.s < c.end)
    .map((l) => ({ ...l, s: Math.max(l.s, c.start), e: Math.min(l.e, c.end) }));
}
const lines = () => (S.lines ||= getLines());

let saveTimer;
function changed({ structure = false } = {}) {
  S.lines = null; S.lineIdx = -2;
  if (structure) renderLineList();
  renderOverlay();
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    try {
      localStorage.setItem(`shorts:${S.job.id}`, JSON.stringify(S.clips));
    } catch {}
  }, 400);
}

/* ---------------- overlay ---------------- */
function renderTitle() {
  const st = clip().style;
  titleEl.replaceChildren();
  if (!st.titleText.trim()) return;
  const f = fontOf(st.titleFont), size = st.titleSize;
  Object.assign(titleEl.style, {
    left: '540px', top: `${1920 * st.titlePosY / 100}px`, textAlign: 'center',
    transform: `translate(-50%,-50%) translateY(${f.shift * size}px)`,
    fontFamily: `"${f.name}"`, fontSize: `${size}px`, lineHeight: f.scale, color: st.titleColor,
  });
  const inner = el('span', { className: 'inner', dir: 'auto', textContent: st.titleText.trim() });
  boxCss(inner, f, size, st.titleBgColor, 18);
  titleEl.append(inner);
}

function renderOverlay() {
  const c = clip();
  if (!c) return;
  const st = c.style, t = video.currentTime;
  const ls = lines();
  const idx = ls.findIndex((l) => t >= l.s && t < l.e);
  if (idx !== S.lineIdx) {
    S.lineIdx = idx;
    subEl.replaceChildren();
    $$('.line.on').forEach((n) => n.classList.remove('on'));
    if (idx >= 0) {
      const { f, size } = textCss(subEl, st);
      const ax = { left: [54, '0'], center: [540, '-50%'], right: [1026, '-100%'] }[st.align] || [540, '-50%'];
      Object.assign(subEl.style, {
        left: `${ax[0]}px`, top: `${1920 * st.posY / 100}px`, textAlign: st.align,
        transform: `translate(${ax[1]},-50%) translateY(${f.shift * size}px)`,
      });
      const anim = el('span', { className: `anim ${st.animation}` });
      anim.style.transformOrigin = { left: '0 50%', center: '50% 50%', right: '100% 50%' }[st.align];
      const inner = el('span', { className: 'inner', dir: 'auto' });
      if (st.bgEnabled) boxCss(inner, f, size, rgba(st.bgColor, st.bgOpacity), st.bgPadding);
      ls[idx].words.forEach((w, i) => {
        const text = disp(w, st);
        if (!text) return;
        if (inner.childNodes.length) inner.append(' ');
        const span = el('span', { className: 'w', textContent: text });
        span._w = w; span._i = i;
        inner.append(span);
      });
      anim.append(inner);
      subEl.append(anim);
      const row = $(`.line[data-i="${idx}"]`);
      if (row) row.classList.add('on');
    }
  }
  if (idx >= 0) {
    const ws = ls[idx].words;
    let active = 0;
    ws.forEach((w, i) => { if (t >= w.s) active = i; });
    for (const span of $$('.w', subEl)) {
      span.style.color = st.highlightEnabled && span._i === active ? st.highlightColor : '';
      span.style.opacity = st.animation === 'reveal' && span._i > active ? 0 : 1;
    }
  }
}

function applyCrop() {
  const { mode, x } = clip().crop;
  bgVideo.hidden = mode !== 'fit';
  video.style.objectFit = mode === 'fit' ? 'contain' : 'cover';
  video.style.objectPosition = `${x * 100}% 50%`;
}

function tick() {
  const c = clip();
  if (c && !$('#editor').hidden) {
    const t = video.currentTime;
    if (t >= c.end || t < c.start - 0.3) {
      video.currentTime = c.start;
    }
    if (!bgVideo.hidden && Math.abs(bgVideo.currentTime - t) > 0.25) bgVideo.currentTime = t;
    renderOverlay();
    if (document.activeElement !== $('#seek')) $('#seek').value = t;
    $('#timeLbl').textContent = `${fmt(Math.max(t - c.start, 0))} / ${fmt(c.end - c.start)}`;
  }
  requestAnimationFrame(tick);
}

function fitCanvas() {
  const k = $('#phone').clientWidth / 1080;
  $('#canvas').style.transform = `scale(${k})`;
}
new ResizeObserver(fitCanvas).observe($('#phone'));

/* ---------------- transport ---------------- */
function setPlaying(on) {
  if (on) { video.play(); if (!bgVideo.hidden) bgVideo.play(); } else { video.pause(); bgVideo.pause(); }
}
video.addEventListener('play', () => { $('#playBtn').textContent = '❚❚'; });
video.addEventListener('pause', () => { $('#playBtn').textContent = '▶'; bgVideo.pause(); });
$('#playBtn').onclick = () => setPlaying(video.paused);
$('#seek').oninput = (e) => { video.currentTime = +e.target.value; };
document.addEventListener('keydown', (e) => {
  if (e.code === 'Space' && !/INPUT|SELECT|TEXTAREA|BUTTON/.test(e.target.tagName) && !$('#editor').hidden) {
    e.preventDefault(); setPlaying(video.paused);
  }
});
function syncSeekRange() {
  const c = clip();
  Object.assign($('#seek'), { min: c.start, max: c.end });
}

// drag the subtitle up/down on the preview
subEl.addEventListener('pointerdown', (e) => {
  subEl.setPointerCapture(e.pointerId);
  const rect = $('#phone').getBoundingClientRect();
  const move = (ev) => {
    const y = Math.round(Math.max(5, Math.min(95, ((ev.clientY - rect.top) / rect.height) * 100)));
    clip().style.posY = y;
    const inp = $('#ctl-posY'); if (inp) { inp.value = y; inp.dispatchEvent(new Event('sync')); }
    changed();
  };
  const up = () => { subEl.removeEventListener('pointermove', move); subEl.removeEventListener('pointerup', up); };
  subEl.addEventListener('pointermove', move);
  subEl.addEventListener('pointerup', up);
});

/* ---------------- generic controls ---------------- */
const STYLE_CONTROLS = [
  { h: 'טקסט' },
  { k: 'size', label: 'גודל', type: 'range', min: 30, max: 220, step: 1 },
  { k: 'color', label: 'צבע טקסט', type: 'color' },
  { k: 'letterSpacing', label: 'ריווח אותיות', type: 'range', min: -4, max: 30, step: 1 },
  { k: 'wordsPerLine', label: 'מילים בשורה', type: 'range', min: 1, max: 6, step: 1, rechunk: true },
  { k: 'stripPunct', label: 'הסר סימני פיסוק', type: 'check' },
  { h: 'הדגשת המילה הנאמרת' },
  { k: 'highlightEnabled', label: 'הדגשה פעילה', type: 'check' },
  { k: 'highlightColor', label: 'צבע הדגשה', type: 'color' },
  { h: 'קו מתאר וצל' },
  { k: 'outlineWidth', label: 'עובי קו מתאר', type: 'range', min: 0, max: 20, step: 1 },
  { k: 'outlineColor', label: 'צבע קו מתאר', type: 'color' },
  { k: 'shadow', label: 'צל', type: 'range', min: 0, max: 20, step: 1 },
  { k: 'shadowColor', label: 'צבע צל', type: 'color' },
  { h: 'רקע לטקסט' },
  { k: 'bgEnabled', label: 'תיבת רקע', type: 'check' },
  { k: 'bgColor', label: 'צבע רקע', type: 'color' },
  { k: 'bgOpacity', label: 'אטימות', type: 'range', min: 0.1, max: 1, step: 0.05 },
  { k: 'bgPadding', label: 'ריפוד בצדדים', type: 'range', min: 0, max: 50, step: 1 },
  { h: 'מיקום ואנימציה' },
  { k: 'posY', label: 'גובה במסך', type: 'range', min: 5, max: 95, step: 1 },
  { k: 'align', label: 'יישור', type: 'seg', options: [['right', 'ימין'], ['center', 'מרכז'], ['left', 'שמאל']] },
  { k: 'animation', label: 'אנימציה', type: 'seg', options: [['none', 'ללא'], ['pop', 'קפיצה'], ['fade', 'עמעום'], ['reveal', 'מילה-מילה']] },
];
const CLIP_CONTROLS = [
  { h: 'חיתוך הקטע' },
  { k: 'start', label: 'התחלה (שניות)', type: 'time', obj: 'clip' },
  { k: 'end', label: 'סיום (שניות)', type: 'time', obj: 'clip' },
  { h: 'מסגור 9:16' },
  { k: 'mode', label: 'מצב', type: 'seg', obj: 'crop', options: [['fill', 'מילוי וחיתוך'], ['fit', 'התאמה + רקע מטושטש']] },
  { k: 'x', label: 'הזזה אופקית', type: 'range', obj: 'crop', min: 0, max: 1, step: 0.01 },
  { h: 'כותרת בראש הסרטון' },
  { k: 'titleText', label: 'טקסט כותרת', type: 'text' },
  { k: 'titleFont', label: 'גופן כותרת', type: 'font' },
  { k: 'titleSize', label: 'גודל כותרת', type: 'range', min: 30, max: 140, step: 1 },
  { k: 'titleColor', label: 'צבע כותרת', type: 'color' },
  { k: 'titleBgColor', label: 'רקע כותרת', type: 'color' },
  { k: 'titlePosY', label: 'גובה כותרת', type: 'range', min: 4, max: 60, step: 1 },
];

function buildControls(host, defs) {
  host.replaceChildren();
  const c = clip();
  for (const d of defs) {
    if (d.h) { host.append(el('h3', { textContent: d.h })); continue; }
    const target = d.obj === 'clip' ? c : d.obj === 'crop' ? c.crop : c.style;
    const row = el('div', { className: 'ctl' }, el('label', { textContent: d.label, htmlFor: `ctl-${d.k}` }));
    const set = (v) => {
      target[d.k] = v;
      if (d.rechunk) rechunk(c);
      if (d.obj === 'crop') applyCrop();
      if (d.k.startsWith('title')) renderTitle();
      changed({ structure: !!d.rechunk || d.k === 'stripPunct' });
    };
    let input, out = el('span');
    if (d.type === 'range') {
      input = el('input', { type: 'range', min: d.min, max: d.max, step: d.step, value: target[d.k], dir: 'ltr' });
      out = el('output', { textContent: target[d.k] });
      input.oninput = () => { out.textContent = input.value; set(+input.value); };
      input.addEventListener('sync', () => { out.textContent = input.value; });
    } else if (d.type === 'color') {
      input = el('input', { type: 'color', value: target[d.k] });
      input.oninput = () => set(input.value.toUpperCase());
    } else if (d.type === 'check') {
      input = el('input', { type: 'checkbox', checked: !!target[d.k] });
      input.onchange = () => set(input.checked);
    } else if (d.type === 'text') {
      input = el('input', { type: 'text', value: target[d.k], dir: 'auto', maxLength: 80 });
      input.oninput = () => set(input.value);
    } else if (d.type === 'font') {
      input = el('select', {}, ...S.fonts.map((f) => el('option', { value: f.name, textContent: f.name })));
      input.value = target[d.k];
      input.onchange = () => set(input.value);
    } else if (d.type === 'seg') {
      input = el('div', { className: 'seg' });
      for (const [v, label] of d.options) {
        const b = el('button', { type: 'button', textContent: label, className: target[d.k] === v ? 'on' : '' });
        b.onclick = () => { $$('button', input).forEach((x) => x.classList.toggle('on', x === b)); set(v); };
        input.append(b);
      }
    } else if (d.type === 'time') {
      input = el('input', { type: 'number', step: 0.1, value: c[d.k].toFixed(1), dir: 'ltr' });
      out = el('button', { className: 'btn small', textContent: 'מהנגן', title: 'קבע לפי המיקום הנוכחי בנגן' });
      const apply = (v) => {
        const lo = d.k === 'start' ? Math.max(c.orig.start - 20, 0) : c.start + 3;
        const hi = d.k === 'start' ? c.end - 3 : Math.min(c.orig.end + 20, S.job.duration);
        v = Math.max(lo, Math.min(hi, v || 0));
        input.value = v.toFixed(1);
        c[d.k] = v; syncSeekRange(); renderClipList(); changed({ structure: true });
      };
      input.onchange = () => apply(+input.value);
      out.onclick = () => apply(video.currentTime);
    }
    input.id = `ctl-${d.k}`;
    row.append(input, out);
    host.append(row);
  }
}

/* ---------------- style tab ---------------- */
function customPresets() {
  try { return JSON.parse(localStorage.getItem('shorts:presets') || '[]'); } catch { return []; }
}
function renderPresets() {
  const host = $('#presets');
  host.replaceChildren();
  const add = (p, custom, i) => {
    const st = { ...S.defaults, ...p.s };
    const b = el('button', { className: 'preset', title: p.name });
    const sample = el('span', { textContent: p.name });
    const k = Math.min(0.22, 20 / st.size);
    const { f, size } = textCss(sample, st, k);
    if (st.bgEnabled) boxCss(sample, f, size, rgba(st.bgColor, st.bgOpacity), st.bgPadding * k);
    b.append(sample);
    b.onclick = () => { applyStyle(p.s); };
    if (custom) {
      const del = el('span', { className: 'del', textContent: '✕', title: 'מחק סגנון' });
      del.onclick = (e) => {
        e.stopPropagation();
        const list = customPresets(); list.splice(i, 1);
        localStorage.setItem('shorts:presets', JSON.stringify(list)); renderPresets();
      };
      b.append(del);
    }
    host.append(b);
  };
  PRESETS.forEach((p) => add(p, false));
  customPresets().forEach((p, i) => add(p, true, i));
}
function applyStyle(s) {
  const c = clip();
  const keep = { titleText: c.style.titleText, posY: c.style.posY };
  Object.assign(c.style, s, s.posY === undefined ? keep : { titleText: keep.titleText });
  rechunk(c);
  renderStyleTab();
  changed({ structure: true });
}
function renderFontList() {
  const host = $('#fontList');
  host.replaceChildren();
  for (const f of S.fonts) {
    const b = el('button', { className: f.name === clip().style.font ? 'on' : '' },
      'שלום עולם', el('small', { textContent: f.name }));
    b.style.fontFamily = `"${f.name}"`;
    b.onclick = () => {
      clip().style.font = f.name;
      $$('button', host).forEach((x) => x.classList.toggle('on', x === b));
      changed();
    };
    host.append(b);
  }
}
function renderStyleTab() {
  renderPresets(); renderFontList();
  buildControls($('#styleControls'), STYLE_CONTROLS);
}
$('#savePreset').onclick = () => {
  const name = prompt('שם לסגנון:');
  if (!name) return;
  const { titleText, ...s } = clip().style;
  localStorage.setItem('shorts:presets', JSON.stringify([...customPresets(), { name: name.slice(0, 20), s }]));
  renderPresets();
};
$('#applyAll').onclick = () => {
  const src = clip();
  for (const c of S.clips) {
    if (c === src) continue;
    c.style = { ...src.style, titleText: c.style.titleText };
    rechunk(c);
  }
  changed();
  flash($('#applyAll'), 'הוחל ✓');
};
function flash(btn, text) {
  const old = btn.textContent; btn.textContent = text;
  setTimeout(() => { btn.textContent = old; }, 1400);
}

/* ---------------- text tab ---------------- */
function renderLineList() {
  const host = $('#lineList');
  if ($('#tab-text').hidden) { host.dataset.stale = '1'; return; }
  host.dataset.stale = '';
  host.replaceChildren();
  const c = clip(), st = c.style;
  lines().forEach((l, i) => {
    const ws = l.words, first = ws[0], last = ws[ws.length - 1];
    const row = el('div', { className: 'line' }); row.dataset.i = i;
    const tBtn = el('button', { className: 'btn small t mono', textContent: fmt(l.s - c.start), dir: 'ltr' });
    tBtn.onclick = () => { video.currentTime = l.s + 0.01; };
    const text = el('input', { type: 'text', dir: 'auto', value: ws.map((w) => w.t).join(' ') });
    text.onchange = () => {
      const toks = text.value.trim().split(/\s+/).filter(Boolean);
      const at = c.words.indexOf(first);
      if (!toks.length) c.words.splice(at, ws.length);
      else if (toks.length === ws.length) ws.forEach((w, k) => { w.t = toks[k]; });
      else {
        const span = (last.e - first.s) / toks.length;
        c.words.splice(at, ws.length, ...toks.map((t, k) => ({
          t, s: +(first.s + span * k).toFixed(3), e: +(first.s + span * (k + 1)).toFixed(3), br: k === toks.length - 1,
        })));
      }
      changed({ structure: true });
    };
    const mk = (label, title, fn) => {
      const b = el('button', { className: 'btn small', textContent: label, title });
      b.onclick = () => { fn(); changed({ structure: true }); };
      return b;
    };
    const tIn = (w, key) => {
      const inp = el('input', { type: 'number', step: 0.05, dir: 'ltr', value: (w[key] - c.start).toFixed(2) });
      inp.onchange = () => {
        const v = c.start + (+inp.value || 0);
        if (key === 's') { w.s = Math.min(v, last.e - 0.05); w.e = Math.max(w.e, w.s + 0.05); }
        else { w.e = Math.max(v, first.s + 0.05); w.s = Math.min(w.s, w.e - 0.05); }
        changed({ structure: true });
      };
      return inp;
    };
    const ops = el('div', { className: 'ops' },
      tIn(first, 's'), '←', tIn(last, 'e'), el('span', { className: 'sp' }),
      mk('פצל', 'פצל את השורה במקום הסמן', () => {
        if (ws.length < 2) return;
        let n = text.value.slice(0, text.selectionStart || 0).trim().split(/\s+/).filter(Boolean).length;
        if (n <= 0 || n >= ws.length) n = Math.ceil(ws.length / 2);
        ws[n - 1].br = true;
      }),
      mk('מזג ↓', 'מזג עם השורה הבאה', () => { last.br = false; }),
      mk('מחק', 'מחק את השורה', () => { c.words.splice(c.words.indexOf(first), ws.length); }));
    row.append(tBtn, text, ops);
    host.append(row);
  });
  if (!host.children.length) host.append(el('p', { className: 'hint', textContent: 'אין כתוביות בטווח הקטע.' }));
  void st;
}

/* ---------------- clips sidebar ---------------- */
function renderClipList() {
  const host = $('#clipList');
  host.replaceChildren();
  S.clips.forEach((c, i) => {
    const b = el('button', { className: `clip${i === S.cur ? ' on' : ''}` },
      el('div', { className: 'head' },
        el('span', { textContent: `שורט ${i + 1} · ${Math.round(c.end - c.start)} שנ׳` }),
        el('span', { className: 'score', textContent: c.score, title: 'ציון ויראליות' })),
      el('div', { className: 'ttl', dir: 'auto', textContent: c.title || '—' }),
      el('div', { className: 'why', textContent: c.reasons.join(' · ') }),
      el('div', { className: 'state', textContent: c.exportId ? 'יוצא ✓' : '' }));
    b.onclick = () => selectClip(i);
    host.append(b);
  });
}
function selectClip(i) {
  S.cur = i; S.lines = null; S.lineIdx = -2;
  const c = clip();
  setPlaying(false);
  syncSeekRange();
  video.currentTime = c.start;
  bgVideo.currentTime = c.start;
  applyCrop(); renderTitle(); renderClipList(); renderStyleTab();
  buildControls($('#clipControls'), CLIP_CONTROLS);
  renderLineList(); renderExport(); renderOverlay();
}

$('#tabs').onclick = (e) => {
  const t = e.target.dataset.t;
  if (!t) return;
  $$('#tabs button').forEach((b) => b.classList.toggle('on', b === e.target));
  $$('.tab').forEach((n) => { n.hidden = n.id !== `tab-${t}`; });
  if (t === 'text' && $('#lineList').dataset.stale) { renderLineList(); S.lineIdx = -2; }
};

/* ---------------- export ---------------- */
function exportPayload(c) {
  return {
    clip_id: c.id, start: c.start, end: c.end, style: c.style, crop: c.crop,
    lines: getLines(c).map((l) => ({
      s: l.s, e: l.e,
      words: l.words.map((w) => ({ t: disp(w, c.style), s: w.s, e: w.e })).filter((w) => w.t),
    })).filter((l) => l.words.length),
  };
}
async function exportClip(c, onProgress) {
  const { export_id } = await api(`/api/jobs/${S.job.id}/export`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(exportPayload(c)),
  });
  for (;;) {
    await new Promise((r) => setTimeout(r, 600));
    const st = await api(`/api/jobs/${S.job.id}/export/${export_id}`);
    onProgress(st.progress || 0);
    if (st.status === 'error') throw new Error(st.message || 'הייצוא נכשל');
    if (st.status === 'done') { c.exportId = export_id; return export_id; }
  }
}
function renderExport() {
  const c = clip(), host = $('#expResult');
  host.replaceChildren();
  $('#expMsg').textContent = '';
  $('#expBarWrap').hidden = true;
  if (c.exportId) {
    const url = `/api/jobs/${S.job.id}/export/${c.exportId}/download`;
    host.append(el('video', { src: url, controls: true, preload: 'metadata' }),
      el('a', { className: 'btn primary wide', href: url, download: `short_${c.id + 1}.mp4`, textContent: 'הורד את השורט' }));
  }
}
$('#exportOne').onclick = async () => {
  const c = clip(), btn = $('#exportOne');
  btn.disabled = true; $('#expBarWrap').hidden = false; $('#expBar').style.width = '0';
  $('#expMsg').textContent = 'מייצא...';
  try {
    await exportClip(c, (p) => { $('#expBar').style.width = `${p * 100}%`; });
    renderClipList(); if (c === clip()) renderExport(); changed();
  } catch (e) { $('#expMsg').textContent = `שגיאה: ${e.message}`; }
  btn.disabled = false;
};
$('#exportAll').onclick = async () => {
  const btn = $('#exportAll');
  btn.disabled = true;
  try {
    for (let i = 0; i < S.clips.length; i++) {
      await exportClip(S.clips[i], (p) => { btn.textContent = `מייצא ${i + 1}/${S.clips.length} · ${Math.round(p * 100)}%`; });
      renderClipList();
    }
    btn.textContent = 'הכול יוצא ✓ - ההורדה בלשונית ייצוא';
    renderExport(); changed();
  } catch (e) { btn.textContent = `שגיאה: ${e.message}`; }
  setTimeout(() => { btn.textContent = 'ייצא את כל השורטס'; btn.disabled = false; }, 4000);
};
$('#srtBtn').onclick = () => {
  const c = clip();
  const ts = (t) => {
    const ms = Math.max(Math.round((t - c.start) * 1000), 0);
    const p = (n, l = 2) => String(n).padStart(l, '0');
    return `${p(Math.floor(ms / 3600000))}:${p(Math.floor(ms / 60000) % 60)}:${p(Math.floor(ms / 1000) % 60)},${p(ms % 1000, 3)}`;
  };
  const srt = exportPayload(c).lines.map((l, i) =>
    `${i + 1}\n${ts(l.s)} --> ${ts(l.e)}\n${l.words.map((w) => w.t).join(' ')}\n`).join('\n');
  const a = el('a', { href: URL.createObjectURL(new Blob([srt], { type: 'text/plain' })), download: `short_${c.id + 1}.srt` });
  a.click(); URL.revokeObjectURL(a.href);
};

/* ---------------- views ---------------- */
function show(view) {
  for (const v of ['home', 'progress', 'editor']) $(`#${v}`).hidden = v !== view;
  if (view !== 'editor') setPlaying(false);
}
function openEditor(job) {
  S.job = job;
  let saved = null;
  try { saved = JSON.parse(localStorage.getItem(`shorts:${job.id}`)); } catch {}
  S.clips = Array.isArray(saved) && saved.length === job.clips.length
    ? saved.map((c) => ({ ...c, style: { ...S.defaults, ...c.style } }))
    : job.clips.map(initClip);
  $('#edTitle').textContent = job.title || 'שורטס';
  const src = `/api/jobs/${job.id}/video`;
  video.src = src; bgVideo.src = src;
  show('editor');
  fitCanvas();
  if (!S.clips.length) { $('#clipList').replaceChildren(el('p', { className: 'hint', textContent: 'לא נמצאו קטעים מתאימים.' })); return; }
  video.addEventListener('loadedmetadata', () => selectClip(0), { once: true });
  location.hash = job.id;
}
async function watch(id) {
  show('progress');
  $('#progErr').hidden = true; $('#progBack').hidden = true; $('#progBlocked').hidden = true;
  const order = ['downloading', 'transcribing', 'analyzing'];
  clearInterval(S.pollTimer);
  const poll = async () => {
    let job;
    try { job = await api(`/api/jobs/${id}`); } catch (e) { job = { status: 'error', message: e.message }; }
    const at = order.indexOf(job.status);
    $$('#steps li').forEach((li, i) => {
      li.classList.toggle('on', i === at); li.classList.toggle('done', at > i || job.status === 'ready');
    });
    $('#progBar').style.width = `${(job.progress || 0) * 100}%`;
    $('#progMsg').textContent = job.status === 'error' ? '' : job.message || '';
    if (job.title) $('#progTitle').textContent = job.title;
    const done = job.status === 'ready' || job.status === 'error';
    $('#progCancel').hidden = done;
    $('#progCancel').onclick = () => api(`/api/jobs/${id}/cancel`, { method: 'POST' }).catch(() => {});
    $('#progBlocked').hidden = !job.blocked_by;
    if (job.blocked_by) {
      $('#blockTitle').textContent = job.blocked_by.title || 'ללא שם';
      $('#blockMsg').textContent = job.blocked_by.message;
      $('#blockCancel').onclick = () => api(`/api/jobs/${job.blocked_by.id}/cancel`, { method: 'POST' }).catch(() => {});
    }
    if (job.status === 'ready') { clearInterval(S.pollTimer); openEditor(job); }
    if (job.status === 'error') {
      clearInterval(S.pollTimer);
      $('#progErr').textContent = job.message; $('#progErr').hidden = false; $('#progBack').hidden = false;
    }
  };
  S.pollTimer = setInterval(poll, 1000);
  poll();
}
async function loadRecent() {
  const list = await api('/api/jobs').catch(() => []);
  $('#recent').hidden = !list.length;
  $('#recentList').replaceChildren(...list.map((j) => {
    const name = el('span', { className: 'name', dir: 'auto', textContent: j.title || 'ללא שם' });
    name.onclick = () => watch(j.id);
    const meta = el('span', { className: 'meta', textContent:
      j.status === 'ready' ? `${j.clips} שורטס` : j.status === 'error' ? 'נכשל' : 'בעיבוד' });
    const del = el('button', { className: 'btn small', textContent: 'מחק' });
    del.onclick = async () => {
      if (!confirm('למחוק את הפרויקט ואת כל הקבצים שלו?')) return;
      try { await api(`/api/jobs/${j.id}`, { method: 'DELETE' }); localStorage.removeItem(`shorts:${j.id}`); } catch {}
      loadRecent();
    };
    return el('li', {}, name, meta, del);
  }));
}
async function loadPhoneCard() {
  const info = await api('/api/phone').catch(() => ({ enabled: false }));
  $('#phoneCard').hidden = !info.enabled;
  if (!info.enabled) return;
  $('#phoneQr').innerHTML = info.qr_svg; // SVG generated by our own server
  $('#phoneUrl').textContent = info.url;
  $('#phonePin').textContent = info.pin;
}
function goHome() {
  clearInterval(S.pollTimer);
  history.replaceState(null, '', location.pathname);
  show('home'); loadRecent(); loadPhoneCard();
}
$('#backHome').onclick = goHome;
$('#progBack').onclick = goHome;

$('#countSeg').onclick = (e) => {
  if (e.target.dataset.v) $$('#countSeg button').forEach((b) => b.classList.toggle('on', b === e.target));
};
$('#jobForm').onsubmit = async (e) => {
  e.preventDefault();
  const err = $('#formErr'); err.hidden = true;
  const opts = {
    count: +$('#countSeg .on').dataset.v, model: $('#model').value, language: $('#language').value,
    min_len: +$('#minLen').value, max_len: +$('#maxLen').value,
  };
  const file = $('#file').files[0], url = $('#url').value.trim();
  try {
    let job;
    if (file) {
      const fd = new FormData();
      fd.append('file', file);
      for (const [k, v] of Object.entries(opts)) fd.append(k, v);
      job = await api('/api/jobs/upload', { method: 'POST', body: fd });
    } else {
      if (!url) throw new Error('הדבק קישור לסרטון או בחר קובץ');
      job = await api('/api/jobs', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, cookies_browser: $('#cookies').value, quality: +$('#quality').value, ...opts }),
      });
    }
    $('#progTitle').textContent = 'מעבד את הסרטון';
    watch(job.id);
  } catch (ex) { err.textContent = ex.message; err.hidden = false; }
};

/* ---------------- boot ---------------- */
(async function boot() {
  const [fonts, defaults] = await Promise.all([api('/api/fonts'), api('/api/defaults')]);
  S.fonts = fonts; S.defaults = defaults.style;
  fonts.forEach((f) => { S.fontMap[f.name] = f; });
  document.head.append(el('style', { textContent: fonts.map((f) =>
    `@font-face{font-family:"${f.name}";src:url("/fonts/${f.file}");font-display:swap}`).join('\n') }));
  await Promise.all(fonts.map((f) => document.fonts.load(`40px "${f.name}"`, 'שלום').catch(() => {})));
  requestAnimationFrame(tick);
  const id = location.hash.slice(1);
  if (/^[0-9a-f]{12}$/.test(id)) watch(id); else goHome();
})();
