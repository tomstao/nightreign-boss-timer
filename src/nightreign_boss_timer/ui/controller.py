"""What the user can do, in one place.

The tray menu, the main window and the hotkeys all call the same methods here, so each action
behaves the same wherever it is started from. The controller changes the settings, saves them,
and announces the change. It draws nothing itself.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from nightreign_boss_timer import settings as settings_file
from nightreign_boss_timer.engine import State, records_path
from nightreign_boss_timer.i18n import LANGUAGES, Translator
from nightreign_boss_timer.records import RecordStore
from nightreign_boss_timer.settings import Settings, TableError


def _open_with_windows(path: Path) -> None:
    os.startfile(path)  # the program Windows has for this kind of file, Excel for a CSV


class Controller(QObject):
    # Something shown in a menu or a window is now different: redraw from the settings.
    changed = Signal()
    # A short message for the overlay, such as the table just switched to.
    notice = Signal(str)
    # A fight was saved, or records were changed by hand: lists of records are out of date.
    records_changed = Signal()
    # The user asked for the calibration window.
    calibration_requested = Signal()
    # The user asked for the main window, at the page with this key (empty: the page it is on).
    window_requested = Signal(str)
    # What the engine is doing changed, for example the game window was found.
    state_changed = Signal()

    def __init__(
        self,
        settings: Settings,
        translate: Translator,
        store: RecordStore,
        *,
        settings_path: Path | None = None,
        opener: Callable[[Path], None] = _open_with_windows,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.translate = translate
        self.store = store
        self.tracking = True
        self.overlay_visible = True
        self.state = State.IDLE
        self._settings_path = settings_path
        self._opener = opener

    def save(self) -> None:
        settings_file.save(self.settings, self._settings_path)

    # --- settings -------------------------------------------------------------------------------

    def set_language(self, language: str) -> None:
        """Switch the UI language. Everything on screen is redrawn in it at once."""
        if language not in LANGUAGES or language == self.settings.ui_language:
            return
        self.settings.ui_language = language
        self.translate.language = language
        self.save()
        self.changed.emit()

    def set_records_folder(self, folder: str) -> None:
        """Save records in another folder from now on. Empty means the default folder.

        Records already saved are not moved.
        """
        if folder == self.settings.records_folder:
            return
        self.settings.records_folder = folder
        self.store.set_path(records_path(self.settings))
        self.save()
        self.records_changed.emit()
        self.changed.emit()

    def set_option(self, name: str, value: float | bool) -> None:
        """Change one of the timing options: ``wait_window_s``, ``skip_walk_pasts``,
        ``fight_rate``. The engine reads them from the settings on its next step."""
        if name not in ("wait_window_s", "skip_walk_pasts", "fight_rate"):
            raise ValueError(f"not an option: {name}")
        if getattr(self.settings, name) == value:
            return
        setattr(self.settings, name, value)
        self.save()
        self.changed.emit()

    # --- tracking and overlay -------------------------------------------------------------------

    def set_tracking(self, on: bool) -> None:
        if on == self.tracking:
            return
        self.tracking = on
        self.notice.emit(self.translate("overlay.tracking" if on else "overlay.paused"))
        self.changed.emit()

    def toggle_tracking(self) -> None:
        self.set_tracking(not self.tracking)

    def set_overlay_visible(self, on: bool) -> None:
        if on == self.overlay_visible:
            return
        self.overlay_visible = on
        self.changed.emit()

    def toggle_overlay(self) -> None:
        self.set_overlay_visible(not self.overlay_visible)

    # --- tables ---------------------------------------------------------------------------------

    def set_table(self, name: str) -> None:
        """Make a table the active one. Fights that start from now on are saved under it."""
        if name == self.settings.active_table:
            return
        self.settings.set_active_table(name)
        self._table_switched()

    def next_table(self) -> None:
        if len(self.settings.tables) > 1:
            self.settings.next_table()
            self._table_switched()

    def _table_switched(self) -> None:
        self.save()
        self.notice.emit(self.translate("overlay.table_switched", table=self.settings.active_table))
        self.changed.emit()

    def _change_tables(self, change: Callable[[], object]) -> str:
        """Make a change to the list of tables. Returns why it was refused, or nothing."""
        active = self.settings.active_table
        try:
            change()
        except TableError as error:
            return self.translate(f"tables.error.{error.reason}", name=error.name)
        self.save()
        if self.settings.active_table != active:
            self.notice.emit(
                self.translate("overlay.table_switched", table=self.settings.active_table)
            )
        self.changed.emit()
        return ""

    def add_table(self, name: str) -> str:
        """Add a table. Returns an error message in the user's language, or nothing if it worked."""
        return self._change_tables(lambda: self.settings.add_table(name))

    def rename_table(self, old: str, new: str) -> str:
        return self._change_tables(lambda: self.settings.rename_table(old, new))

    def delete_table(self, name: str) -> str:
        return self._change_tables(lambda: self.settings.delete_table(name))

    # --- records --------------------------------------------------------------------------------

    def open_records_file(self) -> None:
        """Open the records file in the program Windows uses for CSV files, normally Excel."""
        self.store.ensure_file()
        self._opener(self.store.path)

    def open_records_folder(self) -> None:
        self.store.path.parent.mkdir(parents=True, exist_ok=True)
        self._opener(self.store.path.parent)

    # --- windows and status ---------------------------------------------------------------------

    def show_window(self, page: str = "") -> None:
        self.window_requested.emit(page)

    def set_state(self, state: State) -> None:
        """Called by whoever drives the engine, after every step."""
        if state is not self.state:
            self.state = state
            self.state_changed.emit()

    @property
    def calibrated(self) -> bool:
        return self.settings.bar_region is not None

    # --- calibration ----------------------------------------------------------------------------

    def calibrate(self) -> None:
        self.calibration_requested.emit()
