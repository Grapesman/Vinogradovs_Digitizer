@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Vinogradov's Digitizer - Release Builder

set "APP_NAME=Vinogradov's Digitizer"
set "APP_VERSION=2.3.0"

set "DIST_DIR=dist\VinogradovsDigitizer"
set "APP_EXE=%DIST_DIR%\VinogradovsDigitizer.exe"

set "RELEASE_DIR=release"

set "INSTALLER_NAME=Vinogradovs_Digitizer_Setup_%APP_VERSION%.exe"
set "INSTALLER_PATH=%RELEASE_DIR%\%INSTALLER_NAME%"

set "PORTABLE_NAME=Vinogradovs_Digitizer_Portable_%APP_VERSION%.zip"
set "PORTABLE_PATH=%RELEASE_DIR%\%PORTABLE_NAME%"

set "CHECKSUM_FILE=%RELEASE_DIR%\SHA256SUMS.txt"

echo.
echo ============================================================
echo   Vinogradov's Digitizer %APP_VERSION%
echo   Complete Windows Release Builder
echo ============================================================
echo.


REM ------------------------------------------------------------
REM 1. Clean release artifacts
REM ------------------------------------------------------------

echo [1/5] Preparing release directory...

if not exist "%RELEASE_DIR%" (
    mkdir "%RELEASE_DIR%"
)

if exist "%INSTALLER_PATH%" (
    del /f /q "%INSTALLER_PATH%"
)

if exist "%PORTABLE_PATH%" (
    del /f /q "%PORTABLE_PATH%"
)

if exist "%CHECKSUM_FILE%" (
    del /f /q "%CHECKSUM_FILE%"
)

echo Release directory ready.
echo.


REM ------------------------------------------------------------
REM 2. Build application
REM ------------------------------------------------------------

echo [2/5] Building Windows application...
echo.

call build_windows_exe.bat

if errorlevel 1 (
    echo.
    echo [ERROR] Application build failed.
    goto :fail
)

if not exist "%APP_EXE%" (
    echo.
    echo [ERROR] Application executable was not created:
    echo.
    echo   %APP_EXE%
    goto :fail
)

echo.
echo Application build completed.
echo.


REM ------------------------------------------------------------
REM 3. Build installer
REM ------------------------------------------------------------

echo [3/5] Building Windows installer...
echo.

call build_windows_installer.bat

if errorlevel 1 (
    echo.
    echo [ERROR] Installer build failed.
    goto :fail
)

if not exist "%INSTALLER_PATH%" (
    echo.
    echo [ERROR] Installer was not created:
    echo.
    echo   %INSTALLER_PATH%
    goto :fail
)

echo.
echo Installer build completed.
echo.


REM ------------------------------------------------------------
REM 4. Build portable ZIP
REM ------------------------------------------------------------

echo [4/5] Creating portable ZIP...

powershell -NoProfile -ExecutionPolicy Bypass ^
    -Command ^
    "Compress-Archive -Path '%DIST_DIR%\*' -DestinationPath '%PORTABLE_PATH%' -CompressionLevel Optimal -Force"

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to create portable ZIP.
    goto :fail
)

if not exist "%PORTABLE_PATH%" (
    echo.
    echo [ERROR] Portable ZIP was not created:
    echo.
    echo   %PORTABLE_PATH%
    goto :fail
)

echo Portable ZIP created.
echo.


REM ------------------------------------------------------------
REM 5. Generate SHA-256 checksums
REM ------------------------------------------------------------

echo [5/5] Generating SHA-256 checksums...

powershell -NoProfile -ExecutionPolicy Bypass ^
    -Command ^
    "$files = @('%INSTALLER_PATH%', '%PORTABLE_PATH%');" ^
    "$result = foreach ($file in $files) {" ^
    "  $hash = Get-FileHash -Algorithm SHA256 -Path $file;" ^
    "  '{0}  {1}' -f $hash.Hash.ToLower(), (Split-Path $file -Leaf)" ^
    "};" ^
    "$result | Set-Content -Encoding ASCII '%CHECKSUM_FILE%'"

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to create SHA256SUMS.txt.
    goto :fail
)

if not exist "%CHECKSUM_FILE%" (
    echo.
    echo [ERROR] SHA256SUMS.txt was not created.
    goto :fail
)


REM ------------------------------------------------------------
REM Success
REM ------------------------------------------------------------

echo.
echo ============================================================
echo   RELEASE BUILD SUCCESSFUL
echo ============================================================
echo.
echo Product:
echo.
echo   %APP_NAME%
echo   Version %APP_VERSION%
echo.
echo Release files:
echo.
echo   %CD%\%INSTALLER_PATH%
echo.
echo   %CD%\%PORTABLE_PATH%
echo.
echo   %CD%\%CHECKSUM_FILE%
echo.
echo ------------------------------------------------------------
echo.
echo Recommended file for normal users:
echo.
echo   %INSTALLER_NAME%
echo.
echo Portable version:
echo.
echo   %PORTABLE_NAME%
echo.
echo The end user does NOT need:
echo.
echo   - Python
echo   - Docker
echo   - PySide6
echo   - OpenCV
echo   - Inno Setup
echo.
echo ============================================================
echo.

start "" "%RELEASE_DIR%"

pause
exit /b 0


:fail

echo.
echo ============================================================
echo   RELEASE BUILD FAILED
echo ============================================================
echo.
echo No release should be published until the error is fixed.
echo.
pause
exit /b 1