import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the UI is Windows-only")

if sys.platform == "win32":
    from PySide6.QtWidgets import QApplication

    from nightreign_boss_timer.ui.controller import UNDO_SECONDS
    from test_record_view import fight
    from ui_support import Recorder


@pytest.fixture(scope="module")
def application() -> "QApplication":
    return QApplication.instance() or QApplication([])


class Clock:
    def __init__(self) -> None:
        self.now = 50.0

    def __call__(self) -> float:
        return self.now


def make(folder: Path) -> tuple["Recorder", Clock]:
    recorder = Recorder(folder)
    clock = Clock()
    recorder.controller._clock = clock
    recorder.store.append(fight(1))
    recorder.store.append(fight(2, boss="Night Aspect"))
    return recorder, clock


def test_discard_removes_the_last_record_and_says_so(
    application: "QApplication", tmp_path: Path
) -> None:
    recorder, _ = make(tmp_path)
    refreshed: list[bool] = []
    recorder.controller.records_changed.connect(lambda: refreshed.append(True))
    assert recorder.controller.run_action("discard_last")
    assert [r.boss for r in recorder.store.read_all()] == ["Tree Sentinel"]
    assert recorder.notices == ["Record discarded. Press again to undo."]
    assert refreshed == [True]


def test_discarding_again_soon_brings_it_back(application: "QApplication", tmp_path: Path) -> None:
    recorder, clock = make(tmp_path)
    recorder.controller.discard_last()
    clock.now += UNDO_SECONDS - 1
    recorder.controller.discard_last()
    assert [r.boss for r in recorder.store.read_all()] == ["Tree Sentinel", "Night Aspect"]
    assert recorder.notices[-1] == "Record restored"

    recorder.controller.discard_last()  # after an undo, this discards again
    assert len(recorder.store.read_all()) == 1


def test_discarding_again_later_removes_another(
    application: "QApplication", tmp_path: Path
) -> None:
    recorder, clock = make(tmp_path)
    recorder.controller.discard_last()
    clock.now += UNDO_SECONDS + 1
    recorder.controller.discard_last()
    assert recorder.store.read_all() == []
    clock.now += UNDO_SECONDS + 1
    recorder.controller.discard_last()
    assert recorder.notices[-1] == "No record to discard"


def test_discard_with_the_file_open_elsewhere(
    application: "QApplication", tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorder, _ = make(tmp_path)

    def refuse(self: Path, target: Path) -> None:
        raise PermissionError("open in Excel")

    monkeypatch.setattr(Path, "replace", refuse)
    recorder.controller.discard_last()
    monkeypatch.undo()
    assert recorder.notices == ["Records file is open in another program"]
    assert len(recorder.store.read_all()) == 2


def test_end_fight_is_passed_on(application: "QApplication", tmp_path: Path) -> None:
    recorder, _ = make(tmp_path)
    asked: list[bool] = []
    recorder.controller.end_fight_requested.connect(lambda: asked.append(True))
    assert recorder.controller.run_action("end_fight")
    assert asked == [True]
