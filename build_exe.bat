@echo off
REM Builds SPACE_MINER.exe with PyInstaller. Requires Python 3.8+ on PATH.
echo === SPACE MINER - Windows EXE builder ===
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found on PATH. Install it from https://python.org
    echo        and check "Add Python to PATH" during install.
    pause
    exit /b 1
)
python -m pip install --user --quiet pyinstaller
python -m PyInstaller --onefile --name SPACE_MINER --clean --noconfirm main.py
if errorlevel 1 (
    echo Build FAILED. See output above.
    pause
    exit /b 1
)
echo.
echo === Done! Your game is: dist\SPACE_MINER.exe ===
echo You can copy it anywhere and run it standalone.
pause
