"""The Records page: every saved fight, newest first, with filters and a summary."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nightreign_boss_timer.names import UNKNOWN
from nightreign_boss_timer.record_view import ALL, filter_records, names_in, summarise
from nightreign_boss_timer.records import FightRecord, Status, format_duration
from nightreign_boss_timer.ui.controller import Controller
from nightreign_boss_timer.ui.pages import Page

COLUMNS = ("started_at", "table", "boss", "status", "start_hp", "end_hp", "duration")
_INCOMPLETE = QColor(200, 129, 26)
_ERROR = "color: #c8811a;"


def _ask(parent: QWidget, title: str, question: str) -> bool:
    """Ask a yes-or-no question in a small window. No is the button under Enter."""
    buttons = QMessageBox.StandardButton
    answer = QMessageBox.question(parent, title, question, buttons.Yes | buttons.No, buttons.No)
    return answer == buttons.Yes


class _Cell(QTableWidgetItem):
    """A cell that sorts by a value of its own instead of by its text, so 62% sorts below 100%."""

    def __init__(self, text: str, key: object) -> None:
        super().__init__(text)
        self.key = key
        self.index = -1
        self.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)

    def __lt__(self, other: QTableWidgetItem) -> bool:
        return self.key < other.key  # type: ignore[attr-defined, operator]


class RecordsPage(Page):
    key = "records"

    def __init__(
        self, controller: Controller, ask: Callable[[QWidget, str, str], bool] = _ask
    ) -> None:
        super().__init__(controller)
        self._ask = ask
        self._records: list[FightRecord] = []
        self._shown: list[FightRecord] = []
        self.table_filter = QComboBox()
        self.boss_filter = QComboBox()
        self.status_filter = QComboBox()
        self.search = QLineEdit()
        self.search.setClearButtonEnabled(True)
        self._filter_labels = [QLabel(), QLabel(), QLabel()]
        filters = QHBoxLayout()
        for label, box in zip(
            self._filter_labels,
            (self.table_filter, self.boss_filter, self.status_filter),
            strict=True,
        ):
            filters.addWidget(label)
            filters.addWidget(box)
            box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
            box.currentIndexChanged.connect(self._show)
        filters.addWidget(self.search, 1)
        self.search.textChanged.connect(self._show)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(True)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu)
        delete_key = QShortcut(QKeySequence(QKeySequence.StandardKey.Delete), self.table)
        delete_key.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        delete_key.activated.connect(self.delete_selected)

        self.message = QLabel()
        self.message.setStyleSheet(_ERROR)
        self.delete_button = QPushButton()
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.delete_selected)
        self.summary = QLabel()
        self.count = QLabel()
        self.open_file = QPushButton()
        self.open_folder = QPushButton()
        self.open_file.clicked.connect(controller.open_records_file)
        self.open_folder.clicked.connect(controller.open_records_folder)
        bottom = QHBoxLayout()
        bottom.addWidget(self.count)
        bottom.addWidget(self.message)
        bottom.addStretch(1)
        bottom.addWidget(self.delete_button)
        bottom.addWidget(self.open_file)
        bottom.addWidget(self.open_folder)

        layout = QVBoxLayout(self)
        layout.addLayout(filters)
        layout.addWidget(self.summary)
        layout.addWidget(self.table, 1)
        layout.addLayout(bottom)
        controller.records_changed.connect(self._records_changed)

    def _records_changed(self) -> None:
        if self.isVisible():
            self.refresh()

    def selected_records(self) -> list[FightRecord]:
        """The records of the rows that are selected now."""
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        return [self._shown[self.table.item(row, 0).index] for row in rows]  # type: ignore[union-attr]

    def _selection_changed(self) -> None:
        self.delete_button.setEnabled(bool(self.table.selectedIndexes()))

    def _menu(self, position: object) -> None:
        if not self.table.selectedIndexes():
            return
        menu = QMenu(self.table)
        menu.addAction(self.delete_button.text(), self.delete_selected)
        menu.exec(self.table.viewport().mapToGlobal(position))  # type: ignore[arg-type]

    def delete_selected(self) -> None:
        """Delete the selected records from the file, after asking."""
        records = self.selected_records()
        if not records:
            return
        translate = self.controller.translate
        question = translate("records.delete_ask", count=len(records))
        if not self._ask(self, translate("records.delete"), question):
            return
        error = self.controller.delete_records(records)
        self.refresh()
        self.message.setText(error)

    def _boss_name(self, name: str) -> str:
        return self.controller.translate("records.unknown_boss") if name == UNKNOWN else name

    def _fill(self, box: QComboBox, values: list[tuple[str, str]]) -> None:
        """Put (text, value) choices in a filter box, keeping the current choice if it survives."""
        keep = box.currentData()
        box.blockSignals(True)
        box.clear()
        box.addItem(self.controller.translate("records.filter_all"), ALL)
        for text, value in values:
            box.addItem(text, value)
        box.setCurrentIndex(max(0, box.findData(keep)))
        box.blockSignals(False)

    def refresh(self) -> None:
        """Read the records file again and redraw everything in the current language."""
        controller, translate = self.controller, self.controller.translate
        self._records = controller.store.read_all()
        tables, bosses = names_in(self._records)
        # Tables from the settings come first, in their order, then any that only records have.
        known = controller.settings.table_names()
        tables = known + [name for name in tables if name not in known]
        self._fill(self.table_filter, [(name, name) for name in tables])
        self._fill(self.boss_filter, [(self._boss_name(name), name) for name in bosses])
        self._fill(
            self.status_filter,
            [(translate(f"status.{status.value}"), status.value) for status in Status],
        )
        for label, key in zip(self._filter_labels, ("table", "boss", "status"), strict=True):
            label.setText(translate(f"records.column.{key}"))
        self.search.setPlaceholderText(translate("records.search"))
        self.table.setHorizontalHeaderLabels(
            [translate(f"records.column.{column}") for column in COLUMNS]
        )
        self.delete_button.setText(translate("records.delete"))
        self.message.setText("")
        self.open_file.setText(translate("records.open_file"))
        self.open_folder.setText(translate("records.open_folder"))
        self._show()

    def shown_records(self) -> list[FightRecord]:
        return filter_records(
            self._records,
            table=self.table_filter.currentData() or ALL,
            boss=self.boss_filter.currentData() or ALL,
            status=self.status_filter.currentData() or ALL,
            search=self.search.text(),
        )

    def _show(self) -> None:
        """Fill the table and the summary from the records already read, for the filters as set."""
        translate = self.controller.translate
        records = self._shown = self.shown_records()
        self.table.clearSelection()  # the rows are about to show other records
        self.table.setSortingEnabled(False)  # or rows move while they are being filled
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            cells = (
                _Cell(f"{record.started_at:%Y-%m-%d %H:%M:%S}", record.started_at),
                _Cell(record.table, record.table.casefold()),
                _Cell(self._boss_name(record.boss), record.boss.casefold()),
                _Cell(translate(f"status.{record.status.value}"), record.status.value),
                _Cell(f"{record.start_hp_pct}%", record.start_hp_pct),
                _Cell(f"{record.end_hp_pct}%", record.end_hp_pct),
                _Cell(format_duration(record.duration_s), record.duration_s),
            )
            cells[0].index = row  # which record this row shows, wherever sorting puts it
            for column, cell in enumerate(cells):
                if record.status is Status.INCOMPLETE:
                    cell.setForeground(_INCOMPLETE)
                self.table.setItem(row, column, cell)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.SortOrder.DescendingOrder)
        self.table.resizeColumnsToContents()
        self.count.setText(translate("records.count", count=len(records)))

        # The summary only means something for one boss.
        if self.boss_filter.currentData() and records:
            total = summarise(records)
            if total.best_s is None:
                text = translate(
                    "records.summary_no_time", attempts=total.attempts, completes=total.completes
                )
            else:
                text = translate(
                    "records.summary",
                    attempts=total.attempts,
                    completes=total.completes,
                    best=format_duration(total.best_s),
                    average=format_duration(total.average_s or 0.0),
                )
            self.summary.setText(text)
        else:
            self.summary.setText("")
