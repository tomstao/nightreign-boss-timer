"""Settle on a boss name from several readings.

One reading can be wrong: the player character or an effect may be in front of the name. The name
is read a few times at the start of a fight and the most common answer wins.
"""

from __future__ import annotations

from collections import Counter

# Readings below this certainty are thrown away.
MIN_CONFIDENCE = 0.6
# Stop reading once one answer has been given this many times...
AGREE = 3
# ...or after this many attempts, whichever comes first.
MAX_READS = 8

UNKNOWN = "unknown"


def language_of(name: str) -> str:
    """``en`` for a name in Latin letters, ``zh`` for one in Chinese characters, else empty.

    This is the fallback for a name that is not in the list of known names. Without the list,
    Simplified cannot be told from Traditional Chinese, so both are ``zh``.
    """
    if not name or name == UNKNOWN:
        return ""
    if any("一" <= ch <= "鿿" for ch in name):
        return "zh"
    if any(ch.isascii() and ch.isalpha() for ch in name):
        return "en"
    return ""


class NameVote:
    """Collects readings for one fight. Create a new one for each fight."""

    def __init__(self) -> None:
        self._votes: Counter[str] = Counter()
        self._reads = 0

    def add(self, text: str, confidence: float) -> None:
        self._reads += 1
        text = text.strip()
        if text and confidence >= MIN_CONFIDENCE:
            self._votes[text] += 1

    @property
    def settled(self) -> bool:
        """True when no more readings are needed."""
        if self._reads >= MAX_READS:
            return True
        return bool(self._votes) and self._votes.most_common(1)[0][1] >= AGREE

    @property
    def name(self) -> str:
        """The most common reading so far, or ``unknown``."""
        if not self._votes:
            return UNKNOWN
        return self._votes.most_common(1)[0][0]
