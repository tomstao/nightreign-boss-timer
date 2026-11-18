"""Turn a stream of per-frame readings into fight outcomes.

This is the recording rules from docs/PLAN.md as a state machine. It does no screen capture and
no file writing: the caller feeds it one sample at a time and gets an outcome back when a fight
ends.

    idle --bar seen--> pending --bar held--> fighting --bar gone--> waiting
                                                 ^                      |
                                                 +------bar back--------+

While waiting, defeat text that holds makes the fight complete, provided the boss was nearly dead
when the bar was last read. When the wait window runs out, the fight is complete if the bar had
been empty for a while when it went away, and incomplete otherwise. A fight in which the boss HP
never moved is dropped as a walk-past.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum, auto

from nightreign_boss_timer.detector import BarReading
from nightreign_boss_timer.records import Status

# A bar must stay on screen this long before it counts as a fight.
CONFIRM_S = 0.3
# After the bar disappears, how long to wait for the defeat text or for the bar to come back.
WAIT_WINDOW_S = 8.0
# A bar that is still being confirmed may drop out for this long without starting over.
PENDING_GAP_S = 0.3
# The defeat text must stay visible this long. Hit flashes fill the middle of the screen with
# gold for up to about 0.3 s, and hide the bar at the same moment.
DEFEAT_HOLD_S = 0.8
# Defeat text only counts if the boss was nearly dead when the bar was last read.
KILL_HP_MAX = 0.10
# A reading is trusted for HP when its two bounds are this close. See BarReading.
HP_CERTAIN_GAP = 0.03
# The bar is empty when the visible red ends below this. A sliver stays lit at the left cap.
ZERO_HP = 0.005
# This many readings in a row above zero cancel an earlier zero reading. Blood crossing the empty
# bar after a kill gave two such readings in a row, so two is not enough.
ZERO_CANCEL_SAMPLES = 5
# A bar that stayed empty this long before it went away is a kill, with or without defeat text.
# Not every boss shows the text. In 19 kill clips the empty bar stayed for 1.7 s or more, and
# before the detector learned to read through a skill popup, a wrong empty reading lasted up to
# 1.1 s (docs/observations.md).
ZERO_HOLD_S = 1.2
# HP is the middle one of this many trusted readings, so one wrong reading changes nothing.
HP_MEDIAN_SAMPLES = 3
# HP only goes up when this many readings in a row are above it by more than HP_RISE_MIN: a bar
# that was read too low for a moment, or a boss whose bar refills for its next phase.
HP_RISE_SAMPLES = 10
HP_RISE_MIN = 0.02
# A rise this soon after the bar appeared also corrects the starting HP: the bar fades in.
START_SETTLE_S = 2.0
# A start reading at or above this is a full bar: the fill's right tip fades out.
FULL_HP = 0.98
# Fights where HP moved less than this are walk-pasts and are not recorded.
MIN_HP_CHANGE = 0.01


class _State(Enum):
    IDLE = auto()
    PENDING = auto()
    FIGHTING = auto()
    WAITING = auto()


@dataclass(frozen=True, slots=True)
class FightOutcome:
    """A finished fight. Times are on the caller's clock, in seconds."""

    started_at: float
    duration_s: float
    status: Status
    start_hp_pct: int
    end_hp_pct: int


