"""The main window: a list of pages on the left, the chosen page beside it, a status bar below.

Closing the window only hides it. The tool keeps running in the tray, and quitting is a tray
menu entry.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from nightreign_boss_timer.engine import State
from nightreign_boss_timer.ui.controller import Controller
from nightreign_boss_timer.ui.pages import AboutPage, Page
from nightreign_boss_timer.ui.records_page import RecordsPage
from nightreign_boss_timer.ui.tables_page import TablesPage


def default_pages(controller: Controller) -> list[Page]:
    """The pages in sidebar order."""
    return [RecordsPage(controller), TablesPage(controller), AboutPage(controller)]


class MainWindow(QWidget):
    def __init__(self, controller: Controller, pages: list[Page] | None = None) -> None:
        super().__init__()
        self._controller = controller
        self.pages = pages if pages is not None else default_pages(controller)
        self.resize(980, 620)

        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(170)
        self.stack = QStackedWidget()
        for page in self.pages:
            self.sidebar.addItem("")
            self.stack.addWidget(page)
        self.sidebar.currentRowChanged.connect(self._page_chosen)

        # Each status item is a flat button: clicking it goes to where that thing is changed.
        self.tracking_status = self._status_button(controller.toggle_tracking)
        self.table_status = self._status_button(lambda: self.show_page("tables"))
        self.game_status = self._status_button(None)
        self.regions_status = self._status_button(lambda: self.show_page("regions"))
        status = QHBoxLayout()
        for button in (
            self.tracking_status,
            self.table_status,
            self.game_status,
            self.regions_status,
        ):
            status.addWidget(button)
        status.addStretch(1)

        body = QHBoxLayout()
        body.addWidget(self.sidebar)
        body.addWidget(self.stack, 1)
        layout = QVBoxLayout(self)
        layout.addLayout(body, 1)
        layout.addLayout(status)

        controller.changed.connect(self.refresh)
        controller.state_changed.connect(self._refresh_status)
        self.sidebar.setCurrentRow(0)
        self.refresh()

    def _status_button(self, clicked: object) -> QPushButton:
        button = QPushButton()
        button.setFlat(True)
        if clicked is None:
            button.setEnabled(False)
        else:
            button.clicked.connect(clicked)
        return button

    def _page_chosen(self, row: int) -> None:
        self.stack.setCurrentIndex(row)
        if 0 <= row < len(self.pages):
            self.pages[row].refresh()

    def show_page(self, key: str = "") -> None:
        """Bring the window up, on the page with this key if there is one."""
        for row, page in enumerate(self.pages):
            if page.key == key:
                self.sidebar.setCurrentRow(row)
        self.pages[self.sidebar.currentRow()].refresh()
        self.show()
        self.showNormal()  # in case it was minimised
        self.raise_()
        self.activateWindow()

    def refresh(self) -> None:
        """Redraw every text from the settings, in the current language."""
        translate = self._controller.translate
        self.setWindowTitle(translate("app.name"))
        for row, page in enumerate(self.pages):
            self.sidebar.item(row).setText(translate(f"page.{page.key}"))
        self.pages[self.sidebar.currentRow()].refresh()
        self._refresh_status()

    def _refresh_status(self) -> None:
        controller, translate = self._controller, self._controller.translate
        on = controller.tracking
        self.tracking_status.setText(
            translate("statusbar.tracking_on" if on else "statusbar.tracking_off")
        )
        self.table_status.setText(translate("tray.table", table=controller.settings.active_table))
        found = controller.state in (State.IDLE, State.FIGHT)
        # While paused the tool does not look for the game, so it cannot say either way.
        self.game_status.setVisible(controller.state is not State.PAUSED)
        self.game_status.setText(
            translate("statusbar.game_found" if found else "statusbar.game_not_found")
        )
        self.regions_status.setText(
            translate(
                "statusbar.regions_ok" if controller.calibrated else "statusbar.regions_default"
            )
        )
