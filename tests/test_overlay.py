import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the UI is Windows-only")

# Draw into memory, so the test needs no desktop and shows nothing on screen.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

if sys.platform == "win32":
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from nightreign_boss_timer.ui.overlay import DEFAULT_POSITION, Overlay
    from nightreign_boss_timer.ui.presenter import OverlayText


LEFT = Qt.MouseButton.LeftButton if sys.platform == "win32" else None
NONE = Qt.KeyboardModifier.NoModifier if sys.platform == "win32" else None


@pytest.fixture(scope="module")
def application() -> "QApplication":
    return QApplication.instance() or QApplication([])


def test_overlay_never_takes_clicks_or_focus(application: "QApplication") -> None:
    overlay = Overlay()
    flags = overlay.windowFlags()
    assert flags & Qt.WindowType.WindowTransparentForInput
    assert flags & Qt.WindowType.WindowDoesNotAcceptFocus
    assert flags & Qt.WindowType.WindowStaysOnTopHint
    assert flags & Qt.WindowType.FramelessWindowHint


def test_overlay_is_see_through_as_a_whole(application: "QApplication") -> None:
    overlay = Overlay()
    # Window opacity, not per-pixel transparency: Windows only keeps a window out of screen
    # captures when it is drawn this way.
    assert 0.5 < overlay.windowOpacity() < 1.0
    assert not overlay.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    # Drawn into memory there is no real window to exclude, so the answer here is no.
    assert overlay.hidden_from_capture is False


def test_overlay_can_be_put_back_into_captures(
    application: "QApplication", monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[bool] = []

    def fake(handle: int, exclude: bool = True) -> bool:
        asked.append(exclude)
        return True

    monkeypatch.setattr("nightreign_boss_timer.ui.overlay.exclude_from_capture", fake)
    overlay = Overlay()
    assert asked == [True]
    assert overlay.hidden_from_capture is True

    overlay.set_in_captures(True)
    assert asked == [True, False]
    assert overlay.hidden_from_capture is False

    # Making the overlay movable builds a new window, which must be told again.
    overlay.set_movable(True)
    assert asked == [True, False, False]

    overlay.set_in_captures(False)
    assert asked[-1] is True
    assert overlay.hidden_from_capture is True


def test_overlay_grows_to_fit_its_text(application: "QApplication") -> None:
    overlay = Overlay()
    overlay.show_text(OverlayText(("Arena - ready",)))
    one_line = overlay.size()
    overlay.show_text(OverlayText(("Arena", "Tree Sentinel, a rather long boss name", "01:23.4")))
    three_lines = overlay.size()
    assert three_lines.height() > one_line.height()
    assert three_lines.width() > one_line.width()


def test_overlay_paints_chinese_text_without_error(application: "QApplication") -> None:
    overlay = Overlay()
    overlay.show_text(OverlayText(("Arena   已完成", "大树守卫", "02:41.3   最佳 02:10.9")))
    image = overlay.grab().toImage()
    assert not image.isNull()
    assert image.width() == overlay.width()


def test_overlay_hides_when_it_has_nothing_to_say_or_is_turned_off(
    application: "QApplication",
) -> None:
    overlay = Overlay()
    overlay.show_text(OverlayText(("Arena - ready",)))
    assert overlay.isVisible()
    overlay.show_text(OverlayText(()))
    assert not overlay.isVisible()
    overlay.show_text(OverlayText(("Arena - ready",)))
    overlay.set_enabled(False)
    assert not overlay.isVisible()
    overlay.set_enabled(True)
    assert overlay.isVisible()


def test_overlay_can_be_dragged_only_while_movable(application: "QApplication") -> None:
    overlay = Overlay()
    overlay.show_text(OverlayText(("Arena - ready",)))
    overlay.set_position((300, 400))
    places: list[tuple[int, int]] = []
    overlay.moved.connect(lambda x, y: places.append((x, y)))

    QTest.mousePress(overlay, LEFT, NONE, QPoint(5, 5))
    QTest.mouseMove(overlay, QPoint(65, 35))
    QTest.mouseRelease(overlay, LEFT, NONE, QPoint(65, 35))
    assert places == []  # locked: nothing happens
    assert (overlay.x(), overlay.y()) == (300, 400)

    overlay.set_movable(True, "Overlay - drag to move")
    assert overlay.isVisible()
    assert not overlay.windowFlags() & Qt.WindowType.WindowTransparentForInput
    QTest.mousePress(overlay, LEFT, NONE, QPoint(5, 5))
    QTest.mouseMove(overlay, QPoint(65, 35))
    QTest.mouseRelease(overlay, LEFT, NONE, QPoint(65, 35))
    assert places == [(overlay.x(), overlay.y())]
    assert places[0] != (300, 400)

    overlay.set_movable(False)
    assert overlay.windowFlags() & Qt.WindowType.WindowTransparentForInput
    assert overlay.isVisible()  # still has something to say


def test_movable_overlay_shows_a_hint_when_it_has_nothing_to_say(
    application: "QApplication",
) -> None:
    overlay = Overlay()
    overlay.show_text(OverlayText(()))
    assert not overlay.isVisible()
    overlay.set_movable(True, "Overlay - drag to move")
    assert overlay.isVisible()  # or there would be nothing to take hold of
    assert overlay.width() > 100
    overlay.set_enabled(False)
    assert not overlay.isVisible()  # switched off stays off
    overlay.set_enabled(True)
    overlay.set_movable(False)
    assert not overlay.isVisible()


def test_overlay_position_can_be_set_and_reset(application: "QApplication") -> None:
    overlay = Overlay()
    overlay.set_position((-1200, 50))  # a monitor to the left
    assert (overlay.x(), overlay.y()) == (-1200, 50)
    overlay.set_position(None)
    assert (overlay.x(), overlay.y()) == DEFAULT_POSITION


def test_saved_choice_to_show_in_captures_is_applied_at_start(
    application: "QApplication", tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from nightreign_boss_timer import settings as settings_file
    from nightreign_boss_timer.ui.app import App

    asked: list[bool] = []

    def fake(handle: int, exclude: bool = True) -> bool:
        asked.append(exclude)
        return True

    monkeypatch.setattr("nightreign_boss_timer.ui.overlay.exclude_from_capture", fake)
    path = tmp_path / "settings.json"
    settings_file.save(settings_file.Settings(setup_done=True, overlay_in_captures=True), path)

    app = App(application, "no such window", tmp_path / "records.csv", settings_path=path)
    try:
        assert asked[-1] is False
        assert app.overlay.hidden_from_capture is False
    finally:
        app.close()
