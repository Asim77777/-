#!/usr/bin/env node
'use strict';
// Builds characters/gallery.html: the page for choosing one of the four pairs.
// Run: node kids-letters/characters/src/gallery.js
const fs = require('fs');
const path = require('path');
const { OPTIONS, HEAD_VB, vbSize } = require('./build');
const { svgDoc, g, EXPRESSIONS } = require('./lib');

const INFO = {
  1: {
    names: 'נועם ותמר', en: 'Noam & Tamar',
    style: 'עגול ורך, בלי קווי מתאר וצבעים שמחים, כמו סדרות גן מודרניות. הכי פשוט להנפשה.',
    boy: { name: 'נועם', text: 'נלהב, עונה ראשון ותמיד בטוח בעצמו, גם כשהוא טועה. חסרה לו שן קדמית, אז הוא שורק קצת על ש׳ ועל S.' },
    girl: { name: 'תמר', text: 'חכמה וסבלנית. מכוונת את נועם לתשובה הנכונה וצוחקת הכי חזק מהטעויות שלו.' },
    line: 'נועם: ״אני יודע! אני יודע!״ (ואז טועה)',
    gag: 'נועם מנסה לנחש מילה עם א׳, מתעטש ״אַפְּצִ׳י!״ ותמר: ״נכון! אפצ׳י מתחיל ב־א׳!״. באנגלית זה עובד אותו דבר: <span dir="ltr">A is for… Achoo!</span>',
    voice: 'נועם: גבוה ונמרץ. תמר: ברור וחם.',
  },
  2: {
    names: 'איתי וליה', en: 'Itai & Lia',
    style: 'קריקטורה קלאסית עם קו מתאר עבה והבעות מוגזמות. בולט מאוד במסך קטן של טלפון.',
    boy: { name: 'איתי', text: 'ממציא עם משקפיים ענקיים ומפתח ברגים. בונה מכונה שאמורה ״לייצר״ את האות, והיא תמיד משתבשת.' },
    girl: { name: 'ליה', text: 'הרפתקנית עם זכוכית מגדלת. יוצאת לצוד את האות בעולם ומשמיעה אפקט קולי לכל דבר.' },
    line: 'ליה: ״זכוכית מגדלת… מצאתי!״  איתי: ״רגע, יש לי מכונה בשביל זה!״',
    gag: 'מכונת האותיות של איתי צריכה להוציא א׳ ויורה אננס שנוחת לו על הראש. ליה: ״אננס! גם מתחיל ב־א׳!״',
    voice: 'איתי: מהיר ומלא מילים. ליה: אנרגטית, עם הרבה ״בום!״ ו״ווּש!״.',
  },
  3: {
    names: 'גיל ונוגה', en: 'Gil & Noga',
    style: 'ספר ילדים מגזרי נייר, עם טקסטורה וצללים רכים. חם ושקט יותר, מתאים גם לפני השינה.',
    boy: { name: 'גיל', text: 'ישנוני וגמלוני, ולא נפרד מהכרית שלו. נרדם באמצע ומתעורר בבהלה עם תשובה מצחיקה.' },
    girl: { name: 'נוגה', text: 'דרמטית ושרה כל דבר לתוך מברשת שיער, כאילו זה מיקרופון. כל אות מקבלת ממנה הופעה.' },
    line: 'נוגה: ״ועכשיו… קבלו את… האות!״  גיל: ״זזז… מה? כבר ב׳?״',
    gag: 'נוגה שרה שיר ארוך על א׳ וגיל נרדם. בחלום מופיע אריה ששואג ״אַאַאַ!״, גיל קופץ: ״אַ! זה הצליל של א׳!״',
    voice: 'גיל: איטי ומפהק. נוגה: תיאטרלית ושרה.',
  },
  4: {
    names: 'טלי ודני', en: 'Tali & Danny',
    style: 'צ׳יבי: ראש גדול, גוף קטן ועיניים נוצצות. הכי ״חמוד״ מבין הארבעה.',
    boy: { name: 'דני', text: 'בן הדוד מאמריקה ומומחה ל־<bdi>ABC</bdi>. מחזיק תפוח, כי <span dir="ltr">A is for Apple</span>.' },
    girl: { name: 'טלי', text: 'מישראל ומומחית לאלף־בית. מחזיקה פלח אבטיח, כי א׳ זה אבטיח.' },
    line: 'טלי: ״דני, ׳שלום׳ זה לא סלמי!״',
    gag: 'בכל פרק אחד מלמד את השני ומתבלבלים במילים. בסדרה העברית טלי מובילה ודני מנסה להגיד ״אבטיח״ ויוצא לו ״אבא־טיח״. בסדרה באנגלית דני מוביל.',
    voice: 'טלי: עברית ישראלית. דני: אנגלית במבטא אמריקאי (כמו שצריך לסדרת <bdi>ABC</bdi>).',
  },
};

