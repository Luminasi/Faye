@echo off
title Seed Demo Knowledge Data (8 e-commerce docs)
REM ---- This is seed_demo.bat (ASCII-only filename) ----
setlocal

cd /d "%~dp0backend"
if errorlevel 1 (
  echo [ERROR] Cannot chdir to backend subfolder (path: %~dp0backend)
  goto ENDERR
)
echo [INFO] Working dir: %CD%
echo --------------------------------------------------

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] python.exe not found in PATH.
  goto ENDERR
)

if not exist "venv\Scripts\activate.bat" (
  echo [ERROR] venv missing. Double-click start_backend.bat first (it
  echo         auto-creates venv and installs pip dependencies).
  goto ENDERR
)

call "venv\Scripts\activate.bat"

echo ============================================================
echo  PREREQUISITE CHECK:
echo    - Ollama must be RUNNING (tray icon visible).
echo    - Models already pulled via:
echo         ollama pull nomic-embed-text
echo         ollama pull qwen2.5:7b
echo    - Backend does NOT need to be running for this script.
echo ============================================================
echo.
echo Press ANY KEY to start importing 8 demo e-commerce documents.
echo (This will call Ollama embedding API, may take a few minutes.)
pause >nul

python seed_demo_data.py
set RC=%ERRORLEVEL%

echo.
echo --------------------------------------------------
echo seed_demo_data.py finished with exit code %RC%.
echo.
echo If you see any line starting with [FAIL] above, take
echo a screenshot of that area and send it for support.
echo If every doc shows [OK] ... chunks=XX, you are good.
echo --------------------------------------------------
goto ENDOK

:ENDERR
echo.
echo [SCRIPT ENDED WITH ERROR - code %ERRORLEVEL%]
echo Take a screenshot of this whole window, then press any key.
pause >nul
exit /b 1

:ENDOK
echo.
echo Press any key to close.
pause >nul
exit /b 0
