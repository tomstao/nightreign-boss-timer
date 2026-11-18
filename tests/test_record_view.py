from datetime import datetime

from nightreign_boss_timer.record_view import (
    boss_key,
    boss_label,
    character_names,
    filter_records,
    key_of,
    names_in,
    summarise,
    translations,
)
from nightreign_boss_timer.records import FightRecord, Status


def fight(
    minute: int,
    boss: str = "Tree Sentinel",
    table: str = "Arena",
    status: Status = Status.COMPLETE,
    seconds: float = 100.0,
    start: int = 100,
    level: int | None = None,
    character: str = "",
) -> FightRecord:
    return FightRecord(
        started_at=datetime(2026, 11, 17, 21, minute, 0),
        table=table,
        boss=boss,
        language="en",
        status=status,
        duration_s=seconds,
        start_hp_pct=start,
        end_hp_pct=0 if status is Status.COMPLETE else 40,
        level=level,
        character=character,
    )


RECORDS = [
    fight(1, seconds=161.3, status=Status.INCOMPLETE),
    fight(5, seconds=75.8, start=62),
    fight(9, seconds=130.0),
    fight(12, seconds=110.0),
    fight(20, boss="黄金河马", table="Normal", seconds=60.5),
    fight(30, boss="unknown", table="No-hit practice", status=Status.INCOMPLETE),
]


def test_no_filter_gives_everything_newest_first() -> None:
    shown = filter_records(RECORDS)
    assert [record.started_at.minute for record in shown] == [30, 20, 12, 9, 5, 1]


def test_filters_combine() -> None:
    assert len(filter_records(RECORDS, table="Arena")) == 4
    assert len(filter_records(RECORDS, boss="Tree Sentinel", status="incomplete")) == 1
    assert len(filter_records(RECORDS, table="Normal", boss="Tree Sentinel")) == 0
    assert [r.boss for r in filter_records(RECORDS, status="incomplete")] == [
        "unknown",
        "Tree Sentinel",
    ]


def test_search_matches_boss_table_and_date_ignoring_case() -> None:
    assert len(filter_records(RECORDS, search="tree")) == 4
    assert len(filter_records(RECORDS, search="河马")) == 1
    assert len(filter_records(RECORDS, search="NO-HIT")) == 1
    assert len(filter_records(RECORDS, search="21:20")) == 1
    assert len(filter_records(RECORDS, search="  2026-11-17 ")) == 6
    assert filter_records(RECORDS, search="nothing like this") == []


def test_summary_counts_only_comparable_times() -> None:
    summary = summarise(filter_records(RECORDS, boss="Tree Sentinel"))
    assert (summary.attempts, summary.completes) == (4, 3)
    # The fight that began at 62% is complete, but is left out of best and average.
    assert summary.best_s == 110.0
    assert summary.average_s == 120.0


def test_summary_without_a_comparable_fight() -> None:
    summary = summarise([fight(1, status=Status.INCOMPLETE), fight(2, start=50)])
    assert (summary.attempts, summary.completes) == (2, 1)
    assert summary.best_s is None
    assert summary.average_s is None
    assert summarise([]).attempts == 0


def test_names_are_sorted_without_regard_to_case() -> None:
    tables, bosses = names_in([*RECORDS, fight(40, boss="some new Boss", table="arena 2")])
    assert tables == ["Arena", "arena 2", "No-hit practice", "Normal"]
    # A known boss is listed once, under its English name, whatever language it was read in.
    assert bosses == ["Golden Hippopotamus", "some new Boss", "Tree Sentinel", "unknown"]


def test_one_boss_is_one_group_in_every_game_language() -> None:
    english, simplified, traditional = (
        fight(1, boss="Tree Sentinel"),
        fight(2, boss="大树守卫"),
        fight(3, boss="大樹守衛"),
    )
    assert {boss_key(r) for r in (english, simplified, traditional)} == {"Tree Sentinel"}
    assert key_of("大树守卫") == "Tree Sentinel"
    assert len(filter_records([english, simplified, traditional], boss="Tree Sentinel")) == 3
    # Searching finds a boss by its name in any language.
    assert len(filter_records([english, simplified, traditional], search="大树")) == 3
    assert len(filter_records([english, simplified, traditional], search="sentinel")) == 3


def test_boss_is_shown_in_the_ui_language_or_as_read() -> None:
    old_row = fight(1, boss="大树守卫")  # saved before translations were kept
    assert translations(old_row) == ("Tree Sentinel", "大树守卫", "大樹守衛")
    assert boss_label(old_row, "en") == "Tree Sentinel"
    assert boss_label(old_row, "zh_TW") == "大樹守衛"

    unlisted = fight(2, boss="某个新头目")
    assert translations(unlisted) == ("", "", "")
    assert boss_key(unlisted) == key_of("某个新头目") == "某个新头目"
    assert boss_label(unlisted, "en") == "某个新头目"


def test_search_finds_a_character_by_its_name_in_any_language() -> None:
    played = [fight(1, character="追踪者"), fight(2, character="Raider"), fight(3)]
    assert character_names(played[0]) == ("追踪者", "Wylder", "追蹤者")
    assert character_names(played[2]) == ()
    assert filter_records(played, search="wylder") == [played[0]]
    assert filter_records(played, search="追蹤") == [played[0]]
    assert filter_records(played, search="无赖") == [played[1]]
    # A name typed into the file by hand is no known character, and is found as it is.
    own = fight(4, character="My build")
    assert character_names(own) == ("My build",)
    assert filter_records([*played, own], search="my b") == [own]