function pairInline(opt, id) {
  const { w, h } = vbSize(opt.viewBox);
  return svgDoc({
    viewBox: `0 0 ${w * 2} ${h - 30}`,
    label: `${INFO[opt.number].names}, ציור גוף מלא`,
    body: opt.boy.full(`${id}-b`, { expr: 'happy' }) +
      g('', opt.girl.full(`${id}-g`, { expr: 'happy' }), `transform="translate(${w},0)"`),
  });
}

function headInline(opt, who, id, expr, label) {
  return svgDoc({ viewBox: HEAD_VB, label, body: who.head(id, { expr }) });
}

function card(opt) {
  const n = opt.number, info = INFO[n], p = `gal${n}`;
  const faces = [[opt.boy, info.boy.name], [opt.girl, info.girl.name]].map(([who, name]) =>
    `<div class="faces-row"><span class="faces-name">${name}</span><div class="faces">` +
    EXPRESSIONS.map(e => `<figure>${headInline(opt, who, `${p}-${who.key}-${e.key}`, e.key, `${name} ${e.he}`)}<figcaption>${e.he}</figcaption></figure>`).join('') +
    '</div></div>').join('');
  return `
  <article class="option" id="option-${n}" style="--stage: var(--stage-${n})">
    <header class="option-head">
      <span class="num" aria-label="אפשרות ${n}">${n}</span>
      <div><h2>${info.names}</h2><p class="en" dir="ltr">${info.en}</p></div>
    </header>
    <div class="stage">${pairInline(opt, p)}</div>
    ${faces}
    <dl class="facts">
      <div><dt>סגנון</dt><dd>${info.style}</dd></div>
      <div><dt>${info.boy.name}</dt><dd>${info.boy.text}</dd></div>
      <div><dt>${info.girl.name}</dt><dd>${info.girl.text}</dd></div>
      <div><dt>משפט קבוע</dt><dd>${info.line}</dd></div>
      <div><dt>גאג לדוגמה</dt><dd>${info.gag}</dd></div>
      <div><dt>קולות</dt><dd>${info.voice}</dd></div>
    </dl>
  </article>`;
}

