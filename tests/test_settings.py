import json
from pathlib import Path

import pytest

from nightreign_boss_timer.regions import Fractions
from nightreign_boss_timer.settings import DEFAULT_HOTKEYS, Settings, TableError, load, save


def test_defaults() -> None:
    settings = Settings()
    assert settings.table_names() == ["Arena", "Normal"]
    assert settings.active_table == "Arena"
    assert settings.ui_language == "en"
    assert settings.bar_region is None
    assert settings.hotkeys == DEFAULT_HOTKEYS


def test_missing_file_gives_defaults(tmp_path: Path) -> None:
    assert load(tmp_path / "settings.json") == Settings()


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "settings.json"
    settings = Settings(ui_language="zh_TW", wait_window_s=12.0, skip_walk_pasts=False)
    settings.add_table("无伤练习")
    settings.set_active_table("无伤练习")
    settings.bar_region = Fractions(0.24, 0.756, 0.793, 0.799)
    settings.defeat_text_region = Fractions(0.24, 0.76, 0.455, 0.525)
    settings.calibrated_size = (2560, 1440)
    settings.hotkeys["end_fight"] = "Ctrl+Alt+E"

    save(settings, path)

    assert load(path) == settings
    assert "无伤练习" in path.read_text(encoding="utf-8")  # stored readable, not escaped
    assert not path.with_suffix(".tmp").exists()


def test_damaged_file_is_set_aside_and_defaults_used(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{ this is not json", encoding="utf-8")

    assert load(path) == Settings()
    assert not path.exists()
    assert path.with_suffix(".damaged.json").read_text(encoding="utf-8") == "{ this is not json"


def test_bad_values_fall_back_one_by_one(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "ui_language": "klingon",
                "wait_window_s": -5,
                "skip_walk_pasts": "yes",
                "fight_rate": 20,
                "bar_region": [0.8, 0.2, 0.1, 0.9],  # left is right of right
                "defeat_text_region": [0.24, 0.76, 0.455, 0.525],
                "calibrated_size": [1920, "tall"],
                "hotkeys": {"next_table": "F9", "made_up_action": "F1", "calibrate": 7},
                "future_option": True,
            }
        ),
        encoding="utf-8",
    )
    settings = load(path)

    assert settings.ui_language == "en"
    assert settings.wait_window_s == 8.0
    assert settings.skip_walk_pasts is True
    assert settings.fight_rate == 20.0  # the one good value is kept
    assert settings.bar_region is None
    assert settings.defeat_text_region == Fractions(0.24, 0.76, 0.455, 0.525)
    assert settings.calibrated_size is None
    assert settings.hotkeys["next_table"] == "F9"
    assert settings.hotkeys["calibrate"] == DEFAULT_HOTKEYS["calibrate"]
    assert "made_up_action" not in settings.hotkeys


def test_file_that_is_not_an_object_gives_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    assert load(path) == Settings()


def test_unusable_tables_are_dropped_and_active_table_repaired(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "tables": [
                    {"name": "Practice"},
                    {"name": "practice"},  # same name in another case
                    {"name": "   "},
                    "not a table",
                ],
                "active_table": "Gone",
            }
        ),
        encoding="utf-8",
    )
    settings = load(path)
    assert settings.table_names() == ["Practice"]
    assert settings.active_table == "Practice"


def test_add_table_trims_and_rejects_duplicates_and_blanks() -> None:
    settings = Settings()
    assert settings.add_table("  No-hit practice ").name == "No-hit practice"
    with pytest.raises(TableError, match="already exists"):
        settings.add_table("arena")
    with pytest.raises(TableError, match="needs a name"):
        settings.add_table("   ")


def test_rename_follows_the_active_table() -> None:
    settings = Settings()
    settings.rename_table("Arena", "Boss Arena")
    assert settings.table_names() == ["Boss Arena", "Normal"]
    assert settings.active_table == "Boss Arena"
    with pytest.raises(TableError, match="already exists"):
        settings.rename_table("Boss Arena", "Normal")
    settings.rename_table("Normal", "Normal")  # renaming to itself is not an error


def test_builtin_tables_cannot_be_deleted_but_others_can() -> None:
    settings = Settings()
    settings.add_table("Co-op")
    settings.set_active_table("Co-op")
    with pytest.raises(TableError, match="built-in"):
        settings.delete_table("Arena")

    settings.delete_table("Co-op")

    assert settings.table_names() == ["Arena", "Normal"]
    assert settings.active_table == "Arena"  # the deleted table was active


def test_next_table_cycles() -> None:
    settings = Settings()
    settings.add_table("Co-op")
    assert [settings.next_table() for _ in range(4)] == ["Normal", "Co-op", "Arena", "Normal"]


def test_unknown_table_is_an_error() -> None:
    with pytest.raises(TableError, match="no table named"):
        Settings().set_active_table("Nope")
