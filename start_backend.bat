@echo off
title RAG Backend FastAPI - Port 8002
REM ---- This is start_backend.bat (ASCII-only filename) ----
setlocal

cd /d "%~dp0backend"
if errorlevel 1 (
  echo [ERROR] Cannot chdir to backend subfolder. Path: %~dp0backend
  goto ENDERR
)

echo [INFO] Working dir: %CD%
echo --------------------------------------------------

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] python.exe not found in PATH. Install Python 3.10+ first.
  goto ENDERR
)

REM 1. Create venv if missing
if not exist "venv\Scripts\activate.bat" (
  echo [1/3] Creating virtual environment (venv) ...
  python -m venv venv
  if errorlevel 1 goto ENDERR
  echo       venv created.
) else (
  echo [1/3] venv ready.
)
echo.

REM 2. Activate venv and install missing deps if any
if not exist "venv\Scripts\activate.bat" (
  echo [ERROR] venv activation script missing.
  goto ENDERR
)
call "venv\Scripts\activate.bat"

python -c "import langchain" >nul 2>nul
if errorlevel 1 (
  echo [2/3] Installing dependencies via pip install -r requirements.txt ...
  echo       (5-15 min on first run)
  python -m pip install --upgrade pip >nul
  pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] pip install FAILED.
    goto ENDERR
  )
  echo       Dependencies installed.
) else (
  echo [2/3] Dependencies ready.
)
echo.

REM 3. Start uvicorn
echo [3/3] Starting FastAPI backend server (port 8002) ...
echo       Swagger docs    : http://localhost:8002/docs
echo       Health endpoint : http://localhost:8002/api/health
echo       To stop         : Ctrl + C
echo ============================================================
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

echo.
echo [INFO] Backend process exited (code %ERRORLEVEL%).
goto ENDOK

:ENDERR
echo.
echo [SCRIPT ENDED WITH ERROR - code %ERRORLEVEL%]
echo Take a screenshot if unsure, then press any key to close.
pause >nul
exit /b 1

:ENDOK
echo.
echo Press any key to close this window.
pause >nul
exit /b 0
