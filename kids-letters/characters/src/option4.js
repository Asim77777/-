'use strict';
// Option 4: Tali & Danny. Chibi proportions (huge head, small body), sparkly anime-style eyes.
// Tali is from Israel and knows the Hebrew letters; her cousin Danny is from America and knows the ABC.
const { g, limb } = require('./lib');

const C = { ink: '#2A2030', mouth: '#8A2F3A', tongue: '#FF8A98', shadow: 'rgba(42,32,48,.14)' };

function eyes(expr, iris, { lashes = false, blink = false } = {}) {
  return [-50, 50].map((x, i) => {
    const side = i === 0 ? -1 : 1;
    if (expr === 'laugh' || blink) {
      return `<path d="M${x - 20},20 Q${x},-2 ${x + 20},20" fill="none" stroke="${C.ink}" stroke-width="7" stroke-linecap="round"/>` +
        (lashes ? `<path d="M${x + side * 19},14 l${side * 10},-6" stroke="${C.ink}" stroke-width="4.5" stroke-linecap="round"/>` : '');
    }
    const big = expr === 'surprised';
    const rx = big ? 27 : 24, ry = big ? 34 : 30, cy = 16;
    let s = `<ellipse cx="${x}" cy="${cy}" rx="${rx}" ry="${ry}" fill="${C.ink}"/>` +
      `<ellipse cx="${x}" cy="${cy + 5}" rx="${rx - 6}" ry="${ry - 9}" fill="${iris}"/>` +
      `<ellipse cx="${x}" cy="${cy + 12}" rx="${rx - 12}" ry="${ry - 20}" fill="#fff" opacity=".18"/>` +
      `<ellipse cx="${x}" cy="${cy + 2}" rx="${big ? 6 : 10}" ry="${big ? 8 : 13}" fill="${C.ink}"/>` +
      `<circle cx="${x + 8}" cy="${cy - 11}" r="${big ? 9 : 8}" fill="#fff"/>` +
      `<circle cx="${x - 9}" cy="${cy + 13}" r="3.8" fill="#fff"/>`;
    if (lashes) {
      const ox = x + side * (rx - 4), oy = cy - ry + 8;
      s += `<path d="M${ox},${oy} l${side * 11},-8 M${ox + side * 3},${oy + 9} l${side * 12},-3" stroke="${C.ink}" stroke-width="4.5" stroke-linecap="round"/>`;
    }
    return s;
  }).join('');
}

function brows(expr, color) {
  const y = expr === 'surprised' ? -38 : -24;
  const lift = expr === 'surprised' ? 9 : 5;
  return [-50, 50].map(x => `<path d="M${x - 15},${y + lift / 2} Q${x},${y - lift} ${x + 15},${y + lift / 2}" fill="none" stroke="${color}" stroke-width="6" stroke-linecap="round"/>`).join('');
}

function mouth(id, expr) {
  if (expr === 'surprised') return `<ellipse cx="0" cy="6" rx="11" ry="14" fill="${C.mouth}"/><ellipse cx="0" cy="14" rx="7" ry="4.5" fill="${C.tongue}"/>`;
  const laugh = expr === 'laugh';
  const d = laugh ? 'M-30,-4 Q0,4 30,-4 Q26,38 0,40 Q-26,38 -30,-4Z' : 'M-18,-2 Q0,3 18,-2 Q15,18 0,19 Q-15,18 -18,-2Z';
  const cid = `${id}-mclip`;
  return `<clipPath id="${cid}"><path d="${d}"/></clipPath><path d="${d}" fill="${C.mouth}"/>` +
    `<g clip-path="url(#${cid})"><rect x="-40" y="-10" width="80" height="${laugh ? 13 : 10}" fill="#fff"/>` +
    `<ellipse cx="0" cy="${laugh ? 34 : 18}" rx="${laugh ? 18 : 10}" ry="${laugh ? 12 : 6}" fill="${C.tongue}"/></g>`;
}

function star(cx, cy, R, r, fill) {
  const pts = [];
  for (let i = 0; i < 10; i++) {
    const a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? r : R;
    pts.push(`${(cx + rr * Math.cos(a)).toFixed(1)},${(cy + rr * Math.sin(a)).toFixed(1)}`);
  }
  return `<polygon points="${pts.join(' ')}" fill="${fill}" stroke="${fill}" stroke-width="3" stroke-linejoin="round"/>`;
}

// ---------- Danny ----------
const D = { skin: '#FBDCC6', skinD: '#EDBB9C', cheek: '#F7A093', hair: '#F4C542', hairD: '#D9A520', cap: '#2F6FE4', capD: '#1F52B5',
  iris: '#3D7BD9', tee: '#E5484D', jeans: '#3A5BA0', shoe: '#FFFFFF', apple: '#E8343B', leaf: '#4CAF50' };

