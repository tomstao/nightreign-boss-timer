import os
import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the UI is Windows-only")

# Draw into memory, so the test needs no desktop and shows nothing on screen.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

if sys.platform == "win32":
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from nightreign_boss_timer.ui.overlay import Overlay
    from nightreign_boss_timer.ui.presenter import OverlayText


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
