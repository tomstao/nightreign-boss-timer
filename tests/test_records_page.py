import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the UI is Windows-only")

if sys.platform == "win32":
    from PySide6.QtCore import QItemSelectionModel, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from nightreign_boss_timer.records import Status
    from nightreign_boss_timer.ui.main_window import MainWindow
    from nightreign_boss_timer.ui.records_page import COLUMNS, RecordsPage
    from test_record_view import RECORDS, fight
    from ui_support import Recorder


@pytest.fixture(scope="module")
def application() -> "QApplication":
    return QApplication.instance() or QApplication([])


def make(folder: Path, language: str = "en") -> tuple["Recorder", "RecordsPage"]:
    recorder = Recorder(folder, language)
    for record in RECORDS:
        recorder.store.append(record)
    page = RecordsPage(recorder.controller)
    page.refresh()
    return recorder, page


def at(name: str) -> int:
    """Where a column is in the table."""
    return COLUMNS.index(name)


def column(page: "RecordsPage", name: str) -> list[str]:
    return [page.table.item(row, at(name)).text() for row in range(page.table.rowCount())]


def choose(box: object, value: str) -> None:
    box.setCurrentIndex(box.findData(value))  # type: ignore[attr-defined]


def test_lists_every_record_newest_first(application: "QApplication", tmp_path: Path) -> None:
    _, page = make(tmp_path)
    headers = [page.table.horizontalHeaderItem(i).text() for i in range(page.table.columnCount())]
    assert headers == [
        "Date and time",
        "Table",
        "Boss",
        "Character",
        "Level",
        "Status",
        "Start HP",
        "End HP",
        "Time",
    ]
    assert column(page, "started_at")[0] == "2026-11-17 21:30:00"
    assert column(page, "started_at")[-1] == "2026-11-17 21:01:00"
    assert column(page, "boss")[0] == "unknown"
    assert column(page, "duration")[-1] == "02:41.3"
    assert page.count.text() == "6 records"
    assert page.summary.text() == ""


def test_filter_boxes_offer_what_exists(application: "QApplication", tmp_path: Path) -> None:
    _, page = make(tmp_path)
    tables = [page.table_filter.itemText(i) for i in range(page.table_filter.count())]
    # Tables from the settings first, then the one only the records know.
    assert tables == ["All", "Arena", "Normal", "No-hit practice"]
    bosses = [page.boss_filter.itemText(i) for i in range(page.boss_filter.count())]
    # 黄金河马 is a known boss, so the English UI lists it under its English name.
    assert bosses == ["All", "Golden Hippopotamus", "Tree Sentinel", "unknown"]
    statuses = [page.status_filter.itemText(i) for i in range(page.status_filter.count())]
    assert statuses == ["All", "Complete", "Incomplete"]


def test_choosing_a_boss_filters_and_sums_up(application: "QApplication", tmp_path: Path) -> None:
    _, page = make(tmp_path)
    choose(page.boss_filter, "Tree Sentinel")
    assert page.count.text() == "4 records"
    assert set(column(page, "boss")) == {"Tree Sentinel"}
    assert page.summary.text() == "4 attempts, 3 complete, best 01:50.0, average 02:00.0"

    choose(page.status_filter, "incomplete")
    assert page.count.text() == "1 records"
    assert page.summary.text() == "1 attempts, 0 complete"


def test_search_narrows_as_you_type(application: "QApplication", tmp_path: Path) -> None:
    _, page = make(tmp_path)
    QTest.keyClicks(page.search, "normal")
    assert column(page, "boss") == ["Golden Hippopotamus"]  # saved as 黄金河马, shown in English
    page.search.clear()
    assert page.table.rowCount() == 6


def test_hp_and_time_sort_as_numbers(application: "QApplication", tmp_path: Path) -> None:
    _, page = make(tmp_path)
    page.table.sortByColumn(at("start_hp"), Qt.SortOrder.AscendingOrder)
    assert column(page, "start_hp")[0] == "62%"  # as text, "100%" would come first
    page.table.sortByColumn(at("duration"), Qt.SortOrder.DescendingOrder)
    assert column(page, "duration")[0] == "02:41.3"


def test_incomplete_rows_look_different(application: "QApplication", tmp_path: Path) -> None:
    _, page = make(tmp_path)
    statuses = column(page, "status")
    incomplete = page.table.item(statuses.index("Incomplete"), at("status")).foreground().color()
    complete = page.table.item(statuses.index("Complete"), at("status")).foreground().color()
    assert incomplete != complete


