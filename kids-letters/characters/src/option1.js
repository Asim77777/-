'use strict';
// Option 1: Noam & Tamar. Soft, round shapes, no outlines, bright colors.
const { g, limb } = require('./lib');

const C = {
  ink: '#3A2420', mouth: '#8A2F3A', tongue: '#FF8A98', shadow: 'rgba(40,30,60,.13)',
};

function eyes(expr, { lashes = false, blink = false } = {}) {
  const xs = [-38, 38];
  if (expr === 'laugh' || blink) {
    return xs.map(x => `<path d="M${x - 14},12 Q${x},-5 ${x + 14},12" fill="none" stroke="${C.ink}" stroke-width="6.5" stroke-linecap="round"/>`).join('');
  }
  const big = expr === 'surprised';
  const rx = big ? 13.5 : 11.5, ry = big ? 19 : 15.5;
  return xs.map((x, i) => {
    const side = i === 0 ? -1 : 1;
    let s = `<ellipse cx="${x}" cy="8" rx="${rx}" ry="${ry}" fill="${C.ink}"/>` +
      `<circle cx="${x + 4}" cy="${8 - ry * 0.4}" r="${big ? 5.5 : 4.8}" fill="#fff"/>` +
      `<circle cx="${x - 4}" cy="${8 + ry * 0.38}" r="2.2" fill="#fff" opacity=".85"/>`;
    if (lashes) {
      const ox = x + side * (rx - 3), oy = 8 - ry + 6;
      s += `<path d="M${ox},${oy} l${side * 9},-6 M${ox + side * 2},${oy + 8} l${side * 10},-2" stroke="${C.ink}" stroke-width="4" stroke-linecap="round" fill="none"/>`;
    }
    return s;
  }).join('');
}

function brows(expr, color) {
  const y = expr === 'surprised' ? -32 : expr === 'laugh' ? -24 : -21;
  const lift = expr === 'surprised' ? 10 : 6;
  return [-38, 38].map(x => `<path d="M${x - 13},${y + lift / 2} Q${x},${y - lift} ${x + 13},${y + lift / 2}" fill="none" stroke="${color}" stroke-width="6" stroke-linecap="round"/>`).join('');
}

function mouth(id, expr, { gap = false } = {}) {
  if (expr === 'surprised') {
    return `<ellipse cx="0" cy="6" rx="12" ry="15" fill="${C.mouth}"/><ellipse cx="0" cy="15" rx="8" ry="5" fill="${C.tongue}"/>`;
  }
  const laugh = expr === 'laugh';
  const outline = laugh ? 'M-36,-6 Q0,6 36,-6 Q32,44 0,46 Q-32,44 -36,-6Z' : 'M-27,-3 Q0,5 27,-3 Q24,27 0,29 Q-24,27 -27,-3Z';
  const cid = `${id}-mclip`;
  return `<clipPath id="${cid}"><path d="${outline}"/></clipPath>` +
    `<path d="${outline}" fill="${C.mouth}"/>` +
    `<g clip-path="url(#${cid})">` +
    `<rect x="-40" y="-14" width="80" height="${laugh ? 22 : 20}" rx="4" fill="#fff"/>` +
    (gap ? `<rect x="-9" y="-14" width="8" height="${laugh ? 22 : 20}" rx="2" fill="${C.mouth}"/>` : '') +
    `<ellipse cx="0" cy="${laugh ? 40 : 27}" rx="${laugh ? 22 : 15}" ry="${laugh ? 14 : 9}" fill="${C.tongue}"/>` +
    '</g>';
}

// ---------- Noam ----------
const N = { skin: '#F6C7A1', skinD: '#E7A983', cheek: '#FF9F8E', hair: '#6E3F25', hairL: '#93603F',
  hoodie: '#FF8A3D', hoodieD: '#E86F25', pants: '#3F6FD6', shoe: '#E84B4B' };

function noamHead(id, { expr = 'happy', blink = false } = {}) {
  const curls = [[-94, -36, 28], [-80, -72, 32], [-48, -100, 34], [-8, -112, 36], [34, -106, 35], [70, -84, 33],
    [94, -48, 28], [-56, -62, 30], [-16, -76, 32], [24, -74, 32], [60, -58, 28], [-96, -6, 17], [97, -12, 17]];
  const ears = [-1, 1].map(s => `<circle cx="${s * 103}" cy="18" r="20" fill="${N.skin}"/><circle cx="${s * 106}" cy="18" r="9" fill="${N.skinD}"/>`).join('');
  const face = `<ellipse cx="0" cy="6" rx="106" ry="100" fill="${N.skin}"/>` +
    [-1, 1].map(s => `<ellipse cx="${s * 66}" cy="46" rx="17" ry="10" fill="${N.cheek}" opacity="${expr === 'laugh' ? 0.85 : 0.55}"/>`).join('') +
    `<ellipse cx="0" cy="34" rx="10" ry="7" fill="${N.skinD}"/>`;
  const hair = curls.map(([x, y, r]) => `<circle cx="${x}" cy="${y}" r="${r}" fill="${N.hair}"/>`).join('') +
    [[-48, -100, 34], [34, -106, 35], [-80, -72, 32], [70, -84, 33]].map(([x, y, r]) =>
      `<path d="M${x - r * 0.55},${y - r * 0.1} q${r * 0.3},-${r * 0.45} ${r * 0.75},-${r * 0.3}" fill="none" stroke="${N.hairL}" stroke-width="5" stroke-linecap="round"/>`).join('') +
    `<circle cx="-4" cy="-42" r="14" fill="${N.hair}"/><circle cx="12" cy="-36" r="9" fill="${N.hair}"/>`;
  return g(`${id}-head`,
    g(`${id}-ears`, ears) + g(`${id}-face`, face) +
    g(`${id}-eyes`, eyes(expr, { blink })) + g(`${id}-brows`, brows(expr, N.hair)) +
    g(`${id}-mouth`, mouth(id, expr, { gap: true }), 'transform="translate(0,58)"') +
    g(`${id}-hair`, hair));
}

