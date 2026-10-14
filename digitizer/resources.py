from __future__ import annotations

import sys
from pathlib import Path


# ------------------------------------------------------------
# Application identity
# ------------------------------------------------------------

# Техническое имя приложения.
APP_NAME = "Vinogradovs Digitizer"

# Название, которое видит пользователь.
APP_DISPLAY_NAME = "Vinogradov's Digitizer"

# Версия приложения.
APP_VERSION = "2.3.0"

# Организация / издатель.
APP_ORGANIZATION = "Vinogradov"

# Имя исполняемого файла Windows.
APP_EXECUTABLE_NAME = "VinogradovsDigitizer.exe"

# ------------------------------------------------------------
# Windows Application User Model ID
# ------------------------------------------------------------
#
# ВАЖНО:
# App ID не должен меняться от версии к версии.
#
# Благодаря постоянному ID Windows корректно связывает:
# - EXE;
# - ярлык;
# - панель задач;
# - значок приложения;
# - последующие обновления программы.
#
# Поэтому здесь НЕТ номера версии.
# ------------------------------------------------------------

APP_ID = "Vinogradov.VinogradovsDigitizer"


# ------------------------------------------------------------
# Splash screen
# ------------------------------------------------------------

WELCOME_TEXT = (
    "Добро пожаловать в дигитайзер Виноградова"
)

SPLASH_LOADING_TEXT = (
    "Загрузка Digitizer Vinogradov…"
)


# ------------------------------------------------------------
# Application resources
# ------------------------------------------------------------

APP_ICON_PNG = (
    "assets/app_icon.png"
)

APP_ICON_ICO = (
    "assets/VinogradovsDigitizer.ico"
)

APP_LOGO_PNG = (
    "assets/vinogradovs_digitizer_logo.png"
)


def resource_path(
    relative: str | Path,
) -> Path:
    """
    Получить абсолютный путь к ресурсу приложения.

    Поддерживаются два режима:

    1. Обычный запуск:
       - Python;
       - Docker;
       - среда разработки.

    2. Windows EXE,
       собранный через PyInstaller.

    При запуске PyInstaller ресурсы располагаются
    относительно директории sys._MEIPASS.
    """

    relative_path = Path(
        relative
    )

    # --------------------------------------------------------
    # PyInstaller
    # --------------------------------------------------------

    if (
        getattr(
            sys,
            "frozen",
            False,
        )
        and hasattr(
            sys,
            "_MEIPASS",
        )
    ):
        base_path = Path(
            sys._MEIPASS
        )

    # --------------------------------------------------------
    # Source / Docker
    # --------------------------------------------------------

    else:
        # Структура проекта:
        #
        # project/
        # ├── assets/
        # ├── main.py
        # └── digitizer/
        #     └── resources.py
        #
        # parents[1] == project/
        base_path = (
            Path(__file__)
            .resolve()
            .parents[1]
        )

    return (
        base_path
        / relative_path
    )


def app_icon_png() -> Path:
    """
    PNG-иконка приложения.
    """

    return resource_path(
        APP_ICON_PNG
    )


def app_icon_ico() -> Path:
    """
    Windows ICO-иконка приложения.
    """

    return resource_path(
        APP_ICON_ICO
    )


def app_logo_png() -> Path:
    """
    Большой логотип / герб для заставки.
    """

    return resource_path(
        APP_LOGO_PNG
    )