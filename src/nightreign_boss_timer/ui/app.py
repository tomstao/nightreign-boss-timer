"""Run the timer with its overlay and tray icon.

    uv run python -m nightreign_boss_timer.ui.app

A timer on the UI thread drives the engine. One step takes a few milliseconds, a few times per
second, so it does not need a thread of its own.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from nightreign_boss_timer import __version__
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
from nightreign_boss_timer.ui.global_hotkeys import GlobalHotkeys
from nightreign_boss_timer.ui.main_window import MainWindow
from nightreign_boss_timer.ui.overlay import Overlay
from nightreign_boss_timer.ui.presenter import best_time, overlay_text
from nightreign_boss_timer.ui.setup_window import SetupWindow
from nightreign_boss_timer.ui.tray import IconState, Tray

log = logging.getLogger("nightreign_boss_timer")


class App:
    def __init__(
        self,
        application: QApplication,
        title: str,
        records: Path | None,
        settings_path: Path | None = None,
    ) -> None:
        """``settings_path`` is for the self-test, which must not touch the real settings."""
        self.settings = settings_file.load(settings_path)
        self.translate = Translator(self.settings.ui_language)
        self.store = RecordStore(records or records_path(self.settings))
        self.screen = WindowsScreen()
        try:
            reader = NameReader()
        except FileNotFoundError:
            reader = None  # fights are still timed, and the boss is recorded as unknown
            log.warning("Text model not found: boss names will be recorded as unknown")
        self.reader = reader
        self.title = title
        self.engine = Engine(self.settings, self.screen, self.store, reader, title=title)
        self.controller = Controller(
            self.settings, self.translate, self.store, settings_path=settings_path
        )
        self.calibration = CalibrationWindow(
            self.settings, self.translate, self._take_picture, self.controller.save
        )

        self.controller.probe = self.engine.probe
        self.overlay = Overlay()
        self.overlay.set_position(self.settings.overlay_position)
        self.overlay.set_in_captures(self.settings.overlay_in_captures)
        self.overlay.moved.connect(lambda x, y: self.controller.set_overlay_position((x, y)))
        self.controller.window_shown.connect(self._window_shown)
        self.result: FightRecord | None = None
        self.result_at = 0.0
        self.best: float | None = None
        self.notice = ""
        self.notice_at = 0.0
        # True while finished fights are waiting because the records file is open elsewhere.
        self.rows_held = False

        self.window = MainWindow(self.controller)
        self.controller.window_requested.connect(self.window.show_page)
        self.setup = SetupWindow(self.controller)
        self.controller.setup_requested.connect(self.setup.start)
        self.tray = Tray(self.controller, application.quit)
        self.tray.icon.show()
        self.hotkeys = GlobalHotkeys()
        self.hotkeys.triggered.connect(self.controller.run_action)
        self.controller.hotkey_applier = self._apply_hotkeys
        self.controller.hotkeys_suspended.connect(self._suspend_hotkeys)
        self.controller.refresh_hotkeys()
        self.controller.changed.connect(self._apply)
        self.controller.notice.connect(self._show_notice)
        self.controller.calibration_requested.connect(self.calibration.start)
        self.controller.end_fight_requested.connect(self._end_fight)

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._step)
        application.aboutToQuit.connect(self.close)
        self._step()
        if not self.settings.setup_done:
            self.setup.start()

    def _apply(self) -> None:
        """Bring the engine and the overlay in line with what the user chose."""
        self.engine.paused = not self.controller.tracking
        self.overlay.set_enabled(self.controller.overlay_visible)
        self.overlay.set_position(self.settings.overlay_position)
        self.overlay.set_in_captures(self.settings.overlay_in_captures)
        self.controller.refresh_hotkeys()  # a table or a shortcut may have changed
        self._step()

    def _apply_hotkeys(self, settings: settings_file.Settings) -> set[str]:
        self.hotkeys.apply(settings)
        return self.hotkeys.failed

    def _suspend_hotkeys(self, suspended: bool) -> None:
        if suspended:
            self.hotkeys.manager.release_all()
        else:
            self.controller.refresh_hotkeys()

    def _window_shown(self, shown: bool) -> None:
        # The overlay can be dragged while the main window is open, and only then: during
        # play it must never take a click meant for the game.
        self.overlay.set_movable(shown, self.translate("overlay.drag_hint"))

    def _end_fight(self) -> None:
        self.engine.end_fight()
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
            self.controller.records_changed.emit()
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
        self.hotkeys.close()
        self.calibration.close()
        self.setup.close()
        self.window.close()
        self.screen.close()
        self.tray.icon.hide()


def log_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".cache")
    return Path(base) / "nightreign-boss-timer" / "logs" / "app.log"


def start_logging() -> None:
    """Write warnings and crashes to a small log file.

    The packaged program has no console, so without this an error would leave no trace.
    """
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(path, maxBytes=500_000, backupCount=1, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)

    def crashed(kind: type[BaseException], error: BaseException, trace: object) -> None:
        log.critical("Unhandled error", exc_info=(kind, error, trace))  # type: ignore[arg-type]
        sys.__excepthook__(kind, error, trace)  # type: ignore[arg-type]

    sys.excepthook = crashed


def self_test(application: QApplication) -> int:
    """Start everything for a moment and say whether it works. Used on a freshly built program.

    It uses a temporary folder for settings and records, shows nothing that needs an answer,
    and returns 0 only if every part came up. In a packaged program the text model must be
    there too, because it is packed in.
    """
    with tempfile.TemporaryDirectory() as folder:
        app = App(
            application,
            "nightreign-boss-timer self-test: no such window",
            Path(folder) / "records.csv",
            settings_path=Path(folder) / "settings.json",
        )
        app.setup.close()
        problems = []
        for language in ("en", "zh_CN", "zh_TW"):
            app.controller.set_language(language)
            if app.translate("tray.quit") == "tray.quit":
                problems.append(f"no texts for {language}")
        if app.reader is None and getattr(sys, "frozen", False):
            problems.append("the text model is not packed in")
        if not app.tray.menu.actions():
            problems.append("the tray menu is empty")
        app.controller.show_window("records")
        QTimer.singleShot(1500, application.quit)
        application.exec()
        failed = sorted(app.controller.failed_hotkeys)
        del app
    for problem in problems:
        log.error("Self-test: %s", problem)
    log.info("Self-test %s (hotkeys refused: %s)", "failed" if problems else "passed", failed)
    return 1 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="nightreign-boss-timer")
    parser.add_argument("--title", default=GAME_TITLE, help="title of the game window")
    parser.add_argument("--records", type=Path, default=None, help="path of the records CSV")
    parser.add_argument(
        "--settings",
        type=Path,
        default=None,
        help="path of the settings file, instead of the usual one",
    )
    parser.add_argument(
        "--self-test", action="store_true", help="start, check that everything loads, and exit"
    )
    args = parser.parse_args()

    start_logging()
    log.info("Starting version %s", __version__)
    enable_dpi_awareness()
    application = QApplication(sys.argv[:1])
    application.setQuitOnLastWindowClosed(False)
    try:
        if args.self_test:
            return self_test(application)
        app = App(application, args.title, args.records, args.settings)
        code = application.exec()
        del app
    except Exception:
        log.exception("Could not start")
        return 1
    return code


if __name__ == "__main__":
    sys.exit(main())
