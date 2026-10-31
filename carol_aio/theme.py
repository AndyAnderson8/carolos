"""Colors, fonts and DPI helpers shared by the tray flyout and settings window."""

from __future__ import annotations

import ctypes
import sys
import tkinter as tk

PANEL = "#1d2226"
RAISED = "#262d32"
LINE = "#343d43"
TEXT = "#e9e5dc"
MUTED = "#8e999f"
LAMP = "#f2b544"
FAULT = "#e87d6f"
ON_LAMP = "#1d2226"  # knob color sitting on the amber track

FONT = "Segoe UI"
SYMBOLS = "Segoe UI Symbol"

_scale = 1.0


def enable_dpi_awareness() -> None:
    """Render crisp text on high-DPI displays (call before creating the Tk root)."""
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


def init_scale(root: tk.Misc) -> None:
    global _scale
    _scale = root.winfo_fpixels("1i") / 96


def px(value: int) -> int:
    """Scale a 96-dpi pixel size to the current display."""
    return round(value * _scale)


def dark_titlebar(window: tk.Toplevel) -> None:
    """Ask Windows for a dark title bar so the settings window matches the panel."""
    if sys.platform != "win32":
        return
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), 4)
    except (AttributeError, OSError):
        pass


def work_area(root: tk.Misc) -> tuple[int, int, int, int]:
    """Screen rectangle not covered by the taskbar: (left, top, right, bottom)."""
    if sys.platform == "win32":
        from ctypes import wintypes

        rect = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
            return rect.left, rect.top, rect.right, rect.bottom
    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()
