"""BREAKING THE FOURTH WALL — rare events — port of RareEvents.swift."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import auto
from typing import Callable, Dict, List, Optional, Tuple

from . import script as scr
from .dialogue import LineCategory as LC, MEETING_PAIRS
from .rng import SeededRandom, weighted_pick
from .script import (Activity, FacingRule, Pose, Priority, Step,
                     act_wear, always, maybe, text_line, wt_away_from_cursor,
                     wt_away_from_edge, wt_nearest_edge, wt_offset, wt_toward_cursor)
from .types import AutoName, Accessory, BodyView as BV, CharacterState, Effect as E, \
    FaceExpression as FE, Mood, MotionKind as MK, SoundCue as S


class RareEvent(AutoName):
    pushWindowEdge = auto()
    inspectBorder = auto()
    fakeOutCursor = auto()
    selfMeeting = auto()
    sarcasticAside = auto()
    knockOnScreen = auto()
    ceilingCheck = auto()
    moonwalk = auto()
    dramaticFaint = auto()
    randomCelebration = auto()
    dealWithIt = auto()
    midnightZoomies = auto()
    floorNap = auto()
    existentialEdgeSit = auto()
    selfDestructBluff = auto()
    dizzySpin = auto()
    victoryLap = auto()
    cursorTag = auto()
    windowCleaning = auto()
    edgeKnock = auto()
    hideBehindEdge = auto()
    wallPhaseGlitch = auto()
    gravityTest = auto()
    phantomTyping = auto()
    measureScreen = auto()
    pushUps = auto()
    jumpingJacks = auto()
    airGuitar = auto()
    shadowBoxing = auto()
    backflipAttempt = auto()
    wiggleDance = auto()
    neckCrack = auto()
    disappointedShake = auto()
    slowWave = auto()
    fakePhoneCall = auto()
    flexPose = auto()
    tripNothing = auto()
    paranoidLook = auto()
    jumpScareSelf = auto()

    @property
    def is_fourth_wall(self) -> bool:
        not_fw = {
            RareEvent.moonwalk, RareEvent.dramaticFaint, RareEvent.randomCelebration, RareEvent.dealWithIt,
            RareEvent.midnightZoomies, RareEvent.floorNap, RareEvent.dizzySpin, RareEvent.victoryLap,
            RareEvent.cursorTag, RareEvent.phantomTyping,
            RareEvent.pushUps, RareEvent.jumpingJacks, RareEvent.airGuitar, RareEvent.shadowBoxing,
            RareEvent.backflipAttempt, RareEvent.wiggleDance, RareEvent.neckCrack, RareEvent.fakePhoneCall,
            RareEvent.flexPose, RareEvent.tripNothing, RareEvent.paranoidLook, RareEvent.jumpScareSelf,
        }
        return self not in not_fw


@dataclass
class RareEventContext:
    cursorDistance: Optional[float]
    edgeDistance: float
    areaWidth: float
    mood: Mood
    fourthWallEnabled: bool


@dataclass
class RareEventDefinition:
    event: RareEvent
    weight: float
    cooldown: float
    is_allowed: Callable[[RareEventContext], bool] = field(default=lambda ctx: True)


def _fakeout_ok(ctx):
    d = ctx.cursorDistance
    return d is not None and 1.6 < d < 7


def _cursortag_ok(ctx):
    d = ctx.cursorDistance
    return d is not None and 2 < d < 10


DEFAULT_DEFINITIONS: List[RareEventDefinition] = [
    RareEventDefinition(RareEvent.sarcasticAside, 5, 90),
    RareEventDefinition(RareEvent.pushWindowEdge, 3, 240),
    RareEventDefinition(RareEvent.inspectBorder, 3, 300, lambda c: c.areaWidth > 3),
    RareEventDefinition(RareEvent.fakeOutCursor, 3, 240, _fakeout_ok),
    RareEventDefinition(RareEvent.selfMeeting, 2, 480),
    RareEventDefinition(RareEvent.knockOnScreen, 2, 300),
    RareEventDefinition(RareEvent.ceilingCheck, 2, 420),
    RareEventDefinition(RareEvent.moonwalk, 1.5, 420, lambda c: c.areaWidth > 3),
    RareEventDefinition(RareEvent.dramaticFaint, 1, 600),
    RareEventDefinition(RareEvent.randomCelebration, 0.6, 900),
    RareEventDefinition(RareEvent.dealWithIt, 1.4, 600),
    RareEventDefinition(RareEvent.midnightZoomies, 2.0, 360, lambda c: c.areaWidth > 4),
    RareEventDefinition(RareEvent.floorNap, 2.0, 480),
    RareEventDefinition(RareEvent.existentialEdgeSit, 2.0, 420, lambda c: c.areaWidth > 3),
    RareEventDefinition(RareEvent.selfDestructBluff, 1.5, 480),
    RareEventDefinition(RareEvent.dizzySpin, 2.0, 360),
    RareEventDefinition(RareEvent.victoryLap, 1.5, 480, lambda c: c.areaWidth > 5),
    RareEventDefinition(RareEvent.cursorTag, 2.5, 300, _cursortag_ok),
    RareEventDefinition(RareEvent.windowCleaning, 1.5, 420),
    RareEventDefinition(RareEvent.edgeKnock, 2.0, 360),
    RareEventDefinition(RareEvent.hideBehindEdge, 2.0, 420),
    RareEventDefinition(RareEvent.wallPhaseGlitch, 1.5, 540, lambda c: c.areaWidth > 4),
    RareEventDefinition(RareEvent.gravityTest, 1.5, 600),
    RareEventDefinition(RareEvent.phantomTyping, 2.0, 360),
    RareEventDefinition(RareEvent.measureScreen, 1.5, 480, lambda c: c.areaWidth > 4),
    RareEventDefinition(RareEvent.pushUps, 2.0, 360),
    RareEventDefinition(RareEvent.jumpingJacks, 2.0, 360),
    RareEventDefinition(RareEvent.airGuitar, 1.8, 420),
    RareEventDefinition(RareEvent.shadowBoxing, 1.8, 420),
    RareEventDefinition(RareEvent.backflipAttempt, 1.5, 480),
    RareEventDefinition(RareEvent.wiggleDance, 2.5, 300),
    RareEventDefinition(RareEvent.neckCrack, 2.0, 300),
    RareEventDefinition(RareEvent.disappointedShake, 1.8, 480),
    RareEventDefinition(RareEvent.slowWave, 1.5, 600),
    RareEventDefinition(RareEvent.fakePhoneCall, 1.8, 360),
    RareEventDefinition(RareEvent.flexPose, 1.8, 420),
    RareEventDefinition(RareEvent.tripNothing, 2.0, 360),
    RareEventDefinition(RareEvent.paranoidLook, 2.0, 360),
    RareEventDefinition(RareEvent.jumpScareSelf, 2.0, 360),
]


def _mood_multiplier(event: RareEvent, mood: Mood) -> float:
    pair = (mood, event)
    if pair in {(Mood.dramatic, RareEvent.dramaticFaint), (Mood.dramatic, RareEvent.knockOnScreen),
                (Mood.dramatic, RareEvent.pushWindowEdge)}:
        return 2
    if pair in {(Mood.smug, RareEvent.randomCelebration), (Mood.smug, RareEvent.moonwalk),
                (Mood.smug, RareEvent.sarcasticAside), (Mood.smug, RareEvent.dealWithIt)}:
        return 1.8
    if mood is Mood.sleepy:
        return 0.6
    if pair in {(Mood.chipper, RareEvent.fakeOutCursor), (Mood.chipper, RareEvent.selfMeeting)}:
        return 1.6
    if pair in {(Mood.grumpy, RareEvent.inspectBorder), (Mood.grumpy, RareEvent.sarcasticAside)}:
        return 1.5
    return 1


class RareEventScheduler:
    def __init__(self, definitions: Optional[List[RareEventDefinition]] = None):
        self.definitions = definitions if definitions is not None else list(DEFAULT_DEFINITIONS)
        self.global_gap = 45.0
        self.max_per_hour = 14
        self.exclude_recent = 2
        self.penalty_window = 5
        self.recent_penalty = 0.35
        self.base_chance = 0.3
        self.frequency = 1.0
        self.history: List[RareEvent] = []
        self._next_allowed: Dict[RareEvent, float] = {}
        self._last_fired_at = float("-inf")
        self._fired_times: List[float] = []

    def candidates(self, now: float, context: RareEventContext) -> List[Tuple[RareEvent, float]]:
        blocked = set(self.history[-self.exclude_recent:]) if self.exclude_recent else set()
        penalized = set(self.history[-self.penalty_window:]) if self.penalty_window else set()
        out = []
        for d in self.definitions:
            if d.event.is_fourth_wall and not context.fourthWallEnabled:
                continue
            if d.event in blocked:
                continue
            t = self._next_allowed.get(d.event)
            if t is not None and now < t:
                continue
            if not d.is_allowed(context):
                continue
            weight = d.weight * _mood_multiplier(d.event, context.mood)
            if d.event in penalized:
                weight *= self.recent_penalty
            out.append((d.event, weight))
        return out

    def pick(self, now: float, context: RareEventContext, rng: SeededRandom) -> Optional[RareEvent]:
        if self.frequency <= 0:
            return None
        if now - self._last_fired_at < self.global_gap / max(0.5, self.frequency):
            return None
        self._fired_times = [t for t in self._fired_times if now - t <= 3600]
        if len(self._fired_times) >= self.max_per_hour:
            return None
        if not rng.chance(min(1.0, self.base_chance * self.frequency)):
            return None
        event = weighted_pick(self.candidates(now, context), rng)
        if event is None:
            return None
        self.mark_fired(event, now)
        return event

    def mark_fired(self, event: RareEvent, now: float) -> None:
        self._last_fired_at = now
        self._fired_times.append(now)
        self.history.append(event)
        if len(self.history) > 20:
            self.history = self.history[len(self.history) - 20:]
        cooldown = next((d.cooldown for d in self.definitions if d.event == event), 120)
        self._next_allowed[event] = now + cooldown


def activity_for_event(event: RareEvent, rng: SeededRandom) -> Activity:
    eid = "rare.%s" % event.value

    def act(state, steps, priority=Priority.rare):
        return Activity(eid, state, priority, steps)

    R = RareEvent
    if event == R.pushWindowEdge:
        return act(CharacterState.fourthWall, [
            Step.hold(Pose(BV.threeQuarter, FE.annoyed, MK.inspect), (1.0, 1.2),
                      facing=FacingRule.awayFromNearestEdge),
            Step.hold(Pose(BV.side, FE.worried, MK.push), (2.6, 2.6), line=always(LC.pushWindow),
                      effects=[E.glassAhead], nudge=0.18),
            Step.hold(Pose(BV.side, FE.shocked, MK.freeze), (0.7, 0.7), effects=[E.glassAhead]),
            Step.hold(Pose(BV.front, FE.shocked, MK.breathe), (1.4, 1.6), line=always(LC.pushWindowAfter)),
        ])
    if event == R.inspectBorder:
        return act(CharacterState.fourthWall, [
            Step.walk_to(wt_nearest_edge(), Pose(BV.side, FE.neutral, MK.walk)),
            Step.hold(Pose(BV.side, FE.annoyed, MK.knock), (1.6, 1.6), facing=FacingRule.towardNearestEdge,
                      sound=S.knock, effects=[E.glassAhead]),
            Step.hold(Pose(BV.side, FE.neutral, MK.inspect), (2.2, 2.6), facing=FacingRule.towardNearestEdge,
                      effects=[E.glassAhead]),
            Step.hold(Pose(BV.front, FE.annoyed, MK.breathe), (1.2, 1.6), line=always(LC.escape)),
        ])
    if event == R.fakeOutCursor:
        return act(CharacterState.fourthWall, [
            Step.hold(Pose(BV.threeQuarter, FE.smug, MK.lookAtCursor), (0.6, 0.8), facing=FacingRule.towardCursor,
                      line=always(LC.fakeOutStart)),
            Step.walk_to(wt_toward_cursor(1.1), Pose(BV.front, FE.smug, MK.run), speed=1.4),
            Step.hold(Pose(BV.front, FE.shocked, MK.freeze), (0.8, 0.8), effects=[E.exclaim]),
            Step.hold(Pose(BV.front, FE.bored, MK.shrug), (1.2, 1.2), line=always(LC.fakeOutAbort)),
            Step.walk_to(wt_away_from_cursor(0.8, 1.3), Pose(BV.side, FE.bored, MK.walk), speed=0.5),
        ])
    if event == R.selfMeeting:
        pairs = list(MEETING_PAIRS)
        rng.shuffle(pairs)
        steps = [Step.hold(Pose(BV.front, FE.neutral, MK.breathe), (0.6, 0.8), effects=[E.meeting])]
        for question, answer in pairs[:2]:
            steps.append(Step.hold(Pose(BV.threeQuarter, FE.annoyed, MK.nod), (2.0, 2.0), facing=FacingRule.left,
                                   line=text_line(question), effects=[E.meeting]))
            steps.append(Step.hold(Pose(BV.threeQuarter, FE.smug, MK.nod), (2.0, 2.0), facing=FacingRule.right,
                                   line=text_line(answer), effects=[E.meeting]))
        steps.append(Step.hold(Pose(BV.front, FE.smug, MK.celebrate), (1.6, 1.6), line=always(LC.meetingClose),
                               effects=[E.meeting]))
        steps.append(Step.hold(scr.standing_pose(), (0.6, 1)))
        return act(CharacterState.fourthWall, steps)
    if event == R.sarcasticAside:
        expr = rng.choice([FE.smug, FE.bored, FE.annoyed])
        return act(CharacterState.fourthWall, [
            Step.hold(Pose(BV.front, expr, MK.stare), (3.0, 3.6), line=always(LC.fourthWall)),
            Step.hold(scr.standing_pose(), (0.5, 0.8)),
        ])
    if event == R.knockOnScreen:
        return act(CharacterState.fourthWall, [
            Step.hold(Pose(BV.front, FE.annoyed, MK.knockScreen), (1.8, 1.8), line=always(LC.knockScreen),
                      sound=S.knock, effects=[E.knockRipple]),
            Step.hold(Pose(BV.front, FE.bored, MK.stare), (1.2, 1.5)),
        ])
    if event == R.ceilingCheck:
        return act(CharacterState.fourthWall, [
            Step.hold(Pose(BV.front, FE.worried, MK.lookUp), (2.4, 2.8), line=always(LC.ceiling), effects=[E.question]),
            Step.hold(Pose(BV.front, FE.annoyed, MK.breathe), (0.8, 1.2)),
        ])
    if event == R.moonwalk:
        return act(CharacterState.walking, [
            Step.walk_to(wt_offset(1.2, 2.0), Pose(BV.side, FE.smug, MK.walk), speed=0.45, backwards=True),
            Step.hold(Pose(BV.front, FE.smug, MK.breathe), (1, 1.2), line=always(LC.moonwalk)),
        ])
    if event == R.dramaticFaint:
        return act(CharacterState.reacting, [
            Step.hold(Pose(BV.front, FE.worried, MK.faint), (1.3, 1.3), sound=S.thud),
            Step.hold(Pose(BV.front, FE.sleepy, MK.sleeping), (1.8, 2.2)),
            Step.hold(Pose(BV.front, FE.bored, MK.getUp), (1.2, 1.2)),
            Step.hold(Pose(BV.front, FE.annoyed, MK.breathe), (1, 1.4), line=always(LC.faint)),
        ])
    if event == R.dealWithIt:
        a = scr.deal_with_it()
        a.id = eid
        return a
    if event == R.randomCelebration:
        return act(CharacterState.celebration, [
            Step.hold(Pose(BV.front, FE.smug, MK.victoryDance), (3.2, 3.8), line=always(LC.celebrate),
                      sound=S.celebrate, effects=[E.confetti, E.sparkles]),
            Step.hold(Pose(BV.front, FE.smug, MK.breathe), (1, 1.4)),
        ])
    if event == R.midnightZoomies:
        return act(CharacterState.walking, [
            Step.walk_to(wt_nearest_edge(), Pose(BV.side, FE.smug, MK.run), speed=2.4),
            Step.walk_to(wt_away_from_edge(30, 50), Pose(BV.side, FE.smug, MK.run), speed=2.4),
            Step.walk_to(wt_away_from_edge(30, 50), Pose(BV.side, FE.smug, MK.run), speed=2.4),
            Step.hold(Pose(BV.front, FE.bored, MK.breathe), (1.2, 1.4), line=always(LC.midnightZoomies)),
        ])
    if event == R.floorNap:
        return act(CharacterState.reacting, [
            Step.hold(Pose(BV.front, FE.sleepy, MK.lieDown), (1.0, 1.0)),
            Step.hold(Pose(BV.front, FE.sleepy, MK.sleeping), (3.0, 4.0), effects=[E.zzz]),
            Step.hold(Pose(BV.front, FE.bored, MK.getUp), (1.2, 1.2)),
            Step.hold(Pose(BV.front, FE.bored, MK.breathe), (1.0, 1.2), line=always(LC.floorNap)),
        ])
    if event == R.existentialEdgeSit:
        return act(CharacterState.fourthWall, [
            Step.walk_to(wt_nearest_edge(), Pose(BV.side, FE.bored, MK.walk)),
            Step.hold(Pose(BV.front, FE.bored, MK.sitDown), (0.8, 0.8)),
            Step.hold(Pose(BV.front, FE.bored, MK.sit), (2.5, 3.0), line=always(LC.existentialEdge),
                      effects=[E.question]),
            Step.hold(Pose(BV.front, FE.neutral, MK.standUp), (0.8, 0.8)),
            Step.hold(Pose(BV.front, FE.bored, MK.shrug), (1.0, 1.2)),
            Step.hold(scr.standing_pose(), (0.4, 0.6)),
        ])
    if event == R.selfDestructBluff:
        return act(CharacterState.fourthWall, [
            Step.hold(Pose(BV.front, FE.shocked, MK.holdSign), (0.9, 0.9), line=text_line("5..."), effects=[E.sign]),
            Step.hold(Pose(BV.front, FE.shocked, MK.holdSign), (0.9, 0.9), line=text_line("4..."), effects=[E.sign]),
            Step.hold(Pose(BV.front, FE.shocked, MK.holdSign), (0.9, 0.9), line=text_line("3..."), effects=[E.sign]),
            Step.hold(Pose(BV.front, FE.shocked, MK.holdSign), (0.9, 0.9), line=text_line("2..."), effects=[E.sign]),
            Step.hold(Pose(BV.front, FE.shocked, MK.holdSign), (0.9, 0.9), line=text_line("1..."), effects=[E.sign]),
            Step.hold(Pose(BV.front, FE.bored, MK.shrug), (1.8, 1.8), line=always(LC.selfDestructBluff)),
            Step.hold(scr.standing_pose(), (0.5, 0.8)),
        ])
    if event == R.dizzySpin:
        return act(CharacterState.reacting, [
            Step.hold(Pose(BV.front, FE.smug, MK.spin), (2.4, 2.8), effects=[E.dizzyStars]),
            Step.hold(Pose(BV.front, FE.worried, MK.dizzy), (1.6, 2.0), effects=[E.dizzyStars]),
            Step.hold(Pose(BV.front, FE.bored, MK.stumble), (1.2, 1.4)),
            Step.hold(Pose(BV.front, FE.bored, MK.breathe), (0.8, 1.0), line=always(LC.dizzySpin)),
        ])
    if event == R.victoryLap:
        return act(CharacterState.celebration, [
            Step.walk_to(wt_nearest_edge(), Pose(BV.side, FE.smug, MK.run), speed=2.2),
            Step.walk_to(wt_away_from_edge(30, 50), Pose(BV.side, FE.smug, MK.run), speed=2.2, effects=[E.confetti]),
            Step.hold(Pose(BV.front, FE.smug, MK.celebrate), (1.6, 1.8), line=always(LC.victoryLap),
                      sound=S.celebrate, effects=[E.confetti, E.sparkles]),
        ])
    if event == R.cursorTag:
        return act(CharacterState.reacting, [
            Step.walk_to(wt_toward_cursor(0.2), Pose(BV.front, FE.smug, MK.run), speed=1.8),
            Step.hold(Pose(BV.front, FE.smug, MK.wakeJolt), (0.5, 0.5), line=always(LC.cursorTag), effects=[E.exclaim]),
            Step.walk_to(wt_away_from_cursor(3.0, 5.0), Pose(BV.side, FE.smug, MK.run), speed=2.0),
            Step.hold(Pose(BV.front, FE.smug, MK.breathe), (0.6, 0.8)),
        ])
    if event == R.windowCleaning:
        return act(CharacterState.fourthWall, [
            Step.walk_to(wt_nearest_edge(), Pose(BV.side, FE.bored, MK.walk)),
            Step.hold(Pose(BV.side, FE.annoyed, MK.push), (1.2, 1.4), facing=FacingRule.towardNearestEdge,
                      effects=[E.glassAhead]),
            Step.hold(Pose(BV.side, FE.bored, MK.push), (1.2, 1.4), facing=FacingRule.towardNearestEdge,
                      effects=[E.glassAhead]),
            Step.hold(Pose(BV.side, FE.annoyed, MK.push), (0.8, 1.0), facing=FacingRule.towardNearestEdge,
                      effects=[E.glassAhead]),
            Step.hold(Pose(BV.front, FE.annoyed, MK.inspect), (1.0, 1.2)),
            Step.hold(Pose(BV.front, FE.bored, MK.shrug), (1.0, 1.2), line=always(LC.windowCleaning)),
            Step.hold(scr.standing_pose(), (0.4, 0.6)),
        ])
    if event == R.edgeKnock:
        return act(CharacterState.fourthWall, [
            Step.walk_to(wt_nearest_edge(), Pose(BV.side, FE.neutral, MK.walk)),
            Step.hold(Pose(BV.side, FE.annoyed, MK.knock), (1.6, 1.6), facing=FacingRule.towardNearestEdge,
                      sound=S.knock, effects=[E.glassAhead]),
            Step.hold(Pose(BV.side, FE.bored, MK.stare), (2.0, 2.4), facing=FacingRule.towardNearestEdge,
                      line=always(LC.edgeKnock), effects=[E.question]),
            Step.hold(Pose(BV.front, FE.annoyed, MK.shrug), (1.0, 1.2)),
            Step.walk_to(wt_away_from_edge(1.5, 3.0), Pose(BV.side, FE.annoyed, MK.walk)),
        ])
    if event == R.hideBehindEdge:
        return act(CharacterState.fourthWall, [
            Step.walk_to(wt_nearest_edge(), Pose(BV.side, FE.bored, MK.hide), speed=0.4),
            Step.hold(Pose(BV.side, FE.smug, MK.peekLedge), (1.4, 1.8), facing=FacingRule.awayFromNearestEdge,
                      line=always(LC.hidePeek)),
            Step.hold(Pose(BV.side, FE.shocked, MK.freeze), (0.6, 0.6), facing=FacingRule.awayFromNearestEdge,
                      effects=[E.exclaim]),
            Step.hold(Pose(BV.side, FE.bored, MK.hide), (0.8, 1.0)),
            Step.walk_to(wt_away_from_edge(1.0, 2.0), Pose(BV.side, FE.bored, MK.walk)),
        ])
    if event == R.wallPhaseGlitch:
        return act(CharacterState.fourthWall, [
            Step.walk_to(wt_nearest_edge(), Pose(BV.side, FE.bored, MK.walk)),
            Step.hold(Pose(BV.side, FE.annoyed, MK.pressGlass), (1.0, 1.2), facing=FacingRule.towardNearestEdge,
                      effects=[E.glassAhead, E.sparkles]),
            Step.walk_to(wt_away_from_edge(30, 50), Pose(BV.side, FE.bored, MK.walk), speed=4.0),
            Step.hold(Pose(BV.front, FE.smug, MK.breathe), (1.0, 1.2), line=always(LC.wallPhase)),
        ])
    if event == R.gravityTest:
        return act(CharacterState.fourthWall, [
            Step.walk_to(wt_nearest_edge(), Pose(BV.side, FE.neutral, MK.walk)),
            Step.hold(Pose(BV.side, FE.worried, MK.peekLedge), (1.4, 1.6), facing=FacingRule.towardNearestEdge),
            Step.hold(Pose(BV.side, FE.smug, MK.jump), (0.6, 0.6), facing=FacingRule.towardNearestEdge,
                      line=always(LC.gravityTest), effects=[E.sweat]),
            Step.hold(Pose(BV.front, FE.bored, MK.freeze), (0.4, 0.6)),
            Step.walk_to(wt_away_from_edge(1.0, 2.0), Pose(BV.side, FE.bored, MK.walk)),
        ])
    if event == R.phantomTyping:
        return act(CharacterState.reacting, [
            Step.hold(Pose(BV.front, FE.neutral, MK.sitDown), (0.8, 0.8)),
            Step.hold(Pose(BV.front, FE.neutral, MK.typing), (3.0, 4.0), effects=[E.keyboard]),
            Step.hold(Pose(BV.front, FE.smug, MK.nod), (1.2, 1.2), line=always(LC.phantomTyping)),
            Step.hold(Pose(BV.front, FE.neutral, MK.standUp), (0.8, 0.8)),
        ])
    if event == R.measureScreen:
        return act(CharacterState.fourthWall, [
            Step.walk_to(wt_nearest_edge(), Pose(BV.side, FE.neutral, MK.walk), speed=0.5),
            Step.hold(Pose(BV.side, FE.neutral, MK.inspect), (0.6, 0.8), facing=FacingRule.towardNearestEdge),
            Step.walk_to(wt_away_from_edge(30, 50), Pose(BV.side, FE.neutral, MK.walk), speed=0.5),
            Step.hold(Pose(BV.side, FE.neutral, MK.inspect), (0.6, 0.8), facing=FacingRule.towardNearestEdge),
            Step.hold(Pose(BV.front, FE.smug, MK.nod), (1.4, 1.6), line=always(LC.measureScreen)),
        ])
    if event == R.pushUps:
        return act(CharacterState.reacting, [
            Step.hold(Pose(BV.front, FE.bored, MK.sitDown), (0.5, 0.5)),
            Step.hold(Pose(BV.front, FE.neutral, MK.strain), (0.7, 0.7), effects=[E.sweat]),
            Step.hold(Pose(BV.front, FE.bored, MK.lieDown), (0.5, 0.5)),
            Step.hold(Pose(BV.front, FE.neutral, MK.strain), (0.7, 0.7), effects=[E.sweat]),
            Step.hold(Pose(BV.front, FE.bored, MK.lieDown), (0.5, 0.5)),
            Step.hold(Pose(BV.front, FE.neutral, MK.strain), (0.7, 0.7), effects=[E.sweat]),
            Step.hold(Pose(BV.front, FE.bored, MK.getUp), (0.9, 0.9)),
            Step.hold(Pose(BV.front, FE.bored, MK.pant), (1.4, 1.6), line=always(LC.pushUps), effects=[E.sweat]),
        ])
    if event == R.jumpingJacks:
        return act(CharacterState.reacting, [
            Step.hold(Pose(BV.front, FE.smug, MK.jump), (0.45, 0.45)),
            Step.hold(Pose(BV.front, FE.neutral, MK.wiggle), (0.5, 0.5)),
            Step.hold(Pose(BV.front, FE.smug, MK.jump), (0.45, 0.45)),
            Step.hold(Pose(BV.front, FE.neutral, MK.wiggle), (0.5, 0.5)),
            Step.hold(Pose(BV.front, FE.smug, MK.jump), (0.45, 0.45)),
            Step.hold(Pose(BV.front, FE.neutral, MK.wiggle), (0.5, 0.5)),
            Step.hold(Pose(BV.front, FE.smug, MK.jump), (0.45, 0.45)),
            Step.hold(Pose(BV.front, FE.bored, MK.pant), (1.2, 1.4), line=always(LC.jumpingJacks)),
        ])
    if event == R.airGuitar:
        return act(CharacterState.celebration, [
            Step.hold(Pose(BV.front, FE.smug, MK.victoryDance), (1.4, 1.6), effects=[E.sparkles]),
            Step.hold(Pose(BV.front, FE.smug, MK.wiggle), (1.2, 1.4), effects=[E.sparkles]),
            Step.hold(Pose(BV.front, FE.smug, MK.wave), (0.8, 1.0)),
            Step.hold(Pose(BV.front, FE.smug, MK.victoryDance), (1.4, 1.6), effects=[E.sparkles]),
            Step.hold(Pose(BV.front, FE.smug, MK.breathe), (0.8, 1.0), line=always(LC.airGuitar)),
        ])
    if event == R.shadowBoxing:
        return act(CharacterState.reacting, [
            Step.hold(Pose(BV.side, FE.annoyed, MK.bonk), (0.5, 0.5), facing=FacingRule.left),
            Step.hold(Pose(BV.side, FE.annoyed, MK.kick), (0.5, 0.5), facing=FacingRule.right),
            Step.hold(Pose(BV.side, FE.annoyed, MK.bonk), (0.5, 0.5), facing=FacingRule.left),
            Step.hold(Pose(BV.front, FE.annoyed, MK.flinch), (0.35, 0.35)),
            Step.hold(Pose(BV.side, FE.smug, MK.kick), (0.5, 0.5), facing=FacingRule.right),
            Step.hold(Pose(BV.side, FE.smug, MK.bonk), (0.5, 0.5), facing=FacingRule.left),
            Step.hold(Pose(BV.front, FE.smug, MK.breathe), (0.8, 1.0), line=always(LC.shadowBoxing), effects=[E.sweat]),
        ])
    if event == R.backflipAttempt:
        return act(CharacterState.reacting, [
            Step.hold(Pose(BV.front, FE.smug, MK.jump), (0.4, 0.4)),
            Step.hold(Pose(BV.front, FE.worried, MK.tumble), (1.2, 1.4)),
            Step.hold(Pose(BV.front, FE.bored, MK.land), (0.6, 0.6)),
            Step.hold(Pose(BV.front, FE.bored, MK.breathe), (1.0, 1.2), line=always(LC.backflip)),
        ])
    if event == R.wiggleDance:
        return act(CharacterState.reacting, [
            Step.hold(Pose(BV.front, FE.smug, MK.wiggle), (1.6, 2.0), effects=[E.sparkles]),
            Step.hold(Pose(BV.front, FE.smug, MK.wiggle), (1.6, 2.0), effects=[E.sparkles]),
            Step.hold(Pose(BV.front, FE.smug, MK.breathe), (0.8, 1.0), line=always(LC.wiggleDance)),
        ])
    if event == R.neckCrack:
        return act(CharacterState.reacting, [
            Step.hold(Pose(BV.side, FE.neutral, MK.lookAround), (0.7, 0.8), facing=FacingRule.left),
            Step.hold(Pose(BV.side, FE.neutral, MK.lookAround), (0.7, 0.8), facing=FacingRule.right),
            Step.hold(Pose(BV.front, FE.smug, MK.shrug), (0.8, 1.0), line=always(LC.neckCrack)),
            Step.hold(scr.standing_pose(), (0.4, 0.6)),
        ])
    if event == R.disappointedShake:
        return act(CharacterState.fourthWall, [
            Step.hold(Pose(BV.front, FE.annoyed, MK.stare), (2.6, 3.0), line=always(LC.disappointedShake),
                      effects=[E.question]),
            Step.hold(Pose(BV.front, FE.annoyed, MK.shrug), (1.0, 1.2)),
            Step.hold(scr.standing_pose(), (0.4, 0.6)),
        ])
    if event == R.slowWave:
        return act(CharacterState.fourthWall, [
            Step.hold(Pose(BV.front, FE.smug, MK.wave), (2.0, 2.4), line=always(LC.slowWave)),
            Step.hold(Pose(BV.front, FE.bored, MK.stare), (1.4, 1.8)),
            Step.hold(Pose(BV.front, FE.bored, MK.shrug), (0.8, 1.0)),
        ])
    if event == R.fakePhoneCall:
        return act(CharacterState.reacting, [
            Step.hold(Pose(BV.front, FE.neutral, MK.wakeJolt), (0.4, 0.4), effects=[E.exclaim]),
            Step.hold(Pose(BV.front, FE.neutral, MK.holdItem), (1.8, 2.0), line=text_line("Mmhm.")),
            Step.hold(Pose(BV.front, FE.neutral, MK.nod), (1.2, 1.4), line=text_line("Yeah. No. Yeah.")),
            Step.hold(Pose(BV.front, FE.neutral, MK.holdItem), (1.0, 1.2), line=text_line("Got it. Later.")),
            Step.hold(Pose(BV.front, FE.bored, MK.shrug), (0.8, 1.0), line=always(LC.fakePhoneCall)),
        ])
    if event == R.flexPose:
        return act(CharacterState.celebration, [
            Step.hold(Pose(BV.front, FE.smug, MK.celebrate), (1.4, 1.6), effects=[E.sparkles]),
            Step.hold(Pose(BV.front, FE.smug, MK.victoryDance), (1.4, 1.6), effects=[E.sparkles]),
            Step.hold(Pose(BV.front, FE.smug, MK.nod), (0.8, 1.0), line=always(LC.flexPose)),
            Step.hold(scr.standing_pose(), (0.4, 0.6)),
        ])
    if event == R.tripNothing:
        return act(CharacterState.reacting, [
            Step.hold(Pose(BV.side, FE.neutral, MK.stumble), (0.8, 1.0)),
            Step.hold(Pose(BV.front, FE.shocked, MK.flinch), (0.4, 0.4), effects=[E.exclaim]),
            Step.hold(Pose(BV.front, FE.bored, MK.breathe), (0.6, 0.8)),
            Step.hold(Pose(BV.front, FE.bored, MK.shrug), (0.8, 1.0), line=always(LC.tripNothing)),
        ])
    if event == R.paranoidLook:
        return act(CharacterState.reacting, [
            Step.hold(Pose(BV.side, FE.worried, MK.lookAround), (0.7, 0.9), facing=FacingRule.left),
            Step.hold(Pose(BV.side, FE.worried, MK.lookAround), (0.7, 0.9), facing=FacingRule.right),
            Step.hold(Pose(BV.front, FE.worried, MK.lookUp), (0.6, 0.8)),
            Step.hold(Pose(BV.front, FE.worried, MK.stare), (1.2, 1.4), line=always(LC.paranoidLook),
                      effects=[E.question]),
            Step.hold(scr.standing_pose(), (0.4, 0.6)),
        ])
    # jumpScareSelf (default)
    return act(CharacterState.reacting, [
        Step.hold(Pose(BV.front, FE.bored, MK.breathe), (0.8, 1.0)),
        Step.hold(Pose(BV.front, FE.shocked, MK.wakeJolt), (0.5, 0.5), effects=[E.exclaim]),
        Step.hold(Pose(BV.front, FE.shocked, MK.freeze), (0.6, 0.8)),
        Step.hold(Pose(BV.front, FE.bored, MK.breathe), (1.0, 1.2), line=always(LC.jumpScareSelf)),
    ])
