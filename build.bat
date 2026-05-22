@echo off
REM Build standalone executable for Windows with PyInstaller.

setlocal

set PROJECT_DIR=%~dp0
cd /d "%PROJECT_DIR%"

echo === Installing dependencies ===
pip install -r requirements.txt
pip install pyinstaller

echo.
echo === Building executable ===

set TESS_DIR=C:\Program Files\Tesseract-OCR
set ADD_DATA_FLAG=

if exist "%TESS_DIR%\tesseract.exe" (
    echo Tesseract detected: bundling into executable
    set "ADD_DATA_FLAG=--add-data=%TESS_DIR%;tesseract"
) else (
    echo WARNING: Tesseract not found at %TESS_DIR%
    echo OCR feature will require user-side Tesseract install.
)

pyinstaller --noconfirm ^
    --onefile ^
    --windowed ^
    --name "ContadorPalavras" ^
    %ADD_DATA_FLAG% ^
    --collect-all PyQt6 ^
    --collect-all fitz ^
    --collect-all pytesseract ^
    --collect-all openpyxl ^
    --collect-all regex ^
    src\main.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo === Build complete ===
    echo Executable: dist\ContadorPalavras.exe
) else (
    echo.
    echo === Build failed ===
    exit /b 1
)

endlocal
