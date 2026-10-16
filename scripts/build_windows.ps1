$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

uv sync --group build
uv run --group build pyinstaller --noconfirm --clean video_down.spec

$Iscc = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
if (-not $Iscc) {
    $Candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    $Iscc = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $Iscc) {
    throw "未找到 Inno Setup 6。请先安装：https://jrsoftware.org/isdl.php"
}

& $Iscc "installer\video_down.iss"
Write-Host "安装包已生成：dist\installer\video_down-Setup.exe"
