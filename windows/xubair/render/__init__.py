"""Rendering pipeline: ties the rig compositor, effects and speech bubble into one frame image."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from PIL import Image

from ..core.brain import BrainFrame
from ..core.motion import sample as sample_motion
from ..core.types import CharacterState, MotionKind
from . import bubble as bubble_mod
from . import effects as effects_mod
from .compositor import Composited, compose
from .sprites import SpriteLibrary


@dataclass
class RenderResult:
    image: Image.Image                      # full RGBA frame (character + effects + bubble)
    feet: Tuple[float, float]               # feet point within image (px, top-down)
    hit_rect: Tuple[float, float, float, float]  # body rect within image for click hit-testing


class FrameRenderer:
    def __init__(self, library: SpriteLibrary, reduce_effects: bool = False):
        self.library = library
        self.reduce_effects = reduce_effects
        self.sign_text = ""
        self._bubble_text: Optional[str] = None
        self._bubble_until = 0.0
        self._blink_until = 0.0
        self._next_blink = time.monotonic() + random.uniform(3, 7)
        self._carried_emoji = "⚽️"

    def say(self, text: str, now: float):
        self._bubble_text = text
        self._bubble_until = now + bubble_mod.visible_seconds(text)

    def clear_bubble(self):
        self._bubble_text = None

    @property
    def bubble_text(self) -> Optional[str]:
        return self._bubble_text

    def render(self, frame: BrainFrame, height: float, now: Optional[float] = None) -> RenderResult:
        if now is None:
            now = time.monotonic()
        if frame.speech:
            self.say(frame.speech, now)
        if frame.carriedEmoji:
            self._carried_emoji = frame.carriedEmoji

        # lazy blink
        blink = False
        if now >= self._blink_until and now >= self._next_blink:
            self._blink_until = now + 0.14
            self._next_blink = now + random.uniform(3, 7)
        if now < self._blink_until and frame.state not in (CharacterState.sleep,):
            blink = True

        rig = sample_motion(frame.pose.motion,
                            t=frame.stepTime, duration=max(0.001, frame.stepDuration),
                            gait=frame.gaitPhase, intensity=0.6 if self.reduce_effects else 1.0)

        comp: Composited = compose(frame, rig, self.library, height, blink=blink)

        # Effects drawn onto the character canvas (feet-relative).
        effects_mod.draw_effects(comp.image, comp.feet, frame.effects, frame.facing, height,
                                 comp.body_top_yup, frame.pose, now, reduce=self.reduce_effects,
                                 sign_text=self.sign_text, carried_emoji=self._carried_emoji)

        img = comp.image
        feet = comp.feet
        hit_rect = comp.body_rect

        # Speech bubble above the head.
        if self._bubble_text and now < self._bubble_until:
            head_top_y = comp.body_rect[1]
            head_mid_x = (comp.body_rect[0] + comp.body_rect[2]) / 2
            bub, tip = bubble_mod.render_bubble(self._bubble_text, scale=2.0)
            bw = bub.width // 2
            bh = bub.height // 2
            bub = bub.resize((bw, bh), Image.LANCZOS)
            tipx = tip[0] / 2
            gap = int(height * 0.04)
            # Desired: tail tip just above the head, horizontally over head_mid_x.
            desired_tip_x = head_mid_x
            desired_tip_y = head_top_y - gap
            paste_x = desired_tip_x - tipx
            paste_y = desired_tip_y - (bh - 1)
            img, feet, hit_rect = _expand_and_paste(img, feet, hit_rect, bub, paste_x, paste_y)
        elif self._bubble_text and now >= self._bubble_until:
            self._bubble_text = None

        return RenderResult(image=img, feet=feet, hit_rect=hit_rect)


def _expand_and_paste(base, feet, hit_rect, overlay, px, py):
    """Paste `overlay` at (px, py) which may be negative/outside; grow the canvas as needed
    and shift feet/hit_rect accordingly."""
    min_x = min(0, int(px))
    min_y = min(0, int(py))
    max_x = max(base.width, int(px) + overlay.width)
    max_y = max(base.height, int(py) + overlay.height)
    new_w = max_x - min_x
    new_h = max_y - min_y
    shift_x = -min_x
    shift_y = -min_y
    if new_w == base.width and new_h == base.height and shift_x == 0 and shift_y == 0:
        base.alpha_composite(overlay, (int(px), int(py)))
        return base, feet, hit_rect
    out = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
    out.alpha_composite(base, (shift_x, shift_y))
    out.alpha_composite(overlay, (int(px) + shift_x, int(py) + shift_y))
    feet = (feet[0] + shift_x, feet[1] + shift_y)
    hit_rect = (hit_rect[0] + shift_x, hit_rect[1] + shift_y,
                hit_rect[2] + shift_x, hit_rect[3] + shift_y)
    return out, feet, hit_rect
