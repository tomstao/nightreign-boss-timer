"""Run the timer with its overlay and tray icon.

    uv run python -m nightreign_boss_timer.ui.app

A timer on the UI thread drives the engine. One step takes a few milliseconds, a few times per
second, so it does not need a thread of its own.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from nightreign_boss_timer import settings as settings_file
from nightreign_boss_timer.capture import ScreenGrabber, WindowsScreen, enable_dpi_awareness
from nightreign_boss_timer.engine import (
    GAME_TITLE,
    MIN_WINDOW,
    Engine,
    StepResult,
    records_path,
)
from nightreign_boss_timer.i18n import Translator
from nightreign_boss_timer.ocr import NameReader
from nightreign_boss_timer.records import FightRecord, RecordStore
from nightreign_boss_timer.ui.calibration_window import CalibrationWindow
from nightreign_boss_timer.ui.overlay import Overlay
from nightreign_boss_timer.ui.presenter import best_time, overlay_text


def _icon() -> QIcon:
    """A plain red bar on a dark square, drawn here so no image file is needed."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(20, 22, 28))
    painter = QPainter(pixmap)
    painter.fillRect(8, 27, 48, 10, QColor(60, 60, 60))
    painter.fillRect(8, 27, 30, 10, QColor(190, 60, 40))
    painter.end()
    return QIcon(pixmap)


class App:
    def __init__(self, application: QApplication, title: str, records: Path | None) -> None:
        self.settings = settings_file.load()
        self.translate = Translator(self.settings.ui_language)
        self.store = RecordStore(records or records_path(self.settings))
        self.screen = WindowsScreen()
        try:
            reader = NameReader()
        except FileNotFoundError:
            reader = None  # fights are still timed, and the boss is recorded as unknown
        self.title = title
        self.engine = Engine(self.settings, self.screen, self.store, reader, title=title)
        self.calibration = CalibrationWindow(
            self.settings, self.translate, self._take_picture, self._save_settings
        )

        self.overlay = Overlay()
        self.result: FightRecord | None = None
        self.result_at = 0.0
        self.best: float | None = None

        self.tray = QSystemTrayIcon(_icon())
        self.tray.setToolTip(self.translate("app.name"))
        menu = QMenu()
        self.tracking = QAction(self.translate("tray.tracking"), menu, checkable=True)
        self.tracking.setChecked(True)
        self.tracking.toggled.connect(self._set_tracking)
        menu.addAction(self.tracking)
        show = QAction(self.translate("tray.show_overlay"), menu, checkable=True)
        show.setChecked(True)
        show.toggled.connect(self.overlay.set_enabled)
        menu.addAction(show)
        menu.addSeparator()
        menu.addAction(self.translate("tray.calibrate"), self.calibration.start)
        menu.addSeparator()
        menu.addAction(self.translate("tray.quit"), application.quit)
        self._menu = menu  # keep it alive: the tray icon does not own it
        self.tray.setContextMenu(menu)
        self.tray.show()

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._step)
        application.aboutToQuit.connect(self.close)
        self._step()

    def _set_tracking(self, on: bool) -> None:
        self.engine.paused = not on

    def _take_picture(self) -> NDArray[np.uint8] | None:
        """The whole game image for calibration, or None if the game window is not found."""
        window = self.screen.find_window(self.title)
        if window is None or window.width < MIN_WINDOW or window.height < MIN_WINDOW:
            return None
        # A grabber of its own, released straight away: a full picture is large, and the
        # engine's grabbers are kept for the small regions it reads all the time.
        with ScreenGrabber(window.width, window.height) as grabber:
            return grabber.grab(window.left, window.top)

    def _save_settings(self) -> None:
        # The engine reads the regions from these same settings on every step, so a new
        # calibration is in use at once.
        settings_file.save(self.settings)

    def _step(self) -> None:
        result = self.engine.step()
        self._show(result)
        self.timer.start(max(1, round(result.delay_s * 1000)))

    def _show(self, result: StepResult) -> None:
        if result.record:
            # The best time is looked up before this fight could count towards it.
            earlier = [r for r in self.store.read_all() if r != result.record]
            self.best = best_time(earlier, result.record.boss, result.record.table)
            self.result, self.result_at = result.record, time.monotonic()
        self.overlay.show_text(
            overlay_text(
                result.snapshot,
                self.translate,
                result=self.result,
                result_age_s=time.monotonic() - self.result_at,
                best_s=self.best,
            )
        )

    def close(self) -> None:
        self.timer.stop()
        self.calibration.close()
        self.screen.close()
        self.tray.hide()


def main() -> int:
    parser = argparse.ArgumentParser(prog="nightreign-boss-timer")
    parser.add_argument("--title", default=GAME_TITLE, help="title of the game window")
    parser.add_argument("--records", type=Path, default=None, help="path of the records CSV")
    args = parser.parse_args()

    enable_dpi_awareness()
    application = QApplication(sys.argv[:1])
    application.setQuitOnLastWindowClosed(False)
    app = App(application, args.title, args.records)
    code = application.exec()
    del app
    return code


if __name__ == "__main__":
    sys.exit(main())
