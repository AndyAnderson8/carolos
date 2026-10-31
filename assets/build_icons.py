"""Build the exe icon and the tray artwork from assets/pianta_source.png.

The source is the character on a flat background; this cuts it out and writes
assets/carol_aio.ico plus carol_aio/assets/pianta_face.png, a close-up of the
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
    face = cut_out(Image.open(SOURCE)).crop(FACE_BOX)
    face.thumbnail((FACE_PX, FACE_PX), Image.Resampling.LANCZOS)
    face.save(HERE.parent / "carol_aio" / "assets" / "pianta_face.png", optimize=True)

    rounded_tile(Image.open(SOURCE)).save(HERE / "carol_aio.ico", sizes=[(s, s) for s in SIZES])
    print("wrote carol_aio.ico and carol_aio/assets/pianta_face.png")


if __name__ == "__main__":
    main()
