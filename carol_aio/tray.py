"""Notification-area icon: left-click opens the panel, right-click offers Quit."""

from __future__ import annotations

from collections.abc import Callable

import pystray
from PIL import Image, ImageDraw

from carol_aio import theme

ICON_SIZE = 64
SUPERSAMPLE = 4


def draw_icon(lit: bool) -> Image.Image:
    """A lamp: an amber ring with a filled center when any tool is running."""
    size = ICON_SIZE * SUPERSAMPLE
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    color = theme.LAMP if lit else theme.MUTED
    inset = size // 10
    draw.ellipse((inset, inset, size - inset, size - inset), outline=color, width=size // 9)
    if lit:
        core = size * 3 // 10
        draw.ellipse((core, core, size - core, size - core), fill=color)
    return image.resize((ICON_SIZE, ICON_SIZE), Image.Resampling.LANCZOS)


class Tray:
    """Wraps pystray. Callbacks run on pystray's thread, so keep them to queue puts."""

    def __init__(self, on_open: Callable[[], None], on_quit: Callable[[], None]) -> None:
        self._icon = pystray.Icon(
            "carol_aio",
            draw_icon(False),
            "Carol AIO",
            menu=pystray.Menu(
                pystray.MenuItem("Open Carol AIO", lambda: on_open(), default=True),
                pystray.MenuItem("Quit", lambda: on_quit()),
            ),
        )
        self._lit = False

    def start(self) -> None:
        self._icon.run_detached()

    def stop(self) -> None:
        self._icon.stop()

    def update(self, running: int, total: int) -> None:
        """Light the icon and refresh its tooltip."""
        lit = running > 0
        if lit != self._lit:
            self._lit = lit
            self._icon.icon = draw_icon(lit)
        self._icon.title = f"Carol AIO: {running} of {total} on"
