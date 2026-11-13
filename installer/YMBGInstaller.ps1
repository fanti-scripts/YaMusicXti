param(
    [switch]$NoMutex
)

Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase

$ErrorActionPreference = "Stop"

# --- paths ---------------------------------------------------------------
$script:installerDir = $PSScriptRoot
if ((Split-Path -Leaf $script:installerDir) -ieq "installer") {
    $script:root = Split-Path -Parent $script:installerDir
} else {
    $script:root = $script:installerDir
}
$script:userDir = Join-Path $env:APPDATA "YandexMusic"
$script:version = "1.1.0"

if (-not $NoMutex) {
    $script:mutex = New-Object System.Threading.Mutex -ArgumentList $false, "Local\YMBgInstaller"
    if (-not $script:mutex.WaitOne(0)) { exit }
}

function Get-AppDir {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\YandexMusic"),
        (Join-Path $env:ProgramFiles "YandexMusic")
    )
    $pf86 = ${env:ProgramFiles(x86)}
    if ($pf86) { $candidates += (Join-Path $pf86 "YandexMusic") }
    foreach ($c in $candidates) {
        if (-not $c) { continue }
        $asar = Join-Path $c "resources\app.asar"
        if (Test-Path -LiteralPath $asar) { return $c }
    }
    return $null
}

function Get-AppExe {
    $dir = Get-AppDir
    if (-not $dir) { return $null }
    $candidates = @(Get-ChildItem -LiteralPath $dir -Filter *.exe -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -notlike "Uninstall*" })
    if (-not $candidates.Count) { return $null }
    $main = $candidates | Where-Object { $_.Name -like "*Музыка*" } | Select-Object -First 1
    if (-not $main) { $main = $candidates | Where-Object { $_.Name -like "*YandexMusic*" } | Select-Object -First 1 }
    if (-not $main) { $main = $candidates | Select-Object -First 1 }
    return $main
}

function Get-AppVersion {
    $exe = Get-AppExe
    if (-not $exe) { return $null }
    $v = $exe.VersionInfo.FileVersion
    if (-not $v) { return $null }
    $parts = $v.Split(".")
    if ($parts.Count -ge 3) { return ($parts[0..2] -join ".") }
    return $v
}

function Find-Python {
    $candidates = @(
        (Join-Path $script:root "python\python.exe"),
        (Join-Path $script:installerDir "python\python.exe")
    )
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd) { $candidates += $cmd.Source }
    $local = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1
    if ($local) { $candidates += $local.FullName }
    foreach ($c in $candidates) {
        if ($c -and (Test-Path -LiteralPath $c)) { return (Resolve-Path -LiteralPath $c).Path }
    }
    return $null
}

function Test-AsarPatched {
    $dir = Get-AppDir
    if (-not $dir) { return $false }
    $asar = Join-Path $dir "resources\app.asar"
    if (-not (Test-Path -LiteralPath $asar)) { return $false }
    try {
        $bytes = [IO.File]::ReadAllBytes($asar)
        $text = [Text.Encoding]::ASCII.GetString($bytes)
        return $text.Contains("__ymApplyCustomBackground")
    } catch {
        return $false
    }
}

function Test-HasBackup {
    $dir = Get-AppDir
    if (-not $dir) { return $false }
    $exe = Get-AppExe
    $asar = Join-Path $dir "resources\app.asar"
    return ((Test-Path -LiteralPath ($asar + ".orig")) -or ($exe -and (Test-Path -LiteralPath ($exe.FullName + ".orig"))))
}

