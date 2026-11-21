'use strict';
// Option 3: Gil & Noga. Storybook "cut paper" look: muted colors, layered shapes with soft
// drop shadows, slightly wobbly edges and paper grain (SVG filters).
const { g, limb } = require('./lib');

const C = { ink: '#3B2A26', mouth: '#7A3530', tongue: '#F08A8A', shadow: 'rgba(70,50,30,.16)' };

// Filters live inside each character so any copy carries its own definitions.
function filters(id) {
  return `<defs>` +
    `<filter id="${id}-paper" x="-6%" y="-6%" width="112%" height="112%" color-interpolation-filters="sRGB">` +
    `<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7" result="warp"/>` +
    `<feDisplacementMap in="SourceGraphic" in2="warp" scale="4" xChannelSelector="R" yChannelSelector="G" result="wob"/>` +
    `<feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3" result="grain"/>` +
    `<feColorMatrix in="grain" type="matrix" values="0 0 0 0 0.25  0 0 0 0 0.18  0 0 0 0 0.12  0 0 0 0.45 -0.12" result="grainC"/>` +
    `<feComposite in="grainC" in2="wob" operator="in" result="grainIn"/>` +
    `<feMerge><feMergeNode in="wob"/><feMergeNode in="grainIn"/></feMerge></filter>` +
    `<filter id="${id}-cut" x="-15%" y="-15%" width="130%" height="135%">` +
    `<feDropShadow dx="0" dy="3" stdDeviation="1.8" flood-color="#3B2A1A" flood-opacity=".3"/></filter>` +
    `</defs>`;
}
const cut = id => `filter="url(#${id}-cut)"`;

function mouth(id, expr) {
  if (expr === 'surprised') {
    return `<ellipse cx="0" cy="6" rx="11" ry="14" fill="${C.mouth}"/><ellipse cx="0" cy="14" rx="7" ry="4" fill="${C.tongue}"/>`;
  }
  const laugh = expr === 'laugh';
  const d = laugh ? 'M-30,-4 Q0,4 30,-4 Q26,38 0,40 Q-26,38 -30,-4Z' : 'M-20,-2 Q0,3 20,-2 Q17,20 0,21 Q-17,20 -20,-2Z';
  const cid = `${id}-mclip`;
  return `<clipPath id="${cid}"><path d="${d}"/></clipPath><path d="${d}" fill="${C.mouth}"/>` +
    `<g clip-path="url(#${cid})"><rect x="-40" y="-10" width="80" height="${laugh ? 13 : 10}" fill="#FFF8EE"/>` +
    `<ellipse cx="0" cy="${laugh ? 36 : 20}" rx="${laugh ? 18 : 11}" ry="${laugh ? 12 : 7}" fill="${C.tongue}"/></g>`;
}

function cheeks(x, y, color, on) {
  return [-1, 1].map(s => `<circle cx="${s * x}" cy="${y}" r="13" fill="${color}" opacity="${on ? 0.75 : 0.5}"/>`).join('');
}

function note(x, y, color, rot = 0) {
  return `<g transform="translate(${x},${y}) rotate(${rot})"><ellipse cx="0" cy="0" rx="9" ry="6.5" transform="rotate(-20)" fill="${color}"/>` +
    `<rect x="6" y="-32" width="4" height="32" fill="${color}"/><path d="M10,-32 q13,5 9,18" fill="none" stroke="${color}" stroke-width="4" stroke-linecap="round"/></g>`;
}

// ---------- Gil ----------
const G = { skin: '#F1C7A5', skinD: '#DDA785', cheek: '#E98F7E', hair: '#D2632B', hairD: '#A9491B',
  shirt: '#E8B54A', overall: '#5B7DB1', overallD: '#48689A', shoe: '#7A4E32', pillow: '#C9B6E4', pillowD: '#9C86C6' };

