import tkinter as tk
import unittest
from typing import Any
from unittest import mock

from carolos import theme
from carolos.widgets import Dropdown
from carolos.pages import Choice, NoticePage, SettingsPage
from carolos.tools.call_pause import CallPause


def find_button(widget: tk.Misc, text: str) -> Any:
    for child in widget.winfo_children():
        label = child.cget("text") if isinstance(child, tk.Button) else getattr(child, "text", None)
        if label == text and hasattr(child, "invoke"):
            return child
        found = find_button(child, text)
        if found is not None:
            return found
    return None


class PageTest(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("no display available")
        self.root.withdraw()
        theme.init_scale(self.root)

    def tearDown(self) -> None:
        self.root.destroy()


class SettingsPageTest(PageTest):
    def setUp(self) -> None:
        super().setUp()
        self.saved: list[dict[str, Any]] = []
        self.closed: list[bool] = []
        with mock.patch("carolos.tools.call_pause.running_audio_apps", return_value=[]):
            self.page = SettingsPage(
                self.root,
                CallPause(),
                lambda _tool, values: self.saved.append(values),
                lambda: self.closed.append(True),
            )

    def test_cancel_goes_back_to_the_tools_without_saving(self) -> None:
        find_button(self.page, "Cancel").invoke()
        self.assertEqual(self.closed, [True])
        self.assertEqual(self.saved, [])

    def test_save_saves_and_goes_back_to_the_tools(self) -> None:
        find_button(self.page, "Save").invoke()
        self.assertEqual(len(self.saved), 1)
        self.assertEqual(self.closed, [True])

    def test_escape_goes_back_too(self) -> None:
        self.page.escape()
        self.assertEqual(self.closed, [True])


class NoticePageTest(PageTest):
    def test_a_button_runs_its_command_and_leaves(self) -> None:
        ran: list[str] = []
        done: list[bool] = []
        page = NoticePage(
            self.root,
            "Update available",
            "A new version is ready.",
            [Choice("Later"), Choice("Update now", lambda: ran.append("now"), True)],
            on_done=lambda: done.append(True),
        )
        find_button(page, "Update now").invoke()
        self.assertEqual((ran, done), (["now"], [True]))

    def test_a_keep_open_button_stays_on_the_page(self) -> None:
        done: list[bool] = []
        page = NoticePage(
            self.root,
            "Update",
            "Ready.",
            [Choice("Go", primary=True, keep_open=True)],
            on_done=lambda: done.append(True),
        )
        find_button(page, "Go").invoke()
        self.assertEqual(done, [])

    def test_escape_and_enter_do_nothing_while_busy(self) -> None:
        done: list[bool] = []
        page = NoticePage(self.root, "T", "M", [Choice("Close")], on_done=lambda: done.append(True))
        page.lock(True)
        page.escape()
        page.enter()
        self.assertEqual(done, [])
        page.lock(False)
        page.escape()
        self.assertEqual(done, [True])


class DropdownTest(PageTest):
    def test_clicking_elsewhere_in_the_app_closes_the_options(self) -> None:
        self.root.deiconify()
        entry = tk.Entry(self.root)
        entry.pack()
        dropdown = Dropdown(self.root, [("a", "A"), ("b", "B")], "a", lambda _v: None)
        dropdown.pack()
        self.root.update()
        entry.focus_force()
        self.root.update()
        if self.root.focus_get() is not entry:
            self.skipTest("the window could not take keyboard focus here")
        dropdown._open()
        self.root.update()
        entry.focus_force()  # what a click on the panel does
        self.root.update()
        self.root.after(250, self.root.quit)
        self.root.mainloop()
        self.assertIsNone(dropdown._popup)

    def test_a_click_in_the_window_closes_the_options_immediately(self) -> None:
        self.root.deiconify()
        other = tk.Label(self.root, text="elsewhere")
        other.pack()
        dropdown = Dropdown(self.root, [("a", "A")], "a", lambda _v: None)
        dropdown.pack()
        self.root.update()
        dropdown._open()
        other.event_generate("<Button-1>")
        self.assertIsNone(dropdown._popup)


if __name__ == "__main__":
    unittest.main()
