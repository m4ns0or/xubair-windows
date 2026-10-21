"""Decorative effects around the character — a per-frame Pillow port of EffectsLayer.swift.

The Swift version builds Core Animation layers once and lets the render server animate them.
Here we redraw each active effect every frame, driven by a wall-clock phase `t` (seconds),
onto the character canvas. Positions use the Swift y-up, feet-origin convention and are
converted to top-down Pillow pixels at draw time.
"""
from __future__ import annotations

import math
import random
from typing import Optional, Set, Tuple

from PIL import Image, ImageDraw, ImageFont

from ..core.types import BodyView, Effect, Facing, MotionKind, Pose

TWO_PI = 2 * math.pi
_FONT_CACHE = {}
_EMOJI_FONT = None
_EMOJI_TRIED = False


def _font(size: int, bold: bool = False):
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    names = (["segoeuib.ttf", "Arial Bold.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold
             else ["segoeui.ttf", "arial.ttf", "Arial.ttf", "DejaVuSans.ttf",
                   "/System/Library/Fonts/Helvetica.ttc"])
    font = None
    for n in names:
        try:
            font = ImageFont.truetype(n, size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


def _emoji_font(size: int):
    global _EMOJI_FONT, _EMOJI_TRIED
    try:
        for n in ["seguiemj.ttf", "/System/Library/Fonts/Apple Color Emoji.ttc",
                  "NotoColorEmoji.ttf"]:
            try:
                return ImageFont.truetype(n, size)
            except Exception:
                continue
    except Exception:
        pass
    return _font(size)


def _text(d, s, size, color, cx, cy, bold=True, emoji=False):
    font = _emoji_font(size) if emoji else _font(size, bold)
    try:
        bbox = d.textbbox((0, 0), s, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        kw = {"embedded_color": True} if emoji else {}
        d.text((cx - w / 2 - bbox[0], cy - h / 2 - bbox[1]), s, font=font, fill=color, **kw)
    except Exception:
        d.text((cx, cy), s, font=font, fill=color)


def draw_effects(canvas: Image.Image, feet: Tuple[float, float], effects: Set[Effect],
                 facing: Facing, height: float, body_top_yup: float, pose: Pose, t: float,
                 reduce: bool = False, sign_text: str = "", carried_emoji: str = "⚽️") -> None:
    if not effects:
        return
    d = ImageDraw.Draw(canvas)
    fx, fy = feet
    sign = facing.sign
    h = height

    def P(xup, yup):
        return (fx + xup, fy - yup)

    top = max(body_top_yup, 0.9 * h)

    for e in effects:
        if e is Effect.zzz:
            _zzz(d, P, sign, h, t, reduce)
        elif e is Effect.sweat and not reduce:
            _sweat(d, P, h, t)
        elif e is Effect.sparkles and not reduce:
            _sparkles(d, P, h, t)
        elif e is Effect.confetti and not reduce:
            _confetti(canvas, P, h, t)
        elif e is Effect.glassAhead:
            _glass(canvas, P, sign, h, t, reduce)
        elif e is Effect.keyboard:
            _keyboard(d, P, h, t, reduce)
        elif e is Effect.exclaim:
            _mark(d, "!", (255, 107, 64, 255), P, sign, h, top, t, reduce)
        elif e is Effect.question:
            _mark(d, "?", (140, 204, 255, 255), P, sign, h, top, t, reduce)
        elif e is Effect.knockRipple and not reduce:
            _ripple(d, P, h, t)
        elif e is Effect.meeting:
            _flip_chart(d, P, h)
        elif e is Effect.crumbs and not reduce:
            _crumbs(d, P, sign, h, t)
        elif e is Effect.dizzyStars:
            _dizzy_stars(d, P, h, top, t, reduce)
        elif e is Effect.caffeine and not reduce:
            _caffeine(d, P, h, t)
        elif e in (Effect.document, Effect.carryLight):
            _document(d, P, sign, h)
        elif e is Effect.carryMedium:
            _binder(d, P, sign, h)
        elif e is Effect.carryHeavy:
            _box(d, P, sign, h, big=False)
        elif e is Effect.carryMassive:
            _box(d, P, sign, h, big=True)
        elif e is Effect.sign:
            _sign(d, P, h, sign_text)
        elif e is Effect.carryItem:
            _text(d, carried_emoji, int(max(14, h * 0.17)), (255, 255, 255, 255), *P(0.1 * h * sign, 0.5 * h),
                  emoji=True)


def _zzz(d, P, sign, h, t, reduce):
    base = P(-0.42 * h * sign, 0.3 * h)
    color = (242, 242, 242, 230)
    if reduce:
        _text(d, "z Z", int(max(10, h * 0.09)), color, *base)
        return
    for i in range(3):
        ph = ((t + i * 0.8) % 2.4) / 2.4
        alpha = _keyed(ph, [0, 0.2, 0.7, 1], [0, 1, 1, 0])
        x = base[0] + (-0.15 * h * sign) * ph
        y = base[1] + (0.3 * h) * ph
        c = (color[0], color[1], color[2], int(color[3] * alpha))
        _text(d, "z" if i == 0 else "Z", int(max(9, h * (0.06 + 0.025 * i))), c, x, y)


def _sweat(d, P, h, t):
    for k, side in enumerate((-1.0, 1.0)):
        ph = ((t + (0.35 if side > 0 else 0)) % 0.7) / 0.7
        alpha = _keyed(ph, [0, 0.5, 1], [0, 1, 0])
        x, y = P(side * (0.12 + 0.12 * ph) * h, 0.9 * h + 0.06 * h * ph)
        r = max(2.5, h * 0.018)
        d.ellipse([x - r, y - r * 1.4, x + r, y + r], fill=(153, 217, 255, int(230 * alpha)))


def _sparkles(d, P, h, t):
    rng = random.Random(42)
    for i in range(6):
        sx = rng.uniform(-0.45, 0.45) * h
        sy = rng.uniform(0.2, 1.15) * h
        size = max(8, h * rng.uniform(0.05, 0.09))
        ph = ((t + i * 0.17) % 0.9) / 0.9
        alpha = _keyed(ph, [0, 0.5, 1], [0, 1, 0])
        scale = _keyed(ph, [0, 0.5, 1], [0.3, 1.2, 0.3])
        _text(d, "✦", int(size * scale), (255, 224, 115, int(255 * alpha)), *P(sx, sy), bold=False)


def _confetti(canvas, P, h, t):
    rng = random.Random(7)
    colors = [(255, 105, 180), (255, 214, 10), (90, 200, 220), (255, 149, 0),
              (175, 82, 222), (52, 199, 89)]
    d = ImageDraw.Draw(canvas)
    for i in range(28):
        start_x = rng.uniform(-0.9, 0.9) * h
        dur = rng.uniform(1.6, 2.8)
        begin = rng.uniform(0, 0.6)
        ph = (((t - begin) % dur) / dur)
        y_from = rng.uniform(1.25, 1.5) * h
        y = y_from * (1 - ph)
        x = start_x + rng.uniform(-0.25, 0.25) * h * ph
        alpha = 1.0 if ph < 0.8 else max(0.0, 1 - (ph - 0.8) / 0.2)
        cx, cy = P(x, y)
        w = max(3, h * 0.025)
        hh = max(5, h * 0.045)
        ang = rng.uniform(-3, 3) + ph * rng.uniform(-6, 6)
        _rot_rect(canvas, cx, cy, w, hh, ang, colors[i % len(colors)] + (int(255 * alpha),))


def _glass(canvas, P, sign, h, t, reduce):
    d = ImageDraw.Draw(canvas)
    cx, cy = P(0.3 * h * sign, 0)
    w = max(5, h * 0.045)
    x0 = cx - w / 2
    y_bottom = cy + 0.02 * h
    y_top = cy - 1.33 * h
    shimmer = 1.0 if reduce else (0.78 + 0.22 * math.sin(t * TWO_PI / 1.8))
    d.rounded_rectangle([x0, y_top, x0 + w, y_bottom], radius=w / 2,
                        fill=(200, 230, 255, int(50 * shimmer)), outline=(255, 255, 255, 90), width=1)
    for yy in (0.5, 0.62):
        hx, hy = P(-sign * w * 0.15, yy * h)
        hw = w * 1.1
        hh = h * 0.07
        d.rounded_rectangle([hx - hw / 2, hy - hh / 2, hx + hw / 2, hy + hh / 2],
                            radius=w * 0.5, fill=(255, 255, 255, 56))


def _keyboard(d, P, h, t, reduce):
    w = 0.5 * h
    kh = 0.085 * h
    cx, cy = P(0, 0.34 * h)
    x0, y0 = cx - w / 2, cy - kh / 2
    d.rounded_rectangle([x0, y0, x0 + w, y0 + kh], radius=3,
                        fill=(102, 230, 255, 20), outline=(128, 235, 255, 180), width=1)
    cols, rows = 9, 3
    kw = (w - 8) / cols
    rh = (kh - 6) / rows
    pulse = 1.0 if reduce else (0.6 + 0.4 * abs(math.sin(t * math.pi / 0.18)))
    if kw > 2.5 and rh > 2.5:
        for r in range(rows):
            for c in range(cols):
                kx = x0 + 4 + c * kw + 1
                ky = y0 + 3 + r * rh + 1
                d.rectangle([kx, ky, kx + kw - 2, ky + rh - 2], fill=(128, 235, 255, int(72 * pulse)))


def _mark(d, s, color, P, sign, h, top, t, reduce):
    cx, cy = P(0.24 * h * sign, max(top, 0.9 * h) + 0.02 * h)
    scale = 1.0
    if not reduce:
        ph = min(1.0, t / 0.3) if t < 0.3 else 1.0
        scale = _keyed(ph, [0, 0.6, 1], [0.2, 1.3, 1])
    _text(d, s, int(max(14, h * 0.17) * scale), color, cx, cy)


def _ripple(d, P, h, t):
    cx, cy = P(0, 0.62 * h)
    for i in range(3):
        ph = ((t + i * 0.33) % 0.8) / 0.8
        r = 0.35 * h * (0.2 + 1.4 * ph)
        alpha = int(255 * 0.8 * (1 - ph))
        if alpha <= 0:
            continue
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, alpha), width=2)


def _crumbs(d, P, sign, h, t):
    rng = random.Random(11)
    colors = [(217, 153, 77), (242, 204, 115)]
    for i in range(8):
        ph = ((t + i * 0.12) % 0.7) / 0.7
        dx = rng.uniform(-0.15, 0.15) * h
        x, y = P(0.02 * h * sign + dx * ph, 0.8 * h + 0.75 * h * ph)
        alpha = 1.0 if ph < 0.66 else max(0.0, 1 - (ph - 0.66) / 0.34)
        r = max(1.5, h * 0.012)
        d.ellipse([x - r, y - r, x + r, y + r], fill=colors[i % 2] + (int(255 * alpha),))


def _dizzy_stars(d, P, h, top, t, reduce):
    cx, cy = P(0, max(top, 0.95 * h) - 0.02 * h)
    rx, ry = 0.2 * h, 0.05 * h
    for i in range(3):
        phase = i / 3 * TWO_PI + (0 if reduce else t / 1.1 * TWO_PI)
        x = cx + rx * math.cos(phase)
        y = cy - ry * math.sin(phase)
        _text(d, "✦" if i == 1 else "★", int(max(9, h * 0.07)), (255, 217, 77, 255), x, y, bold=False)


def _caffeine(d, P, h, t):
    for i, x in enumerate((-0.26, 0.26, 0.2)):
        ph = ((t + i * 0.2) % 0.6) / 0.6
        alpha = _keyed(ph, [0, 0.25, 0.5, 0.75, 1], [0, 1, 0.2, 1, 0])
        cx, cy = P(x * h, (0.95 + 0.12 * (i % 2)) * h)
        _text(d, "⚡", int(max(9, h * 0.075)), (255, 230, 51, int(255 * alpha)), cx, cy, bold=True)


def _document(d, P, sign, h):
    w, hh = 0.2 * h, 0.26 * h
    cx, cy = P(0.1 * h * sign, 0.5 * h)
    _rot_filled_rect(d, cx, cy, w, hh, math.degrees(0.12 * sign), (250, 250, 250, 255))
    # lines
    for i in range(6):
        ly = cy - hh * (0.3 - i * 0.12)
        lw = (0.09 if i == 5 else 0.15) * h
        d.rectangle([cx - w * 0.4, ly, cx - w * 0.4 + lw, ly + max(1, 0.008 * h)], fill=(140, 140, 140, 255))


def _binder(d, P, sign, h):
    w, hh = 0.2 * h, 0.25 * h
    cx, cy = P(0.08 * h * sign, 0.46 * h)
    d.rectangle([cx - w / 2, cy - hh / 2, cx + w / 2, cy + hh / 2], fill=(46, 97, 191, 255),
                outline=(26, 56, 128, 255), width=1)
    d.rectangle([cx - w * 0.25, cy - hh * 0.1, cx - w * 0.25 + 0.12 * h, cy - hh * 0.1 + 0.06 * h],
                fill=(242, 242, 242, 255))


def _box(d, P, sign, h, big):
    w = (0.46 if big else 0.32) * h
    bh = (0.36 if big else 0.24) * h
    cx, cy = P(0.04 * h * sign, (0.34 if big else 0.4) * h)
    color = (115, 77, 41, 255) if big else (194, 148, 92, 255)
    d.rectangle([cx - w / 2, cy - bh / 2, cx + w / 2, cy + bh / 2], fill=color)
    if big:
        for i in range(1, 4):
            yy = cy - bh / 2 + bh * i / 4
            d.line([cx - w / 2, yy, cx + w / 2, yy], fill=(71, 46, 23, 255), width=max(1, int(h * 0.01)))
        _text(d, "HEAVY", int(max(7, h * 0.05)), (217, 51, 38, 230), cx, cy)
    else:
        d.rectangle([cx - w * 0.08, cy - bh / 2, cx + w * 0.08, cy + bh / 2], fill=(230, 204, 140, 230))


def _sign(d, P, h, sign_text):
    msg = sign_text if sign_text else "Reminder!"
    font = _font(int(max(11, h * 0.085)), bold=True)
    max_w = max(140, h * 1.45)
    lines = []
    words = msg.split()
    line = []
    for w in words:
        if d.textlength(" ".join(line + [w]), font=font) > max_w - 24 and line:
            lines.append(" ".join(line))
            line = [w]
        else:
            line.append(w)
    if line:
        lines.append(" ".join(line))
    lh = font.getbbox("Ag")[3] - font.getbbox("Ag")[1] + 4
    tw = max((d.textlength(ln, font=font) for ln in lines), default=40)
    bw = min(max_w, tw + 24)
    bh = len(lines) * lh + 18
    cx, cy = P(0, 1.0 * h)
    # stick
    d.rectangle([cx - 2, cy, cx + 2, cy + 0.42 * h], fill=(140, 97, 51, 255))
    # board above head
    x0 = cx - bw / 2
    y0 = cy - bh
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=3, fill=(219, 184, 128, 255),
                        outline=(153, 115, 71, 255), width=1)
    ty = y0 + 9
    for ln in lines:
        lw = d.textlength(ln, font=font)
        d.text((cx - lw / 2, ty), ln, font=font, fill=(31, 31, 31, 255))
        ty += lh


