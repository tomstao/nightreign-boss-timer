"""Region calibration without any drawing: the box the user drags, and what the detectors see in it.

The user marks a box on a frozen picture of the game. This module keeps that box inside the
picture, turns it into the fractions stored in the settings file, and runs the detectors on the
picture exactly as the engine will run them on the screen, so a wrong box is caught before a
fight. Nothing here needs a window, so all of it can be tested with plain arrays.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
from numpy.typing import NDArray

from nightreign_boss_timer.defeat_text import DefeatReading, measure_defeat_text
from nightreign_boss_timer.detector import ABSENT, BarReading, measure_bar
from nightreign_boss_timer.regions import (
    DEFAULT_BAR,
    DEFAULT_DEFEAT_TEXT,
    Box,
    Fractions,
    bar_region,
    defeat_text_region,
)

# The smallest box that can be drawn, in picture pixels. Two rows is the least the settings file
# accepts for a bar, and a narrower box than this is a slip of the mouse.
MIN_WIDTH = 8
MIN_HEIGHT = 2


class RegionKind(Enum):
    BAR = "bar"
    DEFEAT_TEXT = "defeat_text"


class Corner(Enum):
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


@dataclass(frozen=True, slots=True)
class Selection:
    """A box in picture pixels. ``right`` and ``bottom`` are one past the last pixel inside."""

    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(value, high))


def fit(selection: Selection, width: int, height: int) -> Selection:
    """The nearest allowed box: corners in order, not too small, inside the picture."""
    left, right = sorted((selection.left, selection.right))
    top, bottom = sorted((selection.top, selection.bottom))
    left = _clamp(left, 0, width - MIN_WIDTH)
    top = _clamp(top, 0, height - MIN_HEIGHT)
    return Selection(
        left,
        top,
        _clamp(right, left + MIN_WIDTH, width),
        _clamp(bottom, top + MIN_HEIGHT, height),
    )


def move(selection: Selection, dx: int, dy: int, width: int, height: int) -> Selection:
    """Shift the box without changing its size, stopping at the edges of the picture."""
    dx = _clamp(dx, -selection.left, width - selection.right)
    dy = _clamp(dy, -selection.top, height - selection.bottom)
    return Selection(
        selection.left + dx, selection.top + dy, selection.right + dx, selection.bottom + dy
    )


def drag_corner(
    selection: Selection, corner: Corner, x: int, y: int, width: int, height: int
) -> Selection:
    """Put one corner at (x, y). The opposite corner stays where it is."""
    left, top, right, bottom = selection.left, selection.top, selection.right, selection.bottom
    if corner in (Corner.TOP_LEFT, Corner.BOTTOM_LEFT):
        left = _clamp(x, 0, right - MIN_WIDTH)
    else:
        right = _clamp(x, left + MIN_WIDTH, width)
    if corner in (Corner.TOP_LEFT, Corner.TOP_RIGHT):
        top = _clamp(y, 0, bottom - MIN_HEIGHT)
    else:
        bottom = _clamp(y, top + MIN_HEIGHT, height)
    return Selection(left, top, right, bottom)


def to_fractions(selection: Selection, kind: RegionKind, width: int, height: int) -> Fractions:
    """The box as stored in the settings file, for a picture of this size."""
    # The bar's bottom is stored as its last row, the text's as one past it: that is how
    # regions.py reads each of them back.
    bottom = selection.bottom - 1 if kind is RegionKind.BAR else selection.bottom
    return Fractions(
        left=round(selection.left / width, 6),
        right=round(selection.right / width, 6),
        top=round(selection.top / height, 6),
        bottom=round(bottom / height, 6),
    )


def from_fractions(fractions: Fractions, kind: RegionKind, width: int, height: int) -> Selection:
    """The box to draw for stored fractions. The reverse of :func:`to_fractions`."""
    top = round(fractions.top * height)
    bottom = round(fractions.bottom * height)
    if kind is RegionKind.BAR:
        bottom = max(top, bottom) + 1
    selection = Selection(
        round(fractions.left * width), top, round(fractions.right * width), bottom
    )
    return fit(selection, width, height)


def starting_selection(
    saved: Fractions | None, kind: RegionKind, width: int, height: int
) -> Selection:
    """The box shown when calibration opens: the saved one, or where it sits on a 16:9 picture."""
    default = DEFAULT_BAR if kind is RegionKind.BAR else DEFAULT_DEFEAT_TEXT
    return from_fractions(saved or default, kind, width, height)


def _crop(picture: NDArray[np.uint8], box: Box) -> NDArray[np.uint8] | None:
    """The pixels of ``box``, or None if any of it lies outside the picture."""
    rows, columns = picture.shape[:2]
    if box.left < 0 or box.top < 0 or box.left + box.width > columns or box.top + box.height > rows:
        return None
    return picture[box.top : box.top + box.height, box.left : box.left + box.width]


def read_bar(picture: NDArray[np.uint8], fractions: Fractions) -> BarReading:
    """What the bar detector reads in a picture of the whole game image, for these fractions."""
    rows, columns = picture.shape[:2]
    region = _crop(picture, bar_region(Box(0, 0, columns, rows), fractions))
    # The detector needs rows above and below the bar. A box too close to the edge has none.
    return ABSENT if region is None else measure_bar(region)


def read_defeat_text(picture: NDArray[np.uint8], fractions: Fractions) -> DefeatReading:
    """What the defeat text check reads in a picture of the whole game image."""
    rows, columns = picture.shape[:2]
    region = _crop(picture, defeat_text_region(Box(0, 0, columns, rows), fractions))
    return measure_defeat_text(picture[:0] if region is None else region)
