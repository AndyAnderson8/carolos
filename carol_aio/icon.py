"""Tray icon: the app artwork over a "running/total" count."""

from __future__ import annotations

import base64
import ctypes
import io
import sys
import tkinter as tk
from functools import cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from carol_aio.theme import LOGO_YELLOW

ART = Path(__file__).with_name("assets") / "pianta_face.png"
TITLE_FONT = Path(__file__).with_name("assets") / "Pacifico-Regular.ttf"  # OFL, see OFL.txt
TITLE = "Carol AIO"
SCALE = 4  # the lockup is drawn this many times larger, then shrunk, for smooth edges
GAP = 10  # pixels between the face and the name
PANEL = "#1d2226"


@cache
def _face() -> Image.Image:
    return Image.open(ART).convert("RGBA")


def lockup_image(height: int, color: str) -> Image.Image:
    """The face with "Carol AIO" beside it, both exactly ``height`` pixels tall.

    The name is drawn from the font's own measurements, so the letters' ink runs from the
    very top of the face to the very bottom (not floating inside a text box) and the two
    sit on the same line.
    """
    big = height * SCALE
    face = _face()
    face = face.crop(face.getbbox() or (0, 0, *face.size))
    face = face.resize((round(face.width * big / face.height), big), Image.Resampling.LANCZOS)

    probe = ImageFont.truetype(str(TITLE_FONT), 1000)
    _, top, _, bottom = probe.getbbox(TITLE, anchor="ls")
    font = ImageFont.truetype(str(TITLE_FONT), round(1000 * big / (bottom - top)))
    left, top, right, _ = font.getbbox(TITLE, anchor="ls")  # relative to the baseline's left end

    gap = GAP * SCALE
    canvas = Image.new("RGBA", (face.width + gap + round(right - left), big), (0, 0, 0, 0))
    canvas.alpha_composite(face, (0, 0))
    ImageDraw.Draw(canvas).text(
        (face.width + gap - left, -top), TITLE, font=font, fill=color, anchor="ls"
    )
    return canvas.resize((round(canvas.width / SCALE), height), Image.Resampling.LANCZOS)


def lockup_photo(height: int, color: str) -> tk.PhotoImage:
    """``lockup_image`` as a Tk image, for the panel header."""
    buffer = io.BytesIO()
    lockup_image(height, color).save(buffer, "PNG")
    return tk.PhotoImage(data=base64.b64encode(buffer.getvalue()))


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
    """A close-up of the face over a "running/total" count; grey when nothing is running."""
    art = _face()
    face_h = max(1, round(size * art.height / art.width))
    art = art.resize((size, face_h), Image.Resampling.LANCZOS)
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
