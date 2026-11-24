# Cherm Windows PowerShell Installer
# Usage:
#   irm https://raw.githubusercontent.com/subhajit-io/Cherm/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

$repo = "subhajit-io/Cherm"
$installDir = "$HOME\.cherm"
$binDir = "$HOME\.cherm\bin"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Cherm Windows Installer" -ForegroundColor Cyan
Write-Host "  Static Architecture & Code Inspection Suite" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

if (!(Test-Path $binDir)) {
    New-Item -ItemType Directory -Force -Path $binDir | Out-Null
}

$releaseUrl = "https://github.com/$repo/releases/latest/download/Cherm.exe"
$exePath = Join-Path $binDir "Cherm.exe"

$downloaded = $false
try {
    Write-Host "[*] Downloading precompiled Cherm.exe from latest release..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $releaseUrl -OutFile $exePath -UseBasicParsing
    $downloaded = $true
    Write-Host "[+] Downloaded Cherm.exe to $exePath" -ForegroundColor Green
} catch {
    Write-Host "[!] Precompiled release binary not reachable, setting up distribution package..." -ForegroundColor Yellow
}

if (-not $downloaded) {
    $rawBase = "https://raw.githubusercontent.com/$repo/main/check-in-terminal"
    $files = @("cherm.py", "cherm_cli.py", "cherm_gui.py", "cherm_bridge.py", "ml_scanner.py", "cherm_mcp.py", "cherm_commands.json", "cherm_mindmap.html")
    foreach ($file in $files) {
        Write-Host "    -> Fetching $file..." -ForegroundColor Gray
        Invoke-WebRequest -Uri "$rawBase/$file" -OutFile (Join-Path $installDir $file) -UseBasicParsing
    }
    
    # Create batch wrapper in bin directory
    $cmdContent = "@echo off`r`npython `"$installDir\cherm.py`" %*"
    Set-Content -Path (Join-Path $binDir "cherm.cmd") -Value $cmdContent
    Set-Content -Path (Join-Path $binDir "Cherm.cmd") -Value $cmdContent
    Write-Host "[+] Created wrapper at $binDir\cherm.cmd" -ForegroundColor Green
}

# Add $binDir to User Environment PATH if not already present
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$binDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$binDir", "User")
    $env:Path += ";$binDir"
    Write-Host "[+] Added $binDir to User PATH environment variable." -ForegroundColor Green
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Cherm installation complete!" -ForegroundColor Green
Write-Host "  Open a new terminal and run: cherm --help" -ForegroundColor Green
Write-Host "  Launch web dashboard: cherm web" -ForegroundColor Green
Write-Host "  Launch terminal companion: cherm gui" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
