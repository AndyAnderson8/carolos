import tempfile
import unittest
from pathlib import Path

from carol_aio.config import Config, ConfigError
from carol_aio.tool import Field, Tool


class T(Tool):
    key = "t"
    name = "T"
    fields = (Field("level", "Level", float, 0.5, 0.0, 1.0), Field("name", "Name", str, "x"),
              Field("on", "On", bool, False))

    def on_start(self):
        pass


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "config.yaml"

    def tearDown(self):
        self.dir.cleanup()

    def test_roundtrip_and_change_detection(self):
        c = Config(self.path)
        c.set_tool("t", enabled=True, settings={"level": 0.3})
        c.save()
        self.assertFalse(c.changed_on_disk())  # our own write is not an external edit
        c2 = Config(self.path)
        c2.load()
        self.assertEqual(c2.tool_section("t"), {"enabled": True, "settings": {"level": 0.3}})
        self.path.write_text("tools:\n  t:\n    enabled: false\n")
        self.assertTrue(c.changed_on_disk())

    def test_invalid_yaml_raises_and_keeps_data(self):
        c = Config(self.path)
        c.set_tool("t", enabled=True)
        self.path.write_text("tools: [unclosed")
        with self.assertRaises(ConfigError):
            c.load()
        self.assertTrue(c.tool_section("t")["enabled"])
        self.assertFalse(c.changed_on_disk())  # no reload loop on a broken file

    def test_unknown_tools_preserved(self):
        self.path.write_text("tools:\n  other:\n    enabled: true\n")
        c = Config(self.path)
        c.load()
        c.set_tool("t", enabled=False)
        c.save()
        self.assertIn("other", self.path.read_text())

    def test_configure_validation(self):
        t = T()
        errors = t.configure({"level": 5, "name": "y", "on": "yes", "junk": 1})
        self.assertEqual(t.settings, {"level": 0.5, "name": "y", "on": True})
        self.assertEqual(len(errors), 1)
        self.assertEqual(t.configure(None), [])
        self.assertEqual(t.settings, t.defaults())


if __name__ == "__main__":
    unittest.main()
