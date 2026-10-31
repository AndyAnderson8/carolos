import unittest

from carol_aio.tool import Tool


class FakeTool(Tool):
    key = "fake"
    name = "Fake"

    def __init__(self):
        super().__init__()
        self.events = []

    def on_start(self):
        self.events.append("start")

    def on_stop(self):
        self.events.append("stop")


class ToolLifecycleTest(unittest.TestCase):
    def test_toggle(self):
        t = FakeTool()
        t.set_enabled(True)
        t.set_enabled(True)
        self.assertTrue(t.running)
        t.set_enabled(False)
        t.set_enabled(False)
        self.assertFalse(t.running)
        self.assertEqual(t.events, ["start", "stop"])

    def test_failed_start_not_running(self):
        class Bad(FakeTool):
            def on_start(self):
                raise RuntimeError("x")

        t = Bad()
        with self.assertRaises(RuntimeError):
            t.start()
        self.assertFalse(t.running)


if __name__ == "__main__":
    unittest.main()
