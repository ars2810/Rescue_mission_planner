@echo off
cd /d "%~dp0"
set PYTHONHOME=C:\Users\HP\AppData\Local\Programs\Python\Python314
set PATH=C:\Python314;C:\Users\HP\AppData\Local\Programs\Python\Python314\Scripts;%PATH%
set MPLCONFIGDIR=%TEMP%\rescue_planner_mpl

echo ========================================================
echo   Launching Rescue Mission Planner Graphical Interface
echo ========================================================

"C:\Python314\python.exe" run_planner.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================================
    echo   Application exited with error code: %ERRORLEVEL%
    echo ========================================================
    pause
)
