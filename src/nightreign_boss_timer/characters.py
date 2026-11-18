"""The characters a player can choose (the Nightfarers), in English and both kinds of Chinese.

A record says which character the fight was played with. The record holds the name in the
language the program was set to at that time, so a file can hold one character under several
names. This module tells which character a saved name stands for and gives it in any of the
three languages. A name that is not in the list is no error: it is shown as it was saved.

The list is ``characters.json`` next to this file, one ``[English, Simplified, Traditional]``
row per character, in the order the game lists them, with the two characters of The Forsaken
Hollows last. It was taken from the game's own text (docs/observations.md says where from), so
no name in it was translated by hand.
"""

from __future__ import annotations

import json
from functools import cache
from importlib import resources

LANGUAGES = ("en", "zh_CN", "zh_TW")


def _plain(text: str) -> str:
    return "".join(text.split()).casefold()


@cache
def _rows() -> tuple[tuple[str, str, str], ...]:
    text = resources.files(__package__).joinpath("characters.json").read_text(encoding="utf-8")
    return tuple((en, zh_cn, zh_tw) for en, zh_cn, zh_tw in json.loads(text))


@cache
def _index() -> dict[str, tuple[str, str, str]]:
    return {_plain(name): row for row in _rows() for name in row}


def all_keys() -> tuple[str, ...]:
    """Every character by its English name, which is what settings and code call it."""
    return tuple(row[0] for row in _rows())


def key_of(name: str) -> str:
    """The English name of the character a name in any of the three languages stands for.

    Case and spaces do not matter. Empty for an empty name and for one that is no character.
    """
    row = _index().get(_plain(name))
    return row[0] if row else ""


def label_of(name: str, language: str) -> str:
    """A character in a language (``en``, ``zh_CN``, ``zh_TW``), from its name in any of them.

    A name that is no character, or a language that is not one of the three, gives the name
    back as it was.
    """
    row = _index().get(_plain(name))
    if row is None or language not in LANGUAGES:
        return name
    return row[LANGUAGES.index(language)]
