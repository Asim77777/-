'use strict';
// Option 2: Itai & Lia. Classic cartoon: thick dark outline, saturated colors, big expressions.
const { OUT, g, limb } = require('./lib');

const S = `stroke="${OUT}" stroke-width="6" stroke-linejoin="round" stroke-linecap="round"`;
const S4 = `stroke="${OUT}" stroke-width="4.5" stroke-linejoin="round" stroke-linecap="round"`;
const C = { mouth: '#6E1F2B', tongue: '#FF7B8C', shadow: 'rgba(29,26,43,.16)' };

function mouth(id, expr) {
  if (expr === 'surprised') {
    return `<ellipse cx="0" cy="8" rx="14" ry="18" fill="${C.mouth}" ${S}/>` +
      `<ellipse cx="0" cy="18" rx="8" ry="5" fill="${C.tongue}"/>`;
  }
  const laugh = expr === 'laugh';
  const d = laugh ? 'M-42,-8 Q0,8 42,-8 Q36,50 0,52 Q-36,50 -42,-8Z' : 'M-31,-4 Q0,8 31,-4 Q27,30 0,32 Q-27,30 -31,-4Z';
  const cid = `${id}-mclip`;
  return `<clipPath id="${cid}"><path d="${d}"/></clipPath>` +
    `<path d="${d}" fill="${C.mouth}"/>` +
    `<g clip-path="url(#${cid})"><rect x="-50" y="-16" width="100" height="${laugh ? 22 : 20}" fill="#fff"/>` +
    `<path d="M-50,${laugh ? 6 : 4} L50,${laugh ? 6 : 4}" ${S4}/>` +
    `<ellipse cx="0" cy="${laugh ? 46 : 30}" rx="${laugh ? 24 : 16}" ry="${laugh ? 15 : 10}" fill="${C.tongue}"/></g>` +
    `<path d="${d}" fill="none" ${S}/>`;
}

// Union outline: dark circles first (bigger), then the fills, so overlaps merge into one silhouette.
function blob(circles, fill, ow = 6) {
  return circles.map(([x, y, r]) => `<circle cx="${x}" cy="${y}" r="${r + ow}" fill="${OUT}"/>`).join('') +
    circles.map(([x, y, r]) => `<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}"/>`).join('');
}

function hand(x, y, r, skin) {
  return `<circle cx="${x}" cy="${y}" r="${r}" fill="${skin}" ${S}/>`;
}

// ---------- Itai ----------
const I = { skin: '#FFD9B8', skinD: '#F2B48A', hair: '#2A2433', cap: '#E63946', capD: '#B81D2C',
  shirtA: '#2B6CB0', shirtB: '#FFFFFF', shorts: '#D4A85F', sock: '#FFFFFF', shoe: '#2FBF71', lens: '#EAF5FF', metal: '#B9C3CE' };

