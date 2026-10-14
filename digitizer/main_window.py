from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QDoubleSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .dialogs import default_user_directory, open_file, save_file, show_error as show_error_dialog, show_info, show_warning
from .excel_export import build_output_dataframe, export_xlsx
from .image_canvas import ImageCanvas
from .models import AxisScale, CurveConfig, CurveData, DepthCalibration, ProjectData
from .processing import (
    auto_deskew,
    analyze_color_selection,
    curve_points_to_hv,
    curve_quality,
    delete_curve_near,
    detect_vertical_track_lines,
    edit_curve_point,
    estimate_scale_division,
    perspective_warp,
    palette_separation,
    rotate_image_90,
    trace_curve_from_seed,
)
from .project_io import load_project, save_project
from .resources import APP_DISPLAY_NAME, APP_NAME, APP_VERSION, resource_path


class NumericEdit(QLineEdit):
    """Directly editable numeric field; accepts both comma and dot decimals."""

    def __init__(self, value: float = 0.0, decimals: int = 6, parent=None):
        super().__init__(parent)
        self.decimals = decimals
        self.setValue(value)
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setClearButtonEnabled(True)

    def value(self) -> float:
        raw = self.text().strip().replace(" ", "").replace(",", ".")
        if not raw:
            raise ValueError("Числовое поле не заполнено")
        try:
            return float(raw)
        except ValueError as exc:
            raise ValueError(f"Некорректное число: {self.text()}") from exc

    def setValue(self, value: float) -> None:
        value = float(value)
        if abs(value) >= 1e7 or (0 < abs(value) < 1e-5):
            text = f"{value:.8g}"
        else:
            text = f"{value:.{self.decimals}f}".rstrip("0").rstrip(".")
        self.setText(text or "0")


RECOMMENDED_CURVE_DEFAULTS = {
    "color_tolerance": 28.0,
    "competitor_margin": 7.0,
    "hue_tolerance": 10,
    "max_jump_px": 24.0,
    "max_gap_rows": 10,
    "smooth_window": 9,
    "grid_strength": 1.1,
}

# The settings panel is intentionally fixed so it can never be
# accidentally stretched with QSplitter and cover the chart.
CONTROL_PANEL_WIDTH = 500


class _NumericParameterEdit(QLineEdit):
    """QLineEdit-based numeric editor used for recognition parameters.

    We intentionally do not use QSpinBox/QDoubleSpinBox here. On Windows the
    embedded line edit of a styled spin box can be clipped by Qt when display
    scaling is enabled, which makes the numeric value look completely blank.
    A direct QLineEdit has no nested editor, so the value is rendered reliably
    on Windows, macOS and Linux while keeping the same public API we need.
    """

    def __init__(self, *, integer: bool, parent=None):
        super().__init__(parent)
        self._integer = integer
        self._minimum = -2147483648 if integer else -1.0e100
        self._maximum = 2147483647 if integer else 1.0e100
        self._decimals = 0 if integer else 2
        self._single_step = 1.0
        self._last_valid_value = 0 if integer else 0.0

        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setClearButtonEnabled(False)
        self.editingFinished.connect(self._normalize_text)
        self.setValue(self._last_valid_value)

    def setRange(self, minimum, maximum) -> None:
        self._minimum = int(minimum) if self._integer else float(minimum)
        self._maximum = int(maximum) if self._integer else float(maximum)
        if self._minimum > self._maximum:
            self._minimum, self._maximum = self._maximum, self._minimum
        self.setValue(self._last_valid_value)

    def setDecimals(self, decimals: int) -> None:
        if self._integer:
            return
        self._decimals = max(0, int(decimals))
        self.setValue(self._last_valid_value)

    def setSingleStep(self, step) -> None:
        self._single_step = max(0.0, float(step))

    def setButtonSymbols(self, _symbols) -> None:
        # Compatibility with the old QAbstractSpinBox-based implementation.
        pass

    def value(self):
        raw = self.text().strip().replace(" ", "").replace(",", ".")
        try:
            parsed = int(float(raw)) if self._integer else float(raw)
        except (TypeError, ValueError):
            parsed = self._last_valid_value

        parsed = max(self._minimum, min(self._maximum, parsed))
        return int(parsed) if self._integer else float(parsed)

    def setValue(self, value) -> None:
        value = int(round(float(value))) if self._integer else float(value)
        value = max(self._minimum, min(self._maximum, value))
        self._last_valid_value = int(value) if self._integer else float(value)

        if self._integer:
            text = str(int(value))
        else:
            text = f"{float(value):.{self._decimals}f}"
        self.setText(text)

    def _normalize_text(self) -> None:
        self.setValue(self.value())

    def set_locked_appearance(self, locked: bool) -> None:
        if locked:
            self.setStyleSheet(
                "QLineEdit { min-height: 37px; padding: 0 9px; "
                "color: #30465b; background: #eef3f7; "
                "border: 1px solid #d9e2ea; border-radius: 8px; }"
            )
        else:
            self.setStyleSheet(
                "QLineEdit { min-height: 37px; padding: 0 9px; "
                "color: #102d43; background: #ffffff; "
                "border: 2px solid #287c9d; border-radius: 8px; }"
            )

    def wheelEvent(self, event):
        event.ignore()


class NoWheelSpinBox(_NumericParameterEdit):
    """Integer recognition parameter that never changes on mouse-wheel scroll."""

    def __init__(self, parent=None):
        super().__init__(integer=True, parent=parent)


class NoWheelDoubleSpinBox(_NumericParameterEdit):
    """Floating-point recognition parameter with reliable Windows rendering."""

    def __init__(self, parent=None):
        super().__init__(integer=False, parent=parent)

