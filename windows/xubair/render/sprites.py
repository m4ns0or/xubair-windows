"""Loads the generated sprites and pre-computes how the pieces fit together —
a Python/Pillow port of SpriteLibrary.swift.

Each body view is split into legs (below the hoodie hem) and torso (headless upper body);
heads (own head or an expression head) are aligned to the body by matching pupil positions
recorded in sprites.json. All coordinates below are kept in the Swift convention:
image pixels are top-down, but anchor/pivot/eyes/crown are unit or pixel values with y UP.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from PIL import Image

from ..core.types import BodyView, FaceExpression, Facing

WAIST = 0.62
OVERLAP_ROWS = 8


@dataclass
class Head:
    image: Image.Image          # native-resolution RGBA, already mirrored if flipped
    size: Tuple[float, float]   # displayed size in body px (hw*s, hh*s)
    anchor: Tuple[float, float] # neck pivot, unit coords of the head image, y UP
    pivot: Tuple[float, float]  # neck pivot in torso-image px, y UP from torso bottom
    eyes: List[Tuple[float, float]]  # pupils, unit coords of head image, y UP, left->right
    crown: Tuple[float, float]  # hat spot, unit coords, y UP


@dataclass
class ViewSet:
    torso: Image.Image
    legs: Image.Image
    torso_size: Tuple[int, int]
    legs_size: Tuple[int, int]
    overlap: float
    body_height: float
    body_width: float
    heads: Dict[FaceExpression, Head] = field(default_factory=dict)

    def head(self, expression: FaceExpression) -> Optional[Head]:
        return self.heads.get(expression) or self.heads.get(FaceExpression.neutral)


class SpriteLibraryError(Exception):
    pass


class SpriteLibrary:
    def __init__(self, directory: str):
        self.directory = directory
        meta_path = os.path.join(directory, "sprites.json")
        with open(meta_path, "r", encoding="utf-8") as f:
            self._manifest = json.load(f)["sprites"]
        self._images: Dict[str, Image.Image] = {}
        for name, info in self._manifest.items():
            path = os.path.join(directory, info["file"])
            if os.path.exists(path):
                self._images[name] = Image.open(path).convert("RGBA")
        self.sets: Dict[Tuple[BodyView, bool], ViewSet] = {}
        for view in BodyView:
            for flipped in (False, True):
                self.sets[(view, flipped)] = self._build_set(view, flipped)

    @staticmethod
    def default_directory() -> Optional[str]:
        """Sprites next to the frozen exe, bundled by PyInstaller, or in the source tree."""
        import sys
        candidates = []
        base = getattr(sys, "_MEIPASS", None)
        if base:
            candidates.append(os.path.join(base, "Sprites"))
        here = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(os.path.dirname(os.path.dirname(here)), "Sprites"))
        # repo layout: windows/Sprites, and DesktopFreeloader/Resources/Sprites
        candidates.append(os.path.join(os.path.dirname(os.path.dirname(here)), "..", "Resources", "Sprites"))
        for c in candidates:
            if os.path.exists(os.path.join(c, "sprites.json")):
                return os.path.abspath(c)
        return None

    def set(self, view: BodyView, flipped: bool) -> ViewSet:
        return self.sets[(view, flipped)]

    @staticmethod
    def needs_flip(view: BodyView, facing: Facing) -> bool:
        """Native facing of each sheet sprite: side faces right, three-quarter faces left."""
        if view is BodyView.side:
            return facing is Facing.left
        if view is BodyView.threeQuarter:
            return facing is Facing.right
        return False

    # ── building ──────────────────────────────────────────────────────────────

    def _image(self, name: str) -> Image.Image:
        img = self._images.get(name)
        if img is None:
            raise SpriteLibraryError("Missing character asset: %s" % name)
        return img

    def _build_set(self, requested: BodyView, flipped: bool) -> ViewSet:
        view = requested if ("body_%s" % requested.value.lower()) in self._images else BodyView.front
        body_name = "body_%s" % view.value.lower()
        has_head = (("%s_torso" % body_name) in self._images
                    and self._manifest.get(body_name, {}).get("eyes") is not None)
        body = self._image(("%s_torso" % body_name) if has_head else body_name)
        if flipped:
            body = body.transpose(Image.FLIP_LEFT_RIGHT)
        width, height = body.width, body.height
        waist_row = round(height * WAIST)
        overlap = OVERLAP_ROWS
        # Image pixels are top-down: the head/torso is the TOP of the image, legs the bottom.
        torso = body.crop((0, 0, width, int(waist_row + overlap)))
        legs = body.crop((0, int(waist_row), width, height))

        heads: Dict[FaceExpression, Head] = {}
        if has_head and body_name in self._manifest:
            body_info = self._manifest[body_name]
            if view is BodyView.front:
                sources = {
                    FaceExpression.neutral: "head_front", FaceExpression.bored: "face_bored",
                    FaceExpression.shocked: "face_shocked", FaceExpression.annoyed: "face_annoyed",
                    FaceExpression.smug: "face_smug", FaceExpression.sleepy: "face_sleepy",
                    FaceExpression.worried: "face_worried",
                }
            else:
                sources = {FaceExpression.neutral: "head_%s" % view.value.lower()}
            for expression, name in sources.items():
                info = self._manifest.get(name)
                if info is None or info.get("eyes") is None or info.get("chinY") is None:
                    continue
                heads[expression] = self._place_head(name, info, body_info, waist_row + overlap, flipped)

        return ViewSet(torso=torso, legs=legs, torso_size=(width, int(waist_row + overlap)),
                       legs_size=(width, int(height - waist_row)), overlap=overlap,
                       body_height=height, body_width=width, heads=heads)

    def _place_head(self, name, info, body, torso_height, flipped) -> Head:
        head_image = self._image(name)
        hw, hh, bw = float(info["width"]), float(info["height"]), float(body["width"])

        def mirror_x(x, w):
            return (w - x) if flipped else x

        h_eyes = [[mirror_x(e[0], hw), e[1]] for e in info["eyes"]]
        b_eyes = [[mirror_x(e[0], bw), e[1]] for e in body["eyes"]]
        if flipped:
            head_image = head_image.transpose(Image.FLIP_LEFT_RIGHT)

        def mid(e):
            return ((e[0][0] + e[1][0]) / 2, (e[0][1] + e[1][1]) / 2)

        def span(e):
            return math.hypot(e[1][0] - e[0][0], e[1][1] - e[0][1])

        hmx, hmy = mid(h_eyes)
        bmx, bmy = mid(b_eyes)
        s = span(b_eyes) / max(1.0, span(h_eyes))
        chin = float(info["chinY"])
        pivot_x = bmx
        pivot_y_top = bmy + (chin - hmy) * s
        eyes = sorted([(e[0] / hw, 1 - e[1] / hh) for e in h_eyes], key=lambda p: p[0])
        return Head(image=head_image, size=(hw * s, hh * s),
                    anchor=(hmx / hw, 1 - chin / hh),
                    pivot=(pivot_x, torso_height - pivot_y_top),
                    eyes=eyes, crown=(hmx / hw, 0.93))
