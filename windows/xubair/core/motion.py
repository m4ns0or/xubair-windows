"""Procedural animation — port of Motion.swift.

Turns a static sprite into a living character with transforms only (squash/stretch,
lean, bob, tilt). Distances are in character heights; angles in radians, CCW positive
(so the renderer, which draws y-down, negates rotations).
Values describe a character facing RIGHT; the renderer mirrors x/rotation when facing left.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .types import MotionKind

PI = math.pi


@dataclass
class RigPose:
    bodyX: float = 0.0
    bodyY: float = 0.0
    bodyRotation: float = 0.0
    scaleX: float = 1.0
    scaleY: float = 1.0
    torsoRotation: float = 0.0
    torsoY: float = 0.0
    legsScaleY: float = 1.0
    headRotation: float = 0.0
    headX: float = 0.0
    headY: float = 0.0
    shadowScale: float = 1.0

    @property
    def is_finite(self) -> bool:
        return all(math.isfinite(v) for v in (
            self.bodyX, self.bodyY, self.bodyRotation, self.scaleX, self.scaleY,
            self.torsoRotation, self.torsoY, self.legsScaleY, self.headRotation,
            self.headX, self.headY, self.shadowScale))


def _ease(x: float) -> float:
    return 1 - (1 - min(1.0, max(0.0, x))) ** 3


def _ease_in(x: float) -> float:
    return min(1.0, max(0.0, x)) ** 2.2


def _ease_in_out(x: float) -> float:
    v = min(1.0, max(0.0, x))
    return 4 * v * v * v if v < 0.5 else 1 - ((-2 * v + 2) ** 3) / 2


def sample(kind: MotionKind, t: float, duration: float, gait: float = 0.0, intensity: float = 1.0) -> RigPose:
    r = RigPose()
    p = min(1.0, max(0.0, t / duration)) if duration > 0 else 0.0
    a = intensity

    def wave(hz: float, phase: float = 0.0) -> float:
        return math.sin(2 * PI * hz * t + phase)

    bump = math.sin(PI * p)
    lying = PI / 2

    def breathe(amount: float = 1.0) -> None:
        r.scaleY += 0.008 * amount * a * wave(0.3)
        r.torsoY += 0.003 * amount * a * wave(0.3, 0.5)
        r.headRotation += 0.02 * amount * a * wave(0.17, 1)

    def lie(q: float) -> None:
        r.bodyRotation = lying * q
        r.bodyX = 0.48 * q
        r.bodyY = 0.17 * q

    K = MotionKind
    if kind == K.still:
        pass
    elif kind == K.breathe:
        breathe()
    elif kind == K.lookAround:
        breathe()
        r.headRotation += 0.09 * a * wave(0.45)
        r.torsoRotation = 0.015 * a * wave(0.45, 0.4)
    elif kind == K.shiftWeight:
        r.bodyRotation = 0.03 * a * wave(0.32)
        r.bodyX = 0.012 * a * wave(0.32)
        r.headRotation = -0.035 * a * wave(0.32, 0.3)
        breathe(0.5)
    elif kind == K.pocketCheck:
        r.torsoRotation = 0.07 * a * wave(1.3) * bump
        r.torsoY = -0.012 * bump
        r.headRotation = 0.12 * a * bump * (1 if wave(0.6) > 0 else -1)
        r.headY = -0.008 * bump
    elif kind == K.yawn:
        r.scaleY = 1 + 0.045 * a * bump
        r.scaleX = 1 - 0.02 * a * bump
        r.headRotation = 0.14 * a * bump
        r.torsoRotation = 0.03 * a * bump
    elif kind == K.stretch:
        r.scaleY = 1 + 0.06 * a * bump
        r.scaleX = 1 - 0.025 * a * bump
        r.torsoRotation = 0.1 * a * wave(0.8) * bump
        r.headRotation = -0.08 * a * wave(0.8) * bump
    elif kind == K.sitDown:
        r.legsScaleY = 1 - 0.48 * _ease(p)
        r.torsoRotation = -0.05 * bump
    elif kind == K.sit:
        r.legsScaleY = 0.52
        breathe()
        r.headRotation += 0.05 * a * wave(0.12)
    elif kind == K.standUp:
        r.legsScaleY = 0.52 + 0.48 * _ease(p)
        r.torsoRotation = -0.06 * bump
    elif kind == K.stare:
        q = _ease(min(1.0, t / 0.6))
        r.scaleX = 1 + 0.03 * q
        r.scaleY = 1 + 0.03 * q
        r.headRotation = 0.04 * q
        breathe(0.6)
    elif kind == K.walk:
        cycle = gait * 3.4
        r.bodyY = 0.022 * a * abs(math.sin(PI * cycle))
        r.bodyRotation = -0.035 + 0.025 * a * math.sin(2 * PI * cycle)
        r.headRotation = 0.03 * a * math.sin(2 * PI * cycle + 0.8)
        r.scaleY = 1 - 0.012 * a * math.cos(2 * PI * cycle)
    elif kind == K.run:
        cycle = gait * 2.4
        r.bodyY = 0.06 * a * abs(math.sin(PI * cycle))
        r.bodyRotation = -0.14 + 0.05 * a * math.sin(2 * PI * cycle)
        r.headRotation = 0.06 * a * math.sin(2 * PI * cycle + 1.1)
        r.scaleY = 1 - 0.03 * a * math.cos(2 * PI * cycle)
        r.scaleX = 1 + 0.015 * a * math.cos(2 * PI * cycle)
    elif kind == K.stumble:
        fall = _ease(p / 0.45) if p < 0.45 else 1 - _ease((p - 0.45) / 0.55)
        r.bodyRotation = -0.55 * fall
        r.bodyX = 0.08 * fall
        r.headRotation = 0.2 * fall
        r.scaleY = 1 - 0.06 * fall
    elif kind == K.hide:
        r.legsScaleY = 0.62
        r.torsoRotation = -0.12
        r.headRotation = -0.08
        r.bodyX = 0.005 * a * wave(9)
        r.scaleX = 0.96
    elif kind == K.pant:
        r.torsoY = 0.012 * a * wave(2.8)
        r.torsoRotation = -0.06
        r.headRotation = 0.05 * a * wave(2.8, 0.5)
        r.scaleY = 1 + 0.012 * a * wave(2.8)
    elif kind == K.bonk:
        hit = p / 0.25 if p < 0.25 else max(0.0, 1 - (p - 0.25) / 0.75)
        r.bodyX = 0.05 * hit
        r.scaleX = 1 - 0.1 * (bump if p < 0.35 else 0)
        r.bodyRotation = 0.16 * (math.sin(PI * (p - 0.25) / 0.75) if p > 0.25 else 0)
        r.headRotation = 0.15 * a * math.sin(2 * PI * 4 * t) * (1 - p)
    elif kind == K.pressGlass:
        r.bodyX = 0.035
        r.bodyRotation = -0.08
        r.scaleX = 0.93 + 0.02 * a * wave(1.4)
        r.headRotation = -0.06 + 0.03 * a * wave(0.7)
        r.torsoRotation = -0.04 * a * wave(1.4, 1)
    elif kind == K.push:
        strain = _ease(min(1.0, t / 0.4))
        r.bodyRotation = -0.26 * strain
        r.bodyX = 0.05 * strain
        r.scaleX = 1 - 0.05 * strain
        r.bodyY = 0.004 * a * wave(13)
        r.headRotation = -0.1 * strain + 0.02 * a * wave(9)
    elif kind == K.knock:
        r.bodyRotation = -0.05
        r.torsoRotation = -0.07 * max(0.0, math.sin(2 * PI * 3 * t)) * (1 if t < 1.2 else 0)
        r.headRotation = -0.03
    elif kind == K.inspect:
        r.headRotation = 0.16 * a * wave(0.35)
        r.bodyY = 0.012 * max(0.0, wave(0.35, 0.6))
        r.bodyX = 0.02 * a * wave(0.2)
        r.torsoRotation = -0.04
    elif kind == K.lookUp:
        r.headRotation = 0.22 * _ease(min(1.0, t / 0.5))
        r.scaleY = 1 + 0.02 * _ease(min(1.0, t / 0.5))
        r.bodyY = 0.006 * a * max(0.0, wave(0.8))
    elif kind == K.lieDown:
        lie(_ease_in_out(p))
    elif kind == K.sleeping:
        lie(1)
        r.scaleX = 1 + 0.025 * a * wave(0.22)
        r.headRotation = 0.04 * a * wave(0.22, 0.8)
    elif kind == K.getUp:
        q = 1 - _ease_in_out(p)
        lie(q)
        r.scaleY = 1 + 0.03 * bump
    elif kind == K.faint:
        wobble = math.sin(2 * PI * 3 * t) * 0.08 * a if p < 0.35 else 0
        fall = 0 if p < 0.35 else _ease_in((p - 0.35) / 0.65)
        lie(fall)
        r.bodyRotation += wobble
        r.headRotation = 0.2 * (1 - fall) * a * math.sin(2 * PI * 2 * t)
    elif kind == K.typing:
        r.torsoRotation = -0.05
        r.torsoY = 0.005 * a * wave(7)
        r.headRotation = 0.04 * a * wave(1.2) - 0.04
        r.bodyX = 0.003 * a * wave(3.5)
    elif kind == K.celebrate:
        r.bodyY = 0.11 * a * abs(math.sin(2 * PI * 1.4 * t))
        r.scaleY = 1 + 0.04 * a * abs(math.sin(2 * PI * 1.4 * t))
        r.bodyRotation = 0.07 * a * wave(1.4)
        r.headRotation = -0.1 * a * wave(1.4)
    elif kind == K.victoryDance:
        r.bodyRotation = 0.16 * a * wave(2)
        r.bodyY = 0.08 * a * abs(math.sin(2 * PI * 2 * t))
        r.bodyX = 0.06 * a * wave(0.9)
        r.headRotation = -0.15 * a * wave(2)
        r.torsoRotation = 0.08 * a * wave(4)
        r.scaleY = 1 + 0.03 * a * wave(4)
    elif kind == K.nod:
        r.headRotation = -0.05 + 0.06 * a * max(0.0, math.sin(2 * PI * 1.6 * t))
        r.headY = -0.006 * a * max(0.0, math.sin(2 * PI * 1.6 * t))
        breathe(0.5)
    elif kind == K.shrug:
        r.torsoY = 0.02 * bump
        r.headRotation = 0.12 * bump
        r.scaleX = 1 + 0.02 * bump
    elif kind == K.spin:
        r.scaleX = math.cos(2 * PI * _ease_in_out(p))
        r.bodyY = 0.06 * bump
    elif kind == K.wiggle:
        r.bodyRotation = 0.1 * a * wave(4) * (1 - p)
        r.scaleY = 1 + 0.03 * a * wave(8) * (1 - p)
        r.headRotation = -0.1 * a * wave(4) * (1 - p)
    elif kind == K.dangle:
        r.bodyRotation = 0.13 * a * wave(0.9)
        r.legsScaleY = 1.04
        r.headRotation = -0.06 * a * wave(0.9, 0.7)
        r.scaleX = 0.98
    elif kind == K.fall:
        r.scaleY = 1.06
        r.scaleX = 0.96
        r.bodyRotation = 0.06 * a * wave(3)
        r.headRotation = 0.08 * a * wave(3, 1)
    elif kind == K.land:
        squash = math.sin(PI * min(1.0, p * 1.6))
        r.scaleY = 1 - 0.18 * squash
        r.scaleX = 1 + 0.12 * squash
        r.legsScaleY = 1 - 0.1 * squash
    elif kind == K.flinch:
        r.bodyX = -0.04 * bump
        r.bodyRotation = 0.12 * bump
        r.scaleY = 1 - 0.05 * bump
        r.headRotation = 0.1 * bump
    elif kind == K.jump:
        r.bodyY = 0.32 * bump
        r.scaleY = 1 + 0.08 * bump - (0.1 * math.sin(PI * (p - 0.9) / 0.1) if p > 0.9 else 0)
        r.scaleX = 1 - 0.04 * bump
    elif kind == K.wakeJolt:
        up = math.sin(PI * p / 0.45) if p < 0.45 else 0
        r.bodyY = 0.38 * up
        r.bodyRotation = 0.12 * a * wave(6) * (1 - p)
        r.scaleY = 1 + 0.1 * up
        r.headRotation = 0.15 * a * wave(5) * (1 - p)
    elif kind == K.freeze:
        r.scaleY = 1.02
        r.bodyX = 0.003 * a * wave(16)
        r.headRotation = 0.02
    elif kind == K.lookAtCursor:
        q = _ease(min(1.0, t / 0.35))
        r.bodyRotation = -0.03 * q
        r.headRotation = -0.05 * q + 0.02 * a * wave(0.6)
        breathe(0.5)
    elif kind == K.sizeCheck:
        r.scaleY = 1 + 0.05 * a * wave(2.2) * (1 - p)
        r.scaleX = 1 - 0.03 * a * wave(2.2) * (1 - p)
        r.headRotation = 0.12 * a * wave(1)
    elif kind == K.tumble:
        angle = 2 * PI * 1.4 * t
        r.bodyRotation = angle
        r.bodyX = 0.5 * math.sin(angle)
        r.bodyY = 0.5 - 0.5 * math.cos(angle)
        r.headRotation = 0.1 * a * wave(4)
    elif kind == K.dizzy:
        r.bodyRotation = 0.12 * a * wave(0.8)
        r.bodyX = 0.03 * a * wave(0.8, PI / 2)
        r.headRotation = 0.16 * a * wave(0.8, 1)
        r.torsoRotation = -0.05 * a * wave(0.8, 2)
    elif kind == K.chomp:
        r.headRotation = -0.05 + 0.07 * a * abs(math.sin(2 * PI * 3 * t))
        r.headY = -0.008 * abs(math.sin(2 * PI * 3 * t))
        r.torsoRotation = -0.04
        r.scaleY = 1 + 0.01 * a * wave(3)
    elif kind == K.kick:
        rot = 0.1 * _ease(p / 0.4) if p < 0.4 else 0.1 - 0.32 * _ease((p - 0.4) / 0.6)
        r.bodyRotation = rot
        r.bodyY = 0.04 * bump
        r.headRotation = -0.06 * bump
    elif kind == K.patBelly:
        r.torsoRotation = 0.03 * a * wave(1.2)
        r.scaleX = 1 + 0.03 * a * (0.5 + 0.5 * wave(1.2))
        r.headRotation = 0.06
        breathe(0.5)
    elif kind == K.peekLedge:
        r.bodyRotation = -0.18 + 0.03 * a * wave(0.7)
        r.bodyX = 0.03
        r.headRotation = -0.15
        r.scaleY = 1 - 0.01 * a * wave(0.7)
    elif kind == K.wave:
        r.bodyRotation = 0.06 * a * wave(2)
        r.headRotation = 0.08 * a * wave(2, 1)
        r.bodyY = 0.02 * a * abs(math.sin(2 * PI * 2 * t))
    elif kind == K.hyper:
        r.bodyX = 0.012 * a * wave(11)
        r.bodyY = 0.03 * a * abs(math.sin(2 * PI * 5 * t))
        r.scaleY = 1 + 0.03 * a * wave(10)
        r.headRotation = 0.05 * a * wave(7)
    elif kind == K.holdItem:
        r.torsoRotation = -0.03
        r.headRotation = -0.08 + 0.04 * a * wave(0.5)
        breathe(0.6)
    elif kind == K.climb:
        r.bodyRotation = 0.06 * a * math.sin(2 * PI * 1.6 * t)
        r.bodyX = 0.012 * a * math.sin(2 * PI * 1.6 * t + 0.5)
        r.scaleY = 1 + 0.025 * a * math.sin(2 * PI * 3.2 * t)
        r.legsScaleY = 0.94 + 0.05 * a * math.sin(2 * PI * 1.6 * t + 1.2)
    elif kind == K.ropeSwing:
        r.torsoRotation = 0.12 * a * wave(1.8)
        r.bodyRotation = 0.04 * a * wave(1.8, 0.4)
        r.scaleY = 1 + 0.02 * a * wave(3.6)
    elif kind == K.throwRope:
        r.scaleY = 1 + 0.07 * bump
        r.bodyY = 0.05 * bump
        r.torsoRotation = -0.06 * bump
    elif kind == K.tug:
        jerk = max(0.0, math.sin(2 * PI * 2.5 * t))
        r.bodyRotation = 0.08 * jerk
        r.bodyY = -0.01 * jerk
        r.scaleY = 1 - 0.03 * jerk
    elif kind == K.mantle:
        r.bodyY = -0.62 * (1 - _ease(p))
        r.legsScaleY = 0.7 + 0.3 * _ease(p)
        r.bodyRotation = -0.12 * (1 - p)
    elif kind == K.carry:
        cycle = gait * 4.2
        r.bodyRotation = 0.07 + 0.02 * a * math.sin(2 * PI * cycle)
        r.torsoRotation = 0.06
        r.bodyY = 0.012 * a * abs(math.sin(PI * cycle))
        r.scaleY = 0.98 - 0.015 * a * math.cos(2 * PI * cycle)
        r.headRotation = -0.04
    elif kind == K.strain:
        r.legsScaleY = 0.86 + 0.04 * a * wave(6)
        r.torsoRotation = 0.08
        r.bodyX = 0.006 * a * wave(14)
        r.scaleY = 0.96
        r.headRotation = -0.06 + 0.03 * a * wave(9)
    elif kind == K.holdSign:
        r.scaleY = 1.03
        r.bodyRotation = 0.03 * a * wave(0.8)
        r.headRotation = 0.04 * a * wave(0.6, 1)
        r.bodyY = 0.01 * a * abs(math.sin(2 * PI * 0.8 * t))
    elif kind == K.knockScreen:
        knock = max(0.0, math.sin(2 * PI * 3 * t)) * (1 if t < 1.1 else 0)
        r.scaleX = 1 + 0.07 * knock
        r.scaleY = 1 + 0.07 * knock
        r.torsoRotation = -0.04 * knock

    r.shadowScale = max(0.45, 1 - r.bodyY * 1.6) * (1.6 if abs(r.bodyRotation) > 1 else 1)
    return r
