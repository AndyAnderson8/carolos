import unittest

from carol_aio.icon import lockup_image


class LockupTest(unittest.TestCase):
    def test_the_lockup_is_exactly_the_requested_height(self) -> None:
        self.assertEqual(lockup_image(26, "#ffffff").height, 26)

    def test_the_name_spans_the_full_height_of_the_face(self) -> None:
        image = lockup_image(40, "#ffffff")
        face = image.crop((0, 0, image.width // 5, image.height)).getbbox()
        name = image.crop((image.width * 45 // 100, 0, image.width, image.height)).getbbox()
        assert face is not None and name is not None
        for box in (face, name):  # both touch the top and the bottom, give or take a pixel
            self.assertLessEqual(box[1], 1)
            self.assertGreaterEqual(box[3], image.height - 1)

    def test_the_name_takes_the_requested_colour(self) -> None:
        image = lockup_image(40, "#ff0000")
        right = image.crop((image.width * 45 // 100, 0, image.width, image.height))
        pixels = (right.getpixel((x, y)) for y in range(right.height) for x in range(right.width))
        solid = [p for p in pixels if isinstance(p, tuple) and p[3] == 255]
        self.assertTrue(solid)
        self.assertTrue(all(p[:3] == (255, 0, 0) for p in solid))


if __name__ == "__main__":
    unittest.main()
