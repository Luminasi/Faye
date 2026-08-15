@echo off
title Seed Demo Knowledge Data
setlocal

cd /d "%~dp0backend"
echo [INFO] Working dir: %CD%
echo --------------------------------------------------

if not exist "venv\Scripts\activate.bat" (
  echo [ERROR] venv not found. Double-click the backend launcher (Script #1) first
  echo         (it auto-creates the virtual env and installs all dependencies).
  pause
  exit /b 1
)

call "venv\Scripts\activate.bat"

echo ============================================================
echo  Before running, make sure Ollama is RUNNING (tray icon on)
echo  and required models are already pulled:
echo      ollama pull nomic-embed-text
echo      ollama pull qwen2.5:7b
echo  (If embedding model is missing, vectorization will FAIL.)
echo ============================================================
echo.
echo Press any key to start importing 8 demo e-commerce docs ...
pause >nul

python seed_demo_data.py

echo.
echo --------------------------------------------------
echo Script finished.
echo If you see any [FAIL] lines, take a screenshot and send to me.
pause
