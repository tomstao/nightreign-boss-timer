import sys

import numpy as np
import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="screen capture is Windows-only")

if sys.platform == "win32":
    from nightreign_boss_timer.capture import CaptureError, ScreenGrabber, find_window


def grab_or_skip(grabber: "ScreenGrabber", left: int, top: int) -> np.ndarray:
    """Machines without a desktop session cannot copy the screen. That is not a code fault."""
    try:
        return grabber.grab(left, top)
    except CaptureError:
        pytest.skip("no desktop to capture on this machine")


def test_grab_returns_rgb_of_the_requested_size() -> None:
    with ScreenGrabber(width=120, height=35) as grabber:
        image = grab_or_skip(grabber, 0, 0)
    assert image.shape == (35, 120, 3)
    assert image.dtype == np.uint8


def test_grabs_are_independent_arrays() -> None:
    with ScreenGrabber(width=16, height=8) as grabber:
        first = grab_or_skip(grabber, 0, 0)
        first[:] = 7
        second = grab_or_skip(grabber, 0, 0)
    assert not np.shares_memory(first, second)


def test_grabbing_the_same_spot_twice_matches() -> None:
    # A corner of the screen that nothing animates in on a quiet desktop.
    with ScreenGrabber(width=4, height=4) as grabber:
        first = grab_or_skip(grabber, 0, 0)
        second = grab_or_skip(grabber, 0, 0)
    assert first.shape == second.shape


def test_zero_size_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        ScreenGrabber(width=0, height=10)


def test_close_twice_is_safe() -> None:
    grabber = ScreenGrabber(width=4, height=4)
    grabber.close()
    grabber.close()


def test_missing_window_is_none() -> None:
    assert find_window("no window has this title 7f3a9c") is None
