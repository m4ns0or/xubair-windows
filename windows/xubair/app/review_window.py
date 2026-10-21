"""The comedic 'Annual Performance Review' window — a Tk port of ReviewView.swift."""
from __future__ import annotations

import datetime
import tkinter as tk
from typing import Optional

from ..core.stats import ALL_ACHIEVEMENTS

BG = "#1b1b22"
CARD = "#26262e"
STROKE = "#3a3a44"
ACCENT = "#8ecb5c"
SECONDARY = "#9a9aa6"
TEXT = "#f2f2f5"
YELLOW = "#ffd23a"
ORANGE = "#ff9f40"
PINK = "#ff6ba6"

_COMMENTS = [
    "Consistently exceeds expectations of doing nothing. Recommend no changes.",
    "Shows strong initiative when snacks are involved.",
    "Has been seen pressing his face against the screen. Please stop him.",
    "Holds frequent meetings. Attendance at those meetings: one.",
    "His typing has produced zero documents. Impressive consistency.",
    "Would benefit from a window. Already lives in several.",
]


def _comment(stats) -> str:
    seed = stats.pokes + stats.naps * 3 + datetime.date.today().day
    return _COMMENTS[seed % len(_COMMENTS)]


_open_window: Optional[tk.Toplevel] = None


def open_review(parent: tk.Misc, stats, needs, unlocked, mood, hire_epoch):
    global _open_window
    if _open_window is not None:
        try:
            _open_window.deiconify()
            _open_window.lift()
            return
        except tk.TclError:
            _open_window = None

    win = tk.Toplevel(parent)
    _open_window = win
    win.title("Xubair — Performance Review")
    win.configure(bg=BG)
    win.geometry("560x680")

    def _closed():
        global _open_window
        _open_window = None
        win.destroy()
    win.protocol("WM_DELETE_WINDOW", _closed)

    # Scrollable body.
    canvas = tk.Canvas(win, bg=BG, highlightthickness=0)
    scroll = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
    body = tk.Frame(canvas, bg=BG)
    body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=body, anchor="nw", width=540)
    canvas.configure(yscrollcommand=scroll.set)
    canvas.pack(side="left", fill="both", expand=True, padx=(16, 0))
    scroll.pack(side="right", fill="y")
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (1 if e.delta > 0 else -1), "units"))

    def label(parent, text, size, color=TEXT, bold=False, italic=False, wrap=0):
        style = "bold" if bold else ("italic" if italic else "normal")
        lbl = tk.Label(parent, text=text, bg=parent["bg"], fg=color,
                       font=("Segoe UI", size, style), justify="left", anchor="w")
        if wrap:
            lbl.configure(wraplength=wrap)
        return lbl

    # Header
    header = tk.Frame(body, bg=BG)
    header.pack(fill="x", pady=(16, 10))
    label(header, "ANNUAL PERFORMANCE REVIEW", 9, ACCENT, bold=True).pack(anchor="w")
    label(header, "Xubair", 20, TEXT, bold=True).pack(anchor="w")
    label(header, "Unpaid Desktop Intern · Mood: %s" % mood.display_name, 11, SECONDARY).pack(anchor="w")
    days = max(0, (datetime.date.today() - datetime.date.fromtimestamp(hire_epoch)).days)
    label(header, "%d day%s of service · Salary: $0.00" % (days, "" if days == 1 else "s"),
          11, SECONDARY).pack(anchor="w")

    def card(title):
        label(body, title.upper(), 9, SECONDARY, bold=True).pack(anchor="w", pady=(14, 4))
        frame = tk.Frame(body, bg=CARD, highlightbackground=STROKE, highlightthickness=1)
        frame.pack(fill="x")
        inner = tk.Frame(frame, bg=CARD)
        inner.pack(fill="x", padx=12, pady=10)
        return inner

    def stars(n):
        n = max(0, min(5, int(n)))
        return "★" * n + "☆" * (5 - n)

    # Ratings
    c = card("Ratings")
    ratings = [
        ("Productivity", 1 if stats.workSessions > 0 else 0, "Pretended to work %d×" % stats.workSessions),
        ("Attendance", 5, "Literally cannot leave"),
        ("Teamwork", min(5, stats.meetings), "Meetings, all with himself"),
        ("Snack management", min(5, stats.snacks // 2), "%d snacks eaten" % stats.snacks),
        ("Athleticism", min(5, (stats.kicks + stats.throwCount) // 5),
         "%d kicks, %d flights" % (stats.kicks, stats.throwCount)),
        ("Rest & recovery", min(5, stats.naps), "%d naps" % stats.naps),
    ]
    for title, n, note in ratings:
        row = tk.Frame(c, bg=CARD)
        row.pack(fill="x", pady=2)
        label(row, title, 11).pack(side="left")
        label(row, stars(n), 12, YELLOW).pack(side="left", padx=8)
        label(row, note, 10, SECONDARY).pack(side="right")

    # Wellbeing meters
    c = card("Wellbeing")
    for title, value, color in [("Hunger", needs.hunger, ORANGE), ("Energy", needs.energy, ACCENT),
                                ("Fun", needs.fun, PINK)]:
        row = tk.Frame(c, bg=CARD)
        row.pack(fill="x", pady=3)
        label(row, title, 11).pack(side="left")
        label(row, "%d%%" % int(value * 100), 10, SECONDARY).pack(side="right")
        bar_bg = tk.Frame(row, bg="#15151b", height=8, width=300)
        bar_bg.pack(side="left", padx=10)
        bar_bg.pack_propagate(False)
        fill = tk.Frame(bar_bg, bg=color, height=8, width=int(300 * max(0.0, min(1.0, value))))
        fill.place(x=0, y=0)

    # Key metrics grid
    c = card("Key metrics")
    grid = tk.Frame(c, bg=CARD)
    grid.pack(fill="x")
    metrics = [
        ("👉", "Pokes", stats.pokes), ("😱", "Panics", stats.panics), ("🪟", "Glass hits", stats.glassHits),
        ("✈️", "Throws", stats.throwCount), ("🎯", "Bounces", stats.bounces),
        ("🏃", "Lengths", int(stats.distance)), ("🎭", "Fourth walls", stats.fourthWallEvents),
        ("📎", "Files", stats.filesInspected), ("🍅", "Focus", stats.focusSessions),
        ("☕️", "Coffees", stats.coffees), ("🏙️", "Window lands", stats.windowLandings),
        ("🎉", "Celebrations", stats.celebrations),
    ]
    for i, (emoji, title, value) in enumerate(metrics):
        cell = tk.Frame(grid, bg="#202028")
        cell.grid(row=i // 3, column=i % 3, sticky="nsew", padx=3, pady=3, ipady=4)
        label(cell, emoji, 14, TEXT).pack()
        label(cell, str(value), 15, TEXT, bold=True).pack()
        label(cell, title, 9, SECONDARY).pack()
    for col in range(3):
        grid.grid_columnconfigure(col, weight=1)

    # Achievements
    done_count = sum(1 for a in ALL_ACHIEVEMENTS if a.id in unlocked)
    c = card("Achievements · %d of %d" % (done_count, len(ALL_ACHIEVEMENTS)))
    for a in ALL_ACHIEVEMENTS:
        done = a.id in unlocked
        row = tk.Frame(c, bg=CARD)
        row.pack(fill="x", pady=2)
        label(row, a.emoji, 15, TEXT if done else SECONDARY).pack(side="left", padx=(0, 8))
        text = tk.Frame(row, bg=CARD)
        text.pack(side="left", fill="x", expand=True)
        title = a.title + ("  ✅" if done else "")
        label(text, title, 11, TEXT if done else SECONDARY, bold=done).pack(anchor="w")
        label(text, a.detail, 10, SECONDARY).pack(anchor="w")

    # Manager's comment
    c = card("Manager's comments")
    label(c, _comment(stats), 11, SECONDARY, italic=True, wrap=480).pack(anchor="w")

    win.lift()
    win.attributes("-topmost", True)
    win.after(300, lambda: win.attributes("-topmost", False))
