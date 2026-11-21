#!/usr/bin/env node
'use strict';
// Render SVG files to PNG with the preinstalled Chromium (Playwright).
// Usage: node render_svg.js <in.svg> <out.png> [widthPx=800] [scale=1] [background=transparent]
// Several pairs can be passed: node render_svg.js a.svg a.png b.svg b.png --width 800
// Later this same tool renders animation frames for the videos.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

function parseArgs(argv) {
  const opts = { width: 800, scale: 1, bg: 'transparent', pairs: [] };
  const rest = [];
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--width') opts.width = Number(argv[++i]);
    else if (argv[i] === '--scale') opts.scale = Number(argv[++i]);
    else if (argv[i] === '--bg') opts.bg = argv[++i];
    else rest.push(argv[i]);
  }
  for (let i = 0; i + 1 < rest.length; i += 2) opts.pairs.push([rest[i], rest[i + 1]]);
  return opts;
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (!opts.pairs.length) {
    console.error('Usage: node render_svg.js <in.svg> <out.png> [...more pairs] [--width 800] [--scale 1] [--bg #fff]');
    process.exit(1);
  }
  const browser = await chromium.launch();
  const page = await browser.newPage({ deviceScaleFactor: opts.scale });
  page.on('console', m => { if (m.type() === 'error') console.error('console:', m.text()); });
  for (const [input, output] of opts.pairs) {
    const svg = fs.readFileSync(input, 'utf8');
    const vb = /viewBox="([^"]+)"/.exec(svg);
    if (!vb) throw new Error(`${input}: missing viewBox`);
    const [, , w, h] = vb[1].split(/[\s,]+/).map(Number);
    const width = opts.width;
    const height = Math.round(width * h / w);
    await page.setViewportSize({ width, height });
    await page.setContent(`<!doctype html><html><body style="margin:0;background:${opts.bg}">` +
      svg.replace('<svg ', `<svg width="${width}" height="${height}" `) + '</body></html>');
    fs.mkdirSync(path.dirname(output), { recursive: true });
    await page.screenshot({ path: output, omitBackground: opts.bg === 'transparent' });
    console.log(`${input} -> ${output} (${width}x${height} @${opts.scale}x)`);
  }
  await browser.close();
}

main().catch(err => { console.error(err); process.exit(1); });
