@echo off
setlocal
cd /d "%~dp0"

echo.
echo CentroidBridge - installation (bridge + tray + autostart)
echo.

REM Prefer PowerShell 7 if present, else Windows PowerShell
where pwsh >nul 2>&1
if %ERRORLEVEL%==0 (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-bridge.ps1"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-bridge.ps1"
)

set EXITCODE=%ERRORLEVEL%
echo.
if not %EXITCODE%==0 (
  echo Installationen misslyckades ^(kod %EXITCODE%^).
  pause
  exit /b %EXITCODE%
)

pause
exit /b 0
