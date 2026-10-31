import unittest

from carol_aio.icon import bust_image, name_image


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


class BustImageTest(unittest.TestCase):
    def test_the_bust_is_the_requested_height(self) -> None:
        self.assertEqual(bust_image(104).height, 104)

    def test_the_bust_is_taller_than_the_face_crop_not_wider(self) -> None:
        bust = bust_image(104)
        self.assertLess(bust.width, bust.height * 1.05)  # roughly as tall as wide, not a wide strip


if __name__ == "__main__":
    unittest.main()
