"""Build the exe icon and the tray artwork from assets/pianta_source.png.

The source is the character on a flat background; this cuts it out and writes
assets/carol_aio.ico plus two crops of the character in carol_aio/assets/: pianta_face.png, a close-up of the
face that stays recognisable at tray size.
Run from the repo root: python assets/build_icons.py
"""

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = Path(__file__).parent
SOURCE = HERE / "pianta_source.png"
SIZES = [16, 24, 32, 48, 64, 128, 256]
FACE_PX = 512
FACE_BOX = (335, 285, 975, 705)  # flower, eye and nose, in source-image pixels
BUST_BOX = (320, 255, 990, 980)  # head, upper body and the start of the skirt
# Bits of the palm that poke into the top of the bust crop, as fractions of the crop (x, y).
BUST_ERASE = [
    [(0.296, 0.0), (0.486, 0.0), (0.486, 0.113), (0.355, 0.113), (0.355, 0.07), (0.296, 0.07)],
    [(0.0, 0.0), (0.127, 0.0), (0.127, 0.049), (0.0, 0.049)],
]
TILE_PX = 1024  # drawn large, then shrunk so the rounded corners are smooth
TILE_RADIUS = 0.22  # corner radius as a fraction of the tile
TILE_FILL = 0.92  # how much of the tile the artwork covers
BACKGROUND_TOLERANCE = 50


def cut_out(source: Image.Image) -> Image.Image:
    """Make the flat background transparent, keeping the dark outline intact."""
    rgb = source.convert("RGB")
    background = rgb.getpixel((4, 4))
    distance = ImageChops.difference(rgb, Image.new("RGB", rgb.size, background)).convert("L")
    near = distance.point(lambda v: 255 if v < BACKGROUND_TOLERANCE else 0)
    ImageDraw.floodfill(near, (0, 0), 128)  # only background touching the border
    alpha = near.point(lambda v: 0 if v == 128 else 255)
    # Pull the edge in past the blue-tinged antialiasing, then soften it again.
    alpha = alpha.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(1.2))
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


def erase(image: Image.Image, shapes: list[list[tuple[float, float]]]) -> Image.Image:
    """Make the given regions (fractions of the image) transparent, with smooth edges."""
    scale = 4
    mask = Image.new("L", (image.width * scale, image.height * scale), 255)
    for shape in shapes:
        ImageDraw.Draw(mask).polygon([(x * mask.width, y * mask.height) for x, y in shape], fill=0)
    mask = mask.resize(image.size, Image.Resampling.LANCZOS)
    out = image.copy()
    out.putalpha(ImageChops.multiply(out.getchannel("A"), mask))
    return out


def rounded_tile(source: Image.Image) -> Image.Image:
    """The artwork on its own background, clipped to a rounded square."""
    rgb = source.convert("RGB")
    tile = Image.new("RGB", (TILE_PX, TILE_PX), rgb.getpixel((4, 4)))
    inner = round(TILE_PX * TILE_FILL)
    art = rgb.resize((inner, inner), Image.Resampling.LANCZOS)
    tile.paste(art, ((TILE_PX - inner) // 2, (TILE_PX - inner) // 2))
    mask = Image.new("L", (TILE_PX, TILE_PX), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, TILE_PX - 1, TILE_PX - 1), radius=round(TILE_PX * TILE_RADIUS), fill=255
    )
    out = tile.convert("RGBA")
    out.putalpha(mask)
    return out.resize((256, 256), Image.Resampling.LANCZOS)


def main() -> None:
    figure = cut_out(Image.open(SOURCE))
    for name, box in (("pianta_face.png", FACE_BOX), ("pianta_bust.png", BUST_BOX)):
        crop = figure.crop(box)
        crop.thumbnail((FACE_PX, FACE_PX), Image.Resampling.LANCZOS)
        if name == "pianta_bust.png":
            crop = erase(crop, BUST_ERASE)
        crop.save(HERE.parent / "carol_aio" / "assets" / name, optimize=True)

    rounded_tile(Image.open(SOURCE)).save(HERE / "carol_aio.ico", sizes=[(s, s) for s in SIZES])
    print("wrote carol_aio.ico, pianta_face.png and pianta_bust.png")


if __name__ == "__main__":
    main()
