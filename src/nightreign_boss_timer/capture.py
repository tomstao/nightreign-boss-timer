"""Copy small regions of the screen into arrays, on Windows.

This uses GDI through ctypes, so it needs no extra dependency and never touches the game process:
it reads the desktop image that Windows has already composed. Only the requested rectangle is
copied, which is what keeps the cost low.

Everything on the desktop is in that image, other programs' windows and this tool's own included.
The overlay asks Windows to leave it out with :func:`exclude_from_capture`, so that it can never
be mistaken for part of the game.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

if sys.platform != "win32":  # pragma: no cover
    raise ImportError("screen capture is only available on Windows")

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

_SRCCOPY = 0x00CC0020
_DIB_RGB_COLORS = 0
_BI_RGB = 0
_DPI_PER_MONITOR_AWARE_V2 = -4
_WDA_EXCLUDEFROMCAPTURE = 0x11


class _BitmapInfoHeader(ctypes.Structure):
    _fields_ = (
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    )


_user32.GetDC.argtypes = (wintypes.HWND,)
_user32.GetDC.restype = wintypes.HDC
_user32.ReleaseDC.argtypes = (wintypes.HWND, wintypes.HDC)
_user32.SetProcessDpiAwarenessContext.argtypes = (ctypes.c_void_p,)
_user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
_user32.FindWindowW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR)
_user32.FindWindowW.restype = wintypes.HWND
_user32.GetClientRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
_user32.ClientToScreen.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.POINT))
_user32.SetWindowDisplayAffinity.argtypes = (wintypes.HWND, wintypes.DWORD)
_user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
_gdi32.CreateCompatibleDC.argtypes = (wintypes.HDC,)
_gdi32.CreateCompatibleDC.restype = wintypes.HDC
_gdi32.CreateCompatibleBitmap.argtypes = (wintypes.HDC, ctypes.c_int, ctypes.c_int)
_gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
_gdi32.SelectObject.argtypes = (wintypes.HDC, wintypes.HGDIOBJ)
_gdi32.SelectObject.restype = wintypes.HGDIOBJ
_gdi32.DeleteObject.argtypes = (wintypes.HGDIOBJ,)
_gdi32.DeleteDC.argtypes = (wintypes.HDC,)
_gdi32.BitBlt.argtypes = (
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.DWORD,
)
_gdi32.BitBlt.restype = wintypes.BOOL
_gdi32.GetDIBits.argtypes = (
    wintypes.HDC,
    wintypes.HBITMAP,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.c_void_p,
    ctypes.POINTER(_BitmapInfoHeader),
    wintypes.UINT,
)
_gdi32.GetDIBits.restype = ctypes.c_int


@dataclass(frozen=True, slots=True)
class Region:
    """A rectangle in screen pixels."""

    left: int
    top: int
    width: int
    height: int


class CaptureError(RuntimeError):
    """Windows refused to copy the screen region."""


def enable_dpi_awareness() -> None:
    """Make coordinates mean real pixels on scaled displays. Call once, before any window work.

    It fails harmlessly if awareness was already set for the process.
    """
    _user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(_DPI_PER_MONITOR_AWARE_V2))


def exclude_from_capture(handle: int) -> bool:
    """Ask Windows to leave one of this program's own windows out of every screen capture.

    ``handle`` is the window's native handle. Returns False if Windows refuses, which it does
    before Windows 10 version 2004 and for windows drawn with per-pixel transparency. The window
    then also disappears from screenshots and recordings made by other programs.
    """
    return bool(_user32.SetWindowDisplayAffinity(handle, _WDA_EXCLUDEFROMCAPTURE))


def find_window(title: str) -> Region | None:
    """The drawable area of the window with exactly this title, or None if there is none."""
    handle = _user32.FindWindowW(None, title)
    if not handle:
        return None
    rect = wintypes.RECT()
    origin = wintypes.POINT(0, 0)
    if not _user32.GetClientRect(handle, ctypes.byref(rect)):
        return None
    if not _user32.ClientToScreen(handle, ctypes.byref(origin)):
        return None
    return Region(origin.x, origin.y, rect.right - rect.left, rect.bottom - rect.top)


class ScreenGrabber:
    """Grabs one fixed-size region, reusing its Windows resources between grabs.

    Create one grabber per region and call :meth:`grab` each sample. Use it as a context manager
    or call :meth:`close` when done.
    """

    def __init__(self, width: int, height: int) -> None:
        if width < 1 or height < 1:
            raise ValueError("region must be at least 1 by 1 pixel")
        self.width = width
        self.height = height
        self._screen = _user32.GetDC(None)
        self._memory = _gdi32.CreateCompatibleDC(self._screen)
        self._bitmap = _gdi32.CreateCompatibleBitmap(self._screen, width, height)
        if not (self._screen and self._memory and self._bitmap):
            self.close()
            raise CaptureError("could not set up screen capture")
        self._previous = _gdi32.SelectObject(self._memory, self._bitmap)
        self._info = _BitmapInfoHeader(
            biSize=ctypes.sizeof(_BitmapInfoHeader),
            biWidth=width,
            biHeight=-height,  # negative: rows run top to bottom
            biPlanes=1,
            biBitCount=32,
            biCompression=_BI_RGB,
        )
        self._buffer = np.empty((height, width, 4), dtype=np.uint8)

    def grab(self, left: int, top: int) -> NDArray[np.uint8]:
        """Copy the region whose top-left corner is at these screen pixels. Returns RGB."""
        if not _gdi32.BitBlt(
            self._memory, 0, 0, self.width, self.height, self._screen, left, top, _SRCCOPY
        ):
            raise CaptureError("BitBlt failed")
        rows = _gdi32.GetDIBits(
            self._memory,
            self._bitmap,
            0,
            self.height,
            self._buffer.ctypes.data_as(ctypes.c_void_p),
            ctypes.byref(self._info),
            _DIB_RGB_COLORS,
        )
        if rows != self.height:
            raise CaptureError("GetDIBits failed")
        # Windows hands back blue, green, red, unused. Reverse the first three into a new array.
        return np.ascontiguousarray(self._buffer[..., 2::-1])

    def close(self) -> None:
        if getattr(self, "_memory", None):
            if getattr(self, "_previous", None):
                _gdi32.SelectObject(self._memory, self._previous)
            _gdi32.DeleteDC(self._memory)
            self._memory = None
        if getattr(self, "_bitmap", None):
            _gdi32.DeleteObject(self._bitmap)
            self._bitmap = None
        if getattr(self, "_screen", None):
            _user32.ReleaseDC(None, self._screen)
            self._screen = None

    def __enter__(self) -> ScreenGrabber:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class WindowsScreen:
    """The real screen, in the shape the engine expects. Keeps one grabber per region size."""

    def __init__(self) -> None:
        self._grabbers: dict[tuple[int, int], ScreenGrabber] = {}

    def find_window(self, title: str) -> Region | None:
        return find_window(title)

    def grab(self, box: object) -> NDArray[np.uint8]:
        """Copy a rectangle given as anything with left, top, width and height."""
        size = (box.width, box.height)  # type: ignore[attr-defined]
        grabber = self._grabbers.get(size)
        if grabber is None:
            grabber = self._grabbers[size] = ScreenGrabber(*size)
        return grabber.grab(box.left, box.top)  # type: ignore[attr-defined]

    def close(self) -> None:
        for grabber in self._grabbers.values():
            grabber.close()
        self._grabbers.clear()

    def __enter__(self) -> WindowsScreen:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
