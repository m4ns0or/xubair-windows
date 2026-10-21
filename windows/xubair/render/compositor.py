"""Composes a BrainFrame + RigPose into a single RGBA character image — a Pillow port
of the CALayer rig in CharacterView.swift (legs -> torso -> head, shadow, props).

Everything is computed in the Swift convention (y UP, rotations CCW, values for a
right-facing character) and converted to Pillow's top-down pixels at the final blit.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

from PIL import Image, ImageDraw

from ..core.brain import BrainFrame
from ..core.motion import RigPose
from ..core.types import Accessory, BodyView, CharacterState, FaceExpression, Facing, MotionKind
from .sprites import Head, SpriteLibrary, ViewSet

RESAMPLE = Image.BICUBIC


@dataclass
class Composited:
    image: Image.Image           # RGBA
    feet: Tuple[float, float]    # feet point within image (px, top-down)
    body_rect: Tuple[float, float, float, float]  # (minX, minY, maxX, maxY) px top-down
    body_top_yup: float          # height of body above feet, in px (for effects/bubble)


def _center_on(img: Image.Image, ax: float, ay: float) -> Tuple[Image.Image, float, float]:
    """Pad `img` so the pixel (ax, ay) sits at the exact centre; return (padded, cx, cy)."""
    w, h = img.width, img.height
    half_w = max(ax, w - ax)
    half_h = max(ay, h - ay)
    new_w = int(math.ceil(2 * half_w))
    new_h = int(math.ceil(2 * half_h))
    cx, cy = new_w / 2.0, new_h / 2.0
    out = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
    out.alpha_composite(img, (int(round(cx - ax)), int(round(cy - ay))))
    return out, cx, cy


def _rotate_about(img: Image.Image, angle_deg: float, ax: float, ay: float):
    """Rotate `img` CCW about its pixel (ax, ay). Returns (rotated, cx, cy) with the
    pivot at the rotated image's centre (cx, cy)."""
    padded, cx, cy = _center_on(img, ax, ay)
    if abs(angle_deg) < 0.01:
        return padded, cx, cy
    rot = padded.rotate(angle_deg, resample=RESAMPLE, expand=False, center=(cx, cy))
    return rot, cx, cy


def _paste_anchor(dst: Image.Image, img: Image.Image, cx: float, cy: float, dx: float, dy: float):
    """Paste `img` so its pivot (cx, cy) lands at dst pixel (dx, dy)."""
    dst.alpha_composite(img, (int(round(dx - cx)), int(round(dy - cy))))


