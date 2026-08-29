@echo off
echo ======================================================================
echo Starting ETABS to RAM Concept Floor Exporter (Native Windows Mode)
echo RAM Concept 2024 API Integration Enabled
echo ======================================================================

cd /d "%~dp0"

echo 1. Launching Backend FastAPI Server (Port 8080)...
start "Backend - FastAPI" cmd /k "cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload"

echo 2. Launching Frontend Vite Dev Server (Port 5173)...
start "Frontend - Vite" cmd /k "cd frontend && npm run dev"

echo.
echo Servers started successfully!
echo - Web UI: http://localhost:5173
echo - Backend API: http://localhost:8080/api
echo ======================================================================
