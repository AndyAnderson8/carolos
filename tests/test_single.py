"""A second launch asks the running copy to open its panel."""

from __future__ import annotations

import sys
import threading
import unittest

from carolos import single


@unittest.skipUnless(sys.platform == "win32", "uses Windows events")
class SignalTests(unittest.TestCase):
    def test_second_launch_wakes_the_listener(self) -> None:
        woke = threading.Event()
        single.listen(woke.set)
        single.signal_running()
        self.assertTrue(woke.wait(2))


if __name__ == "__main__":
    unittest.main()
