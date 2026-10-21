"""Finds the visible top edges of other apps' windows so he can stand on them — a Windows
port of PlatformScanner (Sensors.swift). Only window *rectangles* are read (EnumWindows +
GetWindowRect): no titles, no contents, no screenshots, and it needs no special permissions.
"""
from __future__ import annotations

import ctypes
import sys
from typing import List, Set, Tuple

from ..core.world import Platform

IS_WIN = sys.platform.startswith("win")

GWL_EXSTYLE = -20
GWL_STYLE = -16
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_MINIMIZE = 0x20000000


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class PlatformScanner:
    def __init__(self):
        self.platforms: List[Platform] = []
        self._last_scan = 0.0

    def clear(self):
        self.platforms = []

    def refresh_if_needed(self, now: float, interval: float, height: float,
                          work: Tuple[int, int, int, int], own_hwnds: Set[int]):
        if now - self._last_scan < interval:
            return
        self._last_scan = now
        self.platforms = self._scan(height, work, own_hwnds)

    def _scan(self, height: float, work, own_hwnds: Set[int]) -> List[Platform]:
        if not IS_WIN:
            return []
        wl, wt, wr, wb = work
        user32 = ctypes.windll.user32
        windows: List[Tuple[int, int, int, int, int]] = []  # (hwnd, left, top, right, bottom)
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def cb(hwnd, _):
            h = int(hwnd) if hwnd else 0
            if h in own_hwnds:
                return True
            if not user32.IsWindowVisible(hwnd):
                return True
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            if style & WS_MINIMIZE:
                return True
            ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if ex & WS_EX_TOOLWINDOW:
                return True
            if user32.GetWindowTextLengthW(hwnd) <= 0:
                return True
            r = RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
                return True
            windows.append((h, r.left, r.top, r.right, r.bottom))
            return True

        user32.EnumWindows(WNDENUMPROC(cb), 0)

        result: List[Platform] = []
        for i, (hwnd, left, top, right, bottom) in enumerate(windows):
            w = right - left
            ht = bottom - top
            if w < height * 0.8 or ht < 40:
                continue
            # Window top must have head-room below the work-area top and sit above the floor.
            if top > wb - height * 1.05 or top < wt + height * 0.3:
                continue
            # Subtract parts hidden behind windows in front (earlier in z-order).
            segments: List[Tuple[float, float]] = [(float(left), float(right))]
            for (_, fl, ftop, fr, fbottom) in windows[:i]:
                if ftop < top - 1 and fbottom > top - 1:
                    new_segs = []
                    for a, b in segments:
                        c, d = float(fl), float(fr)
                        if d <= a or c >= b:
                            new_segs.append((a, b))
                            continue
                        if c > a:
                            new_segs.append((a, c))
                        if d < b:
                            new_segs.append((d, b))
                    segments = new_segs
            base_id = (hwnd & 0x0FFFFFFF) * 16
            for k, (a, b) in enumerate(sorted(segments)):
                if b - a < height * 0.6:
                    continue
                # Convert screen px (top-down) to brain coords (y up, origin at work-area floor/left).
                result.append(Platform(id=base_id + k, minX=a - wl, maxX=b - wl, y=wb - top))
        return result
