import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the UI is Windows-only")

if sys.platform == "win32":
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from nightreign_boss_timer import settings as settings_file
    from nightreign_boss_timer.hotkeys import bindings
    from nightreign_boss_timer.settings import DEFAULT_HOTKEYS, Settings
    from nightreign_boss_timer.ui.hotkeys_page import HotkeysPage, key_name
    from nightreign_boss_timer.ui.main_window import MainWindow
    from ui_support import Recorder

    CTRL = Qt.KeyboardModifier.ControlModifier
    ALT = Qt.KeyboardModifier.AltModifier
    SHIFT = Qt.KeyboardModifier.ShiftModifier
    NONE = Qt.KeyboardModifier.NoModifier
    LEFT = Qt.MouseButton.LeftButton


@pytest.fixture(scope="module")
def application() -> "QApplication":
    return QApplication.instance() or QApplication([])


class Harness:
    def __init__(self, folder: Path, language: str = "en") -> None:
        self.recorder = Recorder(folder, language)
        self.controller = self.recorder.controller
        self.settings = self.recorder.settings
        self.refused: set[str] = set()  # shortcuts "another program" holds
        self.suspensions: list[bool] = []
        self.controller.hotkey_applier = self._apply
        self.controller.hotkeys_suspended.connect(self.suspensions.append)
        self.page = HotkeysPage(self.controller)
        self.window = MainWindow(self.controller, [self.page])

    def _apply(self, settings: "Settings") -> set[str]:
        return {
            action for action, shortcut in bindings(settings).items() if shortcut in self.refused
        }

    def rows(self) -> list[tuple[str, str]]:
        table = self.page.table
        return [(table.item(r, 0).text(), table.item(r, 1).text()) for r in range(table.rowCount())]

    def select(self, action: str) -> None:
        self.page.table.selectRow(self.controller.hotkey_actions().index(action))

    def saved(self) -> "Settings":
        return settings_file.load(self.recorder.settings_path)


