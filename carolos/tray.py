"""Notification-area icon: left-click opens the panel, right-click offers Quit."""

from __future__ import annotations

from collections.abc import Callable

import pystray

from carolos.icon import tray_icon, tray_pixels


class Tray:
    """Wraps pystray. Callbacks run on pystray's thread, so keep them to queue puts."""

    def __init__(
        self,
        on_open: Callable[[], None],
        on_check: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._counts = (0, 0)
        self._size = tray_pixels()
        self._icon = pystray.Icon(
            "carolos",
            tray_icon(0, 0, self._size),
            "CaroLOS",
            menu=pystray.Menu(
                pystray.MenuItem("Open CaroLOS", lambda: on_open(), default=True),
                pystray.MenuItem("Check for updates", lambda: on_check()),
                pystray.MenuItem("Quit", lambda: on_quit()),
            ),
        )

    def start(self) -> None:
        self._icon.run_detached()

    def stop(self) -> None:
        self._icon.stop()

    def update(self, running: int, total: int) -> None:
        """Redraw the count badge and refresh the tooltip."""
        if (running, total) != self._counts:
            self._counts = (running, total)
            self._icon.icon = tray_icon(running, total, self._size)
        self._icon.title = f"CaroLOS: {running} of {total} tools on"
