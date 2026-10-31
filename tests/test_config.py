import tempfile
import unittest
from pathlib import Path

import os
from unittest import mock

from carol_aio import config as cfg
from carol_aio.config import Config, ConfigError
from carol_aio.tool import Field, Tool


class RenamedToolTest(unittest.TestCase):
    def test_old_key_settings_move_to_new_key(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "config.yaml"
            path.write_text(
                "tools:\n"
                "  edge_audio_pause:\n"
                "    enabled: true\n"
                "    settings:\n"
                "      process_name: a.exe\n",
                encoding="utf-8",
            )
            config = Config(path)
            config.load()
            section = config.tool_section("call_pause")
            self.assertTrue(section["enabled"])
            self.assertEqual(section["settings"]["process_name"], "a.exe")
            self.assertNotIn("edge_audio_pause", config.data["tools"])


class T(Tool):
    key = "t"
    name = "T"
    fields = (
        Field("level", "Level", float, 0.5, 0.0, 1.0),
        Field("name", "Name", str, "x"),
        Field("on", "On", bool, False),
    )

    def on_start(self) -> None:
        pass


class ConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "config.yaml"

    def tearDown(self) -> None:
        self.dir.cleanup()

    def test_roundtrip_and_change_detection(self) -> None:
        c = Config(self.path)
        c.set_tool("t", enabled=True, settings={"level": 0.3})
        c.save()
        self.assertFalse(c.changed_on_disk())  # our own write is not an external edit
        c2 = Config(self.path)
        c2.load()
        self.assertEqual(c2.tool_section("t"), {"enabled": True, "settings": {"level": 0.3}})
        self.path.write_text("tools:\n  t:\n    enabled: false\n")
        self.assertTrue(c.changed_on_disk())

    def test_invalid_yaml_raises_and_keeps_data(self) -> None:
        c = Config(self.path)
        c.set_tool("t", enabled=True)
        self.path.write_text("tools: [unclosed")
        with self.assertRaises(ConfigError):
            c.load()
        self.assertTrue(c.tool_section("t")["enabled"])
        self.assertFalse(c.changed_on_disk())  # no reload loop on a broken file

    def test_unknown_tools_preserved(self) -> None:
        self.path.write_text("tools:\n  other:\n    enabled: true\n")
        c = Config(self.path)
        c.load()
        c.set_tool("t", enabled=False)
        c.save()
        self.assertIn("other", self.path.read_text())

    def test_path_precedence(self) -> None:
        with mock.patch.dict(os.environ, {cfg.ENV_VAR: "/env/c.yaml"}):
            self.assertEqual(cfg.default_config_path(), Path("/env/c.yaml"))
            cfg.set_config_path("/cli/c.yaml")
            try:
                self.assertEqual(cfg.default_config_path(), Path("/cli/c.yaml"))
            finally:
                cfg.set_config_path(None)
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(cfg.default_config_path().name, "config.yaml")

    def test_configure_validation(self) -> None:
        t = T()
        errors = t.configure({"level": 5, "name": "y", "on": "yes", "junk": 1})
        self.assertEqual(t.settings, {"level": 0.5, "name": "y", "on": True})
        self.assertEqual(len(errors), 1)
        self.assertEqual(t.configure(None), [])
        self.assertEqual(t.settings, t.defaults())


if __name__ == "__main__":
    unittest.main()
