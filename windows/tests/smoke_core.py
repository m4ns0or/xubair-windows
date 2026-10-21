"""Headless smoke test: drive the brain for a simulated session and exercise every
public event, checking nothing throws and output stays finite. Run:  python tests/smoke_core.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xubair.core import (Bounds, CharacterBrain, Environment, FileKind, ItemKind, Point,
                         WorldInput, sample_motion)
from xubair.core.world import ClipboardContentType, MemoryPressure, Platform
from xubair.core import rare_events, script


def run():
    height = 150.0
    bounds = Bounds(0, 1440, 0, 860)
    brain = CharacterBrain(Point(700, 0), seed=12345)
    dt = 1 / 30.0
    cursor = Point(200, 400)
    lines = 0
    states = set()
    frames = 0

    # ~6 simulated minutes
    for n in range(30 * 360):
        cursor.x = 200 + (n % 600)
        cursor.y = 300 + ((n // 3) % 300)
        platforms = [Platform(1, 300, 700, 420), Platform(2, 900, 1300, 600)]
        frame = brain.tick(WorldInput(dt=dt, bounds=bounds, cursor=cursor, height=height,
                                      platforms=platforms))
        frames += 1
        states.add(frame.state.value)
        assert bounds.minX - 1 <= frame.position.x <= bounds.maxX + 1, frame.position.x
        if frame.speech:
            lines += 1
        # motion sampler must stay finite for whatever pose the frame reports
        pose = frame.pose
        rig = sample_motion(pose.motion, t=frame.stepTime, duration=max(0.001, frame.stepDuration),
                            gait=frame.gaitPhase)
        assert rig.is_finite, pose.motion

        if n == 50:
            brain.handle_click()
        if n == 120:
            brain.spawn_item(ItemKind.pizza)
        if n == 140:
            brain.spawn_item(ItemKind.ball)
        if n == 200:
            brain.spawn_item(ItemKind.coffee)
        if n == 300:
            brain.begin_drag()
            brain.drag(Point(500, 400))
            brain.end_drag(Point(900, -300))  # a throw
        if n == 600:
            brain.inspect_file(FileKind.code)
        if n == 700:
            brain.receive_files(FileKind.video, kept=True, nbytes=2_400_000_000, size_text="2.4 GB")
        if n == 900:
            brain.start_focus()
        if n == 1100:
            brain.complete_focus()
        if n == 1300:
            brain.end_break()
        if n == 1500:
            brain.climb_somewhere()
        if n == 2500:
            brain.remind(missed=False)
        if n == 2600:
            brain.handle_click()  # dismiss reminder
        if n == 2800:
            brain.notice_resize(bigger=True)
        if n == 3000:
            brain.update_environment(Environment(
                userIdleSeconds=1, batteryLevel=0.08, isCharging=False, hour=2, weekday=2,
                cpuLoad=0.9, memoryPressure=MemoryPressure.critical, runningAppCount=22,
                detectedBundleIDs={"com.apple.dt.Xcode"}, buildProcessRunning=True,
                clipboardType=ClipboardContentType.url))
        if n == 3200:
            brain.greet()

    # Force-fire every rare event script through its builder.
    for ev in rare_events.RareEvent:
        a = rare_events.activity_for_event(ev, brain.rng)
        assert a.steps, ev

    # Force every scripted activity we can build without extra context.
    for ev in rare_events.RareEvent:
        brain.force_rare(ev)
        for _ in range(20):
            brain.tick(WorldInput(dt=dt, bounds=bounds, cursor=cursor, height=height))

    print("OK  frames=%d  states=%d  spoken=%d  achievements=%d"
          % (frames, len(states), lines, len(brain.unlockedAchievements)))
    print("states:", sorted(states))


if __name__ == "__main__":
    run()
