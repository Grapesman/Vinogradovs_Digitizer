@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Vinogradov's Digitizer - Windows EXE Build

set "APP_NAME=Vinogradov's Digitizer"
set "APP_VERSION=2.3.0"
set "BUILD_ENV=.venv-build"
set "DIST_DIR=dist\VinogradovsDigitizer"
set "EXE_PATH=%DIST_DIR%\VinogradovsDigitizer.exe"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "QT_QPA_PLATFORM=offscreen"

echo.
echo ============================================================
echo   Vinogradov's Digitizer %APP_VERSION%
echo   Windows EXE Builder
echo ============================================================
echo.

REM ------------------------------------------------------------
REM 1. Find Python
REM ------------------------------------------------------------

echo [1/6] Checking Python...

where py >nul 2>nul

if not errorlevel 1 (
    py -3.12 --version >nul 2>nul

    if not errorlevel 1 (
        set "PYTHON_CMD=py -3.12"
        goto :python_found
    )

    py -3.11 --version >nul 2>nul

    if not errorlevel 1 (
        set "PYTHON_CMD=py -3.11"
        goto :python_found
    )
)

where python >nul 2>nul

if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :python_found
)

echo.
echo [ERROR] Python 3.11 or 3.12 was not found.
echo.
echo Python is required only to BUILD the application.
echo End users do NOT need Python installed.
echo.
echo Recommended build version: Python 3.12 x64
echo.
pause
exit /b 1


:python_found

echo Python:
%PYTHON_CMD% --version

echo.


REM ------------------------------------------------------------
REM 2. Create isolated build environment
REM ------------------------------------------------------------

echo [2/6] Preparing build environment...

if not exist "%BUILD_ENV%\Scripts\python.exe" (
    echo Creating %BUILD_ENV%...
    %PYTHON_CMD% -m venv "%BUILD_ENV%"

    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to create build virtual environment.
        goto :fail
    )
) else (
    echo Existing build environment found.
)

call "%BUILD_ENV%\Scripts\activate.bat"

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to activate build environment.
    goto :fail
)

echo.


REM ------------------------------------------------------------
REM 3. Install / update build dependencies
REM ------------------------------------------------------------

echo [3/6] Installing build dependencies...

python -m pip install --upgrade pip

if errorlevel 1 goto :fail

python -m pip install -r requirements-build.txt

if errorlevel 1 goto :fail

echo.


REM ------------------------------------------------------------
REM 4. Run automated tests
REM ------------------------------------------------------------

echo [4/6] Running tests...

python -m pytest tests -q

if errorlevel 1 (
    echo.
    echo [ERROR] Tests failed.
    echo The EXE will NOT be built.
    goto :fail
)

echo.
echo Tests passed.
echo.


REM ------------------------------------------------------------
REM 5. Clean previous PyInstaller output
REM ------------------------------------------------------------

echo [5/6] Cleaning previous build...

if exist "build" (
    rmdir /s /q "build"
)

if exist "%DIST_DIR%" (
    rmdir /s /q "%DIST_DIR%"
)

echo Build folders cleaned.
echo.


REM ------------------------------------------------------------
REM 6. Build application
REM ------------------------------------------------------------

echo [6/6] Building Windows application...

python -m PyInstaller ^
    --clean ^
    --noconfirm ^
    VinogradovsDigitizer.spec

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller failed.
    goto :fail
)


REM ------------------------------------------------------------
REM Verify result
REM ------------------------------------------------------------

if not exist "%EXE_PATH%" (
    echo.
    echo [ERROR] Build finished but EXE was not found:
    echo %EXE_PATH%
    goto :fail
)


REM ------------------------------------------------------------
REM Success
REM ------------------------------------------------------------

echo.
echo ============================================================
echo   BUILD SUCCESSFUL
echo ============================================================
echo.
echo Application:
echo.
echo   %CD%\%EXE_PATH%
echo.
echo Product:
echo.
echo   %APP_NAME%
echo   Version %APP_VERSION%
echo.
echo The application folder is:
echo.
echo   %CD%\%DIST_DIR%
echo.
echo This folder will be packaged by Inno Setup into:
echo.
echo   Vinogradovs_Digitizer_Setup_%APP_VERSION%.exe
echo.
echo ============================================================
echo.

pause
exit /b 0


:fail

echo.
echo ============================================================
echo   BUILD FAILED
echo ============================================================
echo.
echo Check the error messages above.
echo.
pause
exit /b 1