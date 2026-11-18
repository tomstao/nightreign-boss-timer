from pathlib import Path

import numpy as np
import pytest

from nightreign_boss_timer.level import LevelVote, find_digits, parse_level
from nightreign_boss_timer.ocr import NameReader, default_model_path
from nightreign_boss_timer.regions import Box, level_region

FIXTURES = Path(__file__).parent / "fixtures" / "level_regions.npz"

needs_model = pytest.mark.skipif(
    not default_model_path().exists(),
    reason="OCR model not downloaded; run tools/fetch_model.py",
)


@pytest.fixture(scope="module")
def regions() -> dict[str, np.ndarray]:
    """Level boxes cut from real footage. See tests/fixtures/README.md."""
    with np.load(FIXTURES) as data:
        return {name: data[name] for name in data.files}


def emblem_with_digit() -> np.ndarray:
    """A dark blue box with thin pale-blue lines and one solid white block for a digit."""
    region = np.full((43, 54, 3), (20, 30, 60), dtype=np.uint8)
    region[:, 10] = region[:, 44] = (150, 190, 255)
    region[8] = (150, 190, 255)
    region[14:30, 22:32] = (235, 235, 235)
    return region


def test_level_region_at_1080p_is_the_middle_of_the_emblem() -> None:
    assert level_region(Box(0, 0, 1920, 1080)) == Box(78, 33, 54, 43)
    assert level_region(Box(100, 50, 2560, 1440)) == Box(204, 94, 72, 57)


def test_digits_are_cut_out_with_some_room_and_the_lines_are_left() -> None:
    cut = find_digits(emblem_with_digit())
    assert cut is not None
    # The block is 16 rows by 10 columns. Room around it is 0.3 of its height: 5 pixels.
    assert cut.shape == (26, 20, 3)
    assert (cut[5:21, 5:15] == 235).all()


def test_no_digits_in_a_box_without_white() -> None:
    region = emblem_with_digit()
    region[14:30, 22:32] = (20, 30, 60)
    assert find_digits(region) is None
    assert find_digits(np.zeros((43, 54, 3), dtype=np.uint8)) is None
    assert find_digits(np.zeros((0, 0, 3), dtype=np.uint8)) is None


def test_thin_white_lines_alone_are_not_digits() -> None:
    region = np.full((43, 54, 3), (20, 30, 60), dtype=np.uint8)
    region[:, 20] = region[21] = (240, 240, 240)
    assert find_digits(region) is None


def test_only_levels_the_game_has_are_accepted() -> None:
    assert parse_level("7") == 7
    assert parse_level("15") == 15
    assert parse_level("0") is None
    assert parse_level("16") is None
    assert parse_level("") is None
    assert parse_level("7a") is None


def test_vote_settles_on_the_most_common_level() -> None:
    vote = LevelVote()
    assert vote.level is None
    for text in ("15", "2", "15"):
        vote.add(text)
        assert not vote.settled
    vote.add("15")
    assert vote.settled
    assert vote.level == 15


def test_vote_gives_up_after_enough_unusable_readings() -> None:
    vote = LevelVote()
    for _ in range(8):
        vote.add("")
    assert vote.settled
    assert vote.level is None


def test_no_emblem_frame_has_no_digits(regions: dict[str, np.ndarray]) -> None:
    assert find_digits(regions["no_emblem"]) is None


@needs_model
@pytest.mark.parametrize(
    ("name", "level"),
    [
        ("level_2", 2),
        ("level_7", 7),
        ("level_7_bright_scene", 7),
        ("level_8", 8),
        ("level_15", 15),
        ("level_15_at_1440p", 15),
    ],
)
def test_real_levels_are_read(regions: dict[str, np.ndarray], name: str, level: int) -> None:
    digits = find_digits(regions[name])
    assert digits is not None
    reading = NameReader().read(digits, digits_only=True)
    assert parse_level(reading.text) == level


@needs_model
def test_digits_only_never_answers_with_letters(regions: dict[str, np.ndarray]) -> None:
    # The whole box, emblem lines and all, reads as letters or signs without the limit.
    text = NameReader().read(regions["no_emblem"], digits_only=True).text
    assert text == "" or text.isdecimal()
