from datetime import datetime

from nightreign_boss_timer.__main__ import describe
from nightreign_boss_timer.engine import to_record
from nightreign_boss_timer.records import FightRecord, Status
from nightreign_boss_timer.regions import Box, bar_region, defeat_text_region, name_region
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
    assert (record.boss, record.language) == ("unknown", "")
    assert record.duration_s == 60.3
    assert (record.status, record.start_hp_pct, record.end_hp_pct) == (Status.COMPLETE, 100, 0)


def test_describe_is_one_readable_line() -> None:
    outcome = FightOutcome(1000.0, 161.3, Status.INCOMPLETE, 100, 62)
    record = to_record(outcome, "Arena", 1170.0, datetime(2026, 11, 17, 21, 7, 23))
    assert describe(record) == "21:04:33  incomplete  02:41.3  HP 100% -> 62%  unknown"


OUTCOME = FightOutcome(1000.0, 60.0, Status.COMPLETE, 100, 0)
WHEN = datetime(2026, 11, 17, 21, 5, 40)


def names_of(record: FightRecord) -> list[tuple[str, str]]:
    pairs = [
        (record.boss, record.language),
        (record.boss_2, record.language_2),
        (record.boss_3, record.language_3),
    ]
    return [pair for pair in pairs if pair != ("", "")]


def test_boss_is_saved_in_the_one_language_asked_for() -> None:
    # The game is in Simplified Chinese and the program in English.
    record = to_record(OUTCOME, "Arena", 1067.0, WHEN, "黄金河马", languages=["en"])
    assert names_of(record) == [("Golden Hippopotamus", "en")]


def test_boss_is_saved_in_up_to_three_languages_in_the_order_asked_for() -> None:
    two = to_record(OUTCOME, "Arena", 1067.0, WHEN, "黄金河马", languages=["en", "zh_CN"])
    assert names_of(two) == [("Golden Hippopotamus", "en"), ("黄金河马", "zh_CN")]
    three = to_record(
        OUTCOME, "Arena", 1067.0, WHEN, "Tree Sentinel", languages=["en", "zh_CN", "zh_TW"]
    )
    assert names_of(three) == [
        ("Tree Sentinel", "en"),
        ("大树守卫", "zh_CN"),
        ("大樹守衛", "zh_TW"),
    ]
    # A fourth language would be one name too many for a record.
    four = to_record(
        OUTCOME, "Arena", 1067.0, WHEN, "Tree Sentinel", languages=["zh_TW", "en", "zh_CN", "en"]
    )
    assert names_of(four) == [("大樹守衛", "zh_TW"), ("Tree Sentinel", "en"), ("大树守卫", "zh_CN")]


def test_with_no_language_asked_for_the_name_is_saved_as_the_game_writes_it() -> None:
    record = to_record(OUTCOME, "Arena", 1067.0, WHEN, "黄金河马")
    assert names_of(record) == [("黄金河马", "zh_CN")]
    same_in_both = to_record(OUTCOME, "Arena", 1067.0, WHEN, "王室幽魂")
    assert names_of(same_in_both) == [("王室幽魂", "zh")]


def test_misread_name_is_repaired_and_an_unlisted_name_is_kept_as_read() -> None:
    repaired = to_record(
        OUTCOME, "Arena", 1067.0, WHEN, "卡利亚禁卫骑土", languages=["zh_CN", "en"]
    )
    assert names_of(repaired) == [("卡利亚禁卫骑士", "zh_CN"), ("Royal Carian Knight", "en")]

    # Not a known boss: the text read from the screen is all there is, whatever was asked for.
    unlisted = to_record(OUTCOME, "Arena", 1067.0, WHEN, "某个新头目", languages=["en", "zh_TW"])
    assert names_of(unlisted) == [("某个新头目", "zh")]
    unread = to_record(OUTCOME, "Arena", 1067.0, WHEN, languages=["en"])
    assert names_of(unread) == [("unknown", "")]


def test_name_region_covers_the_measured_name_at_1440p() -> None:
    # Measured on a 1440p screenshot: text rows 1096..1124, starting at column 618.
    region = name_region(Box(0, 0, 2560, 1440))
    assert region.left <= 618
    assert region.top <= 1096
    assert region.top + region.height >= 1124
    assert region.top + region.height <= 1142  # stays above the bar itself


def test_name_region_at_1080p_is_a_thin_strip_above_the_bar() -> None:
    region = name_region(Box(0, 0, 1920, 1080))
    bar = bar_region(Box(0, 0, 1920, 1080))
    assert region.left <= bar.left
    assert 25 <= region.height <= 35
    assert region.top + region.height <= 857  # the fill starts at row 857
