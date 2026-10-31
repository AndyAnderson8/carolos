"""Main window: one row per tool with an on/off toggle and a settings gear."""

import argparse
import tkinter as tk
from tkinter import messagebox, ttk

from carol_aio import __version__
from carol_aio.config import ENV_VAR, Config, ConfigError, set_config_path
from carol_aio.tools import create_tools

CONFIG_POLL_MS = 1000


class SettingsDialog(tk.Toplevel):
    """Form generated from a tool's ``fields``; saving writes to config.yaml."""

    def __init__(self, parent, tool, on_save):
        super().__init__(parent)
        self.title(f"{tool.name} settings")
        self.resizable(False, False)
        self.transient(parent)
        self.tool, self.on_save = tool, on_save
        self.vars = {}

        form = ttk.Frame(self, padding=12)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        if not tool.fields:
            ttk.Label(form, text="This tool has no settings.").grid(row=0, column=0)
        for i, f in enumerate(tool.fields):
            value = tool.settings[f.key]
            ttk.Label(form, text=f.label).grid(row=i, column=0, sticky="w", pady=4, padx=(0, 10))
            if f.type is bool:
                var = tk.BooleanVar(value=value)
                ttk.Checkbutton(form, variable=var).grid(row=i, column=1, sticky="w")
            else:
                var = tk.StringVar(value=str(value))
                ttk.Entry(form, textvariable=var, width=22).grid(row=i, column=1, sticky="ew")
            if f.help:
                ttk.Label(form, text=f.help, foreground="#666", wraplength=220).grid(
                    row=i, column=2, sticky="w", padx=(10, 0)
                )
            self.vars[f.key] = var

        buttons = ttk.Frame(self, padding=(12, 0, 12, 12))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Save", command=self._save).pack(side="right", padx=6)
        ttk.Button(buttons, text="Reset to defaults", command=self._reset).pack(side="left")
        self.grab_set()

    def _reset(self):
        for f in self.tool.fields:
            self.vars[f.key].set(f.default)

    def _save(self):
        values = {}
        for f in self.tool.fields:
            try:
                values[f.key] = f.coerce(self.vars[f.key].get())
            except ValueError as exc:
                messagebox.showerror("Invalid value", f"{f.label}: {exc}", parent=self)
                return
        self.on_save(self.tool, values)
        self.destroy()


class ToolRow(ttk.Frame):
    def __init__(self, parent, tool, on_toggle, on_gear):
        super().__init__(parent, padding=(10, 8))
        self.tool, self._on_toggle = tool, on_toggle
        self.enabled = tk.BooleanVar(value=tool.running)
        self._label_var = tk.StringVar()

        self.columnconfigure(0, weight=1)
        ttk.Label(self, text=tool.name, font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(self, text=tool.description, wraplength=300, foreground="#555").grid(
            row=1, column=0, sticky="w"
        )
        ttk.Button(self, text="\u2699", width=3, command=lambda: on_gear(tool)).grid(
            row=0, column=1, rowspan=2, padx=(10, 0)
        )
        self.toggle = ttk.Checkbutton(
            self, textvariable=self._label_var, variable=self.enabled, command=self._clicked
        )
        self.toggle.grid(row=0, column=2, rowspan=2, padx=(10, 0))
        self.sync()

    def sync(self):
        """Show the tool's real running state."""
        self.enabled.set(self.tool.running)
        self._label_var.set("On" if self.tool.running else "Off")

    def _clicked(self):
        self._on_toggle(self.tool, self.enabled.get())
        self.sync()


class App(tk.Tk):
    def __init__(self, tools=None, config=None):
        super().__init__()
        self.title(f"Carol AIO {__version__}")
        self.minsize(480, 200)
        self.tools = create_tools() if tools is None else tools
        self.config_store = config or Config()
        self.rows = {}
        self.status = tk.StringVar()

        body = ttk.Frame(self, padding=8)
        body.pack(fill="both", expand=True)
        if not self.tools:
            ttk.Label(body, text="No tools installed yet.", padding=20).pack()
        for i, tool in enumerate(self.tools):
            if i:
                ttk.Separator(body).pack(fill="x")
            row = ToolRow(body, tool, self.toggle_tool, self.open_settings)
            row.pack(fill="x")
            self.rows[tool.key] = row
        ttk.Label(self, textvariable=self.status, foreground="#a33", padding=(10, 4)).pack(fill="x")

        self._load_config(startup=True)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(CONFIG_POLL_MS, self._poll_config)

    # --- config <-> tools -------------------------------------------------

    def _load_config(self, startup=False):
        """Apply config.yaml to every tool; create the file if it is missing."""
        try:
            self.config_store.load()
        except ConfigError as exc:
            self.status.set(str(exc))
            return
        problems = []
        for tool in self.tools:
            section = self.config_store.tool_section(tool.key)
            problems += tool.configure(section["settings"])
            if section["enabled"] != tool.running:
                problems += self._set_running(tool, section["enabled"])
            self.rows[tool.key].sync()
        self.status.set("; ".join(problems))
        if startup and not self.config_store.path.exists():
            self._write_config()  # first run: write defaults so there is a file to edit

    def _set_running(self, tool, enabled):
        try:
            tool.set_enabled(enabled)
        except Exception as exc:
            return [f"{tool.name}: could not start ({exc})"]
        return []

    def _write_config(self):
        for tool in self.tools:
            self.config_store.set_tool(tool.key, enabled=tool.running, settings=tool.settings)
        try:
            self.config_store.save()
        except OSError as exc:
            self.status.set(f"Could not write {self.config_store.path.name}: {exc}")

    def _poll_config(self):
        if self.config_store.changed_on_disk():
            self._load_config()
        self.after(CONFIG_POLL_MS, self._poll_config)

    # --- GUI actions ------------------------------------------------------

    def toggle_tool(self, tool, enabled):
        problems = self._set_running(tool, enabled)
        if problems:
            messagebox.showerror(tool.name, problems[0], parent=self)
        self._write_config()

    def open_settings(self, tool):
        SettingsDialog(self, tool, self.save_settings)

    def save_settings(self, tool, values):
        tool.configure(values)
        self._write_config()
        self.status.set("")

    def close(self):
        for tool in self.tools:
            tool.stop()
        self.destroy()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Carol AIO")
    parser.add_argument("--config", metavar="PATH",
                        help=f"config file to use (or set ${ENV_VAR}); default: next to the app")
    set_config_path(parser.parse_args(argv).config)
    App().mainloop()