# --- XAML ----------------------------------------------------------------
$xaml = @'
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Фон Яндекс Музыки — установщик"
        Height="650" Width="790"
        WindowStyle="None" AllowsTransparency="True" Background="Transparent"
        ResizeMode="NoResize" WindowStartupLocation="CenterScreen"
        FontFamily="Segoe UI" SnapsToDevicePixels="True"
        TextOptions.TextFormattingMode="Display">
  <Window.Resources>
    <Style x:Key="Chrome" TargetType="Button">
      <Setter Property="Background" Value="Transparent"/>
      <Setter Property="Foreground" Value="#a0a0a8"/>
      <Setter Property="BorderThickness" Value="0"/>
      <Setter Property="Width" Value="38"/>
      <Setter Property="Height" Value="30"/>
      <Setter Property="FontSize" Value="15"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="b" Background="{TemplateBinding Background}" CornerRadius="8">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="b" Property="Background" Value="#26262b"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <Style x:Key="Primary" TargetType="Button">
      <Setter Property="Background" Value="#ffcc00"/>
      <Setter Property="Foreground" Value="#141414"/>
      <Setter Property="FontSize" Value="14"/>
      <Setter Property="FontWeight" Value="SemiBold"/>
      <Setter Property="Height" Value="44"/>
      <Setter Property="Padding" Value="22,0"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="b" Background="{TemplateBinding Background}" CornerRadius="11">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="b" Property="Background" Value="#ffd633"/>
              </Trigger>
              <Trigger Property="IsEnabled" Value="False">
                <Setter TargetName="b" Property="Background" Value="#333338"/>
                <Setter Property="Foreground" Value="#77777f"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <Style x:Key="Ghost" TargetType="Button">
      <Setter Property="Background" Value="#1b1b1f"/>
      <Setter Property="Foreground" Value="#d8d8de"/>
      <Setter Property="FontSize" Value="13"/>
      <Setter Property="Height" Value="40"/>
      <Setter Property="Padding" Value="14,0"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="b" Background="{TemplateBinding Background}" BorderBrush="#2c2c32" BorderThickness="1" CornerRadius="10">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="b" Property="Background" Value="#24242a"/>
              </Trigger>
              <Trigger Property="IsEnabled" Value="False">
                <Setter Property="Foreground" Value="#66666e"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <Style x:Key="Danger" TargetType="Button">
      <Setter Property="Background" Value="#241417"/>
      <Setter Property="Foreground" Value="#ff8d8d"/>
      <Setter Property="FontSize" Value="13"/>
      <Setter Property="Height" Value="40"/>
      <Setter Property="Padding" Value="16,0"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="b" Background="{TemplateBinding Background}" BorderBrush="#4a252a" BorderThickness="1" CornerRadius="10">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="b" Property="Background" Value="#341b1f"/>
              </Trigger>
              <Trigger Property="IsEnabled" Value="False">
                <Setter Property="Foreground" Value="#6b5558"/>
                <Setter TargetName="b" Property="BorderBrush" Value="#2a2022"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <Style x:Key="Card" TargetType="Border">
      <Setter Property="Background" Value="#17171a"/>
      <Setter Property="BorderBrush" Value="#26262b"/>
      <Setter Property="BorderThickness" Value="1"/>
      <Setter Property="CornerRadius" Value="14"/>
    </Style>

    <Style x:Key="YmCheck" TargetType="CheckBox">
      <Setter Property="Foreground" Value="#c9c9cf"/>
      <Setter Property="FontSize" Value="12.5"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="CheckBox">
            <StackPanel Orientation="Horizontal" Background="Transparent">
              <Grid Width="18" Height="18" VerticalAlignment="Center">
                <Border x:Name="box" CornerRadius="5" Background="#1b1b1f" BorderBrush="#3a3a40" BorderThickness="1.4"/>
                <Path x:Name="mark" Data="M3,9 L7,13 L14,5" Stroke="#17171a" StrokeThickness="2"
                      StrokeStartLineCap="Round" StrokeEndLineCap="Round" Visibility="Collapsed"/>
              </Grid>
              <ContentPresenter Margin="9,0,0,0" VerticalAlignment="Center"/>
            </StackPanel>
            <ControlTemplate.Triggers>
              <Trigger Property="IsChecked" Value="True">
                <Setter TargetName="box" Property="Background" Value="#ffcc00"/>
                <Setter TargetName="box" Property="BorderBrush" Value="#ffcc00"/>
                <Setter TargetName="mark" Property="Visibility" Value="Visible"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
  </Window.Resources>

  <Border CornerRadius="18" Background="#101012" BorderBrush="#2a2a2e" BorderThickness="1">
    <Border.Effect>
      <DropShadowEffect BlurRadius="34" ShadowDepth="10" Opacity="0.55" Color="#000000"/>
    </Border.Effect>
    <Grid>
      <Grid.RowDefinitions>
        <RowDefinition Height="58"/>
        <RowDefinition Height="*"/>
        <RowDefinition Height="48"/>
      </Grid.RowDefinitions>

      <Grid x:Name="Header" Grid.Row="0" Background="Transparent">
        <StackPanel Orientation="Horizontal" Margin="22,0,0,0" VerticalAlignment="Center">
          <Border Width="30" Height="30" CornerRadius="9" Background="#ffcc00" Margin="0,0,12,0">
            <TextBlock Text="♪" Foreground="#141414" FontSize="17" FontWeight="Bold"
                       HorizontalAlignment="Center" VerticalAlignment="Center"/>
          </Border>
          <StackPanel VerticalAlignment="Center">
            <TextBlock Text="Фон Яндекс Музыки" Foreground="#f1f1f4" FontSize="15" FontWeight="SemiBold"/>
            <TextBlock Text="установщик" Foreground="#7f7f88" FontSize="11.5" Margin="0,1,0,0"/>
          </StackPanel>
        </StackPanel>
        <StackPanel Orientation="Horizontal" HorizontalAlignment="Right" Margin="0,0,12,0" VerticalAlignment="Center">
          <Button x:Name="BtnMin" Style="{StaticResource Chrome}" Content="—"/>
          <Button x:Name="BtnClose" Style="{StaticResource Chrome}" Content="✕"/>
        </StackPanel>
      </Grid>

      <ScrollViewer Grid.Row="1" VerticalScrollBarVisibility="Auto" Margin="24,0,24,0">
        <StackPanel>
          <Border x:Name="Hero" Style="{StaticResource Card}" Padding="18" Background="#151518">
            <Grid>
              <Grid.ColumnDefinitions>
                <ColumnDefinition Width="Auto"/>
                <ColumnDefinition Width="*"/>
              </Grid.ColumnDefinitions>
              <Border x:Name="HeroIconWrap" Width="54" Height="54" CornerRadius="16" Background="#20202a" Margin="0,0,16,0">
                <TextBlock x:Name="HeroIcon" Text="…" Foreground="#ffcc00" FontSize="24" FontWeight="Bold"
                           HorizontalAlignment="Center" VerticalAlignment="Center"/>
              </Border>
              <StackPanel Grid.Column="1" VerticalAlignment="Center">
                <TextBlock x:Name="HeroTitle" Text="Проверяю…" Foreground="#f1f1f4" FontSize="19" FontWeight="SemiBold"/>
                <TextBlock x:Name="HeroSub" Text="Смотрю, что установлено в системе." Foreground="#8f8f98"
                           FontSize="12.5" Margin="0,4,0,0" TextWrapping="Wrap"/>
              </StackPanel>
            </Grid>
          </Border>

          <Border Style="{StaticResource Card}" Margin="0,12,0,0" Padding="18">
            <Grid>
              <Grid.ColumnDefinitions>
                <ColumnDefinition Width="1.25*"/>
                <ColumnDefinition Width="*"/>
                <ColumnDefinition Width="*"/>
              </Grid.ColumnDefinitions>
              <StackPanel>
                <TextBlock Text="ЯНДЕКС МУЗЫКА" Foreground="#6f6f78" FontSize="10.5" FontWeight="SemiBold"/>
                <TextBlock x:Name="AppVersion" Text="—" Foreground="#f1f1f4" FontSize="16" FontWeight="SemiBold" Margin="0,7,0,0"/>
                <TextBlock x:Name="AppPath" Text="—" Foreground="#77777f" FontSize="11" Margin="0,3,0,0"
                           TextTrimming="CharacterEllipsis"/>
              </StackPanel>
              <StackPanel Grid.Column="1">
                <TextBlock Text="ПАТЧ" Foreground="#6f6f78" FontSize="10.5" FontWeight="SemiBold"/>
                <StackPanel Orientation="Horizontal" Margin="0,8,0,0">
                  <Ellipse x:Name="PatchDot" Width="8" Height="8" Fill="#6b6b73" VerticalAlignment="Center" Margin="0,0,8,0"/>
                  <TextBlock x:Name="PatchState" Text="Проверяю…" Foreground="#e6e6ea" FontSize="13"/>
                </StackPanel>
                <TextBlock x:Name="PatchHint" Text="" Foreground="#77777f" FontSize="11" Margin="0,4,0,0" TextWrapping="Wrap"/>
              </StackPanel>
              <StackPanel Grid.Column="2">
                <TextBlock Text="PYTHON" Foreground="#6f6f78" FontSize="10.5" FontWeight="SemiBold"/>
                <StackPanel Orientation="Horizontal" Margin="0,8,0,0">
                  <Ellipse x:Name="PythonDot" Width="8" Height="8" Fill="#6b6b73" VerticalAlignment="Center" Margin="0,0,8,0"/>
                  <TextBlock x:Name="PythonState" Text="Проверяю…" Foreground="#e6e6ea" FontSize="13"/>
                </StackPanel>
                <TextBlock x:Name="PythonHint" Text="" Foreground="#77777f" FontSize="11" Margin="0,4,0,0" TextWrapping="Wrap"/>
              </StackPanel>
            </Grid>
          </Border>

          <Grid Margin="0,16,0,0">
            <Grid.ColumnDefinitions>
              <ColumnDefinition Width="*"/>
              <ColumnDefinition Width="Auto"/>
            </Grid.ColumnDefinitions>
            <StackPanel Orientation="Horizontal">
              <Button x:Name="InstallBtn" Content="Установить" Style="{StaticResource Primary}" Width="190"/>
              <Button x:Name="UninstallBtn" Content="Удалить" Style="{StaticResource Danger}" Margin="10,0,0,0" Width="120"/>
            </StackPanel>
            <StackPanel Grid.Column="1" Orientation="Horizontal">
              <Button x:Name="FolderBtn" Content="Папка с фонами" Style="{StaticResource Ghost}" Margin="0,0,8,0"/>
              <Button x:Name="LaunchBtn" Content="Запустить Музыку" Style="{StaticResource Ghost}"/>
            </StackPanel>
          </Grid>

          <StackPanel Margin="2,12,0,0">
            <CheckBox x:Name="LaunchAfter" Style="{StaticResource YmCheck}" IsChecked="True"
                      Content="Запустить Яндекс Музыку после установки"/>
            <CheckBox x:Name="RemoveSettings" Style="{StaticResource YmCheck}" IsChecked="False" Margin="0,8,0,0"
                      Content="При удалении также стереть настройки и фоны"/>
          </StackPanel>

          <ProgressBar x:Name="Progress" Height="3" Margin="0,14,0,0" IsIndeterminate="True"
                       Foreground="#ffcc00" Background="#2a2a2e" BorderThickness="0" Visibility="Collapsed"/>

          <Border Style="{StaticResource Card}" Margin="0,12,0,0" Padding="0">
            <TextBox x:Name="LogBox" Height="112" Background="#0d0d0f" Foreground="#8f8f98"
                     BorderThickness="0" FontFamily="Consolas" FontSize="11" IsReadOnly="True"
                     TextWrapping="Wrap" VerticalScrollBarVisibility="Auto" Padding="12"/>
          </Border>
        </StackPanel>
      </ScrollViewer>

      <Grid Grid.Row="2" Margin="24,0">
        <TextBlock Text="Неофициальный мод · не связан с Яндексом · используйте на свой риск"
                   Foreground="#606069" FontSize="10.5" VerticalAlignment="Center"/>
        <TextBlock x:Name="VersionText" Text="v1.1.0" Foreground="#606069" FontSize="10.5"
                   HorizontalAlignment="Right" VerticalAlignment="Center"/>
      </Grid>
    </Grid>
  </Border>