function dannyHead(id, { expr = 'happy', blink = false } = {}) {
  const tufts = `<path d="M-136,-30 L-150,-6 L-128,-4 L-142,22 L-118,12 L-112,-30Z" fill="${D.hair}"/>` +
    `<path d="M136,-30 L150,-6 L128,-4 L142,22 L118,12 L112,-30Z" fill="${D.hair}"/>`;
  const ears = [-1, 1].map(s => `<circle cx="${s * 130}" cy="24" r="22" fill="${D.skin}"/><circle cx="${s * 133}" cy="24" r="10" fill="${D.skinD}"/>`).join('');
  const face = `<ellipse cx="0" cy="8" rx="132" ry="122" fill="${D.skin}"/>` +
    [-1, 1].map(s => `<ellipse cx="${s * 84}" cy="60" rx="20" ry="11" fill="${D.cheek}" opacity="${expr === 'laugh' ? 0.85 : 0.55}"/>`).join('') +
    [[-70, 48], [-60, 56], [-78, 58], [-66, 64], [70, 48], [60, 56], [78, 58], [66, 64]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="2.6" fill="#D9895F" opacity=".7"/>`).join('') +
    `<ellipse cx="0" cy="48" rx="8" ry="6" fill="${D.skinD}"/>`;
  const fringe = `<path d="M-100,-46 L-86,-24 L-70,-44 L-52,-20 L-34,-44 L-16,-22 L4,-44 L22,-20 L40,-44 L58,-22 L74,-44 L90,-24 L104,-46Z" fill="${D.hair}"/>`;
  const cap = `<path d="M-136,-36 Q-134,-150 0,-156 Q134,-150 136,-36 Q0,-72 -136,-36Z" fill="${D.cap}"/>` +
    `<path d="M-40,-150 Q-46,-110 -42,-62 M40,-150 Q46,-110 42,-62" fill="none" stroke="${D.capD}" stroke-width="4" opacity=".6"/>` +
    `<circle cx="0" cy="-104" r="22" fill="#fff"/>` +
    `<path d="M-10,-92 L0,-118 L10,-92 M-6,-101 L6,-101" fill="none" stroke="${D.tee}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>` +
    `<path d="M-124,-44 Q0,-94 124,-44 Q138,-26 114,-20 Q0,-62 -114,-20 Q-138,-26 -124,-44Z" fill="${D.capD}"/>` +
    `<circle cx="0" cy="-156" r="9" fill="${D.capD}"/>`;
  return g(`${id}-head`,
    g(`${id}-hair-back`, tufts) + g(`${id}-ears`, ears) + g(`${id}-face`, face) +
    g(`${id}-eyes`, eyes(expr, D.iris, { blink })) + g(`${id}-brows`, brows(expr, D.hairD)) +
    g(`${id}-mouth`, mouth(id, expr), 'transform="translate(0,74)"') +
    g(`${id}-hair`, fringe + cap));
}

function dannyFull(id, opts = {}) {
  const legs = `<rect x="158" y="510" width="28" height="64" rx="8" fill="${D.skin}"/><rect x="214" y="510" width="28" height="64" rx="8" fill="${D.skin}"/>` +
    [168, 232].map((x, i) => `<path d="M${x - 32},592 Q${x - 32},566 ${x},566 Q${x + 32},566 ${x + 32},592Z" fill="${D.shoe}"/>` +
      `<rect x="${x - 34}" y="588" width="68" height="12" rx="6" fill="#C9D3E3"/>` +
      `<path d="M${x - 14},576 l${i ? 20 : -20},6" stroke="${D.cap}" stroke-width="6" stroke-linecap="round"/>`).join('');
  const jeans = `<path d="M128,460 L272,460 L274,524 L206,524 L200,500 L194,524 L126,524Z" fill="${D.jeans}"/>` +
    `<path d="M200,466 L200,494" stroke="#2C4785" stroke-width="3"/>`;
  const tee = `<path d="M152,342 Q200,330 248,342 Q266,348 268,368 L272,470 L128,470 L132,368 Q134,348 152,342Z" fill="${D.tee}"/>` +
    `<path d="M180,442 L200,396 L220,442 M188,426 L212,426" fill="none" stroke="#fff" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>`;
  const armL = limb('M150,372 Q92,372 62,330', D.skin, 26) + limb('M152,368 Q142,362 132,358', D.tee, 36) +
    `<circle cx="56" cy="318" r="19" fill="${D.skin}"/><ellipse cx="73" cy="326" rx="7" ry="10" transform="rotate(-30 73 326)" fill="${D.skin}"/>` +
    `<path d="M26,296 q-8,16 0,32 M12,286 q-12,26 0,52" fill="none" stroke="${D.cap}" stroke-width="5" stroke-linecap="round" opacity=".55"/>`;
  const apple = `<path d="M300,432 C284,420 264,434 268,458 C272,482 288,488 300,480 C312,488 328,482 332,458 C336,434 316,420 300,432Z" fill="${D.apple}"/>` +
    `<path d="M300,432 Q298,420 304,412" fill="none" stroke="#7A4E32" stroke-width="5" stroke-linecap="round"/>` +
    `<path d="M304,420 Q318,406 330,414 Q318,428 304,420Z" fill="${D.leaf}"/>` +
    `<ellipse cx="284" cy="448" rx="5" ry="9" fill="#fff" opacity=".55" transform="rotate(20 284 448)"/>`;
  const armR = limb('M250,372 Q282,398 280,446', D.skin, 26) + limb('M248,368 Q258,362 268,360', D.tee, 36) +
    apple + `<circle cx="278" cy="458" r="18" fill="${D.skin}"/>`;
  return g(id,
    `<ellipse cx="200" cy="608" rx="104" ry="13" fill="${C.shadow}"/>` +
    g(`${id}-legs`, legs + jeans) + g(`${id}-body`, tee) +
    g(`${id}-arm-r`, armR) +
    g('', dannyHead(id, opts), 'transform="translate(200,222)"') +
    g(`${id}-arm-l`, armL));
}

// ---------- Tali ----------
const T = { skin: '#D7A07A', skinD: '#C08560', cheek: '#EE8E7A', hair: '#3E2416', hairL: '#64402A', iris: '#8A5428',
  dress: '#FF8C42', dressD: '#E8732B', collar: '#FFFFFF', shoe: '#D93A4A', clip: '#FFD23F',
  rind: '#3E9B4F', rindL: '#BFE3A5', flesh: '#FF5A6E', seed: '#2A2030' };

// Hebrew letter aleph, traced from DejaVu Sans Bold (36 units tall, centered on 0,0).
const ALEPH_D = 'M8.8 4 18.4 18H6.5L-4.8 1.8Q-6.5 3.9 -6.5 8.5V18H-17.1V10.9Q-17.1 7.9 -16.6 5.6Q-16 3.2 -15.3 1.7Q-14.6 0.3 -13.3 -0.9Q-12.1 -2.2 -11.2 -2.7Q-10.3 -3.3 -8.9 -4L-18.4 -18H-6.5L4.7 -1.8Q6.5 -3.9 6.5 -8.5V-18H17.1V-10.9Q17.1 -8.7 16.8 -6.9Q16.5 -5.1 16.1 -3.8Q15.7 -2.4 15 -1.3Q14.3 -0.1 13.7 0.6Q13 1.3 12.1 2Q11.1 2.7 10.4 3.1Q9.8 3.5 8.8 4Z';
function aleph(cx, cy, color, k = 1) {
  return `<path d="${ALEPH_D}" transform="translate(${cx},${cy}) scale(${k})" fill="${color}"/>`;
}

function taliHead(id, { expr = 'happy', blink = false } = {}) {
  const back = `<ellipse cx="0" cy="-8" rx="142" ry="134" fill="${T.hair}"/>`;
  const ears = [-1, 1].map(s => `<circle cx="${s * 128}" cy="28" r="20" fill="${T.skin}"/><circle cx="${s * 131}" cy="28" r="9" fill="${T.skinD}"/>`).join('');
  const face = `<ellipse cx="0" cy="12" rx="128" ry="120" fill="${T.skin}"/>` +
    [-1, 1].map(s => `<ellipse cx="${s * 82}" cy="62" rx="20" ry="11" fill="${T.cheek}" opacity="${expr === 'laugh' ? 0.85 : 0.55}"/>`).join('') +
    `<ellipse cx="0" cy="48" rx="7.5" ry="5.5" fill="${T.skinD}"/>`;
  const bangs = `<path d="M-136,14 Q-146,-124 0,-134 Q146,-124 136,14 Q128,-48 74,-68 Q34,-80 4,-58 Q-26,-82 -74,-68 Q-128,-48 -136,14Z" fill="${T.hair}"/>` +
    `<path d="M-90,-96 q36,-26 80,-22 M30,-112 q40,-2 68,22" fill="none" stroke="${T.hairL}" stroke-width="6" stroke-linecap="round"/>`;
  const braid = [[112, 92], [118, 122], [119, 152]].map(([x, y], i) =>
    `<ellipse cx="${x}" cy="${y}" rx="24" ry="20" transform="rotate(${i % 2 ? 18 : -18} ${x} ${y})" fill="${T.hair}"/>` +
    `<path d="M${x - 14},${y - 4} q14,${i % 2 ? -8 : 8} 26,0" fill="none" stroke="${T.hairL}" stroke-width="4" stroke-linecap="round"/>`).join('') +
    `<rect x="104" y="168" width="30" height="14" rx="7" fill="${T.dress}"/>` +
    `<path d="M108,180 Q102,204 112,212 Q120,200 122,212 Q132,204 130,180Z" fill="${T.hair}"/>`;
  return g(`${id}-head`,
    g(`${id}-hair-back`, back) + g(`${id}-ears`, ears) + g(`${id}-face`, face) +
    g(`${id}-eyes`, eyes(expr, T.iris, { lashes: true, blink })) + g(`${id}-brows`, brows(expr, T.hair)) +
    g(`${id}-mouth`, mouth(id, expr), 'transform="translate(0,76)"') +
    g(`${id}-hair`, bangs + star(-84, -78, 16, 7, T.clip)) + g(`${id}-braid`, braid));
}

function taliFull(id, opts = {}) {
  const legs = `<rect x="166" y="516" width="26" height="60" rx="8" fill="${T.skin}"/><rect x="208" y="516" width="26" height="60" rx="8" fill="${T.skin}"/>` +
    [176, 224].map(x => `<path d="M${x - 28},592 Q${x - 28},568 ${x},568 Q${x + 28},568 ${x + 28},592Z" fill="${T.shoe}"/>` +
      `<path d="M${x - 14},572 L${x + 14},572" stroke="${T.shoe}" stroke-width="6"/>` +
      `<rect x="${x - 30}" y="588" width="60" height="10" rx="5" fill="#8A2430"/>`).join('');
  const dress = `<path d="M156,340 Q200,330 244,340 Q262,346 264,366 L292,516 Q200,534 108,516 L136,366 Q138,346 156,340Z" fill="${T.dress}"/>` +
    `<path d="M108,512 Q200,530 292,512 L294,524 Q200,542 106,524Z" fill="${T.dressD}"/>` +
    `<path d="M200,346 Q178,372 158,348 Q178,336 200,346Z M200,346 Q222,372 242,348 Q222,336 200,346Z" fill="${T.collar}"/>` +
    `<circle cx="200" cy="436" r="27" fill="#fff"/>` + aleph(200, 436, T.hair);
  const armL = limb('M150,372 Q92,372 62,330', T.skin, 26) + `<circle cx="146" cy="364" r="22" fill="${T.dress}"/>` +
    `<circle cx="56" cy="318" r="19" fill="${T.skin}"/><ellipse cx="73" cy="326" rx="7" ry="10" transform="rotate(-30 73 326)" fill="${T.skin}"/>` +
    `<path d="M26,296 q-8,16 0,32 M12,286 q-12,26 0,52" fill="none" stroke="${T.dressD}" stroke-width="5" stroke-linecap="round" opacity=".55"/>`;
  const melon = `<g transform="translate(298,472) rotate(-24)">` +
    `<path d="M-44,0 A44,44 0 0,0 44,0Z" fill="${T.rind}"/><path d="M-38,0 A38,38 0 0,0 38,0Z" fill="${T.rindL}"/>` +
    `<path d="M-33,0 A33,33 0 0,0 33,0Z" fill="${T.flesh}"/>` +
    [[-16, 9], [0, 14], [16, 9], [-6, 22], [8, 22]].map(([x, y]) => `<ellipse cx="${x}" cy="${y}" rx="2.6" ry="4" fill="${T.seed}"/>`).join('') + `</g>`;
  const armR = limb('M250,372 Q284,400 282,446', T.skin, 26) + `<circle cx="254" cy="364" r="22" fill="${T.dress}"/>` +
    melon + `<circle cx="280" cy="456" r="18" fill="${T.skin}"/>`;
  return g(id,
    `<ellipse cx="200" cy="608" rx="104" ry="13" fill="${C.shadow}"/>` +
    g(`${id}-legs`, legs) + g(`${id}-body`, dress) +
    g(`${id}-arm-r`, armR) +
    g('', taliHead(id, opts), 'transform="translate(200,222)"') +
    g(`${id}-arm-l`, armL));
}

module.exports = {
  number: 4,
  viewBox: '0 0 400 700',
  defs: () => '',
  boy: { key: 'danny', full: dannyFull, head: dannyHead },
  girl: { key: 'tali', full: taliFull, head: taliHead },
};
