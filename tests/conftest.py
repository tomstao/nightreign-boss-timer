"""Test-wide set-up."""

import os
import sys
from collections.abc import Iterator

import pytest

# Draw into memory, so UI tests need no desktop and show nothing on screen.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _destroy_windows() -> None:
    """Destroy every window that exists, while the Qt application still does."""
    if sys.platform != "win32" or "PySide6.QtWidgets" not in sys.modules:
        return
    import shiboken6
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance()
    if application is None:
        return
    for widget in application.topLevelWidgets():
        if shiboken6.isValid(widget):
            widget.hide()
            shiboken6.delete(widget)
    application.processEvents()


@pytest.fixture(autouse=True)
def no_windows_left_behind() -> Iterator[None]:
    """Each test starts with no windows from the tests before it.

    A window left open by one test still gets events during a later one. Such a window has
    been repainted while half torn down, which crashed the whole run on one Python version
    and not on another. Windows still alive when Python shuts down crash it on the way out
    in the same manner: the tests pass and the run still fails.
    """
    yield
    _destroy_windows()


def pytest_sessionfinish() -> None:
    _destroy_windows()
