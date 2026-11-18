import json
from pathlib import Path

import numpy as np
import pytest

from nightreign_boss_timer.calibration import (
    MIN_HEIGHT,
    MIN_WIDTH,
    Corner,
    RegionKind,
    Selection,
    drag_corner,
    fit,
    from_fractions,
    move,
    read_bar,
    read_defeat_text,
    starting_selection,
    to_fractions,
)
from nightreign_boss_timer.regions import DEFAULT_BAR, Box, Fractions, bar_region
from nightreign_boss_timer.settings import Settings

FIXTURES = Path(__file__).parent / "fixtures"
W, H = 1920, 1080
# Where the bar is in the 1080p clip the fixtures were cut from: 7 rows, 990 columns.
BAR = Selection(left=462, top=857, right=1452, bottom=864)
# The defeat text fixtures cover this box, with every second pixel kept.
TEXT = Selection(left=461, top=491, right=1459, bottom=567)


def frame_with_bar(name: str = "full") -> np.ndarray:
    """A whole 1080p picture, dark except for a real bar region pasted where the bar belongs."""
    with np.load(FIXTURES / "bar_regions.npz") as data:
        region = data[name]
    picture = np.full((H, W, 3), 40, dtype=np.uint8)
    picture[843 : 843 + region.shape[0], 462 : 462 + region.shape[1]] = region
    return picture


def frame_with_text(name: str = "text_full") -> np.ndarray:
    with np.load(FIXTURES / "defeat_regions.npz") as data:
        region = data[name].repeat(2, axis=0).repeat(2, axis=1)
    picture = np.full((H, W, 3), 40, dtype=np.uint8)
    picture[TEXT.top : TEXT.top + region.shape[0], TEXT.left : TEXT.left + region.shape[1]] = region
    return picture


def test_fit_orders_corners_and_keeps_the_box_inside() -> None:
    assert fit(Selection(300, 200, 100, 50), W, H) == Selection(100, 50, 300, 200)
    assert fit(Selection(-50, -20, 100, 50), W, H) == Selection(0, 0, 100, 50)
    assert fit(Selection(1800, 1000, 2500, 1500), W, H) == Selection(1800, 1000, W, H)


def test_fit_enforces_a_minimum_size() -> None:
    click = fit(Selection(500, 400, 500, 400), W, H)
    assert (click.width, click.height) == (MIN_WIDTH, MIN_HEIGHT)
    corner = fit(Selection(W, H, W, H), W, H)
    assert corner == Selection(W - MIN_WIDTH, H - MIN_HEIGHT, W, H)


def test_move_keeps_the_size_and_stops_at_the_edges() -> None:
    assert move(BAR, 5, -3, W, H) == Selection(467, 854, 1457, 861)
    left = move(BAR, -10_000, 0, W, H)
    assert (left.left, left.width, left.height) == (0, BAR.width, BAR.height)
    bottom = move(BAR, 0, 10_000, W, H)
    assert (bottom.bottom, bottom.height) == (H, BAR.height)


def test_drag_corner_moves_only_that_corner() -> None:
    assert drag_corner(BAR, Corner.TOP_LEFT, 450, 850, W, H) == Selection(450, 850, 1452, 864)
    assert drag_corner(BAR, Corner.BOTTOM_RIGHT, 1500, 870, W, H) == Selection(462, 857, 1500, 870)
    assert drag_corner(BAR, Corner.TOP_RIGHT, 1400, 860, W, H) == Selection(462, 860, 1400, 864)
    assert drag_corner(BAR, Corner.BOTTOM_LEFT, 470, 866, W, H) == Selection(470, 857, 1452, 866)


def test_drag_corner_cannot_cross_the_opposite_corner() -> None:
    crossed = drag_corner(BAR, Corner.TOP_LEFT, 1900, 1000, W, H)
    assert crossed == Selection(BAR.right - MIN_WIDTH, BAR.bottom - MIN_HEIGHT, 1452, 864)
    outside = drag_corner(BAR, Corner.BOTTOM_RIGHT, 5000, 5000, W, H)
    assert outside == Selection(462, 857, W, H)