function itaiHead(id, { expr = 'happy', blink = false } = {}) {
  const tufts = [-1, 1].map(s => `<path d="M${s * 88},-58 L${s * 122},-44 L${s * 102},-30 L${s * 124},-14 L${s * 96},-6Z" fill="${I.hair}" ${S}/>`).join('');
  const ears = [-1, 1].map(s => `<ellipse cx="${s * 96}" cy="14" rx="16" ry="22" fill="${I.skin}" ${S}/>` +
    `<path d="M${s * 98},6 q${s * 6},8 0,16" fill="none" ${S4}/>`).join('');
  const face = `<ellipse cx="0" cy="6" rx="96" ry="104" fill="${I.skin}" ${S}/>`;
  const cap = `<path d="M-100,-44 Q-100,-132 0,-136 Q100,-132 100,-44 Q0,-70 -100,-44Z" fill="${I.cap}" ${S}/>` +
    `<path d="M0,-136 Q-10,-96 -4,-58 M-52,-124 Q-60,-90 -54,-52" fill="none" ${S4}/>` +
    `<path d="M62,-64 Q146,-84 166,-54 Q156,-36 76,-44Z" fill="${I.capD}" ${S}/>` +
    `<circle cx="0" cy="-136" r="8" fill="${I.capD}" ${S4}/>`;
  const brows = (() => {
    const y = expr === 'surprised' ? -52 : -38, lift = expr === 'surprised' ? 10 : 6;
    return [-38, 38].map(x => `<path d="M${x - 20},${y + lift / 2} Q${x},${y - lift} ${x + 20},${y + lift / 2}" fill="none" stroke="${I.hair}" stroke-width="9" stroke-linecap="round"/>`).join('');
  })();
  const eyes = [-38, 38].map(x => {
    if (expr === 'laugh' || blink) return `<path d="M${x - 15},10 Q${x},-8 ${x + 15},10" fill="none" stroke="${OUT}" stroke-width="6.5" stroke-linecap="round"/>`;
    if (expr === 'surprised') return `<circle cx="${x}" cy="4" r="6" fill="${OUT}"/>`;
    return `<circle cx="${x + (x < 0 ? 4 : -2)}" cy="6" r="12" fill="${OUT}"/><circle cx="${x + (x < 0 ? 8 : 2)}" cy="1" r="4" fill="#fff"/>`;
  }).join('');
  const glassesBack = [-38, 38].map(x => `<circle cx="${x}" cy="4" r="31" fill="${I.lens}"/>`).join('');
  const glassesFront = [-38, 38].map(x => `<circle cx="${x}" cy="4" r="31" fill="none" stroke="${OUT}" stroke-width="7"/>` +
    `<path d="M${x - 16},-12 q8,-8 18,-8" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round"/>`).join('') +
    `<path d="M-8,0 Q0,-9 8,0" fill="none" stroke="${OUT}" stroke-width="6"/>` +
    `<path d="M-69,0 L-90,-6 M69,0 L90,-6" stroke="${OUT}" stroke-width="6" stroke-linecap="round"/>`;
  const nose = `<ellipse cx="0" cy="42" rx="15" ry="12" fill="${I.skinD}" ${S4}/>`;
  return g(`${id}-head`,
    g(`${id}-hair-back`, tufts) + g(`${id}-ears`, ears) + g(`${id}-face`, face + nose) +
    g(`${id}-eyes`, glassesBack + eyes) + g(`${id}-glasses`, glassesFront) +
    g(`${id}-brows`, brows) +
    g(`${id}-mouth`, mouth(id, expr), 'transform="translate(0,72)"') +
    g(`${id}-hair`, cap));
}

function shoe(x, dir, color) {
  // dir = -1 toe points left, 1 toe points right
  const d = `M${x - dir * 18},600 L${x + dir * 14},600 Q${x + dir * 40},602 ${x + dir * 40},624 L${x - dir * 22},624 Q${x - dir * 24},604 ${x - dir * 18},600Z`;
  return `<path d="${d}" fill="${color}" ${S}/>` +
    `<rect x="${Math.min(x - dir * 26, x + dir * 44)}" y="620" width="70" height="12" rx="6" fill="#fff" ${S4}/>`;
}

function itaiFull(id, opts = {}) {
  const legs = `<rect x="160" y="520" width="26" height="90" fill="${I.skin}" ${S}/>` +
    `<rect x="214" y="520" width="26" height="90" fill="${I.skin}" ${S}/>` +
    `<rect x="156" y="566" width="34" height="38" rx="4" fill="${I.sock}" ${S4}/>` +
    `<rect x="210" y="566" width="34" height="38" rx="4" fill="${I.sock}" ${S4}/>` +
    `<path d="M158,578 L188,578 M212,578 L242,578" stroke="${I.cap}" stroke-width="5"/>` +
    shoe(170, -1, I.shoe) + shoe(230, 1, I.shoe);
  const shorts = `<path d="M126,468 L274,468 L282,540 L212,540 L200,500 L188,540 L118,540Z" fill="${I.shorts}" ${S}/>`;
  const cid = `${id}-shirtclip`;
  const torsoD = 'M140,306 Q200,292 260,306 Q284,314 286,342 L290,480 L110,480 L114,342 Q116,314 140,306Z';
  const shirt = `<clipPath id="${cid}"><path d="${torsoD}"/></clipPath>` +
    `<path d="${torsoD}" fill="${I.shirtB}"/>` +
    `<g clip-path="url(#${cid})">${[316, 350, 384, 418, 452].map(y => `<rect x="100" y="${y}" width="200" height="17" fill="${I.shirtA}"/>`).join('')}</g>` +
    `<path d="${torsoD}" fill="none" ${S}/>` +
    `<path d="M172,304 Q200,326 228,304" fill="${I.skin}" ${S4}/>`;
  const wrench = `<g transform="translate(76,270) rotate(-18)">` +
    `<rect x="-7" y="-78" width="14" height="86" rx="6" fill="${I.metal}" ${S4}/>` +
    `<path d="M9,-100.5 A23,23 0 1,1 -9,-100.5 L-9,-86 L9,-86Z" transform="translate(0,-2)" fill="${I.metal}" ${S4}/>` +
    `</g>`;
  const armL = limb('M136,338 Q98,326 80,284', I.skin, 24, OUT, 6) +
    limb('M138,336 Q126,330 116,326', I.shirtA, 34, OUT, 6) + wrench + hand(78, 274, 18, I.skin) +
    `<path d="M66,270 l22,0 M66,279 l22,0" stroke="${OUT}" stroke-width="3.5" stroke-linecap="round"/>`;
  const armR = limb('M264,338 Q292,388 288,444', I.skin, 24, OUT, 6) +
    limb('M262,336 Q274,346 280,356', I.shirtA, 34, OUT, 6) + hand(288, 452, 18, I.skin);
  return g(id,
    `<ellipse cx="200" cy="636" rx="112" ry="13" fill="${C.shadow}"/>` +
    g(`${id}-legs`, legs + shorts) + g(`${id}-body`, shirt) +
    g(`${id}-arm-r`, armR) +
    g('', itaiHead(id, opts), 'transform="translate(200,200)"') +
    g(`${id}-arm-l`, armL));
}

