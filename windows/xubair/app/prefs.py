"""User preferences + saved life data, persisted as JSON in %APPDATA%/Xubair — port of Preferences.swift."""
from __future__ import annotations

import json
import os
import time
from typing import Optional, Tuple

from ..core.stats import Stats
from ..core.world import Needs

SCALE_RANGE = (0.4, 3.0)
SPEED_RANGE = (0.5, 2.0)

DEFAULTS = {
    "characterScale": 1.0,
    "animationSpeed": 1.0,
    "soundEnabled": True,
    "volume": 0.5,
    "paused": False,
    "reduceEffects": False,
    "alwaysOnTop": True,
    "gravity": True,
    "talkativeness": 0.6,
    "rareEventFrequency": 1.0,
    "fourthWall": True,
    "hasSeenWelcome": False,
    "isHidden": False,
    "perchOnWindows": True,
    "awareness": True,
    "needsEnabled": True,
    "ropeClimbing": True,
    "keepDroppedFiles": True,
    "pocketRing": True,
    "trashCan": False,
}


def _config_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    d = os.path.join(base, "Xubair")
    os.makedirs(d, exist_ok=True)
    return d


class Preferences:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.path.join(_config_dir(), "prefs.json")
        self._data = dict(DEFAULTS)
        self._data["stats"] = {}
        self._data["needs"] = {}
        self._data["unlocked"] = []
        self._data["hireDate"] = None
        self._data["lastGreetingDay"] = None
        self._data["lastSeen"] = None
        self._data["savedX"] = None
        self._data["savedY"] = None
        self._load()

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                stored = json.load(f)
            if isinstance(stored, dict):
                self._data.update(stored)
        except (OSError, ValueError):
            pass
        if self._data.get("hireDate") is None:
            self._data["hireDate"] = time.time()
            self.save()

    def save(self):
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp, self.path)
        except OSError:
            pass

    # scalar accessors
    def __getattr__(self, name):
        # only reached for names not set as real attributes
        data = self.__dict__.get("_data", {})
        if name in data:
            return data[name]
        raise AttributeError(name)

    def set(self, key: str, value):
        self._data[key] = value
        self.save()

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    # life data
    @property
    def stats(self) -> Stats:
        return Stats.from_dict(self._data.get("stats") or {})

    @stats.setter
    def stats(self, value: Stats):
        self._data["stats"] = value.to_dict()

    @property
    def needs(self) -> Needs:
        return Needs.from_dict(self._data.get("needs") or {})

    @needs.setter
    def needs(self, value: Needs):
        self._data["needs"] = value.to_dict()

    @property
    def unlocked_achievements(self) -> set:
        return set(self._data.get("unlocked") or [])

    @unlocked_achievements.setter
    def unlocked_achievements(self, value: set):
        self._data["unlocked"] = sorted(value)

    @property
    def saved_position(self) -> Optional[Tuple[float, float]]:
        x = self._data.get("savedX")
        y = self._data.get("savedY")
        if x is None or y is None:
            return None
        return (x, y)

    @saved_position.setter
    def saved_position(self, value: Optional[Tuple[float, float]]):
        if value is None:
            self._data["savedX"] = None
            self._data["savedY"] = None
        else:
            self._data["savedX"], self._data["savedY"] = value

    def reset_to_defaults(self):
        for k, v in DEFAULTS.items():
            if k in ("hasSeenWelcome", "isHidden"):
                continue
            self._data[k] = v
        self.save()
