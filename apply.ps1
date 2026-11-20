param(
    [string]$Image,
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
    $deadline = (Get-Date).AddSeconds(30)
    do {
        $procs = @(Get-MusicProcesses)
        foreach ($p in $procs) {
            try { $p.CloseMainWindow() | Out-Null } catch {}
        }
        if ($procs.Count) {
            $procs | Stop-Process -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
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
    throw "Python 3 not found. Install Python or edit this script."
}

if (-not $AppDir) { $AppDir = Join-Path $env:LOCALAPPDATA "Programs\YandexMusic" }
if (-not (Test-Path -LiteralPath $AppDir)) { throw "Yandex Music not found: $AppDir" }
$appDir = (Resolve-Path -LiteralPath $AppDir).Path
$asar = Join-Path $appDir "resources\app.asar"
if (-not (Test-Path -LiteralPath $asar)) { throw "Yandex Music resources not found: $asar" }

$exe = Get-MusicExe
$userDir = Join-Path $env:APPDATA "YandexMusic"
$wallDir = Join-Path $userDir "wallpapers"
$cacheDir = Join-Path $env:LOCALAPPDATA "YaMusicXti"
$py = Find-Python $Python

Write-Host "Stopping Yandex Music..."
Stop-MusicApp
Start-Sleep -Milliseconds 600

Write-Host "Patching executable (fuse)..."
& $py (Join-Path $root "tools\fuse_flip.py") $exe disable
if ($LASTEXITCODE -ne 0) { throw "fuse patch failed" }

Write-Host "Patching app.asar..."
& $py (Join-Path $root "tools\asar_patch.py") apply --asar $asar
if ($LASTEXITCODE -ne 0) { throw "asar patch failed" }

New-Item -ItemType Directory -Force -Path $userDir | Out-Null
New-Item -ItemType Directory -Force -Path $wallDir | Out-Null
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null

# --- Старая раскладка: фоны из корня профиля переезжают в wallpapers,
#     служебные файлы — в кэш. Так папка с обоями остаётся чистой. ---
$mediaExt = @(".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp",
              ".mp4", ".webm", ".mov", ".m4v", ".ogv", ".zip", ".html", ".htm")
$movedCount = 0
Get-ChildItem $userDir -File -ErrorAction SilentlyContinue | ForEach-Object {
    $ext = $_.Extension.ToLower()
    $isMedia = $mediaExt -contains $ext
    $isMod = ($_.Name -like "custom-background.*") -or ($_.Name -like "custom-background-*") -or ($_.Name -like ".custom-background*")
    if (-not $isMedia -and -not $isMod) { return }
    $dstDir = if ($isMedia) { $wallDir } else { $cacheDir }
    $dst = Join-Path $dstDir $_.Name
    if (Test-Path -LiteralPath $dst) {
        Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
    } else {
        Move-Item -LiteralPath $_.FullName -Destination $dst -Force -ErrorAction SilentlyContinue
    }
    $script:movedCount++
}
if ($movedCount -gt 0) { Write-Host "Moved $movedCount file(s): wallpapers -> wallpapers, service -> cache" }
foreach ($legacyDir in @("web-wallpaper", "thumbs")) {
    $p = Join-Path $userDir $legacyDir
    if (Test-Path -LiteralPath $p) {
        Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# --- CSS: старую версию (v1) убираем в .bak, чтобы не мешала ---
$cssDst = Join-Path $cacheDir "custom-background.css"
if (Test-Path $cssDst) {
    $cssText = Get-Content $cssDst -Raw -Encoding UTF8
    if ($cssText -notmatch "v2") {
        Move-Item $cssDst "$cssDst.v1.bak" -Force
        Write-Host "Old CSS saved as custom-background.css.v1.bak"
    }
}
if (-not (Test-Path $cssDst)) {
    Copy-Item (Join-Path $root "custom-background.css") $cssDst
    Write-Host "Installed custom-background.css"
}

# --- JSON-конфиг ---
$jsonDst = Join-Path $cacheDir "custom-background.json"
if (-not (Test-Path $jsonDst)) {
    Copy-Item (Join-Path $root "custom-background.json") $jsonDst
    Write-Host "Installed custom-background.json"
}

# --- Старый отдельный GUI и токен больше не нужны: панель встроена в приложение,
#     а токен живёт только в памяти процесса Музыки. ---
$legacyGui = Join-Path $userDir "YMBackground.ps1"
if (Test-Path -LiteralPath $legacyGui) {
    Remove-Item -LiteralPath $legacyGui -Force -ErrorAction SilentlyContinue
    Write-Host "Removed legacy YMBackground.ps1"
}
$legacyToken = Join-Path $userDir "ymbg.token"
if (Test-Path -LiteralPath $legacyToken) {
    Remove-Item -LiteralPath $legacyToken -Force -ErrorAction SilentlyContinue
    Write-Host "Removed legacy token file"
}

# --- Картинка ---
$images = @(Get-ChildItem $wallDir -File -ErrorAction SilentlyContinue |
    Where-Object { $mediaExt -contains $_.Extension.ToLower() -and $_.Name -notlike "*.zip" -and
                   $_.Name -notlike "*.html" -and $_.Name -notlike "*.htm" })

if ($Image) {
    if (-not (Test-Path -LiteralPath $Image)) { throw "Image not found: $Image" }
    $resolved = (Resolve-Path -LiteralPath $Image).Path
    $ext = [IO.Path]::GetExtension($resolved).ToLower()
    $allowedExt = @(".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp",
                    ".mp4", ".webm", ".mov", ".m4v", ".ogv")
    if ($allowedExt -notcontains $ext) { throw "Unsupported image format: $ext" }
    $size = (Get-Item -LiteralPath $resolved).Length
    if ($size -gt 2GB) { throw "Image is larger than 2 GB" }
    $images | Remove-Item -Force -ErrorAction SilentlyContinue
    $fileName = "custom-background" + $ext
    Copy-Item $resolved (Join-Path $wallDir $fileName) -Force
    $cfg = Get-Content $jsonDst -Raw -Encoding UTF8 | ConvertFrom-Json
    $cfg.file = $fileName
    $cfg.web = ""
    $cfg.adaptive = $false
    $jsonText = $cfg | ConvertTo-Json -Depth 5
    $tmpJson = "$jsonDst.tmp"
    [IO.File]::WriteAllText($tmpJson, $jsonText, (New-Object System.Text.UTF8Encoding($false)))
    Move-Item -LiteralPath $tmpJson -Destination $jsonDst -Force
    Write-Host "Image installed: $fileName"
}
elseif ($images.Count -eq 0) {
    $def = Join-Path $root "background.jpg"
    if (Test-Path $def) {
        Copy-Item $def (Join-Path $wallDir "custom-background.jpg") -Force
        $cfg = Get-Content $jsonDst -Raw -Encoding UTF8 | ConvertFrom-Json
        $cfg.file = "custom-background.jpg"
        $cfg.adaptive = $false
        $jsonText = $cfg | ConvertTo-Json -Depth 5
        $tmpJson = "$jsonDst.tmp"
        [IO.File]::WriteAllText($tmpJson, $jsonText, (New-Object System.Text.UTF8Encoding($false)))
        Move-Item -LiteralPath $tmpJson -Destination $jsonDst -Force
        Write-Host "Default background installed"
    }
}

if (-not $NoLaunch) {
    Write-Host "Starting Yandex Music..."
    Start-Process -FilePath $exe
}

Write-Host "Done."
