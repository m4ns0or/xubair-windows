"""Things in the world around him — port of World.swift."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Set

from .types import AutoName, Point


@dataclass
class Platform:
    """A horizontal surface he can stand on — the visible top edge of another window."""

    id: int
    minX: float
    maxX: float
    y: float

    def contains(self, x: float) -> bool:
        return self.minX <= x <= self.maxX


class MemoryPressure(Enum):
    normal = auto()
    warning = auto()
    critical = auto()


class ClipboardContentType(Enum):
    url = auto()
    stackTrace = auto()
    errorCode = auto()
    other = auto()
    unchanged = auto()


@dataclass
class Environment:
    """Local, read-only facts about the user's PC. Nothing here leaves the device."""

    userIdleSeconds: float = 0.0
    batteryLevel: Optional[float] = None
    isCharging: Optional[bool] = None
    batteryTimeToEmptyMinutes: Optional[float] = None
    hour: int = 12
    weekday: int = 3  # 1 (Sunday) ... 7 (Saturday)
    cpuLoad: float = 0.0
    memoryPressure: MemoryPressure = MemoryPressure.normal
    runningAppCount: int = 0
    detectedBundleIDs: Set[str] = field(default_factory=set)
    buildProcessRunning: bool = False
    clipboardType: ClipboardContentType = ClipboardContentType.other


class FileKind(AutoName):
    image = auto()
    pdf = auto()
    code = auto()
    archive = auto()
    audio = auto()
    video = auto()
    text = auto()
    spreadsheet = auto()
    presentation = auto()
    folder = auto()
    app = auto()
    other = auto()
    many = auto()


class ItemKind(AutoName):
    pizza = auto()
    coffee = auto()
    donut = auto()
    ball = auto()

    @property
    def is_edible(self) -> bool:
        return self is not ItemKind.ball

    @property
    def emoji(self) -> str:
        return {
            ItemKind.pizza: "🍕",
            ItemKind.coffee: "☕️",
            ItemKind.donut: "🍩",
            ItemKind.ball: "⚽️",
        }[self]

    @property
    def display_name(self) -> str:
        return {
            ItemKind.pizza: "Pizza",
            ItemKind.coffee: "Coffee",
            ItemKind.donut: "Donut",
            ItemKind.ball: "Ball",
        }[self]

    @property
    def size(self) -> float:
        return 0.2 if self is ItemKind.ball else 0.22

    @property
    def restitution(self) -> float:
        return 0.68 if self is ItemKind.ball else 0.22


@dataclass
class Item:
    """A snack or toy on the desktop. Position is the bottom-centre, global screen points."""

    id: int
    kind: ItemKind
    position: Point
    vx: float = 0.0
    vy: float = 0.0
    rotation: float = 0.0
    grounded: bool = False
    held: bool = False
    restingFor: float = 0.0
    standingOn: Optional[Platform] = None
    thrownByUser: bool = False


@dataclass
class Needs:
    """Simple needs that drift over time. 0 = fine, 1 = urgent (energy: 1 = rested)."""

    hunger: float = 0.2
    energy: float = 0.8
    fun: float = 0.5

    def clamp(self) -> None:
        self.hunger = min(1.0, max(0.0, self.hunger))
        self.energy = min(1.0, max(0.0, self.energy))
        self.fun = min(1.0, max(0.0, self.fun))

    def to_dict(self) -> dict:
        return {"hunger": self.hunger, "energy": self.energy, "fun": self.fun}

    @classmethod
    def from_dict(cls, d: dict) -> "Needs":
        n = cls()
        if isinstance(d, dict):
            n.hunger = float(d.get("hunger", n.hunger))
            n.energy = float(d.get("energy", n.energy))
            n.fun = float(d.get("fun", n.fun))
        return n
