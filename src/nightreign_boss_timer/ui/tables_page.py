"""The Tables page: the named groups that records are saved under."""

from __future__ import annotations

from collections import Counter

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from nightreign_boss_timer.ui.controller import Controller
from nightreign_boss_timer.ui.pages import Page

COLUMNS = ("active", "name", "records", "hotkey")
ACTIVE_MARK = "●"  # a filled circle
_ERROR = "color: #c8811a; font-weight: bold;"


class TablesPage(Page):
    key = "tables"

    def __init__(self, controller: Controller) -> None:
        super().__init__(controller)
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.cellDoubleClicked.connect(lambda _row, _column: self.make_active())

        self.name = QLineEdit()
        self.name.returnPressed.connect(self.add)
        self.add_button = QPushButton()
        self.rename_button = QPushButton()
        self.delete_button = QPushButton()
        self.active_button = QPushButton()
        self.add_button.clicked.connect(self.add)
        self.rename_button.clicked.connect(self.rename)
        self.delete_button.clicked.connect(self.delete)
        self.active_button.clicked.connect(self.make_active)
        self.message = QLabel()
        self.message.setStyleSheet(_ERROR)
        self.note = QLabel()
        self.note.setWordWrap(True)

        row = QHBoxLayout()
        row.addWidget(self.name, 1)
        for button in (
            self.add_button,
            self.rename_button,
            self.delete_button,
            self.active_button,
        ):
            row.addWidget(button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.table, 1)
        layout.addLayout(row)
        layout.addWidget(self.message)
        layout.addWidget(self.note)

    def selected(self) -> str:
        """The name of the selected table, or nothing."""
        row = self.table.currentRow()
        tables = self.controller.settings.tables
        return tables[row].name if 0 <= row < len(tables) else ""

    def _selection_changed(self) -> None:
        name = self.selected()
        tables = {table.name: table for table in self.controller.settings.tables}
        self.rename_button.setEnabled(bool(name))
        self.active_button.setEnabled(bool(name) and name != self.controller.settings.active_table)
        # Built-in tables stay, so there is always somewhere to record.
        self.delete_button.setEnabled(bool(name) and not tables[name].builtin)

    def refresh(self) -> None:
        controller, translate = self.controller, self.controller.translate
        settings = controller.settings
        counts = Counter(record.table for record in controller.store.read_all())
        keep = self.selected()
        self.table.setHorizontalHeaderLabels(
            [translate(f"tables.column.{column}") for column in COLUMNS]
        )
        self.table.setRowCount(len(settings.tables))
        for row, table in enumerate(settings.tables):
            cells = (
                ACTIVE_MARK if table.name == settings.active_table else "",
                table.name,
                str(counts[table.name]),
                table.hotkey or translate("hotkey.none"),
            )
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if column != 1:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()
        names = settings.table_names()
        self.table.selectRow(names.index(keep) if keep in names else -1)
        self.name.setPlaceholderText(translate("tables.name_placeholder"))
        self.add_button.setText(translate("tables.new"))
        self.rename_button.setText(translate("tables.rename"))
        self.delete_button.setText(translate("tables.delete"))
        self.active_button.setText(translate("tables.set_active"))
        self.note.setText(translate("tables.note"))
        self._selection_changed()

    def _done(self, error: str, select: str = "") -> None:
        """Show why a change was refused, or tidy up after one that worked."""
        self.message.setText(error)
        if error:
            return
        self.name.clear()
        names = self.controller.settings.table_names()
        if select in names:
            self.table.selectRow(names.index(select))

    def add(self) -> None:
        name = self.name.text().strip()
        self._done(self.controller.add_table(name), select=name)

    def rename(self) -> None:
        old, new = self.selected(), self.name.text().strip()
        if old:
            self._done(self.controller.rename_table(old, new), select=new)

    def delete(self) -> None:
        name = self.selected()
        if name:
            self._done(self.controller.delete_table(name))

    def make_active(self) -> None:
        name = self.selected()
        if name:
            self.controller.set_table(name)
            self._done("", select=name)
