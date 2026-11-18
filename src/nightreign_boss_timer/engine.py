"""The watch loop, one step at a time.

The engine joins the pieces: find the game window, grab the watched regions, run the detectors,
feed the tracker, read the boss name, and save finished fights. It has no loop and no sleep of
its own. Whoever drives it (the command line, or a UI timer) calls :meth:`Engine.step` and waits
for the delay it returns.

It talks to the screen through a small interface, so tests can hand it made-up pixels.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from nightreign_boss_timer.defeat_text import DefeatReading, measure_defeat_text
from nightreign_boss_timer.detector import BarReading, measure_bar
from nightreign_boss_timer.level import LevelVote, find_digits
from nightreign_boss_timer.names import UNKNOWN, NameVote, language_of
from nightreign_boss_timer.ocr import TextReading
from nightreign_boss_timer.records import FightRecord, RecordStore
from nightreign_boss_timer.regions import (
    DEFAULT_BAR,
    DEFAULT_DEFEAT_TEXT,
    Box,
    bar_region,
    defeat_text_region,
    level_region,
    name_region,
)
from nightreign_boss_timer.settings import Settings
from nightreign_boss_timer.tracker import FightOutcome, FightTracker

GAME_TITLE = "ELDEN RING NIGHTREIGN"
# How long to wait before looking for the game window again.
WINDOW_RETRY_S = 2.0
# Windows smaller than this are a splash screen or a minimised window, not the game image.
MIN_WINDOW = 100


class Screen(Protocol):
    """What the engine needs from the screen."""

    def find_window(self, title: str) -> Box | None: ...

    def grab(self, box: Box) -> NDArray[np.uint8]: ...


class NameSource(Protocol):
    def read(self, region: NDArray[np.uint8], *, digits_only: bool = False) -> TextReading: ...


class State(Enum):
    PAUSED = "paused"
    NO_GAME = "no_game"
    IDLE = "idle"
    FIGHT = "fight"


@dataclass(frozen=True, slots=True)
class Snapshot:
    """What the overlay shows right now."""

    state: State
    table: str
    boss: str = UNKNOWN
    hp: float | None = None
    elapsed_s: float | None = None


@dataclass(frozen=True, slots=True)
class StepResult:
    snapshot: Snapshot
    # Set on the step that finishes a fight. ``saved`` is False if the row is being held because
    # the records file is open in another program.
    record: FightRecord | None
    saved: bool
    # How long the caller should wait before the next step.
    delay_s: float


@dataclass(frozen=True, slots=True)
class Probe:
    """One look at both watched regions, for showing the user what the tool sees."""

    # Size of the game image, to compare with the size at calibration.
    window: tuple[int, int]
    bar_image: NDArray[np.uint8]
    bar: BarReading
    text_image: NDArray[np.uint8]
    defeat: DefeatReading
    # The boss name as read just now. Empty if there is no bar, no reader, or nothing legible.
    name: str


def default_records_folder() -> Path:
    return Path.home() / "Documents" / "nightreign-boss-timer"


def records_path(settings: Settings) -> Path:
    folder = Path(settings.records_folder) if settings.records_folder else default_records_folder()
    return folder / "records.csv"


def to_record(
    outcome: FightOutcome,
    table: str,
    now: float,
    wall_now: datetime,
    boss: str = UNKNOWN,
    level: int | None = None,
) -> FightRecord:
    """Turn a tracker outcome into a row. ``now`` is the tracker's clock at ``wall_now``."""
    started = wall_now - timedelta(seconds=now - outcome.started_at)
    return FightRecord(
        started_at=started.replace(microsecond=0),
        table=table,
        boss=boss,
        language=language_of(boss),
        status=outcome.status,
        duration_s=round(outcome.duration_s, 1),
        start_hp_pct=outcome.start_hp_pct,
        end_hp_pct=outcome.end_hp_pct,
        level=level,
    )


