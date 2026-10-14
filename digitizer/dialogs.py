from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .resources import (
    app_icon_ico,
    app_icon_png,
)


def _existing_dir(
    path: str | Path | None,
) -> Path | None:
    """
    Возвращает существующую директорию
    либо None.

    Если передан путь к существующему файлу,
    возвращается его родительская папка.
    """

    if not path:
        return None

    try:
        p = (
            Path(path)
            .expanduser()
            .resolve()
        )
    except Exception:
        return None

    if p.exists() and p.is_dir():
        return p

    if p.exists() and p.is_file():
        return p.parent

    return None


def _remember_selected_path(
    path: str | Path | None,
) -> None:
    """
    Запоминает последнюю папку на время
    текущего запуска приложения.

    Никакие настройки в Windows Registry
    или пользовательские файлы не создаются.
    """

    if not path:
        return

    try:
        p = Path(path).expanduser()

        if p.exists() and p.is_dir():
            directory = p
        else:
            directory = p.parent

        if directory.exists():
            os.environ[
                "VINOGRADOVS_LAST_DIR"
            ] = str(
                directory.resolve()
            )

    except Exception:
        pass


def default_user_directory() -> Path:
    """
    Определяет наиболее удобную стартовую папку
    для открытия и сохранения файлов.

    Windows:
        домашняя папка пользователя.

    Docker:
        смонтированная домашняя папка Mac,
        если она доступна.

    Во время текущего запуска приложения
    приоритет имеет последняя использованная папка.
    """

    candidates = (
        os.environ.get(
            "VINOGRADOVS_LAST_DIR"
        ),
        os.environ.get(
            "VINOGRADOVS_HOST_HOME"
        ),
        Path.home(),
        Path.cwd(),
    )

    for candidate in candidates:
        p = _existing_dir(
            candidate
        )

        if p is not None:
            return p

    return Path.cwd()


