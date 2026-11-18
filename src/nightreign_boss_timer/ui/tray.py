"""The tray icon and its menu. The menu is rebuilt from the settings whenever they change."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from nightreign_boss_timer.ui.controller import Controller


class IconState(Enum):
    TRACKING = "tracking"
    FIGHT = "fight"
    PAUSED = "paused"
    ATTENTION = "attention"


_FILL = {
    IconState.TRACKING: QColor(190, 60, 40),
    IconState.FIGHT: QColor(255, 196, 87),
    IconState.PAUSED: QColor(110, 110, 110),
    IconState.ATTENTION: QColor(190, 60, 40),
}


def make_icon(state: IconState) -> QIcon:
    """A health bar on a dark square, drawn here so no image file is needed.

    The bar is red while tracking, gold during a fight and grey when paused. A gold dot in the
    corner means the tool needs attention.
    """
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(20, 22, 28))
    painter = QPainter(pixmap)
    painter.fillRect(8, 27, 48, 10, QColor(60, 60, 60))
    painter.fillRect(8, 27, 30, 10, _FILL[state])
    if state is IconState.ATTENTION:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(255, 196, 87))
        painter.setPen(QColor(20, 22, 28))
        painter.drawEllipse(40, 4, 20, 20)
    painter.end()
    return QIcon(pixmap)


class Tray:
    def __init__(self, controller: Controller, quit_app: Callable[[], None]) -> None:
        self._controller = controller
        self._quit = quit_app
        self._state = IconState.TRACKING
        self.icon = QSystemTrayIcon(make_icon(self._state))
        self.menu = QMenu()  # kept here: the tray icon does not own its menu
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self._activated)
        # Queued: a change usually comes from one of this menu's own entries, and the menu must
        # not be torn down while that entry is still being handled.
        controller.changed.connect(self.rebuild, Qt.ConnectionType.QueuedConnection)
        self.rebuild()

    def _activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        # A left click or a double click on the icon opens the main window.
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._controller.show_window()

    def set_state(self, state: IconState) -> None:
        if state is not self._state:
            self._state = state
            self.icon.setIcon(make_icon(state))

    def _check(self, menu: QMenu, text: str, on: bool, changed: Callable[[bool], None]) -> None:
        action = QAction(text, menu, checkable=True)
        action.setChecked(on)
        action.toggled.connect(changed)
        menu.addAction(action)

    def rebuild(self) -> None:
        controller, translate = self._controller, self._controller.translate
        settings = controller.settings
        self.icon.setToolTip(translate("app.name"))
        menu = self.menu
        menu.clear()
        self._check(menu, translate("tray.tracking"), controller.tracking, controller.set_tracking)

        tables = menu.addMenu(translate("tray.table", table=settings.active_table))
        group = QActionGroup(tables)
        for name in settings.table_names():
            action = QAction(name, tables, checkable=True)
            action.setChecked(name == settings.active_table)
            action.triggered.connect(lambda _checked, name=name: controller.set_table(name))
            group.addAction(action)
            tables.addAction(action)

        menu.addSeparator()
        self._check(
            menu,
            translate("tray.show_overlay"),
            controller.overlay_visible,
            controller.set_overlay_visible,
        )
        menu.addAction(translate("tray.open_records_file"), controller.open_records_file)
        menu.addSeparator()
        menu.addAction(translate("tray.calibrate"), controller.calibrate)
        menu.addAction(translate("tray.open_window"), controller.show_window)
        menu.addSeparator()
        menu.addAction(translate("tray.quit"), self._quit)
