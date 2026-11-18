"""Shortcuts such as ``Ctrl+Alt+P``: reading them, checking them, and keeping them registered.

A shortcut is stored as text in the settings file. This module turns that text into the numbers
Windows wants, spots two actions sharing one shortcut, and keeps the set of registered hotkeys
in step with the settings. It never talks to Windows itself: the two functions that do are
handed in, so everything here can be tested without registering a real hotkey.

Hotkeys are system-wide. Nothing is hooked inside the game.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from nightreign_boss_timer.settings import Settings

# Modifier names in the order they are written, with the flag Windows uses for each.
MODIFIERS = {"Ctrl": 0x0002, "Alt": 0x0001, "Shift": 0x0004, "Win": 0x0008}

# Key names and their Windows virtual-key codes. Letters and digits use their own character code.
_NAMED_KEYS = {
    "Space": 0x20,
    "PageUp": 0x21,
    "PageDown": 0x22,
    "End": 0x23,
    "Home": 0x24,
    "Left": 0x25,
    "Up": 0x26,
    "Right": 0x27,
    "Down": 0x28,
    "Insert": 0x2D,
    "Delete": 0x2E,
    "Pause": 0x13,
    ";": 0xBA,
    "=": 0xBB,
    ",": 0xBC,
    "-": 0xBD,
    ".": 0xBE,
    "/": 0xBF,
    "`": 0xC0,
    "[": 0xDB,
    "\\": 0xDC,
    "]": 0xDD,
    "'": 0xDE,
}
KEYS: dict[str, int] = {
    **{chr(code): code for code in range(ord("A"), ord("Z") + 1)},
    **{chr(code): code for code in range(ord("0"), ord("9") + 1)},
    **{f"F{number}": 0x6F + number for number in range(1, 25)},
    **{f"Num{number}": 0x60 + number for number in range(10)},
    **_NAMED_KEYS,
}
_KEY_BY_FOLDED_NAME = {name.casefold(): name for name in KEYS}
_MODIFIER_BY_FOLDED_NAME = {name.casefold(): name for name in MODIFIERS}

# The id of the action that switches to a table is this followed by the table's name.
TABLE_PREFIX = "table:"


@dataclass(frozen=True, slots=True)
class Hotkey:
    """A shortcut as Windows wants it."""

    modifiers: int
    key: int


def normalise(shortcut: str) -> str:
    """The shortcut written the standard way, such as ``Ctrl+Alt+P``. Empty if it is not one.

    Case and spaces do not matter on the way in. A shortcut needs exactly one key that is not a
    modifier. Modifiers alone, or two keys, are not a shortcut.
    """
    modifiers: set[str] = set()
    key = ""
    # "+" separates the parts. No key is named "+": the key beside Backspace is written "=".
    for part in shortcut.split("+"):
        folded = part.strip().casefold()
        if folded in _MODIFIER_BY_FOLDED_NAME:
            modifiers.add(_MODIFIER_BY_FOLDED_NAME[folded])
        elif folded in _KEY_BY_FOLDED_NAME and not key:
            key = _KEY_BY_FOLDED_NAME[folded]
        else:
            return ""
    if not key:
        return ""
    return "+".join([name for name in MODIFIERS if name in modifiers] + [key])


def parse(shortcut: str) -> Hotkey | None:
    """The numbers for a shortcut, or None if the text is not a shortcut."""
    standard = normalise(shortcut)
    if not standard:
        return None
    *modifiers, key = standard.split("+")
    flags = 0
    for name in modifiers:
        flags |= MODIFIERS[name]
    return Hotkey(flags, KEYS[key])


def has_modifier(shortcut: str) -> bool:
    """False for a single key such as ``F5``. Such a hotkey takes that key away from the game."""
    hotkey = parse(shortcut)
    return hotkey is not None and hotkey.modifiers != 0


def bindings(settings: Settings) -> dict[str, str]:
    """Every action that has a shortcut, with the shortcut written the standard way.

    Actions are the names in ``settings.hotkeys``, and ``table:<name>`` for each table.
    Unreadable shortcuts are left out.
    """
    wanted = dict(settings.hotkeys)
    wanted.update({TABLE_PREFIX + table.name: table.hotkey for table in settings.tables})
    result = {}
    for action, shortcut in wanted.items():
        standard = normalise(shortcut)
        if standard:
            result[action] = standard
    return result


def conflict(settings: Settings, action: str, shortcut: str) -> str:
    """The other action that already uses this shortcut, or nothing."""
    standard = normalise(shortcut)
    if not standard:
        return ""
    for other, taken in bindings(settings).items():
        if other != action and taken == standard:
            return other
    return ""


class HotkeyManager:
    """Keeps Windows' registered hotkeys equal to a set of bindings.

    ``register(id, hotkey)`` asks Windows for a hotkey and returns whether it was granted.
    ``unregister(id)`` gives it back. When Windows reports that hotkey ``id`` was pressed, pass
    the id to :meth:`action_for`.
    """

    def __init__(
        self,
        register: Callable[[int, Hotkey], bool],
        unregister: Callable[[int], None],
    ) -> None:
        self._register = register
        self._unregister = unregister
        self._actions: dict[int, str] = {}
        self._shortcuts: dict[str, str] = {}
        self._next_id = 1
        # Actions whose shortcut Windows refused, usually because another program has it.
        self.failed: set[str] = set()

    def apply(self, wanted: dict[str, str]) -> None:
        """Register what is new or changed, and release what is gone. ``wanted`` maps action
        to shortcut, as :func:`bindings` returns it."""
        for hotkey_id, action in list(self._actions.items()):
            if wanted.get(action) != self._shortcuts[action]:
                self._unregister(hotkey_id)
                del self._actions[hotkey_id]
                del self._shortcuts[action]
        self.failed &= set(wanted)
        for action, shortcut in wanted.items():
            if action in self._shortcuts:
                continue  # already registered with this shortcut
            hotkey = parse(shortcut)
            if hotkey is None:
                continue
            hotkey_id = self._next_id
            self._next_id += 1
            if self._register(hotkey_id, hotkey):
                self._actions[hotkey_id] = action
                self._shortcuts[action] = shortcut
                self.failed.discard(action)
            else:
                self.failed.add(action)

    def action_for(self, hotkey_id: int) -> str:
        """The action a pressed hotkey stands for, or nothing if the id is not ours."""
        return self._actions.get(hotkey_id, "")

    def release_all(self) -> None:
        self.apply({})