function noamFull(id, opts = {}) {
  const legs = `<rect x="143" y="488" width="50" height="130" rx="18" fill="${N.pants}"/>` +
    `<rect x="207" y="488" width="50" height="130" rx="18" fill="${N.pants}"/>`;
  const shoes = [163, 237].map(x => `<ellipse cx="${x}" cy="624" rx="39" ry="22" fill="${N.shoe}"/>` +
    `<rect x="${x - 41}" y="628" width="82" height="15" rx="7.5" fill="#fff"/>` +
    `<circle cx="${x - 6}" cy="614" r="4" fill="#fff"/><circle cx="${x + 8}" cy="614" r="4" fill="#fff"/>`).join('');
  const torso = `<path d="M138,316 Q200,298 262,316 Q284,324 286,350 L292,490 Q292,512 268,512 L132,512 Q108,512 108,490 L114,350 Q116,324 138,316Z" fill="${N.hoodie}"/>` +
    `<rect x="108" y="490" width="184" height="22" rx="11" fill="${N.hoodieD}"/>` +
    `<path d="M146,430 L254,430 Q260,430 260,436 L260,474 Q260,480 254,480 L146,480 Q140,480 140,474 L140,436 Q140,430 146,430Z" fill="${N.hoodieD}" opacity=".75"/>` +
    `<path d="M150,312 Q200,352 250,312 Q236,294 200,294 Q164,294 150,312Z" fill="${N.hoodieD}"/>` +
    `<path d="M187,330 L183,384 M213,330 L217,384" stroke="#fff" stroke-width="4.5" stroke-linecap="round"/>` +
    `<circle cx="183" cy="388" r="5" fill="#fff"/><circle cx="217" cy="388" r="5" fill="#fff"/>`;
  const armL = limb('M134,346 Q78,334 52,284', N.hoodie, 36) +
    `<circle cx="48" cy="266" r="23" fill="${N.skin}"/><ellipse cx="68" cy="276" rx="8" ry="12" transform="rotate(-30 68 276)" fill="${N.skin}"/>` +
    `<path d="M14,240 q-9,18 0,36 M0,228 q-13,30 0,58" fill="none" stroke="${N.hoodie}" stroke-width="5" stroke-linecap="round" opacity=".6"/>`;
  const armR = limb('M266,346 Q300,396 292,452', N.hoodie, 36) +
    `<circle cx="291" cy="466" r="21" fill="${N.skin}"/>`;
  return g(id,
    `<ellipse cx="200" cy="652" rx="112" ry="14" fill="${C.shadow}"/>` +
    g(`${id}-legs`, legs + shoes) + g(`${id}-body`, torso) +
    g(`${id}-arm-l`, armL) + g(`${id}-arm-r`, armR) +
    g('', noamHead(id, opts), 'transform="translate(200,205)"'));
}

// ---------- Tamar ----------
const T = { skin: '#C98B62', skinD: '#B07451', cheek: '#E8846F', hair: '#2B1B14', hairL: '#4A3227', tie: '#FFC93C',
  shirt: '#FF6F91', shirtD: '#E85A7C', overall: '#FFC93C', overallD: '#E8AC12', shoe: '#8E5BD9' };