def test_lists_every_action_and_table(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    assert harness.rows() == [
        ("Pause or resume tracking", "Ctrl+Alt+P"),
        ("Next table", "Ctrl+Alt+T"),
        ("Show or hide overlay", "Ctrl+Alt+O"),
        ("Open region calibration", "Ctrl+Alt+C"),
        ("End current fight now", "(none)"),
        ("Discard last record", "(none)"),
        ("Open main window", "(none)"),
        ("Switch to table: Arena", "Ctrl+Alt+1"),
        ("Switch to table: Normal", "Ctrl+Alt+2"),
    ]
    assert not harness.page.set_button.isEnabled()  # nothing selected yet


def test_pressing_keys_in_the_field_and_enter_sets_the_shortcut(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    page = harness.page
    harness.select("end_fight")
    QTest.keyClick(page.capture, Qt.Key.Key_E, CTRL | ALT)
    assert page.capture.text() == "Ctrl+Alt+E"
    QTest.keyClick(page.capture, Qt.Key.Key_F9, SHIFT)  # a second press replaces the first
    assert page.capture.text() == "Shift+F9"
    QTest.keyClick(page.capture, Qt.Key.Key_Return)

    assert harness.settings.hotkeys["end_fight"] == "Shift+F9"
    assert harness.saved().hotkeys["end_fight"] == "Shift+F9"
    assert harness.rows()[4] == ("End current fight now", "Shift+F9")
    assert page.capture.text() == ""
    assert page.message.text() == ""
    assert page.selected() == "end_fight"  # the row stays selected after the redraw


def test_modifiers_alone_and_unusable_keys_show_nothing(
    application: "QApplication", tmp_path: Path
) -> None:
    page = Harness(tmp_path).page
    QTest.keyClick(page.capture, Qt.Key.Key_Control, CTRL)
    QTest.keyClick(page.capture, Qt.Key.Key_Tab)
    assert page.capture.text() == ""
    QTest.keyClick(page.capture, Qt.Key.Key_K, CTRL)
    QTest.keyClick(page.capture, Qt.Key.Key_Escape)
    assert page.capture.text() == ""


def test_a_shortcut_in_use_is_refused_with_the_name_of_its_action(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    page = harness.page
    harness.select("end_fight")
    QTest.keyClick(page.capture, Qt.Key.Key_1, CTRL | ALT)
    QTest.mouseClick(page.set_button, LEFT)
    assert page.message.text() == 'This shortcut is already used by "Switch to table: Arena".'
    assert harness.settings.hotkeys["end_fight"] == ""
    assert page.capture.text() == "Ctrl+Alt+1"  # kept, so it can be corrected
    assert not harness.recorder.settings_path.exists()


def test_table_hotkeys_are_set_the_same_way(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    harness.controller.add_table("Co-op")
    harness.select("table:Co-op")
    QTest.keyClick(harness.page.capture, Qt.Key.Key_3, CTRL | ALT)
    QTest.keyClick(harness.page.capture, Qt.Key.Key_Enter)
    assert harness.saved().tables[2].hotkey == "Ctrl+Alt+3"
    assert harness.rows()[-1] == ("Switch to table: Co-op", "Ctrl+Alt+3")


def test_backspace_and_the_clear_button_remove_a_shortcut(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    harness.select("toggle_tracking")
    QTest.keyClick(harness.page.capture, Qt.Key.Key_Backspace)
    assert harness.settings.hotkeys["toggle_tracking"] == ""
    harness.select("next_table")
    QTest.mouseClick(harness.page.clear_button, LEFT)
    assert harness.settings.hotkeys["next_table"] == ""
    assert harness.rows()[0][1] == harness.rows()[1][1] == "(none)"
    # A freed shortcut can now go to another action.
    harness.select("end_fight")
    assert harness.controller.set_hotkey("end_fight", "Ctrl+Alt+P") == ""


def test_a_single_key_is_accepted_with_a_warning(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    harness.select("discard_last")
    QTest.keyClick(harness.page.capture, Qt.Key.Key_F8, NONE)
    QTest.keyClick(harness.page.capture, Qt.Key.Key_Return)
    assert harness.settings.hotkeys["discard_last"] == "F8"
    assert harness.page.message.text().startswith("Set. A single key")
    assert harness.page.capture.text() == ""


def test_a_shortcut_windows_refuses_is_marked(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    harness.refused.add("Ctrl+Alt+E")
    harness.select("end_fight")
    QTest.keyClick(harness.page.capture, Qt.Key.Key_E, CTRL | ALT)
    QTest.keyClick(harness.page.capture, Qt.Key.Key_Return)
    assert harness.page.message.text().startswith("Windows could not register this shortcut")
    assert harness.rows()[4] == ("End current fight now", "Ctrl+Alt+E (not working)")
    assert harness.settings.hotkeys["end_fight"] == "Ctrl+Alt+E"  # kept: it may work next time

    harness.refused.clear()
    harness.controller.refresh_hotkeys()
    harness.page.refresh()
    assert harness.rows()[4][1] == "Ctrl+Alt+E"


def test_restore_defaults(application: "QApplication", tmp_path: Path) -> None:
    harness = Harness(tmp_path)
    harness.controller.add_table("Co-op")
    harness.controller.set_hotkey("table:Co-op", "Ctrl+Alt+3")
    harness.controller.set_hotkey("toggle_tracking", "F7")
    harness.controller.set_hotkey("table:Normal", "")
    QTest.mouseClick(harness.page.defaults_button, LEFT)
    assert harness.settings.hotkeys == DEFAULT_HOTKEYS
    assert [t.hotkey for t in harness.settings.tables] == ["Ctrl+Alt+1", "Ctrl+Alt+2", ""]
    assert harness.saved().hotkeys == DEFAULT_HOTKEYS
    assert harness.rows()[0][1] == "Ctrl+Alt+P"


def test_hotkeys_are_switched_off_while_the_field_has_the_keyboard(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    harness.window.show()
    harness.window.activateWindow()
    harness.page.capture.setFocus()
    application.processEvents()
    harness.page.table.setFocus()
    application.processEvents()
    assert harness.suspensions == [True, False]
    harness.window.hide()


def test_unknown_actions_and_bad_text_are_refused(
    application: "QApplication", tmp_path: Path
) -> None:
    harness = Harness(tmp_path)
    assert harness.controller.set_hotkey("make_coffee", "Ctrl+Alt+M") != ""
    assert harness.controller.set_hotkey("end_fight", "Ctrl+Banana").startswith("That is not")
    assert harness.settings.hotkeys["end_fight"] == ""


def test_key_names(application: "QApplication") -> None:
    assert key_name(Qt.Key.Key_P, CTRL) == "P"
    assert key_name(Qt.Key.Key_F12, NONE) == "F12"
    assert key_name(Qt.Key.Key_5, Qt.KeyboardModifier.KeypadModifier) == "Num5"
    assert key_name(Qt.Key.Key_PageDown, NONE) == "PageDown"
    assert key_name(Qt.Key.Key_BracketLeft, NONE) == "["
    # With Shift held Qt reports "!", and Windows' own code says which key it was.
    assert key_name(Qt.Key.Key_Exclam, SHIFT, native_code=0x31) == "1"
    assert key_name(Qt.Key.Key_Exclam, SHIFT) == ""
    assert key_name(Qt.Key.Key_Shift, SHIFT) == ""
    assert key_name(Qt.Key.Key_Escape, NONE) == ""


@pytest.mark.parametrize("language", ["zh_CN", "zh_TW"])
def test_page_is_translated(application: "QApplication", tmp_path: Path, language: str) -> None:
    english = Harness(tmp_path / "en")
    other = Harness(tmp_path / language, language)
    assert all(a[0] != b[0] for a, b in zip(other.rows(), english.rows(), strict=True))
    assert other.rows()[4][1] != "(none)"
    for name in ("set_button", "clear_button", "defaults_button", "help"):
        assert getattr(other.page, name).text() != getattr(english.page, name).text()
    assert other.page.capture.placeholderText() != english.page.capture.placeholderText()
    assert other.controller.set_hotkey("end_fight", "F8") not in ("", "hotkey.single_key")
    assert other.controller.set_hotkey("discard_last", "F8") not in ("", "hotkey.conflict")
