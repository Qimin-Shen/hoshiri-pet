# 打包成免安装 exe（onedir，启动快）
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$py = ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "缺少虚拟环境，先运行 run.bat 安装依赖" -ForegroundColor Red
    exit 1
}

Write-Host "清理旧构建..." -ForegroundColor Cyan
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

Write-Host "开始打包..." -ForegroundColor Cyan
& $py -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name HoshiriPet `
    --icon "assets\out\app.ico" `
    --add-data "assets/out;assets/out" `
    --paths src `
    --hidden-import memory `
    --hidden-import environment `
    --hidden-import ui.memories `
    --exclude-module PySide6.QtWebEngineCore `
    --exclude-module PySide6.QtWebEngineWidgets `
    --exclude-module PySide6.QtWebChannel `
    --exclude-module PySide6.Qt3DCore `
    --exclude-module PySide6.QtMultimedia `
    --exclude-module PySide6.QtQuick `
    --exclude-module PySide6.QtQml `
    --exclude-module tkinter `
    "src\main.py"

if ($LASTEXITCODE -ne 0) {
    Write-Host "打包失败" -ForegroundColor Red
    exit 1
}

$exe = "dist\HoshiriPet\HoshiriPet.exe"
$size = [math]::Round(((Get-ChildItem dist\HoshiriPet -Recurse -File | Measure-Object Length -Sum).Sum / 1MB), 1)
Write-Host "完成：$exe（$size MB）" -ForegroundColor Green
