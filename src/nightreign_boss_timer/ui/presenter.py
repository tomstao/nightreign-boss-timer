"""Decide what the overlay says. No drawing here, so it can be tested without a screen."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from nightreign_boss_timer.engine import Snapshot, State
from nightreign_boss_timer.i18n import Translator
from nightreign_boss_timer.names import UNKNOWN
from nightreign_boss_timer.records import FightRecord, Status, format_duration

# How long the result of a fight stays on the overlay.
RESULT_SECONDS = 8.0


@dataclass(frozen=True, slots=True)
class OverlayText:
    """Up to three lines, or none to hide the overlay. ``warning`` asks for the attention colour."""

    lines: tuple[str, ...]
    warning: bool = False


def best_time(records: Iterable[FightRecord], boss: str, table: str) -> float | None:
    """Fastest complete fight against this boss in this table that started from full health.

    A fight resumed against a damaged boss is not comparable, so it does not count.
    """
    times = [
        r.duration_s
        for r in records
        if r.boss == boss
        and r.table == table
        and r.status is Status.COMPLETE
        and r.start_hp_pct == 100
    ]
    return min(times) if times else None


def _boss(name: str, translate: Translator) -> str:
    return translate("records.unknown_boss") if name == UNKNOWN else name


def overlay_text(
    snapshot: Snapshot,
    translate: Translator,
    *,
    result: FightRecord | None = None,
    result_age_s: float = 0.0,
    best_s: float | None = None,
) -> OverlayText:
    """What to show for the current state. ``result`` is the last finished fight, if any."""
    if snapshot.state is State.PAUSED:
        return OverlayText((translate("overlay.paused"),), warning=True)
    if snapshot.state is State.NO_GAME:
        # Nothing to draw over: an overlay floating on the desktop would only be in the way.
        return OverlayText(())

    if snapshot.state is State.FIGHT:
        elapsed = format_duration(snapshot.elapsed_s or 0.0)
        hp = (
            "" if snapshot.hp is None else translate("overlay.hp", percent=round(snapshot.hp * 100))
        )
        return OverlayText(
            (snapshot.table, _boss(snapshot.boss, translate), f"{elapsed}   {hp}".rstrip())
        )

    if result is not None and result_age_s < RESULT_SECONDS:
        status = translate(f"status.{result.status.value}")
        time_line = format_duration(result.duration_s)
        if best_s is not None:
            time_line += "   " + translate("overlay.best", time=format_duration(best_s))
        return OverlayText(
            (f"{result.table}   {status}", _boss(result.boss, translate), time_line),
            warning=result.status is Status.INCOMPLETE,
        )

    return OverlayText((translate("overlay.ready", table=snapshot.table),))
