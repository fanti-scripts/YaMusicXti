param(
    [string]$AppDir,
    [string]$Python,
    [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

function Get-MusicProcesses {
    $ids = New-Object System.Collections.Generic.List[int]
    $prefix = $appDir.TrimEnd('\') + '\'
    try {
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
            $_.ProcessId -ne $PID -and (
                ($_.ExecutablePath -and $_.ExecutablePath.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) -or
                ($_.CommandLine -and $_.CommandLine.IndexOf($prefix, [System.StringComparison]::OrdinalIgnoreCase) -ge 0)
            )
        } | ForEach-Object { $ids.Add([int]$_.ProcessId) }
    } catch {}
    Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Id -ne $PID -and (
            ($_.ProcessName -like "*Музыка*") -or ($_.ProcessName -like "YandexMusic*")
        )
    } | ForEach-Object { $ids.Add($_.Id) }
    $ids | Sort-Object -Unique | ForEach-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue }
}

function Stop-MusicApp {
    $deadline = (Get-Date).AddSeconds(25)
    do {
        $procs = @(Get-MusicProcesses)
        foreach ($p in $procs) {
            try { $p.CloseMainWindow() | Out-Null } catch {}
        }
        if ($procs.Count) {
            $procs | Stop-Process -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 400
        }
    } while ($procs.Count -and (Get-Date) -lt $deadline)
    if ($procs.Count) { throw "Yandex Music is still running" }

    $exePath = Get-MusicExe
    for ($i = 0; $i -lt 60; $i++) {
        try {
            $fs = [IO.File]::Open($exePath, 'Open', 'ReadWrite', 'None')
            $fs.Close()
            return
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }
    throw "executable is still locked: $exePath"
}

function Get-MusicExe {
    $candidates = @(Get-ChildItem -LiteralPath $appDir -Filter *.exe -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -notlike "Uninstall*" })
    if (-not $candidates.Count) { throw "Yandex Music executable not found in $appDir" }
    $main = $candidates | Where-Object { $_.Name -like "*Музыка*" } | Select-Object -First 1
    if (-not $main) { $main = $candidates | Where-Object { $_.Name -like "*YandexMusic*" } | Select-Object -First 1 }
    if (-not $main) { $main = $candidates | Select-Object -First 1 }
    return $main.FullName
}

function Find-Python {
    param([string]$Hint)
    if ($Hint) {
        if (Test-Path -LiteralPath $Hint) { return (Resolve-Path -LiteralPath $Hint).Path }
        throw "Python not found: $Hint"
    }
    $bundled = Join-Path $root "python\python.exe"
    if (Test-Path -LiteralPath $bundled) { return $bundled }
    $bundled = Join-Path $root "installer\python\python.exe"
    if (Test-Path -LiteralPath $bundled) { return $bundled }
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $cand = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1
    if ($cand) { return $cand.FullName }
    throw "Python 3 not found."
}

if (-not $AppDir) { $AppDir = Join-Path $env:LOCALAPPDATA "Programs\YandexMusic" }
if (-not (Test-Path -LiteralPath $AppDir)) { throw "Yandex Music not found: $AppDir" }
$appDir = (Resolve-Path -LiteralPath $AppDir).Path
$asar = Join-Path $appDir "resources\app.asar"
if (-not (Test-Path -LiteralPath $asar)) { throw "Yandex Music resources not found: $asar" }

$exe = Get-MusicExe
$userDir = Join-Path $env:APPDATA "YandexMusic"
$py = Find-Python $Python

Write-Host "Stopping Yandex Music..."
Stop-MusicApp
Start-Sleep -Milliseconds 600

Write-Host "Restoring executable..."
& $py (Join-Path $root "tools\fuse_flip.py") $exe restore
if ($LASTEXITCODE -ne 0) { throw "fuse restore failed" }

Write-Host "Restoring app.asar..."
& $py (Join-Path $root "tools\asar_patch.py") restore --asar $asar
if ($LASTEXITCODE -ne 0) { throw "asar restore failed" }

# Старые артефакты мода: токен и отдельный GUI больше не используются.
foreach ($name in @("ymbg.token", "YMBackground.ps1")) {
    $path = Join-Path $userDir $name
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
    }
}

# Служебные файлы мода из корня профиля. Папку wallpapers с фонами не трогаем.
Get-ChildItem $userDir -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "custom-background.*" } |
    Remove-Item -Force -ErrorAction SilentlyContinue
foreach ($sub in @("web-wallpaper", "thumbs")) {
    $p = Join-Path $userDir $sub
    if (Test-Path -LiteralPath $p) {
        Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Кэш мода: превью, распакованные из архивов фоны и HTML-обои.
$modCache = Join-Path $env:LOCALAPPDATA "YaMusicXti"
if (Test-Path -LiteralPath $modCache) {
    Remove-Item -LiteralPath $modCache -Recurse -Force -ErrorAction SilentlyContinue
}

if (-not $NoLaunch) {
    Write-Host "Starting Yandex Music..."
    Start-Process -FilePath $exe
}

Write-Host "Restored original app."