function tamarHead(id, { expr = 'happy', blink = false } = {}) {
  const tails = [-1, 1].map(s =>
    `<circle cx="${s * 114}" cy="-74" r="47" fill="${T.hair}"/>` +
    `<circle cx="${s * 140}" cy="-46" r="30" fill="${T.hair}"/>` +
    `<path d="M${s * 98},-96 q${s * 22},-8 ${s * 36},8" fill="none" stroke="${T.hairL}" stroke-width="5" stroke-linecap="round"/>` +
    `<rect x="-14" y="-8" width="28" height="16" rx="8" fill="${T.tie}" transform="translate(${s * 82},-50) rotate(${s * 38})"/>`).join('');
  const back = `<ellipse cx="0" cy="-4" rx="108" ry="104" fill="${T.hair}"/>`;
  const ears = [-1, 1].map(s => `<circle cx="${s * 99}" cy="22" r="17" fill="${T.skin}"/><circle cx="${s * 101}" cy="22" r="7" fill="${T.skinD}"/>`).join('');
  const face = `<ellipse cx="0" cy="10" rx="98" ry="94" fill="${T.skin}"/>` +
    [-1, 1].map(s => `<ellipse cx="${s * 62}" cy="48" rx="16" ry="9" fill="${T.cheek}" opacity="${expr === 'laugh' ? 0.9 : 0.6}"/>`).join('') +
    `<ellipse cx="0" cy="34" rx="8" ry="6" fill="${T.skinD}"/>`;
  const bangs = `<path d="M-102,4 C-106,-78 -46,-110 6,-106 C62,-104 106,-68 102,4 C96,-34 76,-54 46,-58 C20,-60 -12,-50 -34,-36 C-58,-20 -84,-14 -102,4Z" fill="${T.hair}"/>` +
    `<path d="M-40,-82 q30,-16 64,-8" fill="none" stroke="${T.hairL}" stroke-width="5" stroke-linecap="round"/>`;
  return g(`${id}-head`,
    g(`${id}-hair-back`, tails + back) + g(`${id}-ears`, ears) + g(`${id}-face`, face) +
    g(`${id}-eyes`, eyes(expr, { lashes: true, blink })) + g(`${id}-brows`, brows(expr, T.hair)) +
    g(`${id}-mouth`, mouth(id, expr), 'transform="translate(0,60)"') +
    g(`${id}-hair`, bangs));
}

function tamarFull(id, opts = {}) {
  const legs = `<rect x="145" y="496" width="48" height="118" rx="16" fill="${T.overall}"/>` +
    `<rect x="207" y="496" width="48" height="118" rx="16" fill="${T.overall}"/>` +
    `<rect x="141" y="586" width="56" height="18" rx="8" fill="${T.overallD}"/>` +
    `<rect x="203" y="586" width="56" height="18" rx="8" fill="${T.overallD}"/>` +
    `<rect x="150" y="598" width="38" height="20" fill="${T.skin}"/><rect x="212" y="598" width="38" height="20" fill="${T.skin}"/>`;
  const shoes = [167, 233].map(x => `<ellipse cx="${x}" cy="628" rx="38" ry="21" fill="${T.shoe}"/>` +
    `<rect x="${x - 40}" y="632" width="80" height="14" rx="7" fill="#fff"/>` +
    `<path d="M${x - 12},616 l10,-6 M${x + 2},618 l10,-6" stroke="#fff" stroke-width="4" stroke-linecap="round"/>`).join('');
  const torso = `<path d="M146,318 Q200,302 254,318 Q276,326 278,350 L284,476 L116,476 L122,350 Q124,326 146,318Z" fill="${T.shirt}"/>` +
    [338, 372, 406, 440].map(y => `<rect x="118" y="${y}" width="164" height="9" fill="#fff" opacity=".35"/>`).join('') +
    `<path d="M122,462 L278,462 L284,506 Q285,516 274,516 L126,516 Q115,516 116,506Z" fill="${T.overall}"/>` +
    `<path d="M156,380 L244,380 L248,470 L152,470Z" fill="${T.overall}"/>` +
    `<path d="M150,322 L162,384 M250,322 L238,384" stroke="${T.overall}" stroke-width="15" stroke-linecap="round"/>` +
    `<circle cx="164" cy="388" r="6.5" fill="${T.overallD}"/><circle cx="236" cy="388" r="6.5" fill="${T.overallD}"/>` +
    `<path d="M200,446 C188,436 176,424 184,414 C190,407 198,410 200,416 C202,410 210,407 216,414 C224,424 212,436 200,446Z" fill="${T.shirt}"/>`;
  const armL = limb('M140,340 Q88,322 66,268', T.shirt, 32) +
    `<rect x="56" y="210" width="12" height="32" rx="6" fill="${T.skin}"/>` +
    `<circle cx="62" cy="254" r="20" fill="${T.skin}"/>` +
    `<path d="M36,206 l-10,-10 M60,190 l-1,-15 M84,198 l8,-11" stroke="${T.overallD}" stroke-width="5" stroke-linecap="round"/>`;
  const armR = limb('M260,340 Q300,376 274,418', T.shirt, 32) +
    `<circle cx="268" cy="424" r="19" fill="${T.skin}"/>`;
  return g(id,
    `<ellipse cx="200" cy="654" rx="110" ry="14" fill="${C.shadow}"/>` +
    g(`${id}-legs`, legs + shoes) + g(`${id}-body`, torso) +
    g(`${id}-arm-r`, armR) +
    g('', tamarHead(id, opts), 'transform="translate(200,205)"') +
    g(`${id}-arm-l`, armL));
}

module.exports = {
  number: 1,
  viewBox: '0 0 400 700',
  defs: () => '',
  boy: { key: 'noam', full: noamFull, head: noamHead },
  girl: { key: 'tamar', full: tamarFull, head: tamarHead },
};
