@echo off
title RAG Frontend Vue3 Vite - Port 5173
REM ---- This is start_frontend.bat (ASCII-only filename) ----
setlocal

cd /d "%~dp0frontend"
if errorlevel 1 (
  echo [ERROR] Cannot chdir to frontend subfolder. Path: %~dp0frontend
  goto ENDERR
)
echo [INFO] Working dir: %CD%
echo --------------------------------------------------

where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] node.exe not found in PATH. Install Node.js 18+ first.
  echo         Download: https://nodejs.org/
  goto ENDERR
)

REM 1. npm install on first run
if not exist "node_modules" (
  echo [1/2] Running npm install (first run, takes 2-5 min) ...
  call npm install
  if errorlevel 1 (
    echo [ERROR] npm install FAILED.
    goto ENDERR
  )
  echo       npm install finished.
) else (
  echo [1/2] node_modules ready.
)
echo.

REM 2. Start vite
echo [2/2] Starting Vite dev server (port 5173) ...
echo       Visit page    : http://localhost:5173
echo       Admin login   : admin / 123456
echo       To stop       : Ctrl + C
echo ============================================================
call npm run dev

echo.
echo [INFO] Frontend process exited (code %ERRORLEVEL%).
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
