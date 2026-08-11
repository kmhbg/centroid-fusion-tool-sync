#Requires -Version 5.1
<#
.SYNOPSIS
  Installerar CentroidBridge + systemfacks-app med autostart vid inloggning.
.PARAMETER NoAutostart
  Hoppa över schemalagd uppgift (AtLogOn).
.NOTES
  Kör på CNC-PC:n (Windows). Dubbelklicka install-bridge.bat eller:
    powershell -ExecutionPolicy Bypass -File .\install-bridge.ps1
#>
param(
    [switch]$NoAutostart
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$Port = 8765
$FirewallRuleName = "CentroidBridge 8765"
$TaskName = "CentroidBridge"
$PublishDir = Join-Path $ScriptDir "publish"
$AppSettingsPath = Join-Path $ScriptDir "appsettings.json"
$TrayProject = Join-Path $ScriptDir "tray\CentroidBridge.Tray.csproj"
$DllCandidates = @(
    "C:\cncm\CentroidAPI.dll",
    "C:\cnct\CentroidAPI.dll",
    "C:\cncr\CentroidAPI.dll",
    "C:\cncp\CentroidAPI.dll"
)

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "  OK  $Message" -ForegroundColor Green
}

function Write-Warn([string]$Message) {
    Write-Host "  !!  $Message" -ForegroundColor Yellow
}

function Write-Fail([string]$Message) {
    Write-Host "  XX  $Message" -ForegroundColor Red
}

Write-Host "CentroidBridge installation (bridge + tray + autostart)" -ForegroundColor White
Write-Host "Katalog: $ScriptDir"

# --- .NET 8 SDK ---
Write-Step "Kontrollerar .NET 8 SDK"
$dotnet = Get-Command dotnet -ErrorAction SilentlyContinue
if (-not $dotnet) {
    Write-Fail "dotnet hittades inte i PATH."
    Write-Host "Installera .NET 8 SDK: https://dotnet.microsoft.com/download/dotnet/8.0"
    exit 1
}

$sdkLines = & dotnet --list-sdks 2>$null
$hasNet8 = $false
foreach ($line in $sdkLines) {
    if ($line -match "^8\.") {
        $hasNet8 = $true
        break
    }
}

if (-not $hasNet8) {
    $ver = (& dotnet --version 2>$null)
    if ($ver -match "^8\.") {
        $hasNet8 = $true
    }
}

if (-not $hasNet8) {
    Write-Fail ".NET 8 SDK saknas (hittade: $($sdkLines -join '; '))."
    Write-Host "Installera .NET 8 SDK: https://dotnet.microsoft.com/download/dotnet/8.0"
    exit 1
}
Write-Ok "dotnet SDK 8+ finns ($((& dotnet --version).Trim()))"

# --- CentroidAPI.dll ---
Write-Step "Söker CentroidAPI.dll"
$foundDll = $null
foreach ($candidate in $DllCandidates) {
    if (Test-Path -LiteralPath $candidate) {
        $foundDll = $candidate
        break
    }
}

if ($foundDll) {
    Write-Ok "Hittade CentroidAPI.dll: $foundDll"
} else {
    Write-Warn "CentroidAPI.dll hittades inte i standardvägar:"
    foreach ($candidate in $DllCandidates) {
        Write-Host "       - $candidate"
    }
    Write-Warn "Fortsätter i mock-läge (ForceMock=true). Live-sync kräver CNC12 + DLL."
}

# --- appsettings.json ---
Write-Step "Uppdaterar appsettings.json"
if (-not (Test-Path -LiteralPath $AppSettingsPath)) {
    Write-Fail "Saknar $AppSettingsPath"
    exit 1
}

$settings = Get-Content -LiteralPath $AppSettingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($foundDll) {
    $settings.CentroidApiDllPath = $foundDll
    $settings.ForceMock = $false
} else {
    if (-not $settings.CentroidApiDllPath) {
        $settings.CentroidApiDllPath = "C:\cncm\CentroidAPI.dll"
    }
    $settings.ForceMock = $true
}
$settings.Port = $Port
$settings.Urls = "http://0.0.0.0:$Port"

$jsonOut = $settings | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText($AppSettingsPath, $jsonOut + "`n", [System.Text.UTF8Encoding]::new($false))
Write-Ok "CentroidApiDllPath=$($settings.CentroidApiDllPath)"
Write-Ok "ForceMock=$($settings.ForceMock)"

# --- Stop running instances before publish ---
Write-Step "Stoppar eventuellt körande Bridge/Tray"
foreach ($name in @("CentroidBridge.Tray", "CentroidBridge")) {
    Get-Process -Name $name -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
            Write-Ok "Stoppade $($_.ProcessName) (PID $($_.Id))"
        } catch {
            Write-Warn "Kunde inte stoppa $($_.ProcessName)"
        }
    }
}

# --- publish bridge ---
Write-Step "Publicerar CentroidBridge (Release, win-x64)"
if (Test-Path -LiteralPath $PublishDir) {
    Remove-Item -LiteralPath $PublishDir -Recurse -Force
}

& dotnet publish "$ScriptDir\CentroidBridge.csproj" -c Release -r win-x64 --self-contained false -o $PublishDir
if ($LASTEXITCODE -ne 0) {
    Write-Fail "dotnet publish (bridge) misslyckades (exit $LASTEXITCODE)"
    exit $LASTEXITCODE
}
Write-Ok "Bridge publicerad till $PublishDir"

# --- publish tray into same folder ---
Write-Step "Publicerar CentroidBridge.Tray (Release, win-x64)"
if (-not (Test-Path -LiteralPath $TrayProject)) {
    Write-Fail "Saknar tray-projekt: $TrayProject"
    exit 1
}

