@echo off
chcp 65001 >nul
cd /d %~dp0

if not exist venv\Scripts\activate.bat (
  echo [错误] 未找到 venv 虚拟环境，请先运行 setup.bat
  pause
  exit /b 1
)
call venv\Scripts\activate.bat

echo 启动 FastAPI 后端： http://localhost:8000
echo    Swagger 文档：   http://localhost:8000/docs
echo    按 Ctrl+C 停止
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
