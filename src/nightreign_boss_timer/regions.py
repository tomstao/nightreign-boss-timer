"""Where the watched regions are inside the game image.

Regions are stored as fractions of the game window, so they survive the window being moved. The
defaults here were measured on 16:9 screenshots (docs/observations.md) and landed exactly on the
bar at both 1440p and 1080p. They are a starting point until the user calibrates their own.
"""

from __future__ import annotations

from dataclasses import dataclass

from nightreign_boss_timer.detector import grow_box


@dataclass(frozen=True, slots=True)
class Box:
    """A rectangle in pixels. Matches capture.Region, without needing Windows to import."""

    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class Fractions:
    """A rectangle as fractions of the game image: 0.0 is the left or top edge, 1.0 the far one."""

    left: float
    right: float
    top: float
    bottom: float


DEFAULT_BAR = Fractions(left=0.2406, right=0.7559, top=0.7931, bottom=0.7993)
DEFAULT_DEFEAT_TEXT = Fractions(left=0.24, right=0.76, top=0.455, bottom=0.525)
# The middle of the level emblem in the top-left corner: 54 by 43 pixels at 1080p. The digits are
# found inside it, so it has room to spare, but a box 4 pixels larger on each side takes in
# bright parts of the emblem and the reading goes wrong (docs/observations.md).
DEFAULT_LEVEL = Fractions(left=0.0406, right=0.0688, top=0.0306, bottom=0.0704)


def bar_region(window: Box, bar: Fractions = DEFAULT_BAR) -> Box:
    """Screen pixels to grab for the bar detector: the bar box plus its margin above and below."""
    top = round(bar.top * window.height)
    bottom = max(top, round(bar.bottom * window.height))
    grown_top, grown_bottom = grow_box(top, bottom)
    left = round(bar.left * window.width)
    return Box(
        left=window.left + left,
        top=window.top + grown_top,
        width=max(1, round(bar.right * window.width) - left),
        height=grown_bottom - grown_top + 1,
    )


# The boss name sits above the left end of the bar. Measured at 1440p, where the bar is 1320
# pixels wide: the text starts level with the left edge of the bar and spans 46 to 18 pixels
# above its top. The box is a little larger, and is sized by bar width so it follows any
# calibration.
_NAME_ABOVE_FAR = 52 / 1320
_NAME_ABOVE_NEAR = 12 / 1320
_NAME_LEFT_PAD = 4 / 1320
_NAME_WIDTH = 0.45


def name_region(window: Box, bar: Fractions = DEFAULT_BAR) -> Box:
    """Screen pixels holding the boss name, worked out from where the bar is."""
    bar_left = round(bar.left * window.width)
    bar_width = max(1, round(bar.right * window.width) - bar_left)
    bar_top = round(bar.top * window.height)
    top = bar_top - round(_NAME_ABOVE_FAR * bar_width)
    bottom = bar_top - round(_NAME_ABOVE_NEAR * bar_width)
    return Box(
        left=window.left + bar_left - round(_NAME_LEFT_PAD * bar_width),
        top=window.top + top,
        width=max(1, round(_NAME_WIDTH * bar_width)),
        height=max(1, bottom - top),
    )


def defeat_text_region(window: Box, text: Fractions = DEFAULT_DEFEAT_TEXT) -> Box:
    """Screen pixels to grab for the defeat text check."""
    left = round(text.left * window.width)
    top = round(text.top * window.height)
    return Box(
        left=window.left + left,
        top=window.top + top,
        width=max(1, round(text.right * window.width) - left),
        height=max(1, round(text.bottom * window.height) - top),
    )


def level_region(window: Box, level: Fractions = DEFAULT_LEVEL) -> Box:
    """Screen pixels holding the player's level, in the emblem at the top left."""
    left = round(level.left * window.width)
    top = round(level.top * window.height)
    return Box(
        left=window.left + left,
        top=window.top + top,
        width=max(1, round(level.right * window.width) - left),
        height=max(1, round(level.bottom * window.height) - top),
    )