function gilHead(id, { expr = 'happy', blink = false } = {}) {
  const spikesBack = `<path d="M-84,-30 L-112,-70 L-70,-58 L-70,-118 L-36,-76 L-10,-150 L10,-82 L44,-140 L46,-74 L96,-104 L76,-46 L112,-40 L84,-10Z" fill="${G.hairD}"/>`;
  const spikes = `<path d="M-92,-4 L-104,-50 L-78,-40 L-82,-96 L-50,-62 L-36,-128 L-12,-70 L10,-142 L26,-72 L58,-122 L60,-62 L94,-90 L82,-38 L104,-44 L92,-4 Q60,-48 0,-50 Q-60,-48 -92,-4Z" fill="${G.hair}"/>`;
  const ears = [-1, 1].map(s => `<circle cx="${s * 89}" cy="12" r="16" fill="${G.skin}"/>`).join('');
  const face = `<ellipse cx="0" cy="6" rx="90" ry="86" fill="${G.skin}"/>` + cheeks(56, 40, G.cheek, expr === 'laugh') +
    `<ellipse cx="0" cy="30" rx="9" ry="7" fill="${G.skinD}"/>` +
    [[-60, 26], [-50, 32], [-64, 36], [60, 26], [50, 32], [64, 36]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="2.4" fill="${G.hairD}" opacity=".55"/>`).join('');
  const eyes = [-34, 34].map(x => {
    if (expr === 'laugh' || blink) return `<path d="M${x - 13},10 Q${x},-4 ${x + 13},10" fill="none" stroke="${C.ink}" stroke-width="5.5" stroke-linecap="round"/>`;
    if (expr === 'surprised') return `<circle cx="${x}" cy="6" r="16" fill="#FFF8EE"/><circle cx="${x}" cy="7" r="7" fill="${C.ink}"/><circle cx="${x + 2.5}" cy="4" r="2.2" fill="#fff"/>`;
    // sleepy: half-closed lids
    return `<path d="M${x - 12},9 Q${x},5 ${x + 12},9 Q${x + 10},21 ${x},21 Q${x - 10},21 ${x - 12},9Z" fill="${C.ink}"/>` +
      `<path d="M${x - 16},10 Q${x},2 ${x + 16},10" fill="none" stroke="${C.ink}" stroke-width="4.5" stroke-linecap="round"/>` +
      `<circle cx="${x + 3}" cy="14" r="2" fill="#fff"/>`;
  }).join('');
  const brows = [-34, 34].map(x => expr === 'surprised'
    ? `<path d="M${x - 13},-24 Q${x},-34 ${x + 13},-24" fill="none" stroke="${G.hairD}" stroke-width="5" stroke-linecap="round"/>`
    : `<path d="M${x - 12},-10 Q${x},-18 ${x + 12},-10" fill="none" stroke="${G.hairD}" stroke-width="5" stroke-linecap="round"/>`).join('');
  return g(`${id}-head`,
    g(`${id}-hair-back`, spikesBack, cut(id)) + g(`${id}-ears`, ears) + g(`${id}-face`, face, cut(id)) +
    g(`${id}-eyes`, eyes) + g(`${id}-brows`, brows) +
    g(`${id}-mouth`, mouth(id, expr), 'transform="translate(0,52)"') +
    g(`${id}-hair`, spikes, cut(id)));
}

function gilFull(id, opts = {}) {
  const legs = `<path d="M124,436 L276,436 L272,596 L210,596 L204,500 L196,500 L190,596 L128,596Z" fill="${G.overall}"/>` +
    `<path d="M130,580 L188,580 M212,580 L270,580" stroke="${G.overallD}" stroke-width="10"/>` +
    [158, 242].map(x => `<ellipse cx="${x}" cy="606" rx="38" ry="19" fill="${G.shoe}"/>`).join('');
  const torso = `<path d="M146,282 Q200,268 254,282 Q274,290 276,314 L280,456 L120,456 L124,314 Q126,290 146,282Z" fill="${G.shirt}"/>` +
    `<path d="M156,338 L244,338 L248,452 L152,452Z" fill="${G.overall}"/>` +
    `<path d="M150,286 L160,344 M250,286 L240,344" stroke="${G.overall}" stroke-width="14" stroke-linecap="round"/>` +
    `<circle cx="161" cy="346" r="6" fill="${G.shirt}"/><circle cx="239" cy="346" r="6" fill="${G.shirt}"/>` +
    `<rect x="176" y="368" width="48" height="40" rx="6" fill="${G.overallD}"/>` +
    `<rect x="181" y="373" width="38" height="30" rx="4" fill="none" stroke="${G.overall}" stroke-width="2" stroke-dasharray="4 3"/>`;
  const pillow = `<g transform="translate(282,404) rotate(-12)"><rect x="-52" y="-34" width="104" height="68" rx="26" fill="${G.pillow}"/>` +
    `<rect x="-44" y="-26" width="88" height="52" rx="20" fill="none" stroke="${G.pillowD}" stroke-width="2.5" stroke-dasharray="5 4"/></g>`;
  const armL = limb('M144,300 Q110,352 118,408', G.shirt, 30) + `<circle cx="118" cy="420" r="17" fill="${G.skin}"/>`;
  const armR = limb('M256,300 Q302,328 296,378', G.shirt, 30) + `<circle cx="290" cy="390" r="17" fill="${G.skin}"/>`;
  return g(id, filters(id) + g('',
    `<ellipse cx="200" cy="624" rx="110" ry="13" fill="${C.shadow}"/>` +
    g(`${id}-legs`, legs, cut(id)) + g(`${id}-body`, torso, cut(id)) +
    g(`${id}-arm-l`, armL, cut(id)) +
    g('', gilHead(id, opts), 'transform="translate(200,190)"') +
    g(`${id}-pillow`, pillow, cut(id)) + g(`${id}-arm-r`, armR, cut(id)),
  `filter="url(#${id}-paper)"`));
}

// ---------- Noga ----------
const NG = { skin: '#E8B08A', skinD: '#D09670', cheek: '#E87F72', hair: '#3A2626', hairL: '#5E4242',
  petal: '#E86A92', petalD: '#C94F78', center: '#F4CC52', skirt: '#3FA7A0', shoe: '#C8414B', wood: '#B07A4A', woodD: '#8A5A32',
  stripes: ['#D9534F', '#F0954A', '#F4CC52', '#6DB57A', '#5B8FD1', '#8E6BBF', '#D9534F'] };

function flower(x, y, s = 1) {
  let p = '';
  for (let i = 0; i < 5; i++) {
    const a = i * 72;
    p += `<ellipse cx="0" cy="-15" rx="10" ry="14" transform="rotate(${a})" fill="${NG.petal}"/>`;
  }
  return `<g transform="translate(${x},${y}) scale(${s})">${p}<circle r="9" fill="${NG.center}"/><circle r="9" fill="none" stroke="${NG.petalD}" stroke-width="2"/></g>`;
}

function nogaHead(id, { expr = 'happy', blink = false } = {}) {
  const back = `<path d="M-104,40 Q-114,-98 0,-106 Q114,-98 104,40 Q106,74 82,76 L-82,76 Q-106,74 -104,40Z" fill="${NG.hair}"/>`;
  const face = `<ellipse cx="0" cy="8" rx="86" ry="84" fill="${NG.skin}"/>` + cheeks(52, 42, NG.cheek, expr === 'laugh') +
    `<ellipse cx="0" cy="30" rx="7" ry="5.5" fill="${NG.skinD}"/>`;
  const bangs = `<path d="M-90,-14 Q-94,-94 0,-98 Q94,-94 90,-14 L72,-26 L60,-20 L46,-34 L30,-26 L14,-38 L0,-28 L-14,-38 L-30,-26 L-46,-34 L-60,-20 L-72,-26Z" fill="${NG.hair}"/>` +
    `<path d="M-50,-74 q40,-18 86,-6" fill="none" stroke="${NG.hairL}" stroke-width="5" stroke-linecap="round"/>`;
  const eyes = [-32, 32].map((x, i) => {
    const side = i === 0 ? -1 : 1;
    if (expr === 'laugh' || blink) return `<path d="M${x - 13},10 Q${x},-4 ${x + 13},10" fill="none" stroke="${C.ink}" stroke-width="5.5" stroke-linecap="round"/>` +
      `<path d="M${x + side * 12},4 l${side * 8},-5" stroke="${C.ink}" stroke-width="3.5" stroke-linecap="round"/>`;
    const big = expr === 'surprised';
    const rx = big ? 11 : 9, ry = big ? 15 : 12;
    return `<ellipse cx="${x}" cy="8" rx="${rx}" ry="${ry}" fill="${C.ink}"/><circle cx="${x + 3}" cy="${8 - ry * 0.4}" r="3.2" fill="#fff"/>` +
      `<path d="M${x + side * (rx - 2)},${8 - ry + 4} l${side * 9},-6 M${x + side * rx},${8 - ry + 10} l${side * 10},-2" stroke="${C.ink}" stroke-width="3.5" stroke-linecap="round"/>`;
  }).join('');
  const brows = [-32, 32].map(x => {
    const y = expr === 'surprised' ? -22 : -14;
    return `<path d="M${x - 12},${y + 3} Q${x},${y - 6} ${x + 12},${y + 3}" fill="none" stroke="${NG.hair}" stroke-width="4.5" stroke-linecap="round"/>`;
  }).join('');
  return g(`${id}-head`,
    g(`${id}-hair-back`, back, cut(id)) + g(`${id}-face`, face, cut(id)) +
    g(`${id}-eyes`, eyes) + g(`${id}-brows`, brows) +
    g(`${id}-mouth`, mouth(id, expr), 'transform="translate(0,54)"') +
    g(`${id}-hair`, bangs, cut(id)) + g(`${id}-flower`, flower(62, -64), cut(id)));
}

function nogaFull(id, opts = {}) {
  const legs = `<rect x="160" y="500" width="30" height="92" rx="10" fill="${NG.skin}"/><rect x="210" y="500" width="30" height="92" rx="10" fill="${NG.skin}"/>` +
    `<rect x="156" y="566" width="38" height="26" rx="6" fill="#FFF8EE"/><rect x="206" y="566" width="38" height="26" rx="6" fill="#FFF8EE"/>` +
    [162, 238].map(x => `<ellipse cx="${x}" cy="602" rx="32" ry="16" fill="${NG.shoe}"/>`).join('') +
    `<path d="M150,592 L180,592 M220,592 L250,592" stroke="${NG.shoe}" stroke-width="5" stroke-linecap="round"/>`;
  const skirt = `<path d="M124,440 L276,440 L304,524 Q200,540 96,524Z" fill="${NG.skirt}"/>`;
  const cid = `${id}-sweater`;
  const torsoD = 'M144,282 Q200,268 256,282 Q278,290 280,316 L286,452 L114,452 L120,316 Q122,290 144,282Z';
  const sweater = `<clipPath id="${cid}"><path d="${torsoD}"/></clipPath>` +
    `<g clip-path="url(#${cid})">${NG.stripes.map((c, i) => `<rect x="100" y="${268 + i * 27}" width="200" height="27" fill="${c}"/>`).join('')}</g>` +
    `<rect x="112" y="440" width="176" height="16" rx="8" fill="#B8434A"/>`;
  const brush = `<g transform="translate(306,252) rotate(10)"><rect x="-6" y="0" width="12" height="62" rx="6" fill="${NG.woodD}"/>` +
    `<ellipse cx="0" cy="-18" rx="22" ry="27" fill="${NG.wood}"/><ellipse cx="0" cy="-18" rx="15" ry="20" fill="#F6E7D4"/>` +
    [[-6, -30], [6, -30], [-8, -18], [0, -18], [8, -18], [-6, -6], [6, -6], [0, -28], [0, -8]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="2" fill="${NG.woodD}"/>`).join('') + `</g>`;
  const armR = limb('M258,302 Q300,330 300,296', NG.stripes[4], 28) + brush + `<circle cx="300" cy="296" r="16" fill="${NG.skin}"/>`;
  const armL = limb('M142,302 Q98,300 70,258', NG.stripes[1], 28) +
    `<circle cx="66" cy="250" r="16" fill="${NG.skin}"/>` +
    `<path d="M56,236 l-8,-12 M66,232 l-2,-14 M78,236 l4,-12" stroke="${NG.skin}" stroke-width="7" stroke-linecap="round"/>`;
  const notes = note(352, 182, NG.petalD, 10) + note(40, 168, NG.petal, -12) + note(330, 120, NG.stripes[5], 6);
  return g(id, filters(id) + g('',
    `<ellipse cx="200" cy="620" rx="110" ry="13" fill="${C.shadow}"/>` +
    g(`${id}-legs`, legs, cut(id)) + g(`${id}-body`, skirt + sweater, cut(id)) +
    g(`${id}-arm-l`, armL, cut(id)) +
    g('', nogaHead(id, opts), 'transform="translate(200,190)"') +
    g(`${id}-arm-r`, armR, cut(id)) + g(`${id}-fx`, notes),
  `filter="url(#${id}-paper)"`));
}

// Heads drawn alone still need the filters, so wrap them.
const withFilters = fn => (id, opts) => filters(id) + g('', fn(id, opts), `filter="url(#${id}-paper)"`);

module.exports = {
  number: 3,
  viewBox: '0 0 400 700',
  defs: () => '',
  boy: { key: 'gil', full: gilFull, head: withFilters(gilHead) },
  girl: { key: 'noga', full: nogaFull, head: withFilters(nogaHead) },
};
