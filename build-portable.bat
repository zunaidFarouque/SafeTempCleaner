@echo off
echo ===================================================
echo Building SafeTempCleaner Portable Application
echo ===================================================

.\.venv\Scripts\pyinstaller.exe ^
    --onedir ^
    --noconsole ^
    --name "SafeTempCleaner" ^
    --icon "assets\icon.ico" ^
    --add-data "assets\icon.ico;assets" ^
    --add-data "assets\logo.png;assets" ^
    --contents-directory "SafeTempCleaner_files" ^
    --collect-all customtkinter ^
    --clean ^
    -y ^
    src/main.py

REM Ensure default config.json is bundled beside executable for Scoop file-link compatibility
.\.venv\Scripts\python.exe -c "from src.config.config_manager import ConfigManager; ConfigManager('dist/SafeTempCleaner/config.json').load()"

echo.
echo ===================================================
echo Portable Build Complete!
echo Output folder: dist\SafeTempCleaner\
echo   - SafeTempCleaner.exe
echo   - config.json (persisted settings)
echo   - SafeTempCleaner_files\ (runtime dependencies)
echo ===================================================
