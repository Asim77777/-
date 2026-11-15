"""Shorts Studio - local web server.

POST /api/jobs            start: download -> transcribe -> pick highlights
GET  /api/jobs/{id}       status + clips + words
POST /api/jobs/{id}/export  render one short with burned-in subtitles
"""
from __future__ import annotations

import json
import queue
import re
import shutil
import threading
import time
import traceback
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import download, highlights, render, subtitles, transcribe

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

app = FastAPI(title="Shorts Studio")
jobs: dict[str, dict] = {}
work_q: "queue.Queue[str]" = queue.Queue()
export_lock = threading.Lock()  # one ffmpeg render at a time
ID_RE = re.compile(r"^[0-9a-f]{12}$")
PUBLIC_KEYS = ("id", "url", "status", "progress", "message", "title", "duration",
               "width", "height", "language", "clips", "created", "exports")


class JobRequest(BaseModel):
    url: str = Field(min_length=5, max_length=500)
    count: int = Field(default=3, ge=1, le=5)
    model: str = "hebrew"
    language: str = "he"
    min_len: float = Field(default=20, ge=5, le=120)
    max_len: float = Field(default=58, ge=10, le=180)
    cookies_browser: str = ""


class Word(BaseModel):
    t: str = Field(max_length=200)
    s: float
    e: float


class Line(BaseModel):
    s: float
    e: float
    words: list[Word]


class ExportRequest(BaseModel):
    clip_id: int = 0
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    lines: list[Line] = []
    style: dict = {}
    crop: dict = {}


def job_dir(job_id: str) -> Path:
    if not ID_RE.match(job_id):
        raise HTTPException(404, "עבודה לא נמצאה")
    return DATA / job_id


def get_job(job_id: str) -> dict:
    d = job_dir(job_id)
    if job_id not in jobs:
        f = d / "job.json"
        if not f.exists():
            raise HTTPException(404, "עבודה לא נמצאה")
        job = json.loads(f.read_text(encoding="utf-8"))
        if job["status"] not in ("ready", "error"):
            # left mid-flight by a server restart - it can never finish
            job.update(status="error", message="השרת הופעל מחדש באמצע העבודה")
        jobs[job_id] = job
    return jobs[job_id]


def save(job: dict) -> None:
    d = DATA / job["id"]
    tmp = d / "job.json.tmp"
    tmp.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    tmp.replace(d / "job.json")


def update(job: dict, **kw) -> None:
    job.update(kw)


def new_job(url: str, opts: dict) -> dict:
    job = {
        "id": uuid.uuid4().hex[:12], "url": url, "status": "queued",
        "progress": 0.0, "message": "ממתין בתור", "title": "", "clips": [],
        "words": [], "exports": {}, "created": time.time(), "opts": opts,
    }
    (DATA / job["id"]).mkdir(parents=True)
    jobs[job["id"]] = job
    save(job)
    return job


def run_pipeline(job: dict) -> None:
    d = DATA / job["id"]
    opts = job["opts"]
    src = d / "source.mp4"

    if not src.exists():
        update(job, status="downloading", progress=0.0, message="מוריד את הסרטון")
        info = download.download_video(
            job["url"], d, lambda p: update(job, progress=p),
            opts.get("cookies_browser", ""))
        job["title"] = info["title"]

    meta = download.probe(src)
    update(job, duration=meta["duration"], width=meta["width"],
           height=meta["height"], has_audio=meta["has_audio"])
    if not meta["has_audio"]:
        raise RuntimeError("בסרטון אין ערוץ שמע - אי אפשר לתמלל")

    update(job, status="transcribing", progress=0.0,
           message="מתמלל (בהרצה ראשונה מוריד את מודל התמלול)")
    wav = d / "audio.wav"
    download.extract_audio(src, wav)
    lang = None if opts["language"] == "auto" else opts["language"]
    result = transcribe.transcribe(
        wav, opts["model"], lang, lambda p: update(job, progress=p))
    if not result["words"]:
        raise RuntimeError("לא זוהה דיבור בסרטון")
    update(job, words=result["words"], language=result["language"])

    update(job, status="analyzing", progress=0.0, message="בוחר את הקטעים הטובים")
    clips = highlights.find_highlights(
        result["words"], opts["count"], opts["min_len"], opts["max_len"], wav)
    for i, c in enumerate(clips):
        c["id"] = i
    wav.unlink(missing_ok=True)
    update(job, clips=clips, status="ready", progress=1.0, message="מוכן")


def worker() -> None:
    while True:
        job_id = work_q.get()
        job = jobs.get(job_id)
        if not job:
            continue
        try:
            run_pipeline(job)
        except Exception as exc:  # surface the error to the UI
            traceback.print_exc()
            msg = str(exc).replace("ERROR: ", "").strip() or exc.__class__.__name__
            update(job, status="error", message=msg[:600])
        save(job)


threading.Thread(target=worker, daemon=True).start()


def public(job: dict, with_words: bool = False) -> dict:
    out = {k: job.get(k) for k in PUBLIC_KEYS}
    if with_words:
        out["words"] = job.get("words", [])
    return out


@app.post("/api/jobs")
def create_job(req: JobRequest):
    if not re.match(r"^https?://", req.url.strip()):
        raise HTTPException(400, "יש להזין קישור תקין שמתחיל ב-http")
    if req.max_len <= req.min_len:
        raise HTTPException(400, "האורך המקסימלי חייב להיות גדול מהמינימלי")
    job = new_job(req.url.strip(), req.model_dump(exclude={"url"}))
    work_q.put(job["id"])
    return public(job)


