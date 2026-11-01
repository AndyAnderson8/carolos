"""Colors, fonts and DPI helpers shared by the tray flyout and settings window."""

from __future__ import annotations

import ctypes
import sys
import tkinter as tk

# The logo's own colours: the accent is its pink, and the tray count uses its yellow.
LOGO_PINK = "#fc80a3"
LOGO_YELLOW = "#f9d92a"

# Sand, with the brown of the logo's own outline for text and edges.
PANEL = "#f4e6c6"  # sand
RAISED = "#ead8ad"
SELECTED = "#fff6df"  # the chosen segment of a choice control
LINE = "#d8c28f"
OUTLINE = "#43261a"
TEXT = "#43261a"
MUTED = "#715a49"
ACCENT = LOGO_PINK
FAULT = "#c4443a"
SEA = "#1d93b3"  # header band, like the sea behind the icon
ON_ACCENT = "#43261a"  # text and knob sitting on the accent
ON_SEA = "#fff6df"  # text sitting on the header band

PAGE_WIDTH = 384  # every page inside the panel is this wide (before display scaling)

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


def work_area(root: tk.Misc) -> tuple[int, int, int, int]:
    """Screen rectangle not covered by the taskbar: (left, top, right, bottom)."""
    if sys.platform == "win32":
        from ctypes import wintypes

        rect = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
            return rect.left, rect.top, rect.right, rect.bottom
    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()