& dotnet publish $TrayProject -c Release -r win-x64 --self-contained false -o $PublishDir
if ($LASTEXITCODE -ne 0) {
    Write-Fail "dotnet publish (tray) misslyckades (exit $LASTEXITCODE)"
    exit $LASTEXITCODE
}
Write-Ok "Tray publicerad till $PublishDir"

$publishSettings = Join-Path $PublishDir "appsettings.json"
Copy-Item -LiteralPath $AppSettingsPath -Destination $publishSettings -Force
$mockSrc = Join-Path $ScriptDir "mock-tools.json"
$mockDst = Join-Path $PublishDir "mock-tools.json"
if (Test-Path -LiteralPath $mockSrc) {
    Copy-Item -LiteralPath $mockSrc -Destination $mockDst -Force
}

$trayExe = Join-Path $PublishDir "CentroidBridge.Tray.exe"
$bridgeExe = Join-Path $PublishDir "CentroidBridge.exe"
if (-not (Test-Path -LiteralPath $trayExe)) {
    Write-Fail "Saknar $trayExe efter publish"
    exit 1
}
if (-not (Test-Path -LiteralPath $bridgeExe)) {
    Write-Fail "Saknar $bridgeExe efter publish"
    exit 1
}

# --- start-bridge.bat (starts tray) ---
Write-Step "Skapar start-bridge.bat"
$startBat = Join-Path $PublishDir "start-bridge.bat"
$startBatContent = @"
@echo off
cd /d "%~dp0"
echo Startar Centroid Bridge (systemfalt) pa port $Port ...
echo Testa: curl http://127.0.0.1:$Port/health
start "" "CentroidBridge.Tray.exe"
"@
[System.IO.File]::WriteAllText($startBat, $startBatContent, [System.Text.UTF8Encoding]::new($false))
Write-Ok $startBat

# --- firewall ---
Write-Step "Brandväggsregel TCP $Port"
$firewallOk = $false
$manualFirewall = "netsh advfirewall firewall add rule name=`"$FirewallRuleName`" dir=in action=allow protocol=TCP localport=$Port"

try {
    $existing = & netsh advfirewall firewall show rule name="$FirewallRuleName" 2>$null
    if ($LASTEXITCODE -eq 0 -and ($existing -join "`n") -match [regex]::Escape($FirewallRuleName)) {
        Write-Ok "Regel finns redan: $FirewallRuleName"
        $firewallOk = $true
    } else {
        & netsh advfirewall firewall add rule name="$FirewallRuleName" dir=in action=allow protocol=TCP localport=$Port | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "Skapade regel: $FirewallRuleName"
            $firewallOk = $true
        } else {
            Write-Warn "Kunde inte skapa brandväggsregel (kör som administratör?)."
        }
    }
} catch {
    Write-Warn "Brandvägg misslyckades: $($_.Exception.Message)"
}

if (-not $firewallOk) {
    Write-Warn "Kör manuellt i admin-PowerShell:"
    Write-Host "       $manualFirewall"
}

# --- Scheduled Task AtLogOn (default) ---
$autostartOk = $false
if (-not $NoAutostart) {
    Write-Step "Schemalagd uppgift '$TaskName' (AtLogOn)"
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

        $action = New-ScheduledTaskAction -Execute $trayExe -WorkingDirectory $PublishDir
        $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
        $settingsTask = New-ScheduledTaskSettingsSet `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries `
            -StartWhenAvailable `
            -ExecutionTimeLimit ([TimeSpan]::Zero) `
            -RestartCount 3 `
            -RestartInterval (New-TimeSpan -Minutes 1)
        $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

        Register-ScheduledTask `
            -TaskName $TaskName `
            -Action $action `
            -Trigger $trigger `
            -Settings $settingsTask `
            -Principal $principal `
            -Description "Startar Centroid Bridge tray/HTTP vid inloggning (Fusion sync)." `
            -Force | Out-Null

        Write-Ok "Autostart registrerad (Task Scheduler: $TaskName)"
        $autostartOk = $true
    } catch {
        Write-Warn "Kunde inte skapa schemalagd uppgift: $($_.Exception.Message)"
        Write-Warn "Starta manuellt via start-bridge.bat eller lägg Tray.exe i Autostart."
    }
} else {
    Write-Step "Hoppar över autostart (-NoAutostart)"
}

# --- Start tray now ---
Write-Step "Startar CentroidBridge.Tray"
Start-Process -FilePath $trayExe -WorkingDirectory $PublishDir
Write-Ok "Tray startad – kolla systemfältet (aktivitetsfältet)"

# --- summary ---
Write-Host ""
Write-Host "========================================" -ForegroundColor White
Write-Host " Installation klar" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor White
if ($foundDll) {
    Write-Host " CentroidAPI.dll : $foundDll"
    Write-Host " Läge            : live (ForceMock=false)"
} else {
    Write-Host " CentroidAPI.dll : SAKNAS"
    Write-Host " Läge            : mock (ForceMock=true)"
}
Write-Host " Publish         : $PublishDir"
Write-Host " Starta          : $startBat  (eller CentroidBridge.Tray.exe)"
Write-Host " Systemfalt      : Status / Oppna health / Avsluta"
if ($autostartOk) {
    Write-Host " Autostart       : ja (Task Scheduler: $TaskName)"
} elseif ($NoAutostart) {
    Write-Host " Autostart       : nej (-NoAutostart)"
} else {
    Write-Host " Autostart       : misslyckades – se varning ovan"
}
Write-Host " Test            : curl http://127.0.0.1:$Port/health"
Write-Host ""
Write-Host "Avinstallera autostart:"
Write-Host "  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
Write-Host ""
