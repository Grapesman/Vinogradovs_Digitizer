"""Smoke-тест интерфейса Vinogradov's Digitizer.

Тест не открывает реальные диалоговые окна и не требует действий
пользователя. Он проверяет создание интерфейса, основные настройки,
защиту параметров и подключение модуля dialogs.py.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)


def test_modern_ui_editable_fields_and_diagnostics():
    import pytest

    pytest.importorskip(
        "PySide6"
    )

    from PySide6.QtWidgets import QApplication

    from digitizer.dialogs import (
        default_user_directory,
        open_file,
        save_file,
        show_error,
        show_info,
        show_warning,
    )
    from digitizer.main_window import (
        CONTROL_PANEL_WIDTH,
        MainWindow,
    )
    from digitizer.resources import (
        APP_DISPLAY_NAME,
        APP_VERSION,
    )

    app = (
        QApplication.instance()
        or QApplication([])
    )

    window = MainWindow()

    try:
        # ----------------------------------------------------
        # Основное окно
        # ----------------------------------------------------

        assert window.windowTitle().startswith(
            APP_DISPLAY_NAME
        )

        assert APP_VERSION == "2.3.0"

        assert window.minimumWidth() <= 1000
        assert window.minimumHeight() <= 650

        # ----------------------------------------------------
        # Правая панель
        # ----------------------------------------------------
        #
        # Панель должна иметь строго фиксированную ширину.
        # Пользователь не должен случайно растягивать её
        # через QSplitter и уменьшать рабочую область графика.
        # ----------------------------------------------------

        assert CONTROL_PANEL_WIDTH == 500

        assert (
            window.controls.minimumWidth()
            == CONTROL_PANEL_WIDTH
        )

        assert (
            window.controls.maximumWidth()
            == CONTROL_PANEL_WIDTH
        )

        splitter_handle = window.splitter.handle(1)

        assert splitter_handle is not None
        assert not splitter_handle.isEnabled()

        # ----------------------------------------------------
        # Рекомендуемый профиль распознавания
        # ----------------------------------------------------

        assert window.precise_color.isChecked()

        assert (
            abs(
                window.competitor_margin.value()
                - 7.0
            )
            < 1e-9
        )

        assert (
            window.hue_tolerance.value()
            == 10
        )

        assert (
            abs(
                window.tolerance.value()
                - 28.0
            )
            < 1e-9
        )

        assert (
            abs(
                window.max_jump.value()
                - 24.0
            )
            < 1e-9
        )

        assert (
            window.max_gap.value()
            == 10
        )

        assert (
            window.smooth_window.value()
            == 9
        )

        assert (
            abs(
                window.grid_strength.value()
                - 1.1
            )
            < 1e-9
        )

        # ----------------------------------------------------
        # Параметры должны быть заблокированы до ✎
        # ----------------------------------------------------

        assert window.competitor_margin.isReadOnly()
        assert window.hue_tolerance.isReadOnly()
        assert window.tolerance.isReadOnly()
        assert window.max_jump.isReadOnly()
        assert window.max_gap.isReadOnly()
        assert window.smooth_window.isReadOnly()
        assert window.grid_strength.isReadOnly()

        # Тип шкалы также не должен случайно
        # меняться колесом или кликом.
        assert window.scale_type.isLocked()

        # ----------------------------------------------------
        # Числовой ввод с запятой
        # ----------------------------------------------------

        window.h1_value.setText(
            "122,75"
        )

        assert (
            abs(
                window.h1_value.value()
                - 122.75
            )
            < 1e-9
        )

        window.h2_value.setText(
            "2500,5"
        )

        assert (
            abs(
                window.h2_value.value()
                - 2500.5
            )
            < 1e-9
        )

        # ----------------------------------------------------
        # Фокус на графике
        # ----------------------------------------------------

        window.show()

        app.processEvents()

        assert not window.controls.isHidden()

        window.toggle_workspace()

        app.processEvents()

        assert window.controls.isHidden()

        window.toggle_workspace()

        app.processEvents()

        assert not window.controls.isHidden()

        # После возврата панели её ширина
        # должна остаться строго фиксированной.
        assert (
            window.controls.width()
            == CONTROL_PANEL_WIDTH
        )

        assert (
            window.controls.minimumWidth()
            == CONTROL_PANEL_WIDTH
        )

        assert (
            window.controls.maximumWidth()
            == CONTROL_PANEL_WIDTH
        )

        # ----------------------------------------------------
        # Модуль диалогов
        # ----------------------------------------------------

        assert callable(open_file)
        assert callable(save_file)
        assert callable(show_error)
        assert callable(show_info)
        assert callable(show_warning)

        start_dir = default_user_directory()

        assert isinstance(
            start_dir,
            Path,
        )

        assert start_dir.exists()
        assert start_dir.is_dir()

        # ----------------------------------------------------
        # Основные элементы должны существовать
        # ----------------------------------------------------

        assert window.canvas is not None
        assert window.scale_list is not None
        assert window.curve_list is not None
        assert window.table is not None
        assert window.depth_step is not None
        assert window.curve_scale_combo is not None

    finally:
        window.close()
        app.processEvents()