// ---------- Lia ----------
const L = { skin: '#9A6342', skinD: '#7E4D31', cheek: '#C9705E', hair: '#3B2416', hairL: '#6A4430', scrunchie: '#2EC46B',
  tee: '#2EC46B', star: '#FFD23F', shorts: '#4A6FA5', shoe: '#E63946', aid: '#F3D3A8', lens: '#CFEFFF', rim: '#F2B33D', wood: '#8C5A2B' };

function liaHead(id, { expr = 'happy', blink = false } = {}) {
  const pony = [[62, -126, 38], [98, -140, 32], [42, -158, 28], [80, -168, 24]];
  const mass = [[0, -12, 100], [-70, 30, 44], [70, 30, 44]];
  const fringe = [[-70, -54, 26], [-36, -72, 28], [2, -78, 28], [40, -72, 26], [72, -52, 24]];
  const ears = [-1, 1].map(s => `<ellipse cx="${s * 92}" cy="20" rx="14" ry="18" fill="${L.skin}" ${S}/>`).join('');
  const face = `<ellipse cx="0" cy="10" rx="92" ry="94" fill="${L.skin}" ${S}/>` +
    [-1, 1].map(s => `<ellipse cx="${s * 58}" cy="48" rx="15" ry="9" fill="${L.cheek}" opacity="${expr === 'laugh' ? 0.9 : 0.6}"/>`).join('') +
    `<path d="M-7,40 Q0,47 7,40" fill="none" ${S4}/>`;
  const eyes = [-34, 34].map((x, i) => {
    const side = i === 0 ? -1 : 1;
    if (expr === 'laugh' || blink) return `<path d="M${x - 16},12 Q${x},-6 ${x + 16},12" fill="none" stroke="${OUT}" stroke-width="6.5" stroke-linecap="round"/>`;
    const big = expr === 'surprised';
    const rx = big ? 22 : 19, ry = big ? 28 : 23;
    return `<ellipse cx="${x}" cy="10" rx="${rx}" ry="${ry}" fill="#fff" ${S4}/>` +
      `<circle cx="${x + (big ? 0 : 4)}" cy="${big ? 10 : 13}" r="${big ? 6 : 10}" fill="${OUT}"/>` +
      (big ? '' : `<circle cx="${x + 7}" cy="9" r="3.5" fill="#fff"/>`) +
      `<path d="M${x + side * (rx - 4)},${10 - ry + 8} l${side * 10},-7 M${x + side * (rx - 1)},${10 - ry + 16} l${side * 11},-2" stroke="${OUT}" stroke-width="4" stroke-linecap="round"/>`;
  }).join('');
  const brows = (() => {
    const y = expr === 'surprised' ? -36 : -24, lift = expr === 'surprised' ? 10 : 5;
    return [-34, 34].map(x => `<path d="M${x - 16},${y + lift / 2} Q${x},${y - lift} ${x + 16},${y + lift / 2}" fill="none" stroke="${L.hair}" stroke-width="8" stroke-linecap="round"/>`).join('');
  })();
  const scrunchie = `<ellipse cx="0" cy="0" rx="24" ry="13" transform="translate(44,-104) rotate(-32)" fill="${L.scrunchie}" ${S4}/>`;
  const curls = [[-44, -96], [10, -100], [52, -88]].map(([x, y]) => `<path d="M${x},${y} q8,-6 14,2" fill="none" stroke="${L.hairL}" stroke-width="4" stroke-linecap="round"/>`).join('');
  return g(`${id}-head`,
    g(`${id}-hair-back`, blob(pony.concat(mass), L.hair)) + g(`${id}-ears`, ears) + g(`${id}-face`, face) +
    g(`${id}-eyes`, eyes) + g(`${id}-brows`, brows) +
    g(`${id}-mouth`, mouth(id, expr), 'transform="translate(0,64)"') +
    g(`${id}-hair`, blob(fringe, L.hair, 5) + curls + scrunchie));
}

