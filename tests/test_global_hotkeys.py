import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the UI is Windows-only")

if sys.platform == "win32":
    from PySide6.QtWidgets import QApplication

    from nightreign_boss_timer.hotkeys import Hotkey
    from nightreign_boss_timer.settings import Settings
    from nightreign_boss_timer.ui.global_hotkeys import GlobalHotkeys
    from ui_support import Recorder


@pytest.fixture(scope="module")
def application() -> "QApplication":
    return QApplication.instance() or QApplication([])


class Granted(dict):
    """Stands in for Windows: grants every hotkey and remembers it by id."""

    def register(self, hotkey_id: int, hotkey: "Hotkey") -> bool:
        self[hotkey_id] = hotkey
        return True

    def unregister(self, hotkey_id: int) -> None:
        del self[hotkey_id]


def make(application: "QApplication") -> tuple["GlobalHotkeys", Granted]:
    hotkeys = GlobalHotkeys()
    windows = Granted()
    # Tests must not take real shortcuts away from the person running them.
    hotkeys.manager._register = windows.register
    hotkeys.manager._unregister = windows.unregister
    return hotkeys, windows


def test_a_pressed_hotkey_is_announced_by_its_action(application: "QApplication") -> None:
    hotkeys, windows = make(application)
    heard: list[str] = []
    hotkeys.triggered.connect(heard.append)
    hotkeys.apply(Settings())
    for hotkey_id in sorted(windows):
        hotkeys.pressed(hotkey_id)
    hotkeys.pressed(12345)  # not ours: ignored
    assert heard == [
        "toggle_tracking",
        "next_table",
        "toggle_overlay",
        "calibrate",
        "table:Arena",
        "table:Normal",
    ]
    hotkeys.close()
    assert windows == {}


def test_hotkeys_drive_the_controller(application: "QApplication", tmp_path: Path) -> None:
    recorder = Recorder(tmp_path)
    controller = recorder.controller
    calibrations: list[str] = []
    controller.calibration_requested.connect(calibrations.append)
    hotkeys, windows = make(application)
    hotkeys.triggered.connect(controller.run_action)
    hotkeys.apply(recorder.settings)
    by_action = {hotkeys.manager.action_for(i): i for i in windows}

    hotkeys.pressed(by_action["toggle_tracking"])
    assert not controller.tracking
    hotkeys.pressed(by_action["table:Normal"])
    assert recorder.settings.active_table == "Normal"
    hotkeys.pressed(by_action["next_table"])
    assert recorder.settings.active_table == "Arena"
    hotkeys.pressed(by_action["toggle_overlay"])
    assert not controller.overlay_visible
    hotkeys.pressed(by_action["calibrate"])
    assert calibrations == [""]
    hotkeys.close()


def test_open_window_and_unknown_actions(application: "QApplication", tmp_path: Path) -> None:
    recorder = Recorder(tmp_path)
    assert recorder.controller.run_action("open_window")
    assert recorder.windows == [""]
    assert not recorder.controller.run_action("table:No such table")
    assert not recorder.controller.run_action("make_coffee")


def test_a_renamed_table_keeps_its_hotkey(application: "QApplication", tmp_path: Path) -> None:
    recorder = Recorder(tmp_path)
    hotkeys, windows = make(application)
    hotkeys.apply(recorder.settings)
    recorder.controller.rename_table("Normal", "Main game")
    hotkeys.apply(recorder.settings)
    actions = {hotkeys.manager.action_for(i) for i in windows}
    assert "table:Main game" in actions
    assert "table:Normal" not in actions
    hotkeys.close()


def test_refusals_from_windows_are_kept_not_raised(application: "QApplication") -> None:
    hotkeys = GlobalHotkeys()
    hotkeys.manager._register = lambda hotkey_id, hotkey: False
    hotkeys.apply(Settings())
    assert "toggle_tracking" in hotkeys.failed
    assert len(hotkeys.failed) == 6
    hotkeys.close()
