@echo off
setlocal enabledelayedexpansion

set SERVER_USER=rd
set SERVER_IP=192.168.16.231
set REMOTE_DIR=/data/www/backend/dashboard-report
set LOCAL_ENV_FILE=d:\Sources\dashboard-report\.env.server

title [SYNC] Dong Bo .env.server Len Server Linux - %SERVER_IP%

echo ====================================================================
echo   DONG BO CAU HINH: .env.server --^> SERVER LINUX (%SERVER_IP%)
echo ====================================================================
echo.

if not exist "%LOCAL_ENV_FILE%" (
    echo [LOI] Khong tim thay file cau hinh: %LOCAL_ENV_FILE%
    echo Vui long kiem tra lai truoc khi dong bo!
    pause
    exit /b 1
)

echo File nguon: %LOCAL_ENV_FILE%
echo Dich den  : %SERVER_USER%@%SERVER_IP%:%REMOTE_DIR%/.env
echo.
echo * Luu y: Tien trinh se tu dong tao ban sao luu (.env.bak_*) tren server
echo          va khoi dong lai cac service (Backend, Celery, Beat) ngay lap tuc.
echo.

set /p CONFIRM="Ban co chac chan muon dong bo cau hinh nay len Server? (Y/N): "
if /i "%CONFIRM%" NEQ "Y" (
    echo.
    echo [HUY] Da huy thao tac dong bo.
    timeout /t 3
    exit /b 0
)

echo.
echo ====================================================================
echo [1/4] SAO LUU FILE .env HIEN TAI TREN SERVER (Rollback safety)...
echo ====================================================================
ssh %SERVER_USER%@%SERVER_IP% "if [ -f %REMOTE_DIR%/.env ]; then cp %REMOTE_DIR%/.env %REMOTE_DIR%/.env.bak_$(date +%%Y%%m%%d_%%H%%M%%S); echo '✅ Da tao ban backup tai server.'; fi"

echo.
echo ====================================================================
echo [2/4] DANG DAY FILE .env.server LEN SERVER QUA SCP...
echo ====================================================================
scp "%LOCAL_ENV_FILE%" %SERVER_USER%@%SERVER_IP%:/tmp/dashboard_env_new
if %ERRORLEVEL% NEQ 0 (
    echo [LOI] Khong the upload file .env.server len server!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ====================================================================
echo [3/4] CAP NHAT VA PHAN QUYEN AN TOAN TREN SERVER...
echo ====================================================================
ssh %SERVER_USER%@%SERVER_IP% "mv /tmp/dashboard_env_new %REMOTE_DIR%/.env && chmod 640 %REMOTE_DIR%/.env && chown rd:www-data %REMOTE_DIR%/.env 2>/dev/null || true"
if %ERRORLEVEL% NEQ 0 (
    echo [LOI] Khong the ghi de file .env vao %REMOTE_DIR%!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ====================================================================
echo [4/4] KHOI DONG LAI CAC DICH VU (Backend, Celery, Beat)...
echo ====================================================================
ssh %SERVER_USER%@%SERVER_IP% "sudo systemctl restart dashboard-backend dashboard-celery dashboard-beat"
if %ERRORLEVEL% NEQ 0 (
    echo [CANH BAO] Khong the tu dong restart cac dich vu qua sudo!
    echo Vui long kiem tra lai quyen sudoers hoac restart thu cong.
) else (
    echo ✅ Da khoi dong lai thanh cong dashboard-backend, dashboard-celery, dashboard-beat!
)

echo.
echo ====================================================================
echo  [HOAN TAT] DA DONG BO CAU HINH VA AP DUNG THANH CONG LEN SERVER!
echo ====================================================================
timeout /t 5
