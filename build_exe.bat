@echo off
echo =========================================================================
echo  ETABS to RAM Concept Exporter - Standalone Executable Generator (.BAT)
echo =========================================================================
echo.

:: 1. Ensure project directory is current working directory
cd /d "%~dp0"

:: 2. Check if PyInstaller is installed
echo [1/3] Checking PyInstaller installation...
pyinstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    python -m pip install pyinstaller
)
echo PyInstaller is ready.

echo.
:: 3. Kill any running instances of the executable to avoid file lock errors
echo [2/3] Terminating any active background executable processes...
taskkill /F /IM ETABS_to_RAM_Concept_Exporter.exe >nul 2>&1

echo.
:: 4. Build executable using floor_exporter.spec
echo [3/3] Building standalone executable via PyInstaller...
python -m PyInstaller floor_exporter.spec --noconfirm

if %errorlevel% equ 0 (
    echo.
    echo =========================================================================
    echo  SUCCESS: Executable generated successfully!
    echo  Location: %~dp0dist\ETABS_to_RAM_Concept_Exporter.exe
    echo =========================================================================
) else (
    echo.
    echo [ERROR] Build failed. Please check log messages above.
)

echo.
pause
