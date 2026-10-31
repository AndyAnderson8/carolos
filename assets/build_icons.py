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
BUST_BOX = (250, 40, 1045, 1170)  # her whole figure, palm to feet: a tall rectangle
BUST_PX = 1024  # only the top of it is shown at a time, so it is kept sharper
# Bits of the palm that poke into the top of the face crop, in source-image pixels.
ERASE = [
    [(518, 255), (646, 255), (646, 343), (560, 343), (560, 306), (518, 306)],  # the trunk
    [(290, 255), (390, 255), (390, 308), (290, 308)],  # a yellow frond
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


def erase(image: Image.Image, shapes: list[list[tuple[int, int]]]) -> Image.Image:
    """Make the given regions (in this image's pixels) transparent, with smooth edges."""
    scale = 4
    out = image.copy()
    for shape in shapes:
        left, top = min(x for x, _ in shape), min(y for _, y in shape)
        right, bottom = max(x for x, _ in shape), max(y for _, y in shape)
        mask = Image.new("L", ((right - left) * scale, (bottom - top) * scale), 255)
        ImageDraw.Draw(mask).polygon(
            [((x - left) * scale, (y - top) * scale) for x, y in shape], fill=0
        )
        mask = mask.resize((right - left, bottom - top), Image.Resampling.LANCZOS)
        patch = out.crop((left, top, right, bottom))
        patch.putalpha(ImageChops.multiply(patch.getchannel("A"), mask))
        out.paste(patch, (left, top))
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
    cutout = cut_out(Image.open(SOURCE))
    for name, figure, box, size in (
        ("pianta_face.png", erase(cutout, ERASE), FACE_BOX, FACE_PX),
        ("pianta_bust.png", cutout, BUST_BOX, BUST_PX),  # keeps the palm
    ):
        crop = figure.crop(box)
        crop.thumbnail((size, size), Image.Resampling.LANCZOS)
        crop.save(HERE.parent / "carol_aio" / "assets" / name, optimize=True)

    rounded_tile(Image.open(SOURCE)).save(HERE / "carol_aio.ico", sizes=[(s, s) for s in SIZES])
    print("wrote carol_aio.ico, pianta_face.png and pianta_bust.png")


if __name__ == "__main__":
    main()
