# אותיות לילדים: שורטס א־ב ו־ABC

סדרת סרטוני שורטס (9:16, דקה עד שתי דקות) שמלמדים ילדים בגילאי 4 עד 6 את האלף־בית העברי ואת ה־ABC, עם שני מנחים מצוירים: בן ובת.

## מצב נוכחי
שלב 1: בחירת דמויות. יש 4 זוגות לבחירה, בסגנונות שונים:

| # | זוג | סגנון |
|---|-----|-------|
| 1 | נועם ותמר | עגול ורך, בלי קווי מתאר |
| 2 | איתי וליה | קריקטורה עם קו מתאר עבה |
| 3 | גיל ונוגה | ספר ילדים מגזרי נייר |
| 4 | טלי ודני | צ׳יבי, ראש גדול |

עמוד הבחירה: `characters/gallery.html`. תמונות: `characters/options/previews/`.

## מבנה
```
characters/
  src/lib.js            עזרים משותפים
  src/option1..4.js     כל דמות היא פונקציה: (id, { expr, blink }) => SVG
  src/build.js          יוצר את קבצי ה-SVG לכל אפשרות
  src/gallery.js        יוצר את gallery.html
  options/option-N/     boy.svg, girl.svg, pair.svg, expressions.svg, sheet.svg
  options/previews/     תמונות PNG של כל אפשרות
tools/render_svg.js     ממיר SVG ל-PNG עם Chromium (ישמש גם לרינדור פריימים של הסרטונים)
```

כל דמות בנויה משכבות עם id קבוע (`head`, `face`, `eyes`, `brows`, `mouth`, `hair`, `arm-l`, `arm-r`, `legs`, `body`), כדי שאפשר יהיה להנפיש כל חלק בנפרד. `arm-l` ו-`arm-r` הן לפי צד הצופה. הבעות זמינות: `happy`, `surprised`, `laugh`, ו-`blink` לעיניים עצומות.

## בנייה מחדש
```bash
node kids-letters/characters/src/build.js
node kids-letters/characters/src/gallery.js
node kids-letters/tools/render_svg.js kids-letters/characters/options/option-1/sheet.svg out.png --width 1200
```

## השלבים הבאים
1. הכנת הזוג שנבחר להנפשה: צורות פה לדיבור, מצמוץ, תנוחות ידיים, מבט מהצד.
2. תבנית פרק של 60 עד 90 שניות ותסריטים ל־א׳ ול־A.
3. צינור וידאו: סצנות SVG מונפשות, רינדור פריימים, ffmpeg ל-1080x1920, קול AI וסנכרון שפתיים.
