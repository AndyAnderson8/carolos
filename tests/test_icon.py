import unittest

from carol_aio.icon import figure_image, name_image


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


if __name__ == "__main__":
    unittest.main()
