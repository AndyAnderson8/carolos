"""Tray app: a lamp-switch flyout for the tools, and a small settings window per tool."""

from __future__ import annotations

import argparse
import queue
import time
import tkinter as tk
from collections.abc import Callable
from typing import Any

from carol_aio import __version__, theme
from carol_aio.config import ENV_VAR, Config, ConfigError, set_config_path
from carol_aio.theme import FONT, px
from carol_aio.tool import Field, Tool
from carol_aio.tools import create_tools
from carol_aio.tray import Tray
from carol_aio.widgets import Dropdown, GearButton, Segmented, Switch, flat_button

CONFIG_POLL_MS = 1000
QUEUE_POLL_MS = 100
REOPEN_GUARD_S = 0.3  # the tray click that dismissed the panel must not reopen it
FLYOUT_WIDTH = 340
EDGE_GAP = 12


class SettingsDialog(tk.Toplevel):
    """Form generated from a tool's ``fields``; saving writes to config.yaml.

    A borderless card like the flyout, anchored to the same corner.
    """

    def __init__(
        self,
        parent: tk.Tk,
        tool: Tool,
        on_save: Callable[[Tool, dict[str, Any]], None],
        anchor: tuple[int, int],
    ) -> None:
        super().__init__(parent, bg=theme.LINE)
        self.tool, self.on_save = tool, on_save
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.vars: dict[str, tk.BooleanVar | tk.StringVar] = {}
        self.setters: dict[str, Callable[[Any], None]] = {}
        self.shown = [f for f in tool.fields if not f.advanced]
        self.width = px(FLYOUT_WIDTH)
        wrap = self.width - px(36) - 2

        panel = tk.Frame(self, bg=theme.PANEL)
        panel.pack(fill="both", expand=True, padx=1, pady=1)
        header = tk.Frame(panel, bg=theme.PANEL, padx=px(18), pady=px(10))
        header.pack(fill="x")
        tk.Label(
            header, text=tool.name, font=(FONT, 11, "bold"), fg=theme.TEXT, bg=theme.PANEL
        ).pack(side="left")
        GearButton(header, self.destroy, glyph="\u2715", size=11).pack(side="right")
        tk.Frame(panel, bg=theme.LINE, height=1).pack(fill="x")

        body = tk.Frame(panel, bg=theme.PANEL, padx=px(18), pady=px(16))
        body.pack(fill="x")
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
            panel,
            textvariable=self.error,
            font=(FONT, 9),
            fg=theme.FAULT,
            bg=theme.PANEL,
            anchor="w",
            justify="left",
            wraplength=wrap,
            padx=px(18),
        ).pack(fill="x")

        tk.Frame(panel, bg=theme.LINE, height=1).pack(fill="x", pady=(px(8), 0))
        footer = tk.Frame(panel, bg=theme.PANEL, padx=px(12), pady=px(10))
        footer.pack(fill="x")
        flat_button(footer, "Reset to defaults", self._reset, quiet=True).pack(side="left")
        flat_button(footer, "Save", self._save, primary=True).pack(side="right")
        flat_button(footer, "Cancel", self.destroy, quiet=True).pack(side="right", padx=(0, px(4)))

        self.bind("<Escape>", lambda _e: self.destroy())
        self._place(anchor)
        self.after_idle(self.focus_force)

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
        block.pack(fill="x", pady=(0, px(16)))
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
                highlightthickness=1,
                highlightbackground=theme.LINE,
                highlightcolor=theme.LAMP,
            )
            entry.pack(fill="x", pady=(px(6), 0), ipady=px(5))
            entry.bind("<Return>", lambda _e: self._save())
            self.vars[f.key] = text
        if f.help:
            self._caption(block, f.help, wrap)

    def _place(self, anchor: tuple[int, int]) -> None:
        """Put the bottom-right corner at ``anchor``, kept on screen."""
        self.update_idletasks()
        left, top, right, bottom = theme.work_area(self)
        h = self.winfo_reqheight()
        x = max(left, min(anchor[0] - self.width, right - self.width))
        y = max(top, min(anchor[1] - h, bottom - h))
        self.geometry(f"{self.width}x{h}+{x}+{y}")

    def _reset(self) -> None:
        for f in self.shown:
            self.vars[f.key].set(f.default)
            if f.key in self.setters:
                self.setters[f.key](f.default)
        self.error.set("")

    def _save(self) -> None:
        values = dict(self.tool.settings)  # keep settings the popup doesn't show
        for f in self.shown:
            try:
                values[f.key] = f.coerce(self.vars[f.key].get())
            except ValueError as exc:
                self.error.set(f"{f.label}: {exc}")
                return
        self.on_save(self.tool, values)
        self.destroy()


