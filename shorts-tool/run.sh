#!/usr/bin/env bash
# Shorts Studio - install on first run, then start the local server.
set -e
cd "$(dirname "$0")"

command -v ffmpeg >/dev/null || { echo "חסר ffmpeg. התקנה: https://ffmpeg.org/download.html (Mac: brew install ffmpeg)"; exit 1; }
PY=$(command -v python3 || command -v python) || { echo "חסר Python 3.10+ : https://www.python.org/downloads/"; exit 1; }

if [ ! -d .venv ]; then
  echo "התקנה ראשונה - זה לוקח כמה דקות..."
  "$PY" -m venv .venv
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt
fi

PORT="${PORT:-8000}"
URL="http://localhost:$PORT"
echo "Shorts Studio פועל בכתובת $URL  (לעצירה: Ctrl+C)"
( sleep 2; (command -v xdg-open >/dev/null && xdg-open "$URL") || (command -v open >/dev/null && open "$URL") || true ) >/dev/null 2>&1 &
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