</Window>
'@

$win = [System.Windows.Markup.XamlReader]::Parse($xaml)

# --- controls ------------------------------------------------------------
$script:Header = $win.FindName("Header")
$script:BtnMin = $win.FindName("BtnMin")
$script:BtnClose = $win.FindName("BtnClose")
$script:HeroIconWrap = $win.FindName("HeroIconWrap")
$script:HeroIcon = $win.FindName("HeroIcon")
$script:HeroTitle = $win.FindName("HeroTitle")
$script:HeroSub = $win.FindName("HeroSub")
$script:AppVersion = $win.FindName("AppVersion")
$script:AppPath = $win.FindName("AppPath")
$script:PatchDot = $win.FindName("PatchDot")
$script:PatchState = $win.FindName("PatchState")
$script:PatchHint = $win.FindName("PatchHint")
$script:PythonDot = $win.FindName("PythonDot")
$script:PythonState = $win.FindName("PythonState")
$script:PythonHint = $win.FindName("PythonHint")
$script:InstallBtn = $win.FindName("InstallBtn")
$script:UninstallBtn = $win.FindName("UninstallBtn")
$script:FolderBtn = $win.FindName("FolderBtn")
$script:LaunchBtn = $win.FindName("LaunchBtn")
$script:LaunchAfter = $win.FindName("LaunchAfter")
$script:RemoveSettings = $win.FindName("RemoveSettings")
$script:Progress = $win.FindName("Progress")
$script:LogBox = $win.FindName("LogBox")
$script:VersionText = $win.FindName("VersionText")

