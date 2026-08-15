# start.ps1 - Frontend dev server (English only)
if (-not (Test-Path "node_modules")) {
  Write-Host "[INFO] first run: npm install..." -ForegroundColor Cyan
  npm install
}

Write-Host "Frontend dev: http://localhost:5173" -ForegroundColor Green
Write-Host "Stop: Ctrl+C" -ForegroundColor Gray
Write-Host ""

npm run dev
pause
