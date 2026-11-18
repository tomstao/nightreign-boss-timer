import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the UI is Windows-only")

# Draw into memory, so the test needs no desktop and shows nothing on screen.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

if sys.platform == "win32":
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout

    from nightreign_boss_timer import __version__
    from nightreign_boss_timer.engine import State
    from nightreign_boss_timer.regions import Fractions
    from nightreign_boss_timer.ui.main_window import MainWindow, default_pages
    from nightreign_boss_timer.ui.pages import AboutPage, Page
    from ui_support import Recorder

    class CountingPage(Page):
        """A stand-in page that shows how often it was asked to redraw."""

        def __init__(self, controller: object, key: str) -> None:
            super().__init__(controller)
            self.key = key
            self.refreshes = 0
            QVBoxLayout(self).addWidget(QLabel(key))

        def refresh(self) -> None:
            self.refreshes += 1


LEFT = Qt.MouseButton.LeftButton if sys.platform == "win32" else None


@pytest.fixture(scope="module")
def application() -> "QApplication":
    return QApplication.instance() or QApplication([])


def make(folder: Path, language: str = "en") -> tuple["Recorder", "MainWindow"]:
    recorder = Recorder(folder, language)
    controller = recorder.controller
    pages = [CountingPage(controller, key) for key in ("records", "tables", "regions")]
    return recorder, MainWindow(controller, [*pages, AboutPage(controller)])


def test_sidebar_lists_the_pages_by_their_translated_names(
    application: "QApplication", tmp_path: Path
) -> None:
    _, window = make(tmp_path)
    names = [window.sidebar.item(row).text() for row in range(window.sidebar.count())]
    assert names == ["Records", "Tables", "Regions", "About"]
    assert window.windowTitle() == "Nightreign Boss Timer"
    assert window.stack.currentWidget() is window.pages[0]


def test_choosing_a_page_shows_and_redraws_it(application: "QApplication", tmp_path: Path) -> None:
    _, window = make(tmp_path)
    before = window.pages[1].refreshes
    window.sidebar.setCurrentRow(1)
    assert window.stack.currentWidget() is window.pages[1]
    assert window.pages[1].refreshes == before + 1


def test_show_page_opens_the_window_on_that_page(
    application: "QApplication", tmp_path: Path
) -> None:
    _, window = make(tmp_path)
    assert not window.isVisible()
    window.show_page("regions")
    assert window.isVisible()
    assert window.stack.currentWidget().key == "regions"
    window.show_page()  # no page named: stays where it is
    assert window.stack.currentWidget().key == "regions"
    window.show_page("no such page")
    assert window.stack.currentWidget().key == "regions"


def test_closing_only_hides_the_window(application: "QApplication", tmp_path: Path) -> None:
    _, window = make(tmp_path)
    window.show_page("tables")
    window.close()
    assert not window.isVisible()
    window.show_page()
    assert window.isVisible()
    assert window.stack.currentWidget().key == "tables"


def test_status_bar_follows_the_controller(application: "QApplication", tmp_path: Path) -> None:
    recorder, window = make(tmp_path)
    controller = recorder.controller
    window.show()
    assert window.tracking_status.text() == "Tracking on"
    assert window.table_status.text() == "Table: Arena"
    assert window.game_status.text() == "Game: found"
    assert window.regions_status.text() == "Regions: not calibrated"

    controller.set_state(State.NO_GAME)
    assert window.game_status.text() == "Game: not found"
    controller.set_table("Normal")
    assert window.table_status.text() == "Table: Normal"
    recorder.settings.bar_region = Fractions(0.24, 0.76, 0.79, 0.8)
    controller.changed.emit()
    assert window.regions_status.text() == "Regions: calibrated"

    controller.set_tracking(False)
    controller.set_state(State.PAUSED)
    assert window.tracking_status.text() == "Tracking paused"
    assert not window.game_status.isVisible()


def test_status_items_are_shortcuts(application: "QApplication", tmp_path: Path) -> None:
    recorder, window = make(tmp_path)
    QTest.mouseClick(window.tracking_status, LEFT)
    assert not recorder.controller.tracking
    QTest.mouseClick(window.table_status, LEFT)
    assert window.stack.currentWidget().key == "tables"
    QTest.mouseClick(window.regions_status, LEFT)
    assert window.stack.currentWidget().key == "regions"


def test_about_page(application: "QApplication", tmp_path: Path) -> None:
    _, window = make(tmp_path)
    window.show_page("about")
    about = window.stack.currentWidget()
    assert about.version.text() == f"Version {__version__}"
    assert "github.com/sunfish-LittleKight/nightreign-boss-timer" in about.link.text()
    assert "screen pixels" in about.safety.text()


@pytest.mark.parametrize("language", ["zh_CN", "zh_TW"])
def test_window_is_translated(application: "QApplication", tmp_path: Path, language: str) -> None:
    _, english = make(tmp_path / "en")
    _, other = make(tmp_path / language, language)
    english.show_page("about")
    other.show_page("about")
    for row in range(english.sidebar.count()):
        assert other.sidebar.item(row).text() != english.sidebar.item(row).text()
    for name in ("tracking_status", "table_status", "game_status", "regions_status"):
        assert getattr(other, name).text() != getattr(english, name).text()
    assert other.pages[-1].safety.text() != english.pages[-1].safety.text()
    assert other.windowTitle() != english.windowTitle()


def test_default_pages_all_have_a_translated_name(
    application: "QApplication", tmp_path: Path
) -> None:
    recorder = Recorder(tmp_path)
    for page in default_pages(recorder.controller):
        assert recorder.controller.translate(f"page.{page.key}") != f"page.{page.key}"
        page.refresh()
