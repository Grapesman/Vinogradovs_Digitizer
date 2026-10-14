from __future__ import annotations

import ctypes
import os
import sys

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from digitizer.main_window import MainWindow
from digitizer.resources import (
    APP_DISPLAY_NAME,
    APP_ID,
    APP_NAME,
    APP_ORGANIZATION,
    APP_VERSION,
    SPLASH_LOADING_TEXT,
    WELCOME_TEXT,
    app_icon_ico,
    app_icon_png,
    app_logo_png,
)
from digitizer.theme import apply_modern_theme


def _set_windows_app_id() -> None:
    """
    Устанавливает Windows Application User Model ID.

    Это помогает Windows правильно связывать:
    - приложение;
    - значок EXE;
    - ярлык на рабочем столе;
    - значок на панели задач.

    На Linux и macOS функция ничего не делает.
    """

    if sys.platform != "win32":
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            APP_ID
        )
    except Exception:
        pass


def _load_logo() -> QPixmap:
    """
    Загружает большой фирменный логотип.

    Если большой логотип недоступен,
    используется обычная иконка приложения.
    """

    logo = QPixmap(
        str(
            app_logo_png()
        )
    )

    if logo.isNull():
        logo = QPixmap(
            str(
                app_icon_png()
            )
        )

    return logo


