@echo off
chcp 65001 > nul
cd /d "%~dp0"

REM Start Celery Worker in a new terminal window
start "Celery Worker" cmd /k "cd /d ""%~dp0"" && .venv\Scripts\celery -A report2026 worker --loglevel=info -P solo"

REM Start Celery Beat in a new terminal window
start "Celery Beat" cmd /k "cd /d ""%~dp0"" && .venv\Scripts\celery -A report2026 beat --loglevel=info"

exit
