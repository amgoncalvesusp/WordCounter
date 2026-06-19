@echo off
REM Reproducible standalone Windows build with native-DLL validation.

setlocal EnableExtensions

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

set "BOOTSTRAP_PYTHON=py -3.11"
%BOOTSTRAP_PYTHON% -c "import sys" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    set "BOOTSTRAP_PYTHON=python"
)

set "BUILD_VENV=%PROJECT_DIR%.build-venv"
set "BUILD_PYTHON=%BUILD_VENV%\Scripts\python.exe"
set "PYTHONNOUSERSITE=1"

echo === Creating isolated build environment ===
%BOOTSTRAP_PYTHON% -m venv "%BUILD_VENV%"
if %ERRORLEVEL% NEQ 0 exit /b 1

"%BUILD_PYTHON%" -m pip install --disable-pip-version-check --upgrade pip
if %ERRORLEVEL% NEQ 0 exit /b 1

"%BUILD_PYTHON%" -m pip install --disable-pip-version-check ^
    --upgrade -r requirements-build.txt
if %ERRORLEVEL% NEQ 0 exit /b 1

set "TESS_DIR=C:\Program Files\Tesseract-OCR"
if defined TESSERACT_BUNDLE_DIR set "TESS_DIR=%TESSERACT_BUNDLE_DIR%"

set "TESSERACT_ARG="
set "VERIFY_TESSERACT_ARG="
if exist "%TESS_DIR%\tesseract.exe" (
    echo Tesseract detected: bundling from %TESS_DIR%
    set "TESSERACT_ZIP=%BUILD_VENV%\tesseract.zip"
    "%BUILD_PYTHON%" "packaging\windows\package_tesseract.py" ^
        "%TESS_DIR%" "%BUILD_VENV%\tesseract.zip"
    if errorlevel 1 exit /b 1
    set TESSERACT_ARG=--add-data "%BUILD_VENV%\tesseract.zip;bundled_tools"
    set VERIFY_TESSERACT_ARG=--require-tesseract
) else (
    echo WARNING: Tesseract not found. OCR will require a local installation.
)

echo.
echo === Building executable ===

REM Keep third-party Qt/ICU installations out of PyInstaller dependency search.
set "PATH=%BUILD_VENV%\Scripts;%SystemRoot%\System32;%SystemRoot%"
set "PYTHONPATH=%PROJECT_DIR%"

"%BUILD_PYTHON%" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --noupx ^
    --name "ContadorPalavras" ^
    --runtime-hook "packaging\windows\runtime_hook_qt.py" ^
    --hidden-import PyQt6.QtCore ^
    --hidden-import PyQt6.QtGui ^
    --hidden-import PyQt6.QtWidgets ^
    --hidden-import src.core.analysis.vendor.leia.leia ^
    --add-data "src\core\analysis\vendor\leia\lexicons;src\core\analysis\vendor\leia\lexicons" ^
    --add-data "src\core\data;src\core\data" ^
    --exclude-module PyQt5 ^
    --exclude-module PySide6 ^
    %TESSERACT_ARG% ^
    src\main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo === Build failed ===
    exit /b 1
)

echo.
echo === Verifying executable and native DLL layout ===
"%BUILD_PYTHON%" "packaging\windows\verify_build.py" ^
    "dist\ContadorPalavras.exe" %VERIFY_TESSERACT_ARG%
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo === Verification failed ===
    exit /b 1
)

echo.
echo === Build complete ===
echo Executable: dist\ContadorPalavras.exe

endlocal
