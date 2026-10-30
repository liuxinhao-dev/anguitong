# 一键装环境（Windows PowerShell）
# 用法：powershell -ExecutionPolicy Bypass -File setup.ps1
# 先读一遍再跑，不要直接双击。

$ErrorActionPreference = "Stop"
$mirror = "https://pypi.tuna.tsinghua.edu.cn/simple"

Write-Host "`n[1/4] 检查 Python 3.12" -ForegroundColor Cyan
$ver = & py -3.12 --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "没找到 Python 3.12。请先安装：https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}
Write-Host "     $ver"

Write-Host "`n[2/4] 创建虚拟环境 .venv（不污染系统 Python）" -ForegroundColor Cyan
if (-not (Test-Path ".venv")) {
    & py -3.12 -m venv .venv
    Write-Host "     已创建"
} else {
    Write-Host "     已存在，跳过"
}
$py = Join-Path (Get-Location) ".venv\Scripts\python.exe"

Write-Host "`n[3/4] 安装依赖（走清华镜像，约 1-2 GB，耐心等）" -ForegroundColor Cyan
& $py -m pip install --upgrade pip --index-url $mirror -q
& $py -m pip install -r requirements.txt --index-url $mirror --timeout 120
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n安装失败。换成阿里源再试：" -ForegroundColor Yellow
    Write-Host "  & `"$py`" -m pip install -r requirements.txt --index-url https://mirrors.aliyun.com/pypi/simple/"
    exit 1
}

Write-Host "`n[4/4] 准备 .env" -ForegroundColor Cyan
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "     已从 .env.example 生成 .env —— 现在去填两个 key" -ForegroundColor Yellow
} else {
    Write-Host "     .env 已存在，跳过"
}

Write-Host "`n完成。接下来的顺序：" -ForegroundColor Green
Write-Host "  1) 编辑 .env 填入 DEEPSEEK_API_KEY 和 EMBED_API_KEY"
Write-Host "  2) 把 PDF 放进 data\"
Write-Host "  3) & `"$py`" check_env.py"
Write-Host "  4) & `"$py`" ingest.py"
Write-Host "  5) & `"$py`" -m streamlit run app.py"
Write-Host ""