def _build_splash_pixmap() -> QPixmap:
    """
    Создаёт стартовую заставку Vinogradov's Digitizer.
    """

    width = 820
    height = 560

    canvas = QPixmap(
        width,
        height,
    )

    canvas.fill(
        QColor(
            "#0d2137"
        )
    )

    painter = QPainter(
        canvas
    )

    painter.setRenderHint(
        QPainter.Antialiasing,
        True,
    )

    painter.setRenderHint(
        QPainter.SmoothPixmapTransform,
        True,
    )

    # --------------------------------------------------------
    # Основная карточка
    # --------------------------------------------------------

    painter.setPen(
        Qt.NoPen
    )

    painter.setBrush(
        QColor(
            "#102b47"
        )
    )

    painter.drawRoundedRect(
        QRectF(
            28,
            28,
            764,
            504,
        ),
        30,
        30,
    )

    # --------------------------------------------------------
    # Золотая акцентная линия
    # --------------------------------------------------------

    painter.setBrush(
        QColor(
            "#d7b46a"
        )
    )

    painter.drawRoundedRect(
        QRectF(
            28,
            28,
            8,
            504,
        ),
        4,
        4,
    )

    # --------------------------------------------------------
    # Герб
    # --------------------------------------------------------

    logo = _load_logo()

    if not logo.isNull():
        logo = logo.scaled(
            300,
            300,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        x = int(
            (
                width
                - logo.width()
            )
            / 2
        )

        painter.drawPixmap(
            x,
            62,
            logo,
        )

    # --------------------------------------------------------
    # Название приложения
    # --------------------------------------------------------

    painter.setPen(
        QColor(
            "#ffffff"
        )
    )

    title_font = QFont(
        "Segoe UI",
        25,
    )

    title_font.setBold(
        True
    )

    painter.setFont(
        title_font
    )

    painter.drawText(
        QRectF(
            70,
            365,
            680,
            48,
        ),
        Qt.AlignCenter,
        APP_DISPLAY_NAME,
    )

    # --------------------------------------------------------
    # Приветствие
    # --------------------------------------------------------

    painter.setPen(
        QColor(
            "#d4dfeb"
        )
    )

    welcome_font = QFont(
        "Segoe UI",
        13,
    )

    painter.setFont(
        welcome_font
    )

    painter.drawText(
        QRectF(
            70,
            416,
            680,
            34,
        ),
        Qt.AlignCenter,
        WELCOME_TEXT,
    )

    # --------------------------------------------------------
    # Текст загрузки
    # --------------------------------------------------------

    painter.setPen(
        QColor(
            "#e8c985"
        )
    )

    loading_font = QFont(
        "Segoe UI",
        11,
    )

    loading_font.setBold(
        True
    )

    painter.setFont(
        loading_font
    )

    painter.drawText(
        QRectF(
            70,
            468,
            680,
            28,
        ),
        Qt.AlignCenter,
        SPLASH_LOADING_TEXT,
    )

    painter.end()

    return canvas


def _get_splash_duration() -> int:
    """
    Возвращает продолжительность заставки в миллисекундах.

    Windows:
        по умолчанию 3500 мс.

    Docker:
        VINOGRADOVS_SPLASH_MS=0,
        потому что там заставку показывает HTML/noVNC.
    """

    try:
        value = int(
            os.environ.get(
                "VINOGRADOVS_SPLASH_MS",
                "3500",
            )
        )
    except ValueError:
        value = 3500

    return max(
        0,
        value,
    )


def main() -> int:
    """
    Главная точка запуска Vinogradov's Digitizer.
    """

    # --------------------------------------------------------
    # Windows identity
    # --------------------------------------------------------

    _set_windows_app_id()

    # --------------------------------------------------------
    # QApplication
    # --------------------------------------------------------

    app = QApplication(
        sys.argv
    )

    # При закрытии последнего главного окна
    # процесс приложения должен завершаться полностью.
    app.setQuitOnLastWindowClosed(
        True
    )

    # --------------------------------------------------------
    # Информация о приложении
    # --------------------------------------------------------

    app.setApplicationName(
        APP_NAME
    )

    app.setApplicationDisplayName(
        APP_DISPLAY_NAME
    )

    app.setApplicationVersion(
        APP_VERSION
    )

    app.setOrganizationName(
        APP_ORGANIZATION
    )

    # --------------------------------------------------------
    # Иконка приложения
    # --------------------------------------------------------

    icon_path = app_icon_ico()

    if icon_path.exists():
        app.setWindowIcon(
            QIcon(
                str(
                    icon_path
                )
            )
        )

    else:
        png_path = app_icon_png()

        if png_path.exists():
            app.setWindowIcon(
                QIcon(
                    str(
                        png_path
                    )
                )
            )

    # --------------------------------------------------------
    # Тема
    # --------------------------------------------------------

    apply_modern_theme(
        app
    )

    # --------------------------------------------------------
    # Заставка
    # --------------------------------------------------------

    splash = QSplashScreen(
        _build_splash_pixmap()
    )

    splash.setWindowFlag(
        Qt.FramelessWindowHint,
        True,
    )

    splash.setWindowFlag(
        Qt.WindowStaysOnTopHint,
        True,
    )

    splash.show()

    app.processEvents()

    # --------------------------------------------------------
    # Главное окно
    # --------------------------------------------------------

    window = MainWindow()

    def show_main_window() -> None:
        """
        Показывает главное окно после заставки.
        """

        # ----------------------------------------------------
        # Docker / noVNC
        # ----------------------------------------------------

        if (
            os.environ.get(
                "VINOGRADOVS_FULLSCREEN"
            )
            == "1"
        ):
            window.showFullScreen()

        elif (
            os.environ.get(
                "VINOGRADOVS_MAXIMIZED"
            )
            == "1"
        ):
            window.showMaximized()

        # ----------------------------------------------------
        # Windows
        # ----------------------------------------------------
        #
        # Финальная Windows-версия запускается как обычное
        # настольное приложение и сразу использует максимально
        # доступную площадь экрана.
        # ----------------------------------------------------

        elif sys.platform == "win32":
            window.showMaximized()

        # ----------------------------------------------------
        # Другие ОС
        # ----------------------------------------------------

        else:
            window.show()

        # Даём Qt завершить построение layout,
        # после чего корректно вписываем изображение.
        QTimer.singleShot(
            180,
            window.canvas.fit_image,
        )

        splash.finish(
            window
        )

    # --------------------------------------------------------
    # Продолжительность заставки
    # --------------------------------------------------------

    splash_ms = _get_splash_duration()

    if splash_ms <= 0:
        show_main_window()

    else:
        QTimer.singleShot(
            splash_ms,
            show_main_window,
        )

    # --------------------------------------------------------
    # Event loop
    # --------------------------------------------------------

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(
        main()
    )