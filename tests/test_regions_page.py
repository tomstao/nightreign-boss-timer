import sys
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the UI is Windows-only")

if sys.platform == "win32":
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from nightreign_boss_timer.engine import Engine
    from nightreign_boss_timer.regions import Fractions
    from nightreign_boss_timer.settings import Settings
    from nightreign_boss_timer.ui.calibration_window import CalibrationWindow
    from nightreign_boss_timer.ui.regions_page import RegionsPage
    from test_engine import FakeReader, FakeScreen
    from ui_support import Recorder

LEFT = Qt.MouseButton.LeftButton if sys.platform == "win32" else None


@pytest.fixture(scope="module")
def application() -> "QApplication":
    return QApplication.instance() or QApplication([])


class Harness:
    """A Regions page reading a made-up screen through a real engine."""

    def __init__(self, folder: Path, language: str = "en", reader: bool = True) -> None:
        self.recorder = Recorder(folder, language)
        self.controller = self.recorder.controller
        self.screen = FakeScreen()
        self.engine = Engine(
            self.recorder.settings,
            self.screen,
            self.recorder.store,
            FakeReader() if reader else None,
        )
        self.controller.probe = self.engine.probe
        self.calibrations: list[str] = []
        self.controller.calibration_requested.connect(self.calibrations.append)
        self.page = RegionsPage(self.controller)
        self.page.refresh()


def test_before_calibration_both_rows_offer_it(application: "QApplication", tmp_path: Path) -> None:
    page = Harness(tmp_path).page
    assert page.bar_name.text() == "Boss health bar"
    assert page.bar_status.text() == "Using the usual position for a 16:9 game image"
    assert page.bar_button.text() == "Calibrate"
    assert page.text_button.text() == "Calibrate"
    assert page.size.text() == ""


def test_after_calibration_rows_say_so(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    settings = harness.recorder.settings
    settings.bar_region = Fractions(0.2406, 0.7559, 0.7931, 0.7993)
    settings.calibrated_size = (1920, 1080)
    harness.page.refresh()
    page = harness.page
    assert page.bar_status.text() == "Calibrated"
    assert page.bar_button.text() == "Recalibrate"
    assert page.text_status.text() != "Calibrated"  # only the bar was done
    assert page.size.text() == "Calibrated at 1920 x 1080"
    assert page.warning.text() == ""


def test_buttons_open_calibration_at_their_own_region(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    QTest.mouseClick(harness.page.bar_button, LEFT)
    QTest.mouseClick(harness.page.text_button, LEFT)
    assert harness.calibrations == ["bar", "defeat_text"]


def test_calibration_window_can_start_at_the_defeat_text(
    application: "QApplication", tmp_path: Path
) -> None:
    window = CalibrationWindow(
        Settings(), Recorder(tmp_path).controller.translate, lambda: None, lambda: None
    )
    window.start("defeat_text")
    window.load_picture()
    assert window.heading.text() == "Step 2 of 2 - Defeat text"
    window.start()
    window.load_picture()
    assert window.heading.text() == "Step 1 of 2 - Boss health bar"
    window.close()


def test_preview_shows_what_is_read_now(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    page, screen = harness.page, harness.screen
    page.show()
    assert page.bar_readout.text() == "Bar detected: no"
    assert page.text_readout.text() == "No defeat text in this box"
    assert not page.bar_picture.pixmap().isNull()

    screen.hp = 0.62
    page.update_preview()
    assert page.bar_readout.text() == "Bar detected: yes     HP 62%     Name read: Tree Sentinel"
    screen.hp = 1.0
    page.update_preview()
    assert "HP 100%" in page.bar_readout.text()

    screen.hp = None
    screen.defeat_text = True
    page.update_preview()
    assert page.text_readout.text() == "Defeat text found"
    page.hide()


def test_preview_without_a_name_reader(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path, reader=False)
    harness.screen.hp = 0.5
    harness.page.update_preview()
    assert harness.page.bar_readout.text() == "Bar detected: yes     HP 50%"


def test_preview_says_when_the_game_is_not_found(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    harness.page.show()
    harness.screen.window = None
    harness.page.update_preview()
    assert harness.page.warning.text() == "Game not found"
    assert not harness.page.bar_picture.isVisible()
    harness.page.hide()


def test_a_changed_window_size_is_pointed_out(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    harness.recorder.settings.bar_region = Fractions(0.2406, 0.7559, 0.7931, 0.7993)
    harness.recorder.settings.calibrated_size = (2560, 1440)
    harness.page.update_preview()
    assert harness.page.warning.text().startswith("The game image is now 1920 x 1080.")


def test_the_screen_is_only_read_while_the_page_is_shown(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    assert not harness.page.timer.isActive()
    harness.page.show()
    assert harness.page.timer.isActive()
    harness.page.hide()
    assert not harness.page.timer.isActive()


def test_probe_does_not_disturb_a_fight(tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    harness.screen.hp = 0.8
    probe = harness.engine.probe()
    assert probe is not None
    assert probe.window == (1920, 1080)
    assert probe.bar.present
    assert probe.name == "Tree Sentinel"
    assert isinstance(probe.text_image, np.ndarray)
    assert not harness.engine._tracker.in_fight  # looking is not tracking


@pytest.mark.parametrize("language", ["zh_CN", "zh_TW"])
def test_page_is_translated(application: "QApplication", tmp_path: Path, language: str) -> None:
    english = Harness(tmp_path / "en")
    other = Harness(tmp_path / language, language)
    for harness in (english, other):
        harness.recorder.settings.calibrated_size = (2560, 1440)
        harness.screen.hp = 0.5
        harness.page.refresh()
    for name in (
        "bar_name",
        "bar_status",
        "bar_button",
        "size",
        "preview_title",
        "bar_readout",
        "text_readout",
        "warning",
    ):
        assert getattr(other.page, name).text() != getattr(english.page, name).text(), name
