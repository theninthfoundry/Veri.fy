@echo off
echo ===================================================
echo   VERI: Starting End-to-End Environment Setup
echo ===================================================

echo.
echo [1/4] Starting Docker Compose Infrastructure...
docker compose up -d

echo.
echo Waiting for databases and message broker to start...
timeout /t 5 /nobreak > nul

echo.
echo [2/4] Building Go Gateway and Analyzer Services...
cd services\gateway
echo Building Ingestion Gateway...
go build -o gateway.exe main.go
if %errorlevel% neq 0 (
    echo Error building Gateway! Exiting.
    cd ..\..
    pause
    exit /b %errorlevel%
)
cd ..\analyzer
echo Building Analysis Engine...
go build -o analyzer.exe main.go
if %errorlevel% neq 0 (
    echo Error building Analyzer! Exiting.
    cd ..\..
    pause
    exit /b %errorlevel%
)
cd ..\..

echo.
echo [3/4] Launching Go Gateway and Analyzer in separate windows...
start "VERI Ingestion Gateway" cmd /k "cd services\gateway && gateway.exe"
start "VERI Analysis Engine" cmd /k "cd services\analyzer && analyzer.exe"

echo.
echo Waiting 5 seconds for services to initialize...
timeout /t 5 /nobreak > nul

echo.
echo [4/5] Generating Live Telemetry Data...
python verify_ir.py
if %errorlevel% neq 0 (
    echo Error generating telemetry data!
)

echo.
echo [5/5] Running Accountability Verification Test...
python verify_escalation.py
if %errorlevel% neq 0 (
    echo Error running accountability verification!
)

echo.
echo ===================================================
echo   VERI Agent Accountability Platform is running!
echo   Access the Cockpit Dashboard at:
echo   http://localhost:8080/
echo ===================================================
pause

