"""Test-wide set-up."""

import os
import sys

# Draw into memory, so UI tests need no desktop and show nothing on screen.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def pytest_sessionfinish() -> None:
    """Destroy every window while the Qt application still exists.

    Windows that are still alive when Python shuts down are torn down in no particular order,
    some of them after the application object, and that crashes the interpreter on its way out:
    the tests pass and the run still fails.
    """
    if sys.platform != "win32" or "PySide6.QtWidgets" not in sys.modules:
        return
    import shiboken6
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance()
    if application is None:
        return
    for widget in application.topLevelWidgets():
        if shiboken6.isValid(widget):
            shiboken6.delete(widget)
    application.processEvents()