@pytest.mark.parametrize("kind", list(RegionKind))
@pytest.mark.parametrize(
    "size", [(1280, 720), (1920, 1080), (2560, 1440), (3440, 1440), (3840, 2160)]
)
def test_fractions_round_trip_to_the_same_pixels(kind: RegionKind, size: tuple[int, int]) -> None:
    width, height = size
    for selection in (
        Selection(0, 0, MIN_WIDTH, MIN_HEIGHT),
        Selection(width // 4 + 1, height * 4 // 5 + 1, width * 3 // 4, height * 4 // 5 + 8),
        Selection(width - 301, height - 77, width, height),
    ):
        fractions = to_fractions(selection, kind, width, height)
        assert from_fractions(fractions, kind, width, height) == selection


def test_bar_fractions_make_the_engine_grab_exactly_the_marked_rows() -> None:
    fractions = to_fractions(BAR, RegionKind.BAR, W, H)
    # The bar box grown by twice its height above and below, as the detector expects.
    assert bar_region(Box(0, 0, W, H), fractions) == Box(left=462, top=843, width=990, height=35)


def test_fractions_survive_the_settings_file(tmp_path: Path) -> None:
    settings = Settings()
    settings.bar_region = to_fractions(Selection(0, 0, MIN_WIDTH, MIN_HEIGHT), RegionKind.BAR, W, H)
    settings.defeat_text_region = to_fractions(Selection(0, 0, W, H), RegionKind.DEFEAT_TEXT, W, H)
    assert Settings.from_json(json.loads(json.dumps(settings.to_json()))) == settings


def test_starting_selection_uses_the_saved_region_or_the_default() -> None:
    default = starting_selection(None, RegionKind.BAR, W, H)
    assert default == from_fractions(DEFAULT_BAR, RegionKind.BAR, W, H)
    assert abs(default.left - BAR.left) <= 1 and abs(default.top - BAR.top) <= 1
    saved = Fractions(0.1, 0.9, 0.5, 0.51)
    assert starting_selection(saved, RegionKind.BAR, W, H) == Selection(192, 540, 1728, 552)
    text = starting_selection(None, RegionKind.DEFEAT_TEXT, W, H)
    assert text == Selection(461, 491, 1459, 567)


def test_read_bar_finds_the_bar_in_a_correct_box() -> None:
    reading = read_bar(frame_with_bar("full"), to_fractions(BAR, RegionKind.BAR, W, H))
    assert reading.present
    assert reading.hp > 0.97
    half = read_bar(frame_with_bar("half"), to_fractions(BAR, RegionKind.BAR, W, H))
    assert half.present
    assert half.hp == pytest.approx(0.56, abs=0.02)


def test_read_bar_rejects_a_misplaced_box() -> None:
    picture = frame_with_bar("full")
    too_low = move(BAR, 0, 40, W, H)
    assert not read_bar(picture, to_fractions(too_low, RegionKind.BAR, W, H)).present
    with_name = Selection(BAR.left, BAR.top - 40, BAR.right, BAR.bottom)
    assert not read_bar(picture, to_fractions(with_name, RegionKind.BAR, W, H)).present
    assert not read_bar(
        frame_with_bar("no_bar_dark"), to_fractions(BAR, RegionKind.BAR, W, H)
    ).present


def test_read_bar_at_the_edge_of_the_picture_is_absent_not_an_error() -> None:
    at_bottom = Selection(462, H - 7, 1452, H)
    assert not read_bar(frame_with_bar(), to_fractions(at_bottom, RegionKind.BAR, W, H)).present


def test_read_defeat_text() -> None:
    fractions = to_fractions(TEXT, RegionKind.DEFEAT_TEXT, W, H)
    assert read_defeat_text(frame_with_text("text_full"), fractions).visible
    assert not read_defeat_text(frame_with_text("hit_sparks"), fractions).visible
    elsewhere = to_fractions(move(TEXT, 0, 300, W, H), RegionKind.DEFEAT_TEXT, W, H)
    assert not read_defeat_text(frame_with_text("text_full"), elsewhere).visible
