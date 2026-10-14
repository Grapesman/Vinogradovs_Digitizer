"""
Vinogradov's Digitizer — modern light desktop theme.

Интерфейс приложения построен на PySide6/Qt и используется
как непосредственно в Windows EXE, так и внутри Docker/noVNC.

Внешние шрифты, web-ресурсы и сетевые зависимости не используются.
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


MODERN_QSS = r"""

/* ============================================================
   БАЗОВЫЙ ИНТЕРФЕЙС
   ============================================================ */

QMainWindow,
QDialog {
    background: #eef3f8;
}


QWidget {
    color: #1d2f43;

    font-family:
        "DejaVu Sans",
        "Segoe UI",
        Arial;

    font-size: 13px;
}


/* ============================================================
   ГЛАВНАЯ ШАПКА
   ============================================================ */

QFrame#appHeader {
    background: #0d2944;

    border: 1px solid #173b5c;
    border-radius: 15px;
}


QLabel#appTitle {
    color: #ffffff;

    font-size: 21px;
    font-weight: 800;
}


QLabel#appSubtitle {
    color: #c9d6e2;

    font-size: 12px;
}


/* ============================================================
   ОСНОВНАЯ РАБОЧАЯ ОБЛАСТЬ
   ============================================================ */

QFrame#workspace {
    background: #ffffff;

    border: 1px solid #dce6ef;
    border-radius: 16px;
}


QLabel#workspaceTitle {
    color: #17344e;

    font-size: 12px;
    font-weight: 800;
}


QLabel#imageLabel {
    color: #6c7f92;

    font-size: 12px;
}


/* ============================================================
   ВКЛАДКИ
   Подготовка / Шкалы / Кривые / Результат
   ============================================================ */

QTabWidget#workspaceTabs {
    background: transparent;

    border: none;
}


QTabWidget#workspaceTabs::pane {
    background: transparent;

    border: none;

    /*
    ВАЖНО:
    не используем отрицательный top,
    чтобы вкладки не наезжали на содержимое.
    */
}


QTabWidget#workspaceTabs QTabBar {
    background: transparent;

    qproperty-drawBase: 0;
}


QTabWidget#workspaceTabs QTabBar::tab {
    min-height: 34px;

    padding-left: 14px;
    padding-right: 14px;

    margin-right: 6px;
    margin-bottom: 9px;

    color: #65778a;

    background: #e8eef4;

    border: 1px solid #dce5ed;
    border-radius: 9px;

    font-size: 12px;
    font-weight: 700;
}


QTabWidget#workspaceTabs QTabBar::tab:selected {
    color: #ffffff;

    background: #174d73;

    border-color: #174d73;
}


QTabWidget#workspaceTabs QTabBar::tab:hover:!selected {
    color: #204761;

    background: #dce8f1;

    border-color: #cadce8;
}


/* ============================================================
   КАРТОЧКИ
   ============================================================ */

QFrame#card {
    background: #ffffff;

    border: 1px solid #dce6ef;
    border-radius: 14px;
}


QLabel#cardTitle {
    color: #193a55;

    font-size: 15px;
    font-weight: 800;
}


QLabel#cardHint {
    color: #6e8092;

    font-size: 12px;
}


QLabel#diagnostic {
    color: #315c51;

    background: #edf9f5;

    border: 1px solid #c4e8dc;
    border-radius: 9px;

    padding: 10px;

    font-size: 12px;
}


/* ============================================================
   ПАНЕЛЬ ТОЧНОЙ НАСТРОЙКИ
   ============================================================ */

QFrame#parameterPanel {
    background: #f7f9fc;

    border: 1px solid #dce5ee;
    border-radius: 12px;
}


QLabel#parameterLabel {
    color: #43596e;

    font-size: 12px;
    font-weight: 700;
}


/* ============================================================
   КНОПКИ
   ============================================================ */

QPushButton {
    min-height: 36px;

    padding-left: 12px;
    padding-right: 12px;

    color: #29465e;

    background: #fbfcfe;

    border: 1px solid #cad8e5;
    border-radius: 9px;

    font-size: 12px;
    font-weight: 700;
}


QPushButton:hover {
    color: #163f5b;

    background: #edf5fa;

    border-color: #91b4cc;
}


QPushButton:pressed {
    background: #dceaf4;

    border-color: #73a0bf;
}


QPushButton:disabled {
    color: #9aabba;

    background: #f1f4f7;

    border-color: #e2e7ec;
}


/* Главная кнопка */

QPushButton[primary="true"] {
    color: #ffffff;

    background: #174f75;

    border: 1px solid #174f75;
}


QPushButton[primary="true"]:hover {
    background: #21698f;

    border-color: #21698f;
}


QPushButton[primary="true"]:pressed {
    background: #123f60;

    border-color: #123f60;
}


/* Мягкая вторичная кнопка */

