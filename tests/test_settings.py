import unittest

from carolos.audio_apps import friendly_name
from carolos.tool import Field
from carolos.tools.call_pause import CallPause


class ChoiceFieldTest(unittest.TestCase):
    field = Field("mode", "Mode", str, "a", choices=(("a", "A", ""), ("b", "B", "")))

    def test_accepts_a_listed_value(self) -> None:
        self.assertEqual(self.field.coerce("b"), "b")

    def test_rejects_anything_else(self) -> None:
        with self.assertRaises(ValueError):
            self.field.coerce("c")


class CallPauseSettingsTest(unittest.TestCase):
    def test_settings_from_older_versions_are_ignored(self) -> None:
        old = {"reaction": "fast", "pause_target": "spotify.exe", "burst_window": 0.2}
        self.assertEqual(CallPause().configure(old), [])

    def test_app_options_always_include_edge(self) -> None:
        self.assertIn("msedge.exe", [exe for exe, _ in CallPause().options("process_name")])


class FriendlyNameTest(unittest.TestCase):
    def test_known_programs(self) -> None:
        self.assertEqual(friendly_name("msedge.exe"), "Microsoft Edge")
        self.assertEqual(friendly_name("SPOTIFY.EXE"), "Spotify")

    def test_ids_without_an_exe_suffix(self) -> None:
        self.assertEqual(friendly_name("MSEdge"), "Microsoft Edge")
        self.assertEqual(friendly_name("Chrome"), "Google Chrome")

    def test_store_app_ids_are_shortened(self) -> None:
        self.assertEqual(
            friendly_name("Microsoft.ZuneMusic_8wekyb3d8bbwe!Microsoft.ZuneMusic"), "ZuneMusic"
        )

    def test_unknown_programs_are_tidied(self) -> None:
        self.assertEqual(friendly_name("my_cool-app.exe"), "My Cool App")


if __name__ == "__main__":
    unittest.main()
