@echo off
title RAG Frontend Vue3 Vite - Port 5173
setlocal

cd /d "%~dp0frontend"
echo [INFO] Working dir: %CD%
echo --------------------------------------------------

REM ---- 0. Check Node.js ----
where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] node.exe not found. Install Node.js 18+ and add to PATH first.
  echo         Download: https://nodejs.org/
  echo.
  pause
  exit /b 1
)

REM ---- 1. npm install on first run ----
if not exist "node_modules" (
  echo [1/2] node_modules not found. Running npm install ...
  echo       (Takes 2-5 minutes on first run)
  call npm install
  if errorlevel 1 (
    echo.
    echo [ERROR] npm install failed. Please take a screenshot of this output.
    pause
    exit /b 1
  )
  echo       npm install finished.
  echo.
) else (
  echo [1/2] node_modules ready.
  echo.
)

REM ---- 2. Start Vite dev server ----
echo [2/2] Starting Vite frontend dev server ...
echo       Visit URL     : http://localhost:5173
echo       Admin account : admin / 123456
echo       Stop server   : Ctrl+C
echo ============================================================
call npm run dev

echo.
echo Frontend exited.
pause
