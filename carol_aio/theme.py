"""Colors, fonts and DPI helpers shared by the tray flyout and settings window.

The colour names below are module attributes that ``use`` rewrites, so widgets
must read them as ``theme.PANEL`` when they are built, not copy them at import.
"""

from __future__ import annotations

import ctypes
import sys
import tkinter as tk

DARK = {
    "PANEL": "#1d2226",
    "RAISED": "#262d32",
    "SELECTED": "#3a444b",  # the chosen segment of a choice control
    "LINE": "#343d43",
    "TEXT": "#e9e5dc",
    "MUTED": "#8e999f",
    "LAMP": "#f2b544",
    "FAULT": "#e87d6f",
}
LIGHT = {
    "PANEL": "#f7f8f9",
    "RAISED": "#e8ecee",
    "SELECTED": "#ffffff",
    "LINE": "#d0d7db",
    "TEXT": "#1b2227",
    "MUTED": "#5d6a72",
    "LAMP": "#f2b544",
    "FAULT": "#c4443a",
}

PANEL = DARK["PANEL"]
RAISED = DARK["RAISED"]
SELECTED = DARK["SELECTED"]
LINE = DARK["LINE"]
TEXT = DARK["TEXT"]
MUTED = DARK["MUTED"]
LAMP = DARK["LAMP"]
FAULT = DARK["FAULT"]
ON_LAMP = "#1d2226"  # text and knob sitting on amber, in both themes

FONT = "Segoe UI"
SYMBOLS = "Segoe UI Symbol"

_scale = 1.0


def use(light: bool) -> None:
    """Switch every colour above to the light or dark palette."""
    globals().update(LIGHT if light else DARK)


def system_is_light() -> bool:
    """True when Windows' "app mode" is light. Falls back to dark if it can't be read."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            return bool(winreg.QueryValueEx(key, "AppsUseLightTheme")[0])
    except OSError:
        return False


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


def work_area(root: tk.Misc) -> tuple[int, int, int, int]:
    """Screen rectangle not covered by the taskbar: (left, top, right, bottom)."""
    if sys.platform == "win32":
        from ctypes import wintypes

        rect = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
            return rect.left, rect.top, rect.right, rect.bottom
    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()
