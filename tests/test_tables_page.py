import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the UI is Windows-only")

if sys.platform == "win32":
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from nightreign_boss_timer import settings as settings_file
    from nightreign_boss_timer.ui.main_window import MainWindow
    from nightreign_boss_timer.ui.tables_page import ACTIVE_MARK, TablesPage
    from test_record_view import RECORDS
    from ui_support import Recorder

LEFT = Qt.MouseButton.LeftButton if sys.platform == "win32" else None


@pytest.fixture(scope="module")
def application() -> "QApplication":
    return QApplication.instance() or QApplication([])


def make(folder: Path, language: str = "en") -> tuple["Recorder", "TablesPage"]:
    recorder = Recorder(folder, language)
    for record in RECORDS:
        recorder.store.append(record)
    # The page is used inside the window, which redraws it after every change.
    window = MainWindow(recorder.controller, [TablesPage(recorder.controller)])
    page = window.pages[0]
    page.window_kept = window  # keep the window alive as long as the page
    return recorder, page


def rows(page: "TablesPage") -> list[list[str]]:
    return [
        [page.table.item(row, column).text() for column in range(page.table.columnCount())]
        for row in range(page.table.rowCount())
    ]


def test_lists_tables_with_counts_and_hotkeys(application: "QApplication", tmp_path: Path) -> None:
    _, page = make(tmp_path)
    assert rows(page) == [
        [ACTIVE_MARK, "Arena", "4", "Ctrl+Alt+1"],
        ["", "Normal", "1", "Ctrl+Alt+2"],
    ]
    assert not page.rename_button.isEnabled()  # nothing selected yet
    assert not page.delete_button.isEnabled()


def test_adding_a_table(application: "QApplication", tmp_path: Path) -> None:
    recorder, page = make(tmp_path)
    QTest.keyClicks(page.name, "No-hit practice")
    QTest.mouseClick(page.add_button, LEFT)

    # Records saved earlier under that name are counted straight away.
    assert rows(page)[-1] == ["", "No-hit practice", "1", "(none)"]
    assert page.name.text() == ""
    assert page.message.text() == ""
    assert page.selected() == "No-hit practice"
    assert settings_file.load(recorder.settings_path).table_names()[-1] == "No-hit practice"


def test_enter_in_the_name_field_adds(application: "QApplication", tmp_path: Path) -> None:
    recorder, page = make(tmp_path)
    QTest.keyClicks(page.name, "Co-op")
    QTest.keyClick(page.name, Qt.Key.Key_Return)
    assert recorder.settings.table_names() == ["Arena", "Normal", "Co-op"]


def test_refused_names_say_why_and_keep_the_text(
    application: "QApplication", tmp_path: Path
) -> None:
    recorder, page = make(tmp_path)
    QTest.mouseClick(page.add_button, LEFT)
    assert page.message.text() == "A table needs a name."
    QTest.keyClicks(page.name, "arena")
    QTest.mouseClick(page.add_button, LEFT)
    assert page.message.text() == 'A table named "arena" already exists.'
    assert page.name.text() == "arena"
    assert recorder.settings.table_names() == ["Arena", "Normal"]
    assert not recorder.settings_path.exists()


def test_renaming_the_active_table_keeps_it_active(
    application: "QApplication", tmp_path: Path
) -> None:
    recorder, page = make(tmp_path)
    page.table.selectRow(0)
    QTest.keyClicks(page.name, "Boss Arena")
    QTest.mouseClick(page.rename_button, LEFT)
    assert recorder.settings.active_table == "Boss Arena"
    # Records keep the name they were saved with, so the renamed table starts at none.
    assert rows(page)[0] == [ACTIVE_MARK, "Boss Arena", "0", "Ctrl+Alt+1"]
    assert recorder.notices == ["Table: Boss Arena"]


def test_built_in_tables_cannot_be_deleted_but_others_can(
    application: "QApplication", tmp_path: Path
) -> None:
    recorder, page = make(tmp_path)
    recorder.controller.add_table("Co-op")
    page.table.selectRow(0)
    assert not page.delete_button.isEnabled()
    page.table.selectRow(2)
    assert page.delete_button.isEnabled()
    QTest.mouseClick(page.delete_button, LEFT)
    assert recorder.settings.table_names() == ["Arena", "Normal"]
    assert page.message.text() == ""


def test_deleting_the_active_table_falls_back_to_the_first(
    application: "QApplication", tmp_path: Path
) -> None:
    recorder, page = make(tmp_path)
    recorder.controller.add_table("Co-op")
    recorder.controller.set_table("Co-op")
    page.table.selectRow(2)
    page.delete()
    assert recorder.settings.active_table == "Arena"
    assert recorder.notices[-1] == "Table: Arena"


def test_making_a_table_active(application: "QApplication", tmp_path: Path) -> None:
    recorder, page = make(tmp_path)
    page.table.selectRow(1)
    assert page.active_button.isEnabled()
    QTest.mouseClick(page.active_button, LEFT)
    assert recorder.settings.active_table == "Normal"
    assert [row[0] for row in rows(page)] == ["", ACTIVE_MARK]
    assert not page.active_button.isEnabled()  # it is the active one now
    assert page.selected() == "Normal"


@pytest.mark.parametrize("language", ["zh_CN", "zh_TW"])
def test_page_is_translated(application: "QApplication", tmp_path: Path, language: str) -> None:
    _, english = make(tmp_path / "en")
    recorder, other = make(tmp_path / language, language)
    for name in ("add_button", "rename_button", "delete_button", "active_button", "note"):
        assert getattr(other, name).text() != getattr(english, name).text()
    assert other.table.horizontalHeaderItem(1).text() != "Name"
    other.add()
    assert other.message.text() not in ("", "A table needs a name.")
    assert recorder.controller.delete_table("Arena") not in ("", "tables.error.builtin")
    assert recorder.controller.rename_table("Nowhere", "x") not in ("", "tables.error.missing")
