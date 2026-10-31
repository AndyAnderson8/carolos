"""Colors, fonts and DPI helpers shared by the tray flyout and settings window.

The colour names below are module attributes that ``use`` rewrites, so widgets
must read them as ``theme.PANEL`` when they are built, not copy them at import.
"""

from __future__ import annotations

import ctypes
import sys
import tkinter as tk

# The logo's own colours: the accent is its pink, and the tray count uses its yellow.
LOGO_PINK = "#fc80a3"
LOGO_YELLOW = "#f9d92a"

# Beach by day, cocoa by night. Text and outlines are the brown of the logo's own outline.
LIGHT = {
    "PANEL": "#f4e6c6",  # sand
    "RAISED": "#ead8ad",
    "SELECTED": "#fff6df",  # the chosen segment of a choice control
    "LINE": "#d8c28f",
    "OUTLINE": "#43261a",
    "TEXT": "#43261a",
    "MUTED": "#715a49",
    "ACCENT": LOGO_PINK,
    "FAULT": "#c4443a",
    "SEA": "#1d93b3",  # header band, like the sea behind the icon
}
DARK = {
    "PANEL": "#2a2024",
    "RAISED": "#362b30",
    "SELECTED": "#4d3d45",
    "LINE": "#4a3b42",
    "OUTLINE": "#6d5662",
    "TEXT": "#f6e8c8",
    "MUTED": "#b59f8d",
    "ACCENT": LOGO_PINK,
    "FAULT": "#e87d6f",
    "SEA": "#176c82",
}

PANEL = DARK["PANEL"]
RAISED = DARK["RAISED"]
SELECTED = DARK["SELECTED"]
LINE = DARK["LINE"]
OUTLINE = DARK["OUTLINE"]
TEXT = DARK["TEXT"]
MUTED = DARK["MUTED"]
ACCENT = DARK["ACCENT"]
FAULT = DARK["FAULT"]
SEA = DARK["SEA"]
ON_ACCENT = "#43261a"  # text and knob sitting on the accent, in both themes
ON_SEA = "#fff6df"  # text sitting on the header band, in both themes

FONT = "Segoe UI"
SYMBOLS = "Segoe UI Symbol"

_scale = 1.0


def use(light: bool) -> None:
    """Switch every colour above to the light or dark palette."""
    globals().update(LIGHT if light else DARK)


def round_corners(window: tk.Toplevel) -> None:
    """Ask Windows 11 for smooth rounded corners on a borderless window (no-op elsewhere)."""
    if sys.platform != "win32":
        return
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetAncestor(window.winfo_id(), 2)  # 2 = GA_ROOT
        preference = ctypes.c_int(2)  # DWMWCP_ROUND
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(preference), 4)
    except (AttributeError, OSError):
        pass


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
