"""Find the boss health bar in a strip of screen pixels and read how full it is.

The detector looks at the calibrated bar box plus some rows above and below it. Each pixel
column is classified as one of:

- fill:  the red part of the bar. Red inside the box, and not red just above and below it, which
         is what separates a thin bar from a red object in the scene. Under a dark popup the
         fill is dim, and counts when it is much redder than the scene beside it.
- track: the empty part of the bar. A see-through dark strip, so it is darker than the scene
         just above and below it.
- other: anything else, such as a popup or an effect drawn over the bar.

A bar that is ``p`` full is fill up to ``p`` and track after it. The detector finds the split
point that agrees with the most columns. How well the best split explains the strip decides
whether a bar is there at all, so presence and HP come from the same fit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

# The region handed to the detector is the bar box grown by this many bar-heights on each side.
MARGIN_HEIGHTS = 2

# Fill colour: a dark brownish red whose brightness changes with the scene, so the test compares
# channels instead of using a fixed brightness. Values come from docs/observations.md.
RED_MIN = 60
RED_OVER_GREEN = 1.5
RED_OVER_BLUE = 1.9

# A column counts as fill when this share of its rows inside the box is red...
FILL_ROWS_MIN = 0.6
# ...and at most this share of its rows outside the box is red...
OUTSIDE_RED_MAX = 0.34
# ...or, when the scene around the bar is red too, the box is this much darker than the scene.
# A hit flash turns the whole screen orange-red, and the bar stays a darker strip inside it.
FILL_CONTRAST_MAX = 0.75
# A skill popup or a menu draws a dark see-through layer over the bar. The fill under it is too
# dark and too blue for the colour test above (about (49, 26, 30)), but red still leads the other
# two channels by this ratio...
DIM_RED_MIN = 30
DIM_RED_OVER_OTHERS = 1.4
# ...and the column is that many times redder than the scene beside it. The empty track never
# is: it is see-through, so in a red scene it turns as red as the scene and no redder.
DIM_REDDER_THAN_OUTSIDE = 1.4

# Track: the empty part of the bar is a see-through dark strip. It is darker than its
# surroundings by this ratio...
TRACK_CONTRAST_MAX = 0.8
# ...and either dark and nearly colourless, as over a normal scene...
TRACK_BRIGHTNESS_MAX = 110
TRACK_COLOUR_SPREAD_MAX = 30
# ...or, over a bright flash that tints it, much darker than the flash and less colourful.
TRACK_STRONG_CONTRAST_MAX = 0.65
TRACK_SPREAD_OF_OUTSIDE_MAX = 0.75

# A bar is present when the best split explains at least this share of the columns.
PRESENT_SCORE_MIN = 0.6


@dataclass(frozen=True, slots=True)
class BarReading:
    """What one frame shows.

    ``hp`` is where the visible red ends, from 0.0 to 1.0. ``hp_high`` is the furthest the fill
    could reach given what the frame shows. The two are normally within about 0.02 of each other,
    the width of the faded end of the fill. They are far apart when something covers the end of
    the fill, and the true level is then somewhere between them. Both are 0.0 when no bar is
    present.
    """

    present: bool
    hp: float
    hp_high: float
    score: float


ABSENT = BarReading(present=False, hp=0.0, hp_high=0.0, score=0.0)


def grow_box(top: int, bottom: int) -> tuple[int, int]:
    """Rows of the region to capture for a bar whose fill spans ``top`` to ``bottom`` inclusive."""
    margin = (bottom - top + 1) * MARGIN_HEIGHTS
    return top - margin, bottom + margin


def _red(pixels: NDArray[np.int32]) -> NDArray[np.bool_]:
    r, g, b = pixels[..., 0], pixels[..., 1], pixels[..., 2]
    return (r > RED_MIN) & (r > g * RED_OVER_GREEN) & (r > b * RED_OVER_BLUE)


def measure_bar(region: NDArray[np.uint8]) -> BarReading:
    """Read the bar from an RGB region produced with :func:`grow_box`.

    ``region`` has shape (rows, columns, 3). The bar box is the middle fifth of its rows.
    """
    rows, columns, _ = region.shape
    height = rows // (1 + 2 * MARGIN_HEIGHTS)
    if height < 1 or columns < 1:
        return ABSENT
    pixels = region.astype(np.int32)
    top = height * MARGIN_HEIGHTS
    box = pixels[top : top + height]
    # Skip the rows touching the box: they hold the bar's soft edge and its bright lower rim.
    gap = max(1, round(height * 0.7))
    outside = np.concatenate([pixels[: top - gap], pixels[top + height + gap :]])

    box_brightness = box.mean(axis=(0, 2))
    outside_brightness = outside.mean(axis=(0, 2))
    spread = (box.max(axis=2) - box.min(axis=2)).mean(axis=0)
    outside_spread = (outside.max(axis=2) - outside.min(axis=2)).mean(axis=0)

    fill = (_red(box).mean(axis=0) >= FILL_ROWS_MIN) & (
        (_red(outside).mean(axis=0) <= OUTSIDE_RED_MAX)
        | (box_brightness < outside_brightness * FILL_CONTRAST_MAX)
    )

    # Dimmed fill. The comparison with the scene is cross-multiplied so nothing is divided.
    r, g, b = box[..., 0], box[..., 1], box[..., 2]
    dim = (r > DIM_RED_MIN) & (r > g * DIM_RED_OVER_OTHERS) & (r > b * DIM_RED_OVER_OTHERS)
    box_r, box_g, box_b = box.mean(axis=0).T
    out_r, out_g, out_b = outside.mean(axis=0).T
    fill |= (
        (dim.mean(axis=0) >= FILL_ROWS_MIN)
        & (box_r * out_g > DIM_REDDER_THAN_OUTSIDE * box_g * out_r)
        & (box_r * out_b > DIM_REDDER_THAN_OUTSIDE * box_b * out_r)
    )

    plain = (box_brightness < TRACK_BRIGHTNESS_MAX) & (spread < TRACK_COLOUR_SPREAD_MAX)
    tinted = (box_brightness < outside_brightness * TRACK_STRONG_CONTRAST_MAX) & (
        spread < outside_spread * TRACK_SPREAD_OF_OUTSIDE_MAX
    )
    track = ~fill & (plain | tinted) & (box_brightness < outside_brightness * TRACK_CONTRAST_MAX)

    # vote[i] is +1 if column i says "the bar is full here" and -1 if it says "empty here".
    vote = fill.astype(np.int32) - track.astype(np.int32)
    # score[x] = agreement if the fill ends at column x: fill votes left of x, track votes right.
    left = np.concatenate([[0], np.cumsum(vote)])
    score = left + (left - left[-1])
    best = int(score.max())
    if best < PRESENT_SCORE_MIN * columns:
        return ABSENT
    winners = np.flatnonzero(score == best)
    return BarReading(
        present=True,
        hp=float(winners[0]) / columns,
        hp_high=float(winners[-1]) / columns,
        score=best / columns,
    )