$script:VersionText.Text = "v" + $script:version

$script:busy = $false
$script:proc = $null
$script:outTask = $null
$script:errTask = $null
$script:opKind = $null

function Append-Log([string]$text) {
    if (-not $text) { return }
    $text = $text.TrimEnd()
    if (-not $text) { return }
    $stamp = Get-Date -Format "HH:mm:ss"
    foreach ($line in ($text -split "`r?`n")) {
        if ($line.Trim().Length -eq 0) { continue }
        $script:LogBox.AppendText("[$stamp] $line`r`n")
    }
    $script:LogBox.ScrollToEnd()
}

function Set-Busy([bool]$busy) {
    $script:busy = $busy
    $script:Progress.Visibility = if ($busy) { "Visible" } else { "Collapsed" }
    $script:InstallBtn.IsEnabled = -not $busy
    $script:UninstallBtn.IsEnabled = -not $busy
    $script:FolderBtn.IsEnabled = -not $busy
    $script:LaunchBtn.IsEnabled = -not $busy
}

function Refresh-State {
    if ($script:busy) { return }
    $dir = Get-AppDir
    $exe = Get-AppExe
    $py = Find-Python
    $patched = Test-AsarPatched
    $hasBackup = Test-HasBackup

    if ($dir) {
        $script:AppPath.Text = $dir
        $script:AppVersion.Text = if ($exe) { Get-AppVersion } else { "не найдена" }
    } else {
        $script:AppPath.Text = "не найдена"
        $script:AppVersion.Text = "—"
    }

    if ($patched) {
        $script:PatchDot.Fill = [System.Windows.Media.Brushes]::LimeGreen
        $script:PatchState.Text = "Установлен"
        $script:PatchHint.Text = "Вкладка «Фон» доступна"
    } else {
        $script:PatchDot.Fill = [System.Windows.Media.Brushes]::IndianRed
        $script:PatchState.Text = "Не установлен"
        $script:PatchHint.Text = "Нажмите «Установить»"
    }

    if ($py) {
        $script:PythonDot.Fill = [System.Windows.Media.Brushes]::LimeGreen
        $script:PythonState.Text = "Найден"
        if ($py -like (Join-Path $script:root "installer\python\*") -or $py -like (Join-Path $script:root "python\*")) {
            $script:PythonHint.Text = "встроенный Python"
        } else {
            $script:PythonHint.Text = Split-Path -Leaf (Split-Path -Parent $py)
        }
    } else {
        $script:PythonDot.Fill = [System.Windows.Media.Brushes]::IndianRed
        $script:PythonState.Text = "Не найден"
        $script:PythonHint.Text = "Нужен Python 3.12"
    }

    if (-not $dir) {
        $script:HeroIcon.Text = "!"
        $script:HeroIcon.Foreground = [System.Windows.Media.Brushes]::IndianRed
        $script:HeroTitle.Text = "Яндекс Музыка не найдена"
        $script:HeroSub.Text = "Установите клиент Яндекс Музыки, затем запустите установщик снова."
        $script:InstallBtn.Content = "Установить"
        $script:InstallBtn.IsEnabled = $false
        $script:UninstallBtn.IsEnabled = $false
        $script:LaunchBtn.IsEnabled = $false
        return
    }

    if (-not $py) {
        $script:HeroIcon.Text = "!"
        $script:HeroIcon.Foreground = [System.Windows.Media.Brushes]::IndianRed
        $script:HeroTitle.Text = "Не хватает Python"
        $script:HeroSub.Text = "Установите Python 3.12 или используйте сборку установщика с папкой python."
        $script:InstallBtn.Content = "Установить"
        $script:InstallBtn.IsEnabled = $false
        $script:UninstallBtn.IsEnabled = $false
        $script:LaunchBtn.IsEnabled = $true
        return
    }

    $script:InstallBtn.IsEnabled = $true
    $script:UninstallBtn.IsEnabled = $patched -or $hasBackup
    $script:LaunchBtn.IsEnabled = $true

    if ($patched) {
        $script:HeroIcon.Text = "✓"
        $script:HeroIcon.Foreground = [System.Windows.Media.Brushes]::LimeGreen
        $script:HeroTitle.Text = "Всё готово"
        $script:HeroSub.Text = "Фон и вкладка «Фон» уже внутри Яндекс Музыки."
        $script:InstallBtn.Content = "Переустановить патч"
    } else {
        $script:HeroIcon.Text = "↓"
        $script:HeroIcon.Foreground = [System.Windows.Media.BrushConverter]::new().ConvertFromString("#FFCC00")
        $script:HeroTitle.Text = "Готово к установке"
        $script:HeroSub.Text = "Установщик добавит фон и вкладку «Фон» в Яндекс Музыку."
        $script:InstallBtn.Content = "Установить"
    }
}

