"""The open panel closes on a click outside the app, even if it never got focus."""

from __future__ import annotations

import tkinter as tk
import unittest
from unittest import mock

from carolos import theme
from carolos.app import Flyout


class ClickAwayTests(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("no display available")
        self.root.withdraw()
        theme.init_scale(self.root)
        self.flyout = Flyout(self.root, [], lambda *_: None, lambda *_: None, lambda: None)

    def tearDown(self) -> None:
        self.flyout.destroy()
        self.root.destroy()

    def pump(self, seconds: float) -> None:
        end = self.root.tk.call("clock", "milliseconds") + int(seconds * 1000)
        while self.root.tk.call("clock", "milliseconds") < end:
            self.root.update()

    def test_press_outside_closes_it(self) -> None:
        with (
            mock.patch("carolos.outside.pressed", side_effect=[False, False, True, True]),
            mock.patch("carolos.outside.over_other_program", return_value=True),
        ):
            self.flyout.show()
            self.pump(0.6)
        self.assertFalse(self.flyout.visible)

    def test_press_inside_the_app_keeps_it_open(self) -> None:
        with (
            mock.patch("carolos.outside.pressed", return_value=True),
            mock.patch("carolos.outside.over_other_program", return_value=False),
        ):
            self.flyout.show()
            self.pump(0.4)
        self.assertTrue(self.flyout.visible)

    def test_a_press_already_down_when_it_opens_is_ignored(self) -> None:
        with (
            mock.patch("carolos.outside.pressed", return_value=True),
            mock.patch("carolos.outside.over_other_program", return_value=True),
        ):
            self.flyout.show()
            self.pump(0.4)
        self.assertTrue(self.flyout.visible)


if __name__ == "__main__":
    unittest.main()
