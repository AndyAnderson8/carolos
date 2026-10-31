import unittest

from carol_aio.audio_apps import friendly_name
from carol_aio.tool import Field
from carol_aio.tools.call_pause import BURST_WINDOW, REACTIONS, SUSTAIN_RATIO, CallPause


class ChoiceFieldTest(unittest.TestCase):
    field = Field("mode", "Mode", str, "a", choices=(("a", "A", ""), ("b", "B", "")))

    def test_accepts_a_listed_value(self) -> None:
        self.assertEqual(self.field.coerce("b"), "b")

    def test_rejects_anything_else(self) -> None:
        with self.assertRaises(ValueError):
            self.field.coerce("c")


class CallPauseSettingsTest(unittest.TestCase):
    def test_defaults_are_balanced(self) -> None:
        tool = CallPause()
        self.assertEqual(tool.settings["reaction"], "balanced")
        self.assertEqual(REACTIONS["balanced"], (BURST_WINDOW, SUSTAIN_RATIO))

    def test_bad_reaction_falls_back_to_default(self) -> None:
        tool = CallPause()
        errors = tool.configure({"reaction": "turbo"})
        self.assertEqual(len(errors), 1)
        self.assertEqual(tool.settings["reaction"], "balanced")

    def test_old_timing_settings_are_ignored(self) -> None:
        tool = CallPause()
        self.assertEqual(tool.configure({"sustain_ratio": 0.8, "burst_window": 0.25}), [])

    def test_every_reaction_has_a_label_and_timing(self) -> None:
        keys = [c[0] for c in next(f for f in CallPause.fields if f.key == "reaction").choices]
        self.assertEqual(sorted(keys), sorted(REACTIONS))

    def test_app_options_always_include_edge(self) -> None:
        self.assertIn("msedge.exe", [exe for exe, _ in CallPause().options("process_name")])


class FriendlyNameTest(unittest.TestCase):
    def test_known_programs(self) -> None:
        self.assertEqual(friendly_name("msedge.exe"), "Microsoft Edge")
        self.assertEqual(friendly_name("SPOTIFY.EXE"), "Spotify")

    def test_unknown_programs_are_tidied(self) -> None:
        self.assertEqual(friendly_name("my_cool-app.exe"), "My Cool App")


if __name__ == "__main__":
    unittest.main()