function Start-Music {
    $exe = Get-AppExe
    if (-not $exe) { return }
    $running = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
        try { $_.Path -eq $exe.FullName } catch { $false }
    })
    if ($running.Count) {
        return
    }
    Start-Process -FilePath $exe.FullName
}

function Start-Operation([string]$kind, [string]$scriptPath, [string]$argLine) {
    if ($script:busy) { return }
    if (-not (Test-Path -LiteralPath $scriptPath)) {
        [System.Windows.MessageBox]::Show("Не найден файл:`n$scriptPath", "Ошибка", "OK", "Error") | Out-Null
        return
    }
    $script:opKind = $kind
    $ps = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    $env:PYTHONIOENCODING = "utf-8"
    Set-Busy $true
    $script:Progress.IsIndeterminate = $true
    $title = if ($kind -eq "install") { "Установка…" } else { "Удаление…" }
    $script:HeroTitle.Text = $title
    $script:HeroSub.Text = "Не закрывайте окно, это займёт несколько секунд."
    Append-Log ("Запуск: " + (Split-Path -Leaf $scriptPath) + " " + $argLine)
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $ps
        $psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" " + $argLine
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
        $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
        $script:proc = New-Object System.Diagnostics.Process
        $script:proc.StartInfo = $psi
        [void]$script:proc.Start()
        $script:outTask = $script:proc.StandardOutput.ReadToEndAsync()
        $script:errTask = $script:proc.StandardError.ReadToEndAsync()
        $script:poll.Start()
    } catch {
        Set-Busy $false
        Append-Log ("Ошибка запуска: " + $_.Exception.Message)
        [System.Windows.MessageBox]::Show($_.Exception.Message, "Ошибка", "OK", "Error") | Out-Null
    }
}