def compose(frame: BrainFrame, rig: RigPose, library: SpriteLibrary, height: float,
            blink: bool = False) -> Composited:
    h = height
    sign = frame.facing.sign
    flipped = SpriteLibrary.needs_flip(frame.pose.view, frame.facing)
    vs: ViewSet = library.set(frame.pose.view, flipped)
    k = h / vs.body_height

    legs_w = vs.legs_size[0] * k
    legs_h = vs.legs_size[1] * k
    torso_w = vs.torso_size[0] * k
    torso_h = vs.torso_size[1] * k
    overlap = vs.overlap * k
    legs_scale = max(0.02, rig.legsScaleY)

    # ── torso space (y-up, origin bottom-left of the torso piece) ────────────
    torso_img = vs.torso.resize((max(1, int(round(torso_w))), max(1, int(round(torso_h)))), RESAMPLE)
    torso_canvas = Image.new("RGBA", torso_img.size, (0, 0, 0, 0))
    torso_canvas.alpha_composite(torso_img, (0, 0))

    expression = FaceExpression.bored if blink else frame.pose.expression
    head = vs.head(expression)
    if head is not None:
        head_w = head.size[0] * k
        head_h = head.size[1] * k
        head_img = head.image.resize((max(1, int(round(head_w))), max(1, int(round(head_h)))), RESAMPLE)
        # head anchor in head-image px (y-down for Pillow): anchor.y is y-up unit.
        hax = head.anchor[0] * head_img.width
        hay = (1 - head.anchor[1]) * head_img.height
        rot_head, hcx, hcy = _rotate_about(head_img, math.degrees(rig.headRotation * sign), hax, hay)
        # head position in torso space (y-up): pivot*k + head offsets
        pos_x = head.pivot[0] * k + rig.headX * h * sign
        pos_y = head.pivot[1] * k + rig.headY * h
        # torso canvas is top-down with origin at torso TOP; y-up 0 == torso bottom row.
        dst_x = pos_x
        dst_y = torso_img.height - pos_y
        _paste_anchor(torso_canvas, rot_head, hcx, hcy, dst_x, dst_y)
        _draw_props(torso_canvas, frame, head, head_img.width, head_img.height, dst_x, dst_y, k, h)

    # Rotate the whole torso (with head) about the waist anchor (0.5 width, overlap up from bottom).
    anchor_x = torso_canvas.width / 2.0
    anchor_y = torso_canvas.height - overlap
    torso_rot, tcx, tcy = _rotate_about(torso_canvas, math.degrees(rig.torsoRotation * sign), anchor_x, anchor_y)

    # ── body space (y-up, feet at origin, centred x) ─────────────────────────
    legs_scaled = vs.legs.resize((max(1, int(round(legs_w))), max(1, int(round(legs_h * legs_scale)))), RESAMPLE)
    legs_top_yup = legs_h * legs_scale
    torso_anchor_yup = legs_top_yup + rig.torsoY * h  # where the torso waist anchor sits

    # Body-space canvas big enough for everything.
    pad = int(h * 0.9)
    bw = int(max(legs_scaled.width, torso_rot.width) + 2 * pad)
    bh = int(legs_top_yup + torso_rot.height + 2 * pad)
    body = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    feet_x = bw / 2.0
    feet_y = bh - pad  # y-up 0 is here

    def place_yup(img, cx, cy, xup, yup):
        _paste_anchor(body, img, cx, cy, feet_x + xup, feet_y - yup)

    # legs: bottom-centre at feet (y-up 0)
    place_yup(legs_scaled, legs_scaled.width / 2.0, legs_scaled.height, 0, legs_top_yup)
    # torso: its waist anchor at (centre, torso_anchor_yup)
    place_yup(torso_rot, tcx, tcy, 0, torso_anchor_yup)

    # ── whole-body transform: scale, rotate about feet, offset ───────────────
    sx = max(0.05, rig.scaleX)
    sy = max(0.05, rig.scaleY)
    if abs(sx - 1) > 0.001 or abs(sy - 1) > 0.001:
        new_w = max(1, int(round(body.width * sx)))
        new_h = max(1, int(round(body.height * sy)))
        # feet position scales about itself: x about centre, y about bottom offset
        feet_x = (feet_x / body.width) * new_w
        feet_y = new_h - (body.height - feet_y) * sy
        body = body.resize((new_w, new_h), RESAMPLE)

    angle = math.degrees(rig.bodyRotation * sign)
    if abs(angle) > 0.01:
        body, feet_x, feet_y = _rotate_about(body, angle, feet_x, feet_y)

    # ── assemble final canvas with shadow under the feet ─────────────────────
    off_x = rig.bodyX * h * sign
    off_y = rig.bodyY * h
    # Final canvas: body plus headroom for shadow/margins.
    margin = int(h * 0.3)
    cw = body.width + 2 * margin
    ch = body.height + 2 * margin
    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    feet_cx = margin + feet_x
    feet_cy = margin + feet_y - off_y  # off_y is y-up, so subtract

    # Contact shadow (ellipse) under the feet.
    shadow_alpha = _shadow_alpha(frame)
    if shadow_alpha > 0:
        sw = h * 0.42 * rig.shadowScale
        sh = h * 0.065 * min(1.2, rig.shadowScale)
        sx0 = feet_cx + off_x - sw / 2
        sy0 = (margin + feet_y - 2) - sh / 2
        sdraw = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(sdraw).ellipse([sx0, sy0, sx0 + sw, sy0 + sh],
                                      fill=(0, 0, 0, int(0.28 * 255 * shadow_alpha)))
        canvas.alpha_composite(sdraw)

    canvas.alpha_composite(body, (int(round(margin + off_x)), int(round(margin - off_y))))

    # Body bounding rect (for bubble / effects anchoring).
    bbox = body.getbbox()
    if bbox:
        minx = margin + off_x + bbox[0]
        miny = margin - off_y + bbox[1]
        maxx = margin + off_x + bbox[2]
        maxy = margin - off_y + bbox[3]
    else:
        minx, miny, maxx, maxy = feet_cx, feet_cy, feet_cx, feet_cy
    body_top_yup = (margin + feet_y) - miny
    return Composited(image=canvas, feet=(feet_cx + off_x, margin + feet_y),
                      body_rect=(minx, miny, maxx, maxy), body_top_yup=body_top_yup)


