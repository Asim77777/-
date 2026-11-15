import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import highlights, render, subtitles  # noqa: E402


def make_words(n_sentences=40, words_per=8, word_dur=0.3, pause=0.8):
    words, t = [], 0.0
    for s in range(n_sentences):
        for k in range(words_per):
            text = "מילה"
            if k == 0 and s % 7 == 0:
                text = "למה"
            if k == words_per - 1:
                text += "?" if s % 7 == 0 else "."
            words.append({"t": text, "s": round(t, 3), "e": round(t + word_dur - 0.05, 3)})
            t += word_dur
        t += pause
    return words


def test_highlights_lengths_and_no_overlap():
    words = make_words()
    clips = highlights.find_highlights(words, count=3, min_len=20, max_len=58)
    assert 1 <= len(clips) <= 3
    for c in clips:
        assert 19 <= c["end"] - c["start"] <= 59
        assert 55 <= c["score"] <= 98
        assert c["title"]
    spans = sorted((c["start"], c["end"]) for c in clips)
    for (_, e1), (s2, _) in zip(spans, spans[1:]):
        assert s2 >= e1


def test_highlights_prefers_hook_opening():
    best = highlights.find_highlights(make_words(), count=1)[0]
    assert best["title"].startswith("למה")


def test_short_video_returns_whole():
    words = make_words(n_sentences=3)
    clips = highlights.find_highlights(words, count=5, min_len=20, max_len=58)
    assert len(clips) == 1
    assert clips[0]["start"] == 0.0


def test_empty_transcript():
    assert highlights.find_highlights([], count=3) == []


def test_sentences_split_on_punctuation_and_gaps():
    words = [{"t": "א", "s": 0, "e": .2}, {"t": "ב.", "s": .2, "e": .4},
             {"t": "ג", "s": .4, "e": .6}, {"t": "ד", "s": 2.0, "e": 2.2}]
    assert highlights.build_sentences(words) == [(0, 1), (2, 2), (3, 3)]


LINES = [{"s": 0.0, "e": 1.5, "words": [{"t": "שלום", "s": 0.0, "e": 0.5},
                                         {"t": "עולם", "s": 0.6, "e": 1.2}]}]


def test_ass_highlight_events():
    ass = subtitles.build_ass(LINES, {"highlightEnabled": True, "animation": "pop"}, 10)
    events = [l for l in ass.splitlines() if l.startswith("Dialogue")]
    assert len(events) == 2  # one per active word
    assert "PlayResX: 1080" in ass and "Heebo Black" in ass
    assert "\\1c&H00E6FF&" in events[0]  # #FFE600 as BGR
    assert events[0].count("\\t(") == 1 and "\\t(" not in events[1]
    assert "0:00:00.00,0:00:00.60" in events[0] and "0:00:00.60,0:00:01.50" in events[1]


def test_ass_plain_box_and_title():
    ass = subtitles.build_ass(LINES, {"highlightEnabled": False, "animation": "none",
                                      "bgEnabled": True, "titleText": "כותרת"}, 10)
    events = [l for l in ass.splitlines() if l.startswith("Dialogue")]
    styles = [e.split(",")[3] for e in events]
    assert styles == ["TitleBox", "Title", "SubBox", "Sub"]


def test_ass_sanitises_text_and_bad_style():
    lines = [{"s": 0, "e": 1, "words": [{"t": "{\\b1}x", "s": 0, "e": 1}]}]
    ass = subtitles.build_ass(lines, {"font": "Nope", "size": "abc", "color": "zz",
                                      "highlightEnabled": False, "animation": "none"}, 5)
    event = [l for l in ass.splitlines() if l.startswith("Dialogue")][0]
    assert event.endswith("}(b1)x")
    assert "Style: Sub,Heebo Black," in ass


def test_ass_reveal_hides_future_words():
    ass = subtitles.build_ass(LINES, {"highlightEnabled": False, "animation": "reveal"}, 10)
    events = [l for l in ass.splitlines() if l.startswith("Dialogue")]
    assert "\\alpha&HFF&" in events[0] and "\\alpha&HFF&" not in events[1]


def test_filter_modes():
    fill = render.build_filter({"mode": "fill", "x": 0.25}, Path("/tmp/a.ass"))
    assert "crop=1080:1920:(iw-1080)*0.2500" in fill
    fit = render.build_filter({"mode": "fit"}, Path("/tmp/a.ass"))
    assert "boxblur" in fit and "overlay" in fit
    assert "0.5000" in render.build_filter({"x": "bad"}, Path("/tmp/a.ass"))