class Engine:
    def __init__(
        self,
        settings: Settings,
        screen: Screen,
        store: RecordStore,
        reader: NameSource | None = None,
        *,
        title: str = GAME_TITLE,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self.settings = settings
        self.paused = False
        self._screen = screen
        self._store = store
        self._reader = reader
        self._title = title
        self._clock = clock
        self._wall_clock = wall_clock
        self._tracker = self._new_tracker()
        self._vote = NameVote()
        self._level = LevelVote()
        self._fight_table = settings.active_table
        self._end_requested = False

    def end_fight(self) -> None:
        """Ask for the current fight to be ended as incomplete. The next step does it."""
        self._end_requested = True

    def _new_tracker(self) -> FightTracker:
        return FightTracker(
            wait_window_s=self.settings.wait_window_s,
            skip_walk_pasts=self.settings.skip_walk_pasts,
        )

    def step(self) -> StepResult:
        """Look at the screen once."""
        settings = self.settings
        if self.paused:
            return self._result(State.PAUSED, delay=1.0 / settings.idle_rate)

        window = self._screen.find_window(self._title)
        if window is None or window.width < MIN_WINDOW or window.height < MIN_WINDOW:
            return self._result(State.NO_GAME, delay=WINDOW_RETRY_S)

        # Timing options can be changed while the tool runs. They apply from the next sample.
        self._tracker.wait_window_s = settings.wait_window_s
        self._tracker.skip_walk_pasts = settings.skip_walk_pasts

        now = self._clock()
        bar_fractions = settings.bar_region or DEFAULT_BAR
        bar = measure_bar(self._screen.grab(bar_region(window, bar_fractions)))
        defeat = False
        if self._tracker.watching_for_defeat:
            box = defeat_text_region(window, settings.defeat_text_region or DEFAULT_DEFEAT_TEXT)
            defeat = measure_defeat_text(self._screen.grab(box)).visible

        was_in_fight = self._tracker.in_fight
        if self._end_requested:
            self._end_requested = False
            outcome = self._tracker.end_now()
        else:
            outcome = self._tracker.update(now, bar, defeat)
        if self._tracker.in_fight and not was_in_fight:
            # The table is fixed when the fight starts, whatever is switched to during it.
            self._vote = NameVote()
            self._level = LevelVote()
            self._fight_table = settings.active_table

        if self._reader and self._tracker.in_fight and bar.present and not self._vote.settled:
            reading = self._reader.read(self._screen.grab(name_region(window, bar_fractions)))
            self._vote.add(reading.text, reading.confidence)
        if self._reader and self._tracker.in_fight and not self._level.settled:
            digits = find_digits(self._screen.grab(level_region(window)))
            if digits is None:
                self._level.miss()
            else:
                self._level.add(self._reader.read(digits, digits_only=True).text)

        record, saved = None, False
        if outcome:
            record = to_record(
                outcome,
                self._fight_table,
                now,
                self._wall_clock(),
                self._vote.name,
                self._level.level,
            )
            saved = self._store.append(record)

        in_fight = self._tracker.in_fight
        rate = settings.fight_rate if in_fight or bar.present else settings.idle_rate
        return self._result(
            State.FIGHT if in_fight else State.IDLE,
            delay=1.0 / rate,
            record=record,
            saved=saved,
            now=now,
        )

    def probe(self) -> Probe | None:
        """Read both regions once, outside the watch loop. None if the game window is not found.

        This is for the Regions page. It does not touch the tracker, so it can run during a fight.
        """
        window = self._screen.find_window(self._title)
        if window is None or window.width < MIN_WINDOW or window.height < MIN_WINDOW:
            return None
        settings = self.settings
        bar_fractions = settings.bar_region or DEFAULT_BAR
        bar_image = self._screen.grab(bar_region(window, bar_fractions))
        bar = measure_bar(bar_image)
        text_image = self._screen.grab(
            defeat_text_region(window, settings.defeat_text_region or DEFAULT_DEFEAT_TEXT)
        )
        name = ""
        if self._reader and bar.present:
            reading = self._reader.read(self._screen.grab(name_region(window, bar_fractions)))
            name = reading.text.strip()
        return Probe(
            (window.width, window.height),
            bar_image,
            bar,
            text_image,
            measure_defeat_text(text_image),
            name,
        )

    def _result(
        self,
        state: State,
        *,
        delay: float,
        record: FightRecord | None = None,
        saved: bool = False,
        now: float | None = None,
    ) -> StepResult:
        if state is State.FIGHT and now is not None:
            snapshot = Snapshot(
                state,
                self._fight_table,
                self._vote.name,
                self._tracker.hp,
                now - self._tracker.started_at,
            )
        else:
            snapshot = Snapshot(state, self.settings.active_table)
        return StepResult(snapshot, record, saved, delay)
