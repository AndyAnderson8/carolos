import unittest

from carol_aio.icon import figure_image, hand_image, name_image, tray_icon


class NameImageTest(unittest.TestCase):
    def test_the_ink_is_exactly_the_requested_height(self) -> None:
        image = name_image(30, "#ffffff")
        self.assertEqual(image.height, 30)
        box = image.getbbox()
        assert box is not None
        self.assertLessEqual(box[1], 1)  # touches the top and the bottom, give or take a pixel
        self.assertGreaterEqual(box[3], 29)

    def test_it_takes_the_requested_colour(self) -> None:
        image = name_image(30, "#ff0000")
        pixels = (image.getpixel((x, y)) for y in range(image.height) for x in range(image.width))
        solid = [p for p in pixels if isinstance(p, tuple) and p[3] == 255]
        self.assertTrue(solid)
        self.assertTrue(all(p[:3] == (255, 0, 0) for p in solid))


class FigureImageTest(unittest.TestCase):
    def test_the_figure_is_the_requested_height(self) -> None:
        self.assertEqual(figure_image(104).height, 104)

    def test_the_figure_is_a_tall_rectangle(self) -> None:
        figure = figure_image(104)
        self.assertLess(figure.width, figure.height * 0.9)


class HandImageTest(unittest.TestCase):
    def test_it_is_the_same_size_as_the_figure_so_it_lines_up(self) -> None:
        self.assertEqual(hand_image(300).size, figure_image(300).size)

    def test_it_is_only_her_hand_on_the_left(self) -> None:
        hand = hand_image(300)
        box = hand.getchannel("A").point(lambda a: 255 if a > 40 else 0).getbbox()
        assert box is not None
        self.assertLess(box[2], hand.width * 0.65)  # nothing past the middle of the figure
        self.assertGreater(box[1], hand.height * 0.4)  # nothing up in her head or the palm


class TrayIconTest(unittest.TestCase):
    def test_it_is_square_at_any_size(self) -> None:
        for size in (16, 24, 32, 48):
            self.assertEqual(tray_icon(1, 1, size).size, (size, size))

    def test_the_zoomed_in_icon_shows_her_yellow_palm(self) -> None:
        icon_on = tray_icon(1, 1, 64).convert("RGBA")
        yellow = [
            p
            for p in (icon_on.getpixel((x, y)) for x in range(64) for y in range(30))
            if isinstance(p, tuple) and p[3] > 200 and p[0] > 220 and 150 < p[1] < 215 and p[2] < 80
        ]
        self.assertTrue(yellow)


if __name__ == "__main__":
    unittest.main()