def test_new_fights_appear_while_the_page_is_open(
    application: "QApplication", tmp_path: Path
) -> None:
    recorder, page = make(tmp_path)
    choose(page.table_filter, "Arena")
    page.show()
    recorder.store.append(fight(45, boss="Night Aspect", status=Status.COMPLETE))
    recorder.controller.records_changed.emit()
    assert page.count.text() == "5 records"
    assert page.table_filter.currentData() == "Arena"  # the filter is kept
    assert "Night Aspect" in column(page, "boss")
    page.hide()


def test_buttons_open_the_file_and_the_folder(application: "QApplication", tmp_path: Path) -> None:
    recorder, page = make(tmp_path)
    QTest.mouseClick(page.open_file, Qt.MouseButton.LeftButton)
    QTest.mouseClick(page.open_folder, Qt.MouseButton.LeftButton)
    assert recorder.opened == [recorder.store.path, recorder.store.path.parent]


def test_empty_file_shows_an_empty_page(application: "QApplication", tmp_path: Path) -> None:
    recorder = Recorder(tmp_path)
    page = RecordsPage(recorder.controller)
    page.refresh()
    assert page.table.rowCount() == 0
    assert page.count.text() == "0 records"


@pytest.mark.parametrize("language", ["zh_CN", "zh_TW"])
def test_page_is_translated(application: "QApplication", tmp_path: Path, language: str) -> None:
    _, english = make(tmp_path / "en")
    _, other = make(tmp_path / language, language)
    assert column(other, "status") != column(english, "status")
    assert column(other, "boss")[0] != "unknown"
    # A boss saved under its English name is shown in the language of the UI.
    assert ("大树守卫" if language == "zh_CN" else "大樹守衛") in column(other, "boss")
    assert "Tree Sentinel" not in column(other, "boss")
    assert other.count.text() != english.count.text()
    assert other.open_file.text() != english.open_file.text()
    assert other.search.placeholderText() != english.search.placeholderText()
    assert other.table_filter.itemText(0) != "All"
    choose(english.boss_filter, "Tree Sentinel")
    choose(other.boss_filter, "Tree Sentinel")
    assert other.summary.text() != english.summary.text()


def test_level_column_shows_the_level_or_nothing(
    application: "QApplication", tmp_path: Path
) -> None:
    recorder = Recorder(tmp_path)
    recorder.store.append(fight(minute=1, level=7))
    recorder.store.append(fight(minute=2))
    page = RecordsPage(recorder.controller)
    page.refresh()
    assert column(page, "level") == ["", "7"]  # newest first


def make_asking(folder: Path, answer: bool) -> tuple["Recorder", "RecordsPage", list[str]]:
    recorder = Recorder(folder)
    for record in RECORDS:
        recorder.store.append(record)
    asked: list[str] = []

    def ask(parent: object, title: str, question: str) -> bool:
        asked.append(question)
        return answer

    page = RecordsPage(recorder.controller, ask=ask)
    page.refresh()
    return recorder, page, asked


def test_delete_needs_a_selection(application: "QApplication", tmp_path: Path) -> None:
    recorder, page, asked = make_asking(tmp_path, answer=True)
    assert page.delete_button.text() == "Delete selected"
    assert not page.delete_button.isEnabled()
    page.delete_selected()
    assert asked == []
    assert len(recorder.store.read_all()) == len(RECORDS)


def test_delete_removes_the_selected_rows_after_asking(
    application: "QApplication", tmp_path: Path
) -> None:
    recorder, page, asked = make_asking(tmp_path, answer=True)
    page.table.sortByColumn(
        at("duration"), Qt.SortOrder.AscendingOrder
    )  # the rows are not in file order
    page.table.selectRow(0)
    assert page.delete_button.isEnabled()
    (chosen,) = page.selected_records()
    assert chosen.duration_s == min(record.duration_s for record in RECORDS)

    QTest.mouseClick(page.delete_button, Qt.MouseButton.LeftButton)

    assert asked == ["Delete the selected records (1)? This cannot be undone."]
    left = recorder.store.read_all()
    assert len(left) == len(RECORDS) - 1
    assert chosen not in left
    assert page.table.rowCount() == len(RECORDS) - 1
    assert page.message.text() == ""
    assert not page.delete_button.isEnabled()


