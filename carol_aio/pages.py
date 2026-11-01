"""Pages that show inside the flyout: a tool's settings, and update notices.

The flyout is one bubble with her in the header; these are the rooms below it, so settings and
updates live in the same place as the tools list instead of in windows of their own.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from carol_aio import theme
from carol_aio.icon import settings_art_photo
from carol_aio.theme import FONT, px
from carol_aio.tool import Field, Tool
from carol_aio.widgets import Dropdown, PillButton, Segmented, Switch, flat_button, heading


@dataclass(frozen=True)
class Choice:
    label: str
    command: Callable[[], None] | None = None
    primary: bool = False
    keep_open: bool = False  # stay on the page after the click (it shows progress)


def _noop() -> None:
    pass


class SettingsPage(tk.Frame):
    """A tool's settings, generated from its ``fields``; saving writes them to config.yaml."""

    def __init__(
        self,
        parent: tk.Misc,
        tool: Tool,
        on_save: Callable[[Tool, dict[str, Any]], None],
        on_close: Callable[[], None],
        on_change: Callable[[], None] = _noop,
    ) -> None:
        super().__init__(parent, bg=theme.PANEL)
        self.tool, self.on_save, self.on_close, self.on_change = tool, on_save, on_close, on_change
        self.vars: dict[str, tk.BooleanVar | tk.StringVar] = {}
        self.setters: dict[str, Callable[[Any], None]] = {}
        self.shown = [f for f in tool.fields if not f.advanced]
        wrap = px(theme.PAGE_WIDTH) - px(36)

        heading(self, "Settings").pack(fill="x", pady=(px(2), 0))
        tk.Label(
            self,
            text=tool.name,
            font=(FONT, 11, "bold"),
            fg=theme.TEXT,
            bg=theme.PANEL,
            anchor="w",
            padx=px(18),
        ).pack(fill="x", pady=(px(12), 0))
        body = tk.Frame(self, bg=theme.PANEL, padx=px(18))
        body.pack(fill="x", pady=(px(10), 0))
        if not self.shown:
            tk.Label(
                body,
                text="This tool has no settings.",
                font=(FONT, 10),
                fg=theme.MUTED,
                bg=theme.PANEL,
            ).pack(anchor="w")
        for f in self.shown:
            self._add_field(body, f, wrap)

        self.error = tk.StringVar()
        tk.Label(
            self,
            textvariable=self.error,
            font=(FONT, 9),
            fg=theme.FAULT,
            bg=theme.PANEL,
            anchor="w",
            justify="left",
            wraplength=wrap,
            padx=px(18),
        ).pack(fill="x")

        # A small, faint car "driving" along the buttons' divider: its tyres sit right on the line.
        self._art = settings_art_photo(px(104))  # kept so Tk doesn't drop it
        tk.Label(self, image=self._art, bg=theme.PANEL, bd=0, padx=0, pady=0).pack(
            anchor="w", padx=(px(20), 0)
        )

        tk.Frame(self, bg=theme.LINE, height=1).pack(fill="x")
        footer = tk.Frame(self, bg=theme.PANEL, padx=px(12), pady=px(10))
        footer.pack(fill="x")
        flat_button(footer, "Reset to defaults", self._reset, quiet=True).pack(side="left")
        PillButton(footer, "Save", self._save, primary=True).pack(side="right")
        flat_button(footer, "Cancel", self._close, quiet=True).pack(side="right", padx=(0, px(6)))

    def _caption(self, parent: tk.Misc, text: str, wrap: int, pad: int = 6) -> tk.Label:
        label = tk.Label(
            parent,
            text=text,
            font=(FONT, 9),
            fg=theme.MUTED,
            bg=theme.PANEL,
            anchor="w",
            justify="left",
            wraplength=wrap,
        )
        label.pack(fill="x", pady=(px(pad), 0))
        return label

    def _add_field(self, body: tk.Frame, f: Field, wrap: int) -> None:
        value = self.tool.settings[f.key]
        block = tk.Frame(body, bg=theme.PANEL)
        block.pack(fill="x", pady=(0, px(14)))
        top = tk.Frame(block, bg=theme.PANEL)
        top.pack(fill="x")
        tk.Label(top, text=f.label, font=(FONT, 10), fg=theme.TEXT, bg=theme.PANEL).pack(
            side="left"
        )

        if f.type is bool:
            flag = tk.BooleanVar(value=value)
            switch = Switch(top, value, flag.set)
            switch.pack(side="right")
            self.vars[f.key], self.setters[f.key] = flag, lambda v: switch.set(bool(v))
        elif f.choices:
            text = tk.StringVar(value=value)
            hints = {key: hint_text for key, _label, hint_text in f.choices}
            hint_label: list[tk.Label] = []

            def changed(key: str) -> None:
                text.set(key)
                hint_label[0].configure(text=hints[key])

            choice = Segmented(block, [(k, lbl) for k, lbl, _ in f.choices], value, changed)
            choice.pack(fill="x", pady=(px(6), 0))
            hint_label.append(self._caption(block, hints.get(value, ""), wrap))

            def apply_choice(v: Any) -> None:
                choice.set(v)
                changed(v)

            self.vars[f.key], self.setters[f.key] = text, apply_choice
        elif f.picker:
            text = tk.StringVar(value=value)
            dropdown = Dropdown(block, self.tool.options(f.key), value, text.set)
            dropdown.pack(fill="x", pady=(px(6), 0))

            def apply_pick(v: Any) -> None:
                dropdown.set(v)
                text.set(v)

            self.vars[f.key], self.setters[f.key] = text, apply_pick
        else:
            text = tk.StringVar(value=str(value))
            entry = tk.Entry(
                block,
                textvariable=text,
                font=(FONT, 10),
                bg=theme.RAISED,
                fg=theme.TEXT,
                insertbackground=theme.TEXT,
                relief="flat",
                highlightthickness=2,
                highlightbackground=theme.OUTLINE,
                highlightcolor=theme.ACCENT,
            )
            entry.pack(fill="x", pady=(px(6), 0), ipady=px(5))
            entry.bind("<Return>", lambda _e: self._save())
            self.vars[f.key] = text
        if f.help:
            self._caption(block, f.help, wrap)

    def _set_error(self, message: str) -> None:
        self.error.set(message)
        self.on_change()  # the page may have grown or shrunk

    def _reset(self) -> None:
        for f in self.shown:
            self.vars[f.key].set(f.default)
            if f.key in self.setters:
                self.setters[f.key](f.default)
        self._set_error("")

    def escape(self) -> None:
        """Escape leaves the settings, like Cancel."""
        self._close()

    def _close(self) -> None:
        """Go back to the tools page (Cancel, Save and Escape)."""
        self.on_close()

    def _save(self) -> None:
        values = dict(self.tool.settings)  # keep settings this page doesn't show
        for f in self.shown:
            try:
                values[f.key] = f.coerce(self.vars[f.key].get())
            except ValueError as exc:
                self._set_error(f"{f.label}: {exc}")
                return
        self.on_save(self.tool, values)
        self._close()


