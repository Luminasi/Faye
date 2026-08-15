@echo off
chcp 65001 >nul
setlocal
cd /d %~dp0

echo [1/3] 检查 Python 环境...
python --version
if errorlevel 1 (
  echo [错误] 未检测到 python，请先安装 Python 3.10+
  pause
  exit /b 1
)

echo.
echo [2/3] 创建虚拟环境 venv（如果不存在）...
if not exist venv (
  python -m venv venv
  if errorlevel 1 ( echo 创建虚拟环境失败 & pause & exit /b 1 )
)

call venv\Scripts\activate.bat

echo.
echo [3/3] 安装依赖（requirements.txt）...
pip install -r requirements.txt
if errorlevel 1 ( echo 依赖安装失败 & pause & exit /b 1 )

echo.
echo ============================================================
echo  后端环境准备完成！
echo  【前置条件】确保本地 Ollama 服务正在运行，并且已拉取模型：
echo      ollama pull qwen2.5:7b
echo      ollama pull nomic-embed-text
echo.
echo  启动后端（本窗口保持打开）：
echo      venv\Scripts\activate.bat
echo      python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
echo.
echo  导入电商样例数据（另开一个 backend 终端执行）：
echo      venv\Scripts\activate.bat
echo      python seed_demo_data.py
echo ============================================================
pause
