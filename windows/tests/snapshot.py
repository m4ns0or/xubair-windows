"""Render a contact sheet of poses to a PNG so the compositor can be eyeballed without a GUI.
Usage: python tests/snapshot.py [out.png]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw

from xubair.core.brain import BrainFrame
from xubair.core.motion import sample as sample_motion
from xubair.core.types import (BodyView, CharacterState, Effect, FaceExpression, Facing,
                               Mood, MotionKind, Point, Pose)
from xubair.render.compositor import compose
from xubair.render.sprites import SpriteLibrary


def make_frame(view, expr, motion, facing):
    f = BrainFrame(position=Point(0, 0), state=CharacterState.idle, activityID="x",
                   pose=Pose(view, expr, motion), facing=facing, stepTime=0.4, stepDuration=1.0,
                   gaitPhase=0.6, isWalking=False, effects=set(), speech=None, sounds=[], mood=Mood.grumpy)
    return f


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/xubair_poses.png"
    directory = SpriteLibrary.default_directory()
    assert directory, "sprites not found"
    lib = SpriteLibrary(directory)
    height = 130.0

    poses = [
        (BodyView.front, FaceExpression.neutral, MotionKind.breathe, Facing.right, "front/neutral"),
        (BodyView.front, FaceExpression.smug, MotionKind.celebrate, Facing.right, "smug/celebrate"),
        (BodyView.front, FaceExpression.sleepy, MotionKind.yawn, Facing.right, "sleepy/yawn"),
        (BodyView.front, FaceExpression.shocked, MotionKind.jump, Facing.right, "shocked/jump"),
        (BodyView.front, FaceExpression.annoyed, MotionKind.typing, Facing.right, "annoyed/typing"),
        (BodyView.front, FaceExpression.bored, MotionKind.sit, Facing.right, "bored/sit"),
        (BodyView.side, FaceExpression.neutral, MotionKind.walk, Facing.right, "side/walk R"),
        (BodyView.side, FaceExpression.neutral, MotionKind.walk, Facing.left, "side/walk L"),
        (BodyView.side, FaceExpression.worried, MotionKind.pressGlass, Facing.right, "side/pressGlass"),
        (BodyView.threeQuarter, FaceExpression.neutral, MotionKind.lookAround, Facing.left, "3q/lookAround"),
        (BodyView.front, FaceExpression.worried, MotionKind.dizzy, Facing.right, "worried/dizzy"),
        (BodyView.front, FaceExpression.smug, MotionKind.victoryDance, Facing.right, "smug/victoryDance"),
        (BodyView.front, FaceExpression.sleepy, MotionKind.sleeping, Facing.right, "sleeping"),
        (BodyView.back, FaceExpression.neutral, MotionKind.climb, Facing.right, "back/climb"),
        (BodyView.front, FaceExpression.smug, MotionKind.breathe, Facing.right, "sunglasses"),
        (BodyView.front, FaceExpression.smug, MotionKind.breathe, Facing.right, "party hat"),
    ]

    cell_w, cell_h = 180, 220
    cols = 4
    rows = (len(poses) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell_w, rows * cell_h), (34, 34, 40, 255))
    draw = ImageDraw.Draw(sheet)

    for i, (view, expr, motion, facing, label) in enumerate(poses):
        frame = make_frame(view, expr, motion, facing)
        if label == "sunglasses":
            from xubair.core.types import Accessory
            frame.accessories = {Accessory.sunglasses}
        if label == "party hat":
            from xubair.core.types import Accessory
            frame.accessories = {Accessory.partyHat}
        rig = sample_motion(motion, t=0.45, duration=1.0, gait=0.6)
        comp = compose(frame, rig, lib, height)
        cx = (i % cols) * cell_w
        cy = (i // cols) * cell_h
        # place feet near bottom of cell
        img = comp.image
        px = int(cx + cell_w / 2 - comp.feet[0])
        py = int(cy + cell_h - 30 - comp.feet[1])
        sheet.alpha_composite(img, (px, py))
        draw.line([cx, cy + cell_h - 30, cx + cell_w, cy + cell_h - 30], fill=(80, 80, 90, 255))
        draw.text((cx + 6, cy + cell_h - 22), label, fill=(210, 210, 220, 255))

    sheet.convert("RGB").save(out)
    print("wrote", out, sheet.size)


if __name__ == "__main__":
    main()
