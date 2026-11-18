"""The overlay: a small see-through panel over the game that never takes focus or clicks.

It is see-through as a whole, by window opacity, and not pixel by pixel. Windows only agrees to
leave a window out of screen captures when it is drawn that way, and the overlay must stay out
of them: the tool reads the screen, and would otherwise read its own overlay.

While the main window is open the overlay can be dragged to a new place. It then shows a frame,
takes mouse clicks, and stays visible whatever it has to say.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from nightreign_boss_timer.capture import exclude_from_capture
from nightreign_boss_timer.ui.presenter import OverlayText

DEFAULT_POSITION = (40, 200)
_PADDING = 10
_LINE_GAP = 4
_BACKGROUND = QColor(10, 12, 16)
_OPACITY = 0.82
_TEXT = QColor(235, 235, 235)
_WARNING = QColor(255, 196, 87)
_FRAME = QColor(80, 220, 255)

_FLAGS = (
    Qt.WindowType.FramelessWindowHint
    | Qt.WindowType.WindowStaysOnTopHint
    | Qt.WindowType.Tool  # keeps it out of the taskbar and Alt+Tab
    | Qt.WindowType.WindowDoesNotAcceptFocus
)


class Overlay(QWidget):
    # The user dragged the overlay and let go. Carries its new top-left corner on the desktop.
    moved = Signal(int, int)

    def __init__(self) -> None:
        # Clicks go through to the game, except while the overlay is being moved.
        super().__init__(None, _FLAGS | Qt.WindowType.WindowTransparentForInput)
        self.setWindowOpacity(_OPACITY)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._text = OverlayText(())
        self._shown = OverlayText(())
        self._enabled = True
        self._movable = False
        self._move_hint = ""
        self._grab: QPoint | None = None
        self._font = QFont("Segoe UI", 12)
        self._font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self.move(QPoint(*DEFAULT_POSITION))
        # True once Windows has agreed to keep the overlay out of screen captures.
        self.hidden_from_capture = exclude_from_capture(int(self.winId()))

    def show_text(self, text: OverlayText) -> None:
        """Replace what the overlay says. Does nothing if it already says that."""
        if text == self._text:
            return
        self._text = text
        self._layout()

    def set_enabled(self, enabled: bool) -> None:
        """Turn the overlay on or off. It also hides itself when it has nothing to say."""
        self._enabled = enabled
        self._apply_visibility()

    def set_position(self, position: tuple[int, int] | None) -> None:
        """Put the overlay's top-left corner here, or back where it starts with None."""
        self.move(QPoint(*(position or DEFAULT_POSITION)))

    def set_movable(self, movable: bool, hint: str = "") -> None:
        """Let the user drag the overlay (True), or give clicks back to the game (False).

        ``hint`` is shown while movable if the overlay has nothing else to say.
        """
        self._move_hint = hint
        if movable == self._movable:
            self._layout()
            return
        self._movable = movable
        self._grab = None
        flags = _FLAGS if movable else _FLAGS | Qt.WindowType.WindowTransparentForInput
        # Changing the flags makes Windows build a new window, which is hidden and has
        # forgotten that it was to be left out of captures.
        self.setWindowFlags(flags)
        self.hidden_from_capture = exclude_from_capture(int(self.winId()))
        self.setCursor(Qt.CursorShape.SizeAllCursor if movable else Qt.CursorShape.ArrowCursor)
        self._layout()

    def _layout(self) -> None:
        """Size the window for what it shows now, and show or hide it."""
        text = self._text
        if self._movable and not text.lines and self._move_hint:
            text = OverlayText((self._move_hint,))
        self._shown = text
        self.setFont(self._font)
        metrics = self.fontMetrics()
        width = max((metrics.horizontalAdvance(line) for line in text.lines), default=0)
        height = len(text.lines) * metrics.height() + max(0, len(text.lines) - 1) * _LINE_GAP
        self.resize(width + 2 * _PADDING, height + 2 * _PADDING)
        self.update()
        self._apply_visibility()

    def _apply_visibility(self) -> None:
        self.setVisible(self._enabled and bool(self._shown.lines))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._movable and event.button() == Qt.MouseButton.LeftButton:
            self._grab = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._grab is not None:
            self.move(event.globalPosition().toPoint() - self._grab)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._grab is not None:
            self._grab = None
            self.moved.emit(self.x(), self.y())

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self._shown.lines:
            return
        painter = QPainter(self)
        painter.fillRect(self.rect(), _BACKGROUND)
        if self._movable:
            painter.setPen(QPen(_FRAME, 2))
            painter.drawRect(self.rect().adjusted(1, 1, -1, -1))
        painter.setFont(self._font)
        painter.setPen(_WARNING if self._shown.warning else _TEXT)
        metrics = painter.fontMetrics()
        y = _PADDING + metrics.ascent()
        for line in self._shown.lines:
            painter.drawText(_PADDING, y, line)
            y += metrics.height() + _LINE_GAP
        painter.end()
