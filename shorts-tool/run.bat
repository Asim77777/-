@echo off
chcp 65001 >nul
cd /d "%~dp0"

where ffmpeg >nul 2>nul || (echo Missing ffmpeg. Install with: winget install Gyan.FFmpeg & pause & exit /b 1)
where python >nul 2>nul || (echo Missing Python 3.10+. Install from https://www.python.org/downloads/ & pause & exit /b 1)

if not exist .venv python -m venv .venv || (pause & exit /b 1)
.venv\Scripts\python -c "import fastapi, uvicorn, yt_dlp, faster_whisper, segno, multipart" 2>nul || (
  echo Installing components - this takes a few minutes...
  .venv\Scripts\python -m pip install -q --upgrade pip
  .venv\Scripts\python -m pip install -q -r requirements.txt || (pause & exit /b 1)
)

set ARGS=
if /i "%1"=="phone" set ARGS=--phone
.venv\Scripts\python -m app.serve %ARGS%
pause
