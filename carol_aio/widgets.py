"""Small custom widgets: switch, pill and flat buttons, headings, choice control, dropdown."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Callable
from functools import partial

from carol_aio import theme
from carol_aio.theme import FONT, px

SLIDE_STEPS = 6
SLIDE_MS = 12
CHEVRON = "▾"


def draw_pill(canvas: tk.Canvas, x0: float, y0: float, x1: float, y1: float, color: str) -> None:
    """A filled pill (a rectangle with round ends) on ``canvas``."""
    r = y1 - y0
    canvas.create_oval(x0, y0, x0 + r, y1, fill=color, outline=color)
    canvas.create_oval(x1 - r, y0, x1, y1, fill=color, outline=color)
    canvas.create_rectangle(x0 + r / 2, y0, x1 - r / 2, y1, fill=color, outline=color)


def heading(parent: tk.Misc, text: str) -> tk.Label:
    """An underlined section heading, like "Tools". Pack it with ``fill="x"``."""
    return tk.Label(
        parent,
        text=text,
        font=(FONT, 10, "bold", "underline"),
        fg=theme.MUTED,
        bg=theme.PANEL,
        anchor="w",
        padx=px(18),
    )


class Switch(tk.Canvas):
    """On/off switch. The track turns the accent colour and the knob slides across."""

    def __init__(
        self,
        parent: tk.Misc,
        value: bool,
        command: Callable[[bool], None],
        bg: str | None = None,
    ) -> None:
        bg = bg or theme.PANEL
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
        pad, edge, gap = px(2), px(2), px(2)
        lit = self._pos > 0.5
        x0, y0, x1, y1 = pad, pad, self._width - pad, self._height - pad
        draw_pill(
            self, x0, y0, x1, y1, theme.OUTLINE
        )  # the chunky outline, then the track inside it
        draw_pill(
            self, x0 + edge, y0 + edge, x1 - edge, y1 - edge, theme.ACCENT if lit else theme.LINE
        )
        inner_h = y1 - y0 - 2 * edge
        knob = inner_h - 2 * gap
        travel = x1 - x0 - 2 * edge - 2 * gap - knob
        left = x0 + edge + gap + travel * self._pos
        top = y0 + edge + gap
        self.create_oval(
            left,
            top,
            left + knob,
            top + knob,
            fill=theme.ON_ACCENT if lit else theme.MUTED,
            outline="",
        )


class GearButton(tk.Label):
    """Flat icon (a gear by default) that brightens on hover and responds to the keyboard."""

    def __init__(
        self,
        parent: tk.Misc,
        command: Callable[[], None],
        bg: str | None = None,
        glyph: str = "⚙",
        size: int = 14,
        color: str | None = None,
        hover: str | None = None,
    ) -> None:
        bg = bg or theme.PANEL
        color, hover = color or theme.MUTED, hover or theme.TEXT
        super().__init__(
            parent,
            text=glyph,
            font=(theme.SYMBOLS, size),
            fg=color,
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
        self.bind("<Enter>", lambda _e: self.configure(fg=hover))
        self.bind("<Leave>", lambda _e: self.configure(fg=color))


def flat_button(
    parent: tk.Misc,
    text: str,
    command: Callable[[], None],
    primary: bool = False,
    quiet: bool = False,
) -> tk.Button:
    """Flat button: the accent colour when primary, plain muted text when quiet."""
    bg = theme.ACCENT if primary else theme.PANEL if quiet else theme.RAISED
    fg = theme.ON_ACCENT if primary else theme.MUTED if quiet else theme.TEXT
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=(FONT, 10, "bold" if primary else "normal"),
        bg=bg,
        fg=fg,
        activebackground=bg,
        activeforeground=theme.ON_ACCENT if primary else theme.TEXT,
        relief="flat",
        bd=0,
        padx=px(14),
        pady=px(5),
        cursor="hand2",
        highlightthickness=2,
        highlightbackground=theme.OUTLINE if primary else theme.PANEL,
        highlightcolor=theme.TEXT,
    )


class PillButton(tk.Canvas):
    """A pill-shaped, outlined button, like the switch. The primary one is the accent colour."""

    def __init__(
        self,
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
        primary: bool = False,
        bg: str | None = None,
    ) -> None:
        bg = bg or theme.PANEL
        self._font = tkfont.Font(family=FONT, size=10, weight="bold")
        self._width = self._font.measure(text) + 2 * px(20)
        self._height = self._font.metrics("linespace") + 2 * px(7)
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
        self.text, self.command, self.primary = text, command, primary
        self._enabled = True
        self.bind("<Button-1>", self._clicked)
        self.bind("<Return>", self._clicked)
        self.bind("<space>", self._clicked)
        self._draw()

    def enable(self, on: bool) -> None:
        self._enabled = on
        self.configure(cursor="hand2" if on else "arrow")
        self._draw()

    def invoke(self) -> None:
        """Press the button (nothing happens while it is disabled)."""
        if self._enabled:
            self.command()

    def _clicked(self, _event: object) -> None:
        self.focus_set()
        self.invoke()

    def _draw(self) -> None:
        self.delete("all")
        pad, edge = px(2), px(2)
        x0, y0, x1, y1 = pad, pad, self._width - pad, self._height - pad
        draw_pill(self, x0, y0, x1, y1, theme.OUTLINE if self._enabled else theme.LINE)
        fill = theme.ACCENT if self.primary else theme.RAISED
        draw_pill(
            self, x0 + edge, y0 + edge, x1 - edge, y1 - edge, fill if self._enabled else theme.LINE
        )
        ink = theme.ON_ACCENT if self.primary else theme.TEXT
        self.create_text(
            self._width / 2,
            self._height / 2,
            text=self.text,
            font=self._font,
            fill=ink if self._enabled else theme.MUTED,
        )


class Segmented(tk.Frame):
    """A few mutually exclusive choices side by side; arrow keys move the selection."""

    def __init__(
        self,
        parent: tk.Misc,
        options: list[tuple[str, str]],
        value: str,
        on_change: Callable[[str], None],
    ) -> None:
        super().__init__(
            parent,
            bg=theme.RAISED,
            padx=px(3),
            pady=px(3),
            highlightthickness=2,
            highlightbackground=theme.PANEL,
            highlightcolor=theme.TEXT,
            takefocus=True,
        )
        self.options, self.value, self._on_change = options, value, on_change
        self._labels: dict[str, tk.Label] = {}
        for column, (key, text) in enumerate(options):
            self.columnconfigure(column, weight=1, uniform="segment")
            label = tk.Label(
                self, text=text, font=(FONT, 10), pady=px(5), cursor="hand2", bg=theme.RAISED
            )
            label.grid(row=0, column=column, sticky="nsew")
            label.bind("<Button-1>", partial(self._clicked, key))
            self._labels[key] = label
        self.bind("<Left>", lambda _e: self._step(-1))
        self.bind("<Right>", lambda _e: self._step(1))
        self._paint()

    def set(self, value: str) -> None:
        """Select ``value`` without firing the callback."""
        self.value = value
        self._paint()

    def _clicked(self, key: str, _event: object) -> None:
        self._pick(key)

    def _pick(self, key: str) -> None:
        self.focus_set()
        if key != self.value:
            self.set(key)
            self._on_change(key)

    def _step(self, direction: int) -> None:
        keys = [k for k, _ in self.options]
        index = min(max(keys.index(self.value) + direction, 0), len(keys) - 1)
        self._pick(keys[index])

    def _paint(self) -> None:
        for key, label in self._labels.items():
            chosen = key == self.value
            label.configure(
                bg=theme.SELECTED if chosen else theme.RAISED,
                fg=theme.TEXT if chosen else theme.MUTED,
            )


class Dropdown(tk.Frame):
    """A closed box showing the current choice; clicking lists the options below it."""

    def __init__(
        self,
        parent: tk.Misc,
        options: list[tuple[str, str]],
        value: str,
        on_change: Callable[[str], None],
    ) -> None:
        super().__init__(
            parent,
            bg=theme.RAISED,
            highlightthickness=2,
            highlightbackground=theme.OUTLINE,
            highlightcolor=theme.ACCENT,
            takefocus=True,
            cursor="hand2",
        )
        self.options, self.value, self._on_change = options, value, on_change
        self._popup: tk.Toplevel | None = None
        self.text = tk.Label(
            self, font=(FONT, 10), fg=theme.TEXT, bg=theme.RAISED, anchor="w", cursor="hand2"
        )
        self.text.pack(side="left", fill="x", expand=True, padx=(px(10), 0), pady=px(6))
        tk.Label(
            self, text=CHEVRON, font=(theme.SYMBOLS, 10), fg=theme.MUTED, bg=theme.RAISED
        ).pack(side="right", padx=px(10))
        for widget in (self, self.text, *self.winfo_children()):
            widget.bind("<Button-1>", lambda _e: self._toggle())
        self.bind("<space>", lambda _e: self._toggle())
        self.bind("<Return>", lambda _e: self._toggle())
        self._show_value()

    def set(self, value: str) -> None:
        """Select ``value`` without firing the callback."""
        self.value = value
        self._show_value()

    def _label_for(self, value: str) -> str:
        return next((label for key, label in self.options if key == value), value)

    def _show_value(self) -> None:
        self.text.configure(text=self._label_for(self.value))

    def _toggle(self) -> None:
        self.focus_set()
        if self._popup is not None:
            self._close()
        else:
            self._open()

    def _open(self) -> None:
        popup = tk.Toplevel(self, bg=theme.OUTLINE)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        inner = tk.Frame(popup, bg=theme.RAISED)
        inner.pack(fill="both", expand=True, padx=px(2), pady=px(2))
        for key, label in self.options:
            row = tk.Frame(inner, bg=theme.RAISED, cursor="hand2")
            row.pack(fill="x")
            dot = tk.Label(
                row,
                text="●" if key == self.value else "",
                font=(theme.SYMBOLS, 7),
                fg=theme.ACCENT,
                bg=theme.RAISED,
                width=2,
            )
            dot.pack(side="left", padx=(px(6), 0))
            name = tk.Label(
                row, text=label, font=(FONT, 10), fg=theme.TEXT, bg=theme.RAISED, anchor="w"
            )
            name.pack(side="left", fill="x", expand=True, pady=px(6), padx=(0, px(10)))
            for widget in (row, dot, name):
                widget.bind("<Button-1>", partial(self._chosen, key))
                widget.bind("<Enter>", partial(self._hovered, row, True))
                widget.bind("<Leave>", partial(self._hovered, row, False))
        popup.bind("<Escape>", lambda _e: self._close())
        popup.bind("<FocusOut>", lambda _e: popup.after(100, self._close_if_unfocused))
        self._popup = popup

        popup.update_idletasks()
        width, height = self.winfo_width(), popup.winfo_reqheight()
        _, top, _, bottom = theme.work_area(self)
        x, y = self.winfo_rootx(), self.winfo_rooty() + self.winfo_height() + px(2)
        if y + height > bottom:  # no room below: open upward
            y = max(top, self.winfo_rooty() - height - px(2))
        popup.geometry(f"{width}x{height}+{x}+{y}")
        popup.focus_force()

    def _chosen(self, key: str, _event: object) -> None:
        self._choose(key)

    @staticmethod
    def _hovered(row: tk.Frame, on: bool, _event: object) -> None:
        color = theme.SELECTED if on else theme.RAISED
        row.configure(bg=color)
        for child in row.winfo_children():
            child.configure(bg=color)  # type: ignore[call-arg]

    def _choose(self, key: str) -> None:
        self._close()
        if key != self.value:
            self.set(key)
            self._on_change(key)

    def _close_if_unfocused(self) -> None:
        if self._popup is not None and self._popup.focus_displayof() is None:
            self._close(refocus=False)  # the person clicked into another app; leave focus there

    def _close(self, refocus: bool = True) -> None:
        if self._popup is not None:
            popup, self._popup = self._popup, None
            popup.destroy()
            if refocus:  # give focus back to our window so it doesn't think it was clicked away
                self.winfo_toplevel().focus_force()
