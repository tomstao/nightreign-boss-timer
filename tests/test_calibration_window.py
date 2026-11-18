import os
import sys
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the UI is Windows-only")

# Draw into memory, so the test needs no desktop and shows nothing on screen.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

if sys.platform == "win32":
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from nightreign_boss_timer.calibration import RegionKind, Selection, to_fractions
    from nightreign_boss_timer.i18n import Translator
    from nightreign_boss_timer.regions import Box, bar_region
    from nightreign_boss_timer.settings import Settings
    from nightreign_boss_timer.ui.calibration_window import CalibrationWindow

FIXTURES = Path(__file__).parent / "fixtures"
W, H = 1920, 1080
BAR = Selection(left=462, top=857, right=1452, bottom=864)


def game_picture(bar: str = "half", text: str | None = None) -> np.ndarray:
    """A 1080p game image, plain except for a real bar and, if asked, the real defeat text."""
    picture = np.full((H, W, 3), 40, dtype=np.uint8)
    with np.load(FIXTURES / "bar_regions.npz") as data:
        region = data[bar]
    picture[843 : 843 + region.shape[0], 462 : 462 + region.shape[1]] = region
    if text:
        with np.load(FIXTURES / "defeat_regions.npz") as data:
            region = data[text].repeat(2, axis=0).repeat(2, axis=1)
        picture[491 : 491 + region.shape[0], 461 : 461 + region.shape[1]] = region
    return picture


class Harness:
    """A calibration window fed with made-up screenshots, counting saves."""

    def __init__(self, picture: np.ndarray | None, language: str = "en") -> None:
        self.picture = picture
        self.settings = Settings()
        self.saves = 0
        self.window = CalibrationWindow(
            self.settings, Translator(language), lambda: self.picture, self._saved
        )
        self.window.load_picture()

    def _saved(self) -> None:
        self.saves += 1


@pytest.fixture(scope="module")
def application() -> "QApplication":
    return QApplication.instance() or QApplication([])


def test_opens_on_the_bar_step_with_the_usual_position_checked(application: "QApplication") -> None:
    window = Harness(game_picture("half")).window
    assert window.isVisible()
    assert window.kind is RegionKind.BAR
    assert window.heading.text() == "Step 1 of 2 - Boss health bar"
    assert window.readout.text() == "Bar found, HP 56%"
    assert window.save_button.text() == "Save and next"
    assert window.skip_button.isVisible()


def test_a_full_bar_is_reported_as_100(application: "QApplication") -> None:
    assert Harness(game_picture("full")).window.readout.text() == "Bar found, HP 100%"


def test_readout_follows_the_box_as_it_moves(application: "QApplication") -> None:
    window = Harness(game_picture("half")).window
    for _ in range(12):
        QTest.keyClick(window.canvas, Qt.Key.Key_Down)
    assert window.readout.text() == "No bar found in this box"
    for _ in range(12):
        QTest.keyClick(window.canvas, Qt.Key.Key_Up)
    assert window.readout.text() == "Bar found, HP 56%"


def test_saving_the_bar_writes_settings_and_moves_to_the_defeat_text(
    application: "QApplication",
) -> None:
    harness = Harness(game_picture("half"))
    window = harness.window
    window.canvas.set_selection(BAR)
    window.save()

    assert harness.saves == 1
    assert harness.settings.bar_region == to_fractions(BAR, RegionKind.BAR, W, H)
    assert bar_region(Box(0, 0, W, H), harness.settings.bar_region) == Box(462, 843, 990, 35)
    assert harness.settings.calibrated_size == (W, H)
    assert harness.settings.defeat_text_region is None
    assert window.kind is RegionKind.DEFEAT_TEXT
    assert window.heading.text() == "Step 2 of 2 - Defeat text"
    assert window.readout.text() == "No defeat text in this box"
    assert window.save_button.text() == "Save"
    assert not window.skip_button.isVisible()


def test_saving_the_defeat_text_finishes(application: "QApplication") -> None:
    harness = Harness(game_picture("defeat_text", text="text_full"))
    window = harness.window
    window.save()
    assert window.readout.text() == "Defeat text found"
    window.save()

    assert harness.saves == 2
    assert harness.settings.defeat_text_region is not None
    assert not window.isVisible()


def test_skip_leaves_the_bar_as_it_was(application: "QApplication") -> None:
    harness = Harness(game_picture("half"))
    QTest.mouseClick(harness.window.skip_button, Qt.MouseButton.LeftButton)
    assert harness.window.kind is RegionKind.DEFEAT_TEXT
    assert harness.settings.bar_region is None
    assert harness.saves == 0


def test_escape_closes_and_saves_nothing(application: "QApplication") -> None:
    harness = Harness(game_picture("half"))
    QTest.keyClick(harness.window, Qt.Key.Key_Escape)
    assert not harness.window.isVisible()
    assert harness.saves == 0
    assert harness.settings.bar_region is None


def test_a_saved_region_is_shown_again_next_time(application: "QApplication") -> None:
    harness = Harness(game_picture("half"))
    moved = Selection(400, 600, 1500, 620)
    harness.window.canvas.set_selection(moved)
    harness.window.save()
    harness.window.close()

    harness.window.start()
    assert not harness.window.isVisible()  # out of the way while the screenshot is taken
    harness.window.load_picture()  # what the timer does a moment later
    assert harness.window.kind is RegionKind.BAR
    assert harness.window.canvas.selection == moved


def test_retake_keeps_the_box_being_worked_on(application: "QApplication") -> None:
    harness = Harness(game_picture("no_bar_dark"))
    window = harness.window
    assert window.readout.text() == "No bar found in this box"
    QTest.keyClick(window.canvas, Qt.Key.Key_Left)
    box = window.canvas.selection
    harness.picture = game_picture("half")
    window.load_picture()
    assert window.canvas.selection == box
    assert window.readout.text().startswith("Bar found")


def test_without_the_game_nothing_can_be_saved(application: "QApplication") -> None:
    harness = Harness(None)
    window = harness.window
    assert window.readout.text().startswith("Game window not found")
    assert not window.save_button.isEnabled()
    window.save()
    assert harness.saves == 0

    harness.picture = game_picture("half")
    window.load_picture()
    assert window.save_button.isEnabled()
    assert window.readout.text() == "Bar found, HP 56%"


@pytest.mark.parametrize("language", ["zh_CN", "zh_TW"])
def test_window_is_translated(application: "QApplication", language: str) -> None:
    window = Harness(game_picture("half"), language).window
    english = Harness(game_picture("half")).window
    for chinese, original in (
        (window.heading, english.heading),
        (window.hint, english.hint),
        (window.readout, english.readout),
        (window.save_button, english.save_button),
        (window.retake_button, english.retake_button),
    ):
        assert chinese.text() != original.text()
    assert window.windowTitle() != english.windowTitle()