def _flip_chart(d, P, h):
    cx, cy = P(0.62 * h, 0)
    w, bh, leg = 0.36 * h, 0.3 * h, 0.24 * h
    d.line([cx - w * 0.35, cy, cx - w * 0.2, cy - leg], fill=(64, 64, 64, 255), width=max(1, int(h * 0.012)))
    d.line([cx + w * 0.35, cy, cx + w * 0.2, cy - leg], fill=(64, 64, 64, 255), width=max(1, int(h * 0.012)))
    bx0 = cx - w / 2
    by0 = cy - leg - bh
    d.rectangle([bx0, by0, bx0 + w, by0 + bh], fill=(245, 245, 245, 255), outline=(77, 77, 77, 255))
    _text(d, "Q4 GOALS", int(max(7, h * 0.045)), (38, 38, 38, 255), cx, by0 + h * 0.04)
    pts = [(bx0 + w * 0.12, by0 + bh * 0.38), (bx0 + w * 0.35, by0 + bh * 0.5),
           (bx0 + w * 0.55, by0 + bh * 0.45), (bx0 + w * 0.88, by0 + bh * 0.88)]
    d.line(pts, fill=(255, 59, 48, 255), width=max(1, int(h * 0.01)))


# ── helpers ─────────────────────────────────────────────────────────────────────

def _keyed(ph, keytimes, values):
    if ph <= keytimes[0]:
        return values[0]
    if ph >= keytimes[-1]:
        return values[-1]
    for i in range(1, len(keytimes)):
        if ph <= keytimes[i]:
            span = keytimes[i] - keytimes[i - 1]
            f = (ph - keytimes[i - 1]) / span if span else 0
            return values[i - 1] + (values[i] - values[i - 1]) * f
    return values[-1]


def _rot_rect(canvas, cx, cy, w, h, angle_deg, color):
    rad = math.radians(angle_deg)
    ca, sa = math.cos(rad), math.sin(rad)
    corners = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    pts = [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in corners]
    ImageDraw.Draw(canvas).polygon(pts, fill=color)


def _rot_filled_rect(d, cx, cy, w, h, angle_deg, color):
    rad = math.radians(angle_deg)
    ca, sa = math.cos(rad), math.sin(rad)
    corners = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    pts = [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in corners]
    d.polygon(pts, fill=color)