QPushButton[soft="true"] {
    color: #31536a;

    background: #eaf1f6;

    border-color: #d5e2ec;
}


QPushButton[soft="true"]:hover {
    background: #ddeaf3;

    border-color: #b8cfdf;
}


/* Удаление */

QPushButton[danger="true"] {
    color: #a84848;

    background: #fffafa;

    border-color: #efdada;
}


QPushButton[danger="true"]:hover {
    color: #963838;

    background: #feeeee;

    border-color: #e6bcbc;
}


/* ============================================================
   ТЕКСТОВЫЕ И ЧИСЛОВЫЕ ПОЛЯ
   ============================================================ */

QLineEdit,
QComboBox,
QSpinBox,
QDoubleSpinBox {
    min-height: 37px;

    padding-left: 9px;
    padding-right: 9px;

    color: #213a51;

    background: #ffffff;

    border: 1px solid #cfdae5;
    border-radius: 8px;

    font-size: 13px;

    selection-background-color: #24688e;
}


QLineEdit:hover,
QComboBox:hover,
QSpinBox:hover,
QDoubleSpinBox:hover {
    border-color: #91aec4;
}


QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus,
QDoubleSpinBox:focus {
    background: #ffffff;

    border: 2px solid #287899;
}


/* ============================================================
   ЗАБЛОКИРОВАННЫЕ ЧИСЛОВЫЕ ПАРАМЕТРЫ
   ============================================================ */

QSpinBox[locked="true"],
QDoubleSpinBox[locked="true"] {
    color: #30465b;

    background: #eef3f7;

    border: 1px solid #d9e2ea;
}


QSpinBox[locked="false"],
QDoubleSpinBox[locked="false"] {
    color: #102d43;

    background: #ffffff;

    border: 2px solid #287c9d;
}


/* ============================================================
   ЗАБЛОКИРОВАННЫЙ COMBOBOX
   Например Линейная / Логарифмическая
   ============================================================ */

QComboBox[locked="true"] {
    color: #30465b;

    background: #eef3f7;

    border: 1px solid #d9e2ea;
}


QComboBox[locked="false"] {
    color: #102d43;

    background: #ffffff;

    border: 2px solid #287c9d;
}


QComboBox::drop-down {
    width: 28px;

    border: none;
}


QComboBox QAbstractItemView {
    color: #20374d;

    background: #ffffff;

    border: 1px solid #cbd9e5;

    selection-background-color: #dcebf4;
    selection-color: #173c58;

    outline: none;
}


/* ============================================================
   КАРАНДАШ ✎ / СОХРАНИТЬ ✓ / ПОДСКАЗКА ?
   ============================================================ */

QToolButton#editParameter,
QToolButton#infoParameter {
    color: #31536c;

    background: #ffffff;

    border: 1px solid #cad8e5;
    border-radius: 8px;

    font-size: 15px;
    font-weight: 800;
}


QToolButton#editParameter:hover,
QToolButton#infoParameter:hover {
    color: #173e59;

    background: #e9f2f8;

    border-color: #8eafc7;
}


QToolButton#editParameter:pressed,
QToolButton#infoParameter:pressed {
    background: #d9e9f3;
}


/* ============================================================
   КНОПКА "ПО УМОЛЧАНИЮ"
   ============================================================ */

QToolButton#resetParameters {
    min-height: 30px;

    padding-left: 10px;
    padding-right: 10px;

    color: #31536c;

    background: #eaf1f6;

    border: 1px solid #d3e0ea;
    border-radius: 8px;

    font-size: 11px;
    font-weight: 700;
}


QToolButton#resetParameters:hover {
    color: #173f59;

    background: #dceaf3;

    border-color: #b5ccdc;
}


/* ============================================================
   СПИСКИ
   ============================================================ */

QListWidget,
QTableWidget {
    color: #223b52;

    background: #ffffff;

    border: 1px solid #d9e3ec;
    border-radius: 10px;

    alternate-background-color: #f7f9fc;

    outline: none;
}


QListWidget::item {
    padding: 9px 8px;

    margin: 2px;

    border-radius: 6px;
}


QListWidget::item:hover {
    background: #edf4f8;
}


QListWidget::item:selected {
    color: #173d58;

    background: #dcebf4;
}


/* ============================================================
   ТАБЛИЦЫ
   ============================================================ */

QHeaderView::section {
    color: #20425d;

    background: #edf2f7;

    padding: 9px;

    border: none;
    border-right: 1px solid #dce6ef;
    border-bottom: 1px solid #dce6ef;

    font-weight: 700;
}


/* ============================================================
   SCROLL AREA
   ============================================================ */

QScrollArea {
    background: transparent;

    border: none;
}


/* ============================================================
   ВЕРТИКАЛЬНАЯ ПРОКРУТКА
   ============================================================ */

QScrollBar:vertical {
    width: 9px;

    margin: 3px 1px;

    background: transparent;

    border: none;
}