class NoticePage(tk.Frame):
    """A message with buttons and an optional progress bar: update offers, results and progress."""

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        message: str,
        choices: list[Choice],
        detail: str = "",
        on_change: Callable[[], None] = _noop,
        on_done: Callable[[], None] = _noop,
    ) -> None:
        super().__init__(parent, bg=theme.PANEL)
        self.on_change, self.on_done = on_change, on_done
        self.busy = False  # a download is running: keep this page if the panel is hidden
        self._choices: list[Choice] = []
        self._buttons: list[tk.Button | PillButton] = []
        self._fraction: float | None = None
        wrap = px(theme.PAGE_WIDTH) - px(36)

        self.title = heading(self, title)
        self.title.pack(fill="x", pady=(px(2), 0))
        body = tk.Frame(self, bg=theme.PANEL, padx=px(18), pady=px(12))
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
        self.detail = tk.Label(
            body,
            font=(FONT, 9),
            fg=theme.MUTED,
            bg=theme.PANEL,
            anchor="w",
            justify="left",
            wraplength=wrap,
        )
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

        tk.Frame(self, bg=theme.LINE, height=1).pack(fill="x")
        self.footer = tk.Frame(self, bg=theme.PANEL, padx=px(12), pady=px(10))
        self.footer.pack(fill="x")
        self.set_detail(detail)
        self.set_choices(choices)

    def update_content(
        self, title: str, message: str, choices: list[Choice], detail: str = ""
    ) -> None:
        """Replace everything on the page (a "checking" page becomes a result, for example)."""
        self.title.configure(text=title)
        self.message.configure(text=message)
        self.busy = False
        self.set_progress(None)
        self.set_status("")
        self.set_detail(detail)
        self.set_choices(choices)

    def set_detail(self, text: str) -> None:
        self.detail.configure(text=text)
        if text:
            self.detail.pack(fill="x", pady=(px(10), 0))
        else:
            self.detail.pack_forget()
        self.on_change()

    def set_choices(self, choices: list[Choice]) -> None:
        """Replace the footer buttons; the primary one is a pink pill on the right."""
        for old in self._buttons:
            old.destroy()
        self._choices, self._buttons = choices, []
        for choice in sorted(choices, key=lambda c: c.primary, reverse=True):
            button: tk.Button | PillButton
            if choice.primary:
                button = PillButton(
                    self.footer, choice.label, lambda c=choice: self._click(c), primary=True  # type: ignore[misc]
                )
            else:
                button = flat_button(
                    self.footer, choice.label, lambda c=choice: self._click(c), quiet=True  # type: ignore[misc]
                )
            button.pack(side="right", padx=(px(4), 0))
            self._buttons.append(button)
        self.on_change()

    def lock(self, locked: bool) -> None:
        """Disable the buttons while something is happening (a download)."""
        self.busy = locked
        for button in self._buttons:
            if isinstance(button, PillButton):
                button.enable(not locked)
            else:
                button.configure(state="disabled" if locked else "normal")

    def set_message(self, text: str) -> None:
        self.message.configure(text=text)
        self.on_change()

    def set_status(self, text: str, fault: bool = False) -> None:
        self.status.configure(text=text, fg=theme.FAULT if fault else theme.MUTED)
        if text and not self.status.winfo_ismapped():
            self.status.pack(fill="x", pady=(px(10), 0))
        elif not text:
            self.status.pack_forget()
        self.on_change()

    def set_progress(self, fraction: float | None) -> None:
        """Show a bar at ``fraction`` (0-1), or hide it with None."""
        self._fraction = fraction
        if fraction is None:
            self.bar.pack_forget()
            self.on_change()
            return
        if not self.bar.winfo_ismapped():
            self.bar.pack(fill="x", pady=(px(12), 0))
            self.on_change()
        self._draw_bar()

    def _draw_bar(self) -> None:
        self.bar.delete("all")
        width, height = self.bar.winfo_width(), px(6)
        self.bar.create_rectangle(0, 0, width, height, fill=theme.LINE, outline="")
        if self._fraction is not None:
            self.bar.create_rectangle(
                0, 0, width * self._fraction, height, fill=theme.ACCENT, outline=""
            )

    def dismiss(self) -> None:
        """Leave this page and go back to the tools."""
        self.on_done()

    def _click(self, choice: Choice) -> None:
        if not choice.keep_open:
            self.on_done()
        if choice.command is not None:
            choice.command()

    def escape(self) -> None:
        """Escape picks the first non-primary choice (Later, Close...), else just leaves."""
        if self.busy:
            return
        for choice in self._choices:
            if not choice.primary:
                self._click(choice)
                return
        self.on_done()

    def enter(self) -> None:
        if self.busy:
            return
        for choice in self._choices:
            if choice.primary:
                self._click(choice)
                return
