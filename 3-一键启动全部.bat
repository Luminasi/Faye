@echo off
title E-Commerce RAG - Start All Services
setlocal

cls
echo ============================================================
echo   E-Commerce RAG Knowledge QA System  -  ONE CLICK START
echo ============================================================
echo.

where ollama >nul 2>nul
if errorlevel 1 (
  echo [WARNING] Ollama executable not detected in PATH.
  echo           Install Ollama first. Download: https://ollama.com/
  echo.
  echo           After install, run ONCE in PowerShell:
  echo               ollama pull qwen2.5:7b
  echo               ollama pull nomic-embed-text
  echo.
) else (
  echo [OK] Ollama is installed.
  echo      On FIRST RUN make sure the 2 required models are pulled:
  echo          ollama pull qwen2.5:7b
  echo          ollama pull nomic-embed-text
  echo.
)

echo Will open 2 console windows:
echo   - Backend FastAPI   (port 8002)
echo   - Frontend Vite     (port 5173)
echo.
echo First run is slower because it auto-installs pip deps + npm deps.
echo.
echo Press any key to launch ...
pause >nul

start "RAG Backend  :8002"  cmd /k "%~dp0start_backend.bat"
ping -n 3 127.0.0.1 >nul
start "RAG Frontend :5173"  cmd /k "%~dp0start_frontend.bat"

echo.
echo ============================================================
echo  Both services launched.
echo.
echo    Browser URL:
echo        http://localhost:5173       (Login page)
echo        admin / 123456              (Admin login)
echo        http://localhost:8002/docs  (Backend Swagger docs)
echo.
echo    On FIRST RUN: after services are ready, also run the
echo    import-script (4-...) to populate demo documents into DB.
echo ============================================================
echo.
pause
