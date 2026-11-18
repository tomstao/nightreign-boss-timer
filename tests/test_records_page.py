import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the UI is Windows-only")

if sys.platform == "win32":
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from nightreign_boss_timer.records import Status
    from nightreign_boss_timer.ui.records_page import RecordsPage
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


def column(page: "RecordsPage", index: int) -> list[str]:
    return [page.table.item(row, index).text() for row in range(page.table.rowCount())]


def choose(box: object, value: str) -> None:
    box.setCurrentIndex(box.findData(value))  # type: ignore[attr-defined]


def test_lists_every_record_newest_first(application: "QApplication", tmp_path: Path) -> None:
    _, page = make(tmp_path)
    headers = [page.table.horizontalHeaderItem(i).text() for i in range(page.table.columnCount())]
    assert headers == [
        "Date and time",
        "Table",
        "Boss",
        "Level",
        "Status",
        "Start HP",
        "End HP",
        "Time",
    ]
    assert column(page, 0)[0] == "2026-11-17 21:30:00"
    assert column(page, 0)[-1] == "2026-11-17 21:01:00"
    assert column(page, 2)[0] == "unknown"
    assert column(page, 7)[-1] == "02:41.3"
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
    assert set(column(page, 2)) == {"Tree Sentinel"}
    assert page.summary.text() == "4 attempts, 3 complete, best 01:50.0, average 02:00.0"

    choose(page.status_filter, "incomplete")
    assert page.count.text() == "1 records"
    assert page.summary.text() == "1 attempts, 0 complete"


def test_search_narrows_as_you_type(application: "QApplication", tmp_path: Path) -> None:
    _, page = make(tmp_path)
    QTest.keyClicks(page.search, "normal")
    assert column(page, 2) == ["Golden Hippopotamus"]  # saved as 黄金河马, shown in English
    page.search.clear()
    assert page.table.rowCount() == 6


def test_hp_and_time_sort_as_numbers(application: "QApplication", tmp_path: Path) -> None:
    _, page = make(tmp_path)
    page.table.sortByColumn(5, Qt.SortOrder.AscendingOrder)
    assert column(page, 5)[0] == "62%"  # as text, "100%" would come first
    page.table.sortByColumn(7, Qt.SortOrder.DescendingOrder)
    assert column(page, 7)[0] == "02:41.3"


def test_incomplete_rows_look_different(application: "QApplication", tmp_path: Path) -> None:
    _, page = make(tmp_path)
    statuses = column(page, 4)
    incomplete = page.table.item(statuses.index("Incomplete"), 4).foreground().color()
    complete = page.table.item(statuses.index("Complete"), 4).foreground().color()
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
    assert "Night Aspect" in column(page, 2)
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
    assert column(other, 4) != column(english, 4)
    assert column(other, 2)[0] != "unknown"
    # A boss saved under its English name is shown in the language of the UI.
    assert ("大树守卫" if language == "zh_CN" else "大樹守衛") in column(other, 2)
    assert "Tree Sentinel" not in column(other, 2)
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
    assert column(page, 3) == ["", "7"]  # newest first


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
    page.table.sortByColumn(7, Qt.SortOrder.AscendingOrder)  # the rows are not in file order
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
