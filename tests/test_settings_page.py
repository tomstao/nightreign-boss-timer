import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the UI is Windows-only")

if sys.platform == "win32":
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from nightreign_boss_timer import settings as settings_file
    from nightreign_boss_timer.i18n import Translator
    from nightreign_boss_timer.settings import Settings
    from nightreign_boss_timer.ui.calibration_window import CalibrationWindow
    from nightreign_boss_timer.ui.main_window import MainWindow
    from nightreign_boss_timer.ui.settings_page import SettingsPage
    from nightreign_boss_timer.ui.tray import Tray
    from test_record_view import fight
    from ui_support import Recorder

LEFT = Qt.MouseButton.LeftButton if sys.platform == "win32" else None


@pytest.fixture(scope="module")
def application() -> "QApplication":
    return QApplication.instance() or QApplication([])


class Harness:
    def __init__(self, folder: Path, language: str = "en") -> None:
        self.recorder = Recorder(folder, language)
        self.controller = self.recorder.controller
        self.chosen = ""  # what the folder dialog will answer
        self.asked: list[str] = []
        self.page = SettingsPage(self.controller, self._choose)
        self.window = MainWindow(self.controller, [self.page])

    def _choose(self, parent: object, start: str) -> str:
        self.asked.append(start)
        return self.chosen

    def saved(self) -> "Settings":
        return settings_file.load(self.recorder.settings_path)


