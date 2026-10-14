# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


# ------------------------------------------------------------
# Project paths
# ------------------------------------------------------------

project = Path(SPECPATH).resolve()

assets_dir = project / "assets"
windows_dir = project / "windows"


# ------------------------------------------------------------
# Hidden imports
# ------------------------------------------------------------
#
# Большую часть модулей PyInstaller определяет автоматически.
# Здесь оставляем модули, которые могут подгружаться динамически
# pandas/openpyxl и поэтому полезно указать явно.
# ------------------------------------------------------------

hiddenimports = [
    "openpyxl",
    "openpyxl.cell._writer",
    "openpyxl.styles",
    "openpyxl.styles.borders",
    "openpyxl.styles.colors",
    "openpyxl.styles.fills",
    "openpyxl.styles.fonts",
    "openpyxl.styles.numbers",
    "openpyxl.styles.protection",
    "pandas",
]

# OpenPyXL использует ряд динамически импортируемых модулей.
hiddenimports += collect_submodules(
    "openpyxl"
)


# ------------------------------------------------------------
# Application analysis
# ------------------------------------------------------------

a = Analysis(
    [
        str(
            project / "main.py"
        )
    ],
    pathex=[
        str(project)
    ],
    binaries=[],
    datas=[
        (
            str(
                assets_dir
                / "vinogradovs_digitizer_logo.png"
            ),
            "assets",
        ),
        (
            str(
                assets_dir
                / "app_icon.png"
            ),
            "assets",
        ),
        (
            str(
                assets_dir
                / "VinogradovsDigitizer.ico"
            ),
            "assets",
        ),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "IPython",
        "notebook",
        "jupyter",
    ],
    noarchive=False,
    optimize=1,
)


# ------------------------------------------------------------
# Python bytecode archive
# ------------------------------------------------------------

pyz = PYZ(
    a.pure
)


# ------------------------------------------------------------
# Main Windows executable
# ------------------------------------------------------------
#
# Имя самого файла:
#
#     VinogradovsDigitizer.exe
#
# При этом отображаемое имя приложения и ярлыка позже будет:
#
#     Vinogradov's Digitizer
#
# console=False означает, что при запуске пользователь
# НЕ увидит чёрное окно CMD.
# ------------------------------------------------------------

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VinogradovsDigitizer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(
        assets_dir
        / "VinogradovsDigitizer.ico"
    ),
    version=str(
        windows_dir
        / "version_info.txt"
    ),
)


# ------------------------------------------------------------
# Final application directory
# ------------------------------------------------------------
#
# Результат PyInstaller:
#
# dist/
# └── VinogradovsDigitizer/
#     ├── VinogradovsDigitizer.exe
#     └── _internal/
#
# Эту папку затем целиком упакует Inno Setup.
# Конечный пользователь её вручную видеть не будет.
# ------------------------------------------------------------

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="VinogradovsDigitizer",
)