"""A picture of the game with one box on it that the user drags into place.

The picture is scaled to fit the widget, and the box is kept in picture pixels, so what is saved
does not depend on how large the window happens to be. Drag a corner to resize, drag inside the
box to move it, drag anywhere else to draw a new one. Arrow keys move the box one picture pixel,
and with Shift they move its bottom-right corner instead.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from nightreign_boss_timer.calibration import Corner, Selection, drag_corner, fit, move

# How close to a corner, in widget pixels, a press must be to grab it.
_GRAB = 9
_HANDLE = 4
_BACKGROUND = QColor(16, 18, 22)
_SHADE = QColor(0, 0, 0, 110)
_OUTLINE = QColor(80, 220, 255)

_ARROWS = {
    Qt.Key.Key_Left: (-1, 0),
    Qt.Key.Key_Right: (1, 0),
    Qt.Key.Key_Up: (0, -1),
    Qt.Key.Key_Down: (0, 1),
}
_CURSORS = {
    Corner.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
    Corner.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
    Corner.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
    Corner.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
}


def to_image(picture: NDArray[np.uint8]) -> QImage:
    """A Qt image holding its own copy of an RGB array of shape (rows, columns, 3)."""
    picture = np.ascontiguousarray(picture)
    rows, columns = picture.shape[:2]
    return QImage(picture.data, columns, rows, 3 * columns, QImage.Format.Format_RGB888).copy()


class RegionCanvas(QWidget):
    # Sent whenever the box changes, by mouse, by keyboard or from code.
    selection_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setMinimumSize(320, 180)
        self._image: QImage | None = None
        self._selection = Selection(0, 0, 0, 0)
        # What a drag in progress is doing: a corner, "move" with the grab offset, or nothing.
        self._corner: Corner | None = None
        self._move_from: tuple[int, int] | None = None

    # --- contents -------------------------------------------------------------------------------

    def set_picture(self, picture: NDArray[np.uint8], selection: Selection) -> None:
        self._image = to_image(picture)
        self.set_selection(selection)

    @property
    def selection(self) -> Selection:
        return self._selection

    def set_selection(self, selection: Selection) -> None:
        if self._image is None:
            return
        selection = fit(selection, self._image.width(), self._image.height())
        if selection != self._selection:
            self._selection = selection
            self.selection_changed.emit()
        self.update()

    # --- picture pixels and widget pixels -------------------------------------------------------

    def _scale(self) -> float:
        return min(self.width() / self._image.width(), self.height() / self._image.height())

    def _origin(self) -> tuple[float, float]:
        scale = self._scale()
        return (
            (self.width() - self._image.width() * scale) / 2,
            (self.height() - self._image.height() * scale) / 2,
        )

    def to_widget(self, x: float, y: float) -> QPointF:
        """Where a picture position is drawn."""
        scale, (left, top) = self._scale(), self._origin()
        return QPointF(left + x * scale, top + y * scale)

    def to_picture(self, position: QPointF) -> tuple[int, int]:
        """The picture position under a widget position. May lie outside the picture."""
        scale, (left, top) = self._scale(), self._origin()
        return round((position.x() - left) / scale), round((position.y() - top) / scale)

    def _box(self) -> QRectF:
        s = self._selection
        return QRectF(self.to_widget(s.left, s.top), self.to_widget(s.right, s.bottom))

    def _corner_at(self, position: QPointF) -> Corner | None:
        box = self._box()
        corners = {
            Corner.TOP_LEFT: box.topLeft(),
            Corner.TOP_RIGHT: box.topRight(),
            Corner.BOTTOM_LEFT: box.bottomLeft(),
            Corner.BOTTOM_RIGHT: box.bottomRight(),
        }
        distance = {c: (p - position).manhattanLength() for c, p in corners.items()}
        nearest = min(distance, key=distance.get)
        return nearest if distance[nearest] <= _GRAB else None

    def _inside(self, position: QPointF) -> bool:
        # A health bar is only a few pixels tall, so allow a little slack around the box.
        return self._box().adjusted(-3, -3, 3, 3).contains(position)

    # --- mouse and keyboard ---------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._image is None or event.button() != Qt.MouseButton.LeftButton:
            return
        position = event.position()
        x, y = self.to_picture(position)
        self._corner = self._corner_at(position)
        if self._corner is None and self._inside(position):
            self._move_from = (x - self._selection.left, y - self._selection.top)
        elif self._corner is None:
            # Start a new box here. The rest of the drag pulls its bottom-right corner.
            self.set_selection(Selection(x, y, x, y))
            self._corner = Corner.BOTTOM_RIGHT

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._image is None:
            return
        position = event.position()
        x, y = self.to_picture(position)
        size = self._image.width(), self._image.height()
        if self._corner is not None:
            self.set_selection(drag_corner(self._selection, self._corner, x, y, *size))
        elif self._move_from is not None:
            dx = x - self._move_from[0] - self._selection.left
            dy = y - self._move_from[1] - self._selection.top
            self.set_selection(move(self._selection, dx, dy, *size))
        else:
            corner = self._corner_at(position)
            if corner is not None:
                self.setCursor(_CURSORS[corner])
            elif self._inside(position):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._corner = None
        self._move_from = None

    def keyPressEvent(self, event: QKeyEvent) -> None:
        step = _ARROWS.get(event.key())
        if step is None or self._image is None:
            super().keyPressEvent(event)
            return
        size = self._image.width(), self._image.height()
        s = self._selection
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            corner = Corner.BOTTOM_RIGHT
            self.set_selection(drag_corner(s, corner, s.right + step[0], s.bottom + step[1], *size))
        else:
            self.set_selection(move(s, *step, *size))

    # --- drawing --------------------------------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), _BACKGROUND)
        if self._image is None:
            painter.end()
            return
        picture = QRectF(
            self.to_widget(0, 0), self.to_widget(self._image.width(), self._image.height())
        )
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(picture, self._image)

        # Darken everything but the box, then outline it just outside its pixels so the outline
        # never hides the edge of the bar.
        box = self._box()
        for shade in (
            QRectF(picture.left(), picture.top(), picture.width(), box.top() - picture.top()),
            QRectF(picture.left(), box.bottom(), picture.width(), picture.bottom() - box.bottom()),
            QRectF(picture.left(), box.top(), box.left() - picture.left(), box.height()),
            QRectF(box.right(), box.top(), picture.right() - box.right(), box.height()),
        ):
            painter.fillRect(shade, _SHADE)
        painter.setPen(QPen(_OUTLINE, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(box.adjusted(-1, -1, 0, 0))
        painter.setBrush(_OUTLINE)
        for corner in (box.topLeft(), box.topRight(), box.bottomLeft(), box.bottomRight()):
            # Each handle sits outside its corner, pointing away from the box.
            dx = -_HANDLE if corner.x() == box.left() else 0
            dy = -_HANDLE if corner.y() == box.top() else 0
            painter.drawRect(QRectF(corner.x() + dx, corner.y() + dy, _HANDLE, _HANDLE))
        painter.end()
