"""A borderless, click-through window that shows an image with per-pixel transparency.

Tk can't draw a window with smooth, see-through edges, so the flyout's shape is drawn as an
image and shown in one of these, with the real controls in an ordinary window on top.
Windows only.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from PIL import Image

WS_POPUP = 0x80000000
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020  # clicks go to whatever is underneath
WS_EX_TOOLWINDOW = 0x00000080  # no taskbar button
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000  # never takes focus
ULW_ALPHA = 2
AC_SRC_ALPHA = 1
HWND_TOPMOST = -1
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE, SWP_SHOWWINDOW = 0x1, 0x2, 0x10, 0x40
SW_HIDE = 0

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)


class _Blend(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_ubyte),
        ("BlendFlags", ctypes.c_ubyte),
        ("SourceConstantAlpha", ctypes.c_ubyte),
        ("AlphaFormat", ctypes.c_ubyte),
    ]


class _BitmapHeader(ctypes.Structure):
    _fields_ = [
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
    ]


user32.CreateWindowExW.restype = wintypes.HWND
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID,
]  # fmt: skip
user32.GetDC.restype = wintypes.HDC
user32.GetDC.argtypes = [wintypes.HWND]
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.UpdateLayeredWindow.argtypes = [
    wintypes.HWND, wintypes.HDC, ctypes.POINTER(wintypes.POINT), ctypes.POINTER(wintypes.SIZE),
    wintypes.HDC, ctypes.POINTER(wintypes.POINT), wintypes.COLORREF, ctypes.POINTER(_Blend),
    wintypes.DWORD,
]  # fmt: skip
user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.UINT,
]  # fmt: skip
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.DestroyWindow.argtypes = [wintypes.HWND]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateDIBSection.restype = wintypes.HBITMAP
gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC, ctypes.POINTER(_BitmapHeader), wintypes.UINT,
    ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD,
]  # fmt: skip
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteDC.argtypes = [wintypes.HDC]


def _bgra(image: Image.Image) -> bytes:
    """Pixels as Windows wants them: blue, green, red, alpha, with colour pre-multiplied by alpha."""
    r, g, b, a = image.convert("RGBa").split()
    return Image.merge("RGBA", (b, g, r, a)).tobytes()


class LayeredWindow:
    def __init__(self) -> None:
        # "Static" is a window class Windows already provides, so no window procedure is needed.
        style = (
            WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TRANSPARENT
        )
        self.hwnd = user32.CreateWindowExW(
            style, "Static", None, WS_POPUP, 0, 0, 1, 1, None, None, None, None
        )
        if not self.hwnd:
            raise OSError("Couldn't create the shaped window.")

    def show(self, image: Image.Image, x: int, y: int) -> None:
        """Show ``image`` with its top-left corner at screen position (x, y), above other windows."""
        if not self.hwnd:
            return
        width, height = image.size
        screen = user32.GetDC(None)
        memory = gdi32.CreateCompatibleDC(screen)
        header = _BitmapHeader(
            ctypes.sizeof(_BitmapHeader), width, -height, 1, 32, 0, 0, 0, 0, 0, 0
        )
        bits = ctypes.c_void_p()
        bitmap = gdi32.CreateDIBSection(
            screen, ctypes.byref(header), 0, ctypes.byref(bits), None, 0
        )
        data = _bgra(image)
        ctypes.memmove(bits, data, len(data))
        previous = gdi32.SelectObject(memory, bitmap)
        user32.UpdateLayeredWindow(
            self.hwnd,
            screen,
            ctypes.byref(wintypes.POINT(x, y)),
            ctypes.byref(wintypes.SIZE(width, height)),
            memory,
            ctypes.byref(wintypes.POINT(0, 0)),
            0,
            ctypes.byref(_Blend(0, 0, 255, AC_SRC_ALPHA)),
            ULW_ALPHA,
        )
        gdi32.SelectObject(memory, previous)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory)
        user32.ReleaseDC(None, screen)
        user32.SetWindowPos(
            self.hwnd, wintypes.HWND(HWND_TOPMOST), 0, 0, 0, 0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )  # fmt: skip

    def hide(self) -> None:
        if self.hwnd:
            user32.ShowWindow(self.hwnd, SW_HIDE)

    def destroy(self) -> None:
        if self.hwnd:
            user32.DestroyWindow(self.hwnd)
            self.hwnd = None