function page() {
  return `<title>ליהוק מנחי האותיות</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&family=Rubik:wght@400;500;600&display=swap">
<style>
/* Layout: a casting board. Each pair stands on its own colored stage; numbers are the option ids the user replies with. */
:root {
  --bg: #F1F4F9; --surface: #FFFFFF; --fg: #1F2433; --muted: #586176; --line: #DDE3EC; --accent: #F2622E;
  --stage-1: #FFE7D2; --stage-2: #DCE9FF; --stage-3: #E5EFDA; --stage-4: #FBE1EA;
  --display: "Fredoka", "Rubik", "Arial Hebrew", system-ui, sans-serif;
  --body: "Rubik", "Arial Hebrew", system-ui, sans-serif;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #121620; --surface: #1A2030; --fg: #EDF0F6; --muted: #A2ABBE; --line: #2B3346; --accent: #FF8657;
  --stage-1: #EED7C2; --stage-2: #C9D9F2; --stage-3: #D3E0C6; --stage-4: #ECCFDA; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #121620; --surface: #1A2030; --fg: #EDF0F6; --muted: #A2ABBE; --line: #2B3346; --accent: #FF8657;
  --stage-1: #EED7C2; --stage-2: #C9D9F2; --stage-3: #D3E0C6; --stage-4: #ECCFDA; color-scheme: dark; }

body { background: var(--bg); color: var(--fg); font-family: var(--body); font-size: 16px; line-height: 1.6; }
.wrap { max-width: 1240px; margin: 0 auto; padding-block: 40px 56px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.intro { display: grid; gap: 10px; max-width: 62ch; margin-bottom: 32px; }
.eyebrow { font-family: var(--display); font-weight: 600; color: var(--accent); letter-spacing: .02em; margin: 0; }
h1 { font-family: var(--display); font-weight: 700; font-size: clamp(2rem, 5vw, 3.1rem); line-height: 1.1; margin: 0; text-wrap: balance; }
.intro p { margin: 0; color: var(--muted); font-size: 1.05rem; }
.intro strong { color: var(--fg); font-weight: 600; }

.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 520px), 1fr)); gap: 24px; }
.option { background: var(--surface); border: 1px solid var(--line); border-radius: 22px; overflow: hidden;
  display: grid; align-content: start; min-width: 0; }
.option-head { display: flex; align-items: center; gap: 14px; padding: 18px 20px 14px; }
.num { flex: none; width: 52px; height: 52px; border-radius: 50%; background: var(--fg); color: var(--surface);
  display: grid; place-items: center; font-family: var(--display); font-weight: 700; font-size: 1.7rem; line-height: 1; }
h2 { font-family: var(--display); font-weight: 600; font-size: 1.65rem; line-height: 1.15; margin: 0; }
.en { margin: 0; color: var(--muted); font-size: .9rem; text-align: right; }

.stage { background: var(--stage); margin: 0 14px; border-radius: 16px; padding: 10px 8px 0; }
.stage svg { display: block; width: 100%; height: auto; max-width: 100%; }

.faces-row { display: grid; grid-template-columns: 64px 1fr; align-items: center; gap: 8px; padding: 10px 20px 0; }
.faces-name { font-family: var(--display); font-weight: 600; font-size: 1.05rem; }
.faces { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.faces figure { margin: 0; display: grid; justify-items: center; gap: 0; }
.faces svg { width: 100%; max-width: 104px; height: auto; background: var(--stage); border-radius: 50%; }
.faces figcaption { font-size: .82rem; color: var(--muted); }

.facts { margin: 0; padding: 16px 20px 22px; display: grid; gap: 10px; }
.facts div { display: grid; grid-template-columns: 96px 1fr; gap: 12px; padding-top: 10px; border-top: 1px solid var(--line); }
.facts dt { font-family: var(--display); font-weight: 600; font-size: .95rem; }
.facts dd { margin: 0; min-width: 0; }

.next { margin-top: 36px; display: grid; gap: 12px; max-width: 70ch; }
.next h2 { font-size: 1.4rem; }
.next ol { margin: 0; padding-inline-start: 1.3em; display: grid; gap: 6px; color: var(--muted); }
.next ol strong { color: var(--fg); font-weight: 600; }

@media (max-width: 460px) {
  .facts div { grid-template-columns: 1fr; gap: 2px; }
  .faces-row { grid-template-columns: 1fr; padding-inline: 16px; }
  .option-head { padding-inline: 16px; }
  .stage { margin: 0 10px; }
}
</style>

<main class="wrap" dir="rtl" lang="he">
  <section class="intro">
    <p class="eyebrow">א־ב ו־ABC · שורטס לגילאי 4 עד 6</p>
    <h1>מי יגיש את האותיות?</h1>
    <p>ארבעה זוגות מנחים, כל אחד מצויר בסגנון אחר ועם קטע מצחיק משלו. לכל דמות יש כבר שלוש הבעות פנים, והציור בנוי בשכבות (עיניים, פה, ידיים) כדי שיהיה אפשר להנפיש אותו.</p>
    <p><strong>תכתוב לי בצ׳אט את מספר הזוג שבחרת.</strong> אפשר גם לשלב, למשל הבן מזוג 2 עם הבת מזוג 1, ואצייר אותם מחדש באותו סגנון. גם שמות, צבעים ובגדים אפשר לשנות.</p>
  </section>

  <div class="grid">${OPTIONS.map(card).join('')}
  </div>

  <section class="next">
    <h2>מה קורה אחרי שבוחרים</h2>
    <ol>
      <li><strong>הכנת הדמויות להנפשה:</strong> חמש צורות פה לדיבור, מצמוץ, תנוחות ידיים ומבט מהצד.</li>
      <li><strong>תבנית לפרק של 60 עד 90 שניות:</strong> פתיחה שתופסת, הצגת האות והצליל שלה, שלוש מילים עם בדיחה, שיר חזרה קצר וסיום.</li>
      <li><strong>תסריט ראשון:</strong> פרק על א׳ ופרק על A.</li>
      <li><strong>סרטון ראשון בפורמט שורטס (9:16):</strong> אנימציה, קולות וכתוביות.</li>
    </ol>
  </section>
</main>
`;
}

const out = path.join(__dirname, '..', 'gallery.html');
fs.writeFileSync(out, page());
console.log(`wrote ${out} (${Math.round(fs.statSync(out).size / 1024)} KB)`);
