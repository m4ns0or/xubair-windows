"""Main application: wires the behavior brain, renderer, window, sensors and menu together.
Port of the orchestration in CharacterController.swift / StatusBarController.swift / main.swift.
"""
from __future__ import annotations

import ctypes
import os
import sys
import time
import tkinter as tk
from typing import List, Optional, Tuple

from ..core.brain import BehaviorConfig, CharacterBrain, WorldInput
from ..core.rare_events import RareEvent
from ..core.types import Bounds, Point
from ..core.world import ItemKind
from .platforms import PlatformScanner
from .prefs import SCALE_RANGE, SPEED_RANGE, Preferences
from .sensors import EnvironmentSensor, classify_files
from .tray import Tray
from .window import CharacterWindow
from ..render import FrameRenderer
from ..render.sprites import SpriteLibrary

BASE_HEIGHT = 150.0
SIZE_PRESETS = [("Tiny", 0.4), ("Small", 0.7), ("Normal", 1.0), ("Big", 1.6), ("Giant", 3.0)]
IS_WIN = sys.platform.startswith("win")


def _work_area() -> Tuple[int, int, int, int]:
    """(left, top, right, bottom) of the primary monitor work area (excludes the taskbar)."""
    if IS_WIN:
        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
        r = RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0):  # SPI_GETWORKAREA
            return (r.left, r.top, r.right, r.bottom)
    return (0, 0, 1440, 820)


def _make_root() -> tk.Tk:
    """Create the Tk root, with tkinterdnd2 drag-drop support when available."""
    try:
        from tkinterdnd2 import TkinterDnD
        return TkinterDnD.Tk()
    except Exception:
        return tk.Tk()


def _cursor_pos() -> Optional[Tuple[int, int]]:
    if IS_WIN:
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        pt = POINT()
        if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
            return (pt.x, pt.y)
    return None


