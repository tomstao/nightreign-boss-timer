"""Global hotkeys on Windows: register them with the system and hear when one is pressed.

Uses ``RegisterHotKey``, the ordinary Windows way for a program to ask for a system-wide
shortcut. Nothing is hooked or injected anywhere. Windows sends a message to a hidden window of
this program when a hotkey is pressed, and that is passed on as a signal.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QObject, Signal
from PySide6.QtWidgets import QWidget

from nightreign_boss_timer.hotkeys import Hotkey, HotkeyManager, bindings
from nightreign_boss_timer.settings import Settings

_WM_HOTKEY = 0x0312
# Holding the keys down does not fire the hotkey again and again.
_MOD_NOREPEAT = 0x4000

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.RegisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
_user32.RegisterHotKey.restype = wintypes.BOOL
_user32.UnregisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int)
_user32.UnregisterHotKey.restype = wintypes.BOOL


class _Filter(QAbstractNativeEventFilter):
    def __init__(self, owner: GlobalHotkeys) -> None:
        super().__init__()
        self._owner = owner

    def nativeEventFilter(self, event_type: object, message: object) -> tuple[bool, int]:
        if bytes(event_type) == b"windows_generic_MSG":  # type: ignore[call-overload]
            msg = wintypes.MSG.from_address(int(message))  # type: ignore[call-overload]
            if msg.message == _WM_HOTKEY:
                self._owner.pressed(int(msg.wParam))
                return True, 0
        return False, 0


class GlobalHotkeys(QObject):
    # A hotkey was pressed. Carries the action, such as ``toggle_tracking`` or ``table:Arena``.
    triggered = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        # Never shown. It exists so that Windows has a window to send hotkey messages to.
        self._window = QWidget()
        self._handle = int(self._window.winId())
        self.manager = HotkeyManager(self._register, self._unregister)
        self._filter = _Filter(self)
        QCoreApplication.instance().installNativeEventFilter(self._filter)

    def _register(self, hotkey_id: int, hotkey: Hotkey) -> bool:
        return bool(
            _user32.RegisterHotKey(
                self._handle, hotkey_id, hotkey.modifiers | _MOD_NOREPEAT, hotkey.key
            )
        )

    def _unregister(self, hotkey_id: int) -> None:
        _user32.UnregisterHotKey(self._handle, hotkey_id)

    def apply(self, settings: Settings) -> None:
        """Make the registered hotkeys match the settings."""
        self.manager.apply(bindings(settings))

    @property
    def failed(self) -> set[str]:
        """Actions whose shortcut Windows refused to register."""
        return self.manager.failed

    def pressed(self, hotkey_id: int) -> None:
        action = self.manager.action_for(hotkey_id)
        if action:
            self.triggered.emit(action)

    def close(self) -> None:
        self.manager.release_all()
        application = QCoreApplication.instance()
        if application is not None:
            application.removeNativeEventFilter(self._filter)