class ToolRow(tk.Frame):
    """One tool: name and description on the left, gear and lamp switch on the right."""

    def __init__(
        self,
        parent: tk.Misc,
        tool: Tool,
        on_toggle: Callable[[Tool, bool], None],
        on_gear: Callable[[Tool], None],
    ) -> None:
        super().__init__(parent, bg=theme.PANEL, padx=px(18), pady=px(14))
        self.tool, self._on_toggle = tool, on_toggle
        self.columnconfigure(0, weight=1)
        tk.Label(self, text=tool.name, font=(FONT, 11, "bold"), fg=theme.TEXT, bg=theme.PANEL).grid(
            row=0, column=0, sticky="w"
        )
        tk.Label(
            self,
            text=tool.description,
            font=(FONT, 9),
            fg=theme.MUTED,
            bg=theme.PANEL,
            justify="left",
            anchor="w",
            wraplength=px(FLYOUT_WIDTH - 150),
        ).grid(row=1, column=0, sticky="w", pady=(px(2), 0))
        GearButton(self, lambda: on_gear(tool)).grid(row=0, column=1, rowspan=2, padx=(px(8), 0))
        self.switch = Switch(self, tool.running, self._clicked)
        self.switch.grid(row=0, column=2, rowspan=2, padx=(px(6), 0))

    def sync(self) -> None:
        """Show the tool's real running state."""
        self.switch.set(self.tool.running)

    def _clicked(self, enabled: bool) -> None:
        self._on_toggle(self.tool, enabled)
        self.after(0, self.sync)  # snap back if the tool failed to start


class Flyout(tk.Toplevel):
    """Borderless panel that rises from the bottom-right corner above the taskbar."""

    def __init__(
        self,
        parent: tk.Tk,
        tools: list[Tool],
        on_toggle: Callable[[Tool, bool], None],
        on_gear: Callable[[Tool], None],
    ) -> None:
        super().__init__(parent, bg=theme.LINE)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.withdraw()
        self.rows: dict[str, ToolRow] = {}
        self._hidden_at = 0.0
        self.status = tk.StringVar()

        # The 1px outer frame colour (LINE) shows through as the panel's edge.
        panel = tk.Frame(self, bg=theme.PANEL, width=px(FLYOUT_WIDTH))
        panel.pack(fill="both", expand=True, padx=1, pady=1)
        header = tk.Frame(panel, bg=theme.PANEL, padx=px(18), pady=px(12))
        header.pack(fill="x")
        tk.Label(header, text="Carol AIO", font=(FONT, 10), fg=theme.TEXT, bg=theme.PANEL).pack(
            side="left"
        )
        tk.Label(
            header, text=f"v{__version__}", font=(FONT, 9), fg=theme.MUTED, bg=theme.PANEL
        ).pack(side="right")
        tk.Frame(panel, bg=theme.LINE, height=1).pack(fill="x")

        if not tools:
            tk.Label(
                panel,
                text="No tools installed yet.",
                font=(FONT, 10),
                fg=theme.MUTED,
                bg=theme.PANEL,
                pady=px(20),
            ).pack()
        for i, tool in enumerate(tools):
            if i:
                tk.Frame(panel, bg=theme.LINE, height=1).pack(fill="x", padx=px(18))
            row = ToolRow(panel, tool, on_toggle, on_gear)
            row.pack(fill="x")
            self.rows[tool.key] = row

        self.status_label = tk.Label(
            panel,
            textvariable=self.status,
            font=(FONT, 9),
            fg=theme.FAULT,
            bg=theme.PANEL,
            anchor="w",
            justify="left",
            wraplength=px(FLYOUT_WIDTH - 36),
            padx=px(18),
        )
        self.status.trace_add("write", lambda *_: self._show_status())
        self.bind("<Escape>", lambda _e: self.hide())
        self.bind("<FocusOut>", lambda _e: self.after(80, self._hide_if_unfocused))

    def _show_status(self) -> None:
        if self.status.get():
            self.status_label.pack(fill="x", pady=(0, px(10)))
        else:
            self.status_label.pack_forget()

    def _hide_if_unfocused(self) -> None:
        if self.winfo_viewable() and self.focus_displayof() is None:
            self.hide()

    @property
    def visible(self) -> bool:
        return bool(self.winfo_viewable())

    def corner(self) -> tuple[int, int]:
        """Bottom-right of the work area, where the panel (and settings) anchor."""
        _, _, right, bottom = theme.work_area(self)
        return right - px(EDGE_GAP), bottom - px(EDGE_GAP)

    def show(self) -> None:
        for row in self.rows.values():
            row.sync()
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        right, bottom = self.corner()
        self.geometry(f"{w}x{h}+{right - w}+{bottom - h}")
        self.deiconify()
        self.lift()
        self.focus_force()

    def hide(self) -> None:
        self._hidden_at = time.monotonic()
        self.withdraw()

    def toggle(self) -> None:
        if self.visible:
            self.hide()
        elif time.monotonic() - self._hidden_at > REOPEN_GUARD_S:
            self.show()


