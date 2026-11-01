"""Make a window the active one.

The panel closes when it loses focus, like the taskbar's own flyouts. That only works if it
had focus to begin with, and Windows refuses to hand focus to a program that was started
moments ago (a double-click on its shortcut) unless that program borrows the input of the
window that is in front.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

ASFW_ANY = -1  # AllowSetForegroundWindow: let any program take the foreground


def allow_any_program() -> None:
    """Called by a freshly started copy (which Windows trusts) before it hands over to the running one."""
    if sys.platform == "win32":
        ctypes.WinDLL("user32").AllowSetForegroundWindow(ASFW_ANY)


def activate(window: int) -> None:
    """Bring ``window`` (an HWND) to the front and make it the active window."""
    if sys.platform != "win32":
        return
    user32 = ctypes.WinDLL("user32")
    kernel32 = ctypes.WinDLL("kernel32")
    for func in (user32.GetForegroundWindow, user32.GetParent):
        func.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.c_void_p]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.GetParent.argtypes = [wintypes.HWND]
    user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    window = user32.GetParent(window) or window  # Tk's toplevel is wrapped in a frame window
    front = user32.GetForegroundWindow()
    if front == window:
        return
    mine = kernel32.GetCurrentThreadId()
    theirs = user32.GetWindowThreadProcessId(front, None) if front else 0
    joined = bool(theirs and theirs != mine and user32.AttachThreadInput(mine, theirs, True))
    try:
        user32.BringWindowToTop(window)
        user32.SetForegroundWindow(window)
    finally:
        if joined:
            user32.AttachThreadInput(mine, theirs, False)
