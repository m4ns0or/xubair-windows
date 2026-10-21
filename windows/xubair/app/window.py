"""The on-screen character window (Tkinter, borderless + always-on-top + colour-key transparency).

On Windows, `-transparentcolor` makes the key colour fully transparent *and* click-through,
so clicks on the empty area around the character pass to the apps underneath — only his body
(the opaque pixels) receives clicks. The window is resized/repositioned each frame to wrap the
rendered character, keeping the transparent surface small.
"""
from __future__ import annotations

import sys
import time
import tkinter as tk
from typing import Callable, List, Optional, Tuple

from PIL import Image, ImageTk

from ..core.types import Point

KEY_COLOR = "#FE00FE"
KEY_RGB = (254, 0, 254)


class VelocityTracker:
    """Smoothed pointer velocity in screen px/second for flinging."""

    def __init__(self):
        self._samples: List[Tuple[float, float, float]] = []

    def reset(self):
        self._samples.clear()

    def add(self, x: float, y: float):
        self._samples.append((time.monotonic(), x, y))
        if len(self._samples) > 6:
            self._samples.pop(0)

    def velocity(self) -> Tuple[float, float]:
        if len(self._samples) < 2:
            return (0.0, 0.0)
        t0, x0, y0 = self._samples[0]
        t1, x1, y1 = self._samples[-1]
        dt = t1 - t0
        if dt <= 0:
            return (0.0, 0.0)
        return ((x1 - x0) / dt, (y1 - y0) / dt)


class CharacterWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.top = tk.Toplevel(root)
        self.top.overrideredirect(True)
        try:
            self.top.wm_attributes("-topmost", True)
        except tk.TclError:
            pass
        self._colorkey_ok = False
        try:
            self.top.wm_attributes("-transparentcolor", KEY_COLOR)
            self._colorkey_ok = True
        except tk.TclError:
            pass
        if sys.platform.startswith("win"):
            try:
                self.top.wm_attributes("-toolwindow", True)
            except tk.TclError:
                pass
        self.top.configure(bg=KEY_COLOR)

        self.canvas = tk.Canvas(self.top, highlightthickness=0, bd=0, bg=KEY_COLOR)
        self.canvas.pack(fill="both", expand=True)
        self._img_id = self.canvas.create_image(0, 0, anchor="nw")
        self._photo: Optional[ImageTk.PhotoImage] = None

        # callbacks wired by the application
        self.on_click: Optional[Callable[[], None]] = None
        self.on_double_click: Optional[Callable[[], None]] = None
        self.on_begin_drag: Optional[Callable[[], None]] = None
        self.on_drag: Optional[Callable[[Point], None]] = None
        self.on_end_drag: Optional[Callable[[Point], None]] = None
        self.on_right_click: Optional[Callable[[int, int], None]] = None
        self.on_pinch: Optional[Callable[[float], None]] = None
        self.feet_on_screen: Optional[Callable[[], Point]] = None

        self._tracker = VelocityTracker()
        self._down_screen: Optional[Tuple[int, int]] = None
        self._grab_offset = (0.0, 0.0)
        self._dragging = False
        self._hit_rect: Tuple[float, float, float, float] = (0, 0, 0, 0)
        self._feet_in_img = (0.0, 0.0)
        self._win_pos = (0, 0)

        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._motion)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<Double-Button-1>", self._double)
        self.canvas.bind("<ButtonPress-3>", self._rclick)
        self.canvas.bind("<MouseWheel>", self._wheel)

    # ── presentation ───────────────────────────────────────────────────────────

    def show(self):
        self.top.deiconify()

    def hide(self):
        self.top.withdraw()

    def update_frame(self, image: Image.Image, feet_in_img: Tuple[float, float],
                     hit_rect: Tuple[float, float, float, float], feet_screen: Tuple[int, int]):
        if self._colorkey_ok:
            bg = Image.new("RGBA", image.size, KEY_RGB + (255,))
            bg.alpha_composite(image)
            disp = bg.convert("RGB")
        else:
            disp = image.convert("RGB")
        self._photo = ImageTk.PhotoImage(disp)
        self.canvas.itemconfigure(self._img_id, image=self._photo)
        self.canvas.config(width=image.width, height=image.height)

        win_x = int(round(feet_screen[0] - feet_in_img[0]))
        win_y = int(round(feet_screen[1] - feet_in_img[1]))
        self.top.geometry("%dx%d+%d+%d" % (image.width, image.height, win_x, win_y))
        self._win_pos = (win_x, win_y)
        self._feet_in_img = feet_in_img
        self._hit_rect = hit_rect

    def set_topmost(self, value: bool):
        try:
            self.top.wm_attributes("-topmost", bool(value))
        except tk.TclError:
            pass

    # ── input ───────────────────────────────────────────────────────────────────

    def _over_body(self, x_root: int, y_root: int) -> bool:
        lx = x_root - self._win_pos[0]
        ly = y_root - self._win_pos[1]
        r = self._hit_rect
        return r[0] <= lx <= r[2] and r[1] <= ly <= r[3]

    def _press(self, event):
        if not self._over_body(event.x_root, event.y_root):
            return
        self._down_screen = (event.x_root, event.y_root)
        feet = self.feet_on_screen() if self.feet_on_screen else Point(event.x_root, event.y_root)
        self._grab_offset = (event.x_root - feet.x, event.y_root - feet.y)
        self._dragging = False
        self._tracker.reset()
        self._tracker.add(event.x_root, event.y_root)

    def _motion(self, event):
        if self._down_screen is None:
            return
        self._tracker.add(event.x_root, event.y_root)
        sx, sy = self._down_screen
        if not self._dragging and abs(event.x_root - sx) + abs(event.y_root - sy) > 3:
            self._dragging = True
            if self.on_begin_drag:
                self.on_begin_drag()
        if self._dragging and self.on_drag:
            self.on_drag(Point(event.x_root - self._grab_offset[0], event.y_root - self._grab_offset[1]))

    def _release(self, event):
        if self._dragging:
            if self.on_end_drag:
                vx, vy = self._tracker.velocity()
                self.on_end_drag(Point(vx, vy))
        elif self._down_screen is not None:
            if self.on_click:
                self.on_click()
        self._dragging = False
        self._down_screen = None

    def _double(self, event):
        if self._over_body(event.x_root, event.y_root) and self.on_double_click:
            self.on_double_click()

    def _rclick(self, event):
        if self.on_right_click:
            self.on_right_click(event.x_root, event.y_root)

    def _wheel(self, event):
        # Ctrl+wheel over the body resizes him.
        if not (event.state & 0x0004):  # Control
            return
        if not self._over_body(event.x_root, event.y_root):
            return
        if self.on_pinch:
            self.on_pinch((1 if event.delta > 0 else -1) * 0.08)

    # ── OS file drop (Windows WM_DROPFILES) ─────────────────────────────────────

    def enable_file_drop(self, on_files):
        """Accept files dropped onto his body. Only file *paths* are read; files are never opened."""
        if not sys.platform.startswith("win"):
            return
        import ctypes
        self.top.update_idletasks()
        try:
            hwnd = self.top.winfo_id()
        except tk.TclError:
            return
        shell32 = ctypes.windll.shell32
        user32 = ctypes.windll.user32
        shell32.DragAcceptFiles(ctypes.c_void_p(hwnd), True)

        WM_DROPFILES = 0x0233
        GWLP_WNDPROC = -4
        LRESULT = ctypes.c_ssize_t
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_void_p, ctypes.c_uint,
                                     ctypes.c_size_t, ctypes.c_ssize_t)
        set_long = getattr(user32, "SetWindowLongPtrW", None) or user32.SetWindowLongW
        set_long.restype = ctypes.c_void_p
        set_long.argtypes = [ctypes.c_void_p, ctypes.c_int, WNDPROC]
        call_wndproc = user32.CallWindowProcW
        call_wndproc.restype = LRESULT
        call_wndproc.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint,
                                 ctypes.c_size_t, ctypes.c_ssize_t]
        self._old_wndproc = ctypes.c_void_p()

        def handler(h, msg, wparam, lparam):
            if msg == WM_DROPFILES:
                try:
                    hdrop = ctypes.c_void_p(wparam)
                    count = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
                    paths = []
                    for i in range(count):
                        length = shell32.DragQueryFileW(hdrop, i, None, 0)
                        buf = ctypes.create_unicode_buffer(length + 1)
                        shell32.DragQueryFileW(hdrop, i, buf, length + 1)
                        if buf.value:
                            paths.append(buf.value)
                    shell32.DragFinish(hdrop)
                    if paths and on_files:
                        on_files(paths)
                except Exception:
                    pass
                return 0
            return call_wndproc(self._old_wndproc, h, msg, wparam, lparam)

        self._wndproc_ref = WNDPROC(handler)  # keep a reference alive
        self._old_wndproc = ctypes.c_void_p(set_long(ctypes.c_void_p(hwnd), GWLP_WNDPROC,
                                                      self._wndproc_ref))
