import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the UI is Windows-only")

# Draw into memory, so the test needs no desktop and shows nothing on screen.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

if sys.platform == "win32":
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QApplication, QSystemTrayIcon

    from nightreign_boss_timer import settings as settings_file
    from nightreign_boss_timer.i18n import Translator
    from nightreign_boss_timer.records import COLUMNS, RecordStore
    from nightreign_boss_timer.settings import Settings
    from nightreign_boss_timer.ui.controller import Controller
    from nightreign_boss_timer.ui.tray import IconState, Tray, make_icon


@pytest.fixture(scope="module")
def application() -> "QApplication":
    return QApplication.instance() or QApplication([])


class Harness:
    def __init__(self, folder: Path, language: str = "en") -> None:
        self.settings = Settings(ui_language=language)
        self.settings.add_table("No-hit practice")
        self.settings_path = folder / "settings.json"
        self.opened: list[Path] = []
        self.notices: list[str] = []
        self.changes = 0
        self.quits = 0
        self.controller = Controller(
            self.settings,
            Translator(language),
            RecordStore(folder / "records" / "records.csv"),
            settings_path=self.settings_path,
            opener=self.opened.append,
        )
        self.controller.notice.connect(self.notices.append)
        self.controller.changed.connect(self._changed)
        self.tray = Tray(self.controller, self._quit)

    def _changed(self) -> None:
        self.changes += 1

    def _quit(self) -> None:
        self.quits += 1

    def texts(self) -> list[str]:
        return [action.text() for action in self.tray.menu.actions() if not action.isSeparator()]

    def entry(self, text: str) -> "QAction":
        return next(action for action in self.tray.menu.actions() if action.text() == text)

    def tables(self) -> list["QAction"]:
        """The entries of the table submenu that stand for a table."""
        return [a for a in self.tray.menu.actions()[1].menu().actions() if a.isCheckable()]


def test_menu_lists_everything_in_order(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    assert harness.texts() == [
        "Tracking",
        "Table: Arena",
        "Show overlay",
        "Open records",
        "Open records file in Excel",
        "Calibrate regions...",
        "Settings...",
        "Open main window",
        "Quit",
    ]
    assert harness.entry("Tracking").isChecked()
    assert harness.entry("Show overlay").isChecked()


def test_table_submenu_marks_the_active_table(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    assert [(a.text(), a.isChecked()) for a in harness.tables()] == [
        ("Arena", True),
        ("Normal", False),
        ("No-hit practice", False),
    ]


def test_choosing_a_table_switches_saves_and_tells_the_overlay(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    harness.tables()[2].trigger()
    application.processEvents()  # the menu is rebuilt a moment later

    assert harness.settings.active_table == "No-hit practice"
    assert settings_file.load(harness.settings_path).active_table == "No-hit practice"
    assert harness.notices == ["Table: No-hit practice"]
    assert harness.texts()[1] == "Table: No-hit practice"
    assert [a.isChecked() for a in harness.tables()] == [False, False, True]


def test_choosing_the_active_table_again_does_nothing(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    harness.tables()[0].trigger()
    assert harness.notices == []
    assert harness.changes == 0
    assert not harness.settings_path.exists()


def test_next_table_goes_round(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    for expected in ("Normal", "No-hit practice", "Arena"):
        harness.controller.next_table()
        assert harness.settings.active_table == expected
    assert harness.notices[-1] == "Table: Arena"


def test_tracking_and_overlay_switches(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    harness.entry("Tracking").trigger()
    application.processEvents()
    assert not harness.controller.tracking
    assert not harness.entry("Tracking").isChecked()
    assert harness.notices == ["Paused"]

    harness.controller.toggle_tracking()
    assert harness.controller.tracking
    assert harness.notices == ["Paused", "Tracking"]

    harness.entry("Show overlay").trigger()
    assert not harness.controller.overlay_visible
    harness.controller.toggle_overlay()
    assert harness.controller.overlay_visible


def test_open_records_file_creates_it_with_its_header(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    path = tmp_path / "records" / "records.csv"
    harness.entry("Open records file in Excel").trigger()
    assert harness.opened == [path]
    assert path.read_text(encoding="utf-8-sig").strip() == ",".join(COLUMNS)

    harness.controller.open_records_file()  # an existing file is opened as it is
    assert path.read_text(encoding="utf-8-sig").strip() == ",".join(COLUMNS)
    harness.controller.open_records_folder()
    assert harness.opened[-1] == path.parent


def test_clicking_the_icon_or_the_menu_entry_asks_for_the_main_window(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    asked: list[str] = []
    harness.controller.window_requested.connect(asked.append)
    harness.entry("Open main window").trigger()
    harness.entry("Open records").trigger()
    harness.tray.menu.actions()[1].menu().actions()[-1].trigger()  # Manage tables...
    harness.tray.icon.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
    harness.tray.icon.activated.emit(QSystemTrayIcon.ActivationReason.Context)  # a right click
    assert asked == ["", "records", "tables", ""]


def test_calibrate_and_quit(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    asked: list[bool] = []
    harness.controller.calibration_requested.connect(lambda: asked.append(True))
    harness.entry("Calibrate regions...").trigger()
    harness.entry("Quit").trigger()
    assert asked == [True]
    assert harness.quits == 1


@pytest.mark.parametrize("language", ["zh_CN", "zh_TW"])
def test_menu_is_translated(application: "QApplication", tmp_path: Path, language: str) -> None:
    english = Harness(tmp_path / "en").texts()
    other = Harness(tmp_path / language, language).texts()
    assert len(other) == len(english)
    assert all(a != b for a, b in zip(other, english, strict=True))


def test_each_icon_state_looks_different(application: "QApplication") -> None:
    pictures = {state: make_icon(state).pixmap(64, 64).toImage() for state in IconState}
    assert not any(image.isNull() for image in pictures.values())
    states = list(IconState)
    for i, first in enumerate(states):
        for second in states[i + 1 :]:
            assert pictures[first] != pictures[second], (first, second)
