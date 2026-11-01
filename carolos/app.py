"""Tray app: a flyout with a switch per tool; settings and update notices are pages inside it."""

from __future__ import annotations

import argparse
import ctypes
import queue
import time
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PIL import Image

from carolos import __version__, bubble, install, single, theme
from carolos.config import ENV_VAR, Config, ConfigError, set_config_path
from carolos.flows import Updater
from carolos.layered import LayeredWindow
from carolos.theme import FONT, px
from carolos.pages import Choice, NoticePage, SettingsPage
from carolos.tool import Tool
from carolos.tools import create_tools
from carolos.tray import Tray
from carolos.widgets import GearButton, Switch, flat_button, heading

CONFIG_POLL_MS = 1000
QUEUE_POLL_MS = 100
AUTO_CHECK_DELAY_MS = 4000  # let the tray icon settle before checking for updates
REOPEN_GUARD_S = 0.3  # the tray click that dismissed the panel must not reopen it
EDGE_GAP = 12
OFFSCREEN = -20000  # where the panel paints before it is shown


class ToolRow(tk.Frame):
    """One tool: name and description on the left, gear and switch on the right."""

    def __init__(
        self,
        parent: tk.Misc,
        tool: Tool,
        on_toggle: Callable[[Tool, bool], None],
        on_gear: Callable[[Tool], None],
        pad: int = 14,
    ) -> None:
        super().__init__(parent, bg=theme.PANEL, padx=px(18), pady=px(pad))
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
            wraplength=px(theme.PAGE_WIDTH - 150),
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
        on_check: Callable[[], None],
    ) -> None:
        super().__init__(parent, bg=theme.PANEL)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.withdraw()
        self.rows: dict[str, ToolRow] = {}
        self._hidden_at = 0.0
        self._shape_args: tuple[Image.Image, int, int]
        self._geometry = self._unseen = ""
        self.status = tk.StringVar()
        self.shape = LayeredWindow()  # the bubble outline, header and tail, drawn as an image
        self._art: dict[tuple[object, ...], bubble.Bubble] = {}

        # This window holds only the controls; the bubble round it is drawn by ``self.shape``.
        tk.Frame(
            self, bg=theme.PANEL, width=px(theme.PAGE_WIDTH), height=1
        ).pack()  # sets the width
        self.host = tk.Frame(self, bg=theme.PANEL)
        self.host.pack(fill="x")
        self.tools_page = panel = tk.Frame(self.host, bg=theme.PANEL)
        self.page: tk.Frame = panel
        self.notice: NoticePage | None = None
        panel.pack(fill="x")
        heading(panel, "Tools").pack(fill="x", pady=(px(2), 0))

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
            # the first row sits a little higher, under the heading; the gap below stays the same
            row = ToolRow(panel, tool, on_toggle, on_gear, pad=9 if i == 0 else 14)
            row.pack(fill="x", pady=(0, px(5)) if i == 0 else 0)
            self.rows[tool.key] = row

        footer = tk.Frame(panel, bg=theme.PANEL, padx=px(12), pady=px(4))
        footer.pack(side="bottom", fill="x")  # packed first so it stays at the very bottom
        tk.Frame(panel, bg=theme.LINE, height=1).pack(side="bottom", fill="x")
        flat_button(footer, "Check for updates", on_check, quiet=True).pack(side="left")
        tk.Label(footer, text=__version__, font=(FONT, 9), fg=theme.MUTED, bg=theme.PANEL).pack(
            side="right", padx=(0, px(6))
        )

        self.status_label = tk.Label(
            panel,
            textvariable=self.status,
            font=(FONT, 9),
            fg=theme.FAULT,
            bg=theme.PANEL,
            anchor="w",
            justify="left",
            wraplength=px(theme.PAGE_WIDTH - 36),
            padx=px(18),
        )
        self.status.trace_add("write", lambda *_: self._show_status())
        self.bind("<Escape>", lambda _e: self._escape())
        self.bind("<Return>", lambda _e: self._enter())
        self.bind("<FocusOut>", lambda _e: self.after(80, self._hide_if_unfocused))

    # --- pages ------------------------------------------------------------

    def _open(self, page: tk.Frame) -> None:
        """Swap the page shown in the bubble; the tools page is kept, any other is discarded."""
        old = self.page
        shown = self.visible
        if shown:  # swap out of sight, so the new page appears all at once
            self.shape.hide()
            self.geometry(self._unseen)
        old.pack_forget()
        if old is not self.tools_page:
            old.destroy()
        self.page = page
        page.pack(fill="x")
        if shown:
            self._place(reveal=False)
            self.geometry(self._unseen)
            self.update()
            self._reveal()

    def close_page(self) -> None:
        """Back to the tools."""
        if self.page is self.tools_page:
            return
        if self.page is self.notice:
            self.notice = None
        self._open(self.tools_page)

    def show_settings(self, tool: Tool, on_save: Callable[[Tool, dict[str, Any]], None]) -> None:
        self.notice = None
        self._open(SettingsPage(self.host, tool, on_save, self.close_page, self.refit))
        if not self.visible:
            self.show()

    def show_notice(
        self, title: str, message: str, choices: list[Choice], detail: str = ""
    ) -> NoticePage:
        """Show a message page (reusing the one already up) and make sure the panel is open."""
        if self.notice is not None and self.page is self.notice:
            self.notice.update_content(title, message, choices, detail)
        else:
            self.notice = NoticePage(
                self.host, title, message, choices, detail, self.refit, self.close_page
            )
            self._open(self.notice)
        if not self.visible:
            self.show()
        return self.notice

    def warm_up(self, tools: list[Tool]) -> None:
        """Draw the bubble for each tool's settings page now, so opening one is instant."""
        for tool in tools:
            page = SettingsPage(self.host, tool, lambda *_: None, lambda: None)
            self.update_idletasks()
            self._bubble(self.winfo_reqwidth(), page.winfo_reqheight() + 1)
            page.destroy()

    def notice_open(self) -> bool:
        return self.notice is not None and self.page is self.notice

    def _escape(self) -> None:
        if isinstance(self.page, (SettingsPage, NoticePage)):
            self.page.escape()
        else:
            self.hide()

    def _enter(self) -> None:
        if isinstance(self.page, NoticePage):
            self.page.enter()

    def refit(self) -> None:
        """The page changed size: redraw the bubble round it."""
        if self.visible:
            self._place()
            self.lift()  # the redrawn bubble comes up on top; the controls go back above it

    def _show_status(self) -> None:
        if self.status.get():
            self.status_label.pack(fill="x", pady=(0, px(10)))
        else:
            self.status_label.pack_forget()
        self.refit()

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
        self._place(reveal=False)
        self.geometry(self._unseen)  # let the controls paint out of sight first
        self.deiconify()
        self.lift()
        self.update()
        self._reveal()
        self.focus_force()

    def _place(self, reveal: bool = True) -> None:
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        art = self._bubble(w, h)
        right, bottom = self.corner()
        x = right - art.image.width + art.margin  # the bubble's visible edge ends at the corner
        y = bottom - art.image.height + art.margin
        self._shape_args = (art.image, x, y)
        self._geometry = f"{w}x{h}+{x + art.content_x}+{y + art.content_y}"
        self._unseen = f"{w}x{h}+{OFFSCREEN}+0"
        if reveal:
            self.shape.show(*self._shape_args)
            self._move_home()

    def _move_home(self) -> None:
        self.geometry(self._geometry)
        self.update_idletasks()
        self.geometry(
            self._geometry
        )  # a page swap resizes the window itself first; put it back in place

    def _reveal(self) -> None:
        """Put the painted controls and the bubble behind them on screen together."""
        self._move_home()
        self.shape.show(*self._shape_args)
        self.lift()

    def hide(self) -> None:
        self._hidden_at = time.monotonic()
        self.withdraw()
        self.shape.hide()
        if not (isinstance(self.page, NoticePage) and self.page.busy):
            self.close_page()  # next time it opens on the tools (a download keeps its page)

    def destroy(self) -> None:
        self.shape.destroy()
        super().destroy()

    def _bubble(self, width: int, height: int) -> bubble.Bubble:
        """The bubble art for a controls window of this size (cached; it takes a moment to draw)."""
        tail = (
            theme.work_area(self)[3] < self.winfo_screenheight() - 2
        )  # a taskbar below to point at
        key = (width, height, tail)
        if key not in self._art:
            colors = bubble.BubbleColors(theme.PANEL, theme.OUTLINE, theme.SEA, theme.ON_SEA, 0.25)
            self._art[key] = bubble.render(width, height, colors, px, tail)
        return self._art[key]

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
        self.title(f"CaroLoS {__version__}")
        self.withdraw()  # no window of its own; the tray icon is the way in
        self.tools = create_tools() if tools is None else tools
        self.config_store = config or Config()
        self.inbox: queue.Queue[Callable[[], None]] = queue.Queue()
        self.pending_setup: Path | None = None  # a downloaded installer to run once we exit
        self.flyout = Flyout(
            self, self.tools, self.toggle_tool, self.open_settings, self.check_for_updates
        )
        self.updater = Updater(self.flyout, self.post, self._update_with)
        self.tray = Tray(
            lambda: self.post(self.flyout.toggle),
            lambda: self.post(self.check_for_updates),
            lambda: self.post(self.close),
        )

        self._load_config(startup=True)
        self.tray.start()
        self._refresh_tray()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(CONFIG_POLL_MS, self._poll_config)
        self.after(QUEUE_POLL_MS, self._poll_inbox)
        self.after(1500, lambda: self.flyout.warm_up(self.tools))
        self.after(AUTO_CHECK_DELAY_MS, lambda: self.updater.check(manual=False))

    def post(self, action: Callable[[], None]) -> None:
        """Run ``action`` on Tk's thread; safe to call from any thread."""
        self.inbox.put(action)

    @property
    def status(self) -> tk.StringVar:
        return self.flyout.status

    @property
    def rows(self) -> dict[str, ToolRow]:
        return self.flyout.rows

    def _refresh_tray(self) -> None:
        self.tray.update(sum(t.running for t in self.tools), len(self.tools))

    def _poll_inbox(self) -> None:
        """Tray and background-thread callbacks arrive on other threads; run them here."""
        try:
            while True:
                self.inbox.get_nowait()()
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(QUEUE_POLL_MS, self._poll_inbox)

    def check_for_updates(self) -> None:
        self.updater.check(manual=True)

    def _update_with(self, setup: Path) -> None:
        """An update's installer is downloaded: shut down, and main() runs it."""
        self.pending_setup = setup
        self.close()

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
        self.flyout.show_settings(tool, self.save_settings)

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
    parser = argparse.ArgumentParser(description="CaroLoS")
    parser.add_argument(
        "--config",
        metavar="PATH",
        help=f"config file to use (or set ${ENV_VAR}); default: next to the app",
    )
    set_config_path(parser.parse_args(argv).config)

    if not single.acquire():
        ctypes.windll.user32.MessageBoxW(
            0,
            "CaroLoS is already running. Look for it in the tray (the ^ arrow).",
            "CaroLoS",
            0x40,
        )
        return

    app = App()
    app.mainloop()
    if app.pending_setup is not None:
        install.run_setup(app.pending_setup)
