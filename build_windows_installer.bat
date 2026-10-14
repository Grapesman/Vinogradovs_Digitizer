@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Vinogradov's Digitizer - Windows Installer Build

set "APP_NAME=Vinogradov's Digitizer"
set "APP_VERSION=2.3.0"

set "DIST_DIR=dist\VinogradovsDigitizer"
set "APP_EXE=%DIST_DIR%\VinogradovsDigitizer.exe"

set "RELEASE_DIR=release"
set "INSTALLER_NAME=Vinogradovs_Digitizer_Setup_%APP_VERSION%.exe"
set "INSTALLER_PATH=%RELEASE_DIR%\%INSTALLER_NAME%"

echo.
echo ============================================================
echo   Vinogradov's Digitizer %APP_VERSION%
echo   Windows Installer Builder
echo ============================================================
echo.


REM ------------------------------------------------------------
REM 1. Check application build
REM ------------------------------------------------------------

echo [1/4] Checking application build...

if not exist "%APP_EXE%" (
    echo.
    echo Application EXE was not found:
    echo.
    echo   %APP_EXE%
    echo.
    echo Building application first...
    echo.

    call build_windows_exe.bat

    if errorlevel 1 (
        echo.
        echo [ERROR] Application build failed.
        goto :fail
    )
)

if not exist "%APP_EXE%" (
    echo.
    echo [ERROR] Application EXE still does not exist:
    echo.
    echo   %APP_EXE%
    goto :fail
)

echo Application found:
echo.
echo   %APP_EXE%
echo.


REM ------------------------------------------------------------
REM 2. Find Inno Setup 6
REM ------------------------------------------------------------

echo [2/4] Looking for Inno Setup 6...

set "ISCC="

if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
)

if not defined ISCC (
    if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
        set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
    )
)

if not defined ISCC (
    if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" (
        set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
    )
)

if not defined ISCC (
    echo.
    echo [ERROR] Inno Setup 6 was not found.
    echo.
    echo Install Inno Setup 6 and run this script again.
    echo.
    echo Inno Setup is required only to BUILD the installer.
    echo End users do NOT need it installed.
    echo.
    goto :fail
)

echo Found:
echo.
echo   %ISCC%
echo.


REM ------------------------------------------------------------
REM 3. Clean previous installer
REM ------------------------------------------------------------

echo [3/4] Preparing release folder...

if not exist "%RELEASE_DIR%" (
    mkdir "%RELEASE_DIR%"
)

if exist "%INSTALLER_PATH%" (
    del /f /q "%INSTALLER_PATH%"

    if errorlevel 1 (
        echo.
        echo [ERROR] Could not remove old installer:
        echo.
        echo   %INSTALLER_PATH%
        goto :fail
    )
)

echo Release folder ready.
echo.


REM ------------------------------------------------------------
REM 4. Build installer
REM ------------------------------------------------------------

echo [4/4] Building installer...

"%ISCC%" "installer\VinogradovsDigitizer.iss"

if errorlevel 1 (
    echo.
    echo [ERROR] Inno Setup compilation failed.
    goto :fail
)


REM ------------------------------------------------------------
REM Verify result
REM ------------------------------------------------------------

if not exist "%INSTALLER_PATH%" (
    echo.
    echo [ERROR] Inno Setup finished, but installer was not found:
    echo.
    echo   %INSTALLER_PATH%
    goto :fail
)


REM ------------------------------------------------------------
REM Success
REM ------------------------------------------------------------

echo.
echo ============================================================
echo   INSTALLER BUILD SUCCESSFUL
echo ============================================================
echo.
echo Product:
echo.
echo   %APP_NAME%
echo   Version %APP_VERSION%
echo.
echo Installer:
echo.
echo   %CD%\%INSTALLER_PATH%
echo.
echo The end user only needs this file:
echo.
echo   %INSTALLER_NAME%
echo.
echo No Python is required.
echo No Docker is required.
echo No additional runtime is required.
echo.
echo ============================================================
echo.

pause
exit /b 0


:fail

echo.
echo ============================================================
echo   INSTALLER BUILD FAILED
echo ============================================================
echo.
echo Check the error messages above.
echo.
pause
exit /b 1