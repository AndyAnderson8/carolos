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
from carol_aio.tool import Tool
from carol_aio.tools import create_tools
from carol_aio.tray import Tray
from carol_aio.widgets import GearButton, Switch, flat_button

CONFIG_POLL_MS = 1000
QUEUE_POLL_MS = 100
REOPEN_GUARD_S = 0.3  # the tray click that dismissed the panel must not reopen it
FLYOUT_WIDTH = 340
EDGE_GAP = 12


class SettingsDialog(tk.Toplevel):
    """Form generated from a tool's ``fields``; saving writes to config.yaml."""

    def __init__(
        self,
        parent: tk.Tk,
        tool: Tool,
        on_save: Callable[[Tool, dict[str, Any]], None],
        anchor: tuple[int, int],
    ) -> None:
        super().__init__(parent, bg=theme.PANEL)
        self.tool, self.on_save = tool, on_save
        self.title(f"{tool.name} settings")
        self.resizable(False, False)
        self.attributes("-toolwindow", True, "-topmost", True)
        self.vars: dict[str, tk.BooleanVar | tk.StringVar] = {}
        self.switches: dict[str, Switch] = {}

        form = tk.Frame(self, bg=theme.PANEL, padx=px(18), pady=px(16))
        form.pack(fill="both", expand=True)
        form.columnconfigure(0, weight=1)
        if not tool.fields:
            tk.Label(
                form,
                text="This tool has no settings.",
                font=(FONT, 10),
                fg=theme.MUTED,
                bg=theme.PANEL,
            ).grid(row=0, column=0, sticky="w")
        for i, f in enumerate(tool.fields):
            value = tool.settings[f.key]
            cell = tk.Frame(form, bg=theme.PANEL)
            cell.grid(row=i, column=0, sticky="ew", pady=(0, px(12)))
            cell.columnconfigure(0, weight=1)
            tk.Label(
                cell, text=f.label, font=(FONT, 10), fg=theme.TEXT, bg=theme.PANEL, anchor="w"
            ).grid(row=0, column=0, sticky="w")
            if f.type is bool:
                flag = tk.BooleanVar(value=value)
                switch = Switch(cell, value, flag.set)
                switch.grid(row=0, column=1, sticky="e")
                self.vars[f.key], self.switches[f.key] = flag, switch
            else:
                text = tk.StringVar(value=str(value))
                tk.Entry(
                    cell,
                    textvariable=text,
                    width=12,
                    font=(FONT, 10),
                    justify="right",
                    bg=theme.RAISED,
                    fg=theme.TEXT,
                    insertbackground=theme.TEXT,
                    relief="flat",
                    highlightthickness=1,
                    highlightbackground=theme.LINE,
                    highlightcolor=theme.LAMP,
                ).grid(row=0, column=1, sticky="e", ipady=px(3))
                self.vars[f.key] = text
            if f.help:
                tk.Label(
                    cell,
                    text=f.help,
                    font=(FONT, 9),
                    fg=theme.MUTED,
                    bg=theme.PANEL,
                    anchor="w",
                    justify="left",
                    wraplength=px(300),
                ).grid(row=1, column=0, columnspan=2, sticky="w")

        self.error = tk.StringVar()
        tk.Label(
            form,
            textvariable=self.error,
            font=(FONT, 9),
            fg=theme.FAULT,
            bg=theme.PANEL,
            anchor="w",
            justify="left",
            wraplength=px(300),
        ).grid(row=len(tool.fields), column=0, sticky="w")

        buttons = tk.Frame(self, bg=theme.PANEL, padx=px(18), pady=px(12))
        buttons.pack(fill="x")
        flat_button(buttons, "Reset to defaults", self._reset).pack(side="left")
        flat_button(buttons, "Save", self._save, primary=True).pack(side="right")
        flat_button(buttons, "Cancel", self.destroy).pack(side="right", padx=(0, px(8)))

        self.bind("<Escape>", lambda _e: self.destroy())
        self._place(anchor)
        theme.dark_titlebar(self)
        self.focus_force()

    def _place(self, anchor: tuple[int, int]) -> None:
        """Put the bottom-right corner at ``anchor``, kept on screen."""
        self.update_idletasks()
        left, top, right, bottom = theme.work_area(self)
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = max(left, min(anchor[0] - w, right - w))
        y = max(top, min(anchor[1] - h, bottom - h))
        self.geometry(f"+{x}+{y}")

    def _reset(self) -> None:
        for f in self.tool.fields:
            self.vars[f.key].set(f.default)
            if f.key in self.switches:
                self.switches[f.key].set(bool(f.default))
        self.error.set("")

    def _save(self) -> None:
        values = {}
        for f in self.tool.fields:
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
        self.title(f"Carol AIO {__version__}")
        self.withdraw()  # no window of its own; the tray icon is the way in
        self.tools = create_tools() if tools is None else tools
        self.config_store = config or Config()
        self.commands: queue.Queue[str] = queue.Queue()
        self.dialog: SettingsDialog | None = None
        self.flyout = Flyout(self, self.tools, self.toggle_tool, self.open_settings)
        self.tray = Tray(lambda: self.commands.put("toggle"), lambda: self.commands.put("quit"))

        self._load_config(startup=True)
        self.tray.start()
        self._refresh_tray()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(CONFIG_POLL_MS, self._poll_config)
        self.after(QUEUE_POLL_MS, self._poll_commands)

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
