@echo off
setlocal
set SERVER_USER=rd
set SERVER_IP=192.168.16.231
set REMOTE_PATH=/data/www/backend/dashboard-report
cd /d "d:\Sources\dashboard-report"

echo ========================================================
echo [1/4] DANG LOC RAC VA DONG GOI MA NGUON SANG TAR.GZ...
echo ========================================================
call powershell -ExecutionPolicy Bypass -File .\scripts\deploy\build_tar.ps1
if %ERRORLEVEL% NEQ 0 (
    echo [LOI] Dong goi ma nguon that bai!
    pause
    exit /b %ERRORLEVEL%
)

if not exist dashboard_be.tar.gz (
    echo [LOI] Khong tim thay dashboard_be.tar.gz sau khi dong goi!
    pause
    exit /b 1
)

echo ========================================================
echo [2/4] DANG DAY GOI NEN VA SCRIPT LEN SERVER...
echo ========================================================
scp dashboard_be.tar.gz %SERVER_USER%@%SERVER_IP%:/tmp/
if %ERRORLEVEL% NEQ 0 (
    echo [LOI] SCP dashboard_be.tar.gz len server that bai!
    del /f /q dashboard_be.tar.gz
    pause
    exit /b %ERRORLEVEL%
)

scp scripts\deploy\server_update.sh %SERVER_USER%@%SERVER_IP%:/tmp/
if %ERRORLEVEL% NEQ 0 (
    echo [LOI] SCP server_update.sh len server that bai!
    del /f /q dashboard_be.tar.gz
    pause
    exit /b %ERRORLEVEL%
)

del /f /q dashboard_be.tar.gz

echo ========================================================
echo [3/4] THUC THI CAP NHAT & RELOAD SERVICES TREN SERVER...
echo ========================================================
ssh %SERVER_USER%@%SERVER_IP% "bash /tmp/server_update.sh"
if %ERRORLEVEL% NEQ 0 (
    echo [CANH BAO] Qua trinh thuc thi tren server co canh bao/loi, vui long kiem tra log o tren!
)

echo ========================================================
echo [4/4] HOAN TAT! BACKEND DASHBOARD-REPORT DA DEPLOY!
echo ========================================================
timeout /t 5
