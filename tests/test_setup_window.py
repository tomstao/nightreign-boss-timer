import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the UI is Windows-only")

if sys.platform == "win32":
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from nightreign_boss_timer import settings as settings_file
    from nightreign_boss_timer.engine import Engine
    from nightreign_boss_timer.regions import Fractions
    from nightreign_boss_timer.settings import Settings
    from nightreign_boss_timer.ui.settings_page import SettingsPage
    from nightreign_boss_timer.ui.setup_window import SetupWindow
    from test_engine import FakeScreen
    from ui_support import Recorder

LEFT = Qt.MouseButton.LeftButton if sys.platform == "win32" else None


@pytest.fixture(scope="module")
def application() -> "QApplication":
    return QApplication.instance() or QApplication([])


class Harness:
    def __init__(self, folder: Path, language: str = "en") -> None:
        self.recorder = Recorder(folder, language)
        self.controller = self.recorder.controller
        self.screen = FakeScreen()
        engine = Engine(self.recorder.settings, self.screen, self.recorder.store)
        self.controller.probe = engine.probe
        self.calibrations: list[str] = []
        self.controller.calibration_requested.connect(self.calibrations.append)
        self.chosen = ""
        self.window = SetupWindow(self.controller, lambda parent, start: self.chosen)
        self.window.start()

    def saved(self) -> "Settings":
        return settings_file.load(self.recorder.settings_path)

    def next(self) -> None:
        QTest.mouseClick(self.window.next_button, LEFT)


def test_opens_on_the_welcome_step(application: "QApplication", tmp_path: Path) -> None:
    window = Harness(tmp_path).window
    assert window.isVisible()
    assert window.heading.text() == "Step 1 of 3 - Welcome"
    assert "boss health bar" in window.welcome.text()
    assert "screen pixels" in window.safety.text()
    assert not window.back_button.isEnabled()
    assert window.next_button.text() == "Next"


def test_language_chosen_on_the_first_step_applies_at_once(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    window = harness.window
    window.language.setCurrentIndex(window.language.findData("zh_CN"))
    window.language.activated.emit(window.language.currentIndex())
    assert harness.saved().ui_language == "zh_CN"
    assert window.heading.text() == "第 1 步，共 3 步 - 欢迎"
    assert window.next_button.text() == "下一步"
    assert window.language.currentData() == "zh_CN"


def test_second_step_checks_for_the_game(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    window = harness.window
    harness.screen.window = None
    harness.next()
    assert window.heading.text() == "Step 2 of 3 - Game and regions"
    assert window.game_status.text() == "Game: not found"
    assert window.bar_status.text() == ""

    harness.screen.window = FakeScreen().window  # the game was started
    harness.screen.hp = 0.75
    QTest.mouseClick(window.check_button, LEFT)
    assert window.game_status.text() == "Game: found"
    assert window.bar_status.text() == "Bar found, HP 75%"


def test_second_step_offers_calibration_and_shows_when_it_is_done(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    window = harness.window
    harness.next()
    assert window.regions_text.text().startswith("The tool needs to know")
    QTest.mouseClick(window.calibrate_button, LEFT)
    assert harness.calibrations == [""]

    harness.recorder.settings.bar_region = Fractions(0.2406, 0.7559, 0.7931, 0.7993)
    harness.controller.changed.emit()  # what the calibration window causes when it saves
    assert window.regions_text.text().startswith("The regions are calibrated")
    assert window.stack.currentIndex() == 1  # a change elsewhere does not move the guide


def test_third_step_sets_table_and_folder_and_lists_hotkeys(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    window = harness.window
    harness.next()
    harness.next()
    assert window.heading.text() == "Step 3 of 3 - Basics"
    assert window.next_button.text() == "Finish"
    assert [window.table.itemText(i) for i in range(window.table.count())] == ["Arena", "Normal"]
    assert "Ctrl+Alt+P    Pause or resume tracking" in window.hotkeys.text()
    assert "End current fight now" not in window.hotkeys.text()  # it has no shortcut

    window.table.setCurrentIndex(1)
    window.table.activated.emit(1)
    assert harness.saved().active_table == "Normal"
    assert window.table.currentText() == "Normal"

    harness.chosen = str(tmp_path / "my records")
    QTest.mouseClick(window.browse, LEFT)
    assert harness.saved().records_folder == str(tmp_path / "my records")
    assert window.folder.text() == str(tmp_path / "my records")

    QTest.mouseClick(window.hotkeys_button, LEFT)
    assert harness.recorder.windows == ["hotkeys"]


def test_back_and_next_move_between_steps(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    window = harness.window
    harness.next()
    harness.next()
    QTest.mouseClick(window.back_button, LEFT)
    assert window.stack.currentIndex() == 1
    QTest.mouseClick(window.back_button, LEFT)
    QTest.mouseClick(window.back_button, LEFT)  # already at the start
    assert window.stack.currentIndex() == 0


def test_finish_closes_and_is_remembered(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    assert harness.recorder.settings.setup_done is False
    for _ in range(3):
        harness.next()
    assert not harness.window.isVisible()
    assert harness.saved().setup_done is True


def test_skip_at_any_step_is_also_remembered(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    harness.next()
    QTest.mouseClick(harness.window.skip_button, LEFT)
    assert not harness.window.isVisible()
    assert harness.saved().setup_done is True
    # Skipping changes nothing else.
    assert harness.saved().bar_region is None
    assert harness.saved().active_table == "Arena"


def test_setup_can_be_opened_again_from_settings(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    harness.window.finish()
    harness.controller.setup_requested.connect(harness.window.start)
    page = SettingsPage(harness.controller)
    page.refresh()
    assert page.setup_button.text() == "Show the setup guide again"
    QTest.mouseClick(page.setup_button, LEFT)
    assert harness.window.isVisible()
    assert harness.window.stack.currentIndex() == 0


def test_setup_done_survives_the_settings_file(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    assert settings_file.load(path).setup_done is False  # a new user
    settings = Settings(setup_done=True)
    settings_file.save(settings, path)
    assert settings_file.load(path).setup_done is True
    assert Settings.from_json({"setup_done": "yes"}).setup_done is False  # only a real true counts


@pytest.mark.parametrize("language", ["zh_CN", "zh_TW"])
def test_every_step_is_translated(
    application: "QApplication", tmp_path: Path, language: str
) -> None:
    english = Harness(tmp_path / "en")
    other = Harness(tmp_path / language, language)
    names = (
        "heading",
        "welcome",
        "safety",
        "game_help",
        "game_status",
        "check_button",
        "regions_text",
        "calibrate_button",
        "table_label",
        "browse",
        "hotkeys",
        "hotkeys_button",
        "later",
        "skip_button",
        "back_button",
        "next_button",
    )
    headings = []
    for step in range(3):  # visiting the second step fills in the game status
        english.window.go_to(step)
        other.window.go_to(step)
        headings.append((other.window.heading.text(), english.window.heading.text()))
    assert all(theirs != ours for theirs, ours in headings)
    for name in names:
        assert getattr(other.window, name).text() != getattr(english.window, name).text(), name
    assert other.window.windowTitle() != english.window.windowTitle()
