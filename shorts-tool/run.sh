#!/usr/bin/env bash
# Shorts Studio - install on first run, then start the local server.
#   ./run.sh         this computer only
#   ./run.sh phone   also reachable from phones on the same Wi-Fi (access code)
set -e
cd "$(dirname "$0")"

command -v ffmpeg >/dev/null || { echo "חסר ffmpeg. התקנה: https://ffmpeg.org/download.html (Mac: brew install ffmpeg)"; exit 1; }
PY=$(command -v python3 || command -v python) || { echo "חסר Python 3.10+ : https://www.python.org/downloads/"; exit 1; }

[ -d .venv ] || "$PY" -m venv .venv
if ! .venv/bin/python -c "import fastapi, uvicorn, yt_dlp, faster_whisper, segno, multipart" 2>/dev/null; then
  echo "מתקין רכיבים - זה לוקח כמה דקות..."
  .venv/bin/python -m pip install -q --upgrade pip
  .venv/bin/python -m pip install -q -r requirements.txt
fi

ARGS=()
[ "$1" = "phone" ] && ARGS+=(--phone)
exec .venv/bin/python -m app.serve "${ARGS[@]}"
