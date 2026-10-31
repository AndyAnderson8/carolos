"""A small themed message box with buttons and an optional progress bar.

Used for the update prompt and update results, so they look like the rest of
the app. It is a borderless card centred on the screen.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass

from carol_aio import theme
from carol_aio.theme import FONT, px
from carol_aio.widgets import flat_button

WIDTH = 420


@dataclass(frozen=True)
class Choice:
    label: str
    command: Callable[[], None] | None = None
    primary: bool = False
    keep_open: bool = False  # leave the dialog up after the click (it shows progress)


class Prompt(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        message: str,
        choices: list[Choice],
        detail: str = "",
    ) -> None:
        super().__init__(parent, bg=theme.LINE)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self._choices: list[Choice] = []
        self._buttons: list[tk.Button] = []
        self._fraction: float | None = None
        wrap = px(WIDTH) - px(36) - 2

        panel = tk.Frame(self, bg=theme.PANEL)
        panel.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Label(
            panel,
            text=title,
            font=(FONT, 11, "bold"),
            fg=theme.TEXT,
            bg=theme.PANEL,
            anchor="w",
            padx=px(18),
            pady=px(12),
        ).pack(fill="x")
        tk.Frame(panel, bg=theme.LINE, height=1).pack(fill="x")

        body = tk.Frame(panel, bg=theme.PANEL, padx=px(18), pady=px(16))
        body.pack(fill="x")
        self.message = tk.Label(
            body,
            text=message,
            font=(FONT, 10),
            fg=theme.TEXT,
            bg=theme.PANEL,
            anchor="w",
            justify="left",
            wraplength=wrap,
        )
        self.message.pack(fill="x")
        if detail:
            tk.Label(
                body,
                text=detail,
                font=(FONT, 9),
                fg=theme.MUTED,
                bg=theme.PANEL,
                anchor="w",
                justify="left",
                wraplength=wrap,
            ).pack(fill="x", pady=(px(10), 0))
        self.bar = tk.Canvas(body, height=px(6), bg=theme.PANEL, highlightthickness=0)
        self.bar.bind("<Configure>", lambda _e: self._draw_bar())
        self.status = tk.Label(
            body,
            font=(FONT, 9),
            fg=theme.MUTED,
            bg=theme.PANEL,
            anchor="w",
            justify="left",
            wraplength=wrap,
        )

        tk.Frame(panel, bg=theme.LINE, height=1).pack(fill="x")
        self.footer = tk.Frame(panel, bg=theme.PANEL, padx=px(12), pady=px(10))
        self.footer.pack(fill="x")
        self.set_choices(choices)

        self.bind("<Escape>", lambda _e: self._escape())
        self.bind("<Return>", lambda _e: self._enter())
        self._fit()
        self.after_idle(self.focus_force)

    def _fit(self) -> None:
        """Size the card to its content and centre it; called whenever the content changes."""
        self.update_idletasks()
        left, top, right, bottom = theme.work_area(self)
        w, h = px(WIDTH), self.winfo_reqheight()
        self.geometry(f"{w}x{h}+{(left + right - w) // 2}+{(top + bottom - h) // 2}")

    def set_choices(self, choices: list[Choice]) -> None:
        """Replace the footer buttons; the primary one goes rightmost."""
        for button in self._buttons:
            button.destroy()
        self._choices, self._buttons = choices, []
        for choice in sorted(choices, key=lambda c: c.primary, reverse=True):
            button = flat_button(
                self.footer,
                choice.label,
                lambda c=choice: self._click(c),  # type: ignore[misc]
                primary=choice.primary,
                quiet=not choice.primary,
            )
            button.pack(side="right", padx=(px(4), 0))
            self._buttons.append(button)
        self._fit()

    def lock(self, locked: bool) -> None:
        for button in self._buttons:
            button.configure(state="disabled" if locked else "normal")

    def set_message(self, text: str) -> None:
        self.message.configure(text=text)
        self._fit()

    def set_status(self, text: str, fault: bool = False) -> None:
        self.status.configure(text=text, fg=theme.FAULT if fault else theme.MUTED)
        if text and not self.status.winfo_ismapped():
            self.status.pack(fill="x", pady=(px(10), 0))
        elif not text:
            self.status.pack_forget()
        self._fit()

    def set_progress(self, fraction: float | None) -> None:
        """Show a bar at ``fraction`` (0-1), or hide it with None."""
        self._fraction = fraction
        if fraction is None:
            self.bar.pack_forget()
            self._fit()
            return
        if not self.bar.winfo_ismapped():
            self.bar.pack(fill="x", pady=(px(12), 0))
            self._fit()
        self._draw_bar()

    def _draw_bar(self) -> None:
        self.bar.delete("all")
        width, height = self.bar.winfo_width(), px(6)
        self.bar.create_rectangle(0, 0, width, height, fill=theme.LINE, outline="")
        if self._fraction is not None:
            self.bar.create_rectangle(
                0, 0, width * self._fraction, height, fill=theme.ACCENT, outline=""
            )

    def _click(self, choice: Choice) -> None:
        if not choice.keep_open:
            self.destroy()
        if choice.command is not None:
            choice.command()

    def _escape(self) -> None:
        """Escape picks the first non-primary choice (Later, Cancel...), else just closes."""
        for choice in self._choices:
            if not choice.primary:
                self._click(choice)
                return
        self.destroy()

    def _enter(self) -> None:
        for choice in self._choices:
            if choice.primary:
                self._click(choice)
                return
