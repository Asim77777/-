"""Shared HTML rendering of drashot for the web book and the print (PDF) book."""
import html
from parse import video_link, fmt_ts, heb_number

BOOK_TITLE = "דרשות הרב חיים דרעי שליט״א"
BOOK_SUBTITLE = "שיעורים ודרשות בתורה, מחשבה והתבוננות"
BOOK_SPAN = "מתוך השיעורים המצולמים, אלול ה׳תשפ״ד – כסלו ה׳תשפ״ז"

INTRO_HTML = """
<p>הספר שלפניכם נערך מתוך הדרשות המצולמות של הרב חיים דרעי שליט״א, כפי שהן מופיעות באתר השיעורים ובערוץ היוטיוב
"דרשות הרב חיים דרעי שליט״א". כל פרק בספר הוא דרשה אחת, והדרשות מסודרות לפי שערים על פי נושאיהן.</p>
<p><b>דרך העריכה.</b> הטקסט הוא העתקה של הדברים כפי שנאמרו בעל פה, בלשון הדיבור, בלי תוספות, בלי השמטות ובלי סיכומים.
התמלול נעשה מתוך התמלול האוטומטי של יוטיוב, ותוקנו בו רק שגיאות זיהוי ברורות. נוספו פיסוק וחלוקה לפסקאות.</p>
<p><b>סימנים:</b></p>
<ul>
<li><span class="add">[מילה]</span> – מילה או אותיות שהושלמו על ידי העורך, במקום שבו ההקלטה לא נקלטה היטב.</li>
<li><span class="unc">[?]</span> – מילים שלא ניתן היה לשחזר בוודאות מתוך ההקלטה. הסימן מקשר לרגע המדויק בסרטון.</li>
<li><span class="ref">[במדבר יג, ב]</span> – מראה מקום שהוסיף העורך.</li>
<li><span class="note">[מן הקהל: …]</span> – דברים שנאמרו מפי השומעים, והערות על המתרחש בשיעור.</li>
<li>כותרות המשנה בתוך הדרשות נוספו על ידי העורך לנוחות הקורא, ואינן מדברי הרב.</li>
</ul>
<p>מי שמבקש לדייק בלשון הדברים מוזמן לצפות בדרשה עצמה דרך הקישור שבראש כל פרק.</p>
"""


def esc(s):
    return html.escape(s, quote=True)


def render_segs(segs, url, print_mode=False):
    out = []
    for kind, val in segs:
        if kind == "text":
            out.append(esc(val))
        elif kind == "ref":
            out.append(f'<span class="ref">[{esc(val)}]</span>')
        elif kind == "add":
            out.append(f'<span class="add">[{esc(val)}]</span>')
        elif kind == "note":
            out.append(f'<span class="note">[{esc(val)}]</span>')
        elif kind == "unclear":
            out.append(f'<a class="unc" href="{esc(video_link(url, val))}" target="_blank" rel="noopener" '
                       f'title="לא ברור בהקלטה – האזינו בסרטון ({fmt_ts(val)})">[?]</a>')
    return "".join(out)


def render_drasha(d, print_mode=False, marker=None):
    parts = [f'<section class="drasha" id="d-{esc(d["id"])}" data-num="{d["num"]}">']
    mk = f'<span class="mk">{marker}</span>' if marker else ""
    parts.append(f'<header class="dh"><div class="dnum">דרשה {heb_number(d["num"])}</div>'
                 f'<h2 class="dtitle">{mk}{esc(d["title"])}</h2>'
                 f'<div class="dmeta"><span class="ddate">{esc(d["date"])}</span>'
                 f'<a class="dvideo" href="{esc(d["url"])}" target="_blank" rel="noopener">'
                 f'{"צפייה בדרשה: " + esc(d["url"]) if print_mode else "▶ צפייה בדרשה"}</a></div></header>')
    for b in d["blocks"]:
        if b["type"] == "h":
            parts.append(f'<h3 class="sh">{esc(b["text"])}</h3>')
        else:
            ts = ""
            if b["sec"] is not None and not print_mode:
                ts = (f'<a class="ts" href="{esc(video_link(d["url"], b["sec"]))}" target="_blank" '
                      f'rel="noopener" title="האזנה מרגע זה">{fmt_ts(b["sec"])}</a>')
            parts.append(f'<p>{ts}{render_segs(b["segs"], d["url"], print_mode)}</p>')
    parts.append("</section>")
    return "\n".join(parts)
