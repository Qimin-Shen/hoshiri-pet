@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo [首次运行] 正在创建虚拟环境...
    python -m venv .venv
    echo [首次运行] 正在安装依赖（清华镜像）...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple -q
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple -q
)

start "" ".venv\Scripts\pythonw.exe" "src\main.py"
