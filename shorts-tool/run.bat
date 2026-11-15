@echo off
chcp 65001 >nul
cd /d "%~dp0"

where ffmpeg >nul 2>nul || (echo Missing ffmpeg. Install with: winget install Gyan.FFmpeg & pause & exit /b 1)
where python >nul 2>nul || (echo Missing Python 3.10+. Install from https://www.python.org/downloads/ & pause & exit /b 1)

if not exist .venv (
  echo First run - installing, this takes a few minutes...
  python -m venv .venv || (pause & exit /b 1)
  .venv\Scripts\python -m pip install -q --upgrade pip
  .venv\Scripts\python -m pip install -q -r requirements.txt || (pause & exit /b 1)
)

if "%PORT%"=="" set PORT=8000
echo Shorts Studio is running at http://localhost:%PORT%  (Ctrl+C to stop)
start "" http://localhost:%PORT%
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port %PORT%
pause