@app.post("/api/jobs/upload")
def upload_job(file: UploadFile = File(...), count: int = Form(3),
               model: str = Form("hebrew"), language: str = Form("he"),
               min_len: float = Form(20), max_len: float = Form(58)):
    opts = JobRequest(url="upload", count=count, model=model, language=language,
                      min_len=min_len, max_len=max_len).model_dump(exclude={"url"})
    job = new_job("upload", opts)
    d = DATA / job["id"]
    raw = d / "upload.bin"
    with raw.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    job["title"] = Path(file.filename or "video").stem
    try:
        meta = download.probe(raw)
        if meta["vcodec"] == "h264" and (file.filename or "").lower().endswith(".mp4"):
            raw.rename(d / "source.mp4")
        else:
            download.to_browser_mp4(raw, d / "source.mp4")
            raw.unlink()
    except Exception:
        shutil.rmtree(d, ignore_errors=True)
        jobs.pop(job["id"], None)
        raise HTTPException(400, "לא ניתן לקרוא את קובץ הווידאו")
    work_q.put(job["id"])
    return public(job)


@app.get("/api/jobs")
def list_jobs():
    out = []
    for d in DATA.iterdir():
        if d.is_dir() and ID_RE.match(d.name) and (d / "job.json").exists():
            try:
                j = get_job(d.name)
            except Exception:
                continue
            out.append({k: j.get(k) for k in ("id", "title", "status", "created",
                                              "duration")} | {"clips": len(j.get("clips", []))})
    return sorted(out, key=lambda j: -(j["created"] or 0))


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    return public(job, with_words=job["status"] == "ready")


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    job = get_job(job_id)
    if job["status"] not in ("ready", "error"):
        raise HTTPException(409, "העבודה עדיין רצה")
    jobs.pop(job_id, None)
    shutil.rmtree(job_dir(job_id), ignore_errors=True)
    return {"ok": True}


@app.get("/api/jobs/{job_id}/video")
def job_video(job_id: str):
    src = job_dir(job_id) / "source.mp4"
    if not src.exists():
        raise HTTPException(404, "הווידאו לא נמצא")
    return FileResponse(src, media_type="video/mp4")


def run_export(job: dict, exp_id: str, req: ExportRequest) -> None:
    d = DATA / job["id"]
    exp = job["exports"][exp_id]
    try:
        with export_lock:
            exp.update(status="rendering")
            duration = req.end - req.start
            lines = [
                {"s": ln.s - req.start, "e": ln.e - req.start,
                 "words": [{"t": w.t, "s": w.s - req.start, "e": w.e - req.start}
                           for w in ln.words]}
                for ln in req.lines
            ]
            ass = d / f"{exp_id}.ass"
            ass.write_text(subtitles.build_ass(lines, req.style, duration),
                           encoding="utf-8")
            out = d / f"{exp_id}.mp4"
            render.render_clip(d / "source.mp4", out, req.start, req.end, req.crop,
                               ass, job.get("has_audio", True),
                               lambda p: exp.update(progress=p))
            exp.update(status="done", progress=1.0)
    except Exception as exc:
        traceback.print_exc()
        exp.update(status="error", message=str(exc)[:400])
    save(job)


@app.post("/api/jobs/{job_id}/export")
def export_clip(job_id: str, req: ExportRequest):
    job = get_job(job_id)
    if job["status"] != "ready":
        raise HTTPException(409, "העבודה עדיין לא מוכנה")
    total = job.get("duration") or 0
    if req.end <= req.start or req.end - req.start > 600 or req.start > total:
        raise HTTPException(400, "טווח זמנים לא תקין")
    req.end = min(req.end, total)
    exp_id = f"short_{req.clip_id + 1}_{uuid.uuid4().hex[:6]}"
    job["exports"][exp_id] = {"status": "queued", "progress": 0.0,
                              "clip_id": req.clip_id}
    threading.Thread(target=run_export, args=(job, exp_id, req), daemon=True).start()
    return {"export_id": exp_id}


@app.get("/api/jobs/{job_id}/export/{exp_id}")
def export_status(job_id: str, exp_id: str):
    exp = get_job(job_id)["exports"].get(exp_id)
    if not exp:
        raise HTTPException(404, "ייצוא לא נמצא")
    return exp


@app.get("/api/jobs/{job_id}/export/{exp_id}/download")
def export_download(job_id: str, exp_id: str):
    job = get_job(job_id)
    if exp_id not in job["exports"]:
        raise HTTPException(404, "ייצוא לא נמצא")
    f = job_dir(job_id) / f"{exp_id}.mp4"
    if not f.exists():
        raise HTTPException(404, "הקובץ לא נמצא")
    return FileResponse(f, media_type="video/mp4", filename=f"{exp_id}.mp4")


@app.get("/api/fonts")
def fonts():
    return JSONResponse(list(subtitles.load_fonts().values()))


@app.get("/api/defaults")
def defaults():
    return {"style": subtitles.DEFAULT_STYLE,
            "models": list(transcribe.MODELS.keys())}


app.mount("/fonts", StaticFiles(directory=ROOT / "fonts"), name="fonts")
app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="static")
