from pathlib import Path

import numpy as np
import pytest

from nightreign_boss_timer.defeat_text import measure_defeat_text

FIXTURES = Path(__file__).parent / "fixtures" / "defeat_regions.npz"

GOLD = (230, 190, 60)
BAND = (30, 30, 30)
ROWS, COLUMNS = 60, 600


def make_text(letters: int = 16, band: tuple[int, int, int] = BAND) -> np.ndarray:
    """A dark band with evenly spaced gold blocks standing in for letters."""
    region = np.full((ROWS, COLUMNS, 3), band, dtype=np.uint8)
    pitch = COLUMNS * 0.6 / letters
    for i in range(letters):
        left = round(COLUMNS * 0.2 + i * pitch)
        region[15:45, left : left + round(pitch * 0.6)] = GOLD
    return region


@pytest.fixture(scope="module")
def frames() -> dict[str, np.ndarray]:
    """Defeat text boxes cut from a real 1080p fight clip. See tests/fixtures/README.md."""
    with np.load(FIXTURES) as data:
        return {name: data[name] for name in data.files}


def test_gold_letters_on_a_dark_band_are_the_text() -> None:
    reading = measure_defeat_text(make_text())
    assert reading.visible
    assert reading.strokes == 16


def test_empty_band_is_not_the_text() -> None:
    region = np.full((ROWS, COLUMNS, 3), BAND, dtype=np.uint8)
    assert not measure_defeat_text(region).visible


def test_one_gold_blob_is_not_the_text() -> None:
    # A flare or a hit spark: plenty of gold, but one solid shape instead of letters.
    region = np.full((ROWS, COLUMNS, 3), BAND, dtype=np.uint8)
    region[10:50, 150:450] = GOLD
    reading = measure_defeat_text(region)
    assert reading.gold > 0.3
    assert not reading.visible


def test_gold_letters_on_a_bright_scene_are_not_the_text() -> None:
    assert not measure_defeat_text(make_text(band=(200, 200, 200))).visible


def test_too_few_letters_are_not_the_text() -> None:
    assert not measure_defeat_text(make_text(letters=5)).visible


def test_empty_region_is_not_the_text() -> None:
    assert not measure_defeat_text(np.zeros((0, 0, 3), dtype=np.uint8)).visible


@pytest.mark.parametrize("name", ["text_fading_in", "text_full"])
def test_real_frames_with_the_text(frames: dict[str, np.ndarray], name: str) -> None:
    assert measure_defeat_text(frames[name]).visible


@pytest.mark.parametrize("name", ["fight_start", "hit_sparks", "sparks_long", "boss_dissolving"])
def test_real_frames_without_the_text(frames: dict[str, np.ndarray], name: str) -> None:
    assert not measure_defeat_text(frames[name]).visible


def test_hit_sparks_are_gold_but_rejected(frames: dict[str, np.ndarray]) -> None:
    # This frame has more gold than the real text does. Shape is what rules it out.
    sparks = measure_defeat_text(frames["hit_sparks"])
    text = measure_defeat_text(frames["text_full"])
    assert sparks.gold > text.gold
    assert sparks.strokes < text.strokes
