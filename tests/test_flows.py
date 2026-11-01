"""The update flow's failure path reports the error instead of crashing."""

from __future__ import annotations

import threading
import unittest
from collections.abc import Callable
from typing import Any
from unittest import mock

from carolos import updates
from carolos.flows import Updater
from carolos.pages import Choice


class FakeHost:
    def __init__(self) -> None:
        self.notices: list[tuple[str, str]] = []

    def show_notice(self, title: str, message: str, choices: list[Choice], detail: str = "") -> Any:
        self.notices.append((title, message))
        return mock.MagicMock()

    def notice_open(self) -> bool:
        return False

    def show(self) -> None:
        pass


class DownloadFailureTests(unittest.TestCase):
    def test_a_failed_download_shows_the_error(self) -> None:
        host = FakeHost()
        queued: list[Callable[[], None]] = []  # run later, like the Tk thread does
        updater = Updater(host, queued.append, lambda path: None)
        release = updates.Release("v2", "", "", "https://example.test/x", "x.exe", 5, "0" * 64)
        with mock.patch.object(updates, "download", side_effect=updates.UpdateError("no network")):
            updater._download(release)
            for thread in threading.enumerate():
                if thread is not threading.current_thread():
                    thread.join(2)
        for action in queued:
            action()
        self.assertEqual(host.notices[-1], ("Couldn't update", "no network"))


if __name__ == "__main__":
    unittest.main()
