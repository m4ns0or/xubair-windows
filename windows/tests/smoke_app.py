"""Construct the full Application and pump a few frames without the blocking mainloop,
to catch wiring/coordinate/render errors. Needs a display; skips cleanly if there is none.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run():
    import tkinter as tk
    try:
        probe = tk.Tk()
        probe.destroy()
    except Exception as e:
        print("no display, skipping app smoke:", e)
        return

    from xubair.app.application import Application
    from xubair.core.types import Point

    app = Application()
    # Drive the loop manually (mainloop would block).
    for i in range(40):
        app._tick()
        app.root.update_idletasks()
        app.root.update()
        time.sleep(0.01)
    # Exercise a few user actions.
    app.brain.handle_click()
    app.brain.spawn_item.__self__.spawn_item(__import__("xubair.core.world", fromlist=["ItemKind"]).ItemKind.pizza)
    app.brain.begin_drag()
    app.brain.drag(Point(500, 300))
    app.brain.end_drag(Point(400, -300))
    for i in range(30):
        app._tick()
        app.root.update_idletasks()
        app.root.update()
        time.sleep(0.01)
    app.quit()
    print("OK app ran %d frames; brain clock=%.1fs pos=(%.0f,%.0f)"
          % (70, app.brain.clock, app.brain.position.x, app.brain.position.y))


if __name__ == "__main__":
    run()