class NoWheelComboBox(QComboBox):
    """
    ComboBox, который:
    - не переключается колесом мыши;
    - может быть заблокирован до нажатия на карандаш.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._locked = False

    def setLocked(self, locked: bool) -> None:
        self._locked = locked
        self.setProperty("locked", locked)

        self.style().unpolish(self)
        self.style().polish(self)

    def isLocked(self) -> bool:
        return self._locked

    def wheelEvent(self, event):
        # Никогда не менять значение при прокрутке панели.
        event.ignore()

    def mousePressEvent(self, event):
        if self._locked:
            event.ignore()
            return

        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if self._locked:
            event.ignore()
            return

        super().keyPressEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_DISPLAY_NAME} {APP_VERSION}")
        self.setWindowIcon(QIcon(str(resource_path("assets/VinogradovsDigitizer.ico"))))
        self.resize(1430, 800)
        self.setMinimumSize(980, 610)

        self.data_dir = Path(os.environ.get("VINOGRADOVS_DATA_DIR", str(default_user_directory()))).resolve()
        self.last_dialog_dir = default_user_directory()
        self.image_path = ""
        self.source_image_path = ""
        self.image_bgr: np.ndarray | None = None
        self.original_image_bgr: np.ndarray | None = None

        self.h1_point: QPointF | None = None
        self.h2_point: QPointF | None = None
        self.track_guides: list[int] = []

        self.scales: list[AxisScale] = []
        self.scale_edit_index: int | None = None
        self.scale_x1_point: QPointF | None = None
        self.scale_x2_point: QPointF | None = None
        self.scale_roi: QRectF | None = None

        self.curves: list[CurveData] = []
        self.curve_edit_index: int | None = None
        self.current_curve_roi: QRectF | None = None
        self.curve_samples: list[tuple[QPointF, tuple[int, int, int]]] = []
        self.roi_purpose: str = "curve"
        self.color_pick_purpose: str = "curve_sample"

        self._last_df: pd.DataFrame | None = None
        self._last_mask: np.ndarray | None = None

        self.canvas = ImageCanvas()
        self.canvas.roiSelected.connect(self.on_roi_selected)
        self.canvas.pointPicked.connect(self.on_point_picked)
        self.canvas.colorPicked.connect(self.on_color_picked)
        self.canvas.mouseMovedImage.connect(self.on_mouse_moved)
        self.canvas.perspectiveSelected.connect(self.on_perspective_selected)
        self.canvas.editPointPicked.connect(self.on_edit_point)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(14, 11, 14, 9)
        root_layout.setSpacing(12)
        root_layout.addWidget(self._build_header())

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(10)
        canvas_frame = QFrame()
        canvas_frame.setObjectName("workspace")
        canvas_layout = QVBoxLayout(canvas_frame)
        canvas_layout.setContentsMargins(12, 10, 12, 12)
        canvas_layout.setSpacing(9)
        workspace_bar = QHBoxLayout()
        workspace_title = QLabel("РАБОЧАЯ ОБЛАСТЬ")
        workspace_title.setObjectName("workspaceTitle")
        workspace_bar.addWidget(workspace_title)
        self.image_label = QLabel("Изображение не загружено")
        self.image_label.setObjectName("imageLabel")
        self.image_label.setMinimumWidth(0)
        workspace_bar.addWidget(self.image_label, 1)
        fit = self._soft("⤢  Вписать")
        fit.setToolTip(
            "Автоматически изменить масштаб отображения так, чтобы всё изображение "
            "полностью помещалось в рабочую область. Сам файл и его разрешение не изменяются."
        )
        fit.clicked.connect(self.canvas.fit_image)
        workspace_bar.addWidget(fit)
        self.toggle_workspace_button = self._soft("◫  Фокус на графике")
        self.toggle_workspace_button.setToolTip(
            "Временно скрыть или показать правую панель настроек. "
            "Полезно, когда нужно увеличить площадь графика для точной разметки."
        )
        self.toggle_workspace_button.clicked.connect(self.toggle_workspace)
        workspace_bar.addWidget(self.toggle_workspace_button)
        canvas_layout.addLayout(workspace_bar)
        canvas_layout.addWidget(self.canvas, 1)
        self.splitter.addWidget(canvas_frame)

        self.controls = self._build_controls()
        self.controls.setFixedWidth(CONTROL_PANEL_WIDTH)
        self.controls.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Expanding,
        )

        self.splitter.addWidget(self.controls)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([1100, CONTROL_PANEL_WIDTH])

        # The settings panel has a deliberate fixed width. Disable the
        # splitter handle so an accidental drag can never make it cover
        # a larger part of the chart.
        handle = self.splitter.handle(1)
        if handle is not None:
            handle.setEnabled(False)

        root_layout.addWidget(self.splitter, 1)
        self.setCentralWidget(root)

        self.status = QLabel("Готово")
        self.statusBar().addPermanentWidget(self.status, 1)

        # Верхнее меню Файл / Вид / Справка намеренно отсутствует.
        # Все основные действия доступны из рабочего интерфейса.
        self.menuBar().setVisible(False)

        self.new_scale_editor()
        self.new_curve_editor()

    # ---------------- UI helpers ----------------
    def _build_header(self) -> QWidget:
        """
        Компактная шапка рабочего приложения.

        Никаких приветствий и технических надписей.
        Они используются только на заставке.
        """
        header = QFrame()
        header.setObjectName("appHeader")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 6, 14, 6)
        layout.setSpacing(10)

        logo = QLabel()

        pix = QPixmap(
            str(
                resource_path(
                    "assets/app_icon.png"
                )
            )
        )

        if not pix.isNull():
            logo.setPixmap(
                pix.scaled(
                    44,
                    44,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

        logo.setFixedSize(48, 48)
        logo.setAlignment(Qt.AlignCenter)

        layout.addWidget(logo)

        title = QLabel(
            "Vinogradov's Digitizer"
        )

        title.setObjectName("appTitle")

        layout.addWidget(title)

        # Всё свободное пространство справа.
        # Никаких OpenCV / локально / статусов.
        layout.addStretch(1)

        return header

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("Файл")
        for text, slot, shortcut in [
            ("Открыть изображение…", self.open_image, "Ctrl+O"),
            ("Открыть проект…", self.open_project, "Ctrl+Shift+O"),
            ("Сохранить проект…", self.save_project_dialog, "Ctrl+S"),
            ("Экспорт Excel…", self.export_excel, "Ctrl+E"),
        ]:
            act = QAction(text, self)
            act.triggered.connect(slot)
            act.setShortcut(shortcut)
            file_menu.addAction(act)

        view_menu = self.menuBar().addMenu("Вид")
        fit_act = QAction("Вписать изображение", self)
        fit_act.setShortcut("F")
        fit_act.triggered.connect(self.canvas.fit_image)
        view_menu.addAction(fit_act)
        expand_act = QAction("Показать или скрыть настройки", self)
        expand_act.setShortcut("F11")
        expand_act.triggered.connect(self.toggle_workspace)
        view_menu.addAction(expand_act)

        help_menu = self.menuBar().addMenu("Справка")
        help_act = QAction("Порядок работы", self)
        help_act.triggered.connect(self.show_quick_help)
        help_menu.addAction(help_act)
        about_act = QAction("О программе", self)
        about_act.triggered.connect(self.show_about)
        help_menu.addAction(about_act)

    def _build_controls(self) -> QWidget:
        tabs = QTabWidget()
        tabs.addTab(self._build_prepare_tab(), "Подготовка")
        tabs.addTab(self._build_scales_tab(), "Шкалы")
        tabs.addTab(self._build_curves_tab(), "Кривые")
        tabs.addTab(self._build_output_tab(), "Результат")
        tabs.setObjectName("workspaceTabs")
        tabs.setDocumentMode(True)
        tabs.setFixedWidth(CONTROL_PANEL_WIDTH)
        return tabs

    @staticmethod
    def _scroll(content: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        content.setMinimumWidth(0)
        area.setWidget(content)
        return area

    @staticmethod
    def _card(title: str, hint: str = "") -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(17, 15, 17, 17)
        layout.setSpacing(11)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        layout.addWidget(title_label)
        if hint:
            hint_label = QLabel(hint)
            hint_label.setWordWrap(True)
            hint_label.setObjectName("cardHint")
            layout.addWidget(hint_label)
        return card, layout

    @staticmethod
    def _primary(text: str) -> QPushButton:
        b = QPushButton(text)
        b.setProperty("primary", True)
        return b

    @staticmethod
    def _soft(text: str) -> QPushButton:
        b = QPushButton(text)
        b.setProperty("soft", True)
        return b

    @staticmethod
    def _danger(text: str) -> QPushButton:
        b = QPushButton(text)
        b.setProperty("danger", True)
        return b

    def _set_locked_numeric(self, widget, locked: bool, button: QToolButton | None = None) -> None:
        widget.setReadOnly(locked)
        widget.setButtonSymbols(QAbstractSpinBox.NoButtons)
        widget.setProperty("locked", locked)
        if hasattr(widget, "set_locked_appearance"):
            widget.set_locked_appearance(locked)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        if button is not None:
            button.setText("✎" if locked else "✓")
            button.setToolTip("Изменить параметр" if locked else "Сохранить значение")

    def _parameter_row(self, label_text: str, widget, hint: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)

        label = QLabel(label_text)
        label.setObjectName("parameterLabel")
        label.setMinimumWidth(108)
        layout.addWidget(label)
        layout.addWidget(widget, 1)

        edit = QToolButton()
        edit.setObjectName("editParameter")
        edit.setFixedSize(30, 30)
        edit.clicked.connect(lambda _checked=False, w=widget, b=edit: self._set_locked_numeric(w, not w.isReadOnly(), b))
        layout.addWidget(edit)

        info = QToolButton()
        info.setObjectName("infoParameter")
        info.setText("?")
        info.setFixedSize(30, 30)
        info.setToolTip(hint)
        info.clicked.connect(lambda _checked=False, title=label_text, text=hint: show_info(self, title, text))
        layout.addWidget(info)

        widget._vinogradovs_edit_button = edit
        self._set_locked_numeric(widget, True, edit)
        return row

    def _set_locked_combo(
            self,
            widget: NoWheelComboBox,
            locked: bool,
            button: QToolButton | None = None,
    ) -> None:

        widget.setLocked(locked)

        if button is not None:
            button.setText("✎" if locked else "✓")

            button.setToolTip(
                "Изменить значение"
                if locked
                else "Сохранить значение"
            )

    def _combo_parameter_row(
            self,
            label_text: str,
            widget: NoWheelComboBox,
            hint: str,
    ) -> QWidget:

        row = QWidget()

        layout = QHBoxLayout(row)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)

        label = QLabel(label_text)

        label.setObjectName("parameterLabel")
        label.setMinimumWidth(105)

        layout.addWidget(label)
        layout.addWidget(widget, 1)

        edit = QToolButton()

        edit.setObjectName("editParameter")
        edit.setFixedSize(30, 30)

        edit.clicked.connect(
            lambda _checked=False, w=widget, b=edit:
            self._set_locked_combo(
                w,
                not w.isLocked(),
                b,
            )
        )

        layout.addWidget(edit)

        info = QToolButton()

        info.setObjectName("infoParameter")
        info.setText("?")
        info.setFixedSize(30, 30)

        info.setToolTip(hint)

        info.clicked.connect(
            lambda _checked=False,
                   title=label_text,
                   text=hint:
            show_info(self, title, text)
        )

        layout.addWidget(info)

        widget._vinogradovs_edit_button = edit

        self._set_locked_combo(
            widget,
            True,
            edit,
        )

        return row

    def _lock_recognition_parameters(self) -> None:
        for widget in (self.competitor_margin, self.hue_tolerance, self.tolerance, self.max_jump, self.max_gap, self.smooth_window, self.grid_strength):
            button = getattr(widget, "_vinogradovs_edit_button", None)
            self._set_locked_numeric(widget, True, button)

    def reset_curve_recognition_defaults(self) -> None:
        d = RECOMMENDED_CURVE_DEFAULTS
        self.tolerance.setValue(d["color_tolerance"])
        self.competitor_margin.setValue(d["competitor_margin"])
        self.hue_tolerance.setValue(d["hue_tolerance"])
        self.max_jump.setValue(d["max_jump_px"])
        self.max_gap.setValue(d["max_gap_rows"])
        self.smooth_window.setValue(d["smooth_window"])
        self.grid_strength.setValue(d["grid_strength"])
        self.precise_color.setChecked(True)
        self.remove_grid.setChecked(True)
        self.color_diagnostics.setText(
            "Включён рекомендуемый точный профиль для близких цветов. "
            "Параметры защищены от случайного изменения колесом мыши; нажмите ✎, если нужна ручная настройка."
        )

    def _build_prepare_tab(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(10)

        card, cl = self._card(
            "Изображение",
            "Сначала выровняйте фотографию. Геометрические операции сбрасывают калибровку, чтобы координаты не устаревали.",
        )
        row = QHBoxLayout()
        open_btn = self._primary("Открыть фото")
        open_btn.setToolTip(
            "Открыть изображение диаграммы для оцифровки. Поддерживаются PNG, JPG, JPEG и BMP."
        )
        open_btn.clicked.connect(self.open_image)
        left_btn = QPushButton("↺ 90°")
        left_btn.setToolTip("Повернуть изображение на 90° против часовой стрелки. Калибровка будет сброшена.")
        left_btn.clicked.connect(lambda: self.rotate(False))
        right_btn = QPushButton("↻ 90°")
        right_btn.setToolTip("Повернуть изображение на 90° по часовой стрелке. Калибровка будет сброшена.")
        right_btn.clicked.connect(lambda: self.rotate(True))
        row.addWidget(open_btn, 2)
        row.addWidget(left_btn)
        row.addWidget(right_btn)
        cl.addLayout(row)
        deskew = QPushButton("Автовыравнивание")
        deskew.setToolTip(
            "Автоматически определить небольшой наклон изображения по линиям сетки "
            "и выровнять фотографию. После операции калибровка сбрасывается."
        )
        deskew.clicked.connect(self.do_auto_deskew)
        persp = QPushButton("Коррекция перспективы • 4 точки")
        persp.setToolTip(
            "Исправить перспективное искажение фотографии. После нажатия укажите четыре угла "
            "прямоугольной рабочей области. Программа преобразует её в ровный прямоугольник."
        )
        persp.clicked.connect(self.start_perspective)
        fit = QPushButton("Вписать изображение в окно")
        fit.setToolTip(
            "Подогнать только масштаб отображения изображения под размер рабочей области. "
            "Исходное изображение не изменяется."
        )
        fit.clicked.connect(self.canvas.fit_image)
        reset = self._soft("Вернуть исходное фото")
        reset.setToolTip(
            "Отменить геометрические преобразования и снова использовать исходное загруженное изображение. "
            "Калибровка и распознанные кривые будут сброшены."
        )
        reset.clicked.connect(self.reset_to_original)
        cl.addWidget(deskew)
        cl.addWidget(persp)
        cl.addWidget(fit)
        cl.addWidget(reset)
        layout.addWidget(card)

        card, cl = self._card(
            "Калибровка глубины",
            "Цифры можно вводить с клавиатуры. Укажите на изображении две горизонтали с известной глубиной.",
        )
        form = QFormLayout()
        self.h1_value = NumericEdit(20.0, 4)
        self.h2_value = NumericEdit(200.0, 4)
        form.addRow("H1, м", self.h1_value)
        form.addRow("H2, м", self.h2_value)
        cl.addLayout(form)
        row = QHBoxLayout()
        h1b = QPushButton("Указать H1")
        h2b = QPushButton("Указать H2")
        h1b.setToolTip(
            "После нажатия щёлкните по изображению на горизонтали, соответствующей введённому значению H1."
        )
        h2b.setToolTip(
            "После нажатия щёлкните по второй известной горизонтали H2. По H1 и H2 программа вычислит масштаб глубины."
        )
        h1b.clicked.connect(lambda: self.canvas.set_mode("h1"))
        h2b.clicked.connect(lambda: self.canvas.set_mode("h2"))
        row.addWidget(h1b)
        row.addWidget(h2b)
        cl.addLayout(row)
        self.depth_info = QLabel("Две точки ещё не заданы")
        self.depth_info.setObjectName("cardHint")
        cl.addWidget(self.depth_info)
        layout.addWidget(card)

        card, cl = self._card(
            "Границы дорожек",
            "OpenCV может подсветить вероятные вертикальные разделители как ориентиры. Это не меняет данные.",
        )
        self.track_info = QLabel("Границы пока не найдены")
        self.track_info.setObjectName("cardHint")
        cl.addWidget(self.track_info)
        row = QHBoxLayout()
        find_btn = QPushButton("Найти")
        find_btn.setToolTip(
            "Попытаться автоматически найти вертикальные линии-разделители между дорожками диаграммы. "
            "Они показываются только как вспомогательные ориентиры."
        )
        find_btn.clicked.connect(self.find_tracks)
        clear_btn = QPushButton("Скрыть")
        clear_btn.setToolTip(
            "Скрыть найденные вспомогательные границы дорожек. Исходное изображение не изменяется."
        )
        clear_btn.clicked.connect(self.clear_tracks)
        row.addWidget(find_btn)
        row.addWidget(clear_btn)
        cl.addLayout(row)
        layout.addWidget(card)
        layout.addStretch(1)
        return self._scroll(content)

    def _build_scales_tab(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(10)

        card, cl = self._card(
            "Шкалы значений",
            "Создавайте столько шкал, сколько нужно. Одну шкалу можно назначить нескольким кривым.",
        )
        self.scale_list = QListWidget()
        self.scale_list.setMinimumHeight(110)
        self.scale_list.itemDoubleClicked.connect(self.load_scale_to_editor)
        cl.addWidget(self.scale_list)
        row = QHBoxLayout()
        add = self._primary("+ Новая шкала")
        add.setToolTip("Создать новую независимую шкалу значений для одной или нескольких кривых.")
        add.clicked.connect(self.new_scale_editor)
        remove = self._danger("Удалить")
        remove.setToolTip("Удалить выбранную шкалу. Шкалу нельзя удалить, пока она назначена какой-либо кривой.")
        remove.clicked.connect(self.remove_selected_scale)
        row.addWidget(add)
        row.addWidget(remove)
        cl.addLayout(row)
        layout.addWidget(card)

        card, cl = self._card(
            "Калибровка шкалы",
            "Введите минимум и максимум вручную, затем выделите область шкалы на изображении. Программа сама вычислит преобразование пиксель → значение и попробует оценить цену деления.",
        )
        form = QFormLayout()
        self.scale_name = QLineEdit("Время")
        self.scale_unit = QLineEdit("мкс")
        self.scale_min = NumericEdit(250.0, 6)
        self.scale_max = NumericEdit(650.0, 6)
        self.scale_type = NoWheelComboBox()

        self.scale_type.addItem(
            "Линейная",
            "linear",
        )

        self.scale_type.addItem(
            "Логарифмическая",
            "log",
        )
        form.addRow("Название", self.scale_name)
        form.addRow("Единица", self.scale_unit)
        form.addRow("Минимум", self.scale_min)
        form.addRow("Максимум", self.scale_max)
        cl.addLayout(form)
        cl.addWidget(
            self._combo_parameter_row(
                "Тип шкалы",
                self.scale_type,
                "Определяет математическое преобразование координаты X "
                "в физическое значение.\n\n"
                "Линейная — одинаковому расстоянию на графике соответствует "
                "одинаковое изменение значения.\n\n"
                "Пример: 100, 200, 300, 400.\n\n"
                "Логарифмическая — одинаковому расстоянию соответствуют "
                "одинаковые отношения значений.\n\n"
                "Пример: 1, 10, 100, 1000.\n\n"
                "Для изменения нажмите ✎."
            )
        )

        roi_btn = self._primary("Выделить область шкалы")
        roi_btn.setToolTip(
            "Выделить прямоугольником участок изображения, соответствующий диапазону этой шкалы. "
            "Левая и правая границы будут использованы как опорные положения минимума и максимума."
        )
        roi_btn.clicked.connect(self.start_scale_roi)
        cl.addWidget(roi_btn)
        row = QHBoxLayout()
        p1 = QPushButton("Левая/первая отметка")
        p2 = QPushButton("Правая/вторая отметка")
        p1.setToolTip(
            "Указать на изображении положение первой известной отметки шкалы. Ей соответствует минимальное значение."
        )
        p2.setToolTip(
            "Указать положение второй известной отметки шкалы. Ей соответствует максимальное значение."
        )
        p1.clicked.connect(lambda: self.canvas.set_mode("scale_x1"))
        p2.clicked.connect(lambda: self.canvas.set_mode("scale_x2"))
        row.addWidget(p1)
        row.addWidget(p2)
        cl.addLayout(row)

        self.scale_geometry_info = QLabel("Область шкалы не задана")
        self.scale_geometry_info.setObjectName("cardHint")
        self.scale_division_info = QLabel("Цена деления: —")
        self.scale_division_info.setObjectName("cardHint")
        cl.addWidget(self.scale_geometry_info)
        cl.addWidget(self.scale_division_info)
        save = self._primary("Сохранить / обновить шкалу")
        save.setToolTip(
            "Сохранить параметры шкалы и рассчитанное преобразование между координатами изображения "
            "и физическими значениями."
        )
        save.clicked.connect(self.save_scale_from_editor)
        cl.addWidget(save)
        layout.addWidget(card)
        layout.addStretch(1)
        return self._scroll(content)

    def _build_curves_tab(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(10)

        card, cl = self._card(
            "Кривые",
            "Количество кривых не ограничено. Дважды кликните по кривой, чтобы изменить её настройки.",
        )
        self.curve_list = QListWidget()
        self.curve_list.setMinimumHeight(125)
        self.curve_list.itemDoubleClicked.connect(self.load_curve_to_editor)
        self.curve_list.currentRowChanged.connect(lambda _row: self.redraw_overlays())
        cl.addWidget(self.curve_list)
        row = QHBoxLayout()
        add = self._primary("+ Новая кривая")
        add.setToolTip("Создать новую кривую и настроить для неё шкалу, область поиска и образцы цвета.")
        add.clicked.connect(self.new_curve_editor)
        remove = self._danger("Удалить")
        remove.setToolTip("Удалить выбранную распознанную кривую из проекта.")
        remove.clicked.connect(self.remove_selected_curve)
        row.addWidget(add)
        row.addWidget(remove)
        cl.addLayout(row)
        layout.addWidget(card)

        card, cl = self._card(
            "Настройка кривой",
            "Выберите шкалу, область самой кривой и один или несколько образцов цвета пипеткой.",
        )
        form = QFormLayout()
        self.curve_name = QLineEdit("T1")
        self.curve_unit = QLineEdit("мкс")
        self.curve_scale_combo = NoWheelComboBox()
        self.curve_scale_combo.currentIndexChanged.connect(self.on_curve_scale_changed)
        form.addRow("Имя столбца", self.curve_name)
        form.addRow("Единица", self.curve_unit)
        form.addRow("Шкала", self.curve_scale_combo)
        cl.addLayout(form)

        roi = QPushButton("Выделить область кривой")
        roi.setToolTip(
            "Ограничить прямоугольником область поиска этой кривой. Чем точнее выделена дорожка, "
            "тем меньше вероятность захватить соседнюю кривую или сетку."
        )
        roi.clicked.connect(self.start_curve_roi)
        cl.addWidget(roi)
        self.curve_roi_info = QLabel("ROI кривой не задан")
        self.curve_roi_info.setObjectName("cardHint")
        cl.addWidget(self.curve_roi_info)

        sample_title = QLabel("Образцы цвета")
        sample_title.setObjectName("cardTitle")
        cl.addWidget(sample_title)
        self.sample_list = QListWidget()
        self.sample_list.setMinimumHeight(92)
        cl.addWidget(self.sample_list)
        row = QHBoxLayout()
        sample = self._primary("Пипетка + образец")
        sample.setToolTip(
            "Выбрать образец цвета непосредственно на кривой. Для сложного или неравномерного скана "
            "желательно взять 2–4 образца одной кривой в разных местах."
        )
        sample.clicked.connect(self.start_color_pick)
        remove_sample = QPushButton("Удалить образец")
        remove_sample.setToolTip("Удалить выбранный цветовой образец текущей кривой.")
        remove_sample.clicked.connect(self.remove_selected_sample)
        row.addWidget(sample)
        row.addWidget(remove_sample)
        cl.addLayout(row)

        adv = QFrame()
        adv.setObjectName("parameterPanel")
        adv_layout = QVBoxLayout(adv)
        adv_layout.setContentsMargins(10, 10, 10, 10)
        adv_layout.setSpacing(7)

        adv_title_row = QHBoxLayout()
        adv_title = QLabel("Точная настройка распознавания")
        adv_title.setObjectName("cardTitle")
        adv_title_row.addWidget(adv_title)
        adv_title_row.addStretch(1)
        reset_defaults = QToolButton()
        reset_defaults.setObjectName("resetParameters")
        reset_defaults.setText("↺ По умолчанию")
        reset_defaults.setToolTip("Вернуть рекомендуемые значения для различения близких цветов")
        reset_defaults.clicked.connect(self.reset_curve_recognition_defaults)
        adv_title_row.addWidget(reset_defaults)
        adv_layout.addLayout(adv_title_row)

        self.precise_color = QCheckBox("Различать похожие цвета и не смешивать кривые")
        self.precise_color.setChecked(True)
        self.precise_color.setToolTip(
            "Сравнивает выбранный цвет с палитрами соседних кривых и исключает неоднозначные пиксели."
        )
        adv_layout.addWidget(self.precise_color)

        self.competitor_margin = NoWheelDoubleSpinBox()
        self.competitor_margin.setRange(0.0, 25.0)
        self.competitor_margin.setDecimals(1)
        self.competitor_margin.setSingleStep(0.5)
        self.competitor_margin.setValue(RECOMMENDED_CURVE_DEFAULTS["competitor_margin"])
        adv_layout.addWidget(self._parameter_row(
            "Разделение цветов, LAB", self.competitor_margin,
            "Насколько выбранный цвет должен быть ближе к текущей кривой, чем к соседней.\n\n"
            "↑ Увеличить — строже разделять похожие цвета, меньше смешивания, но возможно больше пропусков.\n"
            "↓ Уменьшить — больше точек будет принято, но возрастает риск захватить соседнюю кривую."
        ))

        self.hue_tolerance = NoWheelSpinBox()
        self.hue_tolerance.setRange(2, 90)
        self.hue_tolerance.setValue(RECOMMENDED_CURVE_DEFAULTS["hue_tolerance"])
        adv_layout.addWidget(self._parameter_row(
            "Допуск оттенка, ×2°", self.hue_tolerance,
            "Допуск по цветовому тону HSV.\n\n"
            "↑ Увеличить — если одна кривая заметно меняет оттенок из-за освещения или качества скана.\n"
            "↓ Уменьшить — если рядом находятся кривые очень похожих цветов и их нужно разделять строже."
        ))

        self.tolerance = NoWheelDoubleSpinBox()
        self.tolerance.setRange(1, 180)
        self.tolerance.setValue(RECOMMENDED_CURVE_DEFAULTS["color_tolerance"])
        self.tolerance.setDecimals(1)
        adv_layout.addWidget(self._parameter_row(
            "Допуск цвета LAB", self.tolerance,
            "Допустимое расстояние от образца цвета в пространстве LAB.\n\n"
            "↑ Увеличить — принимать больше оттенков той же линии, полезно при выцветании.\n"
            "↓ Уменьшить — повысить цветовую строгость, если захватывается соседняя линия или сетка."
        ))

        self.max_jump = NoWheelDoubleSpinBox()
        self.max_jump.setRange(2, 400)
        self.max_jump.setValue(RECOMMENDED_CURVE_DEFAULTS["max_jump_px"])
        adv_layout.addWidget(self._parameter_row(
            "Макс. скачок, px", self.max_jump,
            "Максимальное горизонтальное смещение между соседними найденными точками.\n\n"
            "↑ Увеличить — для кривых с резкими реальными скачками.\n"
            "↓ Уменьшить — если трассировка перескакивает на соседнюю кривую."
        ))

        self.max_gap = NoWheelSpinBox()
        self.max_gap.setRange(0, 200)
        self.max_gap.setValue(RECOMMENDED_CURVE_DEFAULTS["max_gap_rows"])
        adv_layout.addWidget(self._parameter_row(
            "Разрыв, строк", self.max_gap,
            "Сколько строк программа может пройти без уверенного пикселя, продолжая ту же кривую.\n\n"
            "↑ Увеличить — соединять более длинные разрывы линии.\n"
            "↓ Уменьшить — не соединять удалённые фрагменты ошибочно."
        ))

        self.smooth_window = NoWheelSpinBox()
        self.smooth_window.setRange(3, 81)
        self.smooth_window.setSingleStep(2)
        self.smooth_window.setValue(RECOMMENDED_CURVE_DEFAULTS["smooth_window"])
        adv_layout.addWidget(self._parameter_row(
            "Сглаживание", self.smooth_window,
            "Размер окна сглаживания найденной траектории.\n\n"
            "↑ Увеличить — получить более плавную кривую и подавить шум.\n"
            "↓ Уменьшить — сохранить мелкие реальные детали и резкие изменения."
        ))

        self.remove_grid = QCheckBox("Подавлять длинные линии сетки")
        self.remove_grid.setChecked(True)
        self.remove_grid.setToolTip("Убирает длинные горизонтальные и вертикальные линии сетки перед трассировкой")
        adv_layout.addWidget(self.remove_grid)

        self.grid_strength = NoWheelDoubleSpinBox()
        self.grid_strength.setRange(0.35, 3.0)
        self.grid_strength.setSingleStep(0.1)
        self.grid_strength.setValue(RECOMMENDED_CURVE_DEFAULTS["grid_strength"])
        adv_layout.addWidget(self._parameter_row(
            "Подавление сетки", self.grid_strength,
            "Интенсивность удаления длинных линий сетки.\n\n"
            "↑ Увеличить — если сетка всё ещё попадает в маску.\n"
            "↓ Уменьшить — если вместе с сеткой начинают исчезать участки самой кривой."
        ))
        cl.addWidget(adv)

        row = QHBoxLayout()
        preview = QPushButton("Предпросмотр маски")
        preview.setToolTip(
            "Показать, какие пиксели программа считает принадлежащими выбранной кривой, "
            "без окончательной трассировки."
        )
        preview.clicked.connect(self.preview_mask)
        detect = self._primary("Распознать / обновить")
        detect.setToolTip(
            "Выполнить распознавание выбранной кривой с текущей шкалой, ROI, образцами цвета и параметрами."
        )
        detect.clicked.connect(self.detect_curve)
        row.addWidget(preview)
        row.addWidget(detect)
        cl.addLayout(row)
        self.color_diagnostics = QLabel(
            "Точная сегментация: после выбора двух кривых проверьте обе маски и "
            "нажмите «Перепроверить все». Спорные пиксели не будут угадываться."
        )
        self.color_diagnostics.setObjectName("diagnostic")
        self.color_diagnostics.setWordWrap(True)
        cl.addWidget(self.color_diagnostics)
        rebuild = self._soft("↻  Перепроверить все кривые")
        rebuild.setToolTip(
            "Повторно распознать все созданные кривые одновременно. Особенно полезно после добавления "
            "второй или третьей кривой похожего цвета: программа заново сравнит палитры и постарается "
            "не смешивать соседние линии."
        )
        rebuild.clicked.connect(self.redetect_all_curves)
        cl.addWidget(rebuild)
        layout.addWidget(card)

        card, cl = self._card(
            "Ручная коррекция",
            "Выберите готовую кривую в списке. Клик в режиме правки перемещает точку, режим удаления стирает ошибочные фрагменты.",
        )
        row = QHBoxLayout()
        move = QPushButton("Править точки")
        move.setToolTip("Перейти в режим ручного перемещения отдельных точек выбранной распознанной кривой.")
        move.clicked.connect(lambda: self.start_edit_mode("edit_move"))
        delete = QPushButton("Удалять точки")
        delete.setToolTip("Перейти в режим удаления ошибочно распознанных точек выбранной кривой.")
        delete.clicked.connect(lambda: self.start_edit_mode("edit_delete"))
        row.addWidget(move)
        row.addWidget(delete)
        cl.addLayout(row)
        stop = QPushButton("Завершить правку")
        stop.setToolTip("Выйти из режима ручного редактирования и вернуться к обычной работе с изображением.")
        stop.clicked.connect(lambda: self.canvas.set_mode(None))
        cl.addWidget(stop)
        layout.addWidget(card)
        layout.addStretch(1)
        return self._scroll(content)

    def _build_output_tab(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(10)
        card, cl = self._card(
            "Таблица и Excel",
            "Столбцы формируются автоматически: H и все распознанные кривые. Шаг глубины можно вписать вручную.",
        )
        form = QFormLayout()
        self.depth_step = NumericEdit(1.0, 4)
        form.addRow("Шаг H, м", self.depth_step)
        cl.addLayout(form)
        row = QHBoxLayout()
        table_btn = self._primary("Построить таблицу")
        table_btn.setToolTip(
            "Сформировать таблицу по заданному шагу глубины. Столбцы H и всех распознанных кривых создаются автоматически."
        )
        table_btn.clicked.connect(self.build_table)
        excel_btn = QPushButton("Экспорт .xlsx")
        excel_btn.setToolTip("Сохранить полную таблицу и параметры проекта в файл Microsoft Excel (.xlsx).")
        excel_btn.clicked.connect(self.export_excel)
        row.addWidget(table_btn)
        row.addWidget(excel_btn)
        cl.addLayout(row)
        self.table = QTableWidget(0, 0)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(355)
        self.table.horizontalHeader().setStretchLastSection(False)
        cl.addWidget(self.table)
        layout.addWidget(card)
        layout.addStretch(1)
        return self._scroll(content)

    def toggle_workspace(self):
        """Maximise the image inside the already-maximised Docker window."""
        if not self.controls.isHidden():
            self.controls.hide()
            self.toggle_workspace_button.setText("⤺  Показать настройки")
        else:
            self.controls.setFixedWidth(CONTROL_PANEL_WIDTH)
            self.controls.show()
            self.splitter.setSizes([1100, CONTROL_PANEL_WIDTH])
            self.toggle_workspace_button.setText("◫  Фокус на графике")
        self.canvas.fit_image()

    # ---------------- General ----------------
    def show_error(self, text: str):
        show_error_dialog(self, text)

    def show_quick_help(self):
        show_info(
            self,
            "Порядок работы",
            "1) Откройте и выровняйте фото.\n"
            "2) На вкладке «Подготовка» задайте H1/H2 и впишите их значения.\n"
            "3) На вкладке «Шкалы» создайте шкалу: минимум, максимум, тип и выделенная область.\n"
            "4) На вкладке «Кривые» создайте кривую, назначьте ей шкалу и ROI.\n"
            "5) Добавьте пипеткой 1–3 образца цвета одной и той же кривой.\n"
            "6) Повторите для любого количества кривых.\n"
            "7) Постройте таблицу и экспортируйте Excel.",
        )

    def show_about(self):
        show_info(
            self,
            f"О программе — {APP_DISPLAY_NAME}",
            f"{APP_DISPLAY_NAME}\nВерсия {APP_VERSION}\n\n"
            "Оцифровка геофизических диаграмм средствами OpenCV. "
            "Поддерживаются независимые шкалы, неограниченное число кривых "
            "и несколько образцов цвета.",
        )

    def _dialog_dir(self) -> str:
        if self.last_dialog_dir.exists():
            return str(self.last_dialog_dir)
        return str(default_user_directory())

    def _remember_dialog_path(self, path: str | Path) -> None:
        if not path:
            return
        p = Path(path).expanduser()
        parent = p if p.is_dir() else p.parent
        if parent.exists():
            self.last_dialog_dir = parent.resolve()

    @staticmethod
    def _read_image_file(path: str | Path) -> np.ndarray | None:
        """OpenCV image loading that also supports Cyrillic/Unicode Windows paths."""
        try:
            raw = np.fromfile(str(path), dtype=np.uint8)
            if raw.size == 0:
                return None
            return cv2.imdecode(raw, cv2.IMREAD_COLOR)
        except Exception:
            return None

    @staticmethod
    def _write_image_file(path: str | Path, image: np.ndarray) -> bool:
        """OpenCV image saving that also supports Cyrillic/Unicode Windows paths."""
        try:
            p = Path(path)
            suffix = p.suffix.lower() or ".png"
            if suffix not in {".png", ".jpg", ".jpeg", ".bmp"}:
                suffix = ".png"
            ok, encoded = cv2.imencode(suffix, image)
            if not ok:
                return False
            p.parent.mkdir(parents=True, exist_ok=True)
            encoded.tofile(str(p))
            return True
        except Exception:
            return False

    def open_image(self):
        path = open_file(
            self,
            title="Открыть изображение",
            initial=self._dialog_dir(),
            name_filter="Изображения (*.png *.jpg *.jpeg *.bmp)",
        )
        if not path:
            return
        self._remember_dialog_path(path)
        image = self._read_image_file(path)
        if image is None:
            return self.show_error("Не удалось открыть изображение")
        self.image_path = path
        self.source_image_path = path
        self.original_image_bgr = image.copy()
        self.set_image(image, reset_geometry=True)
        self.status.setText(Path(path).name)
        self.image_label.setText(Path(path).name)
        self.image_label.setToolTip(str(path))

    def set_image(self, image: np.ndarray, reset_geometry: bool = False):
        self.image_bgr = image.copy()
        self.canvas.set_image(self.image_bgr)
        self.image_label.setText(Path(self.image_path).name if self.image_path else "Рабочее изображение")
        if reset_geometry:
            self.h1_point = self.h2_point = None
            self.track_guides.clear()
            self.scales.clear()
            self.curves.clear()
            self.scale_list.clear()
            self.curve_list.clear()
            self._last_df = None
            self._last_mask = None
            self.new_scale_editor()
            self.new_curve_editor()
            self.refresh_scale_combo()
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.update_depth_info()

    def reset_to_original(self):
        if self.original_image_bgr is None and self.source_image_path:
            self.original_image_bgr = self._read_image_file(self.source_image_path)
        if self.original_image_bgr is None:
            return self.show_error("Исходное изображение не загружено")
        self.set_image(self.original_image_bgr, reset_geometry=True)
        self.image_path = self.source_image_path
        self.status.setText("Возвращено исходное изображение; калибровка сброшена")

    # ---------------- Geometry / depth ----------------
    def rotate(self, clockwise: bool):
        if self.image_bgr is None:
            return self.show_error("Сначала откройте изображение")
        self.set_image(rotate_image_90(self.image_bgr, clockwise), reset_geometry=True)
        self.status.setText("Изображение повернуто; калибровка сброшена")

    def do_auto_deskew(self):
        if self.image_bgr is None:
            return self.show_error("Сначала откройте изображение")
        fixed, angle = auto_deskew(self.image_bgr)
        self.set_image(fixed, reset_geometry=True)
        self.status.setText(f"Автовыравнивание: {angle:.2f}°; калибровка сброшена")

    def start_perspective(self):
        if self.image_bgr is None:
            return self.show_error("Сначала откройте изображение")
        self.canvas.set_mode("perspective")
        self.status.setText("Перспектива: кликните по четырём углам рабочей области")

    def on_perspective_selected(self, points):
        if self.image_bgr is None:
            return
        try:
            fixed = perspective_warp(self.image_bgr, points)
            self.set_image(fixed, reset_geometry=True)
            self.status.setText("Перспектива исправлена; калибровка сброшена")
        except Exception as e:
            self.show_error(str(e))

    def find_tracks(self):
        if self.image_bgr is None:
            return self.show_error("Сначала откройте изображение")
        try:
            y0 = y1 = None
            if self.h1_point and self.h2_point:
                y0 = int(min(self.h1_point.y(), self.h2_point.y()))
                y1 = int(max(self.h1_point.y(), self.h2_point.y()))
            self.track_guides = detect_vertical_track_lines(self.image_bgr, y0, y1)
            self.canvas.show_vertical_guides(self.track_guides)
            self.track_info.setText(f"Найдено вероятных вертикальных линий: {len(self.track_guides)}")
        except Exception as e:
            self.show_error(str(e))

    def clear_tracks(self):
        self.track_guides = []
        self.canvas.clear_guides()
        self.track_info.setText("Границы скрыты")

    def on_point_picked(self, kind: str, p: QPointF):
        if kind == "h1":
            self.h1_point = p
            self.status.setText("Точка H1 установлена")
        elif kind == "h2":
            self.h2_point = p
            self.status.setText("Точка H2 установлена")
        elif kind == "scale_x1":
            self.scale_x1_point = p
            self.status.setText("Первая отметка шкалы установлена")
            self._sync_scale_roi_from_points()
        elif kind == "scale_x2":
            self.scale_x2_point = p
            self.status.setText("Вторая отметка шкалы установлена")
            self._sync_scale_roi_from_points()
        self.update_depth_info()
        self.update_scale_geometry_info()
        self.redraw_overlays()

    def update_depth_info(self):
        if not hasattr(self, "depth_info"):
            return
        if not self.h1_point or not self.h2_point:
            self.depth_info.setText("Две точки ещё не заданы")
            return
        try:
            cal = self.get_depth_calibration()
            per_px = (cal.h2 - cal.h1) / (cal.y2 - cal.y1)
            self.depth_info.setText(
                f"Y1={cal.y1:.1f}px → {cal.h1:g} м • Y2={cal.y2:.1f}px → {cal.h2:g} м • {abs(per_px):.6g} м/px"
            )
        except Exception as e:
            self.depth_info.setText(str(e))

    def get_depth_calibration(self) -> DepthCalibration:
        if self.h1_point is None or self.h2_point is None:
            raise ValueError("Нужно указать две точки глубины H1 и H2")
        cal = DepthCalibration(
            self.h1_point.y(), self.h1_value.value(),
            self.h2_point.y(), self.h2_value.value(),
        )
        if not cal.is_valid():
            raise ValueError("Некорректная калибровка глубины")
        return cal

    def on_mouse_moved(self, p: QPointF):
        extra = ""
        try:
            cal = self.get_depth_calibration()
            h = cal.h1 + (p.y() - cal.y1) * (cal.h2 - cal.h1) / (cal.y2 - cal.y1)
            extra = f" • H≈{h:.3f} м"
        except Exception:
            pass
        self.status.setText(f"x={p.x():.0f}, y={p.y():.0f}{extra}")

    # ---------------- ROI dispatch ----------------
    def start_scale_roi(self):
        if self.image_bgr is None:
            return self.show_error("Сначала откройте изображение")
        self.roi_purpose = "scale"
        self.canvas.set_mode("roi")
        self.status.setText("Выделите прямоугольную область шкалы от минимального до максимального значения")

    def start_curve_roi(self):
        if self.image_bgr is None:
            return self.show_error("Сначала откройте изображение")
        self.roi_purpose = "curve"
        self.canvas.set_mode("roi")
        self.status.setText("Выделите область, внутри которой проходит текущая кривая")

    def on_roi_selected(self, rect: QRectF):
        rect = rect.normalized()
        if self.roi_purpose == "scale":
            self.scale_roi = rect
            cy = rect.center().y()
            self.scale_x1_point = QPointF(rect.left(), cy)
            self.scale_x2_point = QPointF(rect.right(), cy)
            self.update_scale_geometry_info()
            self.status.setText(f"Область шкалы: {rect.width():.0f}×{rect.height():.0f} px")
        else:
            self.current_curve_roi = rect
            self.curve_roi_info.setText(
                f"ROI: x={rect.x():.0f}, y={rect.y():.0f}, {rect.width():.0f}×{rect.height():.0f}px"
            )
            self.status.setText(f"ROI кривой: {rect.width():.0f}×{rect.height():.0f} px")
        self.redraw_overlays()

    # ---------------- Scales ----------------
    def _new_scale_id(self) -> str:
        used = {s.id for s in self.scales}
        n = 1
        while f"scale_{n}" in used:
            n += 1
        return f"scale_{n}"

    def new_scale_editor(self):
        self.scale_edit_index = None
        self.scale_x1_point = None
        self.scale_x2_point = None
        self.scale_roi = None
        if hasattr(self, "scale_name"):
            self.scale_name.setText(f"Шкала {len(self.scales) + 1}")
            self.scale_unit.setText("мкс")
            self.scale_min.setValue(250)
            self.scale_max.setValue(650)
            self.scale_type.setCurrentIndex(0)
            self.update_scale_geometry_info()
        self.redraw_overlays()

    def _sync_scale_roi_from_points(self):
        if not self.scale_x1_point or not self.scale_x2_point or self.image_bgr is None:
            return
        x1, x2 = self.scale_x1_point.x(), self.scale_x2_point.x()
        if self.h1_point and self.h2_point:
            y0 = min(self.h1_point.y(), self.h2_point.y())
            y1 = max(self.h1_point.y(), self.h2_point.y())
        else:
            y0, y1 = 0.0, float(self.image_bgr.shape[0] - 1)
        self.scale_roi = QRectF(min(x1, x2), y0, abs(x2 - x1), max(1.0, y1 - y0))

    def _scale_from_editor(self, scale_id: str | None = None) -> AxisScale:
        if self.scale_x1_point is None or self.scale_x2_point is None:
            raise ValueError("Сначала выделите область шкалы или укажите две отметки")
        vmin, vmax = self.scale_min.value(), self.scale_max.value()
        scale_type = self.scale_type.currentData()
        if scale_type == "log" and (vmin <= 0 or vmax <= 0):
            raise ValueError("Для логарифмической шкалы минимум и максимум должны быть > 0")
        roi = self.scale_roi
        if roi is None:
            self._sync_scale_roi_from_points()
            roi = self.scale_roi
        if roi is None:
            raise ValueError("Не удалось определить область шкалы")
        scale = AxisScale(
            id=scale_id or self._new_scale_id(),
            name=self.scale_name.text().strip() or "Шкала",
            unit=self.scale_unit.text().strip(),
            value_min=vmin,
            value_max=vmax,
            x1=self.scale_x1_point.x(),
            x2=self.scale_x2_point.x(),
            scale_type=scale_type,
            roi=(roi.x(), roi.y(), roi.width(), roi.height()),
        )
        if not scale.is_valid():
            raise ValueError("Некорректная калибровка шкалы")
        if self.image_bgr is not None:
            div, _ = estimate_scale_division(self.image_bgr, scale)
            scale.division = div
        return scale

    def update_scale_geometry_info(self):
        if not hasattr(self, "scale_geometry_info"):
            return
        if not self.scale_x1_point or not self.scale_x2_point:
            self.scale_geometry_info.setText("Область шкалы не задана")
            self.scale_division_info.setText("Цена деления: —")
            return
        try:
            dx = self.scale_x2_point.x() - self.scale_x1_point.x()
            span = self.scale_max.value() - self.scale_min.value()
            px_scale = abs(span / dx) if abs(dx) > 1e-9 else float("nan")
            self.scale_geometry_info.setText(
                f"X1={self.scale_x1_point.x():.1f}px • X2={self.scale_x2_point.x():.1f}px • масштаб ≈ {px_scale:.6g} {self.scale_unit.text().strip() or 'ед.'}/px"
            )
            temp = self._scale_from_editor("preview")
            if temp.division is not None:
                self.scale_division_info.setText(f"Цена деления (автооценка): ≈ {temp.division:.6g} {temp.unit}")
            elif temp.scale_type == "log":
                self.scale_division_info.setText("Цена деления: логарифмическая шкала")
            else:
                self.scale_division_info.setText("Цена деления: сетка не распознана; преобразование всё равно рассчитано по границам")
        except Exception as e:
            self.scale_division_info.setText(f"Цена деления: — ({e})")

    def save_scale_from_editor(self):
        try:
            existing_id = None
            if self.scale_edit_index is not None and 0 <= self.scale_edit_index < len(self.scales):
                existing_id = self.scales[self.scale_edit_index].id
            scale = self._scale_from_editor(existing_id)
            if self.scale_edit_index is None:
                self.scales.append(scale)
                self.scale_edit_index = len(self.scales) - 1
            else:
                self.scales[self.scale_edit_index] = scale
            self.refresh_scale_list()
            self.refresh_scale_combo(scale.id)
            self.recalculate_all_curves()
            self.redraw_overlays()
            div = f", цена деления ≈ {scale.division:.6g} {scale.unit}" if scale.division else ""
            self.status.setText(f"Шкала «{scale.name}» сохранена{div}")
        except Exception as e:
            self.show_error(str(e))

    def refresh_scale_list(self):
        self.scale_list.clear()
        for scale in self.scales:
            kind = "LIN" if scale.scale_type == "linear" else "LOG"
            div = f" • Δ≈{scale.division:.4g}" if scale.division else ""
            item = QListWidgetItem(
                f"{scale.name} • {scale.value_min:g}…{scale.value_max:g} {scale.unit} • {kind}{div}"
            )
            item.setData(Qt.UserRole, scale.id)
            self.scale_list.addItem(item)
        if self.scale_edit_index is not None and self.scales:
            self.scale_list.setCurrentRow(min(self.scale_edit_index, len(self.scales) - 1))

    def refresh_scale_combo(self, select_id: str | None = None):
        if not hasattr(self, "curve_scale_combo"):
            return
        current = select_id or self.curve_scale_combo.currentData()
        self.curve_scale_combo.blockSignals(True)
        self.curve_scale_combo.clear()
        self.curve_scale_combo.addItem("— выберите шкалу —", "")
        for s in self.scales:
            self.curve_scale_combo.addItem(f"{s.name} ({s.unit})" if s.unit else s.name, s.id)
        idx = self.curve_scale_combo.findData(current)
        self.curve_scale_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.curve_scale_combo.blockSignals(False)

    def load_scale_to_editor(self, item: QListWidgetItem):
        row = self.scale_list.row(item)
        if not (0 <= row < len(self.scales)):
            return
        s = self.scales[row]
        self.scale_edit_index = row
        self.scale_name.setText(s.name)
        self.scale_unit.setText(s.unit)
        self.scale_min.setValue(s.value_min)
        self.scale_max.setValue(s.value_max)
        self.scale_type.setCurrentIndex(max(0, self.scale_type.findData(s.scale_type)))
        self.scale_x1_point = QPointF(s.x1, s.roi[1] + s.roi[3] / 2)
        self.scale_x2_point = QPointF(s.x2, s.roi[1] + s.roi[3] / 2)
        self.scale_roi = QRectF(*s.roi)
        self.update_scale_geometry_info()
        self.redraw_overlays()

    def remove_selected_scale(self):
        row = self.scale_list.currentRow()
        if not (0 <= row < len(self.scales)):
            return
        sid = self.scales[row].id
        users = [c.config.name for c in self.curves if c.config.scale_id == sid]
        if users:
            return self.show_error("Эта шкала используется кривыми: " + ", ".join(users) + ". Сначала переназначьте или удалите их.")
        del self.scales[row]
        self.new_scale_editor()
        self.refresh_scale_list()
        self.refresh_scale_combo()

    def get_scale(self, scale_id: str) -> AxisScale:
        scale = next((s for s in self.scales if s.id == scale_id), None)
        if scale is None:
            raise ValueError("Назначенная шкала не найдена")
        return scale

    # ---------------- Curves ----------------
    def new_curve_editor(self):
        self.curve_edit_index = None
        self.current_curve_roi = None
        self.curve_samples = []
        if hasattr(self, "curve_name"):
            self.curve_name.setText(f"T{len(self.curves) + 1}")
            self.curve_unit.setText("")
            self.refresh_scale_combo()
            self.curve_roi_info.setText("ROI кривой не задан")
            self.refresh_sample_list()
            self.tolerance.setValue(RECOMMENDED_CURVE_DEFAULTS["color_tolerance"])
            self.precise_color.setChecked(True)
            self.competitor_margin.setValue(RECOMMENDED_CURVE_DEFAULTS["competitor_margin"])
            self.hue_tolerance.setValue(RECOMMENDED_CURVE_DEFAULTS["hue_tolerance"])
            self.color_diagnostics.setText("Добавьте образцы цвета и проверьте маску до оцифровки")
            self.max_jump.setValue(RECOMMENDED_CURVE_DEFAULTS["max_jump_px"])
            self.max_gap.setValue(RECOMMENDED_CURVE_DEFAULTS["max_gap_rows"])
            self.smooth_window.setValue(RECOMMENDED_CURVE_DEFAULTS["smooth_window"])
            self.remove_grid.setChecked(True)
            self.grid_strength.setValue(RECOMMENDED_CURVE_DEFAULTS["grid_strength"])
            self._lock_recognition_parameters()
        self.redraw_overlays()

    def on_curve_scale_changed(self, _index: int):
        sid = self.curve_scale_combo.currentData()
        if not sid:
            return
        try:
            scale = self.get_scale(sid)
            if not self.curve_unit.text().strip():
                self.curve_unit.setText(scale.unit)
        except Exception:
            pass

    def start_color_pick(self):
        if self.image_bgr is None:
            return self.show_error("Сначала откройте изображение")
        self.color_pick_purpose = "curve_sample"
        self.canvas.set_mode("color")
        self.status.setText("Пипетка: кликните по чистому участку текущей кривой")

    def on_color_picked(self, p: QPointF, bgr: tuple):
        if self.color_pick_purpose != "curve_sample":
            return
        color = tuple(int(v) for v in bgr)
        self.curve_samples.append((p, color))
        self.refresh_sample_list()
        other_colors = [
            other for cfg in self.competing_curve_configs()
            for other in cfg.effective_colors()
        ]
        if other_colors:
            delta = palette_separation([c for _p, c in self.curve_samples], other_colors)
            if delta < 15:
                self.color_diagnostics.setText(
                    f"Внимание: выбранные краски очень похожи (LAB ≈ {delta:.1f}). "
                    "Для разделения выделите более узкую область ROI, "
                    "выберите чистые образцы в нескольких точках каждой "
                    "кривой и проверьте жёлтые неоднозначные участки."
                )
        b, g, r = color
        self.canvas.add_marker(p, QColor(r, g, b), 6)
        self.status.setText(f"Добавлен образец цвета #{len(self.curve_samples)}")

    def refresh_sample_list(self):
        if not hasattr(self, "sample_list"):
            return
        self.sample_list.clear()
        for i, (p, bgr) in enumerate(self.curve_samples, start=1):
            b, g, r = bgr
            item = QListWidgetItem(f"#{i}  RGB({r}, {g}, {b}) • x={p.x():.0f}, y={p.y():.0f}")
            item.setBackground(QColor(r, g, b, 80))
            self.sample_list.addItem(item)

    def remove_selected_sample(self):
        row = self.sample_list.currentRow()
        if 0 <= row < len(self.curve_samples):
            del self.curve_samples[row]
            self.refresh_sample_list()
            self.redraw_overlays()

    def make_curve_config(self) -> CurveConfig:
        if self.current_curve_roi is None:
            raise ValueError("Сначала выделите область кривой")
        if not self.curve_samples:
            raise ValueError("Добавьте хотя бы один образец цвета пипеткой")
        sid = self.curve_scale_combo.currentData()
        if not sid:
            raise ValueError("Выберите шкалу для этой кривой")
        scale = self.get_scale(sid)
        r = self.current_curve_roi.normalized()
        colors = [tuple(map(int, color)) for _p, color in self.curve_samples]
        points = [(float(p.x()), float(p.y())) for p, _color in self.curve_samples]
        unit = self.curve_unit.text().strip() or scale.unit
        return CurveConfig(
            name=self.curve_name.text().strip() or f"Curve {len(self.curves) + 1}",
            unit=unit,
            scale_id=scale.id,
            roi=(r.x(), r.y(), r.width(), r.height()),
            color_bgr=colors[0],
            color_samples_bgr=colors,
            sample_points_xy=points,
            color_tolerance=self.tolerance.value(),
            precise_color=self.precise_color.isChecked(),
            competitor_margin=self.competitor_margin.value(),
            hue_tolerance=self.hue_tolerance.value(),
            seed_xy=points[0],
            max_jump_px=self.max_jump.value(),
            max_gap_rows=self.max_gap.value(),
            smooth_window=self.smooth_window.value(),
            remove_grid=self.remove_grid.isChecked(),
            grid_strength=self.grid_strength.value(),
            x_min=scale.value_min,
            x_max=scale.value_max,
            scale_type=scale.scale_type,
        )

    def competing_curve_configs(self) -> list[CurveConfig]:
        """Only other already detected curves can act as colour references."""
        return [
            c.config for index, c in enumerate(self.curves)
            if index != self.curve_edit_index
        ]

    def _update_ambiguity_label(self, ambiguous: np.ndarray, mask: np.ndarray):
        disputed = int(np.count_nonzero(ambiguous))
        accepted = int(np.count_nonzero(mask))
        total = disputed + accepted
        pct = (100.0 * disputed / total) if total else 0.0
        self.color_diagnostics.setText(
            f"Разделение цветов: {pct:.1f}% спорных точек • "
            f"принято {accepted:,} пикселей • исключено {disputed:,}. "
            "Жёлтая область — цветовая неоднозначность; при необходимости "
            "сузьте область, добавьте образцы и проверьте обе кривые."
        )

    def preview_mask(self):
        if self.image_bgr is None:
            return self.show_error("Сначала откройте изображение")
        try:
            cfg = self.make_curve_config()
            mask, _dist, ambiguous = analyze_color_selection(
                self.image_bgr, cfg, self.competing_curve_configs()
            )
            self._last_mask = mask
            self.redraw_overlays()
            self.canvas.add_mask_overlay(mask, cfg.roi, QColor(0, 200, 165, 120))
            self.canvas.add_mask_overlay(ambiguous, cfg.roi, QColor(255, 193, 7, 155))
            self._update_ambiguity_label(ambiguous, mask)
            self.status.setText(f"Зелёная маска — кривая; жёлтая — спорные пиксели • образцов: {len(cfg.effective_colors())}")
        except Exception as e:
            self.show_error(str(e))

    def detect_curve(self):
        if self.image_bgr is None:
            return self.show_error("Сначала откройте изображение")
        try:
            depth = self.get_depth_calibration()
            cfg = self.make_curve_config()
            scale = self.get_scale(cfg.scale_id)
            competitors = self.competing_curve_configs()
            points_xy, mask = trace_curve_from_seed(self.image_bgr, cfg, competitors)
            if len(points_xy) < 20:
                raise ValueError(
                    f"Найдено слишком мало точек: {len(points_xy)}. Добавьте образцы цвета, увеличьте допуск LAB или выберите более чистый стартовый участок."
                )
            points_hv = curve_points_to_hv(points_xy, cfg, depth, scale)
            quality = curve_quality(points_xy, cfg)
            data = CurveData(cfg, points_xy, points_hv, quality)
            self._last_mask = mask
            if cfg.precise_color and competitors:
                _mask, _distance, ambiguous = analyze_color_selection(self.image_bgr, cfg, competitors)
                self._update_ambiguity_label(ambiguous, _mask)
            if self.curve_edit_index is None:
                self.curves.append(data)
                selected = len(self.curves) - 1
            else:
                self.curves[self.curve_edit_index] = data
                selected = self.curve_edit_index
            self.curve_edit_index = selected
            self.refresh_curve_list(selected)
            self.redraw_overlays()
            self.status.setText(
                f"{cfg.name}: {len(points_xy)} точек • покрытие {quality['coverage_pct']:.1f}% • Q {quality['score']:.0f}/100"
            )
        except Exception as e:
            self.show_error(str(e))

    def redetect_all_curves(self):
        """After both palettes exist, trace every saved curve competitively."""
        if self.image_bgr is None or not self.curves:
            return self.show_error("Сначала откройте фото и создайте кривые")
        try:
            depth = self.get_depth_calibration()
        except Exception as exc:
            return self.show_error(str(exc))
        # Trace against frozen palette/config snapshots. Do not overwrite
        # user-edited curves when re-detection of another curve fails.
        configs = [c.config for c in self.curves]
        reports = []
        updated = 0
        for i, cfg in enumerate(configs):
            try:
                others = [c for j, c in enumerate(configs) if i != j]
                xy, mask = trace_curve_from_seed(self.image_bgr, cfg, others)
                if len(xy) < 20:
                    raise ValueError("меньше 20 точек: проверьте маску")
                hv = curve_points_to_hv(xy, cfg, depth, self.get_scale(cfg.scale_id))
                self.curves[i] = CurveData(cfg, xy, hv, curve_quality(xy, cfg))
                updated += 1
            except Exception as exc:
                reports.append(f"{cfg.name}: {exc}")
        self.refresh_curve_list()
        self.redraw_overlays()
        self.status.setText(f"Повторно распознано {updated} из {len(configs)} кривых")
        if reports:
            show_warning(self, "Проверка кривых", "Не удалось обновить:\n" + "\n".join(reports))

    def refresh_curve_list(self, selected: int | None = None):
        current = self.curve_list.currentRow() if selected is None else selected
        self.curve_list.clear()
        scale_names = {s.id: s.name for s in self.scales}
        for c in self.curves:
            score = c.quality.get("score", 0.0) if c.quality else 0.0
            coverage = c.quality.get("coverage_pct", 0.0) if c.quality else 0.0
            scale_name = scale_names.get(c.config.scale_id, "?")
            item = QListWidgetItem(
                f"{c.config.name} • {scale_name} • {len(c.config.effective_colors())} цв. • покр. {coverage:.0f}% • Q {score:.0f}"
            )
            self.curve_list.addItem(item)
        if self.curves:
            self.curve_list.setCurrentRow(min(max(current, 0), len(self.curves) - 1))

    def load_curve_to_editor(self, item: QListWidgetItem):
        row = self.curve_list.row(item)
        if not (0 <= row < len(self.curves)):
            return
        c = self.curves[row]
        cfg = c.config
        self.curve_edit_index = row
        self.curve_name.setText(cfg.name)
        self.curve_unit.setText(cfg.unit)
        self.refresh_scale_combo(cfg.scale_id)
        self.current_curve_roi = QRectF(*cfg.roi)
        self.curve_roi_info.setText(
            f"ROI: x={cfg.roi[0]:.0f}, y={cfg.roi[1]:.0f}, {cfg.roi[2]:.0f}×{cfg.roi[3]:.0f}px"
        )
        colors = cfg.effective_colors()
        pts = cfg.sample_points_xy or ([cfg.seed_xy] if cfg.seed_xy else [])
        self.curve_samples = []
        for i, color in enumerate(colors):
            if i < len(pts) and pts[i] is not None:
                p = QPointF(*pts[i])
            elif cfg.seed_xy:
                p = QPointF(*cfg.seed_xy)
            else:
                p = QPointF(cfg.roi[0] + cfg.roi[2] / 2, cfg.roi[1] + cfg.roi[3] / 2)
            self.curve_samples.append((p, tuple(color)))
        self.tolerance.setValue(cfg.color_tolerance)
        self.precise_color.setChecked(cfg.precise_color)
        self.competitor_margin.setValue(cfg.competitor_margin)
        self.hue_tolerance.setValue(cfg.hue_tolerance)
        self.max_jump.setValue(cfg.max_jump_px)
        self.max_gap.setValue(cfg.max_gap_rows)
        self.smooth_window.setValue(cfg.smooth_window)
        self.remove_grid.setChecked(cfg.remove_grid)
        self.grid_strength.setValue(cfg.grid_strength)
        self._lock_recognition_parameters()
        self.refresh_sample_list()
        self.redraw_overlays()

    def remove_selected_curve(self):
        row = self.curve_list.currentRow()
        if not (0 <= row < len(self.curves)):
            return
        del self.curves[row]
        self.new_curve_editor()
        self.refresh_curve_list(0)
        self.redraw_overlays()

    def recalculate_all_curves(self):
        try:
            depth = self.get_depth_calibration()
        except Exception:
            return
        for c in self.curves:
            try:
                scale = self.get_scale(c.config.scale_id)
                c.points_hv = curve_points_to_hv(c.points_xy, c.config, depth, scale)
            except Exception:
                c.points_hv = []

    # ---------------- Editing / overlays ----------------
    def start_edit_mode(self, mode: str):
        row = self.curve_list.currentRow()
        if not (0 <= row < len(self.curves)):
            return self.show_error("Сначала выберите распознанную кривую в списке")
        self.canvas.set_mode(mode)
        self.status.setText("Ручная правка кривой" if mode == "edit_move" else "Удаление ошибочных точек")

    def on_edit_point(self, mode: str, p: QPointF):
        row = self.curve_list.currentRow()
        if not (0 <= row < len(self.curves)):
            return
        curve = self.curves[row]
        rx, ry, rw, rh = curve.config.roi
        if not (rx <= p.x() <= rx + rw and ry <= p.y() <= ry + rh):
            self.status.setText("Точка вне ROI выбранной кривой")
            return
        if mode == "edit_move":
            curve.points_xy = edit_curve_point(curve.points_xy, p.x(), p.y())
        else:
            curve.points_xy = delete_curve_near(curve.points_xy, p.x(), p.y())
        try:
            depth = self.get_depth_calibration()
            scale = self.get_scale(curve.config.scale_id)
            curve.points_hv = curve_points_to_hv(curve.points_xy, curve.config, depth, scale)
            curve.quality = curve_quality(curve.points_xy, curve.config)
        except Exception:
            curve.points_hv = []
        self.refresh_curve_list(row)
        self.redraw_overlays()

    def redraw_overlays(self):
        if self.image_bgr is None:
            return
        self.canvas.clear_overlays(keep_roi=False)
        if self.h1_point:
            self.canvas.add_marker(self.h1_point, QColor(239, 68, 68), 6)
        if self.h2_point:
            self.canvas.add_marker(self.h2_point, QColor(14, 165, 233), 6)
        if self.scale_roi is not None:
            self.canvas.add_rect_overlay(self.scale_roi, QColor(194, 154, 67), 2.0, True)
        if self.scale_x1_point:
            self.canvas.add_marker(self.scale_x1_point, QColor(194, 154, 67), 5)
        if self.scale_x2_point:
            self.canvas.add_marker(self.scale_x2_point, QColor(194, 154, 67), 5)
        if self.current_curve_roi is not None:
            self.canvas.add_rect_overlay(self.current_curve_roi, QColor(59, 130, 246), 2.0, True)
        for p, bgr in self.curve_samples:
            b, g, r = bgr
            self.canvas.add_marker(p, QColor(r, g, b), 5)

        palette = [
            QColor(168, 85, 247), QColor(14, 165, 233), QColor(249, 115, 22),
            QColor(34, 197, 94), QColor(236, 72, 153), QColor(234, 179, 8),
            QColor(99, 102, 241), QColor(20, 184, 166),
        ]
        selected = self.curve_list.currentRow() if hasattr(self, "curve_list") else -1
        for i, curve in enumerate(self.curves):
            color = QColor(250, 204, 21) if i == selected else palette[i % len(palette)]
            self.canvas.add_curve_overlay(curve.points_xy, color)

    # ---------------- Table / Excel ----------------
    def build_table(self):
        try:
            depth = self.get_depth_calibration()
            self.recalculate_all_curves()
            step = self.depth_step.value()
            df = build_output_dataframe(self.curves, depth, step)
            self._last_df = df
            preview = df.head(600)
            self.table.setColumnCount(len(preview.columns))
            self.table.setRowCount(len(preview))
            self.table.setHorizontalHeaderLabels(list(preview.columns))
            for r in range(len(preview)):
                for c, col in enumerate(preview.columns):
                    val = preview.iloc[r, c]
                    text = "" if pd.isna(val) else f"{float(val):.8g}"
                    self.table.setItem(r, c, QTableWidgetItem(text))
            self.table.resizeColumnsToContents()
            self.status.setText(f"Таблица: {len(df)} строк • показано {len(preview)}")
            return df
        except Exception as e:
            self.show_error(str(e))
            return None

    def export_excel(self):
        df = self.build_table()
        if df is None:
            return
        path = save_file(
            self,
            title="Экспорт Excel",
            initial=Path(self._dialog_dir()) / "digitized.xlsx",
            name_filter="Microsoft Excel (*.xlsx)",
        )
        if not path:
            return
        self._remember_dialog_path(path)
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            depth = self.get_depth_calibration()
            export_xlsx(
                path,
                df,
                curves=self.curves,
                scales=self.scales,
                depth=depth,
                source_image=self.source_image_path or self.image_path,
                depth_step=self.depth_step.value(),
            )
            self.status.setText(f"Excel сохранён: {Path(path).name}")
        except Exception as e:
            self.show_error(str(e))

    # ---------------- Project ----------------
    def make_project(self) -> ProjectData:
        depth = None
        if self.h1_point is not None and self.h2_point is not None:
            depth = self.get_depth_calibration()
        return ProjectData(
            image_path=self.image_path,
            source_image_path=self.source_image_path,
            depth=depth,
            scales=self.scales,
            curves=self.curves,
            depth_step=self.depth_step.value(),
            version=APP_VERSION,
        )

    def save_project_dialog(self):
        path = save_file(
            self,
            title="Сохранить проект",
            initial=Path(self._dialog_dir()) / "project.vdigit.json",
            name_filter="Проект Vinogradov's Digitizer (*.json)",
        )
        if not path:
            return
        self._remember_dialog_path(path)
        try:
            project_path = Path(path)
            if project_path.suffix.lower() != ".json":
                project_path = project_path.with_suffix(".json")
            project = self.make_project()
            if self.image_bgr is not None:
                working_path = project_path.with_name(project_path.stem + "_working.png")
                if not self._write_image_file(working_path, self.image_bgr):
                    raise ValueError("Не удалось сохранить рабочее изображение проекта")
                project.image_path = str(working_path.resolve())
            save_project(project_path, project)
            self.status.setText(f"Проект сохранён: {project_path.name}")
        except Exception as e:
            self.show_error(str(e))

    def open_project(self):
        path = open_file(
            self,
            title="Открыть проект",
            initial=self._dialog_dir(),
            name_filter="Проект Vinogradov's Digitizer (*.json)",
        )
        if not path:
            return
        self._remember_dialog_path(path)
        try:
            project = load_project(path)
            img = self._read_image_file(project.image_path)
            if img is None:
                raise ValueError(f"Не найден файл рабочего изображения проекта: {project.image_path}")
            self.image_path = project.image_path
            self.source_image_path = project.source_image_path or project.image_path
            source = self._read_image_file(self.source_image_path)
            self.original_image_bgr = source if source is not None else img.copy()
            self.image_bgr = img
            self.canvas.set_image(img)
            self.image_label.setText(Path(project.image_path).name)
            self.scales = project.scales
            self.curves = project.curves
            self.depth_step.setValue(project.depth_step)
            if project.depth:
                self.h1_point = QPointF(15, project.depth.y1)
                self.h2_point = QPointF(15, project.depth.y2)
                self.h1_value.setValue(project.depth.h1)
                self.h2_value.setValue(project.depth.h2)
            else:
                self.h1_point = self.h2_point = None
            self.new_scale_editor()
            self.new_curve_editor()
            self.refresh_scale_list()
            self.refresh_scale_combo()
            for curve in self.curves:
                if not curve.quality:
                    curve.quality = curve_quality(curve.points_xy, curve.config)
            self.recalculate_all_curves()
            self.refresh_curve_list(0)
            self.update_depth_info()
            self.redraw_overlays()
            self.status.setText(f"Проект открыт: {Path(path).name} (v{project.version})")
        except Exception as e:
            self.show_error(str(e))