def _shadow_alpha(frame: BrainFrame) -> float:
    if frame.pose.motion is MotionKind.climb:
        return 0.0
    if frame.state in (CharacterState.dragged, CharacterState.thrown, CharacterState.falling):
        return 0.3
    return 1.0


def _draw_props(torso_canvas, frame, head: Head, head_w, head_h, dst_x, dst_y, k, h):
    """Sunglasses (front only) and party hat, drawn onto the head in torso space."""
    if not frame.accessories:
        return
    d = ImageDraw.Draw(torso_canvas)
    eyes_px = [(ex * head_w, (1 - ey) * head_h) for (ex, ey) in head.eyes]  # top-down within head img
    # head image was pasted with pivot (anchor) at (dst_x, dst_y); convert eye coords to torso space.
    ax_px = head.anchor[0] * head_w
    ay_px = (1 - head.anchor[1]) * head_h

    def to_canvas(px, py):
        return (dst_x + (px - ax_px), dst_y + (py - ay_px))

    if Accessory.sunglasses in frame.accessories and frame.pose.view is BodyView.front and len(eyes_px) == 2:
        e0 = to_canvas(*eyes_px[0])
        e1 = to_canvas(*eyes_px[1])
        eye_dist = math.hypot(e1[0] - e0[0], e1[1] - e0[1]) or head_w * 0.2
        lens_w = eye_dist * 0.95
        lens_h = eye_dist * 0.58
        for e in (e0, e1):
            d.rounded_rectangle([e[0] - lens_w / 2, e[1] - lens_h * 0.62,
                                 e[0] + lens_w / 2, e[1] - lens_h * 0.62 + lens_h],
                                radius=lens_h * 0.35, fill=(10, 10, 10, 245), outline=(0, 0, 0, 255))
        # bridge
        d.rectangle([min(e0[0], e1[0]) + lens_w / 2 - 1, (e0[1] + e1[1]) / 2 - lens_h * 0.02,
                     max(e0[0], e1[0]) - lens_w / 2 + 1, (e0[1] + e1[1]) / 2 + lens_h * 0.1],
                    fill=(10, 10, 10, 245))

    if Accessory.partyHat in frame.accessories:
        crown_x = head.crown[0] if frame.pose.view is BodyView.front else 0.5
        cx = dst_x + (crown_x * head_w - ax_px)
        cy = dst_y + ((1 - head.crown[1]) * head_h - ay_px)
        hat_w = head_w * 0.32
        hat_h = hat_w * 1.5
        # cone pointing up (towards smaller y)
        apex = (cx, cy - hat_h)
        d.polygon([(cx - hat_w / 2, cy), (cx + hat_w / 2, cy), apex], fill=(255, 92, 141, 255),
                  outline=(150, 25, 75, 255))
        pr = hat_w * 0.13
        d.ellipse([apex[0] - pr, apex[1] - pr, apex[0] + pr, apex[1] + pr], fill=(255, 255, 255, 255))
        for fx, fy in [(0.35, 0.3), (0.6, 0.5), (0.45, 0.72)]:
            dot = (cx - hat_w / 2 + hat_w * fx, cy - hat_h * (1 - fy))
            rr = hat_w * 0.07
            d.ellipse([dot[0] - rr, dot[1] - rr, dot[0] + rr, dot[1] + rr], fill=(255, 214, 10, 255))
