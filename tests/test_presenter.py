from datetime import datetime

from nightreign_boss_timer.engine import Snapshot, State
from nightreign_boss_timer.i18n import Translator
from nightreign_boss_timer.records import FightRecord, Status
from nightreign_boss_timer.ui.presenter import best_time, overlay_text

EN = Translator("en")


def record(**changes: object) -> FightRecord:
    values: dict[str, object] = {
        "started_at": datetime(2026, 11, 17, 21, 4, 33),
        "table": "Arena",
        "boss": "Tree Sentinel",
        "language": "en",
        "status": Status.COMPLETE,
        "duration_s": 161.3,
        "start_hp_pct": 100,
        "end_hp_pct": 0,
    }
    values.update(changes)
    return FightRecord(**values)  # type: ignore[arg-type]


def test_idle_shows_the_active_table() -> None:
    text = overlay_text(Snapshot(State.IDLE, "Arena"), EN)
    assert text.lines == ("Arena - ready",)
    assert not text.warning


def test_fight_shows_table_boss_time_and_hp() -> None:
    snapshot = Snapshot(State.FIGHT, "Arena", "Tree Sentinel", hp=0.62, elapsed_s=83.4)
    assert overlay_text(snapshot, EN).lines == ("Arena", "Tree Sentinel", "01:23.4   HP 62%")


def test_fight_before_the_name_and_hp_are_known() -> None:
    snapshot = Snapshot(State.FIGHT, "Arena", elapsed_s=0.4)
    assert overlay_text(snapshot, EN).lines == ("Arena", "unknown", "00:00.4")


def test_result_shows_for_a_while_then_goes_back_to_ready() -> None:
    idle = Snapshot(State.IDLE, "Arena")
    shown = overlay_text(idle, EN, result=record(), result_age_s=3.0, best_s=130.9)
    assert shown.lines == ("Arena   Complete", "Tree Sentinel", "02:41.3   best 02:10.9")
    assert not shown.warning

    later = overlay_text(idle, EN, result=record(), result_age_s=9.0, best_s=130.9)
    assert later.lines == ("Arena - ready",)


def test_incomplete_result_is_highlighted_and_has_no_best_without_history() -> None:
    idle = Snapshot(State.IDLE, "Arena")
    text = overlay_text(idle, EN, result=record(status=Status.INCOMPLETE), result_age_s=1.0)
    assert text.lines == ("Arena   Incomplete", "Tree Sentinel", "02:41.3")
    assert text.warning


def test_a_new_fight_replaces_the_old_result() -> None:
    snapshot = Snapshot(State.FIGHT, "Arena", "Tree Sentinel", hp=1.0, elapsed_s=1.0)
    text = overlay_text(snapshot, EN, result=record(), result_age_s=2.0)
    assert text.lines[0] == "Arena"


def test_warnings() -> None:
    assert overlay_text(Snapshot(State.PAUSED, "Arena"), EN) == overlay_text(
        Snapshot(State.PAUSED, "Normal"), EN
    )
    assert overlay_text(Snapshot(State.PAUSED, "Arena"), EN).warning


def test_overlay_has_nothing_to_show_without_the_game() -> None:
    assert overlay_text(Snapshot(State.NO_GAME, "Arena"), EN).lines == ()


def test_overlay_is_localized() -> None:
    snapshot = Snapshot(State.FIGHT, "Arena", "大树守卫", hp=0.62, elapsed_s=83.4)
    assert overlay_text(snapshot, Translator("zh_CN")).lines[2] == "01:23.4   血量 62%"
    result = overlay_text(
        Snapshot(State.IDLE, "Arena"), Translator("zh_TW"), result=record(), result_age_s=1.0
    )
    assert result.lines[0] == "Arena   已完成"


def test_best_time_counts_only_comparable_fights() -> None:
    history = [
        record(duration_s=150.0),
        record(duration_s=130.9),
        record(duration_s=40.0, start_hp_pct=62),  # resumed against a damaged boss
        record(duration_s=20.0, status=Status.INCOMPLETE),
        record(duration_s=10.0, table="Normal"),
        record(duration_s=5.0, boss="Golden Hippopotamus"),
    ]
    assert best_time(history, "Tree Sentinel", "Arena") == 130.9
    assert best_time(history, "Nobody", "Arena") is None
