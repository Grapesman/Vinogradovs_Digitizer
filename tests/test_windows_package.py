"""Release configuration tests for Vinogradov's Digitizer.

These tests do not build the Windows executable.
They verify that the source tree is internally consistent
before PyInstaller and Inno Setup are started.
"""

from __future__ import annotations

from pathlib import Path

from digitizer.resources import (
    APP_DISPLAY_NAME,
    APP_EXECUTABLE_NAME,
    APP_ICON_ICO,
    APP_ICON_PNG,
    APP_ID,
    APP_LOGO_PNG,
    APP_NAME,
    APP_ORGANIZATION,
    APP_VERSION,
    app_icon_ico,
    app_icon_png,
    app_logo_png,
    resource_path,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)


EXPECTED_VERSION = "2.3.0"
EXPECTED_FILE_VERSION = "2.3.0.0"

EXPECTED_DISPLAY_NAME = (
    "Vinogradov's Digitizer"
)

EXPECTED_APP_NAME = (
    "Vinogradovs Digitizer"
)

EXPECTED_EXE_NAME = (
    "VinogradovsDigitizer.exe"
)

EXPECTED_APP_ID = (
    "Vinogradov.VinogradovsDigitizer"
)


def read_text(
    relative_path: str,
) -> str:
    """Read a UTF-8 project text file."""

    path = (
        PROJECT_ROOT
        / relative_path
    )

    assert path.exists(), (
        f"Required file does not exist: {path}"
    )

    return path.read_text(
        encoding="utf-8",
    )


def test_application_identity() -> None:
    """Application identity must remain consistent."""

    assert (
        APP_DISPLAY_NAME
        == EXPECTED_DISPLAY_NAME
    )

    assert (
        APP_NAME
        == EXPECTED_APP_NAME
    )

    assert (
        APP_VERSION
        == EXPECTED_VERSION
    )

    assert (
        APP_EXECUTABLE_NAME
        == EXPECTED_EXE_NAME
    )

    assert (
        APP_ORGANIZATION
        == "Vinogradov"
    )

    assert (
        APP_ID
        == EXPECTED_APP_ID
    )

    # App ID must be stable between releases.
    # A version number must never be included in it.
    assert (
        APP_VERSION
        not in APP_ID
    )


def test_resource_paths_exist() -> None:
    """All resources required by PyInstaller must exist."""

    expected = {
        APP_ICON_PNG: app_icon_png(),
        APP_ICON_ICO: app_icon_ico(),
        APP_LOGO_PNG: app_logo_png(),
    }

    for relative, resolved in expected.items():

        assert resolved == resource_path(
            relative
        )

        assert resolved.exists(), (
            f"Missing application resource: {resolved}"
        )

        assert resolved.is_file(), (
            f"Resource is not a file: {resolved}"
        )

        assert resolved.stat().st_size > 0, (
            f"Resource is empty: {resolved}"
        )


def test_png_resources_are_valid_files() -> None:
    """PNG resources must at least have a valid PNG signature."""

    png_signature = (
        b"\x89PNG\r\n\x1a\n"
    )

    for path in (
        app_icon_png(),
        app_logo_png(),
    ):

        data = path.read_bytes()

        assert data.startswith(
            png_signature
        ), (
            f"Invalid PNG file: {path}"
        )


def test_windows_icon_is_valid_ico() -> None:
    """Windows executable icon must be a real ICO file."""

    path = app_icon_ico()

    data = path.read_bytes()

    # ICO header:
    # reserved = 0
    # type = 1
    assert data[:4] == (
        b"\x00\x00\x01\x00"
    ), (
        f"Invalid Windows ICO file: {path}"
    )


def test_windows_version_info() -> None:
    """Windows EXE metadata must use version 2.3.0."""

    text = read_text(
        "windows/version_info.txt"
    )

    assert (
        "filevers=(2, 3, 0, 0)"
        in text
    )

    assert (
        "prodvers=(2, 3, 0, 0)"
        in text
    )

    assert (
        '"FileVersion"'
        in text
    )

    assert (
        f'"{EXPECTED_FILE_VERSION}"'
        in text
    )

    assert (
        '"ProductVersion"'
        in text
    )

    assert (
        f'"{EXPECTED_VERSION}"'
        in text
    )

    assert (
        '"OriginalFilename"'
        in text
    )

    assert (
        f'"{EXPECTED_EXE_NAME}"'
        in text
    )

    assert (
        '"ProductName"'
        in text
    )

    assert (
        EXPECTED_DISPLAY_NAME
        in text
    )


