@echo off
set SERVER_USER=rd
set SERVER_IP=192.168.16.231

title [MONITOR] Report2026 Server Logs - %SERVER_IP%

echo ====================================================================
echo  DANG KET NOI VA STREAM LOG TRUC TIEP TU SERVER: %SERVER_IP%
echo  (Nhan Ctrl + C de thoat man hinh theo doi)
echo ====================================================================
echo.

ssh -t %SERVER_USER%@%SERVER_IP% "journalctl -u dashboard-backend -u dashboard-celery -u dashboard-beat -f -n 50"

pause
