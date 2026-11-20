// Print an HTML file to PDF with Chromium (Playwright).
// usage: node print_pdf.js <in.html> <out.pdf> [--footer]
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const [inp, out, flag] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + path.resolve(inp), { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  const footer = flag === '--footer';
  await page.pdf({
    path: out,
    width: '170mm',
    height: '240mm',
    printBackground: true,
    preferCSSPageSize: true,
    displayHeaderFooter: footer,
    headerTemplate: '<span></span>',
    footerTemplate: footer
      ? '<div style="width:100%;text-align:center;font-size:9pt;color:#666;font-family:FreeSerif,serif;"><span class="pageNumber"></span></div>'
      : '<span></span>',
    outline: true,
    tagged: true,
  });
  await browser.close();
})();
