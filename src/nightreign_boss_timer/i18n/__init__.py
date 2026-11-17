"""Text shown to the user, in every supported language.

No user-facing text is written in code. Code asks for a key, such as ``tray.quit``, and gets the
text in the chosen language. Each language is one JSON file in this folder with the same keys.
English is the reference: a key missing from another language falls back to English, and the
tests fail until it is added.
"""

from __future__ import annotations

import json
from functools import cache
from importlib import resources

LANGUAGES = ("en", "zh_CN", "zh_TW")
FALLBACK = "en"


@cache
def load_catalogue(language: str) -> dict[str, str]:
    """All texts of one language, read from its JSON file."""
    if language not in LANGUAGES:
        raise ValueError(f"unsupported language: {language}")
    text = resources.files(__package__).joinpath(f"{language}.json").read_text(encoding="utf-8")
    return json.loads(text)


class Translator:
    """Looks texts up in one language. Change :attr:`language` to switch."""

    def __init__(self, language: str = FALLBACK) -> None:
        self.language = language if language in LANGUAGES else FALLBACK

    def __call__(self, key: str, **values: object) -> str:
        """The text for ``key``, with ``{placeholders}`` filled in from ``values``."""
        text = load_catalogue(self.language).get(key)
        if text is None:
            text = load_catalogue(FALLBACK).get(key)
        if text is None:
            return key  # visible in the UI, so a wrong key is noticed instead of crashing
        try:
            return text.format(**values)
        except (KeyError, IndexError):
            return text
