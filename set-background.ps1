param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Path,
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"
$userDir = Join-Path $env:APPDATA "YandexMusic"
$wallDir = Join-Path $userDir "wallpapers"
$cacheDir = Join-Path $env:LOCALAPPDATA "YaMusicXti"
$jsonPath = Join-Path $cacheDir "custom-background.json"
$appDir = Join-Path $env:LOCALAPPDATA "Programs\YandexMusic"

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

function Get-MusicExe {
    $candidates = @(Get-ChildItem -LiteralPath $appDir -Filter *.exe -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -notlike "Uninstall*" })
    if (-not $candidates.Count) { throw "Yandex Music executable not found in $appDir" }
    $main = $candidates | Where-Object { $_.Name -like "*Музыка*" } | Select-Object -First 1
    if (-not $main) { $main = $candidates | Where-Object { $_.Name -like "*YandexMusic*" } | Select-Object -First 1 }
    if (-not $main) { $main = $candidates | Select-Object -First 1 }
    return $main.FullName
}

if (-not (Test-Path -LiteralPath $Path)) { throw "Файл не найден: $Path" }
$src = (Resolve-Path -LiteralPath $Path).Path
$ext = [IO.Path]::GetExtension($src).ToLower()

$allowed = @(".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp",
             ".mp4", ".webm", ".mov", ".m4v", ".ogv")
if ($allowed -notcontains $ext) {
    throw "Неподдерживаемый формат: $ext. Можно: $($allowed -join ', ')"
}

$size = (Get-Item -LiteralPath $src).Length
if ($size -gt 2GB) { throw ("Файл слишком большой: {0:N1} МБ (максимум 2 ГБ)" -f ($size / 1MB)) }
if ($size -le 0) { throw "Файл пустой" }

New-Item -ItemType Directory -Force -Path $userDir | Out-Null
New-Item -ItemType Directory -Force -Path $wallDir | Out-Null
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null

# Старая раскладка: фоны из корня профиля переезжают в wallpapers.
Get-ChildItem $userDir -File -ErrorAction SilentlyContinue | Where-Object {
    $_.Extension.ToLower() -in @(".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp",
                                 ".mp4", ".webm", ".mov", ".m4v", ".ogv", ".zip", ".html", ".htm")
} | ForEach-Object {
    $dst = Join-Path $wallDir $_.Name
    if (Test-Path -LiteralPath $dst) {
        Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
    } else {
        Move-Item -LiteralPath $_.FullName -Destination $dst -Force -ErrorAction SilentlyContinue
    }
}

$fileName = "custom-background" + $ext
$dst = Join-Path $wallDir $fileName

if (-not ($src -eq $dst)) {
    $tmp = Join-Path $wallDir (".custom-background.tmp" + $ext)
    Copy-Item -LiteralPath $src -Destination $tmp -Force
    Move-Item -LiteralPath $tmp -Destination $dst -Force
}

# Убираем прежние фоны только после успешной замены.
Get-ChildItem -LiteralPath $wallDir -Filter "custom-background*" -File -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -ne $dst } |
    Remove-Item -Force -ErrorAction SilentlyContinue

# Конфиг: свой фон вместо адаптивного.
$cfg = $null
if (Test-Path -LiteralPath $jsonPath) {
    try {
        $cfg = Get-Content -LiteralPath $jsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($cfg -isnot [pscustomobject]) { $cfg = $null }
    } catch {
        Write-Host "Конфиг повреждён, создаю новый."
    }
}
if (-not $cfg) {
    $cfg = [pscustomobject]@{
        adaptive = $false; file = ""; blur = 0; brightness = 1
        dim = 0.25; vignette = 0; navbarDim = 0.35
        playerTransparency = 0.48; playerBlur = 20; playerSaturate = 1.15
        fade = 600; poll = 1500
    }
}
$cfg.file = $fileName
$cfg.web = ""
$cfg.adaptive = $false
$tmpJson = "$jsonPath.tmp"
[IO.File]::WriteAllText($tmpJson, ($cfg | ConvertTo-Json -Depth 5), (New-Object System.Text.UTF8Encoding($false)))
Move-Item -LiteralPath $tmpJson -Destination $jsonPath -Force

Write-Host ("Установлен фон: {0} ({1:N1} МБ)" -f $fileName, ($size / 1MB))

if (-not $NoRestart) {
    $exe = Get-MusicExe
    Write-Host "Перезапускаю Яндекс Музыку..."
    for ($i = 0; $i -lt 40; $i++) {
        $procs = @(Get-MusicProcesses)
        if (-not $procs.Count) { break }
        $procs | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 400
    }
    Start-Sleep -Milliseconds 600
    for ($i = 0; $i -lt 40; $i++) {
        try {
            $fs = [IO.File]::Open($exe, 'Open', 'ReadWrite', 'None')
            $fs.Close()
            break
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }
    Start-Process -FilePath $exe
} else {
    Write-Host "Нажми Ctrl+R в окне приложения, чтобы применить."
}