function liaFull(id, opts = {}) {
  const legs = `<rect x="156" y="522" width="28" height="86" fill="${L.skin}" ${S}/>` +
    `<rect x="216" y="522" width="28" height="86" fill="${L.skin}" ${S}/>` +
    `<g transform="translate(170,556) rotate(-20)"><rect x="-19" y="-7" width="38" height="14" rx="5" fill="${L.aid}" ${S4}/>` +
    `<circle cx="-3" cy="-1" r="1.6" fill="${OUT}"/><circle cx="4" cy="2" r="1.6" fill="${OUT}"/></g>` +
    `<rect x="152" y="584" width="36" height="20" rx="4" fill="#fff" ${S4}/><rect x="212" y="584" width="36" height="20" rx="4" fill="#fff" ${S4}/>` +
    shoe(170, -1, L.shoe) + shoe(230, 1, L.shoe);
  const shorts = `<path d="M120,460 L280,460 L286,528 L212,528 L200,494 L188,528 L114,528Z" fill="${L.shorts}" ${S}/>` +
    `<path d="M118,512 L188,512 M212,512 L284,512" stroke="${OUT}" stroke-width="3.5" stroke-dasharray="6 6"/>`;
  const star = (cx, cy, R, r) => {
    let pts = [];
    for (let i = 0; i < 10; i++) {
      const a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? r : R;
      pts.push(`${(cx + rr * Math.cos(a)).toFixed(1)},${(cy + rr * Math.sin(a)).toFixed(1)}`);
    }
    return `<polygon points="${pts.join(' ')}" fill="${L.star}" ${S4}/>`;
  };
  const tee = `<path d="M144,310 Q200,296 256,310 Q280,318 282,344 L286,470 L114,470 L118,344 Q120,318 144,310Z" fill="${L.tee}" ${S}/>` +
    `<path d="M176,306 Q200,326 224,306" fill="${L.skin}" ${S4}/>` + star(200, 392, 30, 13);
  const armL = limb('M138,336 Q96,318 84,266', L.skin, 24, OUT, 6) +
    limb('M140,334 Q128,328 118,324', L.tee, 34, OUT, 6) +
    `<rect x="64" y="238" width="40" height="36" rx="16" fill="${L.skin}" ${S}/>` +
    `<path d="M74,244 L74,256 M84,242 L84,256 M94,244 L94,256" stroke="${OUT}" stroke-width="3.5" stroke-linecap="round"/>` +
    `<path d="M44,222 l-12,-10 M60,206 l-4,-15 M108,210 l8,-12" stroke="${OUT}" stroke-width="5" stroke-linecap="round"/>`;
  const glass = `<path d="M300,430 L326,386" stroke="${OUT}" stroke-width="22" stroke-linecap="round"/>` +
    `<path d="M300,430 L326,386" stroke="${L.wood}" stroke-width="11" stroke-linecap="round"/>` +
    `<circle cx="340" cy="356" r="32" fill="${L.lens}" opacity=".85"/>` +
    `<circle cx="340" cy="356" r="32" fill="none" stroke="${OUT}" stroke-width="18"/>` +
    `<circle cx="340" cy="356" r="32" fill="none" stroke="${L.rim}" stroke-width="7"/>` +
    `<path d="M322,344 q8,-12 22,-12" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round"/>`;
  const armR = limb('M262,336 Q296,372 300,424', L.skin, 24, OUT, 6) +
    limb('M260,334 Q272,344 278,354', L.tee, 34, OUT, 6) + glass + hand(300, 432, 18, L.skin);
  return g(id,
    `<ellipse cx="200" cy="636" rx="112" ry="13" fill="${C.shadow}"/>` +
    g(`${id}-legs`, legs + shorts) + g(`${id}-body`, tee) +
    g(`${id}-arm-r`, armR) +
    g('', liaHead(id, opts), 'transform="translate(200,202)"') +
    g(`${id}-arm-l`, armL));
}

module.exports = {
  number: 2,
  viewBox: '0 0 400 700',
  defs: () => '',
  boy: { key: 'itai', full: itaiFull, head: itaiHead },
  girl: { key: 'lia', full: liaFull, head: liaHead },
};
