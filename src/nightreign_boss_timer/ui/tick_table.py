"""A table with a tick box in front of every row and one in the header for all rows.

A ticked row is a selected row: there is one selection, shown twice. So everything that selects
rows keeps working (Ctrl and Shift with a click, Ctrl+A, dragging), and the boxes add a way that
can be seen. A click in the first column ticks or unticks that row and leaves the others alone.

The page fills the rows. Its item in the first column of a row is where the tick is drawn.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QItemSelectionModel, QModelIndex, QRect, QSize, Qt, Signal
from PySide6.QtGui import QMouseEvent, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QStyle,
    QStyleOptionButton,
    QTableWidget,
    QWidget,
)

TICK_COLUMN = 0
_Flag = QItemSelectionModel.SelectionFlag


class TickHeader(QHeaderView):
    """A header that draws a tick box in its first section and reports clicks on it."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.state = Qt.CheckState.Unchecked

    def set_state(self, state: Qt.CheckState) -> None:
        if state != self.state:
            self.state = state
            self.viewport().update()

    def paintSection(self, painter: QPainter, rect: QRect, index: int) -> None:
        painter.save()
        super().paintSection(painter, rect, index)
        painter.restore()
        if index != TICK_COLUMN:
            return
        style, option = self.style(), QStyleOptionButton()
        side = style.pixelMetric(QStyle.PixelMetric.PM_IndicatorWidth)
        option.rect = QStyle.alignedRect(
            self.layoutDirection(), Qt.AlignmentFlag.AlignCenter, QSize(side, side), rect
        )
        option.state = (
            QStyle.StateFlag.State_Enabled
            | {
                Qt.CheckState.Checked: QStyle.StateFlag.State_On,
                Qt.CheckState.PartiallyChecked: QStyle.StateFlag.State_NoChange,
                Qt.CheckState.Unchecked: QStyle.StateFlag.State_Off,
            }[self.state]
        )
        style.drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorCheckBox, option, painter)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        # A click on the box is not a request to sort by that column.
        if self.logicalIndexAt(event.position().toPoint()) == TICK_COLUMN:
            self.clicked.emit()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.logicalIndexAt(event.position().toPoint()) != TICK_COLUMN:
            super().mouseReleaseEvent(event)


class TickTable(QTableWidget):
    """The table. ``ticks_changed`` is emitted whenever the set of ticked rows is different."""

    ticks_changed = Signal()

    def __init__(self, columns: int) -> None:
        super().__init__(0, columns)
        self.header = TickHeader(self)
        self.setHorizontalHeader(self.header)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.header.clicked.connect(self.toggle_all)
        self.itemSelectionChanged.connect(self.show_ticks)

    def ticked_rows(self) -> list[int]:
        """The rows that are ticked, top to bottom as they are shown."""
        return sorted(index.row() for index in self.selectionModel().selectedRows())

    def all_state(self) -> Qt.CheckState:
        """What the box in the header shows: every row ticked, some, or none."""
        ticked = len(self.ticked_rows())
        if ticked == 0:
            return Qt.CheckState.Unchecked
        full = ticked == self.rowCount()
        return Qt.CheckState.Checked if full else Qt.CheckState.PartiallyChecked

    def toggle_all(self) -> None:
        """Tick every row, or untick them all if every row is ticked already."""
        if self.all_state() is Qt.CheckState.Checked:
            self.clearSelection()
        else:
            self.selectAll()

    def tick_rows(self, rows: list[int]) -> None:
        """Tick exactly these rows."""
        model, selection = self.model(), self.selectionModel()
        self.blockSignals(True)  # one report at the end instead of one per row
        selection.clearSelection()
        for row in rows:
            selection.select(model.index(row, TICK_COLUMN), _Flag.Select | _Flag.Rows)
        self.blockSignals(False)
        self.show_ticks()

    def show_ticks(self) -> None:
        """Make every box say whether its row is selected, and the header box sum them up."""
        ticked = set(self.ticked_rows())
        self.blockSignals(True)  # setting a tick is not the user changing an item
        for row in range(self.rowCount()):
            item = self.item(row, TICK_COLUMN)
            wanted = Qt.CheckState.Checked if row in ticked else Qt.CheckState.Unchecked
            if item is not None and item.checkState() != wanted:
                item.setCheckState(wanted)
        self.blockSignals(False)
        self.header.set_state(self.all_state())
        self.ticks_changed.emit()

    def selectionCommand(
        self, index: QModelIndex, event: QEvent | None = None
    ) -> QItemSelectionModel.SelectionFlag:
        """How a click or key changes the selection. The first column toggles its own row."""
        mouse = (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.MouseMove,
        )
        if event is not None and index.column() == TICK_COLUMN and event.type() in mouse:
            left = event.button() == Qt.MouseButton.LeftButton  # type: ignore[attr-defined]
            if event.type() == QEvent.Type.MouseButtonPress and left:
                return _Flag.Toggle | _Flag.Rows
            return _Flag.NoUpdate  # or dragging across the boxes would flip them back and forth
        return super().selectionCommand(index, event)
