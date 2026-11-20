// Word edition of the book (docx-js). Input: build/.work/book.json from book.py; output: a .docx path.
// Right-to-left throughout, real footnotes for the sources, David (ships with Windows; has full niqqud).
// usage: node book/build/build_docx.mjs <book.json> <out.docx>
import fs from "node:fs";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const {
  Document, Packer, Paragraph, TextRun, FootnoteReferenceRun, AlignmentType, HeadingLevel, PageBreak,
  Header, Footer, PageNumber, NumberFormat, ImageRun, SectionType, BorderStyle,
} = require("docx");

const [, , inPath, outPath] = process.argv;
const book = JSON.parse(fs.readFileSync(inPath, "utf8"));

const FONT = "David";
const F = { ascii: FONT, hAnsi: FONT, cs: FONT, eastAsia: FONT };
const RED = "8E1B1B";
const GRAY = "6B6B6B";
const BODY = 26;           // half-points: 13pt, room for niqqud
const LINE = 360;          // 1.5 lines
const PAGE = { width: 9638, height: 13606 };  // 17 × 24 cm
const MARGIN = { top: 1361, bottom: 1247, left: 1077, right: 1077, header: 680, footer: 624 };

const run = (text, o = {}) => new TextRun({
  text, font: F, rightToLeft: true,
  size: o.size ?? BODY, sizeComplexScript: o.size ?? BODY,
  bold: o.bold, boldComplexScript: o.bold, color: o.color,
});

// ---- footnotes -------------------------------------------------------------------------------
const footnotes = {};
let fnId = 0;
function footnote(label) {
  fnId += 1;
  footnotes[fnId] = {
    children: [new Paragraph({ bidirectional: true, alignment: AlignmentType.BOTH, children: [run(label, { size: 20 })] })],
  };
  return new FootnoteReferenceRun(fnId);
}

// ---- inline segments -> runs ------------------------------------------------------------------
function segRuns(seg, o = {}) {
  switch (seg.t) {
    case "text": return [run(seg.s, o)];
    case "quote": return [run(seg.marks ? `"${seg.s}"` : seg.s, o)];
    case "fn": return seg.skip ? [] : [footnote(seg.show)];
    case "unclear": return [run("[?]", { size: 17, color: GRAY })];
    case "note": return [run(`[${seg.s}:] `, { size: (o.size ?? BODY) - 4 })];
    case "add": return [run(`[${seg.s}]`, o)];
    default: return [];
  }
}

const bodyPara = (children, o = {}) => new Paragraph({
  bidirectional: true, alignment: AlignmentType.BOTH, children,
  indent: o.noIndent ? undefined : { firstLine: 397 },
  spacing: { line: LINE, after: 0 },
});

// a paragraph; a long quotation becomes its own indented block, as in the printed edition
function paragraphs(segs, first) {
  const out = [];
  let cur = [];
  let afterQuote = false;
  const flush = () => {
    if (cur.length) out.push(bodyPara(cur, { noIndent: afterQuote || (first && out.length === 0) }));
    cur = [];
  };
  segs.forEach((seg, i) => {
    if (seg.t === "quote" && seg.long) {
      flush();
      const q = segRuns(seg, { size: BODY - 3 });
      // the footnote right after the quote stays with it
      if (segs[i + 1] && segs[i + 1].t === "fn") { q.push(...segRuns(segs[i + 1])); segs[i + 1] = { t: "skipme" }; }
      out.push(new Paragraph({
        bidirectional: true, alignment: AlignmentType.BOTH, children: q,
        indent: { left: 567, right: 567 }, spacing: { line: 320, before: 120, after: 120 },
      }));
      afterQuote = true;
      return;
    }
    if (seg.t === "text" && afterQuote && !cur.length) {
      seg = { ...seg, s: seg.s.replace(/^\s*[.,;:]+\s*/, "") };
      if (!seg.s.trim()) return;
    }
    cur.push(...segRuns(seg));
  });
  flush();
  if (first && out.length) openingWords(out, segs);
  return out;
}

