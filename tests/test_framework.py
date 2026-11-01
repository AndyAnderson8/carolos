import unittest

from carolos.tool import Tool


class FakeTool(Tool):
    key = "fake"
    name = "Fake"

    def __init__(self) -> None:
        super().__init__()
        self.events: list[str] = []

    def on_start(self) -> None:
        self.events.append("start")

    def on_stop(self) -> None:
        self.events.append("stop")


class ToolLifecycleTest(unittest.TestCase):
    def test_toggle(self) -> None:
        t = FakeTool()
        t.set_enabled(True)
        t.set_enabled(True)
        self.assertTrue(t.running)
        t.set_enabled(False)
        t.set_enabled(False)
        self.assertFalse(t.running)
        self.assertEqual(t.events, ["start", "stop"])

    def test_failed_start_not_running(self) -> None:
        class Bad(FakeTool):
            def on_start(self) -> None:
                raise RuntimeError("x")

        t = Bad()
        with self.assertRaises(RuntimeError):
            t.start()
        self.assertFalse(t.running)


if __name__ == "__main__":
    unittest.main()
