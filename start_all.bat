@echo off
title E-Commerce RAG - Start All Services
REM ---- This is start_all.bat (ASCII-only filename, double-click this) ----
setlocal

cls
echo ============================================================
echo    E-Commerce RAG Knowledge QA System - ONE-CLICK START
echo ============================================================
echo.

REM Ollama quick status check (no parse-heavy logic on purpose)
where ollama >nul 2>nul
if errorlevel 1 (
  echo [WARNING] Ollama NOT found in PATH.
  echo           Download from https://ollama.com/ then ONCE run:
  echo                ollama pull qwen2.5:7b
  echo                ollama pull nomic-embed-text
  echo.
) else (
  echo [OK] Ollama installed.
  echo      (Make sure tray icon is running and models are pulled.)
  echo.
)

echo This script will open TWO console windows:
echo   - Backend FastAPI   on port 8002
echo   - Frontend Vite     on port 5173
echo.
echo FIRST RUN NOTE: installs pip deps + npm deps automatically,
echo                 expect several minutes. Subsequent runs are fast.
echo.
echo Press ANY KEY to launch ...
pause >nul

REM Launch services (call ASCII-only child scripts so no charset issue at all)
start "RAG Backend  :8002"  cmd /k "%~dp0start_backend.bat"
ping -n 3 127.0.0.1 >nul
start "RAG Frontend :5173"  cmd /k "%~dp0start_frontend.bat"

echo.
echo ============================================================
echo   Both services launched.
echo.
echo   Login page          http://localhost:5173
echo   Admin account       admin / 123456
echo   Swagger API docs    http://localhost:8002/docs
echo.
echo   ON FIRST RUN also double-click  seed_demo.bat  AFTER the
echo   backend shows "Application startup complete" to import
echo   8 demo e-commerce documents into the vector database.
echo ============================================================
echo.
echo Press any key to close this launcher window (services keep running).
pause >nul
exit /b 0
