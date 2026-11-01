"""The flyout's speech-bubble shape, drawn as one image with smooth, transparent edges.

The image holds everything that isn't a control: a soft shadow, the outlined bubble with
its tail pointing at the tray, the wavy sea-coloured header band, and her and the name
(she rises out of the band, over the top edge). The panel's real controls sit in a plain window
placed over the empty body area.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from carolos.icon import figure_image, hand_image, name_image

SS = 3  # drawn this many times larger, then shrunk, so the edges are smooth
NECK = 0.615  # how far down her picture the wave crosses her (0 is the top, 1 the bottom)
Point = tuple[float, float]


@dataclass(frozen=True)
class BubbleColors:
    panel: str
    outline: str
    sea: str
    on_sea: str
    shadow: float  # shadow strength, 0 to 1


@dataclass(frozen=True)
class Bubble:
    image: Image.Image
    content_x: int  # where the controls' window goes inside the image
    content_y: int
    margin: int  # transparent space beside and below the bubble (for the shadow)
    body_y: int  # where the bubble's own top edge is; she pokes up above it
    name_box: tuple[int, int, int, int]  # left, top, right, bottom of "CaroLoS"
    blue_space: tuple[int, int]  # left and right ends of the blue space the name is centred in
    band: int  # height of the blue header band


def _bezier(p0: Point, p1: Point, p2: Point, steps: int = 14) -> list[Point]:
    out: list[Point] = []
    for i in range(steps + 1):
        t = i / steps
        out.append(
            (
                (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0],
                (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1],
            )
        )
    return out


def _arc(cx: float, cy: float, r: float, start: float, end: float, steps: int = 16) -> list[Point]:
    angles = [start + (end - start) * i / steps for i in range(steps + 1)]
    return [
        (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in angles
    ]


def _outline(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    r: float,
    tail: tuple[float, float, float, float] | None,
) -> list[Point]:
    """A closed clockwise path round a rounded rectangle, with an optional tail on its bottom edge.

    ``tail`` is (base left x, base right x, tip x, tip y).
    """
    pts: list[Point] = [(x0 + r, y0)]
    pts += _arc(x1 - r, y0 + r, r, -90, 0)
    pts += _arc(x1 - r, y1 - r, r, 0, 90)
    if tail is not None:
        left, right, tip_x, tip_y = tail
        pts.append((right, y1))
        pts += _bezier((right, y1), (right - 1, y1 + (tip_y - y1) * 0.6), (tip_x, tip_y))
        pts += _bezier(
            (tip_x, tip_y), (left + (tip_x - left) * 0.25, y1 + (tip_y - y1) * 0.9), (left, y1)
        )
    pts += _arc(x0 + r, y1 - r, r, 90, 180)
    pts += _arc(x0 + r, y0 + r, r, 180, 270)
    return pts


def render(
    content_w: int,
    content_h: int,
    colors: BubbleColors,
    scale: Callable[[int], int] = lambda v: v,
    tail: bool = True,
) -> Bubble:
    """Draw a bubble with room for a ``content_w`` by ``content_h`` window in its body.

    ``scale`` turns design pixels into real ones (display scaling).
    """
    s = scale
    margin, top, pad, line, radius = (
        s(18),
        s(48),
        s(10),
        s(2),
        s(22),
    )  # top: room for her to poke out
    left = s(34)  # extra room on the left: her hand sticks out past the edge
    band, amplitude, wavelength, tail_h = s(82), s(3), s(46), s(16)
    body_w = content_w + 2 * pad
    clear = s(20)  # sand between the wave and the controls: room for her hand, and no blur
    body_h = band + amplitude + clear + content_h + pad
    width = left + body_w + margin
    height = top + body_h + (tail_h if tail else 0) + margin
    x0, y0, x1, y1 = left, top, left + body_w, top + body_h
    tail_geometry = (x1 - s(82), x1 - s(46), x1 - s(50), y1 + tail_h) if tail else None
    path = _outline(x0, y0, x1, y1, radius, tail_geometry)

    big = [(x * SS, y * SS) for x, y in path]
    layer = Image.new("RGBA", (width * SS, height * SS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.polygon(big, fill=colors.panel)

    # The sea band: everything inside the bubble above a wavy line.
    inside = Image.new("L", layer.size, 0)
    ImageDraw.Draw(inside).polygon(big, fill=255)
    wave = [
        (x * SS, (y0 + band + amplitude * math.sin(2 * math.pi * (x - x0) / wavelength)) * SS)
        for x in range(x0, x1 + 1)
    ]
    above = Image.new("L", layer.size, 0)
    hand_floor = (y0 + band + s(20)) * SS  # outside the left edge, only her hand shows, above this
    ImageDraw.Draw(above).polygon(
        [(0, 0), (0, hand_floor), (x0 * SS, hand_floor), *wave, (x1 * SS, 0)], fill=255
    )
    layer.paste(colors.sea, mask=ImageChops.multiply(inside, above))
    draw.line([*big, big[0]], fill=colors.outline, width=line * SS, joint="curve")

    # Her palm and head rise out of the band over the top edge, and her left hand sticks out past
    # the left edge. The body below the wave is in front of her, so the wave reads as the top of
    # her outfit.
    figure_h = s(190)
    figure = figure_image(figure_h * SS)
    figure_x = (x0 - s(17)) * SS
    figure_y = round((y0 + band - NECK * figure_h) * SS)  # where the wave crosses her
    placed = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    placed.alpha_composite(figure, (figure_x, figure_y))
    placed.putalpha(ImageChops.multiply(placed.getchannel("A"), above))
    layer.alpha_composite(placed)
    draw.line(wave, fill=colors.outline, width=line * SS)
    # Her left hand is drawn last, unclipped, so the wavy edge passes behind it, not through it.
    layer.alpha_composite(hand_image(figure_h * SS), (figure_x, figure_y))
    bubble = layer.resize((width, height), Image.Resampling.LANCZOS)

    # A soft shadow underneath, drawn at normal size.
    shadow = Image.new("L", (width, height), 0)
    ImageDraw.Draw(shadow).polygon(
        [(x, y + s(4)) for x, y in path], fill=round(255 * colors.shadow)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(s(6)))
    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    out.paste((0, 0, 0, 255), mask=shadow)
    out.alpha_composite(bubble)

    # The name sits (nearly) centred in the blue space left over beside her: between the right-hand edge of
    # her (as high up as the band goes) and the bubble's right edge, and between the top and the wave.
    name = name_image(s(31), colors.on_sea)
    band_top, band_bottom = y0 * SS - figure_y, (y0 + band) * SS - figure_y
    rows = figure.getchannel("A").crop(
        (0, max(0, band_top), figure.width, min(figure.height, band_bottom))
    )
    ink = rows.getbbox()
    her_right = round((figure_x + (ink[2] if ink else figure.width)) / SS)
    name_x = round((her_right + x1 - name.width) / 2) - s(10)  # a little left of dead centre
    name_y = round(y0 + band / 2 - name.height / 2)
    out.alpha_composite(name, (name_x, name_y))
    name_box = (name_x, name_y, name_x + name.width, name_y + name.height)
    return Bubble(
        out, x0 + pad, y0 + band + amplitude + clear, margin, y0, name_box, (her_right, x1), band
    )
