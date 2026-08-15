# setup.ps1 - Backend first-time setup (English only to avoid PS5 GBK encoding issues)
Write-Host "[1/3] Check Python..." -ForegroundColor Cyan
python --version
if ($LASTEXITCODE -ne 0) {
  Write-Host "[ERROR] python not found, install Python 3.10+" -ForegroundColor Red
  pause
  exit 1
}

Write-Host ""
Write-Host "[2/3] Create venv (if not exists)..." -ForegroundColor Cyan
if (-not (Test-Path "venv")) {
  python -m venv venv
  if ($LASTEXITCODE -ne 0) { Write-Host "venv create failed" -ForegroundColor Red; pause; exit 1 }
}

Write-Host ""
Write-Host "[3/3] pip install -r requirements.txt ..." -ForegroundColor Cyan
& ".\venv\Scripts\Activate.ps1"
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "pip install failed" -ForegroundColor Red; pause; exit 1 }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Backend env ready." -ForegroundColor Green
Write-Host "  [REQUIRED] Ollama must be running with models pulled:" -ForegroundColor Yellow
Write-Host "      ollama pull qwen2.5:7b"
Write-Host "      ollama pull nomic-embed-text"
Write-Host ""
Write-Host "  Start backend:      .\start.ps1"
Write-Host "  Import demo data:   .\venv\Scripts\Activate.ps1 ; python seed_demo_data.py"
Write-Host "============================================================" -ForegroundColor Green
pause
