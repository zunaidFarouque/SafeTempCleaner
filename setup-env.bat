@echo off
echo ===================================================
echo Setting up SafeTempCleaner Environment
echo ===================================================

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Installing dependencies...
.\.venv\Scripts\pip install -r requirements.txt

echo.
echo Setup complete! Run .\run.bat to start SafeTempCleaner.
