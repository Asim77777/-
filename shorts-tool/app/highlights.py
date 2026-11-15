"""Pick the most "viral" segments of a transcript - free, local heuristics.

A candidate clip is a run of whole sentences lasting min_len..max_len seconds.
Each candidate is scored on its opening hook, content signals (questions,
numbers, emphatic words), speaking pace, audio energy, dead air and how
cleanly it ends. The best non-overlapping candidates are returned.
"""
from __future__ import annotations

import re
import wave
from pathlib import Path

import numpy as np

HOOK_WORDS = {
    # Hebrew
    "סוד", "הסוד", "טעות", "הטעות", "טעויות", "אמת", "האמת", "מדהים", "מטורף",
    "הזוי", "מפתיע", "הפתעה", "חשוב", "הכי", "אף", "אחד", "לעולם", "תמיד",
    "בחיים", "תדמיינו", "תארו", "דמיינו", "תקשיבו", "שימו", "תראו", "הנה",
    "למה", "איך", "מה", "מי", "האם", "מתי", "ככה", "הסיבה", "הבעיה", "הפתרון",
    "טיפ", "טיפים", "כלל", "חוק", "שיטה", "הוכחה", "גיליתי", "הבנתי", "למדתי",
    "רגע", "פתאום", "סיפור", "פעם", "אסור", "חייבים", "חייב", "מסוכן",
    # English
    "secret", "mistake", "truth", "never", "always", "why", "how", "what",
    "imagine", "listen", "crazy", "insane", "shocking", "best", "worst",
    "nobody", "everyone", "stop", "reason", "problem", "story", "learned",
}
EMPHASIS_WORDS = {
    "מאוד", "ממש", "לגמרי", "בטוח", "ברור", "פשוט", "מדהים", "נורא", "מטורף",
    "אדיר", "ענק", "עצום", "הכי", "כסף", "מיליון", "מיליונים", "אלף", "אחוז",
    "אחוזים", "אהבה", "פחד", "מוות", "חיים", "הצלחה", "כישלון", "נס", "אלוהים",
    "השם", "נשמה", "לב", "אמונה", "שמחה", "כאב", "חופש", "כוח", "עוצמה",
    "really", "very", "absolutely", "money", "million", "love", "fear",
    "death", "life", "success", "failure", "huge", "amazing", "incredible",
}
# Openers that signal the clip starts mid-thought
WEAK_OPENERS = {
    "אז", "אבל", "כי", "וגם", "גם", "או", "ואז", "לכן", "כלומר", "בנוסף",
    "שזה", "וזה", "והוא", "והיא", "והם", "אהה", "אממ", "כאילו",
    "and", "but", "so", "because", "or", "then", "also", "um", "uh",
}

_strip_re = re.compile(r"[^\w֐-׿]+", re.UNICODE)


def _norm(word: str) -> str:
    return _strip_re.sub("", word).lower()


def build_sentences(words: list[dict], max_gap: float = 0.7,
                    max_words: int = 28) -> list[tuple[int, int]]:
    """Split word list into (first_idx, last_idx) sentence spans."""
    spans: list[tuple[int, int]] = []
    start = 0
    for i, w in enumerate(words):
        last = i == len(words) - 1
        gap = 0.0 if last else words[i + 1]["s"] - w["e"]
        ends = w["t"].rstrip('"\')”').endswith((".", "?", "!", "…"))
        if last or ends or gap >= max_gap or (i - start + 1) >= max_words:
            spans.append((start, i))
            start = i + 1
    return spans


