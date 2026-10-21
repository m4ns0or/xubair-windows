"""The small dark speech bubble that floats above his head — port of SpeechBubbleLayer.swift."""
from __future__ import annotations

from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

TAIL_H = 7
_FONT_CACHE = {}


def _font(size: int):
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]
    candidates = [
        "segoeui.ttf", "Segoe UI.ttf", "arial.ttf", "Arial.ttf",
        "DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf",
    ]
    font = None
    for c in candidates:
        try:
            font = ImageFont.truetype(c, size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    _FONT_CACHE[size] = font
    return font


def _wrap(text: str, font, max_w: float, draw: ImageDraw.ImageDraw) -> List[str]:
    words = text.split()
    lines: List[str] = []
    line: List[str] = []
    for w in words:
        test = " ".join(line + [w])
        if draw.textlength(test, font=font) > max_w and line:
            lines.append(" ".join(line))
            line = [w]
        else:
            line.append(w)
    if line:
        lines.append(" ".join(line))
    return lines or [text]


def render_bubble(text: str, max_width: float = 230, scale: float = 2.0,
                  tail_x_frac: float = 0.5) -> Tuple[Image.Image, Tuple[int, int]]:
    """Returns (RGBA image, (tail_tip_x, tail_tip_y)) where the tail tip points at his head.
    The image is rendered at `scale` for crispness; caller places tip over the head."""
    s = scale
    font = _font(int(round(12.5 * s)))
    measure = Image.new("RGBA", (4, 4))
    md = ImageDraw.Draw(measure)
    lines = _wrap(text, font, (max_width - 20) * s, md)

    line_h = (font.getbbox("Ag")[3] - font.getbbox("Ag")[1]) + int(4 * s)
    text_w = max(md.textlength(ln, font=font) for ln in lines)
    pad_x = int(11 * s)
    pad_y = int(8 * s)
    body_w = int(text_w + pad_x * 2)
    body_h = int(len(lines) * line_h + pad_y * 2)
    tail_h = int(TAIL_H * s)

    img = Image.new("RGBA", (body_w, body_h + tail_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = int(11 * s)
    d.rounded_rectangle([0, 0, body_w - 1, body_h - 1], radius=radius,
                        fill=(20, 20, 20, 235), outline=(255, 255, 255, 36), width=max(1, int(s)))
    tail_x = int(body_w * tail_x_frac)
    tail_x = max(int(14 * s), min(body_w - int(14 * s), tail_x))
    d.polygon([(tail_x - int(6 * s), body_h - 1), (tail_x + int(6 * s), body_h - 1),
               (tail_x, body_h + tail_h - 1)], fill=(20, 20, 20, 235))

    ty = pad_y
    for ln in lines:
        lw = d.textlength(ln, font=font)
        d.text(((body_w - lw) / 2, ty), ln, font=font, fill=(245, 245, 245, 255))
        ty += line_h

    return img, (tail_x, body_h + tail_h - 1)


def visible_seconds(text: str) -> float:
    return min(5.5, 1.8 + len(text) * 0.055)
