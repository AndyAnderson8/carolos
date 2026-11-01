"""The character artwork: the panel header pieces and the tray icon."""

from __future__ import annotations

import ctypes
import sys
from functools import cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from carolos.theme import LOGO_YELLOW

FIGURE = Path(__file__).with_name("assets") / "avatar_figure.png"
HAND = Path(__file__).with_name("assets") / "avatar_hand.png"
TITLE_FONT = Path(__file__).with_name("assets") / "LilyScriptOne-Regular.ttf"  # OFL, see OFL.txt
TITLE = "CaroLoS"
# The part of the figure the tray icon zooms in on, as fractions (left, top, right, bottom):
# her palm, flower and head. Her whole figure is too small to make out at 16 to 32 pixels.
TRAY_CROP = (0.12, 0.02, 0.88, 0.46)
SCALE = 4  # the name is drawn this many times larger, then shrunk, for smooth edges
PANEL = "#1d2226"


@cache
def _figure() -> Image.Image:
    return Image.open(FIGURE).convert("RGBA")


@cache
def _hand() -> Image.Image:
    return Image.open(HAND).convert("RGBA")


def figure_image(height: int) -> Image.Image:
    """Her whole figure, from the palm to her feet, ``height`` pixels tall."""
    figure = _figure()
    return figure.resize(
        (round(figure.width * height / figure.height), height), Image.Resampling.LANCZOS
    )


def hand_image(height: int) -> Image.Image:
    """Just her left hand and forearm, on a canvas exactly the size ``figure_image`` gives."""
    hand = _hand()
    return hand.resize((round(hand.width * height / hand.height), height), Image.Resampling.LANCZOS)


def name_image(height: int, color: str) -> Image.Image:
    """ "CaroLoS" in Lily Script One, with the letters' ink exactly ``height`` pixels tall.

    Drawn from the font's own measurements, so the ink runs from the very top of the tallest
    letter to the bottom of the line, with no empty text-box space above or below.
    """
    big = height * SCALE
    probe = ImageFont.truetype(str(TITLE_FONT), 1000)
    _, top, _, bottom = probe.getbbox(TITLE, anchor="ls")
    font = ImageFont.truetype(str(TITLE_FONT), round(1000 * big / (bottom - top)))
    left, top, right, _ = font.getbbox(TITLE, anchor="ls")  # relative to the baseline's left end
    canvas = Image.new("RGBA", (round(right - left), big), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).text((-left, -top), TITLE, font=font, fill=color, anchor="ls")
    return canvas.resize((round(canvas.width / SCALE), height), Image.Resampling.LANCZOS)


def tray_pixels() -> int:
    """Size Windows wants for notification-area icons (scales with display DPI)."""
    if sys.platform == "win32":
        try:
            return int(ctypes.windll.user32.GetSystemMetrics(49))  # SM_CXSMICON
        except (AttributeError, OSError):
            pass
    return 16


def _font(px: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("segoeuib.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def tray_icon(running: int, total: int, size: int) -> Image.Image:
    """Her palm, flower and head, zoomed in, over a "running/total" count; grey when off.

    Zoomed in because the yellow palm on the pink head is what she is recognised by at this size.
    """
    figure = _figure()
    left, top, right, bottom = TRAY_CROP
    art = figure.crop(
        (
            round(left * figure.width),
            round(top * figure.height),
            round(right * figure.width),
            round(bottom * figure.height),
        )
    )
    art = art.resize((size, max(1, round(size * art.height / art.width))), Image.Resampling.LANCZOS)
    if running == 0:
        grey = art.convert("LA").convert("RGBA")
        grey.putalpha(art.getchannel("A").point(lambda a: int(a * 0.7)))
        art = grey
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(art, (0, 0))

    scale = 4
    big = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(big)
    text = f"{running}/{total}"
    font = _font(round(size * scale * 0.36))
    stroke = max(scale, round(size * scale / 16))
    box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    x = (size * scale - (box[2] - box[0])) / 2 - box[0]
    y = size * scale - (box[3] - box[1]) - box[1]
    draw.text(
        (x, y),
        text,
        font=font,
        fill=LOGO_YELLOW if running else "#ffffff",
        stroke_width=stroke,
        stroke_fill=PANEL,
    )
    canvas.alpha_composite(big.resize((size, size), Image.Resampling.LANCZOS))
    return canvas
