import csv
from pathlib import Path

import pytest

from nightreign_boss_timer.detector import BarReading
from nightreign_boss_timer.records import Status
from nightreign_boss_timer.tracker import FightOutcome, FightTracker

FIXTURES = Path(__file__).parent / "fixtures"
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


def test_empty_bar_then_gone_is_complete_without_defeat_text() -> None:
    # Not every boss shows the gold text. The bar emptied and went away: that is a kill.
    run = Replay()
    run.fall(1.0, 0.01, 30)
    run.feed(bar(0.0), 3)
    run.feed(GONE, 7.5)
    assert run.outcomes == []  # the bar may still come back inside the wait window
    run.feed(GONE, 1)

    assert len(run.outcomes) == 1
    outcome = run.outcomes[0]
    assert outcome.status is Status.COMPLETE
    assert outcome.duration_s == pytest.approx(30.0, abs=0.11)
    assert (outcome.start_hp_pct, outcome.end_hp_pct) == (100, 0)


def test_a_moment_of_empty_readings_before_the_bar_goes_is_not_a_kill() -> None:
    # A popup or a menu dims the bar so it reads empty, then hides it.
    run = Replay()
    run.fall(1.0, 0.4, 20)
    run.feed(bar(0.0), 1)
    run.feed(GONE, 9)
    assert [o.status for o in run.outcomes] == [Status.INCOMPLETE]


def test_empty_readings_that_end_do_not_stick() -> None:
    run = Replay()
    run.fall(1.0, 0.4, 20)
    run.feed(bar(0.0), 2)  # read as empty for a while, wrongly
    run.feed(bar(0.4), 1.5)
    assert run.tracker.hp == pytest.approx(0.4)
    run.feed(GONE, 9)
    assert [(o.status, o.end_hp_pct) for o in run.outcomes] == [(Status.INCOMPLETE, 40)]


def test_bar_that_refills_starts_the_next_phase_of_the_same_fight() -> None:
    run = Replay()
    run.fall(1.0, 0.01, 20)
    run.feed(bar(0.0), 2)
    run.feed(GONE, 3)
    run.fall(1.0, 0.5, 20)  # second phase
    run.feed(GONE, 9)
    assert [(o.status, o.start_hp_pct, o.end_hp_pct) for o in run.outcomes] == [
        (Status.INCOMPLETE, 100, 50)
    ]


def test_one_wrong_reading_changes_nothing() -> None:
    run = Replay()
    run.feed(bar(0.0), STEP)  # the bar fading in reads as empty once
    run.feed(bar(0.99), 2)
    run.feed(bar(0.0), STEP)
    run.fall(0.99, 0.6, 10)
    run.feed(GONE, 9)
    assert (run.outcomes[0].start_hp_pct, run.outcomes[0].end_hp_pct) == (100, 60)


def test_empty_bar_that_was_never_fuller_is_not_recorded() -> None:
    run = Replay()
    run.feed(bar(0.0), 5)
    run.feed(GONE, 9)
    assert run.outcomes == []


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


def test_defeat_text_must_hold() -> None:
    run = Replay()
    run.fall(1.0, 0.02, 10)
    run.feed(GONE, 1)
    run.feed(GONE, 0.5, defeat=True)  # a flash of gold, shorter than the hold time
    run.feed(GONE, 9)
    assert [o.status for o in run.outcomes] == [Status.INCOMPLETE]


def test_defeat_text_does_not_count_while_the_boss_has_health() -> None:
    # A hit flash hides the bar and puts gold mid-screen at once. The boss is at half health.
    run = Replay()
    run.fall(1.0, 0.5, 10)
    run.feed(GONE, 2, defeat=True)
    assert run.outcomes == []
    run.fall(0.5, 0.4, 5)  # the fight goes on as one record
    run.feed(GONE, 9)
    assert [(o.status, o.start_hp_pct, o.end_hp_pct) for o in run.outcomes] == [
        (Status.INCOMPLETE, 100, 40)
    ]


def test_dropout_while_the_bar_is_being_confirmed_keeps_the_start_time() -> None:
    run = Replay()
    run.feed(GONE, 1)
    run.feed(bar(1.0), 0.1)  # first sight at 1.0 s
    run.feed(GONE, 0.2)  # one flash
    run.fall(1.0, 0.5, 10)
    run.feed(GONE, 9)
    assert run.outcomes[0].started_at == pytest.approx(1.0)


