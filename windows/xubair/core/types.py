"""Shared vocabulary between the behavior brain and the renderer.

A faithful Python port of FreeloaderCore/Types.swift.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, auto


class AutoName(str, Enum):
    """A str-backed enum whose value equals the member name (like a Swift String raw enum)."""

    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name


class BodyView(AutoName):
    front = auto()
    threeQuarter = auto()
    side = auto()
    back = auto()


class FaceExpression(AutoName):
    neutral = auto()
    bored = auto()
    shocked = auto()
    annoyed = auto()
    smug = auto()
    sleepy = auto()
    worried = auto()


class Facing(Enum):
    left = -1
    right = 1

    @property
    def sign(self) -> float:
        return 1.0 if self is Facing.right else -1.0

    @property
    def opposite(self) -> "Facing":
        return Facing.left if self is Facing.right else Facing.right


class CharacterState(AutoName):
    idle = auto()
    walking = auto()
    bored = auto()
    cursorDetected = auto()
    panic = auto()
    glassWall = auto()
    sleep = auto()
    work = auto()
    celebration = auto()
    dragged = auto()
    falling = auto()
    reacting = auto()
    fourthWall = auto()
    thrown = auto()
    eating = auto()
    playing = auto()
    focus = auto()
    climbing = auto()
    carrying = auto()
    reminding = auto()


class MotionKind(AutoName):
    still = auto()
    breathe = auto()
    lookAround = auto()
    shiftWeight = auto()
    pocketCheck = auto()
    yawn = auto()
    stretch = auto()
    sitDown = auto()
    sit = auto()
    standUp = auto()
    stare = auto()
    walk = auto()
    run = auto()
    stumble = auto()
    hide = auto()
    pant = auto()
    bonk = auto()
    pressGlass = auto()
    push = auto()
    knock = auto()
    inspect = auto()
    lookUp = auto()
    lieDown = auto()
    sleeping = auto()
    getUp = auto()
    faint = auto()
    typing = auto()
    celebrate = auto()
    victoryDance = auto()
    nod = auto()
    shrug = auto()
    spin = auto()
    wiggle = auto()
    dangle = auto()
    fall = auto()
    land = auto()
    flinch = auto()
    jump = auto()
    wakeJolt = auto()
    freeze = auto()
    lookAtCursor = auto()
    sizeCheck = auto()
    knockScreen = auto()
    tumble = auto()
    dizzy = auto()
    chomp = auto()
    kick = auto()
    patBelly = auto()
    peekLedge = auto()
    wave = auto()
    hyper = auto()
    holdItem = auto()
    climb = auto()
    ropeSwing = auto()
    throwRope = auto()
    tug = auto()
    mantle = auto()
    carry = auto()
    strain = auto()
    holdSign = auto()


class Effect(AutoName):
    zzz = auto()
    sweat = auto()
    sparkles = auto()
    confetti = auto()
    glassAhead = auto()
    keyboard = auto()
    exclaim = auto()
    question = auto()
    knockRipple = auto()
    meeting = auto()
    crumbs = auto()
    dizzyStars = auto()
    caffeine = auto()
    document = auto()
    carryLight = auto()
    carryMedium = auto()
    carryHeavy = auto()
    carryMassive = auto()
    sign = auto()
    carryItem = auto()


class Accessory(AutoName):
    sunglasses = auto()
    partyHat = auto()


class SoundCue(AutoName):
    pop = auto()
    thud = auto()
    squeak = auto()
    celebrate = auto()
    knock = auto()
    typing = auto()
    wake = auto()
    glass = auto()
    whoosh = auto()
    chomp = auto()
    bounce = auto()
    achievement = auto()
    slurp = auto()
    kick = auto()


class Mood(AutoName):
    grumpy = auto()
    smug = auto()
    sleepy = auto()
    dramatic = auto()
    chipper = auto()

    @property
    def display_name(self) -> str:
        return {
            Mood.grumpy: "Grumpy",
            Mood.smug: "Smug",
            Mood.sleepy: "Sleepy",
            Mood.dramatic: "Dramatic",
            Mood.chipper: "Suspiciously chipper",
        }[self]


@dataclass
class Pose:
    view: BodyView
    expression: FaceExpression
    motion: MotionKind

    def __hash__(self):
        return hash((self.view, self.expression, self.motion))


# Pose.standing equivalent — a function so each use is a fresh copy (Swift value semantics).
def standing_pose() -> Pose:
    return Pose(BodyView.front, FaceExpression.neutral, MotionKind.breathe)


@dataclass
class Point:
    x: float = 0.0
    y: float = 0.0

    def distance(self, other: "Point") -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    def copy(self) -> "Point":
        return Point(self.x, self.y)


@dataclass
class Bounds:
    """Rectangle the character's *feet* may occupy, in global screen points (y grows upward)."""

    minX: float
    maxX: float
    floorY: float
    maxY: float

    def __post_init__(self):
        self.maxY = max(self.floorY, self.maxY)

    @property
    def width(self) -> float:
        return self.maxX - self.minX

    def clamped(self, p: Point) -> Point:
        return Point(min(max(p.x, self.minX), self.maxX),
                     min(max(p.y, self.floorY), self.maxY))
