"""Activities as small data-driven scripts — port of Script.swift + ScriptExtras.swift.

Swift enums with associated values become small tagged dataclasses with factory helpers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional

from .dialogue import LineCategory, MEETING_PAIRS
from .rng import SeededRandom
from .types import (Accessory, BodyView, CharacterState, Effect, FaceExpression,
                    Facing, MotionKind, Pose, SoundCue, standing_pose)
from .world import FileKind, ItemKind

BV = BodyView
FE = FaceExpression
MK = MotionKind
E = Effect
S = SoundCue
LC = LineCategory


# ── Tagged "enum with payload" helpers ─────────────────────────────────────────

@dataclass
class WalkTarget:
    kind: str
    lo: float = 0.0
    hi: float = 0.0
    stop_short: float = 0.0
    value: float = 0.0


def wt_random_spot() -> WalkTarget: return WalkTarget("randomSpot")
def wt_offset(lo, hi) -> WalkTarget: return WalkTarget("offset", lo, hi)
def wt_away_from_cursor(lo, hi) -> WalkTarget: return WalkTarget("awayFromCursor", lo, hi)
def wt_toward_cursor(stop_short) -> WalkTarget: return WalkTarget("towardCursor", stop_short=stop_short)
def wt_nearest_edge() -> WalkTarget: return WalkTarget("nearestEdge")
def wt_through_nearest_edge() -> WalkTarget: return WalkTarget("throughNearestEdge")
def wt_away_from_edge(lo, hi) -> WalkTarget: return WalkTarget("awayFromEdge", lo, hi)
def wt_item(stop_short) -> WalkTarget: return WalkTarget("item", stop_short=stop_short)
def wt_x(value) -> WalkTarget: return WalkTarget("x", value=value)
def wt_trash_can() -> WalkTarget: return WalkTarget("trashCan")


class ClimbDirection(Enum):
    up = auto()
    down = auto()


@dataclass
class StepAction:
    kind: str
    accessory: Optional[Accessory] = None
    seconds: float = 0.0


def act_eat() -> StepAction: return StepAction("eatTargetItem")
def act_kick() -> StepAction: return StepAction("kickTargetItem")
def act_wear(accessory, seconds) -> StepAction: return StepAction("wear", accessory, seconds)
def act_jump_off() -> StepAction: return StepAction("jumpOff")
def act_throw_rope() -> StepAction: return StepAction("throwRope")
def act_attach_rope() -> StepAction: return StepAction("attachRopeAndStepOff")
def act_coil_rope() -> StepAction: return StepAction("coilRope")
def act_pick_up() -> StepAction: return StepAction("pickUpTarget")
def act_dump() -> StepAction: return StepAction("dumpCarried")


class FacingRule(Enum):
    left = auto()
    right = auto()
    flip = auto()
    towardCursor = auto()
    awayFromCursor = auto()
    towardNearestEdge = auto()
    awayFromNearestEdge = auto()
    random = auto()


@dataclass
class LineRequest:
    kind: str  # 'maybe' | 'always' | 'text'
    category: Optional[LineCategory] = None
    chance: float = 1.0
    text: Optional[str] = None


def maybe(category, chance) -> LineRequest: return LineRequest("maybe", category, chance)
def always(category) -> LineRequest: return LineRequest("always", category)
def text_line(s) -> LineRequest: return LineRequest("text", text=s)


@dataclass
class Step:
    pose: Optional[Pose] = None
    duration: tuple = (1.0, 1.0)
    walk: Optional[WalkTarget] = None
    speed: float = 0.55
    backwards: bool = False
    facing: Optional[FacingRule] = None
    line: Optional[LineRequest] = None
    sound: Optional[SoundCue] = None
    effects: List[Effect] = field(default_factory=list)
    nudge: float = 0.0
    action: Optional[StepAction] = None
    climb: Optional[ClimbDirection] = None

    @staticmethod
    def hold(pose, duration, facing=None, line=None, sound=None, effects=None, nudge=0.0, action=None) -> "Step":
        return Step(pose=pose, duration=duration, facing=facing, line=line, sound=sound,
                    effects=list(effects or []), nudge=nudge, action=action)

    @staticmethod
    def walk_to(target, pose, speed=0.55, backwards=False, line=None, sound=None, effects=None) -> "Step":
        return Step(pose=pose, duration=(0.0, 0.0), walk=target, speed=speed, backwards=backwards,
                    line=line, sound=sound, effects=list(effects or []))

    @staticmethod
    def climb_step(direction: ClimbDirection, speed: float) -> "Step":
        return Step(pose=Pose(BV.back, FE.neutral, MK.climb), duration=(0.0, 0.0), speed=speed, climb=direction)


@dataclass
class Activity:
    id: str
    state: CharacterState
    priority: int
    steps: List[Step]


def _activity(id, state, steps, priority=0) -> Activity:
    return Activity(id, state, priority, steps)


class Priority:
    ambient = 0
    attention = 1
    rare = 2
    urgent = 3
    direct = 4


def _standing() -> Pose:
    return standing_pose()


# ── ActivityLibrary: Idle ───────────────────────────────────────────────────────

def idle_stand():
    return _activity("idle.stand", CharacterState.idle,
                     [Step.hold(_standing(), (3, 6), line=maybe(LC.idle, 0.15))])


def idle_look_around():
    return _activity("idle.lookAround", CharacterState.idle, [
        Step.hold(_standing(), (0.6, 1.0)),
        Step.hold(Pose(BV.threeQuarter, FE.neutral, MK.lookAround), (1.2, 1.8), facing=FacingRule.left),
        Step.hold(Pose(BV.threeQuarter, FE.neutral, MK.lookAround), (1.2, 1.8), facing=FacingRule.right),
        Step.hold(_standing(), (0.8, 1.4)),
    ])


def idle_shift_weight():
    return _activity("idle.shiftWeight", CharacterState.idle,
                     [Step.hold(Pose(BV.front, FE.neutral, MK.shiftWeight), (3, 5))])


def idle_pockets():
    return _activity("idle.pockets", CharacterState.idle, [
        Step.hold(Pose(BV.front, FE.bored, MK.pocketCheck), (2.4, 2.4), line=maybe(LC.pockets, 0.6)),
        Step.hold(Pose(BV.front, FE.annoyed, MK.breathe), (1.0, 1.6)),
    ])


def wander():
    return _activity("idle.wander", CharacterState.walking, [
        Step.walk_to(wt_random_spot(), Pose(BV.side, FE.neutral, MK.walk)),
        Step.hold(_standing(), (0.8, 2.0)),
    ])


def try_to_leave():
    return _activity("idle.tryToLeave", CharacterState.walking, [
        Step.walk_to(wt_through_nearest_edge(), Pose(BV.side, FE.neutral, MK.walk), speed=0.6),
    ])


# ── Bored ─────────────────────────────────────────────────────────────────────

def yawn():
    return _activity("bored.yawn", CharacterState.bored, [
        Step.hold(Pose(BV.front, FE.sleepy, MK.yawn), (2.2, 2.2), line=maybe(LC.bored, 0.4)),
        Step.hold(Pose(BV.front, FE.bored, MK.breathe), (1, 2)),
    ])


def stretch():
    return _activity("bored.stretch", CharacterState.bored, [
        Step.hold(Pose(BV.front, FE.sleepy, MK.stretch), (2.4, 2.4)),
        Step.hold(Pose(BV.front, FE.bored, MK.breathe), (1, 1.5)),
    ])


def sit_down():
    return _activity("bored.sit", CharacterState.bored, [
        Step.hold(Pose(BV.front, FE.bored, MK.sitDown), (0.7, 0.7)),
        Step.hold(Pose(BV.front, FE.bored, MK.sit), (5, 10), line=maybe(LC.bored, 0.35)),
        Step.hold(Pose(BV.front, FE.annoyed, MK.standUp), (0.7, 0.7)),
    ])


def stare_at_user():
    return _activity("bored.stare", CharacterState.bored, [
        Step.hold(Pose(BV.front, FE.bored, MK.stare), (3, 4.5), line=maybe(LC.stare, 0.8)),
        Step.hold(_standing(), (0.8, 1.2)),
    ])


# ── Work & celebration ──────────────────────────────────────────────────────────

def work():
    return _activity("work", CharacterState.work, [
        Step.hold(Pose(BV.front, FE.annoyed, MK.typing), (3, 5), line=maybe(LC.work, 0.7), sound=S.typing,
                  effects=[E.keyboard]),
        Step.hold(Pose(BV.front, FE.shocked, MK.typing), (1.5, 2.5), sound=S.typing, effects=[E.keyboard]),
        Step.hold(Pose(BV.front, FE.smug, MK.celebrate), (2, 2), line=maybe(LC.celebrate, 0.9), sound=S.celebrate,
                  effects=[E.sparkles]),
        Step.hold(_standing(), (0.8, 1.2)),
    ])


def celebration():
    return _activity("celebration", CharacterState.celebration, [
        Step.hold(Pose(BV.front, FE.smug, MK.victoryDance), (3, 3.5), line=maybe(LC.celebrate, 0.9),
                  sound=S.celebrate, effects=[E.confetti]),
        Step.hold(Pose(BV.front, FE.smug, MK.breathe), (1, 1.5)),
    ])


# ── Sleep ─────────────────────────────────────────────────────────────────────

def sleep():
    return _activity("sleep", CharacterState.sleep, [
        Step.hold(Pose(BV.front, FE.sleepy, MK.yawn), (2, 2)),
        Step.hold(Pose(BV.front, FE.sleepy, MK.lieDown), (1.2, 1.2)),
        Step.hold(Pose(BV.front, FE.sleepy, MK.sleeping), (45, 110), effects=[E.zzz]),
        Step.hold(Pose(BV.front, FE.bored, MK.getUp), (1.2, 1.2)),
        Step.hold(Pose(BV.front, FE.bored, MK.breathe), (1, 2), line=maybe(LC.sleepWake, 0.6)),
    ], priority=Priority.urgent)


# ── Cursor ────────────────────────────────────────────────────────────────────

def notice_cursor():
    return _activity("cursor.notice", CharacterState.cursorDetected, [
        Step.hold(Pose(BV.threeQuarter, FE.annoyed, MK.lookAtCursor), (1.6, 2.6), facing=FacingRule.towardCursor,
                  line=maybe(LC.cursor, 0.45)),
        Step.hold(_standing(), (0.4, 0.8)),
    ], priority=Priority.attention)


def panic(rng: SeededRandom):
    variants = [
        _activity("panic.flee", CharacterState.panic, [
            Step.walk_to(wt_away_from_cursor(1.4, 2.2), Pose(BV.front, FE.shocked, MK.run), speed=1.9,
                         line=always(LC.panic), sound=S.squeak, effects=[E.sweat]),
            Step.hold(Pose(BV.front, FE.worried, MK.pant), (1.2, 1.6), effects=[E.sweat]),
            Step.hold(Pose(BV.front, FE.annoyed, MK.breathe), (0.6, 1), line=maybe(LC.panicRecover, 0.5)),
        ], priority=Priority.urgent),
        _activity("panic.stumble", CharacterState.panic, [
            Step.walk_to(wt_away_from_cursor(0.6, 1.0), Pose(BV.side, FE.shocked, MK.run), speed=1.8,
                         line=always(LC.panic), sound=S.squeak),
            Step.hold(Pose(BV.side, FE.shocked, MK.stumble), (0.9, 0.9), sound=S.thud),
            Step.hold(Pose(BV.front, FE.annoyed, MK.breathe), (1, 1.4), line=always(LC.panicRecover)),
        ], priority=Priority.urgent),
        _activity("panic.hide", CharacterState.panic, [
            Step.walk_to(wt_nearest_edge(), Pose(BV.front, FE.worried, MK.run), speed=2.0, line=always(LC.panic),
                         sound=S.squeak),
            Step.hold(Pose(BV.side, FE.worried, MK.hide), (2.5, 3.5), facing=FacingRule.towardNearestEdge,
                      effects=[E.sweat]),
            Step.hold(Pose(BV.threeQuarter, FE.worried, MK.lookAround), (1, 1.4),
                      facing=FacingRule.awayFromNearestEdge),
            Step.hold(_standing(), (0.5, 0.8)),
        ], priority=Priority.urgent),
    ]
    return rng.choice(variants)


# ── Glass wall ──────────────────────────────────────────────────────────────────

def glass_wall():
    return _activity("glassWall", CharacterState.glassWall, [
        Step.hold(Pose(BV.side, FE.shocked, MK.bonk), (0.45, 0.45), facing=FacingRule.towardNearestEdge, sound=S.thud,
                  effects=[E.glassAhead]),
        Step.hold(Pose(BV.side, FE.worried, MK.pressGlass), (2.4, 3.0), line=always(LC.glassWall), sound=S.glass,
                  effects=[E.glassAhead]),
        Step.hold(Pose(BV.front, FE.annoyed, MK.breathe), (1, 1.4)),
        Step.walk_to(wt_away_from_edge(0.5, 1.2), Pose(BV.side, FE.annoyed, MK.walk)),
    ], priority=Priority.urgent)


# ── Direct interaction ──────────────────────────────────────────────────────────

def click_reaction(repeated: bool, rng: SeededRandom):
    if repeated:
        return _activity("click.annoyed", CharacterState.reacting, [
            Step.hold(Pose(BV.front, FE.annoyed, MK.stare), (1.6, 1.6), line=always(LC.clickedAgain), sound=S.pop),
            Step.hold(_standing(), (0.4, 0.6)),
        ], priority=Priority.direct)
    variants = [
        _activity("click.flinch", CharacterState.reacting, [
            Step.hold(Pose(BV.front, FE.annoyed, MK.flinch), (0.6, 0.6), line=always(LC.clicked), sound=S.pop),
            Step.hold(Pose(BV.front, FE.annoyed, MK.breathe), (0.8, 1.2)),
        ], priority=Priority.direct),
        _activity("click.jump", CharacterState.reacting, [
            Step.hold(Pose(BV.front, FE.shocked, MK.jump), (0.7, 0.7), line=always(LC.clicked), sound=S.squeak,
                      effects=[E.exclaim]),
            Step.hold(Pose(BV.front, FE.worried, MK.breathe), (0.8, 1.2)),
        ], priority=Priority.direct),
        _activity("click.shrug", CharacterState.reacting, [
            Step.hold(Pose(BV.front, FE.bored, MK.shrug), (1.3, 1.3), line=always(LC.clicked), sound=S.pop),
            Step.hold(_standing(), (0.5, 0.8)),
        ], priority=Priority.direct),
        _activity("click.wiggle", CharacterState.reacting, [
            Step.hold(Pose(BV.front, FE.smug, MK.wiggle), (1.1, 1.1), line=always(LC.clicked), sound=S.pop),
            Step.hold(Pose(BV.front, FE.smug, MK.breathe), (0.6, 1)),
        ], priority=Priority.direct),
        _activity("click.spin", CharacterState.reacting, [
            Step.hold(Pose(BV.front, FE.worried, MK.spin), (0.9, 0.9), sound=S.whoosh, effects=[E.question]),
            Step.hold(Pose(BV.front, FE.annoyed, MK.breathe), (0.6, 1), line=always(LC.clicked)),
        ], priority=Priority.direct),
    ]
    return rng.choice(variants)


def dramatic_wake():
    return _activity("click.dramaticWake", CharacterState.reacting, [
        Step.hold(Pose(BV.front, FE.shocked, MK.wakeJolt), (1.0, 1.0), line=always(LC.dramaticWake), sound=S.wake,
                  effects=[E.exclaim]),
        Step.hold(Pose(BV.front, FE.worried, MK.pant), (1.0, 1.3)),
        Step.hold(Pose(BV.front, FE.annoyed, MK.breathe), (1, 1.5), line=always(LC.sleepWake)),
    ], priority=Priority.direct)


def landed(moved_far: bool):
    return _activity("drop.land", CharacterState.reacting, [
        Step.hold(Pose(BV.front, FE.annoyed, MK.land), (0.6, 0.6), sound=S.thud),
        Step.hold(Pose(BV.front, FE.annoyed, MK.breathe), (1.0, 1.4),
                  line=always(LC.moved if moved_far else LC.dropped)),
    ], priority=Priority.direct)


def notice_resize(bigger: bool):
    return _activity("fourthWall.resize", CharacterState.fourthWall, [
        Step.hold(Pose(BV.front, FE.smug if bigger else FE.shocked, MK.sizeCheck), (1.4, 1.4),
                  line=always(LC.resizedBigger if bigger else LC.resizedSmaller),
                  effects=[E.sparkles if bigger else E.question]),
        Step.hold(_standing(), (0.6, 1)),
    ], priority=Priority.direct)


def notice_screen_change():
    return _activity("fourthWall.screen", CharacterState.fourthWall, [
        Step.hold(Pose(BV.threeQuarter, FE.shocked, MK.lookAround), (1.2, 1.2), facing=FacingRule.random,
                  line=always(LC.screenChanged)),
        Step.hold(_standing(), (0.6, 1)),
    ], priority=Priority.direct)


# ── Physics (ScriptExtras) ──────────────────────────────────────────────────────

def airborne(thrown: bool):
    return _activity("thrown" if thrown else "falling",
                     CharacterState.thrown if thrown else CharacterState.falling, [
        Step.hold(Pose(BV.front, FE.shocked, MK.tumble if thrown else MK.fall), (600, 600),
                  effects=[E.sweat] if thrown else []),
    ], priority=9)


def dizzy():
    return _activity("dizzy", CharacterState.reacting, [
        Step.hold(Pose(BV.front, FE.worried, MK.dizzy), (2.6, 2.6), line=always(LC.dizzy), effects=[E.dizzyStars]),
        Step.hold(Pose(BV.front, FE.annoyed, MK.breathe), (0.8, 1.2)),
    ], priority=Priority.direct)


def landed_on_window():
    return _activity("perch.land", CharacterState.reacting, [
        Step.hold(Pose(BV.front, FE.shocked, MK.land), (0.6, 0.6), sound=S.thud),
        Step.hold(Pose(BV.threeQuarter, FE.smug, MK.lookAround), (1.8, 2.2), facing=FacingRule.random,
                  line=always(LC.landedOnWindow)),
        Step.hold(_standing(), (0.5, 0.8)),
    ], priority=Priority.direct)


def ride_window():
    return _activity("perch.ride", CharacterState.reacting, [
        Step.hold(Pose(BV.front, FE.shocked, MK.freeze), (1.2, 1.2), line=maybe(LC.rideWindow, 0.8)),
        Step.hold(_standing(), (0.4, 0.6)),
    ], priority=Priority.attention)


def ledge(facing: Facing, rng: SeededRandom):
    side = FacingRule.left if facing is Facing.left else FacingRule.right
    if rng.chance(0.35):
        return _activity("perch.jump", CharacterState.reacting, [
            Step.hold(Pose(BV.side, FE.worried, MK.peekLedge), (1.4, 1.6), facing=side, line=maybe(LC.ledge, 0.6)),
            Step.hold(Pose(BV.front, FE.smug, MK.stare), (0.6, 0.6), line=always(LC.jumpDown)),
            Step.hold(Pose(BV.side, FE.shocked, MK.jump), (0.25, 0.25), facing=side, action=act_jump_off()),
        ], priority=Priority.rare)
    return _activity("perch.ledge", CharacterState.reacting, [
        Step.hold(Pose(BV.side, FE.worried, MK.peekLedge), (1.6, 2.2), facing=side, line=maybe(LC.ledge, 0.8),
                  effects=[E.sweat]),
        Step.walk_to(wt_offset(0.5, 1.0), Pose(BV.side, FE.annoyed, MK.walk)),
    ], priority=Priority.rare)


# ── Items ─────────────────────────────────────────────────────────────────────

def go_eat(kind: ItemKind, from_sleep: bool):
    steps = []
    if from_sleep:
        steps.append(Step.hold(Pose(BV.front, FE.shocked, MK.wakeJolt), (0.9, 0.9), line=always(LC.smellFood),
                               effects=[E.exclaim]))
    steps.append(Step.walk_to(wt_item(0.16), Pose(BV.side, FE.smug, MK.run), speed=1.3,
                              line=None if from_sleep else maybe(LC.smellFood, 0.4)))
    line = LC.eatPizza if kind is ItemKind.pizza else LC.eatCoffee if kind is ItemKind.coffee else LC.eatDonut
    steps.append(Step.hold(Pose(BV.front, FE.smug, MK.chomp), (2.2, 2.2),
                           sound=S.slurp if kind is ItemKind.coffee else S.chomp,
                           effects=[E.crumbs], action=act_eat()))
    if kind is ItemKind.coffee:
        steps.append(Step.hold(Pose(BV.front, FE.shocked, MK.hyper), (1.6, 1.6), line=always(line),
                               effects=[E.caffeine]))
    else:
        steps.append(Step.hold(Pose(BV.front, FE.smug, MK.patBelly), (1.4, 1.6), line=always(line)))
    return _activity("item.eat", CharacterState.eating, steps, priority=Priority.rare)


def play_ball(first: bool):
    return _activity("item.ball", CharacterState.playing, [
        Step.walk_to(wt_item(0.13), Pose(BV.side, FE.smug, MK.run), speed=1.4,
                     line=always(LC.ballSpotted) if first else None),
        Step.hold(Pose(BV.side, FE.smug, MK.kick), (0.55, 0.55), line=maybe(LC.kickBall, 0.35), sound=S.kick,
                  action=act_kick()),
        Step.hold(Pose(BV.front, FE.smug, MK.breathe), (0.3, 0.6)),
    ], priority=Priority.rare)


def done_with_ball():
    return _activity("item.ballDone", CharacterState.playing, [
        Step.hold(Pose(BV.front, FE.bored, MK.pant), (1.4, 1.6), line=always(LC.boredOfBall)),
    ], priority=Priority.attention)


# ── Needs ─────────────────────────────────────────────────────────────────────

def hungry_complaint():
    return _activity("need.hungry", CharacterState.bored,
                     [Step.hold(Pose(BV.front, FE.bored, MK.patBelly), (2.4, 2.6), line=always(LC.hungry))])


def tired_complaint():
    return _activity("need.tired", CharacterState.bored,
                     [Step.hold(Pose(BV.front, FE.sleepy, MK.yawn), (2.2, 2.2), line=always(LC.tired))])


def hyper_zoom():
    return _activity("need.hyper", CharacterState.walking, [
        Step.walk_to(wt_random_spot(), Pose(BV.front, FE.shocked, MK.run), speed=2.6, line=maybe(LC.hyper, 0.6),
                     effects=[E.caffeine]),
        Step.walk_to(wt_random_spot(), Pose(BV.side, FE.smug, MK.run), speed=2.6, effects=[E.caffeine]),
        Step.hold(Pose(BV.front, FE.shocked, MK.hyper), (1.0, 1.4), effects=[E.caffeine]),
    ])


# ── Focus buddy ─────────────────────────────────────────────────────────────────

def quiet_work():
    return _activity("focus.work", CharacterState.focus, [
        Step.hold(Pose(BV.front, FE.annoyed, MK.typing), (6, 10), effects=[E.keyboard]),
        Step.hold(Pose(BV.front, FE.neutral, MK.breathe), (1.5, 3)),
    ])


def focus_start():
    return _activity("focus.start", CharacterState.focus, [
        Step.hold(Pose(BV.front, FE.smug, MK.nod), (1.8, 1.8), line=always(LC.focusStart)),
    ], priority=Priority.direct)


def focus_end():
    return _activity("focus.end", CharacterState.celebration, [
        Step.hold(Pose(BV.front, FE.smug, MK.victoryDance), (3.2, 3.2), line=always(LC.focusEnd), sound=S.celebrate,
                  effects=[E.confetti], action=act_wear(Accessory.partyHat, 10)),
        Step.hold(Pose(BV.front, FE.smug, MK.breathe), (1, 1.2)),
    ], priority=Priority.direct)


def break_start():
    return _activity("break.start", CharacterState.bored, [
        Step.hold(Pose(BV.front, FE.sleepy, MK.stretch), (2.4, 2.4), line=always(LC.breakStart)),
        Step.hold(Pose(BV.front, FE.bored, MK.sitDown), (0.7, 0.7)),
        Step.hold(Pose(BV.front, FE.bored, MK.sit), (12, 18)),
        Step.hold(Pose(BV.front, FE.annoyed, MK.standUp), (0.7, 0.7)),
    ], priority=Priority.direct)


def break_end():
    return _activity("break.end", CharacterState.reacting, [
        Step.hold(Pose(BV.front, FE.annoyed, MK.wave), (1.6, 1.6), line=always(LC.breakEnd)),
    ], priority=Priority.direct)


# ── Awareness ───────────────────────────────────────────────────────────────────

def away_sleep():
    activity = sleep()
    activity.id = "sleep.away"
    activity.steps[0].line = maybe(LC.awayAsleep, 0.7)
    activity.steps[2].duration = (600, 900)
    return activity


def welcome_back():
    return _activity("aware.welcomeBack", CharacterState.reacting, [
        Step.hold(Pose(BV.front, FE.shocked, MK.wakeJolt), (1.0, 1.0), line=always(LC.welcomeBack), sound=S.wake,
                  effects=[E.exclaim]),
        Step.hold(Pose(BV.front, FE.smug, MK.wave), (1.4, 1.4)),
        Step.hold(_standing(), (0.5, 0.8)),
    ], priority=Priority.direct)


def low_battery():
    return _activity("aware.battery", CharacterState.panic, [
        Step.hold(Pose(BV.front, FE.worried, MK.pant), (2.4, 2.4), line=always(LC.lowBattery), sound=S.squeak,
                  effects=[E.sweat]),
        Step.hold(Pose(BV.front, FE.worried, MK.breathe), (1, 1.4)),
    ], priority=Priority.urgent)


def say(category, id, motion=MK.stare, expression=FE.bored):
    return _activity(id, CharacterState.idle, [
        Step.hold(Pose(BV.front, expression, motion), (2.6, 3.2), line=always(category)),
        Step.hold(_standing(), (0.4, 0.6)),
    ], priority=Priority.attention)


def battery20():
    return say(LC.battery20, "aware.battery20", motion=MK.shrug, expression=FE.bored)


def battery10():
    return _activity("aware.battery10", CharacterState.panic, [
        Step.hold(Pose(BV.front, FE.shocked, MK.freeze), (0.5, 0.5), effects=[E.sweat]),
        Step.hold(Pose(BV.front, FE.shocked, MK.pant), (2.8, 3.2), line=always(LC.battery10), effects=[E.sweat]),
        Step.hold(_standing(), (0.5, 0.8)),
    ], priority=Priority.urgent)


def screen_time_nag(hours: int):
    category = LC.screenTime6h if hours >= 6 else LC.screenTime4h if hours >= 4 else LC.screenTime2h
    expr = FE.shocked if hours >= 6 else FE.worried if hours >= 4 else FE.bored
    return say(category, "aware.screenTime%dh" % hours, motion=MK.breathe, expression=expr)


def clipboard_react(ctype):
    from .world import ClipboardContentType as C
    category = {C.url: LC.clipboardUrl, C.stackTrace: LC.clipboardTrace,
                C.errorCode: LC.clipboardError}.get(ctype, LC.idle)
    return say(category, "aware.clipboard", motion=MK.stare)


def plugged_in():
    return _activity("aware.plugged", CharacterState.celebration, [
        Step.hold(Pose(BV.front, FE.smug, MK.celebrate), (1.8, 1.8), line=always(LC.pluggedIn), effects=[E.sparkles]),
    ], priority=Priority.rare)


def greeting(hour: int):
    if 5 <= hour < 12:
        category = LC.greetingMorning
    elif 12 <= hour < 17:
        category = LC.greetingAfternoon
    elif 17 <= hour < 22:
        category = LC.greetingEvening
    else:
        category = LC.greetingNight
    return say(category, "aware.greeting", motion=MK.wave, expression=FE.smug)


# ── Files ─────────────────────────────────────────────────────────────────────

def file_hover():
    return _activity("file.hover", CharacterState.cursorDetected, [
        Step.hold(Pose(BV.front, FE.shocked, MK.lookUp), (1.2, 1.2), line=always(LC.fileHover), effects=[E.question]),
        Step.hold(Pose(BV.front, FE.worried, MK.breathe), (6, 6), effects=[E.question]),
    ], priority=Priority.direct)


def inspect_file(kind: FileKind, kept: bool = False):
    activity = _activity("file.inspect", CharacterState.reacting, [
        Step.hold(Pose(BV.front, FE.shocked, MK.holdItem), (0.6, 0.6), sound=S.pop, effects=[E.document]),
        Step.hold(Pose(BV.front, FE.annoyed if kind is FileKind.code else FE.smug, MK.holdItem), (2.8, 3.2),
                  line=always(LC.for_file(kind)), effects=[E.document]),
        Step.hold(Pose(BV.front, FE.bored, MK.shrug), (1.0, 1.0)),
    ], priority=Priority.direct)
    if kept:
        activity.steps[2] = Step.hold(Pose(BV.front, FE.smug, MK.pocketCheck), (1.6, 1.6),
                                      line=always(LC.keepMany if kind is FileKind.many else LC.keepFile))
    return activity


# ── Accessories & achievements ──────────────────────────────────────────────────

def deal_with_it():
    return _activity("rare.dealWithIt", CharacterState.fourthWall, [
        Step.hold(Pose(BV.front, FE.smug, MK.stare), (0.8, 0.8)),
        Step.hold(Pose(BV.front, FE.smug, MK.still), (1.4, 1.4), action=act_wear(Accessory.sunglasses, 35)),
        Step.hold(Pose(BV.front, FE.smug, MK.nod), (2.2, 2.2), line=always(LC.dealWithIt)),
        Step.hold(Pose(BV.front, FE.smug, MK.breathe), (1.5, 2)),
    ], priority=Priority.rare)


def party_celebration():
    return _activity("celebration.party", CharacterState.celebration, [
        Step.hold(Pose(BV.front, FE.smug, MK.victoryDance), (3, 3.4), line=maybe(LC.partyHat, 0.9), sound=S.celebrate,
                  effects=[E.confetti], action=act_wear(Accessory.partyHat, 14)),
        Step.hold(Pose(BV.front, FE.smug, MK.breathe), (1, 1.5)),
    ])


def achievement_unlocked():
    return _activity("achievement", CharacterState.celebration, [
        Step.hold(Pose(BV.front, FE.smug, MK.celebrate), (2.2, 2.2), sound=S.achievement, effects=[E.sparkles],
                  action=act_wear(Accessory.partyHat, 8)),
        Step.hold(Pose(BV.front, FE.smug, MK.breathe), (0.8, 1)),
    ], priority=Priority.rare)


# ── Rope climbing ─────────────────────────────────────────────────────────────

def rope_climb(to_x: float):
    return _activity("rope.climb", CharacterState.climbing, [
        Step.walk_to(wt_x(to_x), Pose(BV.side, FE.neutral, MK.walk)),
        Step.hold(Pose(BV.back, FE.neutral, MK.ropeSwing), (1.3, 1.3), line=maybe(LC.ropeThrow, 0.9)),
        Step.hold(Pose(BV.back, FE.neutral, MK.throwRope), (0.75, 0.75), sound=S.whoosh, action=act_throw_rope()),
        Step.hold(Pose(BV.back, FE.neutral, MK.tug), (0.8, 0.8), line=maybe(LC.ropeTug, 0.4)),
        Step.climb_step(ClimbDirection.up, 0.85),
        Step.hold(Pose(BV.front, FE.shocked, MK.mantle), (0.45, 0.45), sound=S.thud),
        Step.hold(Pose(BV.front, FE.smug, MK.wave), (1.4, 1.6), line=always(LC.ropeArrive), action=act_coil_rope()),
        Step.hold(_standing(), (0.4, 0.6)),
    ], priority=Priority.urgent)


def rappel(edge_x: float, side: Facing):
    return _activity("rope.down", CharacterState.climbing, [
        Step.walk_to(wt_x(edge_x), Pose(BV.side, FE.neutral, MK.walk)),
        Step.hold(Pose(BV.side, FE.worried, MK.peekLedge), (1.0, 1.2),
                  facing=FacingRule.left if side is Facing.left else FacingRule.right, line=maybe(LC.rappel, 0.9)),
        Step.hold(Pose(BV.back, FE.neutral, MK.tug), (0.6, 0.6), sound=S.whoosh, action=act_attach_rope()),
        Step.climb_step(ClimbDirection.down, 1.3),
        Step.hold(Pose(BV.front, FE.annoyed, MK.land), (0.6, 0.6), sound=S.thud, action=act_coil_rope()),
        Step.hold(_standing(), (0.4, 0.6)),
    ], priority=Priority.urgent)


# ── Pocket ────────────────────────────────────────────────────────────────────

def pocket_react(category, priority=Priority.direct):
    return _activity("pocket.react", CharacterState.reacting, [
        Step.hold(Pose(BV.front, FE.smug, MK.pocketCheck), (1.6, 1.6), line=always(category)),
        Step.hold(_standing(), (0.4, 0.6)),
    ], priority=priority)


def hand_over(file: bool):
    return _activity("pocket.handOver", CharacterState.reacting, [
        Step.hold(Pose(BV.front, FE.smug, MK.holdItem), (1.6, 1.6),
                  line=always(LC.handOverFile if file else LC.handOverClip), sound=S.pop,
                  effects=[E.document] if file else []),
        Step.hold(Pose(BV.front, FE.smug, MK.wave), (0.8, 0.8)),
    ], priority=Priority.direct)


# ── Carrying files (weight by size) & reminders ──────────────────────────────────

class CarryWeight(Enum):
    light = 0
    medium = 1
    heavy = 2
    massive = 3

    @staticmethod
    def for_bytes(nbytes: int) -> "CarryWeight":
        if nbytes < 1_000_000:
            return CarryWeight.light
        if nbytes < 100_000_000:
            return CarryWeight.medium
        if nbytes < 1_000_000_000:
            return CarryWeight.heavy
        return CarryWeight.massive

    @property
    def effect(self) -> Effect:
        return {CarryWeight.light: E.carryLight, CarryWeight.medium: E.carryMedium,
                CarryWeight.heavy: E.carryHeavy, CarryWeight.massive: E.carryMassive}[self]

    @property
    def speed(self) -> float:
        return [0.5, 0.33, 0.18, 0.1][self.value]


def carry(weight: CarryWeight, kind: FileKind, size: str, rng: SeededRandom):
    fx = weight.effect

    def line(templates):
        return text_line(rng.choice(templates))

    if weight is CarryWeight.light:
        steps = [
            Step.hold(Pose(BV.front, FE.shocked, MK.holdItem), (0.5, 0.5), sound=S.pop, effects=[fx]),
            Step.hold(Pose(BV.front, FE.smug, MK.holdItem), (2.2, 2.2), line=always(LC.for_file(kind)), effects=[fx]),
            Step.walk_to(wt_offset(0.5, 0.9), Pose(BV.side, FE.smug, MK.carry), speed=weight.speed, effects=[fx]),
            Step.hold(Pose(BV.front, FE.smug, MK.pocketCheck), (1.4, 1.4),
                      line=line(["%s. Light as a feather. Pocketed." % size,
                                 "Only %s? Easy. Into the pocket." % size])),
        ]
    elif weight is CarryWeight.medium:
        steps = [
            Step.hold(Pose(BV.front, FE.shocked, MK.strain), (0.6, 0.6), sound=S.thud, effects=[fx]),
            Step.hold(Pose(BV.front, FE.annoyed, MK.holdItem), (2.0, 2.0),
                      line=line(["%s? This one's got some weight." % size, "Ooh, %s. Chunky." % size,
                                 "%s. I'll need both hands." % size]), effects=[fx]),
            Step.walk_to(wt_offset(0.5, 0.9), Pose(BV.side, FE.annoyed, MK.carry), speed=weight.speed, effects=[fx]),
            Step.hold(Pose(BV.front, FE.smug, MK.pocketCheck), (1.4, 1.4), line=always(LC.keepFile)),
        ]
    elif weight is CarryWeight.heavy:
        steps = [
            Step.hold(Pose(BV.front, FE.shocked, MK.strain), (1.0, 1.0),
                      line=line(["Oof! %s?! What's in here?" % size, "%s! My spine!" % size,
                                 "%s?! Lift with the knees…" % size]), sound=S.thud, effects=[fx, E.sweat]),
            Step.walk_to(wt_offset(0.6, 1.0), Pose(BV.side, FE.worried, MK.carry), speed=weight.speed,
                         effects=[fx, E.sweat]),
            Step.hold(Pose(BV.front, FE.worried, MK.pant), (1.2, 1.2), effects=[fx, E.sweat]),
            Step.hold(Pose(BV.front, FE.annoyed, MK.pocketCheck), (1.5, 1.5), line=always(LC.pocketedHeavy)),
        ]
    else:
        steps = [
            Step.hold(Pose(BV.front, FE.shocked, MK.strain), (1.4, 1.4),
                      line=line(["%s?! WHAT IS IN THIS?!" % size, "%s! Is this a whole movie?!" % size,
                                 "%s?! I'm not a hard drive!" % size]), sound=S.thud, effects=[fx, E.sweat]),
            Step.hold(Pose(BV.front, FE.worried, MK.strain), (1.6, 1.6), effects=[fx, E.sweat]),
            Step.walk_to(wt_offset(0.4, 0.7), Pose(BV.side, FE.worried, MK.carry), speed=weight.speed,
                         effects=[fx, E.sweat]),
            Step.hold(Pose(BV.front, FE.worried, MK.pant), (1.4, 1.4), effects=[fx, E.sweat]),
            Step.hold(Pose(BV.front, FE.annoyed, MK.pocketCheck), (1.6, 1.6), line=always(LC.pocketedHeavy)),
        ]
    return _activity("file.carry", CharacterState.carrying, steps, priority=Priority.direct)


def reminder(missed: bool):
    return _activity("reminder", CharacterState.reminding, [
        Step.hold(Pose(BV.front, FE.shocked, MK.wakeJolt), (0.9, 0.9),
                  line=always(LC.reminderMissed if missed else LC.reminderIntro), sound=S.wake, effects=[E.exclaim]),
        Step.hold(Pose(BV.front, FE.annoyed, MK.holdSign), (30, 30), sound=S.knock, effects=[E.sign]),
        Step.hold(_standing(), (0.4, 0.6)),
    ], priority=Priority.direct)


def reminder_done():
    return _activity("reminder.done", CharacterState.reacting, [
        Step.hold(Pose(BV.front, FE.smug, MK.nod), (1.6, 1.6), line=always(LC.reminderDismissed)),
    ], priority=Priority.direct)


# ── Trash can ───────────────────────────────────────────────────────────────────

def tidy_up():
    return _activity("item.tidy", CharacterState.walking, [
        Step.walk_to(wt_item(0.12), Pose(BV.side, FE.bored, MK.walk), speed=0.6),
        Step.hold(Pose(BV.front, FE.bored, MK.holdItem), (0.6, 0.6), sound=S.pop, effects=[E.carryItem],
                  action=act_pick_up()),
        Step.walk_to(wt_trash_can(), Pose(BV.side, FE.bored, MK.carry), speed=0.45, effects=[E.carryItem]),
        Step.hold(Pose(BV.side, FE.smug, MK.throwRope), (0.6, 0.6), facing=FacingRule.towardNearestEdge,
                  action=act_dump()),
        Step.hold(Pose(BV.front, FE.smug, MK.nod), (1.4, 1.4), line=always(LC.tidyUp)),
    ], priority=Priority.rare)


def bin_cheer():
    return _activity("item.binCheer", CharacterState.celebration, [
        Step.hold(Pose(BV.front, FE.smug, MK.celebrate), (1.4, 1.4), line=always(LC.binShot)),
    ], priority=Priority.attention)
