# PowerShell Build Script for ETABS -> RAM Concept Exporter Desktop App

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Building ETABS -> RAM Concept Exporter Executable         " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Clean previous build artifacts
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

# 2. Run PyInstaller build
Write-Host "[1/2] Compiling Windows executable with PyInstaller..." -ForegroundColor Yellow
pyinstaller floor_exporter.spec --noconfirm

if (Test-Path "dist\ETABS_to_RAM_Concept_Exporter.exe") {
    Write-Host "[SUCCESS] Executable built successfully at: dist\ETABS_to_RAM_Concept_Exporter.exe" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Build failed." -ForegroundColor Red
    exit 1
}
