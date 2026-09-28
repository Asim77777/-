# סרטון תדמית – 70 פנים לתורה

| קובץ | פורמט | אורך |
|---|---|---|
| `out/promo-vertical-9x16.mp4` | ‏1080×1920 (סטטוס, רילס, שורטס) | כ-63 שניות |
| `out/promo-horizontal-16x9.mp4` | ‏1920×1080 (יוטיוב, אתר) | כ-83 שניות |

## איך זה בנוי
- `scene.html` – כל הסרטון הוא דף HTML אחד. `window.setTime(t)` מצייר את הפריים בזמן `t`.
  הסצנות, הכיתובים ומיקומי ההדגשות מוגדרים במערך `SCENES` (קואורדינטות לפי תצוגה של 923×2000).
- `render.py` – מריץ את הדף ב-Chromium ללא ממשק, מצלם 30 פריימים לשנייה, מקודד עם ffmpeg (H.264)
  ומוסיף צליל רקע סינתטי עדין (אקורד לה מינור).
- `assets/` – צילומי המסך ותמונת המותג. שורת הסטטוס ושורת הניווט של אנדרואיד נחתכות בתצוגה,
  והשם בכותרת מוחלף ב"שלום, משתמש יקר".
- `fonts/` – Heebo ו-Frank Ruhl Libre (רישיון OFL).

## רינדור מחדש
```bash
pip install playwright imageio-ffmpeg
python3 render.py all            # או vertical / horizontal
python3 render.py vertical --preview 3,10,20   # תמונות PNG לבדיקה בלבד
```
אם Chromium לא נמצא בנתיב `/opt/pw-browsers/chromium`, צריך להגדיר את משתנה הסביבה `CHROMIUM_PATH`.
