"""Read the player's level from the emblem in the top-left corner of the game image.

The level is one or two white digits in the middle of a round blue emblem. The bright lines of
the emblem confuse a text model, and how much of them falls inside the box changes what it
reads. So the digits are found first, as the solid white shapes in the box, and only a tight
crop around them is handed to the model, which is told to answer in digits.

As with the boss name, one reading can be wrong, so a few are taken and the most common wins.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
from numpy.typing import NDArray

# The levels the game has. A reading outside them is thrown away.
MIN_LEVEL = 1
MAX_LEVEL = 15
# Stop reading once one level has been read this many times...
AGREE = 3
# ...or after this many attempts, whichever comes first.
MAX_READS = 8
# Give up after this many looks that found no digits at all: the emblem is hidden.
MAX_MISSES = 50

# White means every colour channel is high. A digit pixel is at least this share of the
# brightest white in the box. The lines of the emblem are bluer, so their lowest channel is lower.
_WHITE_SHARE = 0.72
# With no digits on screen the box holds only scenery and emblem. Its whitest pixels are then
# below this, on the 0 to 255 scale of the lowest colour channel.
_WHITE_MIN = 120
# A digit stroke is a few pixels thick: a pixel counts when this many of the nine pixels around
# and including it are white. The thin lines of the emblem do not reach it.
_SOLID_NEIGHBOURS = 6
_SOLID_PIXELS_MIN = 8
# Space left around the digits, as a share of their height. The model reads cramped text badly.
_PADDING = 0.3


def find_digits(region: NDArray[np.uint8]) -> NDArray[np.uint8] | None:
    """Cut the digits out of an RGB region of shape (rows, columns, 3). None if there are none."""
    if region.shape[0] < 3 or region.shape[1] < 3:
        return None
    white = region.min(axis=2).astype(np.int32)
    brightest = float(np.percentile(white, 99))
    if brightest < _WHITE_MIN:
        return None
    mask = white > _WHITE_SHARE * brightest
    padded = np.pad(mask.astype(np.int32), 1)
    rows, columns = mask.shape
    around = sum(padded[dy : dy + rows, dx : dx + columns] for dy in range(3) for dx in range(3))
    solid = mask & (around >= _SOLID_NEIGHBOURS)
    ys, xs = np.nonzero(solid)
    if len(ys) < _SOLID_PIXELS_MIN:
        return None
    top, bottom, left, right = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    pad = max(2, round((bottom - top) * _PADDING))
    return region[max(0, top - pad) : bottom + pad, max(0, left - pad) : right + pad]


def parse_level(text: str) -> int | None:
    """The level a reading stands for, or None if it is not one."""
    if not (text.isascii() and text.isdecimal()):
        return None
    level = int(text)
    return level if MIN_LEVEL <= level <= MAX_LEVEL else None


class LevelVote:
    """Collects level readings for one fight. Create a new one for each fight."""

    def __init__(self) -> None:
        self._votes: Counter[int] = Counter()
        self._reads = 0
        self._misses = 0

    def miss(self) -> None:
        """Note a look at the screen that found no digits to read."""
        self._misses += 1

    def add(self, text: str) -> None:
        self._reads += 1
        level = parse_level(text.strip())
        if level is not None:
            self._votes[level] += 1

    @property
    def settled(self) -> bool:
        """True when no more readings are needed."""
        if self._reads >= MAX_READS or self._misses >= MAX_MISSES:
            return True
        return bool(self._votes) and self._votes.most_common(1)[0][1] >= AGREE

    @property
    def level(self) -> int | None:
        """The most common reading so far, or None."""
        if not self._votes:
            return None
        return self._votes.most_common(1)[0][0]
