import unittest

from carol_aio.bubble import BubbleColors, render

COLORS = BubbleColors("#f4e6c6", "#43261a", "#1d93b3", "#fff6df", 0.3)


class BubbleTest(unittest.TestCase):
    def test_the_corners_are_see_through(self) -> None:
        art = render(300, 200, COLORS)
        for point in ((0, 0), (art.image.width - 1, 0), (0, art.image.height - 1)):
            pixel = art.image.getpixel(point)
            assert isinstance(pixel, tuple)
            self.assertEqual(pixel[3], 0)

    def test_the_controls_window_sits_wholly_on_the_bubble_body(self) -> None:
        art = render(300, 200, COLORS)
        x, y = art.content_x, art.content_y
        for point in ((x, y), (x + 299, y), (x, y + 199), (x + 299, y + 199)):
            pixel = art.image.getpixel(point)
            assert isinstance(pixel, tuple)
            self.assertEqual(pixel[3], 255, point)
            self.assertEqual(pixel[:3], (0xF4, 0xE6, 0xC6), point)  # same sand as the controls

    def test_she_does_not_spill_below_the_wave(self) -> None:
        art = render(300, 200, COLORS)
        for dx in (10, 40, 70):  # across where she stands
            pixel = art.image.getpixel((art.content_x + dx, art.content_y + 2))
            assert isinstance(pixel, tuple)
            self.assertEqual(pixel[:3], (0xF4, 0xE6, 0xC6), dx)

    def test_her_hand_sticks_out_past_the_left_edge(self) -> None:
        art = render(300, 200, COLORS)
        outside = art.content_x - 10 - 8  # a few pixels left of the bubble's edge (pad is 10)
        column = [art.image.getpixel((outside, y)) for y in range(art.body_y, art.body_y + 140)]
        solid = [p for p in column if isinstance(p, tuple) and p[3] > 200]
        self.assertTrue(solid)

    def test_the_name_is_in_the_blue_space_beside_her_a_little_left_of_centre(self) -> None:
        art = render(360, 200, COLORS)  # about as wide as the real panel
        left, top, right, bottom = art.name_box
        space_left, space_right = art.blue_space
        gap_left, gap_right = left - space_left, space_right - right
        self.assertLessEqual(abs((gap_right - gap_left) - 20), 1)  # nudged 10px left of centre
        self.assertGreater(gap_left, 4)  # and not squeezed against her
        band_middle = art.body_y + art.band / 2
        self.assertLessEqual(abs((top + bottom) / 2 - band_middle), 1)

    def test_the_header_band_is_sea_coloured(self) -> None:
        art = render(300, 200, COLORS)
        pixel = art.image.getpixel((art.image.width - art.margin - 24, art.body_y + 14))
        assert isinstance(pixel, tuple)
        self.assertEqual(pixel[:3], (0x1D, 0x93, 0xB3))

    def test_a_tail_adds_height_and_points_down(self) -> None:
        plain, tailed = render(300, 200, COLORS, tail=False), render(300, 200, COLORS, tail=True)
        self.assertGreater(tailed.image.height, plain.image.height)
        column = tailed.image.width - tailed.margin - 50  # where the tail's tip is
        pixel = tailed.image.getpixel((column, tailed.image.height - tailed.margin - 2))
        assert isinstance(pixel, tuple)
        self.assertGreater(pixel[3], 0)

    def test_scaling_makes_it_bigger(self) -> None:
        small, big = render(300, 200, COLORS), render(300, 200, COLORS, scale=lambda v: v * 2)
        self.assertGreater(big.image.width, small.image.width)


if __name__ == "__main__":
    unittest.main()
