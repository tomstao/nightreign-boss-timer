"""What the user can do, in one place.

The tray menu, the main window and the hotkeys all call the same methods here, so each action
behaves the same wherever it is started from. The controller changes the settings, saves them,
and announces the change. It draws nothing itself.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from nightreign_boss_timer import settings as settings_file
from nightreign_boss_timer.engine import Probe, State, records_path
from nightreign_boss_timer.hotkeys import TABLE_PREFIX, conflict, has_modifier, normalise
from nightreign_boss_timer.i18n import LANGUAGES, Translator
from nightreign_boss_timer.records import FightRecord, RecordStore
from nightreign_boss_timer.settings import DEFAULT_HOTKEYS, Settings, TableError, default_tables

# How long after discarding a record the same action brings it back.
UNDO_SECONDS = 5.0


def _open_with_windows(path: Path) -> None:
    os.startfile(path)  # the program Windows has for this kind of file, Excel for a CSV


class Controller(QObject):
    # Something shown in a menu or a window is now different: redraw from the settings.
    changed = Signal()
    # A short message for the overlay, such as the table just switched to.
    notice = Signal(str)
    # A fight was saved, or records were changed by hand: lists of records are out of date.
    records_changed = Signal()
    # The user asked for the calibration window, starting at this region (empty: the first).
    calibration_requested = Signal(str)
    # The user asked for the first-run setup guide.
    setup_requested = Signal()
    # The main window was shown (True) or hidden (False).
    window_shown = Signal(bool)
    # A shortcut is being typed in: hotkeys must not fire (True), or may again (False).
    hotkeys_suspended = Signal(bool)
    # The user asked for the fight in progress to be ended now.
    end_fight_requested = Signal()
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
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.translate = translate
        self.store = store
        self.tracking = True
        self.overlay_visible = True
        self.state = State.IDLE
        # Set by the app: reads both regions from the screen once, or returns None if the game
        # is not found. Left empty when there is no screen to read, as in tests.
        self.probe: Callable[[], Probe | None] | None = None
        self._settings_path = settings_path
        self._opener = opener
        self._clock = clock
        self._discarded: FightRecord | None = None
        # Set by the app: registers the hotkeys in the settings with Windows and returns the
        # actions it refused. Left empty when there is nothing to register with, as in tests.
        self.hotkey_applier: Callable[[Settings], set[str]] | None = None
        # Actions whose shortcut Windows refused, usually because another program has it.
        self.failed_hotkeys: set[str] = set()
        self._discarded_at = 0.0

    def save(self) -> None:
        settings_file.save(self.settings, self._settings_path)

    # --- hotkeys --------------------------------------------------------------------------------

    def hotkey_actions(self) -> list[str]:
        """Every action that can have a shortcut, in display order."""
        tables = [TABLE_PREFIX + name for name in self.settings.table_names()]
        return [*DEFAULT_HOTKEYS, *tables]

    def action_label(self, action: str) -> str:
        """The name of an action in the user's language."""
        if action.startswith(TABLE_PREFIX):
            return self.translate("hotkey.switch_table", table=action[len(TABLE_PREFIX) :])
        return self.translate(f"hotkey.{action}")

    def hotkey_of(self, action: str) -> str:
        """The shortcut of an action, or nothing."""
        if action.startswith(TABLE_PREFIX):
            name = action[len(TABLE_PREFIX) :]
            return next((t.hotkey for t in self.settings.tables if t.name == name), "")
        return self.settings.hotkeys.get(action, "")

    def refresh_hotkeys(self) -> None:
        """Register the shortcuts in the settings with Windows and note which were refused."""
        if self.hotkey_applier is not None:
            self.failed_hotkeys = set(self.hotkey_applier(self.settings))

    def _store_hotkey(self, action: str, shortcut: str) -> None:
        if action.startswith(TABLE_PREFIX):
            name = action[len(TABLE_PREFIX) :]
            for table in self.settings.tables:
                if table.name == name:
                    table.hotkey = shortcut
        else:
            self.settings.hotkeys[action] = shortcut

    def set_hotkey(self, action: str, shortcut: str) -> str:
        """Give an action a shortcut, or none with an empty one.

        Returns a message in the user's language: why it was refused, a warning about a
        shortcut that was accepted, or nothing. Check :meth:`hotkey_of` to tell which.
        """
        if action not in self.hotkey_actions():
            return self.translate("hotkey.invalid")
        standard = normalise(shortcut)
        if shortcut.strip() and not standard:
            return self.translate("hotkey.invalid")
        other = conflict(self.settings, action, standard)
        if other:
            return self.translate("hotkey.conflict", action=self.action_label(other))
        self._store_hotkey(action, standard)
        self.save()
        self.refresh_hotkeys()
        self.changed.emit()
        if action in self.failed_hotkeys:
            return self.translate("hotkey.failed")
        if standard and not has_modifier(standard):
            return self.translate("hotkey.single_key")
        return ""

    def restore_default_hotkeys(self) -> None:
        """Put every shortcut back as it was at first. Tables added by the user get none."""
        self.settings.hotkeys = dict(DEFAULT_HOTKEYS)
        defaults = [table.hotkey for table in default_tables()]
        builtin = 0
        for table in self.settings.tables:
            if table.builtin and builtin < len(defaults):
                table.hotkey = defaults[builtin]
                builtin += 1
            else:
                table.hotkey = ""
        self.save()
        self.refresh_hotkeys()
        self.changed.emit()

    def suspend_hotkeys(self, suspended: bool) -> None:
        """Stop hotkeys from firing while a new shortcut is being typed, or let them again."""
        self.hotkeys_suspended.emit(suspended)

    def run_action(self, action: str) -> bool:
        """Do what a hotkey stands for. ``action`` is a name from ``settings.hotkeys``, or
        ``table:<name>``. Returns False if there is no such action."""
        if action.startswith(TABLE_PREFIX):
            name = action[len(TABLE_PREFIX) :]
            if name not in self.settings.table_names():
                return False
            self.set_table(name)
            return True
        handlers: dict[str, Callable[[], None]] = {
            "toggle_tracking": self.toggle_tracking,
            "next_table": self.next_table,
            "toggle_overlay": self.toggle_overlay,
            "calibrate": self.calibrate,
            "open_window": self.show_window,
            "end_fight": self.end_fight,
            "discard_last": self.discard_last,
        }
        handler = handlers.get(action)
        if handler is None:
            return False
        handler()
        return True

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

    def set_overlay_position(self, position: tuple[int, int] | None) -> None:
        """Remember where the overlay was put. None puts it back where it starts."""
        if position == self.settings.overlay_position:
            return
        self.settings.overlay_position = position
        self.save()
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

    def end_fight(self) -> None:
        """End the fight in progress now. It is saved as incomplete."""
        self.end_fight_requested.emit()

    def discard_last(self) -> None:
        """Remove the most recent record. Doing it again within a few seconds puts it back."""
        undo = self._discarded is not None and self._clock() - self._discarded_at < UNDO_SECONDS
        try:
            if undo:
                self.store.append(self._discarded)
                self._discarded = None
                text = self.translate("overlay.record_restored")
            else:
                self._discarded = self.store.remove_last()
                self._discarded_at = self._clock()
                found = self._discarded is not None
                text = self.translate(
                    "overlay.record_discarded" if found else "overlay.nothing_to_discard"
                )
        except PermissionError:
            text = self.translate("overlay.records_locked")
        self.notice.emit(text)
        self.records_changed.emit()

    def open_records_file(self) -> None:
        """Open the records file in the program Windows uses for CSV files, normally Excel."""
        self.store.ensure_file()
        self._opener(self.store.path)

    def open_records_folder(self) -> None:
        self.store.path.parent.mkdir(parents=True, exist_ok=True)
        self._opener(self.store.path.parent)

    # --- windows and status ---------------------------------------------------------------------

    def show_setup(self) -> None:
        """Open the first-run setup guide."""
        self.setup_requested.emit()

    def finish_setup(self) -> None:
        """Remember that setup was finished or skipped, so it is not shown again by itself."""
        if not self.settings.setup_done:
            self.settings.setup_done = True
            self.save()

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

    def calibrate(self, region: str = "") -> None:
        """Open the calibration window. ``region`` is ``bar``, ``defeat_text`` or empty."""
        self.calibration_requested.emit(region)
