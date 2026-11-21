#!/usr/bin/env node
'use strict';
// Builds the character option files:
//   options/option-N/{boy,girl,pair,expressions,sheet}.svg
// Run: node kids-letters/characters/src/build.js
const fs = require('fs');
const path = require('path');
const { svgDoc, g, EXPRESSIONS } = require('./lib');

const OPTIONS = [1, 2, 3, 4]
  .filter(n => fs.existsSync(path.join(__dirname, `option${n}.js`)))
  .map(n => require(`./option${n}.js`));
const OUT_DIR = path.join(__dirname, '..', 'options');

// Head-only frame, in the head's local coordinates (origin = head center).
const HEAD_VB = '-180 -195 360 360';

function vbSize(vb) {
  const [, , w, h] = vb.split(/\s+/).map(Number);
  return { w, h };
}

function fullSvg(opt, who, id, opts) {
  return svgDoc({ viewBox: opt.viewBox, defs: opt.defs(id), body: who.full(id, opts) });
}

function headSvg(opt, who, id, opts) {
  return svgDoc({ viewBox: HEAD_VB, defs: opt.defs(id), body: who.head(id, opts) });
}

function pairSvg(opt, id) {
  const { w, h } = vbSize(opt.viewBox);
  return svgDoc({
    viewBox: `0 0 ${w * 2} ${h}`,
    defs: opt.defs(id),
    body: opt.boy.full(`${id}-b`, { expr: 'happy' }) +
      g('', opt.girl.full(`${id}-g`, { expr: 'happy' }), `transform="translate(${w},0)"`),
  });
}

function expressionsSvg(opt, id) {
  const cell = 240, scale = cell / 360;
  let body = '';
  [opt.boy, opt.girl].forEach((who, row) => {
    EXPRESSIONS.forEach((e, col) => {
      const cx = cell * col + cell / 2, cy = row * cell + 195 * scale;
      body += g('', who.head(`${id}-${who.key}-${e.key}`, { expr: e.key }),
        `transform="translate(${cx},${cy}) scale(${scale})"`);
    });
  });
  return svgDoc({ viewBox: `0 0 ${cell * 3} ${cell * 2}`, defs: opt.defs(id), body });
}

// Pair on top, six expression heads below, on a light stage. Used for PNG previews.
function sheetSvg(opt, id, stage) {
  const { w, h } = vbSize(opt.viewBox);
  const pairW = w * 2, sheetW = 1440, cell = sheetW / 6, scale = cell / 360;
  const pairScale = 760 / h;
  const pairX = (sheetW - pairW * pairScale) / 2;
  let body = `<rect width="${sheetW}" height="${760 + cell + 20}" fill="${stage}"/>` +
    g('', opt.boy.full(`${id}-b`, { expr: 'happy' }) +
      g('', opt.girl.full(`${id}-g`, { expr: 'happy' }), `transform="translate(${w},0)"`),
    `transform="translate(${pairX},0) scale(${pairScale})"`);
  [opt.boy, opt.girl].forEach((who, row) => {
    EXPRESSIONS.forEach((e, col) => {
      const cx = cell * (row * 3 + col) + cell / 2, cy = 760 + 195 * scale;
      body += g('', who.head(`${id}-${who.key}-${e.key}`, { expr: e.key }),
        `transform="translate(${cx},${cy}) scale(${scale})"`);
    });
  });
  return svgDoc({ viewBox: `0 0 ${sheetW} ${760 + cell + 20}`, defs: opt.defs(id), body });
}

const STAGES = { 1: '#FFE9D6', 2: '#DDEBFF', 3: '#E8F1DE', 4: '#FCE4EC' };

function build() {
  for (const opt of OPTIONS) {
    const dir = path.join(OUT_DIR, `option-${opt.number}`);
    fs.mkdirSync(dir, { recursive: true });
    const p = `o${opt.number}`;
    const files = {
      'boy.svg': fullSvg(opt, opt.boy, `${p}-${opt.boy.key}`, { expr: 'happy' }),
      'girl.svg': fullSvg(opt, opt.girl, `${p}-${opt.girl.key}`, { expr: 'happy' }),
      'pair.svg': pairSvg(opt, p),
      'expressions.svg': expressionsSvg(opt, `${p}x`),
      'sheet.svg': sheetSvg(opt, `${p}s`, STAGES[opt.number]),
    };
    for (const [name, content] of Object.entries(files)) {
      fs.writeFileSync(path.join(dir, name), content + '\n');
    }
    console.log(`option-${opt.number}: ${Object.keys(files).join(', ')}`);
  }
}

if (require.main === module) build();
module.exports = { OPTIONS, HEAD_VB, vbSize, fullSvg, headSvg, pairSvg, expressionsSvg, sheetSvg, STAGES };
