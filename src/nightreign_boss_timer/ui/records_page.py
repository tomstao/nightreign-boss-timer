"""The Records page: every saved fight, newest first, with filters and a summary."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

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
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nightreign_boss_timer import characters
from nightreign_boss_timer.names import UNKNOWN
from nightreign_boss_timer.record_view import (
    ALL,
    boss_key,
    boss_label,
    filter_records,
    incompletes,
    names_in,
    summarise,
)
from nightreign_boss_timer.records import FightRecord, Status, format_duration
from nightreign_boss_timer.ui.controller import Controller
from nightreign_boss_timer.ui.pages import Page
from nightreign_boss_timer.ui.tick_table import TICK_COLUMN, TickTable

# The first column holds the tick box of a row and has no heading of its own.
COLUMNS = (
    "selected",
    "started_at",
    "table",
    "boss",
    "character",
    "level",
    "status",
    "start_hp",
    "end_hp",
    "duration",
)
_INCOMPLETE = QColor(200, 129, 26)
_ERROR = "color: #c8811a;"


def _ask(parent: QWidget, title: str, question: str) -> bool:
    """Ask a yes-or-no question in a small window. No is the button under Enter."""
    buttons = QMessageBox.StandardButton
    answer = QMessageBox.question(parent, title, question, buttons.Yes | buttons.No, buttons.No)
    return answer == buttons.Yes


def _identity(record: FightRecord) -> FightRecord:
    """What stays the same about a record when its character is changed by hand."""
    return replace(record, character="")


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

        self.table = TickTable(len(COLUMNS))
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(True)
        self.table.ticks_changed.connect(self._selection_changed)
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
        self.delete_incomplete_button = QPushButton()
        self.delete_incomplete_button.clicked.connect(self.delete_incomplete)
        # A button that opens the list of characters, for the selected rows.
        self.character_menu = QMenu(self)
        self.character_button = QPushButton()
        self.character_button.setEnabled(False)
        self.character_button.setMenu(self.character_menu)
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
        bottom.addWidget(self.character_button)
        bottom.addWidget(self.delete_incomplete_button)
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
        return [self._record_at(row) for row in self.table.ticked_rows()]

    def _record_at(self, row: int) -> FightRecord:
        """The record a row of the table shows, wherever sorting has put it."""
        return self._shown[self.table.item(row, TICK_COLUMN).index]  # type: ignore[union-attr]

    def _selection_changed(self) -> None:
        """Say how many rows are ticked, on the count line and on the delete button."""
        translate = self.controller.translate
        shown, selected = len(self._shown), len(self.table.ticked_rows())
        self.delete_button.setText(translate("records.delete", count=selected))
        self.delete_button.setEnabled(selected > 0)
        self.character_button.setEnabled(selected > 0)
        if selected:
            text = translate("records.count_selected", count=shown, selected=selected)
        else:
            text = translate("records.count", count=shown)
        self.count.setText(text)

    def _menu(self, position: object) -> None:
        if not self.table.ticked_rows():
            return
        menu = QMenu(self.table)
        menu.addMenu(self.character_menu)
        menu.addAction(self.delete_button.text(), self.delete_selected)
        menu.exec(self.table.viewport().mapToGlobal(position))  # type: ignore[arg-type]

    def delete_selected(self) -> None:
        """Delete the selected records from the file, after asking."""
        records = self.selected_records()
        if not records:
            return
        translate = self.controller.translate
        question = translate("records.delete_ask", count=len(records))
        if not self._ask(self, translate("records.delete", count=len(records)), question):
            return
        error = self.controller.delete_records(records)
        self.refresh()
        self.message.setText(error)

    def filtered(self) -> bool:
        """True while a filter or the search box hides some records."""
        boxes = (self.table_filter, self.boss_filter, self.status_filter)
        return any(box.currentData() for box in boxes) or bool(self.search.text().strip())

    def delete_incomplete(self) -> None:
        """Delete every incomplete record among those shown, after asking with their number.

        Records the filters hide are kept, so nothing is deleted that cannot be seen.
        """
        records = incompletes(self._shown)
        if not records:
            return
        translate = self.controller.translate
        key = "records.delete_incomplete_ask_shown" if self.filtered() else ""
        question = translate(key or "records.delete_incomplete_ask", count=len(records))
        title = translate("records.delete_incomplete", count=len(records))
        if not self._ask(self, title, question):
            return
        error = self.controller.delete_records(records)
        self.refresh()
        self.message.setText(error)

    def set_character(self, character: str) -> None:
        """Give the selected records a character, by its English name. Empty takes it away."""
        records = self.selected_records()
        if not records:
            return
        error = self.controller.set_character(records, character)
        self.refresh()
        self.message.setText(error)

    def _fill_character_menu(self) -> None:
        """List "none" and every character, named in the current language."""
        translate, language = self.controller.translate, self.controller.settings.ui_language
        self.character_menu.clear()
        self.character_menu.setTitle(translate("records.set_character"))
        choices = [(translate("records.no_character"), "")]
        choices += [(characters.label_of(key, language), key) for key in characters.all_keys()]
        for text, key in choices:
            action = self.character_menu.addAction(text)
            action.triggered.connect(lambda _checked=False, key=key: self.set_character(key))

    def _boss_name(self, record: FightRecord) -> str:
        """The boss of a record in the UI language if it is a known boss, else as it was read."""
        if record.boss == UNKNOWN:
            return self.controller.translate("records.unknown_boss")
        return boss_label(record, self.controller.settings.ui_language)

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
        """Read the records file again and redraw everything in the current language.

        Rows that were ticked stay ticked if their records are still shown, so a fight that is
        saved while the page is open does not undo a selection.
        """
        controller, translate = self.controller, self.controller.translate
        ticked = {_identity(record) for record in self.selected_records()}
        self._records = controller.store.read_all()
        tables, bosses = names_in(self._records)
        # Tables from the settings come first, in their order, then any that only records have.
        known = controller.settings.table_names()
        tables = known + [name for name in tables if name not in known]
        self._fill(self.table_filter, [(name, name) for name in tables])
        labels = {boss_key(record): self._boss_name(record) for record in self._records}
        self._fill(self.boss_filter, [(labels[key], key) for key in bosses])
        self._fill(
            self.status_filter,
            [(translate(f"status.{status.value}"), status.value) for status in Status],
        )
        for label, key in zip(self._filter_labels, ("table", "boss", "status"), strict=True):
            label.setText(translate(f"records.column.{key}"))
        self.search.setPlaceholderText(translate("records.search"))
        self.table.setHorizontalHeaderLabels(
            ["", *(translate(f"records.column.{column}") for column in COLUMNS[1:])]
        )
        self.table.horizontalHeaderItem(TICK_COLUMN).setToolTip(translate("records.select_all"))
        self.character_button.setText(translate("records.set_character"))
        self._fill_character_menu()
        self.message.setText("")
        self.open_file.setText(translate("records.open_file"))
        self.open_folder.setText(translate("records.open_folder"))
        self._show()
        rows = range(self.table.rowCount())
        self.table.tick_rows([row for row in rows if _identity(self._record_at(row)) in ticked])

    def shown_records(self) -> list[FightRecord]:
        return filter_records(
            self._records,
            table=self.table_filter.currentData() or ALL,
            boss=self.boss_filter.currentData() or ALL,
            status=self.status_filter.currentData() or ALL,
            search=self.search.text(),
        )

    def _show(self) -> None:
        """Fill the table and the summary from the records already read, for the filters as set.

        No row is ticked afterwards: a filter may have hidden what was ticked, and nothing that
        cannot be seen is to be deleted.
        """
        translate, language = self.controller.translate, self.controller.settings.ui_language
        records = self._shown = self.shown_records()
        self.table.clearSelection()  # the rows are about to show other records
        self.table.setSortingEnabled(False)  # or rows move while they are being filled
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            cells = (
                _Cell("", 0),  # the tick box
                _Cell(f"{record.started_at:%Y-%m-%d %H:%M:%S}", record.started_at),
                _Cell(record.table, record.table.casefold()),
                _Cell(self._boss_name(record), boss_key(record).casefold()),
                # One character sorts as one, whatever language its name was saved in.
                _Cell(
                    characters.label_of(record.character, language),
                    (characters.key_of(record.character) or record.character).casefold(),
                ),
                _Cell("" if record.level is None else str(record.level), record.level or 0),
                _Cell(translate(f"status.{record.status.value}"), record.status.value),
                _Cell(f"{record.start_hp_pct}%", record.start_hp_pct),
                _Cell(f"{record.end_hp_pct}%", record.end_hp_pct),
                _Cell(format_duration(record.duration_s), record.duration_s),
            )
            cells[TICK_COLUMN].index = row  # which record this row shows, wherever sorting puts it
            cells[TICK_COLUMN].setCheckState(Qt.CheckState.Unchecked)
            for column, cell in enumerate(cells):
                if record.status is Status.INCOMPLETE:
                    cell.setForeground(_INCOMPLETE)
                self.table.setItem(row, column, cell)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(COLUMNS.index("started_at"), Qt.SortOrder.DescendingOrder)
        self.table.resizeColumnsToContents()
        self.table.show_ticks()  # also fills in the count line and the delete button
        unfinished = len(incompletes(records))
        self.delete_incomplete_button.setText(
            translate("records.delete_incomplete", count=unfinished)
        )
        self.delete_incomplete_button.setEnabled(unfinished > 0)

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
