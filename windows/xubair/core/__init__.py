"""FreeloaderCore — pure behavior logic, ported from the Swift package.

No GUI here: the app drives CharacterBrain.tick() each frame and reads the BrainFrame.
"""
from .brain import (BehaviorConfig, BrainFrame, CharacterBrain, FocusPhase, RopeState,
                    WorldInput)
from .dialogue import DialogueDirector, LineCategory, lines_for
from .motion import RigPose, sample as sample_motion
from .rng import SeededRandom, weighted_pick
from .stats import ALL_ACHIEVEMENTS, Achievement, Stats
from .types import (Accessory, BodyView, Bounds, CharacterState, Effect, FaceExpression,
                    Facing, Mood, MotionKind, Point, Pose, SoundCue, standing_pose)
from .world import (ClipboardContentType, Environment, FileKind, Item, ItemKind,
                    MemoryPressure, Needs, Platform)
from . import script
from . import rare_events

__all__ = [
    "BehaviorConfig", "BrainFrame", "CharacterBrain", "FocusPhase", "RopeState", "WorldInput",
    "DialogueDirector", "LineCategory", "lines_for",
    "RigPose", "sample_motion",
    "SeededRandom", "weighted_pick",
    "ALL_ACHIEVEMENTS", "Achievement", "Stats",
    "Accessory", "BodyView", "Bounds", "CharacterState", "Effect", "FaceExpression",
    "Facing", "Mood", "MotionKind", "Point", "Pose", "SoundCue", "standing_pose",
    "ClipboardContentType", "Environment", "FileKind", "Item", "ItemKind",
    "MemoryPressure", "Needs", "Platform",
    "script", "rare_events",
]
