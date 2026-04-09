@echo off
REM PyQt6 UI launcher for Upload Lab Tool

setlocal enabledelayedexpansion

REM Get the directory of this script
set SCRIPT_DIR=%~dp0

REM Change to script directory
cd /d "%SCRIPT_DIR%"

REM Run bootstrap
python bootstrap_ui_pyqt6.py

REM Pause on error
if errorlevel 1 (
    echo.
    echo Bootstrap failed! Press any key to exit...
    pause
    exit /b 1
)

exit /b 0
