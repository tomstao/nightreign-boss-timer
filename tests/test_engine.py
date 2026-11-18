from datetime import datetime
from pathlib import Path

import numpy as np

from nightreign_boss_timer.detector import MARGIN_HEIGHTS
from nightreign_boss_timer.engine import Engine, State, records_path
from nightreign_boss_timer.ocr import TextReading
from nightreign_boss_timer.records import RecordStore, Status
from nightreign_boss_timer.regions import Box, bar_region, defeat_text_region
from nightreign_boss_timer.settings import Settings

WINDOW = Box(0, 0, 1920, 1080)
BAR_BOX = bar_region(WINDOW)
DEFEAT_BOX = defeat_text_region(WINDOW)
FILL, TRACK, SCENE, GOLD = (110, 53, 24), (22, 22, 22), (70, 68, 64), (230, 190, 60)


class FakeScreen:
    """A made-up screen: set ``hp`` to show a bar that full, None for no bar."""

    def __init__(self) -> None:
        self.window: Box | None = WINDOW
        self.hp: float | None = None
        self.defeat_text = False
        self.grabs: list[Box] = []

    def find_window(self, title: str) -> Box | None:
        return self.window

    def grab(self, box: Box) -> np.ndarray:
        self.grabs.append(box)
        image = np.full((box.height, box.width, 3), SCENE, dtype=np.uint8)
        if box == BAR_BOX and self.hp is not None:
            bar_height = box.height // (1 + 2 * MARGIN_HEIGHTS)
            top = bar_height * MARGIN_HEIGHTS
            end = round(box.width * self.hp)
            image[top : top + bar_height, :end] = FILL
            image[top : top + bar_height, end:] = TRACK
        if box == DEFEAT_BOX and self.defeat_text:
            image[:] = (30, 30, 30)
            pitch = box.width * 0.6 / 16
            for i in range(16):
                left = round(box.width * 0.2 + i * pitch)
                image[20:55, left : left + round(pitch * 0.6)] = GOLD
        return image


class FakeReader:
    def read(self, region: np.ndarray) -> TextReading:
        return TextReading("Tree Sentinel", 0.99)


class Harness:
    def __init__(self, tmp_path: Path, settings: Settings | None = None) -> None:
        self.now = 100.0
        self.screen = FakeScreen()
        self.store = RecordStore(tmp_path / "records.csv")
        self.engine = Engine(
            settings or Settings(),
            self.screen,
            self.store,
            FakeReader(),
            clock=lambda: self.now,
            wall_clock=lambda: datetime(2026, 11, 17, 21, 0, 0),
        )
        self.records = []
        self.last = None

    def run(self, seconds: float, hp: float | None, defeat_text: bool = False) -> None:
        """Hold the screen in one state and step the engine through that much time."""
        self.screen.hp, self.screen.defeat_text = hp, defeat_text
        end = self.now + seconds
        while self.now < end - 1e-9:
            self.last = self.engine.step()
            if self.last.record:
                self.records.append(self.last.record)
            self.now += self.last.delay_s


def test_no_game_window_waits_and_grabs_nothing(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    h.screen.window = None
    h.run(5, None)
    assert h.last.snapshot.state is State.NO_GAME
    assert h.last.delay_s == 2.0
    assert h.screen.grabs == []


def test_idle_is_slow_and_a_fight_is_fast(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    h.run(2, None)
    assert (h.last.snapshot.state, h.last.delay_s) == (State.IDLE, 0.5)
    h.run(2, 1.0)
    assert (h.last.snapshot.state, h.last.delay_s) == (State.FIGHT, 0.1)


def test_kill_is_saved_with_name_table_and_time(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    h.run(1, None)
    for hp in (1.0, 0.7, 0.4, 0.1, 0.02):
        h.run(4, hp)
    h.run(3, 0.0)
    h.run(1, None)
    h.run(2, None, defeat_text=True)

    assert len(h.records) == 1
    record = h.records[0]
    assert (record.status, record.boss, record.language) == (Status.COMPLETE, "Tree Sentinel", "en")
    assert (record.table, record.start_hp_pct, record.end_hp_pct) == ("Arena", 100, 0)
    assert 19.5 <= record.duration_s <= 20.5  # bar appears to zero HP, not to the defeat text
    assert h.store.read_all() == [record]
    assert h.last.snapshot.state is State.IDLE


def test_snapshot_during_a_fight_shows_boss_hp_and_time(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    h.run(3, 1.0)
    h.run(3, 0.6)
    snapshot = h.last.snapshot
    assert (snapshot.state, snapshot.boss, snapshot.table) == (
        State.FIGHT,
        "Tree Sentinel",
        "Arena",
    )
    assert abs(snapshot.hp - 0.6) < 0.01
    assert 5.5 <= snapshot.elapsed_s <= 6.5


def test_defeat_text_is_only_looked_at_after_the_bar_disappears(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    h.run(3, 1.0)
    assert DEFEAT_BOX not in h.screen.grabs
    h.run(1, None)
    assert DEFEAT_BOX in h.screen.grabs


def test_table_is_fixed_when_the_fight_starts(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    h.run(3, 1.0)
    h.engine.settings.set_active_table("Normal")
    h.run(3, 0.5)
    h.run(9, None)
    assert [r.table for r in h.records] == ["Arena"]


def test_paused_engine_does_not_look_at_the_screen(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    h.engine.paused = True
    h.run(3, 1.0)
    assert h.last.snapshot.state is State.PAUSED
    assert h.screen.grabs == []


def test_walk_past_setting_is_honoured(tmp_path: Path) -> None:
    skipping = Harness(tmp_path / "a")
    skipping.run(3, 1.0)
    skipping.run(9, None)
    assert skipping.records == []

    keeping = Harness(tmp_path / "b", Settings(skip_walk_pasts=False))
    keeping.run(3, 1.0)
    keeping.run(9, None)
    assert [r.status for r in keeping.records] == [Status.INCOMPLETE]


def test_wait_window_setting_is_honoured(tmp_path: Path) -> None:
    h = Harness(tmp_path, Settings(wait_window_s=3.0))
    h.run(3, 1.0)
    h.run(3, 0.5)
    h.run(3.5, None)
    assert len(h.records) == 1


def test_records_path_follows_the_setting(tmp_path: Path) -> None:
    assert records_path(Settings(records_folder=str(tmp_path))) == tmp_path / "records.csv"
    assert records_path(Settings()).name == "records.csv"


def test_timing_options_changed_while_running_apply_to_the_next_fight(tmp_path: Path) -> None:
    settings = Settings()
    harness = Harness(tmp_path, settings)
    settings.wait_window_s = 20.0
    settings.skip_walk_pasts = False
    harness.engine.step()
    assert harness.engine._tracker.wait_window_s == 20.0
    assert harness.engine._tracker.skip_walk_pasts is False


def test_end_fight_saves_the_fight_in_progress_on_the_next_step(tmp_path: Path) -> None:
    h = Harness(tmp_path)
    h.run(4, 1.0)
    h.run(4, 0.5)
    h.engine.end_fight()
    h.run(0.1, 0.5)
    assert len(h.records) == 1
    assert (h.records[0].status, h.records[0].end_hp_pct) == (Status.INCOMPLETE, 50)
    assert h.store.read_all() == h.records

    h.engine.end_fight()  # nothing in progress that lost HP: nothing more is written
    h.run(1, 0.5)
    assert len(h.records) == 1
