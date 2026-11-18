"""Shared set-up for UI tests: a controller that touches nothing outside a temporary folder."""

from __future__ import annotations

from pathlib import Path

from nightreign_boss_timer.i18n import Translator
from nightreign_boss_timer.records import RecordStore
from nightreign_boss_timer.settings import Settings
from nightreign_boss_timer.ui.controller import Controller


class Recorder:
    """A controller with made-up surroundings, remembering what it was asked to do."""

    def __init__(self, folder: Path, language: str = "en") -> None:
        self.settings = Settings(ui_language=language)
        self.settings_path = folder / "settings.json"
        self.store = RecordStore(folder / "records" / "records.csv")
        self.opened: list[Path] = []
        self.notices: list[str] = []
        self.windows: list[str] = []
        self.changes = 0
        self.controller = Controller(
            self.settings,
            Translator(language),
            self.store,
            settings_path=self.settings_path,
            opener=self.opened.append,
        )
        self.controller.notice.connect(self.notices.append)
        self.controller.window_requested.connect(self.windows.append)
        self.controller.changed.connect(self._changed)

    def _changed(self) -> None:
        self.changes += 1
