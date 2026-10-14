#!/usr/bin/env bash
set -Eeuo pipefail

export QT_QPA_PLATFORM=offscreen
export PYTHONPATH=/app

cd /app

python - <<'PY'
import os
from pathlib import Path

import cv2
import numpy

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
    APP_NAME,
    APP_VERSION,
    WELCOME_TEXT,
)


print("==============================================")
print(" Vinogradov's Digitizer — Docker Smoke Test")
print("==============================================")
print()


# ------------------------------------------------------------
# QApplication
# ------------------------------------------------------------

app = QApplication.instance() or QApplication([])

window = MainWindow()


# ------------------------------------------------------------
# Название и версия
# ------------------------------------------------------------

assert APP_NAME == "Vinogradovs Digitizer"
assert APP_DISPLAY_NAME == "Vinogradov's Digitizer"
assert APP_VERSION == "2.3.0"

assert (
    WELCOME_TEXT
    == "Добро пожаловать в дигитайзер Виноградова"
)

assert window.windowTitle().startswith(
    APP_DISPLAY_NAME
)


# ------------------------------------------------------------
# Размеры интерфейса
# ------------------------------------------------------------

assert window.minimumWidth() <= 1000

# Правая панель должна быть строго фиксированной ширины.
assert CONTROL_PANEL_WIDTH == 500

assert (
    window.controls.minimumWidth()
    == CONTROL_PANEL_WIDTH
)

assert (
    window.controls.maximumWidth()
    == CONTROL_PANEL_WIDTH
)

# Разделитель панели должен быть заблокирован,
# чтобы пользователь не мог случайно растянуть
# панель и закрыть большую часть графика.
splitter_handle = window.splitter.handle(1)

assert splitter_handle is not None
assert not splitter_handle.isEnabled()


# ------------------------------------------------------------
# Основные параметры распознавания
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Параметры должны быть защищены
# от случайного изменения
# ------------------------------------------------------------

assert window.competitor_margin.isReadOnly()
assert window.hue_tolerance.isReadOnly()
assert window.tolerance.isReadOnly()
assert window.max_jump.isReadOnly()
assert window.max_gap.isReadOnly()
assert window.smooth_window.isReadOnly()
assert window.grid_strength.isReadOnly()


# ------------------------------------------------------------
# Тип шкалы также заблокирован
# до нажатия на карандаш
# ------------------------------------------------------------

assert window.scale_type.isLocked()


# ------------------------------------------------------------
# Проверка ввода числа через запятую
# ------------------------------------------------------------

window.h1_value.setText(
    "123,45"
)

assert (
    abs(
        window.h1_value.value()
        - 123.45
    )
    < 1e-6
)


# ------------------------------------------------------------
# Проверка панели настроек
# ------------------------------------------------------------

window.showMaximized()

app.processEvents()

assert window.isMaximized()

# При скрытии панели рабочая область должна
# занимать всё доступное пространство.
window.toggle_workspace()

app.processEvents()

assert window.controls.isHidden()

# После возврата панель снова должна иметь
# строго фиксированную ширину 500 px.
window.toggle_workspace()

app.processEvents()

assert not window.controls.isHidden()

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


# ------------------------------------------------------------
# Проверка нового модуля диалогов
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Проверка папок Docker
# ------------------------------------------------------------

data_dir = Path(
    os.environ.get(
        "VINOGRADOVS_DATA_DIR",
        "/data",
    )
)

if data_dir.exists():
    print(
        "DATA DIR:",
        data_dir,
    )


host_home = Path(
    os.environ.get(
        "VINOGRADOVS_HOST_HOME",
        "/host/home",
    )
)

if host_home.exists():
    print(
        "HOST HOME:",
        host_home,
    )


host_volumes = Path(
    os.environ.get(
        "VINOGRADOVS_HOST_VOLUMES",
        "/host/volumes",
    )
)

if host_volumes.exists():
    print(
        "HOST VOLUMES:",
        host_volumes,
    )


# ------------------------------------------------------------
# Завершение
# ------------------------------------------------------------

window.close()

app.processEvents()


print()
print("SMOKE TEST OK")
print(
    APP_DISPLAY_NAME,
    APP_VERSION,
)

print(
    "OpenCV:",
    cv2.__version__,
)

print(
    "NumPy:",
    numpy.__version__,
)

print(
    "Start directory:",
    start_dir,
)
PY