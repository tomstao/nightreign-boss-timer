"""The user's settings, kept in one JSON file outside the program folder.

Loading never fails: a missing file gives the defaults, a damaged file is set aside and replaced
by the defaults, and a single bad value falls back to its default while the rest is kept. Saving
writes a temporary file first and then swaps it in, so a crash cannot leave half a file.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from nightreign_boss_timer import characters
from nightreign_boss_timer.regions import Fractions

FILE_VERSION = 1
UI_LANGUAGES = ("en", "zh_CN", "zh_TW")
# The languages a boss name can be saved in, in the order they are saved, and how many of them
# one record may hold. More languages may come, but a record never holds more names than this.
NAME_LANGUAGES = ("en", "zh_CN", "zh_TW")
MAX_NAMES = 3

# Shown in this order on the Hotkeys page. An empty shortcut means "not set".
DEFAULT_HOTKEYS: dict[str, str] = {
    "toggle_tracking": "Ctrl+Alt+P",
    "next_table": "Ctrl+Alt+T",
    "toggle_overlay": "Ctrl+Alt+O",
    "calibrate": "Ctrl+Alt+C",
    "end_fight": "",
    "discard_last": "",
    "open_window": "",
}


class TableError(ValueError):
    """A table change that is not allowed.

    The message says why in plain English. ``reason`` is ``missing``, ``empty``, ``duplicate``
    or ``builtin``, and ``name`` the table it is about, so the UI can say it in its own language.
    """

    def __init__(self, message: str, reason: str, name: str = "") -> None:
        super().__init__(message)
        self.reason = reason
        self.name = name


@dataclass(slots=True)
class Table:
    """A named group of records. Built-in tables can be renamed but not deleted."""

    name: str
    builtin: bool = False
    hotkey: str = ""


def default_tables() -> list[Table]:
    return [
        Table("Arena", builtin=True, hotkey="Ctrl+Alt+1"),
        Table("Normal", builtin=True, hotkey="Ctrl+Alt+2"),
    ]


@dataclass(slots=True)
class Settings:
    ui_language: str = "en"
    # False until the first-run setup has been finished or skipped.
    setup_done: bool = False
    tables: list[Table] = field(default_factory=default_tables)
    active_table: str = "Arena"
    # Empty means the default folder under Documents.
    records_folder: str = ""
    wait_window_s: float = 8.0
    skip_walk_pasts: bool = True
    fight_rate: float = 10.0
    idle_rate: float = 2.0
    # None until the user calibrates. The size is the game window's at calibration time.
    bar_region: Fractions | None = None
    defeat_text_region: Fractions | None = None
    calibrated_size: tuple[int, int] | None = None
    # Top-left corner of the overlay on the desktop. None until the user moves it.
    overlay_position: tuple[int, int] | None = None
    # True lets screenshots and recordings show the overlay. The tool then reads it too.
    overlay_in_captures: bool = False
    # The languages the boss name is saved in, at most MAX_NAMES. Empty until the user chooses:
    # the name is then saved in the language of the UI.
    name_languages: list[str] = field(default_factory=list)
    # The character every new record gets, by its English name (see characters.py). Empty
    # until the user chooses one: records then have no character.
    default_character: str = ""
    hotkeys: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_HOTKEYS))

    # --- boss name languages ------------------------------------------------------------------

    def record_languages(self) -> list[str]:
        """The languages a boss name is saved in, in the order of the record's name columns."""
        return list(self.name_languages) or [self.ui_language]

    def set_name_language(self, language: str, on: bool) -> bool:
        """Start or stop saving the boss name in a language. False if that is not allowed.

        At least one language stays, and no more than MAX_NAMES are saved.
        """
        if language not in NAME_LANGUAGES:
            return False
        chosen = set(self.record_languages())
        if on:
            chosen.add(language)
        else:
            chosen.discard(language)
        if not chosen or len(chosen) > MAX_NAMES:
            return False
        self.name_languages = [code for code in NAME_LANGUAGES if code in chosen]
        return True

    # --- tables -----------------------------------------------------------------------------

    def table_names(self) -> list[str]:
        return [table.name for table in self.tables]

    def _find(self, name: str) -> Table:
        for table in self.tables:
            if table.name == name:
                return table
        raise TableError(f'There is no table named "{name}".', "missing", name)

    def _check_new_name(self, name: str) -> str:
        name = name.strip()
        if not name:
            raise TableError("A table needs a name.", "empty")
        if name.casefold() in (existing.casefold() for existing in self.table_names()):
            raise TableError(f'A table named "{name}" already exists.', "duplicate", name)
        return name

    def add_table(self, name: str) -> Table:
        table = Table(self._check_new_name(name))
        self.tables.append(table)
        return table

    def rename_table(self, old: str, new: str) -> None:
        table = self._find(old)
        if new.strip() == old:
            return
        table.name = self._check_new_name(new)
        if self.active_table == old:
            self.active_table = table.name

    def delete_table(self, name: str) -> None:
        table = self._find(name)
        if table.builtin:
            raise TableError(
                f'"{name}" is a built-in table. It can be renamed but not deleted.', "builtin", name
            )
        self.tables.remove(table)
        if self.active_table == name:
            self.active_table = self.tables[0].name

    def set_active_table(self, name: str) -> None:
        self.active_table = self._find(name).name

    def next_table(self) -> str:
        """Make the table after the active one active, wrapping around. Returns its name."""
        names = self.table_names()
        self.active_table = names[(names.index(self.active_table) + 1) % len(names)]
        return self.active_table

    # --- file -------------------------------------------------------------------------------

    def to_json(self) -> dict:
        def fractions(value: Fractions | None) -> list[float] | None:
            return None if value is None else [value.left, value.right, value.top, value.bottom]

        return {
            "version": FILE_VERSION,
            "ui_language": self.ui_language,
            "setup_done": self.setup_done,
            "tables": [
                {"name": t.name, "builtin": t.builtin, "hotkey": t.hotkey} for t in self.tables
            ],
            "active_table": self.active_table,
            "records_folder": self.records_folder,
            "wait_window_s": self.wait_window_s,
            "skip_walk_pasts": self.skip_walk_pasts,
            "fight_rate": self.fight_rate,
            "idle_rate": self.idle_rate,
            "bar_region": fractions(self.bar_region),
            "defeat_text_region": fractions(self.defeat_text_region),
            "calibrated_size": list(self.calibrated_size) if self.calibrated_size else None,
            "overlay_position": list(self.overlay_position) if self.overlay_position else None,
            "overlay_in_captures": self.overlay_in_captures,
            "name_languages": list(self.name_languages),
            "default_character": self.default_character,
            "hotkeys": dict(self.hotkeys),
        }

    @classmethod
    def from_json(cls, data: object) -> Settings:
        """Build settings from loaded JSON, keeping every value that is usable."""
        settings = cls()
        if not isinstance(data, dict):
            return settings

        if data.get("ui_language") in UI_LANGUAGES:
            settings.ui_language = data["ui_language"]

        settings.setup_done = data.get("setup_done") is True

        tables = _read_tables(data.get("tables"))
        if tables:
            settings.tables = tables
        active = data.get("active_table")
        settings.active_table = (
            active if active in settings.table_names() else settings.tables[0].name
        )

        if isinstance(data.get("records_folder"), str):
            settings.records_folder = data["records_folder"]
        settings.wait_window_s = _number(data.get("wait_window_s"), 8.0, low=1.0, high=120.0)
        if isinstance(data.get("skip_walk_pasts"), bool):
            settings.skip_walk_pasts = data["skip_walk_pasts"]
        settings.fight_rate = _number(data.get("fight_rate"), 10.0, low=1.0, high=30.0)
        settings.idle_rate = _number(data.get("idle_rate"), 2.0, low=0.5, high=10.0)

        settings.bar_region = _read_fractions(data.get("bar_region"))
        settings.defeat_text_region = _read_fractions(data.get("defeat_text_region"))
        size = data.get("calibrated_size")
        if (
            isinstance(size, list)
            and len(size) == 2
            and all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in size)
        ):
            settings.calibrated_size = (size[0], size[1])

        position = data.get("overlay_position")
        if (
            isinstance(position, list)
            and len(position) == 2
            and all(isinstance(v, int) and not isinstance(v, bool) for v in position)
        ):
            # A second monitor can be to the left or above, so negative values are fine.
            settings.overlay_position = (position[0], position[1])

        settings.overlay_in_captures = data.get("overlay_in_captures") is True

        languages = data.get("name_languages")
        if isinstance(languages, list):
            chosen = [code for code in NAME_LANGUAGES if code in languages]
            settings.name_languages = chosen[:MAX_NAMES]

        character = data.get("default_character")
        if isinstance(character, str) and character in characters.all_keys():
            settings.default_character = character

        hotkeys = data.get("hotkeys")
        if isinstance(hotkeys, dict):
            for action in DEFAULT_HOTKEYS:
                if isinstance(hotkeys.get(action), str):
                    settings.hotkeys[action] = hotkeys[action]
        return settings


