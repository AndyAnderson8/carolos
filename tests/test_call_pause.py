import unittest

from carol_aio.tools.call_pause import is_sustained


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def clock(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.t += s


def run(samples: list[float]) -> bool:
    c = FakeClock()
    it = iter(samples + [samples[-1]] * 1000)
    return is_sustained(lambda: next(it), sleep=c.sleep, clock=c.clock)


class SustainTest(unittest.TestCase):
    def test_sustained_loud(self) -> None:
        self.assertTrue(run([0.3] * 20))

    def test_brief_blip_ignored(self) -> None:
        self.assertFalse(run([0.3, 0.3] + [0.0] * 20))

    def test_silence(self) -> None:
        self.assertFalse(run([0.0] * 20))

    def test_small_dropouts_tolerated(self) -> None:
        self.assertTrue(run([0.3, 0.3, 0.0, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3] * 3))


if __name__ == "__main__":
    unittest.main()