class FightTracker:
    """Feed it samples in time order with :meth:`update`."""

    def __init__(
        self, wait_window_s: float = WAIT_WINDOW_S, *, skip_walk_pasts: bool = True
    ) -> None:
        self.wait_window_s = wait_window_s
        self.skip_walk_pasts = skip_walk_pasts
        self._state = _State.IDLE
        self._started_at = 0.0
        self._last_seen = 0.0
        self._gone_at = 0.0
        self._zero_at: float | None = None
        self._above_zero_run = 0
        self._start_hp: float | None = None
        self._hp: float | None = None
        self._recent: deque[float] = deque(maxlen=HP_MEDIAN_SAMPLES)
        self._rise: list[float] = []
        self._defeat_since: float | None = None

    @property
    def in_fight(self) -> bool:
        return self._state in (_State.FIGHTING, _State.WAITING)

    @property
    def started_at(self) -> float:
        """When the bar of the current fight was first seen. Only meaningful while in a fight."""
        return self._started_at

    @property
    def watching_for_defeat(self) -> bool:
        """True when the caller should check the defeat text box. It is not needed otherwise."""
        return self._state is _State.WAITING

    @property
    def hp(self) -> float | None:
        """Current boss HP from 0.0 to 1.0, or None before the first trusted reading."""
        return self._hp

    def update(
        self, now: float, bar: BarReading, defeat_visible: bool = False
    ) -> FightOutcome | None:
        """Take one sample. Returns an outcome on the sample that ends a recorded fight."""
        if self._state is _State.IDLE:
            if bar.present:
                self._begin(now)
                self._read_hp(now, bar)
            return None

        if self._state is _State.PENDING:
            if not bar.present:
                if now - self._last_seen > PENDING_GAP_S:
                    self._state = _State.IDLE
                return None
            self._read_hp(now, bar)
            if now - self._started_at >= CONFIRM_S:
                self._state = _State.FIGHTING
            return None

        if bar.present:
            # Covers both fighting and the bar coming back inside the wait window.
            self._state = _State.FIGHTING
            self._defeat_since = None
            self._read_hp(now, bar)
            return None

        if self._state is _State.FIGHTING:
            self._state = _State.WAITING
            self._gone_at = now

        if not defeat_visible:
            self._defeat_since = None
        elif self._defeat_since is None:
            self._defeat_since = now
        if (
            self._defeat_since is not None
            and now - self._defeat_since >= DEFEAT_HOLD_S
            and self._hp is not None
            and self._hp <= KILL_HP_MAX
        ):
            return self._finish(Status.COMPLETE)
        if now - self._gone_at >= self.wait_window_s:
            return self._finish(Status.COMPLETE if self._left_empty() else Status.INCOMPLETE)
        return None

    def end_now(self) -> FightOutcome | None:
        """End the current fight as incomplete, because the user asked. None if there is none.

        Like any incomplete fight it runs to the last moment the bar was seen, and it is dropped
        if the boss lost no HP. A bar still on screen afterwards starts a new record.
        """
        if not self.in_fight:
            self._state = _State.IDLE
            return None
        return self._finish(Status.INCOMPLETE)

    def _begin(self, now: float) -> None:
        self._state = _State.PENDING
        self._started_at = now
        self._zero_at = None
        self._above_zero_run = 0
        self._start_hp = None
        self._hp = None
        self._recent.clear()
        self._rise.clear()
        self._defeat_since = None

    def _left_empty(self) -> bool:
        """True when the bar had been empty for a while at the moment it was last seen."""
        return (
            self._zero_at is not None
            and self._last_seen - self._zero_at >= ZERO_HOLD_S
            and self._start_hp is not None
            and self._start_hp >= MIN_HP_CHANGE
        )

    def _read_hp(self, now: float, bar: BarReading) -> None:
        self._last_seen = now
        if bar.hp_high - bar.hp > HP_CERTAIN_GAP:
            return  # something covers the end of the fill
        # The clock stops at the start of the last stretch of empty readings. One stray reading
        # above zero does not restart it, because effects cross the bar after the kill too.
        if bar.hp <= ZERO_HP:
            self._above_zero_run = 0
            if self._zero_at is None:
                self._zero_at = now
        else:
            self._above_zero_run += 1
            if self._above_zero_run >= ZERO_CANCEL_SAMPLES:
                self._zero_at = None

        self._recent.append(bar.hp)
        if len(self._recent) < HP_MEDIAN_SAMPLES:
            return
        level = sorted(self._recent)[HP_MEDIAN_SAMPLES // 2]
        if self._hp is None or self._start_hp is None:
            self._start_hp = self._hp = level
        elif level <= self._hp + HP_RISE_MIN:
            # HP does not go up within a phase: a higher reading is an effect crossing the bar.
            self._hp = min(self._hp, level)
            self._rise.clear()
        else:
            self._rise.append(level)
            if len(self._rise) >= HP_RISE_SAMPLES:
                self._hp = min(self._rise)
                self._rise.clear()
                if now - self._started_at <= START_SETTLE_S:
                    self._start_hp = max(self._start_hp, self._hp)

    def _finish(self, status: Status) -> FightOutcome | None:
        self._state = _State.IDLE
        start_hp = self._start_hp if self._start_hp is not None else 1.0
        end_hp = self._hp if self._hp is not None else start_hp
        if status is Status.COMPLETE:
            end_hp = 0.0
            # The empty bar stays up during the death animation: stop the clock at zero HP.
            ended_at = self._zero_at if self._zero_at is not None else self._last_seen
        else:
            ended_at = self._last_seen
            if self.skip_walk_pasts and start_hp - end_hp < MIN_HP_CHANGE:
                return None  # walked past the boss without damaging it
        return FightOutcome(
            started_at=self._started_at,
            duration_s=ended_at - self._started_at,
            status=status,
            start_hp_pct=100 if start_hp >= FULL_HP else round(start_hp * 100),
            end_hp_pct=round(end_hp * 100),
        )