def audio_energy(wav_path: Path | None, hop: float = 0.5) -> np.ndarray | None:
    """RMS energy per `hop` seconds, normalised to z-scores."""
    if not wav_path or not Path(wav_path).exists():
        return None
    with wave.open(str(wav_path), "rb") as wf:
        rate = wf.getframerate()
        data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    n = int(rate * hop)
    if len(data) < n * 2:
        return None
    data = data[: len(data) // n * n].astype(np.float32).reshape(-1, n)
    rms = np.sqrt((data ** 2).mean(axis=1))
    voiced = rms[rms > rms.max() * 0.02]
    if len(voiced) < 2 or voiced.std() == 0:
        return None
    return (rms - voiced.mean()) / voiced.std()


def _hook_score(tokens: list[str], raw_first_sentence: str) -> float:
    if not tokens:
        return 0.0
    score = 0.0
    head = tokens[:8]
    score += min(sum(1 for t in head if t in HOOK_WORDS), 3) * 0.6
    if "?" in raw_first_sentence:
        score += 1.2
    if any(ch.isdigit() for ch in "".join(head)):
        score += 0.5
    if len(tokens) <= 14:
        score += 0.4  # short punchy opener
    if tokens[0] in WEAK_OPENERS:
        score -= 1.0
    # Hebrew prefix "ו" (and) at clip start usually continues a thought
    if tokens[0].startswith("ו") and len(tokens[0]) > 2:
        score -= 0.4
    return score


def find_highlights(words: list[dict], count: int = 3, min_len: float = 20.0,
                    max_len: float = 58.0, wav_path: Path | None = None,
                    hop: float = 0.5) -> list[dict]:
    """Return up to `count` clips: {start, end, score, title, reasons}."""
    if not words:
        return []
    total_start, total_end = words[0]["s"], words[-1]["e"]
    if total_end - total_start <= min_len:
        return [_clip(words, 0, len(words) - 1, 75, ["הסרטון קצר - נלקח במלואו"])]

    sents = build_sentences(words)
    toks = [_norm(w["t"]) for w in words]
    energy = audio_energy(wav_path, hop)
    pace_all = len(words) / max(total_end - total_start, 1.0)

    cands = []
    for i, (a, _) in enumerate(sents):
        gap_before = words[a]["s"] - words[a - 1]["e"] if a > 0 else 1.0
        for j in range(i, len(sents)):
            b = sents[j][1]
            dur = words[b]["e"] - words[a]["s"]
            if dur > max_len:
                break
            if dur < min_len:
                continue
            seg_words = words[a:b + 1]
            seg_toks = toks[a:b + 1]
            fa, fb = sents[i]
            first_raw = " ".join(w["t"] for w in words[fa:fb + 1])
            reasons = []

            hook = _hook_score(toks[fa:fb + 1], first_raw)
            if hook >= 1.0:
                reasons.append("פתיחה חזקה")
            if gap_before >= 0.5:
                hook += 0.4  # starts after a natural pause

            n = len(seg_words)
            questions = sum(1 for w in seg_words if "?" in w["t"])
            numbers = sum(1 for t in seg_toks if any(c.isdigit() for c in t))
            emph = sum(1 for t in seg_toks if t in EMPHASIS_WORDS or t in HOOK_WORDS)
            content = (min(questions, 3) * 0.5 + min(numbers, 3) * 0.25
                       + min(emph / max(n, 1) * 25, 2.0))
            if questions:
                reasons.append("שאלות שמעוררות סקרנות")
            if emph / max(n, 1) > 0.05:
                reasons.append("מילים רגשיות וחזקות")

            pace = (n / dur) / pace_all
            pace_score = max(min((pace - 1.0) * 2.0, 1.0), -1.0)
            if pace > 1.1:
                reasons.append("קצב דיבור מהיר")

            dead = sum(max(seg_words[k + 1]["s"] - seg_words[k]["e"] - 1.0, 0)
                       for k in range(n - 1))
            silence_pen = min(dead / dur * 6, 2.0)

            en_score = 0.0
            if energy is not None:
                lo = int(words[a]["s"] / hop)
                hi = max(int(words[b]["e"] / hop), lo + 1)
                win = energy[lo:hi]
                if len(win):
                    en_score = float(np.clip(win.mean(), -1.5, 1.5)) * 0.6
                    if win.mean() > 0.3:
                        reasons.append("אנרגיה גבוהה בקול")

            last = words[b]["t"].rstrip('"\')”')
            gap_after = words[b + 1]["s"] - words[b]["e"] if b + 1 < len(words) else 1.0
            ending = (0.6 if last.endswith((".", "?", "!")) else 0.0)
            ending += 0.4 if gap_after >= 0.4 else 0.0
            if ending >= 1.0:
                reasons.append("סיום נקי")

            # prefer ~30-45s
            length = 0.5 - abs(dur - 38.0) / 40.0

            raw = (hook * 1.4 + content + pace_score * 0.6 + en_score
                   + ending + length - silence_pen)
            cands.append((raw, a, b, reasons))

    if not cands:  # no sentence-aligned window fits: fall back to fixed windows
        return _fallback(words, count, min_len, max_len)

    raws = np.array([c[0] for c in cands])
    lo, hi = float(raws.min()), float(raws.max())
    span = (hi - lo) or 1.0

    picked: list[tuple[float, int, int, list[str]]] = []
    for raw, a, b, reasons in sorted(cands, key=lambda c: -c[0]):
        s, e = words[a]["s"], words[b]["e"]
        if all(e + 3 <= words[pa]["s"] or s >= words[pb]["e"] + 3
               for _, pa, pb, _ in picked):
            picked.append((raw, a, b, reasons))
            if len(picked) >= count:
                break

    return [
        _clip(words, a, b, int(round(55 + (raw - lo) / span * 43)), reasons)
        for raw, a, b, reasons in picked
    ]


def _clip(words, a, b, score, reasons):
    title_words = []
    for w in words[a:b + 1]:
        if not any(ch.isalnum() for ch in w["t"]):
            continue
        title_words.append(w["t"])
        if w["t"].endswith((".", "?", "!")) or len(" ".join(title_words)) > 60:
            break
    return {
        "start": round(max(words[a]["s"] - 0.15, 0.0), 2),
        "end": round(words[b]["e"] + 0.25, 2),
        "score": score,
        "title": " ".join(title_words).strip(" .,…"),
        "reasons": reasons,
    }


def _fallback(words, count, min_len, max_len):
    target = (min_len + max_len) / 2
    clips, a = [], 0
    while a < len(words) and len(clips) < count:
        b = a
        while b + 1 < len(words) and words[b + 1]["e"] - words[a]["s"] <= target:
            b += 1
        if words[b]["e"] - words[a]["s"] >= min_len * 0.6:
            clips.append(_clip(words, a, b, 60, []))
        a = b + 1
    return clips
