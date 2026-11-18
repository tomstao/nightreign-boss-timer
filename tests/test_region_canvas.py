import os
import sys

import numpy as np
import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the UI is Windows-only")

# Draw into memory, so the test needs no desktop and shows nothing on screen.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

if sys.platform == "win32":
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from nightreign_boss_timer.calibration import MIN_HEIGHT, MIN_WIDTH, Selection
    from nightreign_boss_timer.ui.region_canvas import RegionCanvas, to_image

W, H = 1920, 1080
BAR = Selection(left=462, top=857, right=1452, bottom=864)
LEFT = Qt.MouseButton.LeftButton
NONE = Qt.KeyboardModifier.NoModifier
SHIFT = Qt.KeyboardModifier.ShiftModifier


@pytest.fixture(scope="module")
def application() -> "QApplication":
    return QApplication.instance() or QApplication([])


@pytest.fixture
def canvas(application: "QApplication") -> "RegionCanvas":
    """A canvas at exactly half the size of its 1080p picture, with the box on the bar."""
    canvas = RegionCanvas()
    canvas.resize(W // 2, H // 2)
    canvas.set_picture(np.full((H, W, 3), 40, dtype=np.uint8), BAR)
    return canvas


def at(canvas: "RegionCanvas", x: int, y: int) -> "QPoint":
    """The widget position of a picture position."""
    return canvas.to_widget(x, y).toPoint()


def drag(canvas: "RegionCanvas", start: "QPoint", end: "QPoint") -> None:
    QTest.mousePress(canvas, LEFT, NONE, start)
    QTest.mouseMove(canvas, end)
    QTest.mouseRelease(canvas, LEFT, NONE, end)


def test_image_keeps_the_colours_of_the_array(application: "QApplication") -> None:
    picture = np.zeros((4, 6, 3), dtype=np.uint8)
    picture[1, 2] = (110, 53, 24)
    image = to_image(picture)
    assert (image.width(), image.height()) == (6, 4)
    colour = image.pixelColor(2, 1)
    assert (colour.red(), colour.green(), colour.blue()) == (110, 53, 24)


def test_positions_map_both_ways(canvas: "RegionCanvas") -> None:
    assert canvas.to_widget(1920, 1080).toPoint() == QPoint(960, 540)
    assert canvas.to_picture(canvas.to_widget(462, 857)) == (462, 857)


def test_picture_is_centred_when_the_widget_has_another_shape(canvas: "RegionCanvas") -> None:
    canvas.resize(960, 740)  # 200 spare pixels of height: 100 above and 100 below
    assert canvas.to_widget(0, 0).toPoint() == QPoint(0, 100)
    assert canvas.to_picture(canvas.to_widget(462, 857)) == (462, 857)


def test_dragging_on_empty_picture_draws_a_new_box(canvas: "RegionCanvas") -> None:
    drag(canvas, at(canvas, 200, 100), at(canvas, 600, 300))
    assert canvas.selection == Selection(200, 100, 600, 300)


def test_dragging_inside_the_box_moves_it(canvas: "RegionCanvas") -> None:
    drag(canvas, at(canvas, 900, 860), at(canvas, 1000, 760))
    assert canvas.selection == Selection(562, 757, 1552, 764)


def test_dragging_a_corner_resizes_the_box(canvas: "RegionCanvas") -> None:
    drag(canvas, at(canvas, BAR.right, BAR.bottom), at(canvas, 1500, 880))
    assert canvas.selection == Selection(462, 857, 1500, 880)
    drag(canvas, at(canvas, 462, 857), at(canvas, 400, 800))
    assert canvas.selection == Selection(400, 800, 1500, 880)


def test_a_plain_click_leaves_the_smallest_box(canvas: "RegionCanvas") -> None:
    QTest.mouseClick(canvas, LEFT, NONE, at(canvas, 200, 100))
    assert canvas.selection == Selection(200, 100, 200 + MIN_WIDTH, 100 + MIN_HEIGHT)


def test_dragging_outside_the_picture_stops_at_its_edge(canvas: "RegionCanvas") -> None:
    canvas.resize(960, 740)  # 100 widget pixels of nothing below the picture
    drag(canvas, at(canvas, 1000, 900), QPoint(750, 739))
    assert canvas.selection == Selection(1000, 900, 1500, H)


def test_arrow_keys_move_one_picture_pixel(canvas: "RegionCanvas") -> None:
    QTest.keyClick(canvas, Qt.Key.Key_Up)
    QTest.keyClick(canvas, Qt.Key.Key_Right)
    QTest.keyClick(canvas, Qt.Key.Key_Right)
    assert canvas.selection == Selection(464, 856, 1454, 863)


def test_shift_arrow_keys_resize_from_the_bottom_right(canvas: "RegionCanvas") -> None:
    QTest.keyClick(canvas, Qt.Key.Key_Down, SHIFT)
    QTest.keyClick(canvas, Qt.Key.Key_Left, SHIFT)
    assert canvas.selection == Selection(462, 857, 1451, 865)


def test_changes_are_announced_once_each(canvas: "RegionCanvas") -> None:
    seen: list[Selection] = []
    canvas.selection_changed.connect(lambda: seen.append(canvas.selection))
    QTest.keyClick(canvas, Qt.Key.Key_Down)
    canvas.set_selection(canvas.selection)  # no change, no signal
    canvas.set_selection(Selection(-10, -10, 50, 50))  # fitted into the picture
    assert seen == [Selection(462, 858, 1452, 865), Selection(0, 0, 50, 50)]


def test_canvas_without_a_picture_ignores_input_and_paints(application: "QApplication") -> None:
    canvas = RegionCanvas()
    canvas.resize(400, 300)
    drag(canvas, QPoint(10, 10), QPoint(100, 100))
    QTest.keyClick(canvas, Qt.Key.Key_Down)
    assert canvas.selection == Selection(0, 0, 0, 0)
    assert not canvas.grab().toImage().isNull()


def test_box_is_outlined_and_the_rest_is_shaded(canvas: "RegionCanvas") -> None:
    canvas.set_selection(Selection(400, 400, 1200, 800))
    image = canvas.grab().toImage()
    inside = image.pixelColor(400, 300)  # picture (800, 600): untouched grey
    outside = image.pixelColor(100, 100)
    assert inside.red() == 40
    assert outside.red() < inside.red()
    outline = image.pixelColor(300, 199)  # just above the box's top edge at widget y = 200
    assert outline.blue() > 200