function Complete-Operation {
    $code = 1
    try { $code = $script:proc.ExitCode } catch { $code = -1 }
    $out = ""
    $err = ""
    try { if ($script:outTask) { $out = [string]$script:outTask.Result } } catch { $out = "" }
    try { if ($script:errTask) { $err = [string]$script:errTask.Result } } catch { $err = "" }
    if ($out) { Append-Log $out }
    if ($err) { Append-Log $err }

    if ($code -eq 0) {
        Append-Log "Готово."
        if ($script:opKind -eq "install") {
            if ($script:LaunchAfter.IsChecked) { Start-Music }
        } elseif ($script:opKind -eq "uninstall") {
            foreach ($legacy in @("ymbg.token", "YMBackground.ps1")) {
                try {
                    Remove-Item -LiteralPath (Join-Path $script:userDir $legacy) -Force -ErrorAction SilentlyContinue
                } catch {}
            }
            if ($script:RemoveSettings.IsChecked) {
                try {
                    Get-ChildItem -LiteralPath $script:userDir -Filter "custom-background.*" -File -ErrorAction SilentlyContinue |
                        Remove-Item -Force -ErrorAction SilentlyContinue
                    Append-Log "Настройки и фоны удалены."
                } catch {
                    Append-Log ("Не удалось удалить настройки: " + $_.Exception.Message)
                }
            }
        }
    } else {
        Append-Log ("Операция завершилась с кодом $code.")
        [System.Windows.MessageBox]::Show("Операция не удалась. Подробности в журнале.", "Ошибка", "OK", "Error") | Out-Null
    }

    $script:proc = $null
    $script:outTask = $null
    $script:errTask = $null
    Set-Busy $false
    Refresh-State
}

