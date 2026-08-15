# start.ps1 - Backend dev server (English only to avoid encoding issues)
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
  Write-Host "[ERROR] venv not found, run .\setup.ps1 first" -ForegroundColor Red
  pause
  exit 1
}

& ".\venv\Scripts\Activate.ps1"

Write-Host "FastAPI backend: http://localhost:8000" -ForegroundColor Green
Write-Host "Swagger docs:    http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "Stop: Ctrl+C" -ForegroundColor Gray
Write-Host ""

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