# ---------------------------------------------------------------- phone mode
def _client(monkeypatch, host, pin="123456"):
    from fastapi.testclient import TestClient

    from app import main
    monkeypatch.setattr(main, "PIN", pin)
    monkeypatch.setattr(main, "TOKEN", "t" * 30)
    monkeypatch.setattr(main, "LAN_URL", "http://192.168.1.10:8000" if pin else "")
    main.login_fails.clear()
    return TestClient(main.app, client=(host, 50000), follow_redirects=False)


def test_local_computer_needs_no_code(monkeypatch):
    c = _client(monkeypatch, "127.0.0.1")
    assert c.get("/api/fonts").status_code == 200
    info = c.get("/api/phone").json()
    assert info["enabled"] and info["pin"] == "123456" and "<svg" in info["qr_svg"]


def test_phone_must_log_in(monkeypatch):
    c = _client(monkeypatch, "192.168.1.50")
    assert c.get("/api/fonts").status_code == 401
    assert c.get("/api/jobs").status_code == 401
    r = c.get("/")
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert c.get("/login").status_code == 200
    assert c.post("/api/login", json={"pin": "000000"}).status_code == 401
    assert c.post("/api/login", json={"pin": "123456"}).status_code == 200
    assert c.get("/api/fonts").status_code == 200
    assert c.get("/").status_code == 200
    assert c.get("/api/phone").json() == {"enabled": False}  # code never sent to phones


def test_login_lockout(monkeypatch):
    c = _client(monkeypatch, "192.168.1.51")
    for _ in range(5):
        assert c.post("/api/login", json={"pin": "111111"}).status_code == 401
    assert c.post("/api/login", json={"pin": "123456"}).status_code == 429


def test_remote_blocked_when_phone_mode_off(monkeypatch):
    c = _client(monkeypatch, "192.168.1.52", pin="")
    assert c.get("/api/fonts").status_code == 401
    assert c.post("/api/login", json={"pin": ""}).status_code == 403
    assert c.cookies.get("shorts_auth") is None


# ---------------------------------------------------------------- download
def _fake_ytdlp(monkeypatch, tmp_path, script):
    """Replace `python -m yt_dlp` with a small script."""
    from app import download
    fake = tmp_path / "fake.py"
    fake.write_text(script)
    real_popen = download.subprocess.Popen
    monkeypatch.setattr(download.subprocess, "Popen",
                        lambda cmd, **kw: real_popen([sys.executable, str(fake)], **kw))
    return download


def test_download_reports_progress_and_title(monkeypatch, tmp_path):
    d = _fake_ytdlp(monkeypatch, tmp_path, f"""
import pathlib
print("TITLE שלום", flush=True)
print("PROG 5000000 10000000 NA 2000000", flush=True)
pathlib.Path(r"{tmp_path}/source.mp4").write_bytes(b"x")
""")
    seen = []
    info = d.download_video("https://x", tmp_path, lambda p, t: seen.append((p, t)))
    assert info["title"] == "שלום"
    assert seen[0][0] == 0.5 and "5MB מתוך 10MB" in seen[0][1]


def test_download_stall_is_killed(monkeypatch, tmp_path):
    d = _fake_ytdlp(monkeypatch, tmp_path, "import time; time.sleep(60)")
    monkeypatch.setattr(d, "STALL_SECONDS", 1)
    import pytest, time
    t = time.time()
    with pytest.raises(RuntimeError, match="נתקעה"):
        d.download_video("https://x", tmp_path)
    assert time.time() - t < 10


def test_download_cancel(monkeypatch, tmp_path):
    d = _fake_ytdlp(monkeypatch, tmp_path, "import time; time.sleep(60)")
    import pytest
    with pytest.raises(d.Cancelled):
        d.download_video("https://x", tmp_path, should_cancel=lambda: True)


def test_download_error_is_friendly(monkeypatch, tmp_path):
    d = _fake_ytdlp(monkeypatch, tmp_path, """
import sys
print("ERROR: [youtube] abc: Sign in to confirm you're not a bot", flush=True)
sys.exit(1)
""")
    import pytest
    with pytest.raises(RuntimeError, match="הגדרות מתקדמות"):
        d.download_video("https://x", tmp_path)
    assert "עדכן" in d.friendly_error("ERROR: unable to download video data: HTTP Error 403: Forbidden")
