"""Small deterministic RNG (SplitMix64) + weighted picker — port of Random.swift."""
from __future__ import annotations

import math
import random as _random
from typing import List, Optional, Sequence, Tuple, TypeVar

_MASK = 0xFFFFFFFFFFFFFFFF
T = TypeVar("T")


class SeededRandom:
    """SplitMix64. Matches the Swift generator so behavior is reproducible if seeded."""

    def __init__(self, seed: Optional[int] = None):
        if seed is None:
            seed = _random.getrandbits(64) or 1
        self.state = seed & _MASK

    def next_u64(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & _MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK
        return z ^ (z >> 31)

    # --- conveniences mirroring the Swift RandomNumberGenerator extension ---

    def unit(self) -> float:
        """A Double in [0, 1), the same construction Swift uses for Double.random."""
        return (self.next_u64() >> 11) * (2.0 ** -53)

    def chance(self, p: float) -> bool:
        return self.unit() < p

    def uniform(self, lo: float, hi: float) -> float:
        if lo == hi:
            return lo
        return lo + (hi - lo) * self.unit()

    def pick(self, rng_range: Tuple[float, float]) -> float:
        lo, hi = rng_range
        return self.uniform(lo, hi)

    def randint(self, lo: int, hi: int) -> int:
        """Inclusive, like Swift's Int.random(in: lo...hi)."""
        if hi <= lo:
            return lo
        return lo + int(self.unit() * (hi - lo + 1))

    def choice(self, seq: Sequence[T]) -> T:
        return seq[int(self.unit() * len(seq))]

    def shuffle(self, items: list) -> None:
        for i in range(len(items) - 1, 0, -1):
            j = int(self.unit() * (i + 1))
            items[i], items[j] = items[j], items[i]


def weighted_pick(items: List[Tuple[T, float]], rng: SeededRandom) -> Optional[T]:
    """Weighted random selection. Items with weight <= 0 are never chosen."""
    valid = [(v, w) for (v, w) in items if w > 0 and math.isfinite(w)]
    total = sum(w for _, w in valid)
    if total <= 0:
        return None
    roll = rng.unit() * total
    for v, w in valid:
        if roll < w:
            return v
        roll -= w
    return valid[-1][0] if valid else None
