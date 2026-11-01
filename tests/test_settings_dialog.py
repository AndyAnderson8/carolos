import tkinter as tk
import unittest
from typing import Any
from unittest import mock

from carol_aio import theme
from carol_aio.app import SettingsDialog
from carol_aio.tools.call_pause import CallPause


def find_button(widget: tk.Misc, text: str) -> tk.Button | None:
    for child in widget.winfo_children():
        if isinstance(child, tk.Button) and child.cget("text") == text:
            return child
        found = find_button(child, text)
        if found is not None:
            return found
    return None


class SettingsDialogTest(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("no display available")
        self.root.withdraw()
        theme.init_scale(self.root)
        self.saved: list[dict[str, Any]] = []
        self.closed: list[bool] = []
        with mock.patch("carol_aio.tools.call_pause.running_audio_apps", return_value=[]):
            self.dialog = SettingsDialog(
                self.root,
                CallPause(),
                lambda _tool, values: self.saved.append(values),
                (900, 900),
                lambda: self.closed.append(True),
            )

    def tearDown(self) -> None:
        self.root.destroy()

    def test_cancel_goes_back_to_the_main_panel_without_saving(self) -> None:
        button = find_button(self.dialog, "Cancel")
        assert button is not None
        button.invoke()
        self.assertEqual(self.closed, [True])
        self.assertEqual(self.saved, [])
        self.assertFalse(self.dialog.winfo_exists())

    def test_save_saves_and_goes_back_to_the_main_panel(self) -> None:
        button = find_button(self.dialog, "Save")
        assert button is not None
        button.invoke()
        self.assertEqual(len(self.saved), 1)
        self.assertEqual(self.closed, [True])
        self.assertFalse(self.dialog.winfo_exists())

    def test_escape_goes_back_too(self) -> None:
        self.dialog.focus_force()
        self.dialog.update()
        if self.root.focus_displayof() is None:
            self.skipTest("the window could not take keyboard focus here")
        self.dialog.event_generate("<Escape>", when="now")
        self.dialog.update()
        self.assertEqual(self.closed, [True])


if __name__ == "__main__":
    unittest.main()