def test_shows_the_current_settings(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    page = harness.page
    assert page.language.currentData() == "en"
    assert [page.language.itemText(i) for i in range(3)] == ["English", "简体中文", "繁體中文"]
    assert page.wait_window.value() == 8
    assert page.skip_walk_pasts.isChecked()
    assert page.fight_rate.value() == 10
    assert page.folder.text() == str(tmp_path / "records")
    assert not page.default_folder.isEnabled()
    # Showing the values must not count as changing them.
    assert not harness.recorder.settings_path.exists()
    assert harness.recorder.changes == 0


def test_changing_the_language_redraws_everything_at_once(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    tray = Tray(harness.controller, lambda: None)
    page, window = harness.page, harness.window
    page.language.setCurrentIndex(page.language.findData("zh_TW"))
    page.language.activated.emit(page.language.currentIndex())
    application.processEvents()

    assert harness.saved().ui_language == "zh_TW"
    assert page.general.title() == "一般"
    assert page.language_label.text() == "語言"
    assert window.sidebar.item(0).text() == "設定"
    assert window.windowTitle() == "黑夜君臨 Boss 計時器"
    assert tray.menu.actions()[-1].text() == "結束"
    # The names of the languages themselves stay as they are.
    assert page.language.currentText() == "繁體中文"
    assert page.language.itemText(0) == "English"


def test_calibration_window_follows_the_language(
    application: "QApplication", tmp_path: Path
) -> None:
    translate = Translator("en")
    window = CalibrationWindow(Settings(), translate, lambda: None, lambda: None)
    window.load_picture()
    assert window.retake_button.text() == "Retake screenshot"
    window.close()
    translate.language = "zh_CN"
    window.load_picture()
    assert window.retake_button.text() == "重新截图"
    assert window.windowTitle() == "标定区域"
    window.close()


def test_timing_options_are_saved_as_they_change(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    page = harness.page
    page.wait_window.setValue(15)
    page.fight_rate.setValue(5)
    QTest.mouseClick(page.skip_walk_pasts, LEFT)

    saved = harness.saved()
    assert saved.wait_window_s == 15.0
    assert saved.fight_rate == 5.0
    assert saved.skip_walk_pasts is False
    assert page.wait_window.value() == 15  # the redraw after a change keeps what was typed


def test_showing_the_overlay_in_recordings_is_off_until_chosen(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    page = harness.page
    assert not page.overlay_in_captures.isChecked()
    assert page.captures_note.text()

    QTest.mouseClick(page.overlay_in_captures, LEFT)

    assert harness.saved().overlay_in_captures is True
    assert page.overlay_in_captures.isChecked()


def test_boss_name_languages_can_be_ticked_but_never_all_unticked(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    page = harness.page
    boxes = page.name_languages
    assert [box.text() for box in boxes.values()] == ["English", "简体中文", "繁體中文"]
    # It starts with the language of the program alone, which cannot be unticked.
    assert [box.isChecked() for box in boxes.values()] == [True, False, False]
    assert not boxes["en"].isEnabled()

    boxes["zh_CN"].click()

    assert harness.saved().name_languages == ["en", "zh_CN"]
    assert boxes["en"].isEnabled()
    boxes["en"].click()
    assert harness.saved().name_languages == ["zh_CN"]
    assert [box.isChecked() for box in boxes.values()] == [False, True, False]
    assert not boxes["zh_CN"].isEnabled()
    assert "3" in page.names_note.text()


def test_out_of_range_values_cannot_be_entered(application: "QApplication", tmp_path: Path) -> None:
    page = Harness(tmp_path).page
    page.wait_window.setValue(500)
    page.fight_rate.setValue(0)
    assert page.wait_window.value() == 120
    assert page.fight_rate.value() == 1


def test_choosing_a_folder_moves_where_records_are_saved(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    page, store = harness.page, harness.recorder.store
    store.append(fight(1))
    target = tmp_path / "elsewhere"
    harness.chosen = str(target)
    QTest.mouseClick(page.browse, LEFT)

    assert harness.asked == [str(tmp_path / "records")]  # the dialog starts where records are
    assert harness.saved().records_folder == str(target)
    assert store.path == target / "records.csv"
    assert store.pending_path == target / "records.pending.csv"
    assert page.folder.text() == str(target)
    assert page.default_folder.isEnabled()
    store.append(fight(2))
    assert len(store.read_all()) == 1  # the new file holds only what came after the move
    assert (tmp_path / "records" / "records.csv").exists()  # the old one is left alone


def test_cancelling_the_folder_dialog_changes_nothing(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    QTest.mouseClick(harness.page.browse, LEFT)
    assert harness.recorder.settings.records_folder == ""
    assert harness.recorder.changes == 0


def test_open_folder_button(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    QTest.mouseClick(harness.page.open_folder, LEFT)
    assert harness.recorder.opened == [tmp_path / "records"]


def test_unknown_option_or_language_is_refused(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    harness.controller.set_language("klingon")
    assert harness.recorder.settings.ui_language == "en"
    with pytest.raises(ValueError, match="not an option"):
        harness.controller.set_option("ui_language", 1.0)


def test_overlay_position_is_saved_and_can_be_reset(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    assert not harness.page.reset_position.isEnabled()
    harness.controller.set_overlay_position((-300, 120))
    assert harness.saved().overlay_position == (-300, 120)
    assert harness.page.reset_position.isEnabled()
    QTest.mouseClick(harness.page.reset_position, LEFT)
    assert harness.saved().overlay_position is None


def test_main_window_says_when_it_is_shown_and_hidden(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    seen: list[bool] = []
    harness.controller.window_shown.connect(seen.append)
    harness.window.show_page()
    harness.window.close()
    assert seen == [True, False]


def choose_character(page: "SettingsPage", key: str) -> None:
    page.character.setCurrentIndex(page.character.findData(key))
    page.character.activated.emit(page.character.currentIndex())


def test_default_character_is_chosen_from_a_list(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    page = harness.page
    names = [page.character.itemText(i) for i in range(page.character.count())]
    assert names[0] == "Not set"
    assert names[1:] == [
        "Wylder",
        "Guardian",
        "Ironeye",
        "Duchess",
        "Raider",
        "Revenant",
        "Recluse",
        "Executor",
        "Scholar",
        "Undertaker",
    ]
    assert page.character.currentData() == ""
    assert not harness.recorder.settings_path.exists()  # showing it changed nothing

    choose_character(page, "Duchess")

    assert harness.saved().default_character == "Duchess"
    assert page.character.currentText() == "Duchess"
    choose_character(page, "")
    assert harness.saved().default_character == ""
    assert page.character.currentText() == "Not set"


def test_default_character_is_listed_in_the_language_of_the_program(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path, "zh_TW")
    page = harness.page
    choose_character(page, "Wylder")
    assert page.character_label.text() == "角色："
    assert page.character.itemText(0) == "未設定"
    assert page.character.currentText() == "追蹤者"

    harness.controller.set_language("zh_CN")
    application.processEvents()

    assert page.character.currentText() == "追踪者"  # the choice holds, its name follows
    assert harness.saved().default_character == "Wylder"


def test_a_character_the_game_does_not_have_is_refused(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    harness.controller.set_default_character("Priestess")
    assert harness.recorder.settings.default_character == ""
    assert harness.recorder.changes == 0
