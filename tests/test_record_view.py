from datetime import datetime

from nightreign_boss_timer.record_view import filter_records, names_in, summarise
from nightreign_boss_timer.records import FightRecord, Status


def fight(
    minute: int,
    boss: str = "Tree Sentinel",
    table: str = "Arena",
    status: Status = Status.COMPLETE,
    seconds: float = 100.0,
    start: int = 100,
    level: int | None = None,
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
    tables, bosses = names_in([*RECORDS, fight(40, boss="ancient Dragon", table="arena 2")])
    assert tables == ["Arena", "arena 2", "No-hit practice", "Normal"]
    assert bosses == ["ancient Dragon", "Tree Sentinel", "unknown", "黄金河马"]
