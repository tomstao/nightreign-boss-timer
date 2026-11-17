"""Tell whether the defeat text is on screen, from the pixels of its calibrated box.

The defeat text is a line of large gold letters on a dark band, the same in every game language.
It is recognised by its look and never read as text. Gold alone is not enough: hit sparks and
weapon effects in the middle of the screen are gold too. What sets the text apart is its shape,
many separate letters spread along a line with dark band between them.

One frame can still be fooled, so the caller should require the text to hold steady over several
samples before believing it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

# Gold: strong red and green, little blue. Values come from docs/observations.md.
GOLD_RED_MIN = 150
GOLD_GREEN_MIN = 110
GOLD_BLUE_MAX = 110
GOLD_RED_OVER_BLUE = 80

# Share of the box that must be gold, and share of its width the letters must span.
GOLD_MIN = 0.015
SPAN_MIN = 0.35
# Letters are separate strokes: at least this many gold runs along the line.
STROKES_MIN = 12
# The band behind the letters is dark. Mean brightness of the non-gold pixels on the text rows.
BAND_BRIGHTNESS_MAX = 120


@dataclass(frozen=True, slots=True)
class DefeatReading:
    """What one frame shows in the defeat text box."""

    visible: bool
    gold: float
    span: float
    strokes: int
    band_brightness: float


def measure_defeat_text(region: NDArray[np.uint8]) -> DefeatReading:
    """Read an RGB region of shape (rows, columns, 3) covering the defeat text box."""
    if region.size == 0:
        return DefeatReading(False, 0.0, 0.0, 0, 0.0)
    pixels = region.astype(np.int32)
    r, g, b = pixels[..., 0], pixels[..., 1], pixels[..., 2]
    gold = (
        (r > GOLD_RED_MIN)
        & (g > GOLD_GREEN_MIN)
        & (b < GOLD_BLUE_MAX)
        & (r - b > GOLD_RED_OVER_BLUE)
    )
    gold_share = float(gold.mean())

    gold_columns = gold.any(axis=0)
    span = float(gold_columns.mean())
    # Count runs of gold columns: each letter stroke starts one.
    starts = gold_columns & ~np.concatenate([[False], gold_columns[:-1]])
    strokes = int(starts.sum())

    text_rows = gold.any(axis=1)
    behind = pixels[text_rows][~gold[text_rows]]
    band_brightness = float(behind.mean()) if behind.size else 0.0

    visible = (
        gold_share >= GOLD_MIN
        and span >= SPAN_MIN
        and strokes >= STROKES_MIN
        and band_brightness <= BAND_BRIGHTNESS_MAX
    )
    return DefeatReading(visible, gold_share, span, strokes, band_brightness)
