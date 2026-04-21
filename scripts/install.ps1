# AgentRun CLI installer for Windows (PowerShell 5+).
#
# Usage:
#   irm https://raw.githubusercontent.com/Serverless-Devs/agentrun-cli/main/scripts/install.ps1 | iex
#
# Environment overrides:
#   AGENTRUN_VERSION   Pin to a specific version (e.g. v0.1.0). Default: latest release.
#   AGENTRUN_INSTALL   Install directory. Default: $env:LOCALAPPDATA\Programs\agentrun
#   AGENTRUN_REPO      owner/repo slug. Default: Serverless-Devs/agentrun-cli

#Requires -Version 5.0
$ErrorActionPreference = 'Stop'

function Write-Info($msg) { Write-Host "==> $msg" -ForegroundColor Blue }
function Write-Warn($msg) { Write-Host "warn: $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "error: $msg" -ForegroundColor Red; exit 1 }

# ---------- config ----------
$Repo       = if ($env:AGENTRUN_REPO)    { $env:AGENTRUN_REPO }    else { 'Serverless-Devs/agentrun-cli' }
$InstallDir = if ($env:AGENTRUN_INSTALL) { $env:AGENTRUN_INSTALL } else { Join-Path $env:LOCALAPPDATA 'Programs\agentrun' }
$Version    = $env:AGENTRUN_VERSION

# ---------- detect arch ----------
$arch = (Get-CimInstance Win32_OperatingSystem).OSArchitecture
switch -Wildcard ($arch) {
    '64-bit*'  { $Target = 'windows-amd64'; break }
    'ARM 64*'  { Write-Err "Windows ARM64 is not yet published. Track progress at https://github.com/$Repo/issues." }
    default    { Write-Err "Unsupported architecture: $arch" }
}
Write-Info "Detected target: $Target"

# ---------- resolve version ----------
if (-not $Version) {
    Write-Info "Resolving latest release from github.com/$Repo"
    try {
        $rel = Invoke-RestMethod -UseBasicParsing -Uri "https://api.github.com/repos/$Repo/releases/latest" -Headers @{ 'User-Agent' = 'agentrun-installer' }
        $Version = $rel.tag_name
    } catch {
        Write-Err "could not resolve latest release tag: $($_.Exception.Message)"
    }
}
Write-Info "Version: $Version"

$VersionNum = $Version -replace '^v',''
$Asset      = "agentrun-$VersionNum-$Target.zip"
$Url        = "https://github.com/$Repo/releases/download/$Version/$Asset"
$ShaUrl     = "$Url.sha256"

# ---------- download ----------
$Tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("agentrun-install-" + [guid]::NewGuid())
New-Item -ItemType Directory -Force -Path $Tmp | Out-Null
try {
    $ZipPath = Join-Path $Tmp $Asset
    $ShaPath = "$ZipPath.sha256"

    Write-Info "Downloading $Asset"
    Invoke-WebRequest -UseBasicParsing -Uri $Url    -OutFile $ZipPath
    Invoke-WebRequest -UseBasicParsing -Uri $ShaUrl -OutFile $ShaPath

    # ---------- verify checksum ----------
    $expected = (Get-Content $ShaPath -Raw).Trim().Split()[0].ToLower()
    $actual   = (Get-FileHash $ZipPath -Algorithm SHA256).Hash.ToLower()
    if ($expected -ne $actual) {
        Write-Err "checksum mismatch (expected $expected, got $actual)"
    }
    Write-Info "Checksum OK"

    # ---------- extract & install ----------
    Expand-Archive -Path $ZipPath -DestinationPath $Tmp -Force
    $Exe = Join-Path $Tmp 'agentrun.exe'
    if (-not (Test-Path $Exe)) {
        Write-Err "archive did not contain 'agentrun.exe'"
    }

    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    $Dest = Join-Path $InstallDir 'agentrun.exe'
    Move-Item -Force -Path $Exe -Destination $Dest

    # Also drop an `ar.exe` alongside so the short alias works.
    $ArDest = Join-Path $InstallDir 'ar.exe'
    Copy-Item -Force -Path $Dest -Destination $ArDest

    Write-Info "Installed agentrun.exe → $Dest"

    # ---------- PATH hint ----------
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if (-not ($userPath -split ';' | Where-Object { $_ -eq $InstallDir })) {
        Write-Warn "$InstallDir is not in your user PATH."
        Write-Host ""
        Write-Host "  Add it with:"
        Write-Host "    [Environment]::SetEnvironmentVariable('Path', `"$InstallDir;`$env:Path`", 'User')"
        Write-Host ""
        Write-Host "  Then open a new terminal and run: agentrun --version"
    } else {
        Write-Info "Run: agentrun --version"
    }
}
finally {
    Remove-Item -Recurse -Force -Path $Tmp -ErrorAction SilentlyContinue
}
