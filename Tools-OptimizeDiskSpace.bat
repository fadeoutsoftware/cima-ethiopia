@echo off
echo ============================================
echo   Docker WSL2 Disk Compaction Utility
echo ============================================
echo.

REM ------------------------------------------------------------
REM Check if Optimize-VHD is available (Hyper-V PowerShell module)
REM ------------------------------------------------------------
echo Checking for Optimize-VHD availability...
powershell -Command "Get-Command Optimize-VHD -ErrorAction SilentlyContinue" >nul 2>&1

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] The Optimize-VHD PowerShell cmdlet is not available.
    echo This usually means that the Hyper-V feature is not enabled.
    echo.
    echo To enable Hyper-V, run the following command in an elevated PowerShell:
    echo.
    echo   Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -All
    echo.
    echo After enabling and rebooting, run this script again.
    echo.
    echo Script aborted.
    pause
    exit /b 1
)

echo Optimize-VHD detected. Proceeding...
echo.

REM ------------------------------------------------------------
REM Stop Docker Desktop
REM ------------------------------------------------------------
echo Stopping Docker Desktop...
taskkill /IM "Docker Desktop.exe" /F >nul 2>&1

REM ------------------------------------------------------------
REM Shutdown WSL
REM ------------------------------------------------------------
echo Shutting down WSL...
wsl --shutdown

REM ------------------------------------------------------------
REM Compact the VHDX disk
REM ------------------------------------------------------------
echo.
echo Compacting docker_data.vhdx ...
powershell -Command "Optimize-Vhd -Path \"$env:LOCALAPPDATA\Docker\wsl\disk\docker_data.vhdx\" -Mode Full"

echo.
echo ============================================
echo   DONE!
echo   The Docker VHDX has been compacted.
echo ============================================
pause
