"""Build the exe icon and the character artwork from assets/avatar_source.png.

The source is the character on a flat background; this cuts it out and writes
assets/carol_aio.ico plus, in carol_aio/assets/: avatar_figure.png (her whole figure, used in
the panel header and the tray icon) and avatar_hand.png (just her left hand and forearm, on a
canvas the same size, so the header can draw it in front of the wavy edge).
Run from the repo root: python assets/build_icons.py
"""

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = Path(__file__).parent
SOURCE = HERE / "avatar_source.png"
SIZES = [16, 24, 32, 48, 64, 128, 256]
FIGURE_BOX = (170, 40, 1070, 1170)  # her whole figure, palm to feet: a tall rectangle
HAND_BOX = (150, 560, 430, 900)  # her left hand and forearm, in source-image pixels
FIGURE_PX = 1024  # only the top of it is shown at a time, so it is kept sharper
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


def hand_layer(figure: Image.Image, scale: float) -> Image.Image:
    """Her left hand and forearm, with their outline, on a canvas the size of the figure.

    Found by colour: the pink inside ``HAND_BOX``, grown by the outline's thickness.
    """
    r, g, b, alpha = figure.split()
    pink = ImageChops.multiply(
        ImageChops.multiply(
            r.point(lambda v: 255 if v > 200 else 0),
            g.point(lambda v: 255 if 80 < v < 145 else 0),
        ),
        b.point(lambda v: 255 if 120 < v < 195 else 0),
    )
    area = Image.new("L", figure.size, 0)
    left, top, right, bottom = HAND_BOX
    left0, top0 = FIGURE_BOX[0], FIGURE_BOX[1]
    ImageDraw.Draw(area).rectangle(
        (
            round((left - left0) * scale),
            round((top - top0) * scale),
            round((right - left0) * scale),
            round((bottom - top0) * scale),
        ),
        fill=255,
    )
    grown = ImageChops.multiply(pink, area).filter(
        ImageFilter.MaxFilter(2 * round(7 * scale) + 1)  # the outline is about 7 pixels thick
    )
    out = figure.copy()
    out.putalpha(ImageChops.multiply(alpha, grown))
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
    figure = cutout.crop(FIGURE_BOX)
    figure.thumbnail((FIGURE_PX, FIGURE_PX), Image.Resampling.LANCZOS)
    scale = figure.width / (FIGURE_BOX[2] - FIGURE_BOX[0])
    assets = HERE.parent / "carol_aio" / "assets"
    figure.save(assets / "avatar_figure.png", optimize=True)
    hand_layer(figure, scale).save(assets / "avatar_hand.png", optimize=True)

    rounded_tile(Image.open(SOURCE)).save(HERE / "carol_aio.ico", sizes=[(s, s) for s in SIZES])
    print("wrote carol_aio.ico, avatar_figure.png and avatar_hand.png")


if __name__ == "__main__":
    main()