// the first words of a drasha, large and red (siddur style)
function openingWords(out, segs) {
  const firstText = segs.find((s) => s.t === "text");
  if (!firstText) return;
  const m = firstText.s.match(/^\s*(\S+\s+\S+)(\s[\s\S]*)?$/);
  if (!m) return;
  const rest = segs.slice(segs.indexOf(firstText) + 1);
  const children = [run(m[1], { size: 34, bold: true, color: RED }), run(m[2] || "")];
  let hitQuote = false;
  for (const s of rest) {
    if (s.t === "quote" && s.long) { hitQuote = true; break; }
    children.push(...segRuns(s));
  }
  if (hitQuote) return;  // keep the generic layout in this rare case
  out[0] = bodyPara(children, { noIndent: true });
}

const center = (children, o = {}) => new Paragraph({
  bidirectional: true, alignment: AlignmentType.CENTER, children,
  spacing: { before: o.before ?? 0, after: o.after ?? 0, line: o.line ?? 300 }, heading: o.heading,
  keepNext: true, pageBreakBefore: o.pageBreak,
});
const rule = (o = {}) => new Paragraph({
  bidirectional: true, alignment: AlignmentType.CENTER, spacing: { before: o.before ?? 120, after: o.after ?? 240 },
  indent: { left: 3600, right: 3600 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: RED, space: 1 } }, children: [],
});

const headerOf = (text) => new Header({
  children: [new Paragraph({
    bidirectional: true, alignment: AlignmentType.CENTER,
    border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "999999", space: 4 } },
    children: [run(text, { size: 18, color: "333333" })],
  })],
});
const footerNum = () => new Footer({
  children: [new Paragraph({
    bidirectional: true, alignment: AlignmentType.CENTER,
    children: [new TextRun({ children: [PageNumber.CURRENT], font: F, size: 20, sizeComplexScript: 20, rightToLeft: true })],
  })],
});
const emptyHeader = () => new Header({ children: [new Paragraph({ children: [] })] });
const emptyFooter = () => new Footer({ children: [new Paragraph({ children: [] })] });

const pageProps = (type) => ({
  type,
  page: { size: PAGE, margin: MARGIN, pageNumbers: { formatType: NumberFormat.HEBREW_1 } },
  titlePage: true,
});

const L = book.labels;
const sections = [];

// ---- title page ------------------------------------------------------------------------------
sections.push({
  properties: { page: { size: PAGE, margin: MARGIN, pageNumbers: { start: 1, formatType: NumberFormat.HEBREW_1 } } },
  headers: { default: emptyHeader() }, footers: { default: emptyFooter() },
  children: [
    center([run(book.title_main, { size: 96, bold: true })], { before: 2600, after: 200, line: 240 }),
    center([run(book.title_by, { size: 44, bold: true })], { after: 120 }),
    rule({ before: 240, after: 360 }),
    center([run(book.subtitle, { size: 30 })]),
    center([run(book.year, { size: 26 })], { before: 5200 }),
  ],
});

// ---- contents and introduction ---------------------------------------------------------------
const front = [];
front.push(center([run(L["label-toc"], { size: 40, bold: true })], { after: 120, heading: HeadingLevel.TITLE }));
front.push(rule());
for (const s of book.shaarim) {
  front.push(new Paragraph({
    bidirectional: true, spacing: { before: 200, after: 60 }, keepNext: true,
    children: [run(`${L["label-shaar"]} ${s.ordinal}: `, { color: RED, size: 24 }), run(s.name, { bold: true, size: 26 })],
  }));
  for (const d of s.drashot) {
    front.push(new Paragraph({
      bidirectional: true, spacing: { after: 40 }, indent: { right: 400 },
      children: [run(`${d.num_heb}  `, { size: 24 }), run(d.title, { size: 24 })],
    }));
  }
}
let introFirst = true;
for (const b of book.intro) {
  if (b.type === "h") {
    const text = b.segs.map((s) => s.s || "").join("");
    if (introFirst) {
      front.push(center([run(text, { size: 40, bold: true })], { pageBreak: true, after: 120, heading: HeadingLevel.HEADING_1 }));
      front.push(rule());
      introFirst = false;
    } else {
      front.push(center([run(text, { size: 28, bold: true })], { before: 280, after: 100, heading: HeadingLevel.HEADING_3 }));
    }
  } else {
    front.push(bodyPara(b.segs.flatMap((s) => segRuns(s)), { noIndent: true }));
  }
}
sections.push({
  properties: { type: SectionType.NEXT_PAGE, page: { size: PAGE, margin: MARGIN, pageNumbers: { formatType: NumberFormat.HEBREW_1 } } },
  headers: { default: emptyHeader() }, footers: { default: footerNum() },
  children: front,
});

