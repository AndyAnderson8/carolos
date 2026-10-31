"""Main window: one row per tool with an on/off toggle."""

import tkinter as tk
from tkinter import messagebox, ttk

from carol_aio import __version__
from carol_aio.tools import create_tools


class ToolRow(ttk.Frame):
    def __init__(self, parent, tool):
        super().__init__(parent, padding=(10, 8))
        self.tool = tool
        self.enabled = tk.BooleanVar(value=tool.running)

        self.columnconfigure(0, weight=1)
        ttk.Label(self, text=tool.name, font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(self, text=tool.description, wraplength=330, foreground="#555").grid(
            row=1, column=0, sticky="w"
        )
        self._label_var = tk.StringVar()
        self.toggle = ttk.Checkbutton(
            self, textvariable=self._label_var, variable=self.enabled, command=self._on_toggle
        )
        self.toggle.grid(row=0, column=1, rowspan=2, padx=(10, 0))
        self._refresh_label()

    def _refresh_label(self):
        self._label_var.set("On" if self.enabled.get() else "Off")

    def _on_toggle(self):
        try:
            self.tool.set_enabled(self.enabled.get())
        except Exception as exc:  # surface tool errors instead of dying silently
            self.enabled.set(False)
            messagebox.showerror(self.tool.name, f"Could not start tool:\n{exc}")
        self._refresh_label()


class App(tk.Tk):
    def __init__(self, tools=None):
        super().__init__()
        self.title(f"Carol AIO {__version__}")
        self.minsize(460, 200)
        self.tools = create_tools() if tools is None else tools

        body = ttk.Frame(self, padding=8)
        body.pack(fill="both", expand=True)

        if not self.tools:
            ttk.Label(body, text="No tools installed yet.", padding=20).pack()
        for i, tool in enumerate(self.tools):
            if i:
                ttk.Separator(body).pack(fill="x")
            row = ToolRow(body, tool)
            row.pack(fill="x")

        self.protocol("WM_DELETE_WINDOW", self.close)

    def close(self):
        for tool in self.tools:
            tool.stop()
        self.destroy()


def main():
    App().mainloop()
