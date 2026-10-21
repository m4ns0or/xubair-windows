"""System-tray icon so the menu is reachable even while he's hidden.

Uses pystray in its own thread; menu clicks are pushed to a thread-safe queue that the Tk
main loop drains, because Tkinter must only be touched from its own thread.
"""
from __future__ import annotations

import queue
import threading
from typing import Callable, Optional

try:
    import pystray  # type: ignore
    from pystray import Menu, MenuItem
except Exception:  # pragma: no cover
    pystray = None

from PIL import Image


class Tray:
    def __init__(self, icon_image: Image.Image, actions: dict):
        """actions: {label: callable}. Callables are invoked on the Tk thread via the queue."""
        self._queue: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self._actions = actions
        self._icon = None
        self._thread: Optional[threading.Thread] = None
        self._image = icon_image

    def available(self) -> bool:
        return pystray is not None

    def _enqueue(self, fn):
        def handler(icon=None, item=None):
            self._queue.put(fn)
        return handler

    def start(self):
        if pystray is None:
            return
        items = []
        for label, fn in self._actions.items():
            if label == "-":
                items.append(Menu.SEPARATOR)
            else:
                items.append(MenuItem(label, self._enqueue(fn),
                                      default=(label in ("Show Xubair", "Poke Him"))))
        self._icon = pystray.Icon("Xubair", self._image, "Xubair", Menu(*items))
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def pump(self):
        """Call periodically from the Tk loop to run queued actions on the main thread."""
        while True:
            try:
                fn = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                fn()
            except Exception:
                pass

    def stop(self):
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
