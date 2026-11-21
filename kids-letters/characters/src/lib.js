'use strict';
// Shared helpers for the character generators.
// Every character is a function of (idPrefix, options) that returns an SVG <g>.
// Ids are prefixed so several copies can live on one page without clashing.

const OUT = '#1D1A2B'; // outline ink for the bold-outline style

function svgDoc({ viewBox, body, defs = '', label = '', width, height }) {
  const size = (width ? ` width="${width}"` : '') + (height ? ` height="${height}"` : '');
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}"${size} role="img"` +
    (label ? ` aria-label="${label}"` : '') + '>' +
    (defs ? `<defs>${defs}</defs>` : '') + body + '</svg>';
}

function g(id, body, attrs = '') {
  return `<g${id ? ` id="${id}"` : ''}${attrs ? ' ' + attrs : ''}>${body}</g>`;
}

// A thick rounded limb (arm or leg) drawn as a stroked path.
// With `outline`, a wider dark stroke is drawn underneath to fake a contour line.
function limb(d, color, w, outline = null, ow = 6) {
  const base = 'fill="none" stroke-linecap="round" stroke-linejoin="round"';
  return (outline ? `<path d="${d}" ${base} stroke="${outline}" stroke-width="${w + ow * 2}"/>` : '') +
    `<path d="${d}" ${base} stroke="${color}" stroke-width="${w}"/>`;
}

// Expression keys every character supports.
const EXPRESSIONS = [
  { key: 'happy', he: 'שמח' },
  { key: 'surprised', he: 'מופתע' },
  { key: 'laugh', he: 'צוחק' },
];

module.exports = { OUT, svgDoc, g, limb, EXPRESSIONS };