def _sidebar_paths() -> list[Path]:
    """
    Формирует быстрые ссылки слева
    в Qt-файловом диалоге.

    Используется прежде всего
    в Docker/Linux.
    """

    roots: list[Path] = []

    base = default_user_directory()

    roots.append(
        base
    )

    for name in (
        "Desktop",
        "Downloads",
        "Documents",
        "Pictures",
    ):
        p = base / name

        if (
            p.exists()
            and p.is_dir()
        ):
            roots.append(
                p
            )

    # Дополнительные диски/тома,
    # смонтированные в Docker.
    volumes = _existing_dir(
        os.environ.get(
            "VINOGRADOVS_HOST_VOLUMES"
        )
    )

    if volumes is not None:
        roots.append(
            volumes
        )

    unique: list[Path] = []
    seen: set[str] = set()

    for p in roots:
        key = str(
            p
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        unique.append(
            p
        )

    return unique


def _application_icon() -> QIcon:
    """
    Возвращает фирменную иконку приложения.
    """

    ico = app_icon_ico()

    if ico.exists():
        return QIcon(
            str(ico)
        )

    png = app_icon_png()

    if png.exists():
        return QIcon(
            str(png)
        )

    return QIcon()


def _qt_file_dialog(
    parent: QWidget,
    *,
    title: str,
    initial: str | Path | None,
    name_filter: str,
    save: bool,
    default_name: str = "",
) -> str:
    """
    Стилизованный Qt-файловый диалог.

    Используется в Docker/Linux.

    Windows использует нативный
    Windows Explorer.
    """

    start = (
        _existing_dir(initial)
        or default_user_directory()
    )

    dialog = QFileDialog(
        parent,
        title,
        str(start),
        name_filter,
    )

    # В Docker/Linux используем Qt-диалог,
    # чтобы применялся наш современный QSS.
    dialog.setOption(
        QFileDialog.DontUseNativeDialog,
        True,
    )

    dialog.setModal(
        True
    )

    dialog.setWindowIcon(
        _application_icon()
    )

    dialog.setObjectName(
        "modernFileDialog"
    )

    dialog.setViewMode(
        QFileDialog.Detail
    )

    # --------------------------------------------------------
    # Быстрые папки слева
    # --------------------------------------------------------

    urls = [
        QUrl.fromLocalFile(
            str(p)
        )
        for p in _sidebar_paths()
    ]

    if urls:
        dialog.setSidebarUrls(
            urls
        )

    # --------------------------------------------------------
    # Save mode
    # --------------------------------------------------------

    if save:
        dialog.setAcceptMode(
            QFileDialog.AcceptSave
        )

        dialog.setFileMode(
            QFileDialog.AnyFile
        )

        if default_name:
            dialog.selectFile(
                default_name
            )

    # --------------------------------------------------------
    # Open mode
    # --------------------------------------------------------

    else:
        dialog.setAcceptMode(
            QFileDialog.AcceptOpen
        )

        dialog.setFileMode(
            QFileDialog.ExistingFile
        )

    # --------------------------------------------------------
    # Execute
    # --------------------------------------------------------

    if (
        dialog.exec()
        != QDialog.Accepted
    ):
        return ""

    files = (
        dialog.selectedFiles()
    )

    if not files:
        return ""

    result = files[0]

    _remember_selected_path(
        result
    )

    return result


def open_file(
    parent: QWidget,
    *,
    title: str,
    initial: str | Path | None,
    name_filter: str,
) -> str:
    """
    Открыть один файл.

    Windows:
        используется стандартный
        нативный Проводник Windows.

    Docker/Linux:
        используется стилизованный
        Qt-файловый диалог.
    """

    start_dir = (
        _existing_dir(initial)
        or default_user_directory()
    )

    # --------------------------------------------------------
    # Windows
    # --------------------------------------------------------

    if sys.platform == "win32":

        path, _selected_filter = (
            QFileDialog.getOpenFileName(
                parent,
                title,
                str(start_dir),
                name_filter,
            )
        )

        if path:
            _remember_selected_path(
                path
            )

        return path

    # --------------------------------------------------------
    # Docker / Linux / other
    # --------------------------------------------------------

    return _qt_file_dialog(
        parent,
        title=title,
        initial=start_dir,
        name_filter=name_filter,
        save=False,
    )


def save_file(
    parent: QWidget,
    *,
    title: str,
    initial: str | Path | None,
    name_filter: str,
) -> str:
    """
    Сохранить один файл.

    Windows:
        используется стандартный
        нативный Проводник Windows.

    Docker/Linux:
        используется стилизованный
        Qt-файловый диалог.
    """

    if initial:
        initial_path = (
            Path(initial)
            .expanduser()
        )
    else:
        initial_path = (
            default_user_directory()
        )

    # --------------------------------------------------------
    # Windows
    # --------------------------------------------------------
    #
    # Здесь intentionally НЕ используется
    # QFileDialog.DontUseNativeDialog.
    #
    # Поэтому пользователь получает обычное
    # системное окно Windows Explorer.
    # --------------------------------------------------------

    if sys.platform == "win32":

        path, _selected_filter = (
            QFileDialog.getSaveFileName(
                parent,
                title,
                str(initial_path),
                name_filter,
            )
        )

        if path:
            _remember_selected_path(
                path
            )

        return path

    # --------------------------------------------------------
    # Docker / Linux
    # --------------------------------------------------------

    if initial_path.suffix:
        start_dir = (
            initial_path.parent
        )

        default_name = (
            initial_path.name
        )

    else:
        start_dir = (
            initial_path
        )

        default_name = ""

    path = _qt_file_dialog(
        parent,
        title=title,
        initial=start_dir,
        name_filter=name_filter,
        save=True,
        default_name=default_name,
    )

    if not path:
        return ""

    _remember_selected_path(
        path
    )

    return path


class ModernMessageDialog(QDialog):
    """
    Современное информационное окно
    Vinogradov's Digitizer.

    Используется вместо стандартного QMessageBox.
    """

    def __init__(
        self,
        parent: QWidget | None,
        *,
        title: str,
        text: str,
        kind: str = "info",
    ) -> None:

        super().__init__(
            parent
        )

        self.setWindowTitle(
            title
        )

        self.setModal(
            True
        )

        self.setMinimumWidth(
            430
        )

        self.setMaximumWidth(
            680
        )

        self.setObjectName(
            "modernMessageDialog"
        )

        self.setWindowIcon(
            _application_icon()
        )

        outer = QVBoxLayout(
            self
        )

        outer.setContentsMargins(
            22,
            20,
            22,
            18,
        )

        outer.setSpacing(
            16
        )

        # ----------------------------------------------------
        # Верхняя часть
        # ----------------------------------------------------

        top = QHBoxLayout()

        top.setSpacing(
            14
        )

        icon = QLabel()

        icon.setObjectName(
            "messageIcon"
        )

        icon.setFixedSize(
            54,
            54,
        )

        png = app_icon_png()

        if png.exists():

            pix = QPixmap(
                str(png)
            )

            if not pix.isNull():

                icon.setPixmap(
                    pix.scaled(
                        50,
                        50,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )

        top.addWidget(
            icon,
            0,
            Qt.AlignTop,
        )

        # ----------------------------------------------------
        # Заголовок + текст
        # ----------------------------------------------------

        text_box = QVBoxLayout()

        text_box.setSpacing(
            7
        )

        heading = QLabel(
            title
        )

        heading.setObjectName(
            "messageTitle"
        )

        heading.setWordWrap(
            True
        )

        text_box.addWidget(
            heading
        )

        body = QLabel(
            text
        )

        body.setObjectName(
            "messageBody"
        )

        body.setWordWrap(
            True
        )

        # Пользователь может выделить
        # и скопировать текст ошибки.
        body.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )

        text_box.addWidget(
            body
        )

        top.addLayout(
            text_box,
            1,
        )

        outer.addLayout(
            top
        )

        # ----------------------------------------------------
        # Нижняя часть
        # ----------------------------------------------------

        footer = QHBoxLayout()

        footer.addStretch(
            1
        )

        ok = QPushButton(
            "Понятно"
        )

        ok.setProperty(
            "primary",
            True,
        )

        ok.setMinimumWidth(
            120
        )

        ok.clicked.connect(
            self.accept
        )

        footer.addWidget(
            ok
        )

        outer.addLayout(
            footer
        )

        self.setProperty(
            "messageKind",
            kind,
        )


def show_message(
    parent: QWidget | None,
    title: str,
    text: str,
    kind: str = "info",
) -> None:
    """
    Показать фирменное сообщение.
    """

    dialog = ModernMessageDialog(
        parent,
        title=title,
        text=text,
        kind=kind,
    )

    dialog.exec()


def show_error(
    parent: QWidget | None,
    text: str,
) -> None:
    """
    Показать сообщение об ошибке.
    """

    show_message(
        parent,
        "Ошибка",
        text,
        "error",
    )


def show_warning(
    parent: QWidget | None,
    title: str,
    text: str,
) -> None:
    """
    Показать предупреждение.
    """

    show_message(
        parent,
        title,
        text,
        "warning",
    )


def show_info(
    parent: QWidget | None,
    title: str,
    text: str,
) -> None:
    """
    Показать информационное сообщение.
    """

    show_message(
        parent,
        title,
        text,
        "info",
    )