def test_pyinstaller_spec() -> None:
    """PyInstaller spec must build the expected application."""

    text = read_text(
        "VinogradovsDigitizer.spec"
    )

    assert (
        '"main.py"'
        in text
        or "'main.py'"
        in text
    )

    assert (
        'name="VinogradovsDigitizer"'
        in text
        or "name='VinogradovsDigitizer'"
        in text
    )

    assert (
        "VinogradovsDigitizer.ico"
        in text
    )

    assert (
        "version_info.txt"
        in text
    )

    # Final Windows application must not open
    # an additional console window.
    compact = (
        text
        .replace(" ", "")
        .replace("\n", "")
    )

    assert (
        "console=False"
        in compact
    )

    # We intentionally build one-dir,
    # because Inno Setup packages the directory.
    assert (
        "COLLECT("
        in text
    )


def test_installer_configuration() -> None:
    """Inno Setup must use the final product identity."""

    text = read_text(
        "installer/VinogradovsDigitizer.iss"
    )

    assert (
        '#define MyAppName "Vinogradov\'s Digitizer"'
        in text
    )

    assert (
        '#define MyAppVersion "2.3.0"'
        in text
    )

    assert (
        '#define MyAppExeName "VinogradovsDigitizer.exe"'
        in text
    )

    assert (
        "Vinogradovs_Digitizer_Setup_"
        in text
    )

    assert (
        "VinogradovsDigitizer.ico"
        in text
    )

    assert (
        "PrivilegesRequired=lowest"
        in text
    )

    assert (
        "MinVersion=10.0"
        in text
    )

    # Desktop shortcut must be available.
    assert (
        'Name: "desktopicon"'
        in text
    )

    assert (
        "{autodesktop}"
        in text
    )

    # Installer must include the complete
    # PyInstaller one-dir folder.
    assert (
        r"..\dist\VinogradovsDigitizer\*"
        in text
    )


def test_github_windows_workflow() -> None:
    """GitHub Actions must build the same release version."""

    text = read_text(
        ".github/workflows/build-windows.yml"
    )

    assert (
        'APP_VERSION: "2.3.0"'
        in text
    )

    assert (
        "windows-latest"
        in text
    )

    assert (
        'python-version: "3.12"'
        in text
    )

    assert (
        "VinogradovsDigitizer.spec"
        in text
    )

    assert (
        "Vinogradovs_Digitizer_Setup_2.3.0.exe"
        in text
    )

    assert (
        "Vinogradovs_Digitizer_Portable_2.3.0.zip"
        in text
    )

    assert (
        "SHA256SUMS.txt"
        in text
    )

    assert (
        "Publish GitHub Release"
        in text
    )

    assert (
        "refs/tags/"
        in text
    )


def test_main_entry_point_is_desktop_application() -> None:
    """Final application must remain a native Qt desktop app."""

    text = read_text(
        "main.py"
    )

    assert (
        "QApplication"
        in text
    )

    assert (
        "MainWindow"
        in text
    )

    assert (
        "setQuitOnLastWindowClosed"
        in text
    )

    assert (
        "window.showMaximized()"
        in text
    )

    # The final Windows application is native.
    # It must not depend on browser/local-server startup.
    forbidden = (
        "webbrowser.open(",
        "localhost:6080",
        "127.0.0.1:6080",
    )

    for marker in forbidden:
        assert marker not in text, (
            f"Unexpected browser/server startup in main.py: {marker}"
        )


def test_release_build_files_exist() -> None:
    """All files required for release automation must exist."""

    required = (
        "requirements.txt",
        "requirements-build.txt",
        "VinogradovsDigitizer.spec",
        "windows/version_info.txt",
        "installer/VinogradovsDigitizer.iss",
        "build_windows_exe.bat",
        "build_windows_installer.bat",
        "build_windows_release.bat",
        ".github/workflows/build-windows.yml",
    )

    for relative in required:

        path = (
            PROJECT_ROOT
            / relative
        )

        assert path.exists(), (
            f"Missing release file: {relative}"
        )

        assert path.is_file(), (
            f"Release path is not a file: {relative}"
        )


def test_no_old_release_version_in_critical_files() -> None:
    """Old 2.2 release metadata must not return."""

    critical_files = (
        "VinogradovsDigitizer.spec",
        "windows/version_info.txt",
        "installer/VinogradovsDigitizer.iss",
        ".github/workflows/build-windows.yml",
    )

    for relative in critical_files:

        text = read_text(
            relative
        )

        assert "2.2.0" not in text, (
            f"Old version 2.2.0 found in {relative}"
        )