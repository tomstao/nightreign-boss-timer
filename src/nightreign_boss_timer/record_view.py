"""Choose which records to show and sum them up. No drawing, so it is tested with plain lists."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from nightreign_boss_timer.records import FightRecord, Status

# A filter left at this value lets everything through.
ALL = ""


@dataclass(frozen=True, slots=True)
class Summary:
    """What a set of fights adds up to. The times are None when no fight qualifies."""

    attempts: int
    completes: int
    # Fastest complete fight that began at full health: a fight resumed against a damaged boss
    # is not comparable.
    best_s: float | None
    # Average over the same fights as ``best_s``.
    average_s: float | None


def filter_records(
    records: Iterable[FightRecord],
    *,
    table: str = ALL,
    boss: str = ALL,
    status: str = ALL,
    search: str = "",
) -> list[FightRecord]:
    """The records that pass every filter, newest first.

    ``status`` is ``complete`` or ``incomplete``. ``search`` matches any part of the boss name,
    the table name or the date and time, ignoring case.
    """
    needle = search.strip().casefold()
    chosen = [
        record
        for record in records
        if table in (ALL, record.table)
        and boss in (ALL, record.boss)
        and status in (ALL, record.status.value)
        and (
            not needle
            or needle in record.boss.casefold()
            or needle in record.table.casefold()
            or needle in f"{record.started_at:%Y-%m-%d %H:%M:%S}"
        )
    ]
    return sorted(chosen, key=lambda record: record.started_at, reverse=True)


def summarise(records: Iterable[FightRecord]) -> Summary:
    records = list(records)
    completes = [record for record in records if record.status is Status.COMPLETE]
    full = [record.duration_s for record in completes if record.start_hp_pct == 100]
    return Summary(
        attempts=len(records),
        completes=len(completes),
        best_s=min(full) if full else None,
        average_s=sum(full) / len(full) if full else None,
    )


def names_in(records: Iterable[FightRecord]) -> tuple[list[str], list[str]]:
    """The table names and the boss names that appear in the records, each sorted."""
    records = list(records)
    return (
        sorted({record.table for record in records}, key=str.casefold),
        sorted({record.boss for record in records}, key=str.casefold),
    )
