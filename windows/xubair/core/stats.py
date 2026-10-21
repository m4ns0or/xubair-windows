"""Lifetime counters + achievements — port of Stats.swift."""
from __future__ import annotations

from dataclasses import dataclass, asdict, fields
from typing import Callable


@dataclass
class Stats:
    pokes: int = 0
    naps: int = 0
    panics: int = 0
    glassHits: int = 0
    throwCount: int = 0
    bounces: int = 0
    mostBouncesInOneThrow: int = 0
    snacks: int = 0
    coffees: int = 0
    kicks: int = 0
    distance: float = 0.0  # in his own heights
    fourthWallEvents: int = 0
    filesInspected: int = 0
    focusSessions: int = 0
    meetings: int = 0
    windowLandings: int = 0
    workSessions: int = 0
    celebrations: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Stats":
        s = cls()
        if isinstance(d, dict):
            for f in fields(cls):
                if f.name in d:
                    try:
                        s.__dict__[f.name] = type(getattr(s, f.name))(d[f.name])
                    except (TypeError, ValueError):
                        pass
        return s


@dataclass
class Achievement:
    id: str
    emoji: str
    title: str
    detail: str
    target: int
    value: Callable[[Stats], int]

    def progress(self, stats: Stats) -> float:
        return min(1.0, self.value(stats) / max(1, self.target))

    def is_unlocked(self, stats: Stats) -> bool:
        return self.value(stats) >= self.target


ALL_ACHIEVEMENTS = [
    Achievement("poke", "👉", "Poke Master", "Poke him 25 times.", 25, lambda s: s.pokes),
    Achievement("flyer", "✈️", "Frequent Flyer", "Throw him 10 times.", 10, lambda s: s.throwCount),
    Achievement("pinball", "🎯", "Pinball Wizard", "4 bounces in a single throw.", 4,
                lambda s: s.mostBouncesInOneThrow),
    Achievement("nap", "😴", "Professional Napper", "Take 5 naps.", 5, lambda s: s.naps),
    Achievement("glass", "🪟", "Glass Ceiling", "Hit the invisible wall 10 times.", 10, lambda s: s.glassHits),
    Achievement("snack", "🍕", "Snack Attack", "Eat 10 snacks.", 10, lambda s: s.snacks),
    Achievement("coffee", "☕️", "Caffeine Dependency", "Drink 5 coffees.", 5, lambda s: s.coffees),
    Achievement("striker", "⚽️", "Striker", "Kick the ball 20 times.", 20, lambda s: s.kicks),
    Achievement("marathon", "🏃", "Marathon of Nothing", "Walk 500 body lengths.", 500, lambda s: int(s.distance)),
    Achievement("meta", "🎭", "Meta", "Break the fourth wall 15 times.", 15, lambda s: s.fourthWallEvents),
    Achievement("paperwork", "📎", "Paperwork", "Hand him 5 files.", 5, lambda s: s.filesInspected),
    Achievement("deepwork", "🧠", "Deep Work (Yours)", "Finish a focus session.", 1, lambda s: s.focusSessions),
    Achievement("pomodoro", "🍅", "Pomodoro Pro", "Finish 10 focus sessions.", 10, lambda s: s.focusSessions),
    Achievement("penthouse", "🏙️", "Penthouse Suite", "Land him on top of a window.", 1, lambda s: s.windowLandings),
    Achievement("scaredy", "😱", "Scaredy Cat", "Make him panic 20 times.", 20, lambda s: s.panics),
    Achievement("selfemployed", "📊", "Self-Employed", "He holds 3 meetings with himself.", 3, lambda s: s.meetings),
    Achievement("workaholic", "⌨️", "Workaholic (Allegedly)", "Pretend to work 25 times.", 25,
                lambda s: s.workSessions),
]