QScrollBar::handle:vertical {
    min-height: 35px;

    background: #b8c8d5;

    border-radius: 4px;
}


QScrollBar::handle:vertical:hover {
    background: #88a7bc;
}


QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;

    border: none;

    background: transparent;
}


QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}


/* ============================================================
   ГОРИЗОНТАЛЬНАЯ ПРОКРУТКА
   На основных настройках она запрещена кодом.
   Здесь оставляем максимально компактное оформление на случай,
   если какой-либо другой виджет её использует.
   ============================================================ */

QScrollBar:horizontal {
    height: 8px;

    margin: 1px;

    background: transparent;

    border: none;
}


QScrollBar::handle:horizontal {
    min-width: 30px;

    background: #bdcad5;

    border-radius: 4px;
}


QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;

    border: none;

    background: transparent;
}


/* ============================================================
   SPLITTER
   ============================================================ */

QSplitter::handle {
    background: transparent;
}


QSplitter::handle:horizontal {
    width: 8px;
}


QSplitter::handle:horizontal:hover {
    background: #e2eaf1;

    border-radius: 4px;
}


/* ============================================================
   CANVAS
   ============================================================ */

QGraphicsView {
    background: #1c293a;

    border: none;
    border-radius: 10px;
}


/* ============================================================
   CHECKBOX
   ============================================================ */

QCheckBox {
    spacing: 9px;

    color: #30475d;
}


QCheckBox::indicator {
    width: 16px;
    height: 16px;
}


/* ============================================================
   STATUS BAR
   ============================================================ */

QStatusBar {
    color: #50657a;

    background: #ffffff;

    border-top: 1px solid #dce5ed;

    font-size: 11px;
}


/* ============================================================
   TOOLTIP
   ============================================================ */

QToolTip {
    color: #ffffff;

    background: #173148;

    border: 1px solid #294a64;
    border-radius: 6px;

    padding: 8px;

    font-size: 12px;
}


/* ============================================================
   MESSAGE BOX
   ============================================================ */

QMessageBox {
    background: #f5f8fb;
}


QMessageBox QLabel {
    color: #20364b;

    min-width: 260px;
}


/* ============================================================
   ФОРМЫ
   ============================================================ */

QFormLayout {
    spacing: 8px;
}


/* ============================================================
   СОВРЕМЕННЫЕ ФАЙЛОВЫЕ ДИАЛОГИ
   ============================================================ */

QFileDialog#modernFileDialog {
    background: #f3f6fa;
}

QFileDialog#modernFileDialog QLabel {
    color: #294157;
    font-size: 12px;
}

QFileDialog#modernFileDialog QTreeView,
QFileDialog#modernFileDialog QListView {
    background: #ffffff;
    border: 1px solid #d8e2eb;
    border-radius: 10px;
    padding: 4px;
    outline: none;
    alternate-background-color: #f7f9fc;
}

QFileDialog#modernFileDialog QTreeView::item,
QFileDialog#modernFileDialog QListView::item {
    min-height: 28px;
    padding: 4px 7px;
    border-radius: 6px;
}

QFileDialog#modernFileDialog QTreeView::item:hover,
QFileDialog#modernFileDialog QListView::item:hover {
    background: #edf4f8;
}

QFileDialog#modernFileDialog QTreeView::item:selected,
QFileDialog#modernFileDialog QListView::item:selected {
    color: #173d58;
    background: #dcebf4;
}

QFileDialog#modernFileDialog QToolButton {
    min-width: 32px;
    min-height: 32px;
    color: #31536c;
    background: #ffffff;
    border: 1px solid #cad8e5;
    border-radius: 8px;
}

QFileDialog#modernFileDialog QToolButton:hover {
    background: #e9f2f8;
    border-color: #8eafc7;
}

QFileDialog#modernFileDialog QPushButton {
    min-width: 100px;
}


/* ============================================================
   БРЕНДИРОВАННЫЕ ИНФОРМАЦИОННЫЕ ОКНА
   ============================================================ */

QDialog#modernMessageDialog {
    background: #f7f9fc;
}

QDialog#modernMessageDialog QLabel#messageTitle {
    color: #173a55;
    font-size: 18px;
    font-weight: 800;
}

QDialog#modernMessageDialog QLabel#messageBody {
    color: #425a70;
    font-size: 13px;
    line-height: 1.4;
}

QDialog#modernMessageDialog QLabel#messageIcon {
    background: #ffffff;
    border: 1px solid #d9e3ec;
    border-radius: 12px;
    padding: 2px;
}

"""


def apply_modern_theme(app: QApplication) -> None:
    """
    Применить единый современный стиль приложения.
    """

    app.setStyle("Fusion")

    app.setFont(
        QFont(
            "DejaVu Sans",
            10,
        )
    )

    app.setStyleSheet(
        MODERN_QSS
    )