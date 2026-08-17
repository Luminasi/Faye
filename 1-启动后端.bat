@echo off
title RAG Backend FastAPI - Port 8002
setlocal

cd /d "%~dp0backend"
echo [INFO] Working dir: %CD%
echo --------------------------------------------------

REM ---- 0. Check Python ----
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] python.exe not found. Install Python 3.10+ and add to PATH first.
  echo.
  pause
  exit /b 1
)

REM ---- 1. Auto-create venv on first run ----
if not exist "venv\Scripts\activate.bat" (
  echo [1/3] venv not found. Creating virtual environment ...
  python -m venv venv
  if errorlevel 1 (
    echo [ERROR] Failed to create venv.
    pause
    exit /b 1
  )
  echo       venv created.
  echo.
) else (
  echo [1/3] venv ready.
  echo.
)

REM ---- 2. Activate venv. If langchain package missing -> auto pip install ----
call "venv\Scripts\activate.bat"

python -c "import langchain, langchain_openai, langchain_ollama, langchain_community, chromadb, bcrypt" >nul 2>nul
if errorlevel 1 (
  echo [2/3] Dependencies not installed. Running pip install -r requirements.txt ...
  echo       (Takes 5-15 minutes on first run, please wait)
  echo.
  python -m pip install --upgrade pip >nul
  pip install -r requirements.txt
  if errorlevel 1 (
    echo.
    echo [ERROR] pip install failed. Please take a screenshot of this output.
    pause
    exit /b 1
  )
  echo       Dependencies installed.
  echo.
) else (
  echo [2/3] Dependencies ready.
  echo.
)

REM ---- 3. Start FastAPI with auto reload ----
echo [3/3] Starting FastAPI backend server ...
echo       Swagger docs : http://localhost:8002/docs
echo       Frontend URL  : http://localhost:5173
echo       Stop server   : Ctrl+C
echo ============================================================
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

echo.
echo Backend exited.
pause