class Application:
    def __init__(self):
        self.prefs = Preferences()
        self.root = _make_root()
        self.root.withdraw()
        try:
            self.root.title("Xubair")
        except tk.TclError:
            pass

        directory = SpriteLibrary.default_directory()
        if not directory:
            raise SystemExit("Could not find the Sprites folder next to the app.")
        self.library = SpriteLibrary(directory)
        self.renderer = FrameRenderer(self.library, reduce_effects=self.prefs.reduceEffects)

        wl, wt, wr, wb = _work_area()
        self._work = (wl, wt, wr, wb)
        config = BehaviorConfig()
        start = self.prefs.saved_position or (float((wr - wl) // 2), 60.0)
        self.brain = CharacterBrain(Point(*start), config=config)
        self.brain.stats = self.prefs.stats
        self.brain.needs = self.prefs.needs
        self.brain.unlockedAchievements = set(self.prefs.unlocked_achievements)
        self._apply_prefs_to_brain()

        self.window = CharacterWindow(self.root)
        self._wire_window()
        self.window.enable_file_drop(self._on_files_dropped)
        self.sensors = EnvironmentSensor()
        self.scanner = PlatformScanner()
        self._own_hwnds = set()

        self._last_tick = time.monotonic()
        self._last_env = 0.0
        self._last_save = 0.0
        self._focus_deadline: Optional[float] = None
        self._break_deadline: Optional[float] = None
        self._running = True
        self._hidden = bool(self.prefs.isHidden)

        if self._hidden:
            self.window.hide()
        self.window.set_topmost(self.prefs.alwaysOnTop)

        # Greet once a day.
        try:
            self.brain.update_environment(self.sensors.sample())
        except Exception:
            pass
        self.brain.greet()

        self._menu = self._build_menu()
        self.tray = self._make_tray()
        if self.tray is not None:
            self.tray.start()
        self.root.after(0, self._tick)

    def _make_tray(self) -> Optional[Tray]:
        try:
            icon = self._tray_icon_image()
            actions = {
                "Show Xubair": lambda: (self._hidden and self.toggle_hidden()),
                "Hide Xubair": lambda: ((not self._hidden) and self.toggle_hidden()),
                "Poke Him": self.poke,
                "-": None,
                "Pause Movement": lambda: self._toggle("paused"),
                "Keep Above Other Apps": self.toggle_on_top,
                "Reset Position": self.reset_position,
                "--": None,
                "Feed (Pizza)": lambda: self.brain.spawn_item(ItemKind.pizza),
                "Toss a Ball": lambda: self.brain.spawn_item(ItemKind.ball),
                "---": None,
                "Quit Xubair": self.quit,
            }
            tray = Tray(icon, actions)
            return tray if tray.available() else None
        except Exception:
            return None

    def _tray_icon_image(self):
        from ..core.brain import BrainFrame
        from ..core.types import (BodyView, CharacterState, FaceExpression, Facing, Mood,
                                   MotionKind, Pose)
        from ..render.compositor import compose
        from ..core.motion import sample as sample_motion
        f = BrainFrame(position=Point(0, 0), state=CharacterState.idle, activityID="icon",
                       pose=Pose(BodyView.front, FaceExpression.smug, MotionKind.breathe),
                       facing=Facing.right, stepTime=0.3, stepDuration=1.0, gaitPhase=0.0,
                       isWalking=False, effects=set(), speech=None, sounds=[], mood=Mood.grumpy)
        rig = sample_motion(MotionKind.breathe, t=0.3, duration=1.0)
        comp = compose(f, rig, self.library, 56.0)
        bbox = comp.image.getbbox() or (0, 0, comp.image.width, comp.image.height)
        return comp.image.crop(bbox)

    # ── geometry ──────────────────────────────────────────────────────────────

    def _bounds(self) -> Bounds:
        wl, wt, wr, wb = self._work
        floor_pad = 4.0
        return Bounds(0, float(wr - wl), 0, float(wb - wt - floor_pad))

    def _brain_to_screen(self, p: Point) -> Tuple[int, int]:
        wl, wt, wr, wb = self._work
        return (int(round(wl + p.x)), int(round(wb - p.y)))

    def _screen_to_brain(self, sx: float, sy: float) -> Point:
        wl, wt, wr, wb = self._work
        return Point(sx - wl, wb - sy)

    # ── window wiring ───────────────────────────────────────────────────────────

    def _wire_window(self):
        w = self.window
        w.feet_on_screen = lambda: Point(*self._brain_to_screen(self.brain.position))
        w.on_click = self.brain.handle_click
        w.on_double_click = lambda: self.brain.open_pocket(0)
        w.on_begin_drag = self.brain.begin_drag
        w.on_drag = lambda scr: self.brain.drag(self._screen_to_brain(scr.x, scr.y))
        w.on_end_drag = self._end_drag
        w.on_right_click = self._popup_menu
        w.on_pinch = self._pinch
        w.on_file_hover = lambda entered: (self.brain.file_hover_began() if entered
                                           else self.brain.file_hover_ended())

    def _end_drag(self, velocity_screen: Point):
        # Screen velocity is y-down; brain y is up, so negate y.
        self.brain.end_drag(Point(velocity_screen.x, -velocity_screen.y))

    def _pinch(self, amount: float):
        self.set_scale(self.prefs.characterScale * (1 + amount))

    def _on_files_dropped(self, paths: List[str]):
        if self._hidden:
            self.toggle_hidden()
        kind = classify_files(paths)
        total = 0
        for p in paths:
            try:
                total += os.path.getsize(p)
            except OSError:
                pass
        if self.prefs.keepDroppedFiles:
            self.brain.receive_files(kind, True, total, _human_size(total))
        else:
            self.brain.inspect_file(kind)

    # ── main loop ───────────────────────────────────────────────────────────────

    def _tick(self):
        if not self._running:
            return
        now = time.monotonic()
        dt = now - self._last_tick
        self._last_tick = now

        if self.tray is not None:
            self.tray.pump()

        # Environment every ~2s.
        if now - self._last_env > 2.0:
            self._last_env = now
            try:
                self.brain.update_environment(self.sensors.sample())
            except Exception:
                pass

        self._check_focus(now)

        height = BASE_HEIGHT * self.prefs.characterScale
        cur = _cursor_pos()
        cursor = self._screen_to_brain(*cur) if cur else None
        speed = 0.0 if self.prefs.paused else self.prefs.animationSpeed
        platforms = self._scan_platforms(now, height)
        frame = self.brain.tick(WorldInput(dt=dt, bounds=self._bounds(), cursor=cursor,
                                           height=height, speed=speed, platforms=platforms))

        for cue in frame.sounds:
            self._play_sound(cue)
        if frame.achievement is not None:
            self.renderer.say("🏆 " + frame.achievement.title, now)

        if not self._hidden:
            res = self.renderer.render(frame, height, now=now)
            feet_screen = self._brain_to_screen(self.brain.position)
            self.window.update_frame(res.image, res.feet, res.hit_rect, feet_screen)

        # Persist every ~15s.
        if now - self._last_save > 15:
            self._last_save = now
            self._persist()

        delay = int(1000 / self._target_fps(frame))
        self.root.after(delay, self._tick)

    def _target_fps(self, frame) -> int:
        from ..core.types import CharacterState
        if self.prefs.paused:
            return 12
        if frame.state in (CharacterState.sleep,):
            return 12
        if frame.isWalking or self.brain.isHyper or frame.state in (
                CharacterState.thrown, CharacterState.falling, CharacterState.dragged,
                CharacterState.panic, CharacterState.climbing, CharacterState.playing):
            return 30
        return 20

    def _scan_platforms(self, now: float, height: float):
        if not (self.prefs.perchOnWindows and self.prefs.gravity) or self._hidden:
            self.scanner.clear()
            return []
        if not self._own_hwnds:
            try:
                self._own_hwnds = {int(self.window.top.winfo_id()), int(self.root.winfo_id())}
            except Exception:
                self._own_hwnds = set()
        from ..core.types import CharacterState
        fast = (self.brain.isPerched or self.brain.state in (
            CharacterState.climbing, CharacterState.thrown, CharacterState.falling))
        interval = 0.3 if fast else 1.0
        self.scanner.refresh_if_needed(now, interval, height, self._work, self._own_hwnds)
        return self.scanner.platforms

    def _check_focus(self, now: float):
        if self._focus_deadline is not None and now >= self._focus_deadline:
            self._focus_deadline = None
            minutes = 5 if self._focus_minutes == 25 else 10
            self.brain.complete_focus()
            self._break_deadline = now + minutes * 60
        if self._break_deadline is not None and now >= self._break_deadline:
            self._break_deadline = None
            self.brain.end_break()

    # ── preferences ───────────────────────────────────────────────────────────

    def _apply_prefs_to_brain(self):
        p = self.prefs
        b = self.brain
        b.gravityEnabled = p.gravity
        b.fourthWallEnabled = p.fourthWall
        b.needsEnabled = p.needsEnabled
        b.awarenessEnabled = p.awareness
        b.ropeEnabled = p.ropeClimbing
        b.trashEnabled = p.trashCan
        b.dialogue.talkativeness = p.talkativeness
        b.rare.frequency = p.rareEventFrequency

    def set_scale(self, scale: float):
        scale = max(SCALE_RANGE[0], min(SCALE_RANGE[1], scale))
        bigger = scale > self.prefs.characterScale
        self.prefs.set("characterScale", scale)
        self.brain.notice_resize(bigger)

    # ── menu actions ────────────────────────────────────────────────────────────

    def _build_menu(self) -> tk.Menu:
        return self._fresh_menu()

    def _fresh_menu(self) -> tk.Menu:
        p = self.prefs
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="Xubair", state="disabled")
        n = self.brain.needs
        m.add_command(label="Mood: %s" % self.brain.mood.display_name, state="disabled")
        if p.needsEnabled:
            m.add_command(label="🍕 Hunger %s   ⚡ Energy %s" % (_bar(n.hunger), _bar(n.energy)), state="disabled")
        m.add_separator()
        m.add_command(label="Show Xubair" if self._hidden else "Hide Xubair", command=self.toggle_hidden)
        m.add_checkbutton(label="Pause Movement", command=lambda: self._toggle("paused"))
        m.add_checkbutton(label="Mute Sounds", command=lambda: self._toggle("soundEnabled"))
        m.add_checkbutton(label="Keep Him Above Other Apps", command=self.toggle_on_top)
        m.add_separator()
        m.add_command(label="Poke Him", command=self.poke)

        size = tk.Menu(m, tearoff=0)
        size.add_command(label="Bigger", command=lambda: self.set_scale(self.prefs.characterScale + 0.15))
        size.add_command(label="Smaller", command=lambda: self.set_scale(self.prefs.characterScale - 0.15))
        size.add_separator()
        for name, sc in SIZE_PRESETS:
            size.add_command(label="%s  (%d%%)" % (name, int(sc * 100)), command=lambda s=sc: self.set_scale(s))
        m.add_cascade(label="Size", menu=size)

        m.add_command(label="🪢  Climb a Window",
                      command=self.brain.climb_somewhere,
                      state=("normal" if (p.perchOnWindows and p.gravity) else "disabled"))
        if self.brain.isPerched:
            m.add_command(label="🪢  Rappel Down", command=self.brain.rappel_down)

        feed = tk.Menu(m, tearoff=0)
        for kind in (ItemKind.pizza, ItemKind.coffee, ItemKind.donut):
            feed.add_command(label="%s  %s" % (kind.emoji, kind.display_name),
                             command=lambda k=kind: self.brain.spawn_item(k))
        m.add_cascade(label="Feed Him", menu=feed)
        m.add_command(label="⚽️  Toss a Ball", command=lambda: self.brain.spawn_item(ItemKind.ball))
        if self.brain.items:
            m.add_command(label="🗑️  Throw Away All Snacks & Toys", command=self.brain.remove_all_items)
        m.add_checkbutton(label="Show Trash Can", command=lambda: self._toggle("trashCan", apply=True))

        focus = tk.Menu(m, tearoff=0)
        if self._focus_deadline is not None or self._break_deadline is not None:
            focus.add_command(label="Stop Focus Session", command=self.stop_focus)
        else:
            focus.add_command(label="Start 25-Minute Focus", command=lambda: self.start_focus(25))
            focus.add_command(label="Start 50-Minute Focus", command=lambda: self.start_focus(50))
        m.add_cascade(label="Focus Buddy", menu=focus)
        m.add_command(label="Performance Review…", command=self.open_review)
        m.add_command(label="⏰  Remind Me…", command=self.remind_me)
        m.add_command(label="🎒  His Pocket…", command=lambda: self.brain.open_pocket(0))
        m.add_command(label="Reset Position", command=self.reset_position)

        settings = tk.Menu(m, tearoff=0)
        for label, key in [("Gravity", "gravity"), ("Fourth-wall antics", "fourthWall"),
                           ("Needs (hunger/energy)", "needsEnabled"), ("Real-world awareness", "awareness"),
                           ("Rope climbing", "ropeClimbing"), ("Reduce visual effects", "reduceEffects"),
                           ("Stand on windows", "perchOnWindows")]:
            settings.add_checkbutton(label=label, command=lambda k=key: self._toggle(k, apply=True))
        talk = tk.Menu(settings, tearoff=0)
        for label, val in [("Quiet", 0.2), ("Normal", 0.6), ("Chatty", 1.0)]:
            talk.add_command(label=label, command=lambda v=val: self._set_pref("talkativeness", v, apply=True))
        settings.add_cascade(label="Talkativeness", menu=talk)
        freq = tk.Menu(settings, tearoff=0)
        for label, val in [("Never", 0.0), ("Normal", 1.0), ("Often", 2.0)]:
            freq.add_command(label=label, command=lambda v=val: self._set_pref("rareEventFrequency", v, apply=True))
        settings.add_cascade(label="Rare event frequency", menu=freq)
        m.add_cascade(label="Settings", menu=settings)

        rare = tk.Menu(m, tearoff=0)
        for ev in RareEvent:
            rare.add_command(label=ev.value, command=lambda e=ev: self.brain.force_rare(e))
        m.add_cascade(label="Trigger Rare Event", menu=rare)

        m.add_separator()
        m.add_command(label="Quit Xubair", command=self.quit)
        return m

    def _popup_menu(self, x_root: int, y_root: int):
        menu = self._fresh_menu()
        try:
            menu.tk_popup(x_root, y_root)
        finally:
            menu.grab_release()

    def _toggle(self, key: str, apply: bool = False):
        self.prefs.set(key, not self.prefs.get(key))
        if apply:
            self._apply_prefs_to_brain()
        if key == "reduceEffects":
            self.renderer.reduce_effects = self.prefs.reduceEffects

    def _set_pref(self, key: str, value, apply: bool = False):
        self.prefs.set(key, value)
        if apply:
            self._apply_prefs_to_brain()

    def toggle_hidden(self):
        self._hidden = not self._hidden
        self.prefs.set("isHidden", self._hidden)
        if self._hidden:
            self.window.hide()
        else:
            self.window.show()

    def toggle_on_top(self):
        self.prefs.set("alwaysOnTop", not self.prefs.alwaysOnTop)
        self.window.set_topmost(self.prefs.alwaysOnTop)

    def poke(self):
        if self._hidden:
            self.toggle_hidden()
        self.brain.handle_click()

    def reset_position(self):
        if self._hidden:
            self.toggle_hidden()
        b = self._bounds()
        self.brain.place(Point(b.width / 2, 60), b)

    def open_review(self):
        try:
            from .review_window import open_review
            open_review(self.root, self.brain.stats, self.brain.needs,
                        set(self.brain.unlockedAchievements), self.brain.mood,
                        self.prefs.get("hireDate") or time.time())
        except Exception:
            pass

    def start_focus(self, minutes: int):
        self._focus_minutes = minutes
        self._focus_deadline = time.monotonic() + minutes * 60
        self.brain.start_focus()

    def stop_focus(self):
        self._focus_deadline = None
        self._break_deadline = None
        self.brain.stop_focus()

    def remind_me(self):
        from tkinter import simpledialog
        try:
            msg = simpledialog.askstring("Remind Me", "What should I remind you about?", parent=self.root)
        except tk.TclError:
            msg = None
        if not msg:
            return
        self.renderer.sign_text = msg
        self.brain.reminder_set()
        # Fire after a short delay for demo; a full scheduler comes with the reminders store.
        self.root.after(5 * 60 * 1000, lambda: self.brain.remind(False))

    def _play_sound(self, cue):
        if not self.prefs.soundEnabled or not IS_WIN:
            return
        try:
            import winsound
            winsound.MessageBeep(0xFFFFFFFF)
        except Exception:
            pass

    def _persist(self):
        self.prefs.stats = self.brain.stats
        self.prefs.needs = self.brain.needs
        self.prefs.unlocked_achievements = set(self.brain.unlockedAchievements)
        self.prefs.saved_position = (self.brain.position.x, self.brain.position.y)
        self.prefs.save()

    def quit(self):
        self._running = False
        self._persist()
        if self.tray is not None:
            self.tray.stop()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self):
        self.root.mainloop()


def _bar(value: float) -> str:
    filled = int(round(value * 5))
    return "●" * filled + "○" * (5 - filled)


def _human_size(nbytes: int) -> str:
    size = float(nbytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return "%d B" % int(size)
            return ("%.1f %s" % (size, unit)).replace(".0 ", " ")
        size /= 1024
    return "%d B" % int(nbytes)
