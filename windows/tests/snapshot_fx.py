"""Render character + effects + speech bubble combinations to a PNG for eyeballing."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw

from xubair.core.brain import BrainFrame
from xubair.core.types import (BodyView, CharacterState, Effect, FaceExpression, Facing,
                               Mood, MotionKind, Point, Pose)
from xubair.render import FrameRenderer
from xubair.render.sprites import SpriteLibrary


def frame(view, expr, motion, facing, effects=None, speech=None):
    return BrainFrame(position=Point(0, 0), state=CharacterState.idle, activityID="x",
                      pose=Pose(view, expr, motion), facing=facing, stepTime=0.5, stepDuration=1.2,
                      gaitPhase=0.6, isWalking=False, effects=set(effects or []), speech=speech,
                      sounds=[], mood=Mood.grumpy)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/xubair_fx.png"
    lib = SpriteLibrary(SpriteLibrary.default_directory())
    r = FrameRenderer(lib)
    r.sign_text = "Call mom!"
    h = 130.0

    cases = [
        (frame(BodyView.front, FaceExpression.sleepy, MotionKind.sleeping, Facing.right, [Effect.zzz]), "zzz", 0.4),
        (frame(BodyView.front, FaceExpression.worried, MotionKind.pant, Facing.right, [Effect.sweat]), "sweat", 0.3),
        (frame(BodyView.front, FaceExpression.smug, MotionKind.celebrate, Facing.right, [Effect.confetti]),
         "confetti", 0.5),
        (frame(BodyView.side, FaceExpression.worried, MotionKind.pressGlass, Facing.right, [Effect.glassAhead]),
         "glass", 0.3),
        (frame(BodyView.front, FaceExpression.annoyed, MotionKind.typing, Facing.right, [Effect.keyboard]),
         "keyboard", 0.2),
        (frame(BodyView.front, FaceExpression.shocked, MotionKind.jump, Facing.right, [Effect.exclaim]),
         "exclaim", 0.15),
        (frame(BodyView.front, FaceExpression.worried, MotionKind.dizzy, Facing.right, [Effect.dizzyStars]),
         "dizzyStars", 0.4),
        (frame(BodyView.front, FaceExpression.shocked, MotionKind.hyper, Facing.right, [Effect.caffeine]),
         "caffeine", 0.3),
        (frame(BodyView.front, FaceExpression.smug, MotionKind.holdItem, Facing.right, [Effect.document]),
         "document", 0.4),
        (frame(BodyView.side, FaceExpression.worried, MotionKind.carry, Facing.right, [Effect.carryMassive]),
         "crate", 0.4),
        (frame(BodyView.front, FaceExpression.annoyed, MotionKind.holdSign, Facing.right, [Effect.sign]),
         "sign", 0.4),
        (frame(BodyView.front, FaceExpression.neutral, MotionKind.breathe, Facing.right, None,
               "I don't pay rent. I have no regrets."), "bubble", 0.4),
    ]

    cell_w, cell_h = 210, 260
    cols = 4
    rows = (len(cases) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell_w, rows * cell_h), (34, 34, 40, 255))
    draw = ImageDraw.Draw(sheet)
    for i, (f, label, t) in enumerate(cases):
        res = r.render(f, h, now=t)
        cx = (i % cols) * cell_w
        cy = (i // cols) * cell_h
        px = int(cx + cell_w / 2 - res.feet[0])
        py = int(cy + cell_h - 34 - res.feet[1])
        sheet.alpha_composite(res.image, (px, py))
        draw.line([cx, cy + cell_h - 30, cx + cell_w, cy + cell_h - 30], fill=(80, 80, 90, 255))
        draw.text((cx + 6, cy + cell_h - 22), label, fill=(210, 210, 220, 255))
    sheet.convert("RGB").save(out)
    print("wrote", out, sheet.size)


if __name__ == "__main__":
    main()
