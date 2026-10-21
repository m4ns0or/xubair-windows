"""The character's behavior state machine — port of Brain.swift.

Pure logic: no GUI, no timers, no global state. The app drives it by calling tick()
each frame and the user-event methods; it returns a BrainFrame the renderer draws.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple

from . import script as scr
from . import rare_events as revents
from .dialogue import DialogueDirector, LineCategory as LC
from .rng import SeededRandom, weighted_pick
from .script import Activity, FacingRule, LineRequest, Priority, StepAction
from .stats import ALL_ACHIEVEMENTS, Achievement, Stats
from .types import (Accessory, BodyView as BV, CharacterState, Effect, FaceExpression as FE,
                    Facing, Mood, MotionKind as MK, Point, Pose, SoundCue, Bounds)
from .world import (ClipboardContentType, Environment, Item, ItemKind, MemoryPressure,
                    Needs, Platform)

INF = float("inf")


class BehaviorConfig:
    def __init__(self):
        self.noticeRadius = 1.4
        self.panicRadius = 2.0
        self.panicApproachSpeed = 5.5
        self.panicChance = 0.8
        self.sleepAfter = 150.0
        self.gravity = 9.0
        self.throwThreshold = 2.5
        self.maxThrowSpeed = 14.0
        self.awayAfter = 240.0
        self.moodDuration = (240.0, 600.0)
        self.cooldowns: Dict[str, float] = {
            "cursor": 7, "panic": 20, "glassWall": 8, "sleep": 240, "work": 50, "celebration": 120,
            "bored": 20, "idle.tryToLeave": 75, "idle.pockets": 30, "idle.wander": 3,
            "fourthWall.resize": 3, "fourthWall.screen": 10,
            "perch.ride": 25, "perch.ledge": 6, "perch.jump": 6, "item.eat": 3, "item.ball": 1.5,
            "need.hungry": 150, "need.tired": 150, "need.hyper": 8,
            "aware.battery": 1200, "aware.plugged": 60, "aware.time": 900, "aware.welcomeBack": 30,
            "aware.battery20": 600, "aware.battery10": 300, "aware.batteryTimer": 600,
            "aware.cpu": 300, "aware.ram": 600,
            "aware.tooManyApps": 600, "aware.appDetect": 120,
            "aware.build": 120,
            "aware.lateNightBed": 3600, "aware.monday": 3600, "aware.friday": 3600,
            "aware.screenTime2h": 7200, "aware.screenTime4h": 7200, "aware.screenTime6h": 7200,
            "aware.clipboard": 60,
            "rope.climb": 45, "rope.down": 35, "item.tidy": 90, "item.binCheer": 4,
        }

    def cooldown(self, group: str) -> float:
        return self.cooldowns.get(group, 0)


@dataclass
class WorldInput:
    dt: float
    bounds: Bounds
    cursor: Optional[Point]
    height: float
    speed: float = 1.0
    platforms: List[Platform] = field(default_factory=list)


class FocusPhase(Enum):
    off = auto()
    focus = auto()
    rest = auto()


@dataclass
class RopeState:
    anchor: Point
    reach: float


class BrainFrame:
    def __init__(self, position, state, activityID, pose, facing, stepTime, stepDuration,
                 gaitPhase, isWalking, effects, speech, sounds, mood):
        self.position = position
        self.state = state
        self.activityID = activityID
        self.pose = pose
        self.facing = facing
        self.stepTime = stepTime
        self.stepDuration = stepDuration
        self.gaitPhase = gaitPhase
        self.isWalking = isWalking
        self.effects: Set[Effect] = effects
        self.speech = speech
        self.sounds: List[SoundCue] = sounds
        self.mood = mood
        self.accessories: Set[Accessory] = set()
        self.achievement: Optional[Achievement] = None
        self.isPerched = False
        self.isHyper = False
        self.rope: Optional[RopeState] = None
        self.binHit = False
        self.carriedEmoji: Optional[str] = None


class CharacterBrain:
    def __init__(self, position: Point, config: Optional[BehaviorConfig] = None, seed: Optional[int] = None):
        self.config = config or BehaviorConfig()
        self.dialogue = DialogueDirector()
        self.rare = revents.RareEventScheduler()
        self.gravityEnabled = True
        self.fourthWallEnabled = True
        self.needsEnabled = True
        self.awarenessEnabled = True
        self.ropeEnabled = True
        self.trashEnabled = True
        self.trashCanSize = 46.0

        self.position = position
        self.clock = 0.0
        self.rng = SeededRandom(seed)
        self.mood = self.rng.choice(list(Mood))
        self.activity: Activity = scr.idle_stand()
        self.stepIndex = 0
        self.isDragging = False
        self.items: List[Item] = []
        self.focusPhase = FocusPhase.off
        self.isAway = False
        self.needs = Needs()
        self.stats = Stats()
        self.unlockedAchievements: Set[str] = set()

        self._stepStarted = False
        self._stepElapsed = 0.0
        self._stepDuration = 0.0
        self._walkTargetX: Optional[float] = None
        self._walkExpectsWall = False
        self._walkItemStopShort: Optional[float] = None
        self._nudgeRate = 0.0
        self.pose = scr.standing_pose()
        self.facing = Facing.right
        self.effects: Set[Effect] = set()
        self.gaitPhase = 0.0

        self._lastAttention = 0.0
        self._cooldownUntil: Dict[str, float] = {}
        self._recentGroups: List[str] = []
        self._moodUntil = self.rng.pick(self.config.moodDuration)
        self._dragStart = Point(0, 0)
        self._dropWasFar = False
        self._clickTimes: List[float] = []
        self._lastForcedLineAt = -INF

        # Physics & perching
        self._airborne = False
        self._thrownFlight = False
        self._vx = 0.0
        self._vy = 0.0
        self._bouncesThisFlight = 0
        self._standingOn: Optional[Platform] = None
        self._ignorePlatformID: Optional[int] = None
        self._platforms: List[Platform] = []

        # Rope
        self._rope: Optional[RopeState] = None
        self._ropePlatformID: Optional[int] = None
        self._ropeTarget: Optional[Platform] = None
        self._climbTargetY: Optional[float] = None

        # Trash can
        self._carriedItem: Optional[ItemKind] = None
        self._pendingBinHit = False
        self._binQueue: List[int] = []

        # Items
        self._nextItemID = 1
        self._targetItemID: Optional[int] = None
        self._kicksThisSession = 0
        self._kickLimit = 4

        # Needs, accessories, achievements, awareness
        self._hyperUntil = -INF
        self._accessoryUntil: Dict[Accessory, float] = {}
        self._pendingAchievements: List[Achievement] = []
        self._achievementsToCelebrate = 0
        self._lastAchievementCheck = 0.0
        self._environment = Environment()
        self._lastCharging: Optional[bool] = None
        self._lastDetectedApps: Set[str] = set()
        self._lastClipboardType = ClipboardContentType.other
        self._buildRunningSince: Optional[float] = None
        self._lastLongIdle: Optional[float] = None

        self._cursorDistance: Optional[float] = None
        self._cursorPoint: Optional[Point] = None
        self._previousCursor: Optional[Point] = None
        self._approachSpeed = 0.0
        self.bounds = Bounds(0, 1000, 0, 800)
        self.height = 150.0

        self._pendingSpeech: Optional[str] = None
        self._pendingSounds: List[SoundCue] = []

    # ── public read-only-ish properties ──────────────────────────────────────

    @property
    def state(self) -> CharacterState:
        return CharacterState.dragged if self.isDragging else self.activity.state

    @property
    def isHyper(self) -> bool:
        return self.clock < self._hyperUntil

    @property
    def isPerched(self) -> bool:
        return self._standingOn is not None

    # ── Tick ─────────────────────────────────────────────────────────────────

    def tick(self, inp: WorldInput) -> BrainFrame:
        dt = max(0.0, min(inp.dt, 0.1)) * max(0.1, inp.speed)
        self.clock += dt
        self.bounds = inp.bounds
        self.height = max(20.0, inp.height)
        self._platforms = list(inp.platforms) if self.gravityEnabled else []

        self._update_mood()
        self._update_needs(dt)
        self._perceive_cursor(inp.cursor, dt)
        self._update_items(dt)
        self._flush_bin_queue()

        if self.isDragging:
            return self._make_frame(Pose(BV.front, FE.shocked, MK.dangle), CharacterState.dragged)

        if self.gravityEnabled:
            self._follow_rope()
            if not self._airborne:
                self._follow_platform()
            if not self._airborne and not self._is_supported():
                self._launch(0, 0, False)
            if self._airborne:
                self._integrate_flight(dt)
                if self._airborne:
                    return self._make_frame(self.pose, self.activity.state)
        elif self._airborne:
            self._airborne = False
            self._start(scr.landed(self._dropWasFar))

        self.position = self.bounds.clamped(self.position)
        self._react_to_items()
        self._react_to_cursor()
        self._advance(dt)
        self._check_achievements()
        return self._make_frame(self.pose, self.activity.state)

    # ── User events ──────────────────────────────────────────────────────────

    def handle_click(self):
        self._lastAttention = self.clock
        self._clickTimes.append(self.clock)
        self._clickTimes = [t for t in self._clickTimes if self.clock - t <= 4]
        self.stats.pokes += 1
        self.needs.fun += 0.03
        if self.isDragging or self._airborne:
            return
        if self.activity.id == "reminder":
            self._start(scr.reminder_done())
        elif self.activity.state == CharacterState.sleep:
            self._start(scr.dramatic_wake())
        elif self.focusPhase == FocusPhase.focus:
            self._start(Activity("click.focus", CharacterState.reacting, Priority.direct, [
                scr.Step.hold(Pose(BV.front, FE.annoyed, MK.flinch), (0.6, 0.6), line=scr.always(LC.focusPoke),
                              sound=SoundCue.pop),
            ]))
        else:
            self._start(scr.click_reaction(len(self._clickTimes) >= 3, self.rng))

    def begin_drag(self):
        self.isDragging = True
        self._dragStart = self.position.copy()
        self._lastAttention = self.clock
        self._airborne = False
        self._standingOn = None
        self._rope = None
        self._vx = 0
        self._vy = 0
        self.effects = set()
        self._speak(scr.always(LC.pickedUp))
        self._pendingSounds.append(SoundCue.whoosh)

    def drag(self, point: Point):
        if not self.isDragging:
            return
        self.position = self.bounds.clamped(point)

    def end_drag(self, velocity: Point = None):
        if velocity is None:
            velocity = Point(0, 0)
        if not self.isDragging:
            return
        self.isDragging = False
        self._lastAttention = self.clock
        self._dropWasFar = self.position.distance(self._dragStart) > self.height * 3
        speed = math.sqrt(velocity.x * velocity.x + velocity.y * velocity.y) / self.height
        if self.gravityEnabled and speed > self.config.throwThreshold:
            scale = min(1.0, self.config.maxThrowSpeed / speed)
            self.stats.throwCount += 1
            self.needs.fun += 0.05
            self._speak(scr.always(LC.thrown))
            self._launch(velocity.x * scale, max(velocity.y * scale, self.height * 1.5), True)
        elif self.gravityEnabled and not self._is_supported():
            self._launch(0, 0, False)
        else:
            self._start(scr.landed(self._dropWasFar))

    def notice_resize(self, bigger: bool):
        if (not self.isDragging and not self._airborne and self.activity.state != CharacterState.sleep
                and self._cooldown_ready("fourthWall.resize")):
            self._start(scr.notice_resize(bigger))

    def notice_screen_change(self, new_bounds: Bounds):
        self.bounds = new_bounds
        self.position = new_bounds.clamped(self.position)
        if (not self.isDragging and not self._airborne and self.activity.state != CharacterState.sleep
                and self._cooldown_ready("fourthWall.screen")):
            self._start(scr.notice_screen_change())

    def place(self, point: Point, new_bounds: Bounds):
        self.bounds = new_bounds
        self.position = new_bounds.clamped(point)
        if not self.isDragging:
            self._airborne = False
            self._standingOn = None
            self._vx = 0
            self._vy = 0

    def force(self, new_activity: Activity):
        self._start(new_activity)

    def force_rare(self, event):
        self.rare.mark_fired(event, self.clock)
        self._start(revents.activity_for_event(event, self.rng))

    def note_user_attention(self):
        self._lastAttention = self.clock

    # ── Items ────────────────────────────────────────────────────────────────

    def spawn_item(self, kind: ItemKind) -> int:
        if len(self.items) >= 6:
            self.items.pop(0)
        x = min(max(self.position.x + self.rng.uniform(-2.5, 2.5) * self.height, self.bounds.minX), self.bounds.maxX)
        item = Item(id=self._nextItemID, kind=kind,
                    position=Point(x, self.bounds.maxY + self.height * 0.9))
        item.vx = self.rng.uniform(-0.3, 0.3) * self.height
        self.items.append(item)
        self._nextItemID += 1
        self._lastAttention = self.clock
        return item.id

    def _item_index(self, id: int) -> Optional[int]:
        for i, it in enumerate(self.items):
            if it.id == id:
                return i
        return None

    def grab_item(self, id: int):
        i = self._item_index(id)
        if i is None:
            return
        self.items[i].held = True
        self.items[i].grounded = False
        self.items[i].standingOn = None
        if self._targetItemID == id:
            self._abort_activity()

    def drag_item(self, id: int, point: Point):
        i = self._item_index(id)
        if i is None:
            return
        self.items[i].position = Point(
            min(max(point.x, self.bounds.minX - self.height), self.bounds.maxX + self.height),
            min(max(point.y, self.bounds.floorY), self.bounds.maxY + self.height))

    def release_item(self, id: int, velocity: Point):
        i = self._item_index(id)
        if i is None:
            return
        if self.trashEnabled and self.is_over_trash_can(self.items[i].position):
            self._swallow_into_bin(id, cheer=True)
            return
        self.items[i].held = False
        cap = self.config.maxThrowSpeed * self.height
        self.items[i].vx = max(-cap, min(cap, velocity.x))
        self.items[i].vy = max(-cap, min(cap, velocity.y))
        self.items[i].restingFor = 0
        self.items[i].thrownByUser = True

    @property
    def trash_can_position(self) -> Point:
        return Point(self.bounds.maxX - self.trashCanSize * 0.4, self.bounds.floorY)

    def is_over_trash_can(self, p: Point) -> bool:
        c = self.trash_can_position
        return (abs(p.x - c.x) < self.trashCanSize * 0.75
                and p.y >= c.y - 4 and p.y < c.y + self.trashCanSize * 1.4)

    def remove_item(self, id: int):
        self.items = [it for it in self.items if it.id != id]
        if self._targetItemID == id:
            self._abort_activity()

    def _swallow_into_bin(self, id: int, cheer: bool):
        self.items = [it for it in self.items if it.id != id]
        if self._targetItemID == id:
            self._targetItemID = None
            if self.activity.id.startswith("item."):
                self._abort_activity()
        self._pendingBinHit = True
        self._pendingSounds.append(SoundCue.thud)
        if (cheer and not self.isDragging and not self._airborne
                and self.activity.priority < Priority.direct and self._cooldown_ready("item.binCheer")):
            self._start(scr.bin_cheer())

    def remove_all_items(self):
        self.items = []
        if self._targetItemID is not None:
            self._abort_activity()

    # ── Focus buddy ──────────────────────────────────────────────────────────

    def start_focus(self):
        self.focusPhase = FocusPhase.focus
        self._lastAttention = self.clock
        if not self.isDragging and not self._airborne:
            self._start(scr.focus_start())

    def complete_focus(self):
        self.stats.focusSessions += 1
        self.focusPhase = FocusPhase.rest
        combined = Activity("focus.end", CharacterState.celebration, Priority.direct,
                            scr.focus_end().steps + scr.break_start().steps)
        if not self.isDragging and not self._airborne:
            self._start(combined)

    def end_break(self):
        self.focusPhase = FocusPhase.off
        self._lastAttention = self.clock
        if not self.isDragging and not self._airborne:
            self._start(scr.break_end())

    def stop_focus(self):
        self.focusPhase = FocusPhase.off
        if self.activity.state == CharacterState.focus:
            self._abort_activity()

    # ── Awareness ────────────────────────────────────────────────────────────

    def update_environment(self, env: Environment):
        self._environment = env
        if not self.awarenessEnabled:
            self._lastCharging = env.isCharging
            return
        busy = self.isDragging or self._airborne
        if env.userIdleSeconds > self.config.awayAfter and not self.isAway:
            self.isAway = True
            if (not busy and self.focusPhase == FocusPhase.off and self.activity.state != CharacterState.sleep
                    and self.activity.priority < Priority.urgent):
                self._start(scr.away_sleep())
        elif self.isAway and env.userIdleSeconds < 3:
            self.isAway = False
            self._lastAttention = self.clock
            if not busy and (self.activity.state == CharacterState.sleep or self._cooldown_ready("aware.welcomeBack")):
                self._start(scr.welcome_back())

        if env.isCharging is not None and env.batteryLevel is not None:
            charging = env.isCharging
            level = env.batteryLevel
            if (self._lastCharging is False and charging and not busy
                    and self.activity.priority < Priority.urgent and self._cooldown_ready("aware.plugged")):
                self._start(scr.plugged_in())
            elif not charging:
                if level < 0.10 and not busy and self.activity.priority < Priority.urgent \
                        and self._cooldown_ready("aware.battery10"):
                    self._start(scr.battery10())
                elif level < 0.20 and not busy and self.activity.priority < Priority.urgent \
                        and self._cooldown_ready("aware.battery20"):
                    self._start(scr.battery20())
                elif level < 0.15 and not busy and self.activity.priority < Priority.urgent \
                        and self._cooldown_ready("aware.battery"):
                    self._start(scr.low_battery())
                mins = env.batteryTimeToEmptyMinutes
                if (mins is not None and mins < 30 and not busy and self.activity.priority < Priority.urgent
                        and self._cooldown_ready("aware.batteryTimer")):
                    self._start(scr.say(LC.batteryTimer, "aware.batteryTimer", motion=MK.pant, expression=FE.worried))
        self._lastCharging = env.isCharging

        if env.cpuLoad > 0.80 and not busy and self.activity.priority < Priority.attention \
                and self._cooldown_ready("aware.cpu"):
            self._start(scr.say(LC.cpuSpike, "aware.cpu", motion=MK.strain, expression=FE.worried))

        if env.memoryPressure == MemoryPressure.critical and not busy \
                and self.activity.priority < Priority.attention and self._cooldown_ready("aware.ram"):
            self._start(scr.say(LC.ramCritical, "aware.ram", motion=MK.faint, expression=FE.worried))

        if not busy and self.activity.priority < Priority.attention and self._cooldown_ready("aware.tooManyApps"):
            if env.runningAppCount >= 20:
                self._start(scr.say(LC.tooManyApps20, "aware.tooManyApps", expression=FE.shocked))
            elif env.runningAppCount >= 15:
                self._start(scr.say(LC.tooManyApps15, "aware.tooManyApps", expression=FE.annoyed))
            elif env.runningAppCount >= 10:
                self._start(scr.say(LC.tooManyApps, "aware.tooManyApps"))

        if not self._lastDetectedApps and env.runningAppCount > 0:
            self._lastDetectedApps = set(env.detectedBundleIDs)
        else:
            new_apps = env.detectedBundleIDs - self._lastDetectedApps
            if not new_apps:
                self._lastDetectedApps = set(env.detectedBundleIDs)
            else:
                watched = [("com.apple.dt.Xcode", LC.appXcode), ("us.zoom.xos", LC.appZoom),
                           ("com.tinyspeck.slackmacgap", LC.appSlack), ("com.figma.Desktop", LC.appFigma)]
                match = next(((bid, cat) for (bid, cat) in watched if bid in new_apps), None)
                if match is not None and not busy and self._cooldown_ready("aware.appDetect"):
                    self._lastDetectedApps = set(env.detectedBundleIDs)
                    self._start(scr.say(match[1], "aware.appDetect", expression=FE.annoyed))
                elif match is None:
                    self._lastDetectedApps = set(env.detectedBundleIDs)

        if env.buildProcessRunning:
            if self._buildRunningSince is None:
                self._buildRunningSince = self.clock
            build_mins = int((self.clock - (self._buildRunningSince or self.clock)) / 60)
            if build_mins > 0 and not busy and self.activity.priority < Priority.attention \
                    and self._cooldown_ready("aware.build"):
                self._start(scr.say(LC.buildSuffering, "aware.build"))
        else:
            self._buildRunningSince = None

        h, d = env.hour, env.weekday
        if 2 <= h < 5 and not busy and self.activity.priority < Priority.attention \
                and self._cooldown_ready("aware.lateNightBed"):
            self._start(scr.say(LC.lateNightBed, "aware.lateNightBed", motion=MK.holdSign))
        if d == 2 and 8 <= h < 10 and not busy and self.activity.priority < Priority.attention \
                and self._cooldown_ready("aware.monday"):
            self._start(scr.say(LC.mondaySigh, "aware.monday", motion=MK.shrug))
        if d == 6 and 16 <= h < 19 and not busy and self.activity.priority < Priority.attention \
                and self._cooldown_ready("aware.friday"):
            self._start(scr.say(LC.fridayHype, "aware.friday", motion=MK.celebrate, expression=FE.smug))

        if self._lastLongIdle is None:
            self._lastLongIdle = self.clock
        if env.userIdleSeconds > 300:
            self._lastLongIdle = self.clock
        screen_mins = (self.clock - (self._lastLongIdle or self.clock)) / 60
        if not busy and self.activity.priority < Priority.attention:
            if screen_mins > 360 and self._cooldown_ready("aware.screenTime6h"):
                self._start(scr.screen_time_nag(6))
            elif screen_mins > 240 and self._cooldown_ready("aware.screenTime4h"):
                self._start(scr.screen_time_nag(4))
            elif screen_mins > 120 and self._cooldown_ready("aware.screenTime2h"):
                self._start(scr.screen_time_nag(2))

        if env.clipboardType != ClipboardContentType.unchanged:
            changed = env.clipboardType != self._lastClipboardType
            self._lastClipboardType = env.clipboardType
            if (changed and env.clipboardType != ClipboardContentType.other and not busy
                    and self.activity.priority < Priority.attention and self._cooldown_ready("aware.clipboard")):
                self._start(scr.clipboard_react(env.clipboardType))

    def greet(self):
        if self.isDragging or self._airborne:
            return
        self._start(scr.greeting(self._environment.hour))

    # ── Files ────────────────────────────────────────────────────────────────

    def file_hover_began(self):
        if self.isDragging or self._airborne or self.activity.id == "file.hover":
            return
        self._lastAttention = self.clock
        self._start(scr.file_hover())

    def file_hover_ended(self):
        if self.activity.id == "file.hover":
            self._abort_activity()

    def inspect_file(self, kind, kept=False):
        self.stats.filesInspected += 1
        self._lastAttention = self.clock
        if self.isDragging or self._airborne:
            return
        self._start(scr.inspect_file(kind, kept))

    def receive_files(self, kind, kept, nbytes, size_text):
        if not kept:
            self.inspect_file(kind)
            return
        self.stats.filesInspected += 1
        self._lastAttention = self.clock
        if self.isDragging or self._airborne:
            return
        self._start(scr.carry(scr.CarryWeight.for_bytes(nbytes), kind, size_text, self.rng))

    def remind(self, missed=False):
        self._lastAttention = self.clock
        if self.isDragging:
            return
        if self._airborne or self._hanging_on_rope:
            self._rope = None
            self._airborne = False
            self._standingOn = None
        self._start(scr.reminder(missed))

    @property
    def is_holding_reminder(self) -> bool:
        return self.activity.id == "reminder"

    def reminder_set(self):
        if self.isDragging or self._airborne or self.activity.priority >= Priority.direct:
            return
        self._start(scr.say(LC.reminderSet, "reminder.set", motion=MK.nod, expression=FE.smug))

    def ring_opened(self):
        if (self.isDragging or self._airborne or self.activity.priority >= Priority.rare
                or not self._cooldown_ready("pocket.ring")):
            return
        self._cooldownUntil["pocket.ring"] = self.clock + 30
        self._start(scr.pocket_react(LC.whichOne, priority=Priority.attention))

    # ── Pocket ───────────────────────────────────────────────────────────────

    def clipboard_saved(self):
        if (self.isDragging or self._airborne or self.focusPhase == FocusPhase.focus
                or self.activity.priority >= Priority.rare or self.activity.state == CharacterState.sleep
                or not self._cooldown_ready("pocket.clip")):
            return
        self._cooldownUntil["pocket.clip"] = self.clock + 25
        self._start(scr.pocket_react(LC.clipboardSaved, priority=Priority.attention))

    def open_pocket(self, item_count: int):
        self._lastAttention = self.clock
        if self.isDragging or self._airborne:
            return
        self._start(scr.pocket_react(LC.pocketEmpty if item_count == 0 else LC.whichOne))

    def hand_over(self, file: bool):
        self._lastAttention = self.clock
        if self.isDragging or self._airborne:
            return
        self._start(scr.hand_over(file))

    def pocket_forgot(self):
        if self.isDragging or self._airborne:
            return
        self._start(scr.pocket_react(LC.binForget))

    def notice_new_look(self):
        if self.isDragging or self._airborne:
            return
        self._start(scr.say(LC.newLook, "fourthWall.newLook", motion=MK.sizeCheck, expression=FE.smug))

    def wear(self, accessory: Accessory, seconds: float):
        self._accessoryUntil[accessory] = self.clock + seconds

    # ── Rope climbing ────────────────────────────────────────────────────────

    def climb_somewhere(self) -> bool:
        if not self.gravityEnabled or self.isDragging or self._airborne:
            self._speak(scr.always(LC.noWindows))
            return False
        plan = self._climb_plan()
        if plan is None:
            self._speak(scr.always(LC.noWindows))
            return False
        self._ropeTarget = plan[0]
        self._start(scr.rope_climb(plan[1]))
        return True

    def rappel_down(self) -> bool:
        if self.isDragging or self._airborne or self._standingOn is None:
            return False
        plan = self._rappel_plan(self._standingOn)
        if plan is None:
            return False
        self._start(scr.rappel(plan[0], plan[1]))
        return True

    def _climb_plan(self) -> Optional[Tuple[Platform, float]]:
        limits = self._walk_limits()
        options: List[Tuple[Tuple[Platform, float], float]] = []
        for p in self._platforms:
            if (self._standingOn is not None and p.id == self._standingOn.id):
                continue
            if not (p.y > self.position.y + self.height * 0.9 and p.y <= self.bounds.maxY):
                continue
            lo = max(p.minX + self.height * 0.25, limits[0])
            hi = min(p.maxX - self.height * 0.25, limits[1])
            if lo > hi:
                continue
            x = min(max(self.position.x + self.rng.uniform(-1, 1) * self.height, lo), hi)
            weight = 1 / (1 + abs(x - self.position.x) / self.height * 0.2
                          + (p.y - self.position.y) / self.height * 0.15)
            options.append(((p, x), weight))
        return weighted_pick(options, self.rng)

    def _rappel_plan(self, p: Platform) -> Optional[Tuple[float, Facing]]:
        limits = self._walk_limits()
        drop = self.height * 0.18
        sides: List[Facing] = []
        if limits[2] and p.minX - drop >= self.bounds.minX:
            sides.append(Facing.left)
        if limits[3] and p.maxX + drop <= self.bounds.maxX:
            sides.append(Facing.right)
        if not sides:
            return None
        side = self.rng.choice(sides)
        return (limits[0] if side is Facing.left else limits[1], side)

    @property
    def _hanging_on_rope(self) -> bool:
        if self._rope is None:
            return False
        return ((self.activity.id == "rope.climb" and self.stepIndex == 4)
                or (self.activity.id == "rope.down" and self.stepIndex == 3))

    def _follow_rope(self):
        if self._rope is None or self._ropePlatformID is None:
            return
        r = self._rope
        id = self._ropePlatformID
        p = next((pl for pl in self._platforms if pl.id == id), None)
        if p is None:
            was_hanging = self._hanging_on_rope
            self._rope = None
            self._ropePlatformID = None
            self._ropeTarget = None
            if self.activity.id.startswith("rope."):
                self._speak(scr.always(LC.ropeSnap))
                if was_hanging:
                    self._launch(0, 0, False)
                else:
                    self._abort_activity()
            return
        old = self._ropeTarget
        if old is not None and old.id == id and abs((p.maxX - p.minX) - (old.maxX - old.minX)) < 1:
            dx = p.minX - old.minX
            r.anchor.x += dx
            if self._hanging_on_rope:
                self.position.x += dx
        self._ropeTarget = p
        r.anchor.y = p.y
        self._rope = r

    def _ground_below(self, x: float, from_y: float, excluding: Optional[int]) -> Tuple[float, Optional[Platform]]:
        best = (self.bounds.floorY, None)
        for p in self._platforms:
            if p.id == excluding:
                continue
            if p.contains(x) and p.y < from_y - 1 and p.y > best[0]:
                best = (p.y, p)
        return best

    # ── Internals ────────────────────────────────────────────────────────────

    def _update_mood(self):
        if self.clock < self._moodUntil:
            return
        weights = [(m, 0.4 if m == self.mood else (0.5 if m == Mood.chipper else 1.0)) for m in Mood]
        self.mood = weighted_pick(weights, self.rng) or Mood.grumpy
        self._moodUntil = self.clock + self.rng.pick(self.config.moodDuration)

    def _update_needs(self, dt):
        if not self.needsEnabled:
            return
        self.needs.hunger += dt / 2700
        if self.activity.state == CharacterState.sleep:
            self.needs.energy += dt / 400
        else:
            self.needs.energy -= dt / (1500 if self.isHyper else 4000)
        self.needs.fun -= dt / 2400
        self.needs.clamp()

    def _perceive_cursor(self, cursor: Optional[Point], dt: float):
        self._cursorPoint = cursor
        if cursor is None:
            self._cursorDistance = None
            self._previousCursor = None
            self._approachSpeed = 0
            return
        chest = Point(self.position.x, self.position.y + self.height * 0.55)
        distance = chest.distance(cursor) / self.height
        if self._previousCursor is not None and dt > 0:
            instant = (chest.distance(self._previousCursor) / self.height - distance) / dt
            self._approachSpeed = self._approachSpeed * 0.6 + instant * 0.4
        self._previousCursor = cursor.copy()
        self._cursorDistance = distance
        if distance < self.config.noticeRadius * 1.6:
            self._lastAttention = self.clock

    def _react_to_cursor(self):
        distance = self._cursorDistance
        if distance is None:
            return
        if (distance < self.config.panicRadius and self._approachSpeed > self.config.panicApproachSpeed
                and self._can_interrupt(Priority.urgent) and self._cooldown_ready("panic")):
            self._cooldownUntil["panic"] = self.clock + self.config.cooldown("panic") * 0.4
            if self.rng.chance(self.config.panicChance):
                self._start(scr.panic(self.rng))
            return
        if (distance < self.config.noticeRadius and self._can_interrupt(Priority.attention)
                and self._cooldown_ready("cursor")):
            self._start(scr.notice_cursor())

    def _can_interrupt(self, priority: int) -> bool:
        return priority > self.activity.priority

    # ── Physics ──────────────────────────────────────────────────────────────

    def _launch(self, vx, vy, thrown):
        self._airborne = True
        self._thrownFlight = thrown
        self._vx = vx
        self._vy = vy
        self._bouncesThisFlight = 0
        if self._standingOn is not None:
            self._ignorePlatformID = self._standingOn.id
        self._standingOn = None
        self._start(scr.airborne(thrown))
        self._begin_step()

    def _is_supported(self) -> bool:
        if self._hanging_on_rope:
            return True
        if self.position.y <= self.bounds.floorY + 0.5:
            self.position.y = self.bounds.floorY
            return True
        if self._standingOn is not None:
            return True
        p = next((pl for pl in self._platforms if pl.contains(self.position.x) and abs(pl.y - self.position.y) < 1.5),
                 None)
        if p is not None:
            self._standingOn = p
            self.position.y = p.y
            return True
        return False

    def _follow_platform(self):
        old = self._standingOn
        if old is None:
            return
        now = next((pl for pl in self._platforms if pl.id == old.id), None)
        if now is None or not now.contains(self.position.x + (now.minX - old.minX)):
            self._standingOn = None
            return
        same_width = abs((now.maxX - now.minX) - (old.maxX - old.minX)) < 1
        dx = (now.minX - old.minX) if same_width else 0
        dy = now.y - old.y
        self.position.x += dx
        self.position.y = now.y
        self._standingOn = now
        if (abs(dx) + abs(dy) > self.height * 0.08 and self.activity.priority < Priority.attention
                and self._cooldown_ready("perch.ride")):
            self._start(scr.ride_window())

    def _integrate_flight(self, dt):
        g = self.config.gravity * self.height
        self._vy -= g * dt
        previous_y = self.position.y
        self.position.x += self._vx * dt
        self.position.y += self._vy * dt
        if self._ignorePlatformID is not None:
            ip = next((pl for pl in self._platforms if pl.id == self._ignorePlatformID), None)
            if ip is None or not ip.contains(self.position.x):
                self._ignorePlatformID = None

        if self.position.x < self.bounds.minX or self.position.x > self.bounds.maxX:
            self.position.x = min(max(self.position.x, self.bounds.minX), self.bounds.maxX)
            if abs(self._vx) > self.height * 0.8:
                self._vx = -self._vx * 0.55
                self._register_bounce(wall=True)
            else:
                self._vx = 0
        if self.position.y > self.bounds.maxY:
            self.position.y = self.bounds.maxY
            if self._vy > 0:
                self._vy = -self._vy * 0.4
                self._register_bounce(wall=True)
        if self._vy > 0:
            return
        support = self._landing_support(previous_y)
        if support is None:
            return
        self.position.y = support[0]
        if self._thrownFlight and abs(self._vy) > self.height * 3:
            self._vy = -self._vy * 0.38
            self._vx *= 0.7
            self._register_bounce(wall=False)
            return
        self._land(support[1])

    def _landing_support(self, previous_y) -> Optional[Tuple[float, Optional[Platform]]]:
        best = None
        if self.position.y <= self.bounds.floorY:
            best = (self.bounds.floorY, None)
        for p in self._platforms:
            if p.id == self._ignorePlatformID:
                continue
            if (p.contains(self.position.x) and p.y > self.bounds.floorY
                    and previous_y >= p.y - 0.5 and self.position.y <= p.y):
                if best is None or p.y > best[0]:
                    best = (p.y, p)
        return best

    def _register_bounce(self, wall):
        self._bouncesThisFlight += 1
        self.stats.bounces += 1
        if wall:
            self.stats.glassHits += 1
        self._pendingSounds.append(SoundCue.bounce)

    def _land(self, platform: Optional[Platform]):
        self._airborne = False
        was_thrown = self._thrownFlight
        self._thrownFlight = False
        self._vx = 0
        self._vy = 0
        self._standingOn = platform
        self._ignorePlatformID = None
        self.stats.mostBouncesInOneThrow = max(self.stats.mostBouncesInOneThrow, self._bouncesThisFlight)
        if platform is not None:
            self.stats.windowLandings += 1
            self._start(scr.landed_on_window())
        elif was_thrown:
            self._start(scr.dizzy())
        else:
            self._start(scr.landed(self._dropWasFar))

    # ── Items physics ────────────────────────────────────────────────────────

    def _update_items(self, dt):
        if not self.items:
            return
        g = self.config.gravity * self.height
        for i in range(len(self.items)):
            item = self.items[i]
            if item.held:
                continue
            radius = item.kind.size * self.height / 2
            if item.grounded:
                item.restingFor += dt
                if item.kind == ItemKind.ball and abs(item.vx) > 1:
                    item.position.x += item.vx * dt
                    item.vx *= pow(0.35, dt)
                    item.rotation -= item.vx * dt / max(1, radius)
                else:
                    item.vx = 0
                if item.standingOn is not None:
                    p = item.standingOn
                    now = next((pl for pl in self._platforms if pl.id == p.id), None)
                    if now is not None and now.contains(item.position.x):
                        item.position.x += (now.minX - p.minX) if abs((now.maxX - now.minX)
                                                                       - (p.maxX - p.minX)) < 1 else 0
                        item.position.y = now.y
                        item.standingOn = now
                    else:
                        item.grounded = False
                        item.standingOn = None
            else:
                item.vy -= g * dt
                previous_y = item.position.y
                item.position.x += item.vx * dt
                item.position.y += item.vy * dt
                item.rotation -= item.vx * dt / max(1, radius) * (1 if item.kind == ItemKind.ball else 0.3)
                landed = None
                if item.position.y <= self.bounds.floorY:
                    landed = (self.bounds.floorY, None)
                for p in self._platforms:
                    if (p.contains(item.position.x) and previous_y >= p.y - 0.5 and item.position.y <= p.y
                            and p.y > (landed[0] if landed else -INF)):
                        landed = (p.y, p)
                if landed is not None and item.vy <= 0:
                    y, p = landed
                    item.position.y = y
                    if abs(item.vy) > self.height * 1.2 and item.kind.restitution > 0.5:
                        item.vy = -item.vy * item.kind.restitution
                        item.vx *= 0.85
                    else:
                        item.vy = 0
                        item.grounded = True
                        item.restingFor = 0
                        item.thrownByUser = False
                        item.standingOn = p
                        if item.kind != ItemKind.ball:
                            item.vx = 0
            if (self.trashEnabled and item.thrownByUser and not item.grounded and item.vy < 0
                    and self.is_over_trash_can(item.position)
                    and item.position.y < self.bounds.floorY + self.trashCanSize * 1.2):
                self.items[i] = item
                self._binQueue.append(item.id)
                continue
            if item.position.x < self.bounds.minX or item.position.x > self.bounds.maxX:
                item.position.x = min(max(item.position.x, self.bounds.minX), self.bounds.maxX)
                item.vx = -item.vx * item.kind.restitution
            if item.position.y > self.bounds.maxY + self.height:
                item.position.y = self.bounds.maxY + self.height
                item.vy = min(0, item.vy)
            self.items[i] = item

    def _flush_bin_queue(self):
        for id in self._binQueue:
            self._swallow_into_bin(id, cheer=True)
        self._binQueue = []

    def _reachable(self, item: Item) -> bool:
        return (item.grounded and not item.held
                and abs(item.position.y - self.position.y) < self.height * 0.3)

    def _react_to_items(self):
        if not self.items or self._airborne:
            return
        food = next((it for it in self.items if it.kind.is_edible and self._reachable(it) and it.restingFor > 0.8),
                    None)
        if food is not None:
            if self.activity.state == CharacterState.sleep:
                if food.restingFor > 2.5 and self.activity.priority < Priority.direct:
                    self._targetItemID = food.id
                    self._start(scr.go_eat(food.kind, from_sleep=True))
                return
            elif self.activity.priority < Priority.rare and self._cooldown_ready("item.eat"):
                self._targetItemID = food.id
                self._start(scr.go_eat(food.kind, from_sleep=False))
            return
        if (self.focusPhase != FocusPhase.off or self.activity.state == CharacterState.sleep
                or self.activity.priority >= Priority.rare or not self._cooldown_ready("item.ball")):
            return
        ball = next((it for it in self.items if it.kind == ItemKind.ball and self._reachable(it)
                     and it.restingFor > 0.3 and abs(it.vx) < self.height * 1.5), None)
        if ball is None:
            return
        if self._kicksThisSession >= self._kickLimit:
            self._kicksThisSession = 0
            self._kickLimit = self.rng.randint(3, 6)
            self._start(scr.done_with_ball())
            self._cooldownUntil["item.ball"] = self.clock + 45
            return
        self._targetItemID = ball.id
        self._start(scr.play_ball(first=self._kicksThisSession == 0))

    def _perform(self, action: StepAction):
        k = action.kind
        if k == "eatTargetItem":
            if self._targetItemID is None:
                return
            i = self._item_index(self._targetItemID)
            if i is None or abs(self.items[i].position.x - self.position.x) >= self.height * 0.6:
                return
            kind = self.items[i].kind
            self.items.pop(i)
            self._targetItemID = None
            self.stats.snacks += 1
            if kind == ItemKind.pizza:
                self.needs.hunger -= 0.6
                self.needs.fun += 0.1
            elif kind == ItemKind.donut:
                self.needs.hunger -= 0.35
                self.needs.fun += 0.2
            elif kind == ItemKind.coffee:
                self.stats.coffees += 1
                self.needs.energy += 0.6
                self.needs.hunger -= 0.05
                self._hyperUntil = self.clock + 90
            self.needs.clamp()
        elif k == "kickTargetItem":
            if self._targetItemID is None:
                return
            i = self._item_index(self._targetItemID)
            if i is None or abs(self.items[i].position.x - self.position.x) >= self.height * 0.6:
                return
            self.items[i].vx = self.facing.sign * self.rng.uniform(2.5, 4.5) * self.height
            self.items[i].vy = self.rng.uniform(1.8, 3.4) * self.height
            self.items[i].grounded = False
            self.items[i].standingOn = None
            self._kicksThisSession += 1
            self.stats.kicks += 1
            self.needs.fun += 0.08
            self.needs.clamp()
        elif k == "wear":
            self.wear(action.accessory, action.seconds)
        elif k == "jumpOff":
            self._launch(self.facing.sign * 1.6 * self.height, 2.4 * self.height, False)
        elif k == "throwRope":
            target = self._ropeTarget
            p = next((pl for pl in self._platforms if target is not None and pl.id == target.id), None)
            if target is None or p is None or not p.contains(self.position.x):
                self._speak(scr.always(LC.noWindows))
                self._abort_activity()
                return
            self._ropeTarget = p
            self._ropePlatformID = p.id
            self._rope = RopeState(Point(self.position.x, p.y), 0)
        elif k == "attachRopeAndStepOff":
            p = self._standingOn
            if p is None:
                self._abort_activity()
                return
            left = self.position.x - p.minX < p.maxX - self.position.x
            edge = (p.minX + self.height * 0.04) if left else (p.maxX - self.height * 0.04)
            self._ropeTarget = p
            self._ropePlatformID = p.id
            self._rope = RopeState(Point(edge, p.y), 1)
            self.position.x = min(max((p.minX - self.height * 0.16) if left else (p.maxX + self.height * 0.16),
                                      self.bounds.minX), self.bounds.maxX)
            self._standingOn = None
            self._ignorePlatformID = p.id
        elif k == "coilRope":
            self._rope = None
            self._ropePlatformID = None
            self._ropeTarget = None
        elif k == "pickUpTarget":
            if self._targetItemID is None:
                self._abort_activity()
                return
            i = self._item_index(self._targetItemID)
            if i is None:
                self._abort_activity()
                return
            self._carriedItem = self.items[i].kind
            self.items.pop(i)
            self._targetItemID = None
        elif k == "dumpCarried":
            if self._carriedItem is not None:
                self._carriedItem = None
                self._pendingBinHit = True
                self._pendingSounds.append(SoundCue.thud)

    # ── Steps ────────────────────────────────────────────────────────────────

    def _walk_limits(self) -> Tuple[float, float, bool, bool]:
        p = self._standingOn
        if p is None:
            return (self.bounds.minX, self.bounds.maxX, False, False)
        inset = self.height * 0.12
        lo = max(self.bounds.minX, p.minX + inset)
        hi = min(self.bounds.maxX, p.maxX - inset)
        if lo > hi:
            lo = self.position.x
            hi = self.position.x
        return (lo, hi, p.minX + inset > self.bounds.minX, p.maxX - inset < self.bounds.maxX)

    def _advance(self, dt):
        if not self._stepStarted:
            self._begin_step()
        if self._airborne:
            return
        if self.stepIndex >= len(self.activity.steps):
            self._choose_next()
            return
        step = self.activity.steps[self.stepIndex]
        self._stepElapsed += dt
        limits = self._walk_limits()

        if self._nudgeRate != 0:
            self.position.x = min(max(self.position.x + self._nudgeRate * dt, limits[0]), limits[1])

        if self._walkItemStopShort is not None:
            if self._targetItemID is None:
                self._abort_activity()
                return
            item = next((it for it in self.items if it.id == self._targetItemID), None)
            if item is None or item.held:
                self._abort_activity()
                return
            side = 1.0 if item.position.x >= self.position.x else -1.0
            self._walkTargetX = item.position.x - side * self._walkItemStopShort * self.height
            self.facing = Facing.right if side > 0 else Facing.left

        if step.climb is not None:
            if self._rope is None:
                self._abort_activity()
                return
            speed = step.speed * self.height * (1.5 if self.isHyper else 1)
            self.gaitPhase += speed * dt / self.height
            if step.climb == scr.ClimbDirection.up:
                goal = max(self.position.y, self._rope.anchor.y - self.height * 0.72)
                self.position.y = min(goal, self.position.y + speed * dt)
                if self.position.y >= goal - 0.5:
                    self.position.y = self._rope.anchor.y
                    self._standingOn = next((pl for pl in self._platforms if pl.id == self._ropePlatformID), None)
                    self._next_step()
            else:
                goal = self._climbTargetY if self._climbTargetY is not None else self.bounds.floorY
                self.position.y = max(goal, self.position.y - speed * dt)
                if self.position.y <= goal + 0.5:
                    landing = self._ground_below(self.position.x, self._rope.anchor.y, self._ropePlatformID)
                    self.position.y = landing[0]
                    self._standingOn = landing[1]
                    self._ignorePlatformID = None
                    self._next_step()
            return

        if self._walkTargetX is not None:
            target = self._walkTargetX
            speed = step.speed * self.height * (1.5 if self.isHyper else 1)
            direction = 1.0 if target >= self.position.x else -1.0
            nxt = self.position.x + direction * speed * dt
            if (direction > 0 and nxt >= target) or (direction < 0 and nxt <= target):
                nxt = target
            self.gaitPhase += speed * dt / self.height
            clamped = min(max(nxt, limits[0]), limits[1])
            self.stats.distance += abs(clamped - self.position.x) / self.height
            self.position.x = clamped
            if clamped != nxt or (self._walkExpectsWall and clamped == target):
                side = Facing.left if clamped <= limits[0] + 0.5 else Facing.right
                is_ledge = limits[2] if side is Facing.left else limits[3]
                if is_ledge:
                    self._hit_ledge(side)
                else:
                    self._hit_wall()
                return
            if abs(self.position.x - target) < 0.5:
                self._next_step()
        elif self._stepElapsed >= self._stepDuration:
            self._next_step()

    def _begin_step(self):
        self._stepStarted = True
        self._stepElapsed = 0
        self._walkTargetX = None
        self._walkExpectsWall = False
        self._walkItemStopShort = None
        self._nudgeRate = 0
        if self.stepIndex >= len(self.activity.steps):
            return
        step = self.activity.steps[self.stepIndex]
        if step.pose is not None:
            self.pose = step.pose
        if step.facing is not None:
            self.facing = self._resolve_facing(step.facing)
        self._stepDuration = self.rng.pick(step.duration)
        self.effects = set(step.effects)
        if step.walk is not None:
            if step.walk.kind == "item":
                self._walkItemStopShort = step.walk.stop_short
                self._walkTargetX = self.position.x
            else:
                target = self._resolve_walk(step.walk)
                self._walkTargetX = target[0]
                self._walkExpectsWall = target[1]
                if abs(target[0] - self.position.x) > 0.5:
                    direction = Facing.right if target[0] > self.position.x else Facing.left
                    self.facing = direction.opposite if step.backwards else direction
        if step.nudge != 0 and self._stepDuration > 0:
            self._nudgeRate = self.facing.sign * step.nudge * self.height / self._stepDuration
        self._climbTargetY = None
        if step.climb == scr.ClimbDirection.down and self._rope is not None:
            self._climbTargetY = self._ground_below(self.position.x, self._rope.anchor.y, self._ropePlatformID)[0]
        if step.climb == scr.ClimbDirection.up:
            self._standingOn = None
        if step.line is not None:
            self._speak(step.line)
        if step.sound is not None:
            self._pendingSounds.append(step.sound)
        if step.action is not None:
            self._perform(step.action)

    def _next_step(self):
        self.stepIndex += 1
        self._stepStarted = False
        if self.stepIndex >= len(self.activity.steps):
            self._choose_next()
        else:
            self._begin_step()

    def _abort_activity(self):
        self._targetItemID = None
        self._start(scr.idle_stand())

    def _hit_wall(self):
        self._walkTargetX = None
        self._walkItemStopShort = None
        if self.activity.id != "glassWall" and self._cooldown_ready("glassWall"):
            self.facing = self._resolve_facing(FacingRule.towardNearestEdge)
            self._start(scr.glass_wall())
            self._begin_step()
        else:
            self._next_step()

    def _hit_ledge(self, side: Facing):
        self._walkTargetX = None
        self._walkItemStopShort = None
        if not self.activity.id.startswith("perch.") and self._cooldown_ready("perch.ledge"):
            self._cooldownUntil["perch.ledge"] = self.clock + self.config.cooldown("perch.ledge")
            self._start(scr.ledge(side, self.rng))
            self._begin_step()
        else:
            self._next_step()

    def _start(self, new_activity: Activity):
        self.activity = new_activity
        self.stepIndex = 0
        self._stepStarted = False
        self._walkTargetX = None
        self._walkItemStopShort = None
        self._nudgeRate = 0
        self.effects = set()
        if not new_activity.id.startswith("item."):
            self._targetItemID = None
        if self._carriedItem is not None and new_activity.id != "item.tidy":
            kind = self._carriedItem
            self._carriedItem = None
            dropped = Item(id=self._nextItemID, kind=kind,
                           position=Point(self.position.x, self.position.y + self.height * 0.4))
            dropped.vy = self.height
            self._nextItemID += 1
            self.items.append(dropped)
        if not new_activity.id.startswith("rope.") and self._rope is not None:
            self._rope = None
            self._ropePlatformID = None
            self._ropeTarget = None
        group = self.group_of(new_activity.id)
        self._cooldownUntil[group] = self.clock + self.config.cooldown(group)
        self._recentGroups.append(group)
        if len(self._recentGroups) > 6:
            self._recentGroups.pop(0)
        self._count_stats(new_activity)

    def _count_stats(self, a: Activity):
        if a.state == CharacterState.sleep:
            self.stats.naps += 1
        elif a.state == CharacterState.panic and a.id.startswith("panic"):
            self.stats.panics += 1
        elif a.state == CharacterState.glassWall:
            self.stats.glassHits += 1
        elif a.state == CharacterState.work:
            self.stats.workSessions += 1
        elif a.state == CharacterState.celebration:
            self.stats.celebrations += 1
        if a.id.startswith("rare."):
            try:
                event = revents.RareEvent(a.id[5:])
            except ValueError:
                event = None
            if event is not None:
                if event.is_fourth_wall:
                    self.stats.fourthWallEvents += 1
                if event == revents.RareEvent.selfMeeting:
                    self.stats.meetings += 1

    def _check_achievements(self):
        if self.clock - self._lastAchievementCheck <= 1:
            return
        self._lastAchievementCheck = self.clock
        for a in ALL_ACHIEVEMENTS:
            if a.id not in self.unlockedAchievements and a.is_unlocked(self.stats):
                self.unlockedAchievements.add(a.id)
                self._pendingAchievements.append(a)
                self._achievementsToCelebrate += 1

    def _choose_next(self):
        if self.focusPhase == FocusPhase.focus:
            self._start(scr.quiet_work() if self.rng.chance(0.8) else scr.idle_shift_weight())
            self._begin_step()
            return
        if self.isAway and self._cooldown_ready("sleep.away"):
            self._start(scr.away_sleep())
            self._begin_step()
            return
        sleep_factor = (0.6 if self.mood == Mood.sleepy else 1) \
            * (0.5 if (self.needsEnabled and self.needs.energy < 0.25) else 1)
        if (self.focusPhase == FocusPhase.off and not self.isHyper
                and self.clock - self._lastAttention > self.config.sleepAfter * sleep_factor
                and self._cooldown_ready("sleep")):
            self._start(scr.sleep())
            self._begin_step()
            return
        edge_distance = min(self.position.x - self.bounds.minX, self.bounds.maxX - self.position.x) / self.height
        context = revents.RareEventContext(
            cursorDistance=self._cursorDistance, edgeDistance=edge_distance,
            areaWidth=self.bounds.width / self.height, mood=self.mood,
            fourthWallEnabled=self.fourthWallEnabled)
        if self.focusPhase == FocusPhase.off:
            event = self.rare.pick(self.clock, context, self.rng)
            if event is not None:
                self._start(revents.activity_for_event(event, self.rng))
                self._begin_step()
                return
        if (self.awarenessEnabled and self.focusPhase == FocusPhase.off and self._cooldown_ready("aware.time")
                and self.rng.chance(0.06)):
            category = self._time_of_day_category()
            if category is not None:
                self._start(scr.say(category, "aware.time"))
                self._begin_step()
                return
        if self._achievementsToCelebrate > 0:
            self._achievementsToCelebrate = 0
            self._start(scr.achievement_unlocked())
            self._begin_step()
            return

        idle_for = self.clock - self._lastAttention
        boredom = 2.0 if idle_for > 30 else 1.0
        limits = self._walk_limits()
        room_to_walk = limits[1] - limits[0] > self.height * 1.5
        hyper = 1.0 if self.isHyper else 0.0
        resting = self.focusPhase == FocusPhase.rest
        options = [
            (scr.idle_stand, "idle.stand", 3 * (1 - 0.7 * hyper)),
            (scr.idle_look_around, "idle.lookAround", 2.5),
            (scr.idle_shift_weight, "idle.shiftWeight", 2),
            (scr.idle_pockets, "idle.pockets", 1.2),
            (scr.yawn, "bored", 1.0 * boredom * (1 - hyper)),
            (scr.stretch, "bored", 0.8 * boredom * (3 if resting else 1)),
            (scr.sit_down, "bored", 1.0 * boredom * (3 if resting else 1) * (1 - hyper)),
            (scr.stare_at_user, "bored", 0.9 * boredom),
            (scr.work, "work", 0 if resting else 0.9 * (1 + hyper)),
            (scr.celebration, "celebration", 0.25 * (1 + hyper)),
            (scr.party_celebration, "celebration", 0.12 * (1 + hyper)),
        ]
        if self.needsEnabled:
            if self.needs.hunger > 0.75:
                options.append((scr.hungry_complaint, "need.hungry", 2.5))
            if self.needs.energy < 0.25:
                options.append((scr.tired_complaint, "need.tired", 2))
        if self.trashEnabled and self._cooldown_ready("item.tidy") and self._standingOn is None:
            leftover = next((it for it in self.items if self._reachable(it) and it.restingFor > 75), None)
            if leftover is not None:
                def make_tidy(_id=leftover.id):
                    self._targetItemID = _id
                    return scr.tidy_up()
                options.append((make_tidy, "item.tidy", 4))
        if self.ropeEnabled and self.gravityEnabled:
            if self._cooldown_ready("rope.climb"):
                plan = self._climb_plan()
                if plan is not None:
                    def make_climb(_plan=plan):
                        self._ropeTarget = _plan[0]
                        return scr.rope_climb(_plan[1])
                    options.append((make_climb, "rope.climb", 1.5 * (1 + hyper)))
            if self._standingOn is not None and self._cooldown_ready("rope.down"):
                plan = self._rappel_plan(self._standingOn)
                if plan is not None:
                    def make_rappel(_plan=plan):
                        return scr.rappel(_plan[0], _plan[1])
                    options.append((make_rappel, "rope.down", 1.2))
        if room_to_walk:
            options.append((scr.wander, "idle.wander", 3 * (1 + hyper)))
            options.append((scr.try_to_leave, "idle.tryToLeave", 0 if resting else 0.7))
            if self.isHyper:
                options.append((scr.hyper_zoom, "need.hyper", 4))

        weighted = []
        for make, group, base in options:
            if not self._cooldown_ready(group):
                continue
            weight = base * self._mood_weight(group)
            if self._recentGroups and self._recentGroups[-1] == group:
                weight *= 0.25
            weighted.append((make, weight))
        make = weighted_pick(weighted, self.rng) or scr.idle_stand
        self._start(make())
        self._begin_step()

    def _time_of_day_category(self):
        h, d = self._environment.hour, self._environment.weekday
        if d == 1 or d == 7:
            return LC.weekend
        if d == 6 and h >= 12:
            return LC.friday
        if 5 <= h < 11:
            return LC.morning
        if 12 <= h < 14:
            return LC.lunch
        if h == 23 or 0 <= h < 5:
            return LC.lateNight
        return None

    def _mood_weight(self, group: str) -> float:
        pair = (self.mood, group)
        table = {
            (Mood.sleepy, "bored"): 2,
            (Mood.sleepy, "idle.wander"): 0.5, (Mood.sleepy, "work"): 0.5,
            (Mood.smug, "celebration"): 1.8, (Mood.smug, "work"): 1.8,
            (Mood.dramatic, "idle.tryToLeave"): 2.5,
            (Mood.chipper, "idle.wander"): 1.6, (Mood.chipper, "work"): 1.6,
            (Mood.grumpy, "idle.pockets"): 1.4, (Mood.grumpy, "bored"): 1.4,
        }
        return table.get(pair, 1)

    def _cooldown_ready(self, group: str) -> bool:
        until = self._cooldownUntil.get(group)
        if until is None:
            return True
        return self.clock >= until

    @staticmethod
    def group_of(id: str) -> str:
        prefix_groups = {"panic", "bored", "cursor", "click", "rare"}
        first = id.split(".")[0] if "." in id else None
        if first is not None and first in prefix_groups:
            return first
        return id

    def _speak(self, request: LineRequest):
        if request.kind == "maybe":
            if self.focusPhase == FocusPhase.focus:
                return
            text = self.dialogue.line(request.category, now=self.clock, chance=request.chance, rng=self.rng)
            if text is not None:
                self._pendingSpeech = text
        elif request.kind == "always":
            if self.clock - self._lastForcedLineAt <= 0.9:
                return
            text = self.dialogue.line(request.category, now=self.clock, force=True, rng=self.rng)
            if text is not None:
                self._pendingSpeech = text
                self._lastForcedLineAt = self.clock
        elif request.kind == "text":
            self.dialogue.record(request.text, None, self.clock)
            self._pendingSpeech = request.text
            self._lastForcedLineAt = self.clock

    def _resolve_walk(self, target: scr.WalkTarget) -> Tuple[float, bool]:
        limits = self._walk_limits()
        left, right = limits[0], limits[1]

        def clamp(x):
            return min(max(x, left), right)

        nearest_is_left = (self.position.x - left) < (right - self.position.x)
        k = target.kind
        if k == "randomSpot":
            for _ in range(4):
                x = self.rng.uniform(left, max(left, right))
                if abs(x - self.position.x) > self.height:
                    return (x, False)
            return (clamp(self.position.x + (self.height if nearest_is_left else -self.height)), False)
        if k == "offset":
            direction = 1.0 if self.rng.chance(0.5) else -1.0
            distance = self.rng.uniform(target.lo, target.hi) * self.height
            if ((direction > 0 and self.position.x + distance > right)
                    or (direction < 0 and self.position.x - distance < left)):
                direction = -direction
            return (clamp(self.position.x + direction * distance), False)
        if k == "awayFromCursor":
            cursor_x = self._cursorPoint.x if self._cursorPoint is not None else (self.position.x - 1)
            direction = 1.0 if cursor_x <= self.position.x else -1.0
            return (self.position.x + direction * self.rng.uniform(target.lo, target.hi) * self.height, False)
        if k == "towardCursor":
            if self._cursorPoint is None:
                return (self.position.x, False)
            cursor_x = self._cursorPoint.x
            direction = 1.0 if cursor_x >= self.position.x else -1.0
            x = cursor_x - direction * target.stop_short * self.height
            safe = max(self.position.x, x) if direction > 0 else min(self.position.x, x)
            return (clamp(safe), False)
        if k == "nearestEdge":
            return (left if nearest_is_left else right, False)
        if k == "throughNearestEdge":
            return (left if nearest_is_left else right, True)
        if k == "awayFromEdge":
            distance = self.rng.uniform(target.lo, target.hi) * self.height
            return (clamp(self.position.x + distance if nearest_is_left else self.position.x - distance), False)
        if k == "item":
            return (self.position.x, False)
        if k == "x":
            return (clamp(target.value), False)
        if k == "trashCan":
            return (clamp(self.trash_can_position.x - self.trashCanSize * 0.5 - self.height * 0.15), False)
        return (self.position.x, False)

    def _resolve_facing(self, rule: FacingRule) -> Facing:
        nearest_is_left = (self.position.x - self.bounds.minX) < (self.bounds.maxX - self.position.x)
        if rule == FacingRule.left:
            return Facing.left
        if rule == FacingRule.right:
            return Facing.right
        if rule == FacingRule.flip:
            return self.facing.opposite
        if rule == FacingRule.random:
            return Facing.left if self.rng.chance(0.5) else Facing.right
        if rule == FacingRule.towardCursor:
            if self._cursorPoint is None:
                return self.facing
            return Facing.right if self._cursorPoint.x >= self.position.x else Facing.left
        if rule == FacingRule.awayFromCursor:
            if self._cursorPoint is None:
                return self.facing
            return Facing.left if self._cursorPoint.x >= self.position.x else Facing.right
        if rule == FacingRule.towardNearestEdge:
            return Facing.left if nearest_is_left else Facing.right
        if rule == FacingRule.awayFromNearestEdge:
            return Facing.right if nearest_is_left else Facing.left
        return self.facing

    def _make_frame(self, frame_pose: Pose, state: CharacterState) -> BrainFrame:
        frame = BrainFrame(
            position=self.position.copy(), state=state,
            activityID="dragged" if self.isDragging else self.activity.id,
            pose=frame_pose, facing=self.facing, stepTime=self._stepElapsed,
            stepDuration=self._stepDuration if self._walkTargetX is None else 0,
            gaitPhase=self.gaitPhase, isWalking=self._walkTargetX is not None and not self.isDragging,
            effects=({Effect.sweat} if self.isDragging else set(self.effects)),
            speech=self._pendingSpeech, sounds=list(self._pendingSounds), mood=self.mood)
        if self._airborne:
            frame.stepTime = self.clock
        if self.isHyper and not self._airborne and not self.isDragging:
            frame.effects.add(Effect.caffeine)
        frame.accessories = {a for a, t in self._accessoryUntil.items() if t > self.clock}
        frame.isPerched = self._standingOn is not None
        frame.isHyper = self.isHyper
        frame.binHit = self._pendingBinHit
        self._pendingBinHit = False
        frame.carriedEmoji = self._carriedItem.emoji if self._carriedItem is not None else None
        if self._rope is not None:
            r = RopeState(self._rope.anchor.copy(), self._rope.reach)
            if self.stepIndex < len(self.activity.steps):
                step = self.activity.steps[self.stepIndex]
                if step.action is not None and step.action.kind == "throwRope" and self._stepDuration > 0:
                    r.reach = min(1.0, self._stepElapsed / (self._stepDuration * 0.7))
            frame.rope = r
        if self._pendingAchievements and not self.isDragging and not self._airborne:
            frame.achievement = self._pendingAchievements.pop(0)
        self._pendingSpeech = None
        self._pendingSounds = []
        return frame
