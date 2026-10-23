@echo off
echo ===================================================
echo Building SafeTempCleaner Portable Application
echo ===================================================

.\.venv\Scripts\pyinstaller.exe ^
    --onedir ^
    --noconsole ^
    --name "SafeTempCleaner" ^
    --icon "assets\icon.ico" ^
    --contents-directory "SafeTempCleaner_files" ^
    --collect-all customtkinter ^
    --clean ^
    -y ^
    src/main.py

echo.
echo ===================================================
echo Portable Build Complete!
echo Output folder: dist\SafeTempCleaner\
echo   - SafeTempCleaner.exe
echo   - SafeTempCleaner_files\ (runtime dependencies)
echo ===================================================
