import unittest

from carol_aio.tools.call_pause import SoundTrigger


class SoundTriggerTest(unittest.TestCase):
    def test_silence_never_fires(self) -> None:
        trigger = SoundTrigger()
        self.assertEqual([trigger.update(False) for _ in range(5)], [False] * 5)

    def test_fires_on_the_very_first_sound(self) -> None:
        trigger = SoundTrigger()
        trigger.update(False)
        self.assertTrue(trigger.update(True))

    def test_fires_once_while_the_sound_continues(self) -> None:
        trigger = SoundTrigger()
        self.assertEqual([trigger.update(True) for _ in range(4)], [True, False, False, False])

    def test_fires_again_only_after_it_has_gone_quiet(self) -> None:
        trigger = SoundTrigger()
        results = [trigger.update(a) for a in (True, True, False, True, True)]
        self.assertEqual(results, [True, False, False, True, False])


if __name__ == "__main__":
    unittest.main()
