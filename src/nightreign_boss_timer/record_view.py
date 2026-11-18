"""Choose which records to show and sum them up. No drawing, so it is tested with plain lists."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache

from nightreign_boss_timer import boss_names
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


@cache
def _known(name: str) -> boss_names.BossMatch | None:
    return boss_names.load().lookup(name)


def translations(record: FightRecord) -> tuple[str, str, str]:
    """The boss of a record in English, Simplified and Traditional Chinese. Empty where unknown.

    Records saved before translations were kept have none, so their name is looked up now.
    """
    if record.boss_en or record.boss_zh_cn or record.boss_zh_tw:
        return record.boss_en, record.boss_zh_cn, record.boss_zh_tw
    known = _known(record.boss)
    return (known.en, known.zh_cn, known.zh_tw) if known else ("", "", "")


def key_of(name: str) -> str:
    """What a boss name is grouped under: its English name if it is known, else the name itself."""
    known = _known(name)
    return known.en if known and known.en else name


def boss_key(record: FightRecord) -> str:
    """What a record's boss is grouped under, so one boss is one group in every game language."""
    return translations(record)[0] or record.boss


def boss_label(record: FightRecord, language: str) -> str:
    """The boss of a record in a UI language (``en``, ``zh_CN``, ``zh_TW``), or as it was read."""
    en, zh_cn, zh_tw = translations(record)
    return {"en": en, "zh_CN": zh_cn, "zh_TW": zh_tw}.get(language) or record.boss


def filter_records(
    records: Iterable[FightRecord],
    *,
    table: str = ALL,
    boss: str = ALL,
    status: str = ALL,
    search: str = "",
) -> list[FightRecord]:
    """The records that pass every filter, newest first.

    ``boss`` is a :func:`boss_key`. ``status`` is ``complete`` or ``incomplete``. ``search``
    matches any part of the boss name in any language, the table name or the date and time,
    ignoring case.
    """
    needle = search.strip().casefold()
    chosen = [
        record
        for record in records
        if table in (ALL, record.table)
        and boss in (ALL, boss_key(record))
        and status in (ALL, record.status.value)
        and (
            not needle
            or needle in record.boss.casefold()
            or any(needle in name.casefold() for name in translations(record))
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
    """The table names and the boss keys that appear in the records, each sorted."""
    records = list(records)
    return (
        sorted({record.table for record in records}, key=str.casefold),
        sorted({boss_key(record) for record in records}, key=str.casefold),
    )