// ---- the shaarim and the drashot -------------------------------------------------------------
for (const s of book.shaarim) {
  sections.push({
    properties: { type: SectionType.ODD_PAGE, page: { size: PAGE, margin: MARGIN, pageNumbers: { formatType: NumberFormat.HEBREW_1 } } },
    headers: { default: emptyHeader() }, footers: { default: emptyFooter() },
    children: [
      center([run(`${L["label-shaar"]} ${s.ordinal}`, { size: 32, color: RED })], { before: 3600, after: 300 }),
      center([run(s.name, { size: 56, bold: true })], { heading: HeadingLevel.HEADING_1, line: 400 }),
      rule({ before: 360 }),
    ],
  });
  for (const d of s.drashot) {
    const ch = [];
    ch.push(center([run(`${L["label-drasha"]} ${d.num_heb}`, { size: 24, color: RED })], { before: 900, after: 160 }));
    ch.push(center([run(d.title, { size: 44, bold: true })], { heading: HeadingLevel.HEADING_2, after: 160, line: 400 }));
    ch.push(center([run(`${L["label-said"]} ${d.date}`, { size: 22 })]));
    ch.push(rule({ before: 200, after: 480 }));
    let first = true;
    for (const b of d.blocks) {
      if (b.type === "h") {
        ch.push(center(b.segs.flatMap((sg) => segRuns(sg, { size: 28, bold: true })),
          { before: 360, after: 120, heading: HeadingLevel.HEADING_3 }));
        continue;
      }
      ch.push(...paragraphs(b.segs.map((x) => ({ ...x })), first));
      first = false;
    }
    // closing: the recording
    ch.push(rule({ before: 480, after: 160 }));
    ch.push(new Paragraph({
      alignment: AlignmentType.CENTER, keepNext: true,
      children: [new ImageRun({ type: "png", data: fs.readFileSync(d.qr), transformation: { width: 64, height: 64 } })],
    }));
    ch.push(center([run(L["label-watch"], { size: 18 })], { after: 0 }));
    sections.push({
      properties: pageProps(SectionType.NEXT_PAGE),
      headers: { default: headerOf(d.title_plain), even: headerOf(book.title), first: emptyHeader() },
      footers: { default: footerNum(), even: footerNum(), first: footerNum() },
      children: ch,
    });
  }
}

const doc = new Document({
  creator: book.title, title: book.title, description: book.subtitle,
  evenAndOddHeaderAndFooters: true,
  styles: {
    default: {
      document: { run: { font: F, size: BODY, rightToLeft: true } },
      title: { run: { font: F, size: 40, bold: true }, paragraph: { spacing: { before: 0, after: 120 }, keepNext: true } },
      heading1: { run: { font: F, size: 40, bold: true, color: "000000" }, paragraph: { spacing: { before: 0, after: 120 }, keepNext: true } },
      heading2: { run: { font: F, size: 44, bold: true, color: "000000" }, paragraph: { spacing: { before: 0, after: 160 }, keepNext: true } },
      heading3: { run: { font: F, size: 28, bold: true, color: "000000" }, paragraph: { spacing: { before: 360, after: 120 }, keepNext: true } },
    },
  },
  footnotes,
  sections,
});

fs.writeFileSync(outPath, await Packer.toBuffer(doc));
console.log(`${outPath}: ${fnId} footnotes, ${sections.length} sections`);