def test_answering_no_deletes_nothing(application: "QApplication", tmp_path: Path) -> None:
    recorder, page, asked = make_asking(tmp_path, answer=False)
    page.table.selectAll()
    page.delete_selected()
    assert len(asked) == 1
    assert len(recorder.store.read_all()) == len(RECORDS)


def test_delete_says_so_when_the_file_is_open_elsewhere(
    application: "QApplication", tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorder, page, _ = make_asking(tmp_path, answer=True)

    def locked(records: object) -> int:
        raise PermissionError

    monkeypatch.setattr(recorder.store, "remove", locked)
    page.table.selectRow(0)
    page.delete_selected()
    assert page.message.text() == "Records file is open in another program"
    assert page.table.rowCount() == len(RECORDS)


def character_choices(page: "RecordsPage") -> list[str]:
    return [action.text() for action in page.character_menu.actions()]


def pick_character(page: "RecordsPage", text: str) -> None:
    """Choose an entry of the character menu, as a click on it does."""
    (action,) = [action for action in page.character_menu.actions() if action.text() == text]
    action.trigger()


def test_character_column_shows_it_in_the_language_of_the_program(
    application: "QApplication", tmp_path: Path
) -> None:
    recorder = Recorder(tmp_path)
    recorder.store.append(fight(minute=1))  # from before characters were recorded
    recorder.store.append(fight(minute=2, character="追踪者"))
    recorder.store.append(fight(minute=3, character="My build"))
    page = RecordsPage(recorder.controller)
    window = MainWindow(recorder.controller, [page])
    page.refresh()
    assert column(page, "character") == ["My build", "Wylder", ""]  # newest first

    recorder.controller.set_language("zh_TW")
    application.processEvents()

    assert window.pages[0] is page
    assert column(page, "character") == ["My build", "追蹤者", ""]
    assert page.character_button.text() == "設定角色"
    assert character_choices(page)[:2] == ["無", "追蹤者"]


def test_set_character_needs_a_selection(application: "QApplication", tmp_path: Path) -> None:
    recorder, page = make(tmp_path)
    assert page.character_button.text() == "Set character"
    assert character_choices(page) == [
        "None",
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
    assert not page.character_button.isEnabled()
    pick_character(page, "Raider")
    assert all(record.character == "" for record in recorder.store.read_all())

    page.table.selectRow(0)
    assert page.character_button.isEnabled()


def test_set_character_changes_the_selected_rows(
    application: "QApplication", tmp_path: Path
) -> None:
    recorder, page = make(tmp_path, "zh_CN")
    page.table.sortByColumn(at("duration"), Qt.SortOrder.AscendingOrder)
    page.table.selectRow(0)
    page.table.selectionModel().select(
        page.table.model().index(2, 0),
        QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
    )
    chosen = page.selected_records()
    assert len(chosen) == 2

    pick_character(page, "铁之眼")

    saved = recorder.store.read_all()
    # Written in the language of the program, like a new record.
    assert sorted(record.character for record in saved) == ["", "", "", "", "铁之眼", "铁之眼"]
    assert {r.started_at for r in saved if r.character} == {r.started_at for r in chosen}
    assert column(page, "character").count("铁之眼") == 2
    assert page.message.text() == ""

    page.table.selectAll()
    pick_character(page, "无")
    assert all(record.character == "" for record in recorder.store.read_all())
    assert set(column(page, "character")) == {""}


def test_set_character_says_so_when_the_file_is_open_elsewhere(
    application: "QApplication", tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorder, page = make(tmp_path)

    def locked(records: object, character: str) -> int:
        raise PermissionError

    monkeypatch.setattr(recorder.store, "set_character", locked)
    page.table.selectRow(0)
    pick_character(page, "Wylder")
    assert page.message.text() == "Records file is open in another program"
    assert set(column(page, "character")) == {""}


def test_characters_sort_as_one_whatever_language_they_were_saved_in(
    application: "QApplication", tmp_path: Path
) -> None:
    recorder = Recorder(tmp_path)
    for minute, name in enumerate(["Wylder", "Duchess", "追踪者", "", "女爵"], start=1):
        recorder.store.append(fight(minute=minute, character=name))
    page = RecordsPage(recorder.controller)
    page.refresh()
    page.table.sortByColumn(at("character"), Qt.SortOrder.AscendingOrder)
    assert column(page, "character") == ["", "Duchess", "Duchess", "Wylder", "Wylder"]
