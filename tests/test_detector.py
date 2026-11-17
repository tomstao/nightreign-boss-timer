from pathlib import Path

import numpy as np
import pytest

from nightreign_boss_timer.detector import MARGIN_HEIGHTS, grow_box, measure_bar

FIXTURES = Path(__file__).parent / "fixtures" / "bar_regions.npz"

# Synthetic colours, taken from docs/observations.md.
FILL = (110, 53, 24)
TRACK = (22, 22, 22)
SCENE = (70, 68, 64)
BAR_HEIGHT = 8
WIDTH = 400


def make_region(hp: float, scene: tuple[int, int, int] = SCENE) -> np.ndarray:
    """A clean bar that is ``hp`` full, with plain scene above and below it."""
    rows = BAR_HEIGHT * (1 + 2 * MARGIN_HEIGHTS)
    region = np.empty((rows, WIDTH, 3), dtype=np.uint8)
    region[:] = scene
    top = BAR_HEIGHT * MARGIN_HEIGHTS
    end = round(WIDTH * hp)
    region[top : top + BAR_HEIGHT, :end] = FILL
    region[top : top + BAR_HEIGHT, end:] = TRACK
    return region


@pytest.fixture(scope="module")
def frames() -> dict[str, np.ndarray]:
    """Bar regions cut from a real 1080p fight clip. See tests/fixtures/README.md."""
    with np.load(FIXTURES) as data:
        return {name: data[name] for name in data.files}


def test_grow_box_adds_margin_on_both_sides() -> None:
    assert grow_box(857, 863) == (843, 877)


@pytest.mark.parametrize("hp", [0.0, 0.05, 0.37, 0.5, 0.99, 1.0])
def test_reads_a_clean_bar(hp: float) -> None:
    reading = measure_bar(make_region(hp))
    assert reading.present
    assert reading.hp == pytest.approx(hp, abs=0.005)
    assert reading.hp_high == pytest.approx(hp, abs=0.005)


def test_plain_scene_has_no_bar() -> None:
    rows = BAR_HEIGHT * (1 + 2 * MARGIN_HEIGHTS)
    region = np.full((rows, WIDTH, 3), SCENE, dtype=np.uint8)
    assert not measure_bar(region).present


def test_dark_scene_has_no_bar() -> None:
    # Dark and colourless like the track, but no darker than its surroundings.
    rows = BAR_HEIGHT * (1 + 2 * MARGIN_HEIGHTS)
    region = np.full((rows, WIDTH, 3), TRACK, dtype=np.uint8)
    assert not measure_bar(region).present


def test_red_object_in_the_scene_is_not_a_bar() -> None:
    # Red everywhere, including above and below the box: a thing in the scene, not a thin bar.
    rows = BAR_HEIGHT * (1 + 2 * MARGIN_HEIGHTS)
    region = np.full((rows, WIDTH, 3), FILL, dtype=np.uint8)
    assert not measure_bar(region).present


def test_popup_over_the_left_end_keeps_the_reading() -> None:
    region = make_region(0.6)
    region[:, : WIDTH // 8] = (40, 45, 80)  # a HUD box drawn over the left end of the bar
    reading = measure_bar(region)
    assert reading.present
    assert reading.hp == pytest.approx(0.6, abs=0.005)


def test_covered_end_of_fill_widens_the_bounds() -> None:
    region = make_region(0.5)
    region[:, round(WIDTH * 0.4) : round(WIDTH * 0.7)] = (230, 225, 215)  # bright effect
    reading = measure_bar(region)
    assert reading.present
    assert reading.hp == pytest.approx(0.4, abs=0.005)
    assert reading.hp_high == pytest.approx(0.7, abs=0.005)


def test_empty_region_is_absent() -> None:
    assert not measure_bar(np.zeros((0, 0, 3), dtype=np.uint8)).present


@pytest.mark.parametrize("name", ["no_bar_dark", "no_bar_before", "defeat_text"])
def test_real_frames_without_a_bar(frames: dict[str, np.ndarray], name: str) -> None:
    assert not measure_bar(frames[name]).present


@pytest.mark.parametrize(
    ("name", "expected_hp"),
    [
        ("full", 0.99),
        ("popup_near_full", 0.98),  # a skill popup covers the left end of the bar
        ("half", 0.56),
        ("popup_third", 0.37),  # same popup, lower HP
        ("low", 0.14),
        ("very_low", 0.055),
        ("effect_at_one_percent", 0.01),  # a red effect crosses the bar
        ("zero", 0.0),
        ("zero_dissolving", 0.0),
    ],
)
def test_real_frames_with_a_bar(
    frames: dict[str, np.ndarray], name: str, expected_hp: float
) -> None:
    reading = measure_bar(frames[name])
    assert reading.present
    assert reading.hp == pytest.approx(expected_hp, abs=0.01)
    assert reading.hp <= reading.hp_high <= reading.hp + 0.03
