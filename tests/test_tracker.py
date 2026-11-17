import csv
from pathlib import Path

import pytest

from nightreign_boss_timer.detector import BarReading
from nightreign_boss_timer.records import Status
from nightreign_boss_timer.tracker import FightOutcome, FightTracker

READINGS = Path(__file__).parent / "fixtures" / "hippo_readings.csv"
STEP = 0.1
GONE = BarReading(present=False, hp=0.0, hp_high=0.0, score=0.0)


def bar(hp: float, hp_high: float | None = None) -> BarReading:
    return BarReading(present=True, hp=hp, hp_high=hp if hp_high is None else hp_high, score=0.9)


class Replay:
    """Feeds samples to a tracker at a fixed rate and collects what comes out."""

    def __init__(self, tracker: FightTracker | None = None) -> None:
        self.tracker = tracker or FightTracker()
        self.now = 0.0
        self.outcomes: list[FightOutcome] = []

    def feed(self, reading: BarReading, seconds: float, defeat: bool = False) -> None:
        for _ in range(round(seconds / STEP)):
            outcome = self.tracker.update(self.now, reading, defeat)
            if outcome:
                self.outcomes.append(outcome)
            self.now += STEP

    def fall(self, start: float, end: float, seconds: float) -> None:
        """HP falling in a straight line."""
        steps = round(seconds / STEP)
        for i in range(steps):
            self.feed(bar(start + (end - start) * i / (steps - 1)), STEP)


def test_kill_is_complete_and_timed_to_zero_hp() -> None:
    run = Replay()
    run.feed(GONE, 2)
    run.fall(1.0, 0.01, 30)  # 2.0 s to 32.0 s
    run.feed(bar(0.0), 6)  # empty bar during the death animation
    run.feed(GONE, 0.5)
    run.feed(GONE, 2, defeat=True)

    assert len(run.outcomes) == 1
    outcome = run.outcomes[0]
    assert outcome.status is Status.COMPLETE
    assert outcome.started_at == pytest.approx(2.0)
    assert outcome.duration_s == pytest.approx(30.0, abs=0.11)  # not 36: the clock stops at zero
    assert (outcome.start_hp_pct, outcome.end_hp_pct) == (100, 0)


def test_bar_gone_without_defeat_text_is_incomplete() -> None:
    run = Replay()
    run.fall(1.0, 0.62, 20)
    run.feed(GONE, 7.5)
    assert run.outcomes == []  # still inside the wait window
    run.feed(GONE, 1)

    assert len(run.outcomes) == 1
    outcome = run.outcomes[0]
    assert outcome.status is Status.INCOMPLETE
    assert outcome.duration_s == pytest.approx(19.9, abs=0.11)  # to the last sight of the bar
    assert (outcome.start_hp_pct, outcome.end_hp_pct) == (100, 62)


def test_walk_past_is_not_recorded() -> None:
    run = Replay()
    run.feed(bar(0.992), 5)
    run.feed(GONE, 10)
    assert run.outcomes == []
    assert not run.tracker.in_fight


def test_damaged_boss_starts_below_full() -> None:
    run = Replay()
    run.fall(0.62, 0.3, 10)
    run.feed(GONE, 9)
    assert (run.outcomes[0].start_hp_pct, run.outcomes[0].end_hp_pct) == (62, 30)


def test_bar_back_inside_the_wait_window_is_the_same_fight() -> None:
    run = Replay()
    run.fall(1.0, 0.7, 10)
    run.feed(GONE, 5)  # map opened over the bar
    run.fall(0.7, 0.4, 10)
    run.feed(GONE, 9)

    assert len(run.outcomes) == 1
    assert run.outcomes[0].duration_s == pytest.approx(24.9, abs=0.11)
    assert (run.outcomes[0].start_hp_pct, run.outcomes[0].end_hp_pct) == (100, 40)


def test_bar_back_after_the_wait_window_is_a_new_fight() -> None:
    run = Replay()
    run.fall(1.0, 0.7, 10)
    run.feed(GONE, 9)
    run.fall(0.7, 0.4, 10)
    run.feed(GONE, 9)

    assert [(o.start_hp_pct, o.end_hp_pct) for o in run.outcomes] == [(100, 70), (70, 40)]


def test_flash_of_a_bar_is_ignored() -> None:
    run = Replay()
    run.feed(bar(0.5), 0.2)
    run.feed(GONE, 10)
    assert run.outcomes == []


def test_covered_readings_do_not_change_hp() -> None:
    run = Replay()
    run.feed(bar(0.8), 2)
    run.feed(bar(0.0, hp_high=0.12), 1)  # popup over the left end: HP unknown, not zero
    assert run.tracker.hp == pytest.approx(0.8)


def test_effect_crossing_the_bar_does_not_raise_hp() -> None:
    run = Replay()
    run.feed(bar(0.3), 2)
    run.feed(bar(0.5), 0.2)
    assert run.tracker.hp == pytest.approx(0.3)


def test_one_stray_reading_does_not_restart_the_clock_after_zero() -> None:
    run = Replay()
    run.fall(1.0, 0.01, 10)
    run.feed(bar(0.0), 1)
    run.feed(bar(0.3), STEP)  # effect crossing the empty bar
    run.feed(bar(0.0), 3)
    run.feed(GONE, 1, defeat=True)
    assert run.outcomes[0].duration_s == pytest.approx(10.0, abs=0.11)


def test_defeat_text_must_hold_for_several_samples() -> None:
    run = Replay()
    run.fall(1.0, 0.5, 10)
    run.feed(GONE, 1)
    run.feed(GONE, 0.2, defeat=True)  # two samples of gold sparks
    run.feed(GONE, 9)
    assert [o.status for o in run.outcomes] == [Status.INCOMPLETE]


def test_defeat_check_is_only_wanted_while_waiting() -> None:
    run = Replay()
    assert not run.tracker.watching_for_defeat
    run.fall(1.0, 0.5, 5)
    assert not run.tracker.watching_for_defeat
    run.feed(GONE, 1)
    assert run.tracker.watching_for_defeat


def test_real_clip_gives_one_complete_fight() -> None:
    """Detector readings from an 80 s clip of a kill, 10 per second. See fixtures/README.md."""
    tracker = FightTracker()
    outcomes = []
    with READINGS.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            reading = BarReading(
                present=row["present"] == "1",
                hp=float(row["hp"]),
                hp_high=float(row["hp_high"]),
                score=0.0,
            )
            outcome = tracker.update(float(row["t"]), reading, row["defeat"] == "1")
            if outcome:
                outcomes.append(outcome)

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status is Status.COMPLETE
    # Measured by hand, frame by frame: bar appears at 11.13 s, HP reaches zero at 71.61 s.
    assert outcome.started_at == pytest.approx(11.13, abs=0.1)
    assert outcome.duration_s == pytest.approx(60.5, abs=0.2)
    assert (outcome.start_hp_pct, outcome.end_hp_pct) == (100, 0)
