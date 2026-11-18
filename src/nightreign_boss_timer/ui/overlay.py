"""The overlay: a small see-through panel over the game that never takes focus or clicks."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from nightreign_boss_timer.ui.presenter import OverlayText

_PADDING = 10
_LINE_GAP = 4
_BACKGROUND = QColor(10, 12, 16, 170)
_TEXT = QColor(235, 235, 235)
_WARNING = QColor(255, 196, 87)


class Overlay(QWidget):
    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # keeps it out of the taskbar and Alt+Tab
            | Qt.WindowType.WindowTransparentForInput  # clicks go through to the game
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._text = OverlayText(())
        self._enabled = True
        self._font = QFont("Segoe UI", 12)
        self._font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self.move(QPoint(40, 200))

    def show_text(self, text: OverlayText) -> None:
        """Replace what the overlay says. Does nothing if it already says that."""
        if text == self._text:
            return
        self._text = text
        self.setFont(self._font)
        metrics = self.fontMetrics()
        width = max((metrics.horizontalAdvance(line) for line in text.lines), default=0)
        height = len(text.lines) * metrics.height() + max(0, len(text.lines) - 1) * _LINE_GAP
        self.resize(width + 2 * _PADDING, height + 2 * _PADDING)
        self.update()
        self._apply_visibility()

    def set_enabled(self, enabled: bool) -> None:
        """Turn the overlay on or off. It also hides itself when it has nothing to say."""
        self._enabled = enabled
        self._apply_visibility()

    def _apply_visibility(self) -> None:
        self.setVisible(self._enabled and bool(self._text.lines))

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self._text.lines:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_BACKGROUND)
        painter.drawRoundedRect(self.rect(), 6, 6)
        painter.setFont(self._font)
        painter.setPen(_WARNING if self._text.warning else _TEXT)
        metrics = painter.fontMetrics()
        y = _PADDING + metrics.ascent()
        for line in self._text.lines:
            painter.drawText(_PADDING, y, line)
            y += metrics.height() + _LINE_GAP
        painter.end()
