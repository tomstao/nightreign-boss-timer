from datetime import datetime

from nightreign_boss_timer.__main__ import describe, to_record
from nightreign_boss_timer.records import Status
from nightreign_boss_timer.regions import Box, bar_region, defeat_text_region
from nightreign_boss_timer.tracker import FightOutcome


def test_default_bar_region_at_1080p_matches_the_measured_bar() -> None:
    # Measured on a 1080p clip: fill rows 857..863, columns 462..1451 (docs/observations.md).
    region = bar_region(Box(left=0, top=0, width=1920, height=1080))
    assert (region.left, region.width) == (462, 989)
    assert (region.top, region.height) == (843, 35)  # rows 843..877


def test_regions_follow_the_window_position() -> None:
    at_origin = bar_region(Box(0, 0, 1920, 1080))
    moved = bar_region(Box(100, 50, 1920, 1080))
    assert (moved.left - at_origin.left, moved.top - at_origin.top) == (100, 50)
    assert (moved.width, moved.height) == (at_origin.width, at_origin.height)


def test_defeat_text_region_is_in_the_middle_of_the_screen() -> None:
    region = defeat_text_region(Box(0, 0, 2560, 1440))
    assert region.left + region.width / 2 == 1280
    assert region.top < 720 < region.top + region.height


def test_tiny_window_still_gives_a_usable_region() -> None:
    region = bar_region(Box(0, 0, 200, 100))
    assert region.width >= 1
    assert region.height >= 5


def test_outcome_becomes_a_record_with_the_wall_clock_start() -> None:
    outcome = FightOutcome(
        started_at=1000.0,
        duration_s=60.348,
        status=Status.COMPLETE,
        start_hp_pct=100,
        end_hp_pct=0,
    )
    # The outcome is emitted 67 s after the fight began, at 21:05:40 on the wall clock.
    record = to_record(outcome, "Arena", now=1067.0, wall_now=datetime(2026, 11, 17, 21, 5, 40))

    assert record.started_at == datetime(2026, 11, 17, 21, 4, 33)
    assert record.table == "Arena"
    assert record.boss == "unknown"
    assert record.duration_s == 60.3
    assert (record.status, record.start_hp_pct, record.end_hp_pct) == (Status.COMPLETE, 100, 0)


def test_describe_is_one_readable_line() -> None:
    outcome = FightOutcome(1000.0, 161.3, Status.INCOMPLETE, 100, 62)
    record = to_record(outcome, "Arena", 1170.0, datetime(2026, 11, 17, 21, 7, 23))
    assert describe(record) == "21:04:33  incomplete  02:41.3  HP 100% -> 62%"
