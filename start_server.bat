@echo off
cd /d "%~dp0"
echo 正在启动资源搜索后端...
call "C:\Users\X\anaconda3\python.exe" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
pause
