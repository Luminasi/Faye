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

REM 2. Activate venv and ensure ALL deps match requirements.txt (ALWAYS re-check so
REM    version bumps like bcrypt 3.x->4.x are picked up automatically)
if not exist "venv\Scripts\activate.bat" (
  echo [ERROR] venv activation script missing.
  goto ENDERR
)
call "venv\Scripts\activate.bat"

echo [2/3] Checking dependencies (skip install if already satisfied) ...
python -c "import langchain, langchain_openai, langchain_ollama, langchain_community, chromadb, bcrypt, tenacity, python_jose" >nul 2>nul
if not errorlevel 1 (
  echo       Dependencies ready. (skip pip install)
) else (
  echo       Installing dependencies via pip install -r requirements.txt ...
  echo       (First run may take 5-15 min; later runs are skipped.)
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo.
    echo [ERROR] pip install FAILED.
    echo.
    echo [HINT] If you see a dependency conflict over and over:
    echo        1. Close this window.
    echo        2. Delete the folder:  F:\LangchainRAG\backend\venv
    echo        3. Re-run start_backend.bat  (it will rebuild a 100%% clean venv
    echo           with no leftover old bcrypt/passlib packages to confuse pip).
    echo.
    goto ENDERR
  )
  echo       Dependencies installed.
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
