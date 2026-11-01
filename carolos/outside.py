"""Spots a mouse press outside the app's own windows (to close the panel).

The panel normally closes when it loses focus, but Windows may refuse to give focus to a
program that was just started (a double-click on its shortcut), so there is nothing to lose.
Watching the mouse works either way.
"""

from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes

VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
GA_ROOT = 2


def pressed() -> bool:
    """Whether the left or right mouse button is down right now."""
    if sys.platform != "win32":
        return False
    user32 = ctypes.WinDLL("user32")
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    return bool(
        (user32.GetAsyncKeyState(VK_LBUTTON) | user32.GetAsyncKeyState(VK_RBUTTON)) & 0x8000
    )


def over_other_program() -> bool:
    """Whether the mouse pointer is over a window that belongs to some other program."""
    if sys.platform != "win32":
        return False
    user32 = ctypes.WinDLL("user32")
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    window = user32.WindowFromPoint(point)
    if not window:
        return True  # the desktop or nothing at all
    root = user32.GetAncestor(window, GA_ROOT) or window
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(root, ctypes.byref(pid))
    return pid.value != os.getpid()
