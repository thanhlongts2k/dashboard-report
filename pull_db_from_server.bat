@echo off
setlocal enabledelayedexpansion

cd /d "d:\Sources\dashboard-report"

set SERVER_USER=rd
set SERVER_IP=192.168.16.231
set LOCAL_DB_NAME=reportdb
set LOCAL_DB_USER=postgres
set LOCAL_DB_HOST=localhost
set LOCAL_DB_PORT=5433

REM Doc mat khau PostgreSQL tu file .env local (Khong hardcode trong script)
set LOCAL_DB_PASS=
if exist ".env" (
    for /f "tokens=1,* delims==" %%A in ('findstr /R "^DB_PASSWORD=" .env') do (
        set LOCAL_DB_PASS=%%B
    )
)
if defined LOCAL_DB_PASS (
    set LOCAL_DB_PASS=!LOCAL_DB_PASS:'=!
    set LOCAL_DB_PASS=!LOCAL_DB_PASS:"=!
) else (
    echo [CANH BAO] Khong tim thay DB_PASSWORD trong .env local!
)

echo ====================================================================
echo [1/4] DANG KICH HOAT DUMP DATABASE TREN SERVER (%SERVER_IP%)...
echo ====================================================================
ssh %SERVER_USER%@%SERVER_IP% "sudo -u postgres pg_dump -d reportdb -F c -b -f /tmp/server_reportdb.dump && sudo chmod 666 /tmp/server_reportdb.dump"
if %ERRORLEVEL% NEQ 0 (
    echo [LOI] Khong the dump database tren server Linux!
    pause
    exit /b %ERRORLEVEL%
)

echo ====================================================================
echo [2/4] DANG TAI FILE DUMP VE MAY LOCAL (qua SCP)...
echo ====================================================================
if not exist ".\scratch" mkdir ".\scratch"
set LOCAL_DUMP=.\scratch\server_reportdb.dump
if exist "%LOCAL_DUMP%" del /f /q "%LOCAL_DUMP%"

scp %SERVER_USER%@%SERVER_IP%:/tmp/server_reportdb.dump "%LOCAL_DUMP%"
if %ERRORLEVEL% NEQ 0 (
    echo [LOI] Khong the tai file dump tu server ve local!
    pause
    exit /b %ERRORLEVEL%
)

ssh %SERVER_USER%@%SERVER_IP% "rm -f /tmp/server_reportdb.dump"

echo ====================================================================
echo [3/4] DANG NAP (RESTORE) VAO POSTGRESQL LOCAL (PORT %LOCAL_DB_PORT%)...
echo ====================================================================
set PGPASSWORD=%LOCAL_DB_PASS%
pg_restore -U %LOCAL_DB_USER% -h %LOCAL_DB_HOST% -p %LOCAL_DB_PORT% -d %LOCAL_DB_NAME% --clean --if-exists -v "%LOCAL_DUMP%"
set RESTORE_STATUS=%ERRORLEVEL%

echo ====================================================================
echo [4/4] DON DEP FILE DUMP TAM...
echo ====================================================================
if exist "%LOCAL_DUMP%" del /f /q "%LOCAL_DUMP%"

echo.
echo ====================================================================
echo  [HOAN TAT] DATABASE REPORTDB LOCAL DA DONG BO 100%% VOI SERVER!
echo ====================================================================
timeout /t 5