def _number(value: object, default: float, *, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return default
    return float(value) if low <= value <= high else default


def _read_fractions(value: object) -> Fractions | None:
    if not (isinstance(value, list) and len(value) == 4):
        return None
    if not all(isinstance(v, int | float) and not isinstance(v, bool) for v in value):
        return None
    left, right, top, bottom = (float(v) for v in value)
    if not (0.0 <= left < right <= 1.0 and 0.0 <= top < bottom <= 1.0):
        return None
    return Fractions(left, right, top, bottom)


def _read_tables(value: object) -> list[Table]:
    """Usable tables from the file. Empty if the list is missing or holds nothing usable."""
    tables: list[Table] = []
    seen: set[str] = set()
    if not isinstance(value, list):
        return tables
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        name = item["name"].strip()
        if not name or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        hotkey = item.get("hotkey")
        tables.append(
            Table(name, item.get("builtin") is True, hotkey if isinstance(hotkey, str) else "")
        )
    return tables


def default_settings_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    return Path(base) / "nightreign-boss-timer" / "settings.json"


def load(path: Path | None = None) -> Settings:
    """Read the settings file. Never raises for a missing or damaged file."""
    path = path or default_settings_path()
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Settings()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Keep the damaged file for the user to look at, and carry on with defaults.
        path.replace(path.with_suffix(".damaged.json"))
        return Settings()
    return Settings.from_json(data)


def save(settings: Settings, path: Path | None = None) -> None:
    path = path or default_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".tmp")
    partial.write_text(
        json.dumps(settings.to_json(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    partial.replace(path)
