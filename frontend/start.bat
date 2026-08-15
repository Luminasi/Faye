@echo off
chcp 65001 >nul
cd /d %~dp0

if not exist node_modules (
  echo [INFO] 首次运行，正在安装前端依赖...
  call npm install
)

echo 启动前端开发服务器：http://localhost:5173
echo 按 Ctrl+C 停止
echo.

call npm run dev
pause
