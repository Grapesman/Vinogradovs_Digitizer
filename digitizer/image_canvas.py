from __future__ import annotations

from typing import Optional

import cv2
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPainterPath, QPen, QPixmap, QWheelEvent
from .processing import sample_ink_color_at

from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
)


class ImageCanvas(QGraphicsView):
    roiSelected = Signal(QRectF)
    pointPicked = Signal(str, QPointF)
    colorPicked = Signal(QPointF, tuple)
    mouseMovedImage = Signal(QPointF)
    perspectiveSelected = Signal(object)  # list[(x, y)]
    editPointPicked = Signal(str, QPointF)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setMouseTracking(True)
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._image_bgr: Optional[np.ndarray] = None
        self._mode: Optional[str] = None
        self._roi_start: Optional[QPointF] = None
        self._temp_rect: Optional[QGraphicsRectItem] = None
        self._overlay_items: list = []
        self._guide_items: list = []
        self._roi_item: Optional[QGraphicsRectItem] = None
        self._perspective_points: list[QPointF] = []
        self._auto_fit = True

    @property
    def image_bgr(self) -> Optional[np.ndarray]:
        return self._image_bgr

    def set_image(self, image_bgr: np.ndarray) -> None:
        self._image_bgr = image_bgr.copy()
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
        pix = QPixmap.fromImage(qimg)
        self.scene().clear()
        self._pixmap_item = self.scene().addPixmap(pix)
        self._pixmap_item.setZValue(0)
        self.scene().setSceneRect(QRectF(0, 0, w, h))
        self._overlay_items.clear()
        self._guide_items.clear()
        self._roi_item = None
        self._perspective_points.clear()
        self.resetTransform()
        self._auto_fit = True
        self.fit_image()

    def fit_image(self) -> None:
        self._auto_fit = True
        if self._pixmap_item is not None:
            self.resetTransform()
            self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._auto_fit and self._pixmap_item is not None:
            self.fit_image()

    def set_mode(self, mode: Optional[str]) -> None:
        self._mode = mode
        self._roi_start = None
        if mode == "perspective":
            self._perspective_points = []
            self.clear_perspective_marks()
        if mode in {"h1", "h2", "scale_x1", "scale_x2", "color", "roi", "perspective", "edit_move", "edit_delete"}:
            self.setDragMode(QGraphicsView.NoDrag)
        else:
            self.setDragMode(QGraphicsView.ScrollHandDrag)

    def show_roi(self, rect: QRectF) -> None:
        if self._roi_item is not None:
            try:
                self.scene().removeItem(self._roi_item)
            except RuntimeError:
                pass
        pen = QPen(QColor(255, 170, 0), 2)
        self._roi_item = self.scene().addRect(rect.normalized(), pen)
        self._roi_item.setZValue(5)

    def add_rect_overlay(self, rect: QRectF, color: QColor, width: float = 2.0, dashed: bool = True) -> None:
        pen = QPen(color, width, Qt.DashLine if dashed else Qt.SolidLine)
        item = self.scene().addRect(rect.normalized(), pen, QBrush(Qt.NoBrush))
        item.setZValue(6)
        self._overlay_items.append(item)

    def add_marker(self, p: QPointF, color: QColor, radius: float = 5.0) -> None:
        item = self.scene().addEllipse(
            p.x() - radius, p.y() - radius, 2 * radius, 2 * radius,
            QPen(color, 2), QBrush(Qt.NoBrush),
        )
        item.setZValue(8)
        self._overlay_items.append(item)

    def add_curve_overlay(self, points: list[tuple[float, float]], color: QColor = QColor(255, 0, 255)) -> None:
        if not points:
            return
        ordered = sorted(points, key=lambda p: p[1])
        path = QPainterPath(QPointF(ordered[0][0], ordered[0][1]))
        prev_y = ordered[0][1]
        for x, y in ordered[1:]:
            # Do not visually bridge very large manually deleted gaps.
            if abs(y - prev_y) > 12:
                path.moveTo(QPointF(x, y))
            else:
                path.lineTo(QPointF(x, y))
            prev_y = y
        item = QGraphicsPathItem(path)
        item.setPen(QPen(color, 2.2))
        item.setZValue(7)
        self.scene().addItem(item)
        self._overlay_items.append(item)

    def add_mask_overlay(self, mask: np.ndarray, roi: tuple[float, float, float, float], color: QColor | None = None) -> None:
        if mask is None or mask.size == 0:
            return
        color = color or QColor(255, 0, 255, 105)
        h, w = mask.shape[:2]
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        active = mask > 0
        rgba[active, 0] = color.red()
        rgba[active, 1] = color.green()
        rgba[active, 2] = color.blue()
        rgba[active, 3] = color.alpha()
        qimg = QImage(rgba.data, w, h, 4 * w, QImage.Format_RGBA8888).copy()
        item = self.scene().addPixmap(QPixmap.fromImage(qimg))
        item.setPos(float(roi[0]), float(roi[1]))
        item.setZValue(4)
        self._overlay_items.append(item)

    def show_vertical_guides(self, xs: list[int]) -> None:
        self.clear_guides()
        if self._image_bgr is None:
            return
        h = self._image_bgr.shape[0]
        pen = QPen(QColor(0, 180, 255, 190), 1.5, Qt.DashLine)
        for x in xs:
            item = self.scene().addLine(float(x), 0.0, float(x), float(h - 1), pen)
            item.setZValue(6)
            self._guide_items.append(item)

    def clear_guides(self) -> None:
        for item in self._guide_items:
            try:
                self.scene().removeItem(item)
            except RuntimeError:
                pass
        self._guide_items.clear()

    def clear_perspective_marks(self) -> None:
        # Perspective marks are ordinary overlays; clearing all is predictable.
        self.clear_overlays(keep_roi=True)

    def clear_overlays(self, keep_roi: bool = True) -> None:
        for item in self._overlay_items:
            try:
                self.scene().removeItem(item)
            except RuntimeError:
                pass
        self._overlay_items.clear()
        if not keep_roi and self._roi_item is not None:
            try:
                self.scene().removeItem(self._roi_item)
            except RuntimeError:
                pass
            self._roi_item = None

    def _scene_point(self, event) -> QPointF:
        return self.mapToScene(event.position().toPoint())

    def _point_inside_image(self, p: QPointF) -> bool:
        return self._image_bgr is not None and 0 <= p.x() < self._image_bgr.shape[1] and 0 <= p.y() < self._image_bgr.shape[0]

    def _draw_perspective_progress(self) -> None:
        pts = self._perspective_points
        if not pts:
            return
        for p in pts:
            self.add_marker(p, QColor(255, 80, 40), 7)
        if len(pts) >= 2:
            pen = QPen(QColor(255, 80, 40), 2, Qt.DashLine)
            for a, b in zip(pts[:-1], pts[1:]):
                item = self.scene().addLine(a.x(), a.y(), b.x(), b.y(), pen)
                item.setZValue(9)
                self._overlay_items.append(item)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._mode and self._image_bgr is not None:
            p = self._scene_point(event)
            if not self._point_inside_image(p):
                return
            if self._mode == "roi":
                self._roi_start = p
                if self._temp_rect:
                    self.scene().removeItem(self._temp_rect)
                self._temp_rect = self.scene().addRect(
                    QRectF(p, p), QPen(QColor(255, 170, 0), 2, Qt.DashLine)
                )
                self._temp_rect.setZValue(10)
                return
            if self._mode in {"h1", "h2", "scale_x1", "scale_x2"}:
                self.pointPicked.emit(self._mode, p)
                self.set_mode(None)
                return
            if self._mode == "color":
                x = int(np.clip(round(p.x()), 0, self._image_bgr.shape[1] - 1))
                y = int(np.clip(round(p.y()), 0, self._image_bgr.shape[0] - 1))
                bgr = sample_ink_color_at(self._image_bgr, x, y)
                self.colorPicked.emit(p, bgr)
                self.set_mode(None)
                return
            if self._mode == "perspective":
                self._perspective_points.append(p)
                # Redraw progress without losing guide lines.
                self.clear_overlays(keep_roi=True)
                self._draw_perspective_progress()
                if len(self._perspective_points) == 4:
                    pts = [(q.x(), q.y()) for q in self._perspective_points]
                    self.perspectiveSelected.emit(pts)
                    self.set_mode(None)
                return
            if self._mode in {"edit_move", "edit_delete"}:
                self.editPointPicked.emit(self._mode, p)
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        p = self._scene_point(event)
        if self._point_inside_image(p):
            self.mouseMovedImage.emit(p)
        if self._mode == "roi" and self._roi_start is not None and self._temp_rect is not None:
            self._temp_rect.setRect(QRectF(self._roi_start, p).normalized())
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._mode == "roi" and self._roi_start is not None:
            p = self._scene_point(event)
            rect = QRectF(self._roi_start, p).normalized()
            if self._temp_rect is not None:
                self.scene().removeItem(self._temp_rect)
                self._temp_rect = None
            self._roi_start = None
            if rect.width() >= 5 and rect.height() >= 5:
                self.show_roi(rect)
                self.roiSelected.emit(rect)
            self.set_mode(None)
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        if self._image_bgr is None:
            return super().wheelEvent(event)
        self._auto_fit = False
        factor = 1.18 if event.angleDelta().y() > 0 else 1 / 1.18
        self.scale(factor, factor)
