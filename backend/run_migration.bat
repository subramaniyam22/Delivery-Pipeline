@echo off
REM Run Alembic migrations (ensure PostgreSQL is running and .env DATABASE_URL is set)
cd /d "%~dp0"
python -m alembic upgrade head
if %ERRORLEVEL% neq 0 (
    echo.
    echo Migration failed. Check that:
    echo 1. PostgreSQL is running (e.g. port 5432)
    echo 2. .env exists with correct DATABASE_URL
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo Migration completed successfully.
pause
