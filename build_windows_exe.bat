@echo off
echo ======================================================================
echo Building Standalone Windows Executables (.EXE & Package)
echo ETABS to RAM Concept Floor Exporter
echo ======================================================================

cd /d "%~dp0"

echo 1. Building React Frontend Static Assets...
cmd /c "cd frontend && npm run build"

echo.
echo 2. Installing PyInstaller Build Dependencies...
python -m pip install --upgrade pyinstaller

echo.
echo 3. Packaging Standalone Windows Executables via PyInstaller Spec...
pyinstaller --noconfirm ETABS_RAMConcept_Floor_Exporter.spec

echo.
echo 4. Creating Portable ZIP Distribution Archive...
powershell -Command "if (Test-Path 'dist\ETABS_RAMConcept_Floor_Exporter_Package.zip') { Remove-Item 'dist\ETABS_RAMConcept_Floor_Exporter_Package.zip' }; Compress-Archive -Path 'dist\ETABS_RAMConcept_Floor_Exporter_Folder\*' -DestinationPath 'dist\ETABS_RAMConcept_Floor_Exporter_Package.zip' -Force"

echo.
echo ======================================================================
echo Build Complete!
echo.
echo Ready for Sharing / Distribution:
echo 1. Single-File Standalone Executable:
echo    %~dp0dist\ETABS_RAMConcept_Floor_Exporter_SingleFile.exe
echo.
echo 2. Zip Package (Portable Folder):
echo    %~dp0dist\ETABS_RAMConcept_Floor_Exporter_Package.zip
echo ======================================================================
pause

