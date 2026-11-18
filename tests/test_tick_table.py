import os
import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the UI is Windows-only")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

if sys.platform == "win32":
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QTableWidgetItem

    from nightreign_boss_timer.ui.tick_table import TICK_COLUMN, TickTable

    LEFT = Qt.MouseButton.LeftButton
    CHECKED, PARTLY, UNCHECKED = (
        Qt.CheckState.Checked,
        Qt.CheckState.PartiallyChecked,
        Qt.CheckState.Unchecked,
    )


@pytest.fixture(scope="module")
def application() -> "QApplication":
    return QApplication.instance() or QApplication([])


def make(rows: int = 4) -> tuple["TickTable", list[int]]:
    """A table of ``rows`` rows and three columns, and a list that counts its reports."""
    table = TickTable(3)
    table.setRowCount(rows)
    for row in range(rows):
        for column in range(3):
            item = QTableWidgetItem("" if column == TICK_COLUMN else f"{row}.{column}")
            if column == TICK_COLUMN:
                item.setCheckState(Qt.CheckState.Unchecked)
            table.setItem(row, column, item)
    table.resize(600, 300)
    reports: list[int] = []
    table.ticks_changed.connect(lambda: reports.append(len(table.ticked_rows())))
    return table, reports


def click(table: "TickTable", row: int, column: int, modifier: object = None) -> None:
    where = table.visualItemRect(table.item(row, column)).center()
    modifiers = modifier or Qt.KeyboardModifier.NoModifier
    QTest.mouseClick(table.viewport(), LEFT, modifiers, where)


def ticks(table: "TickTable") -> list[bool]:
    return [table.item(row, TICK_COLUMN).checkState() is CHECKED for row in range(table.rowCount())]


def test_a_click_on_a_box_ticks_that_row_and_leaves_the_others(application: "QApplication") -> None:
    table, reports = make()
    assert table.ticked_rows() == []
    assert table.all_state() is UNCHECKED

    click(table, 1, TICK_COLUMN)
    click(table, 3, TICK_COLUMN)

    assert table.ticked_rows() == [1, 3]
    assert ticks(table) == [False, True, False, True]
    assert table.all_state() is PARTLY
    assert table.header.state is PARTLY
    assert reports == [1, 2]

    click(table, 1, TICK_COLUMN)  # a second click takes the tick away again
    assert table.ticked_rows() == [3]
    assert ticks(table) == [False, False, False, True]


def test_a_click_elsewhere_in_a_row_selects_as_tables_always_do(
    application: "QApplication",
) -> None:
    table, _ = make()
    click(table, 0, TICK_COLUMN)
    click(table, 2, 1)  # a plain click picks that row alone
    assert ticks(table) == [False, False, True, False]
    click(table, 3, 1, Qt.KeyboardModifier.ControlModifier)  # Ctrl adds to it
    assert ticks(table) == [False, False, True, True]
    click(table, 0, 2, Qt.KeyboardModifier.ShiftModifier)  # Shift takes the range
    assert ticks(table) == [True, True, True, True]
    assert table.all_state() is CHECKED


def test_the_box_in_the_header_ticks_all_rows_and_then_none(application: "QApplication") -> None:
    table, reports = make()
    header = table.header
    in_box = QPoint(header.sectionViewportPosition(TICK_COLUMN) + 3, header.height() // 2)

    QTest.mouseClick(header.viewport(), LEFT, Qt.KeyboardModifier.NoModifier, in_box)
    assert ticks(table) == [True, True, True, True]
    assert header.state is CHECKED

    QTest.mouseClick(header.viewport(), LEFT, Qt.KeyboardModifier.NoModifier, in_box)
    assert ticks(table) == [False, False, False, False]
    assert header.state is UNCHECKED
    assert reports == [4, 0]

    click(table, 2, TICK_COLUMN)  # from "some", the box goes to "all"
    table.toggle_all()
    assert table.ticked_rows() == [0, 1, 2, 3]


def test_a_click_on_the_header_box_does_not_sort(application: "QApplication") -> None:
    table, _ = make()
    table.setSortingEnabled(True)
    table.sortByColumn(1, Qt.SortOrder.DescendingOrder)
    header = table.header
    in_box = QPoint(header.sectionViewportPosition(TICK_COLUMN) + 3, header.height() // 2)
    QTest.mouseClick(header.viewport(), LEFT, Qt.KeyboardModifier.NoModifier, in_box)
    assert header.sortIndicatorSection() == 1
    assert [table.item(row, 1).text() for row in range(4)] == ["3.1", "2.1", "1.1", "0.1"]


def test_ticks_follow_a_selection_made_from_code(application: "QApplication") -> None:
    table, reports = make()
    table.selectAll()  # what Ctrl+A does
    assert ticks(table) == [True, True, True, True]
    table.tick_rows([0, 2])
    assert table.ticked_rows() == [0, 2]
    assert ticks(table) == [True, False, True, False]
    assert reports[-1] == 2
    table.tick_rows([])
    assert table.all_state() is UNCHECKED


def test_an_empty_table_has_nothing_ticked(application: "QApplication") -> None:
    table, _ = make(rows=0)
    table.toggle_all()
    assert table.ticked_rows() == []
    assert table.all_state() is UNCHECKED
