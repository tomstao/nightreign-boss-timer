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
from PySide6.QtWidgets import QApplication

from nightreign_boss_timer import settings as settings_file
from nightreign_boss_timer.capture import ScreenGrabber, WindowsScreen, enable_dpi_awareness
from nightreign_boss_timer.engine import (
    GAME_TITLE,
    MIN_WINDOW,
    Engine,
    State,
    StepResult,
    records_path,
)
from nightreign_boss_timer.i18n import Translator
from nightreign_boss_timer.ocr import NameReader
from nightreign_boss_timer.records import FightRecord, RecordStore
from nightreign_boss_timer.ui.calibration_window import CalibrationWindow
from nightreign_boss_timer.ui.controller import Controller
from nightreign_boss_timer.ui.main_window import MainWindow
from nightreign_boss_timer.ui.overlay import Overlay
from nightreign_boss_timer.ui.presenter import best_time, overlay_text
from nightreign_boss_timer.ui.tray import IconState, Tray


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
        self.controller = Controller(self.settings, self.translate, self.store)
        self.calibration = CalibrationWindow(
            self.settings, self.translate, self._take_picture, self.controller.save
        )

        self.overlay = Overlay()
        self.result: FightRecord | None = None
        self.result_at = 0.0
        self.best: float | None = None
        self.notice = ""
        self.notice_at = 0.0
        # True while finished fights are waiting because the records file is open elsewhere.
        self.rows_held = False

        self.window = MainWindow(self.controller)
        self.controller.window_requested.connect(self.window.show_page)
        self.tray = Tray(self.controller, application.quit)
        self.tray.icon.show()
        self.controller.changed.connect(self._apply)
        self.controller.notice.connect(self._show_notice)
        self.controller.calibration_requested.connect(self.calibration.start)

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._step)
        application.aboutToQuit.connect(self.close)
        self._step()

    def _apply(self) -> None:
        """Bring the engine and the overlay in line with what the user chose."""
        self.engine.paused = not self.controller.tracking
        self.overlay.set_enabled(self.controller.overlay_visible)
        self._step()

    def _show_notice(self, text: str) -> None:
        self.notice, self.notice_at = text, time.monotonic()

    def _take_picture(self) -> NDArray[np.uint8] | None:
        """The whole game image for calibration, or None if the game window is not found."""
        window = self.screen.find_window(self.title)
        if window is None or window.width < MIN_WINDOW or window.height < MIN_WINDOW:
            return None
        # A grabber of its own, released straight away: a full picture is large, and the
        # engine's grabbers are kept for the small regions it reads all the time.
        with ScreenGrabber(window.width, window.height) as grabber:
            return grabber.grab(window.left, window.top)

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
            self.rows_held = not result.saved
        now = time.monotonic()
        self.overlay.show_text(
            overlay_text(
                result.snapshot,
                self.translate,
                result=self.result,
                result_age_s=now - self.result_at,
                best_s=self.best,
                notice=self.notice,
                notice_age_s=now - self.notice_at,
            )
        )
        self.tray.set_state(self._icon_state(result.snapshot.state))
        self.controller.set_state(result.snapshot.state)

    def _icon_state(self, state: State) -> IconState:
        if state is State.PAUSED:
            return IconState.PAUSED
        if state is State.NO_GAME or self.rows_held:
            return IconState.ATTENTION
        return IconState.FIGHT if state is State.FIGHT else IconState.TRACKING

    def close(self) -> None:
        self.timer.stop()
        self.calibration.close()
        self.window.close()
        self.screen.close()
        self.tray.icon.hide()


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
