"""The boss names the game uses, in English, Simplified Chinese and Traditional Chinese.

A name read from the screen is looked up here. A match gives the same boss in the other two
languages, tells which language the game is in, and repairs a reading that is one or two
characters off. A name that is not in the list is no error: the caller keeps what was read.

The list is ``boss_names.json`` next to this file, one ``[English, Simplified, Traditional]``
row per name the game has. It was taken from the game's own text (docs/observations.md says
where from), so no name in it was translated by hand.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from importlib import resources

LANGUAGES = ("en", "zh_CN", "zh_TW")
# The language of a Chinese name that is written the same in Simplified and Traditional.
CHINESE = "zh"

# How many wrong, missing or extra characters a reading may have, by the length of the name
# once spaces and punctuation are dropped. Short names get none: 白角 and 征兆 are two
# characters, and one wrong character would turn them into something else.
_NO_ERRORS_BELOW = 4
_TWO_ERRORS_FROM = 8


@dataclass(frozen=True, slots=True)
class BossMatch:
    """A boss found in the list.

    ``language`` is the language the reading was in: ``en``, ``zh_CN``, ``zh_TW``, or ``zh`` when
    the name is the same in both kinds of Chinese. ``name`` is the name in that language as the
    game writes it. A translation is empty when the list has more than one for this name: a few
    English names stand for two Chinese ones, and the other way round.
    """

    name: str
    language: str
    en: str
    zh_cn: str
    zh_tw: str


def _plain(text: str) -> str:
    """Lower case letters and digits only. Quote marks, dots and spaces are often misread."""
    return "".join(ch for ch in text.casefold() if ch.isalnum())


def _distance(a: str, b: str, limit: int) -> int:
    """How many single-character changes turn ``a`` into ``b``. Stops counting above ``limit``."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    row = list(range(len(b) + 1))
    for i, ch in enumerate(a, 1):
        new = [i]
        for j, other in enumerate(b, 1):
            new.append(min(row[j] + 1, new[j - 1] + 1, row[j - 1] + (ch != other)))
        if min(new) > limit:
            return limit + 1
        row = new
    return row[-1]


def _allowed_errors(length: int) -> int:
    if length < _NO_ERRORS_BELOW:
        return 0
    return 2 if length >= _TWO_ERRORS_FROM else 1


class BossNames:
    """The list, ready for looking names up."""

    def __init__(self, rows: list[list[str]]) -> None:
        self._rows = [tuple(row) for row in rows]
        # For each language: the plain form of a name -> the rows that have it.
        self._index: list[dict[str, list[tuple[str, ...]]]] = [{}, {}, {}]
        for row in self._rows:
            for column, name in enumerate(row):
                self._index[column].setdefault(_plain(name), []).append(row)

    def __len__(self) -> int:
        return len(self._rows)

    def lookup(self, text: str) -> BossMatch | None:
        """The boss a reading stands for, or None if it is not close to exactly one name."""
        plain = _plain(text)
        if not plain:
            return None
        found = self._find(plain)
        if found is None:
            return None
        columns, rows = found
        # A name written the same in both kinds of Chinese matches in both columns.
        language = CHINESE if len(columns) > 1 else LANGUAGES[columns[0]]

        def only(column: int) -> str:
            values = {row[column] for row in rows}
            return values.pop() if len(values) == 1 else ""

        return BossMatch(only(columns[0]), language, only(0), only(1), only(2))

    def _find(self, plain: str) -> tuple[list[int], list[tuple[str, ...]]] | None:
        exact = [column for column in range(3) if plain in self._index[column]]
        if exact:
            return exact, self._index[exact[0]][plain]
        limit = _allowed_errors(len(plain))
        if limit == 0:
            return None
        best, nearest = limit + 1, []
        for column in range(3):
            for name in self._index[column]:
                distance = _distance(plain, name, limit)
                if distance < best:
                    best, nearest = distance, [(column, name)]
                elif distance == best and distance <= limit:
                    nearest.append((column, name))
        if not nearest or len({name for _, name in nearest}) != 1:
            return None  # nothing close enough, or two different names equally close
        columns = sorted({column for column, _ in nearest})
        return columns, self._index[columns[0]][nearest[0][1]]


@cache
def load() -> BossNames:
    """The list packed with the program."""
    text = resources.files(__package__).joinpath("boss_names.json").read_text(encoding="utf-8")
    return BossNames(json.loads(text))