# --- timers --------------------------------------------------------------
$script:poll = New-Object System.Windows.Threading.DispatcherTimer
$script:poll.Interval = [TimeSpan]::FromMilliseconds(250)
$script:poll.Add_Tick({
    if (-not $script:proc) { $script:poll.Stop(); return }
    if (-not $script:proc.HasExited) { return }
    $script:poll.Stop()
    Complete-Operation
})

# --- events --------------------------------------------------------------
$script:Header.Add_MouseLeftButtonDown({ try { $win.DragMove() } catch {} })
$win.Add_KeyDown({
    if ($_.Key -eq [System.Windows.Input.Key]::Escape -and -not $script:busy) { $win.Close() }
})
$script:BtnClose.Add_Click({
    if ($script:busy) {
        [System.Windows.MessageBox]::Show("Дождитесь окончания операции.", "Установщик", "OK", "Information") | Out-Null
        return
    }
    $win.Close()
})
$script:BtnMin.Add_Click({ $win.WindowState = "Minimized" })

$script:InstallBtn.Add_Click({
    if ($script:busy) { return }
    $dir = Get-AppDir
    if (-not $dir) {
        [System.Windows.MessageBox]::Show("Яндекс Музыка не найдена.", "Ошибка", "OK", "Error") | Out-Null
        return
    }
    $py = Find-Python
    if (-not $py) {
        [System.Windows.MessageBox]::Show("Python 3.12 не найден.`nУстановите Python или используйте сборку с папкой python.", "Ошибка", "OK", "Error") | Out-Null
        return
    }
    $apply = Join-Path $script:root "apply.ps1"
    Start-Operation "install" $apply ("-NoLaunch -AppDir `"$dir`" -Python `"$py`"")
})

$script:UninstallBtn.Add_Click({
    if ($script:busy) { return }
    $res = [System.Windows.MessageBox]::Show(
        "Вернуть оригинальные файлы Яндекс Музыки?`n`nПатч будет удалён, фон и вкладка «Фон» исчезнут.",
        "Удаление", "YesNo", "Question")
    if ($res -ne "Yes") { return }
    $dir = Get-AppDir
    $py = Find-Python
    if (-not $dir -or -not $py) {
        [System.Windows.MessageBox]::Show("Не удалось найти Яндекс Музыку или Python.", "Ошибка", "OK", "Error") | Out-Null
        return
    }
    $restore = Join-Path $script:root "restore.ps1"
    Start-Operation "uninstall" $restore ("-NoLaunch -AppDir `"$dir`" -Python `"$py`"")
})

$script:FolderBtn.Add_Click({
    if (Test-Path -LiteralPath $script:userDir) { Start-Process explorer.exe $script:userDir }
    else { [System.Windows.MessageBox]::Show("Папка ещё не создана. Установите патч.", "Фон", "OK", "Information") | Out-Null }
})

$script:LaunchBtn.Add_Click({ Start-Music })

$win.Add_Loaded({
    Refresh-State
    Append-Log "Установщик готов."
})

$win.Add_Closed({
    try { $script:poll.Stop() } catch {}
    try { if ($script:mutex) { $script:mutex.ReleaseMutex() } } catch {}
})

[void]$win.ShowDialog()