class App(tk.Tk):
    def __init__(self, tools: list[Tool] | None = None, config: Config | None = None) -> None:
        theme.enable_dpi_awareness()
        super().__init__()
        theme.init_scale(self)
        self._light = theme.system_is_light()
        theme.use(self._light)
        self.title(f"Carol AIO {__version__}")
        self.withdraw()  # no window of its own; the tray icon is the way in
        self.tools = create_tools() if tools is None else tools
        self.config_store = config or Config()
        self.commands: queue.Queue[str] = queue.Queue()
        self.dialog: SettingsDialog | None = None
        self.flyout = self._build_flyout()
        self.tray = Tray(lambda: self.commands.put("toggle"), lambda: self.commands.put("quit"))

        self._load_config(startup=True)
        self.tray.start()
        self._refresh_tray()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(CONFIG_POLL_MS, self._poll_config)
        self.after(QUEUE_POLL_MS, self._poll_commands)

    def _build_flyout(self) -> Flyout:
        return Flyout(self, self.tools, self.toggle_tool, self.open_settings)

    def _follow_system_theme(self) -> None:
        """Rebuild the panel in the new colours if Windows switched light/dark."""
        light = theme.system_is_light()
        if light == self._light:
            return
        self._light = light
        theme.use(light)
        message = self.flyout.status.get()
        self.flyout.destroy()
        self.flyout = self._build_flyout()
        self.flyout.status.set(message)

    @property
    def status(self) -> tk.StringVar:
        return self.flyout.status

    @property
    def rows(self) -> dict[str, ToolRow]:
        return self.flyout.rows

    def _refresh_tray(self) -> None:
        self.tray.update(sum(t.running for t in self.tools), len(self.tools))

    def _poll_commands(self) -> None:
        """Tray callbacks arrive on another thread; handle them here on Tk's."""
        try:
            while True:
                command = self.commands.get_nowait()
                if command == "quit":
                    self.close()
                    return
                if not self.flyout.visible:
                    self._follow_system_theme()
                self.flyout.toggle()
        except queue.Empty:
            pass
        self.after(QUEUE_POLL_MS, self._poll_commands)

    # --- config <-> tools -------------------------------------------------

    def _load_config(self, startup: bool = False) -> None:
        """Apply config.yaml to every tool; create the file if it is missing."""
        try:
            self.config_store.load()
        except ConfigError as exc:
            self.status.set(str(exc))
            return
        problems: list[str] = []
        for tool in self.tools:
            section = self.config_store.tool_section(tool.key)
            problems += tool.configure(section["settings"])
            if section["enabled"] != tool.running:
                problems += self._set_running(tool, section["enabled"])
            self.rows[tool.key].sync()
        self.status.set("; ".join(problems))
        self._refresh_tray()
        if startup and not self.config_store.path.exists():
            self._write_config()  # first run: write defaults so there is a file to edit

    def _set_running(self, tool: Tool, enabled: bool) -> list[str]:
        try:
            tool.set_enabled(enabled)
        except Exception as exc:
            return [f"{tool.name}: could not start ({exc})"]
        return []

    def _write_config(self) -> None:
        for tool in self.tools:
            self.config_store.set_tool(tool.key, enabled=tool.running, settings=tool.settings)
        try:
            self.config_store.save()
        except OSError as exc:
            self.status.set(f"Could not write {self.config_store.path.name}: {exc}")

    def _poll_config(self) -> None:
        if self.config_store.changed_on_disk():
            self._load_config()
        self.after(CONFIG_POLL_MS, self._poll_config)

    # --- GUI actions ------------------------------------------------------

    def toggle_tool(self, tool: Tool, enabled: bool) -> None:
        problems = self._set_running(tool, enabled)
        self.status.set(problems[0] if problems else "")
        self._write_config()
        self._refresh_tray()

    def open_settings(self, tool: Tool) -> None:
        anchor = self.flyout.corner()
        self.flyout.hide()
        self._follow_system_theme()
        if self.dialog is not None and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.dialog = SettingsDialog(self, tool, self.save_settings, anchor)

    def save_settings(self, tool: Tool, values: dict[str, Any]) -> None:
        tool.configure(values)
        self._write_config()
        self.status.set("")

    def close(self) -> None:
        self.tray.stop()
        for tool in self.tools:
            tool.stop()
        self.destroy()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Carol AIO")
    parser.add_argument(
        "--config",
        metavar="PATH",
        help=f"config file to use (or set ${ENV_VAR}); default: next to the app",
    )
    set_config_path(parser.parse_args(argv).config)
    App().mainloop()
