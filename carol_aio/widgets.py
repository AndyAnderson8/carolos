"""Small custom widgets: the lamp switch, the gear button and flat buttons."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from carol_aio import theme
from carol_aio.theme import px

SLIDE_STEPS = 6
SLIDE_MS = 12


class Switch(tk.Canvas):
    """On/off switch. The track lights up amber and the knob slides across."""

    def __init__(
        self,
        parent: tk.Misc,
        value: bool,
        command: Callable[[bool], None],
        bg: str = theme.PANEL,
    ) -> None:
        self._width, self._height = px(40), px(22)
        super().__init__(
            parent,
            width=self._width,
            height=self._height,
            bg=bg,
            highlightthickness=2,
            highlightbackground=bg,
            highlightcolor=theme.TEXT,
            cursor="hand2",
            takefocus=True,
        )
        self.command = command
        self.value = value
        self._pos = 1.0 if value else 0.0
        self._after: str | None = None
        self.bind("<Button-1>", self._clicked)
        self.bind("<space>", self._clicked)
        self.bind("<Return>", self._clicked)
        self._draw()

    def set(self, value: bool) -> None:
        """Show ``value`` without firing the command."""
        if value != self.value:
            self.value = value
            self._slide(1.0 if value else 0.0)

    def _clicked(self, _event: object) -> None:
        self.focus_set()
        self.value = not self.value
        self._slide(1.0 if self.value else 0.0)
        self.command(self.value)

    def _slide(self, target: float, step: int = 0) -> None:
        if self._after is not None:
            self.after_cancel(self._after)
            self._after = None
        if step == 0:
            self._start = self._pos
        if step >= SLIDE_STEPS:
            self._pos = target
            self._draw()
            return
        self._pos = self._start + (target - self._start) * (step + 1) / SLIDE_STEPS
        self._draw()
        self._after = self.after(SLIDE_MS, self._slide, target, step + 1)

    def _draw(self) -> None:
        self.delete("all")
        pad, w, h = px(2), self._width, self._height
        lit = self._pos > 0.5
        track = theme.LAMP if lit else theme.LINE
        r = h - 2 * pad
        x0, y0, x1, y1 = pad, pad, w - pad, h - pad
        self.create_oval(x0, y0, x0 + r, y1, fill=track, outline=track)
        self.create_oval(x1 - r, y0, x1, y1, fill=track, outline=track)
        self.create_rectangle(x0 + r // 2, y0, x1 - r // 2, y1, fill=track, outline=track)
        knob = r - 2 * px(3)
        left = x0 + px(3) + (x1 - x0 - 2 * px(3) - knob) * self._pos
        self.create_oval(
            left,
            y0 + px(3),
            left + knob,
            y0 + px(3) + knob,
            fill=theme.ON_LAMP if lit else theme.MUTED,
            outline="",
        )


class GearButton(tk.Label):
    """Flat gear icon that brightens on hover and responds to the keyboard."""

    def __init__(self, parent: tk.Misc, command: Callable[[], None], bg: str = theme.PANEL) -> None:
        super().__init__(
            parent,
            text="⚙",
            font=(theme.SYMBOLS, 14),
            fg=theme.MUTED,
            bg=bg,
            cursor="hand2",
            takefocus=True,
            highlightthickness=2,
            highlightbackground=bg,
            highlightcolor=theme.TEXT,
            padx=px(4),
        )
        self.bind("<Button-1>", lambda _e: command())
        self.bind("<Return>", lambda _e: command())
        self.bind("<space>", lambda _e: command())
        self.bind("<Enter>", lambda _e: self.configure(fg=theme.TEXT))
        self.bind("<Leave>", lambda _e: self.configure(fg=theme.MUTED))


def flat_button(
    parent: tk.Misc, text: str, command: Callable[[], None], primary: bool = False
) -> tk.Button:
    """Flat button; the primary one is the amber lamp color."""
    bg = theme.LAMP if primary else theme.RAISED
    fg = theme.ON_LAMP if primary else theme.TEXT
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=(theme.FONT, 10, "bold" if primary else "normal"),
        bg=bg,
        fg=fg,
        activebackground=bg,
        activeforeground=fg,
        relief="flat",
        bd=0,
        padx=px(14),
        pady=px(5),
        cursor="hand2",
        highlightthickness=2,
        highlightbackground=theme.PANEL,
        highlightcolor=theme.TEXT,
    )