def test_defeat_check_is_only_wanted_while_waiting() -> None:
    run = Replay()
    assert not run.tracker.watching_for_defeat
    run.fall(1.0, 0.5, 5)
    assert not run.tracker.watching_for_defeat
    run.feed(GONE, 1)
    assert run.tracker.watching_for_defeat


def replay_readings(name: str, run: Replay) -> None:
    """Feed a file of real detector readings, 10 per second. See fixtures/README.md."""
    with (FIXTURES / name).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            reading = BarReading(
                present=row["present"] == "1",
                hp=float(row["hp"]),
                hp_high=float(row["hp_high"]),
                score=0.0,
            )
            run.now = float(row["t"])
            outcome = run.tracker.update(run.now, reading, row["defeat"] == "1")
            if outcome:
                run.outcomes.append(outcome)
    run.now += STEP


def test_real_clip_gives_one_complete_fight() -> None:
    run = Replay()
    replay_readings("hippo_readings.csv", run)
    outcomes = run.outcomes

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status is Status.COMPLETE
    # Measured by hand, frame by frame: bar appears at 11.13 s, HP reaches zero at 71.61 s.
    assert outcome.started_at == pytest.approx(11.13, abs=0.1)
    assert outcome.duration_s == pytest.approx(60.5, abs=0.2)
    assert (outcome.start_hp_pct, outcome.end_hp_pct) == (100, 0)


def test_real_clip_of_a_kill_with_no_gold_text_is_complete() -> None:
    """A night boss: the banner is silver, which the defeat text check does not know."""
    run = Replay()
    replay_readings("bell_bearing_hunter_readings.csv", run)

    assert len(run.outcomes) == 1
    outcome = run.outcomes[0]
    assert outcome.status is Status.COMPLETE
    # The bar appears at 11.8 s. Its last red goes at 60.7 s, but a paler strip of recent damage
    # covers the end of the fill until 61.4 s, so the tracker stops the clock there.
    assert outcome.started_at == pytest.approx(11.8, abs=0.1)
    assert outcome.duration_s == pytest.approx(49.6, abs=0.2)
    assert (outcome.start_hp_pct, outcome.end_hp_pct) == (100, 0)


def test_real_clip_with_hit_flashes_is_not_ended_early() -> None:
    """A 160 s kill of a golden boss. Hit flashes hide the bar and look like defeat text 20 times.

    The clip ends just as the real defeat text appears, so the test supplies what would follow.
    """
    run = Replay()
    replay_readings("tree_sentinel_readings.csv", run)
    assert run.outcomes == []  # no flash was taken for the defeat text
    assert run.tracker.in_fight
    assert run.tracker.hp == pytest.approx(0.0, abs=0.005)

    run.feed(GONE, 2, defeat=True)

    assert len(run.outcomes) == 1
    outcome = run.outcomes[0]
    assert outcome.status is Status.COMPLETE
    # The bar appears at 9.3 s and the last hit lands at about 151.5 s.
    assert outcome.started_at == pytest.approx(9.3, abs=0.15)
    assert outcome.duration_s == pytest.approx(142.2, abs=0.5)
    assert (outcome.start_hp_pct, outcome.end_hp_pct) == (100, 0)


def test_ending_a_fight_by_hand_saves_it_as_incomplete() -> None:
    replay = Replay()
    replay.fall(1.0, 0.6, 10.0)
    outcome = replay.tracker.end_now()
    assert outcome is not None
    assert (outcome.status, outcome.start_hp_pct, outcome.end_hp_pct) == (
        Status.INCOMPLETE,
        100,
        60,
    )
    assert outcome.duration_s == pytest.approx(9.9, abs=0.15)
    assert not replay.tracker.in_fight

    # The bar is still on screen: under the recording rules that is a new record from 60%.
    replay.feed(bar(0.6), 0.5)
    replay.fall(0.6, 0.3, 5.0)
    second = replay.tracker.end_now()
    assert second is not None
    assert second.start_hp_pct == 60


def test_ending_by_hand_with_no_fight_or_no_damage_writes_nothing() -> None:
    replay = Replay()
    assert replay.tracker.end_now() is None
    replay.feed(bar(1.0), 5.0)
    assert replay.tracker.end_now() is None  # a walk-past, as if the bar had gone away
    assert not replay.tracker.in_fight
