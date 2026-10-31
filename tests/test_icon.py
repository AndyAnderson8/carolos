import unittest

from carol_aio.icon import face_image, name_image


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


class FaceImageTest(unittest.TestCase):
    def test_the_face_is_the_requested_height(self) -> None:
        self.assertEqual(face_image(54).height, 54)

    def test_the_face_is_wider_than_tall(self) -> None:
        face = face_image(54)
        self.assertGreater(face.width, face.height)


if __name__ == "__main__":
    unittest.main()
