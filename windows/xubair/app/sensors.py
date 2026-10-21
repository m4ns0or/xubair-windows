"""Reads local, non-personal system state on Windows — idle time, battery, clock, CPU, RAM,
open windows and clipboard — a Windows port of EnvironmentSensor (Sensors.swift).

Nothing here leaves the machine. Windows app names are mapped onto the same identifiers the
behavior brain already reacts to, so the personality stays identical to the Mac version.
"""
from __future__ import annotations

import ctypes
import os
import re
import sys
import time
from datetime import datetime
from typing import Optional, Set, Tuple

from ..core.world import ClipboardContentType, Environment, FileKind, MemoryPressure

IS_WIN = sys.platform.startswith("win")

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None

# Map Windows process names -> the watched identifiers in the brain (keeps reactions identical).
_WATCHED = {
    "slack.exe": "com.tinyspeck.slackmacgap",
    "zoom.exe": "us.zoom.xos",
    "figma.exe": "com.figma.Desktop",
    "figma_agent.exe": "com.figma.Desktop",
}
_BUILD_HINTS = ("msbuild", "cl.exe", "link.exe", "gcc", "clang", "cargo", "rustc",
                "go build", "dotnet", "ninja", "make", "webpack", "tsc", "gradle", "javac",
                "xcodebuild", "swift")


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [("ACLineStatus", ctypes.c_byte), ("BatteryFlag", ctypes.c_byte),
                ("BatteryLifePercent", ctypes.c_byte), ("Reserved1", ctypes.c_byte),
                ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]


class EnvironmentSensor:
    def __init__(self):
        self._last_clip_seq = -1
        self._last_clip_type = ClipboardContentType.other
        self._cpu_primed = False

    def sample(self) -> Environment:
        now = datetime.now()
        level, charging, mins = self._battery()
        return Environment(
            userIdleSeconds=self._idle_seconds(),
            batteryLevel=level, isCharging=charging, batteryTimeToEmptyMinutes=mins,
            hour=now.hour, weekday=(now.isoweekday() % 7) + 1,  # 1=Sunday..7=Saturday
            cpuLoad=self._cpu_load(), memoryPressure=self._memory_pressure(),
            runningAppCount=self._window_count(), detectedBundleIDs=self._detected_apps(),
            buildProcessRunning=self._build_running(), clipboardType=self._classify_clipboard())

    # ── idle ────────────────────────────────────────────────────────────────
    def _idle_seconds(self) -> float:
        if not IS_WIN:
            return 0.0
        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            millis = ctypes.windll.kernel32.GetTickCount() - info.dwTime
            return max(0.0, millis / 1000.0)
        return 0.0

    # ── battery ───────────────────────────────────────────────────────────────
    def _battery(self) -> Tuple[Optional[float], Optional[bool], Optional[float]]:
        if IS_WIN:
            status = SYSTEM_POWER_STATUS()
            if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
                pct = status.BatteryLifePercent
                ac = status.ACLineStatus
                if pct == 255 or (status.BatteryFlag & 128):  # no battery
                    return (None, None, None)
                level = pct / 100.0
                charging = (ac == 1)
                secs = status.BatteryLifeTime
                mins = None if (charging or secs == 0xFFFFFFFF) else secs / 60.0
                return (level, charging, mins)
            return (None, None, None)
        if psutil is not None:
            b = psutil.sensors_battery()
            if b is None:
                return (None, None, None)
            mins = None if (b.power_plugged or b.secsleft in (-1, -2)) else b.secsleft / 60.0
            return (b.percent / 100.0, b.power_plugged, mins)
        return (None, None, None)

    # ── cpu / memory ─────────────────────────────────────────────────────────
    def _cpu_load(self) -> float:
        if psutil is None:
            return 0.0
        if not self._cpu_primed:
            psutil.cpu_percent(interval=None)
            self._cpu_primed = True
            return 0.0
        return min(1.0, psutil.cpu_percent(interval=None) / 100.0)

    def _memory_pressure(self) -> MemoryPressure:
        if psutil is None:
            return MemoryPressure.normal
        avail = psutil.virtual_memory().available / max(1, psutil.virtual_memory().total)
        if avail < 0.05:
            return MemoryPressure.critical
        if avail < 0.12:
            return MemoryPressure.warning
        return MemoryPressure.normal

    # ── running windows / apps ────────────────────────────────────────────────
    def _window_count(self) -> int:
        if not IS_WIN:
            return 0
        count = [0]
        user32 = ctypes.windll.user32
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def cb(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            # skip tool windows
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if ex & WS_EX_TOOLWINDOW:
                return True
            count[0] += 1
            return True

        user32.EnumWindows(WNDENUMPROC(cb), 0)
        return count[0]

    def _process_names(self) -> Set[str]:
        if psutil is None:
            return set()
        names = set()
        for p in psutil.process_iter(["name"]):
            try:
                n = (p.info.get("name") or "").lower()
                if n:
                    names.add(n)
            except Exception:
                continue
        return names

    def _detected_apps(self) -> Set[str]:
        out = set()
        for name in self._process_names():
            bid = _WATCHED.get(name)
            if bid:
                out.add(bid)
        return out

    def _build_running(self) -> bool:
        names = self._process_names()
        return any(any(hint in n for hint in _BUILD_HINTS) for n in names)

    # ── clipboard ──────────────────────────────────────────────────────────────
    def _classify_clipboard(self) -> ClipboardContentType:
        if not IS_WIN:
            return ClipboardContentType.unchanged
        seq = ctypes.windll.user32.GetClipboardSequenceNumber()
        if seq == self._last_clip_seq:
            return ClipboardContentType.unchanged
        self._last_clip_seq = seq
        text = _read_clipboard_text()
        if not text:
            self._last_clip_type = ClipboardContentType.other
            return ClipboardContentType.other
        t = text.strip()
        if t.startswith("http://") or t.startswith("https://"):
            result = ClipboardContentType.url
        elif ("\n" in t and ("Error" in t or "Exception" in t or "Traceback" in t)
              and (" at " in t or "0x" in t)):
            result = ClipboardContentType.stackTrace
        elif len(t) < 80 and re.match(r"^(0x[0-9a-fA-F]+|[A-Z][A-Z0-9_]{2,}(Error|Exception|Code)?)$", t):
            result = ClipboardContentType.errorCode
        else:
            result = ClipboardContentType.other
        self._last_clip_type = result
        return result


def _read_clipboard_text() -> str:
    if not IS_WIN:
        return ""
    CF_UNICODETEXT = 13
    u = ctypes.windll.user32
    k = ctypes.windll.kernel32
    if not u.OpenClipboard(0):
        return ""
    try:
        if not u.IsClipboardFormatAvailable(CF_UNICODETEXT):
            return ""
        handle = u.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        ptr = k.GlobalLock(handle)
        if not ptr:
            return ""
        try:
            return ctypes.c_wchar_p(ptr).value or ""
        finally:
            k.GlobalUnlock(handle)
    finally:
        u.CloseClipboard()


_IMAGE = {"png", "jpg", "jpeg", "gif", "heic", "webp", "tiff", "bmp", "svg", "raw", "ico"}
_CODE = {"swift", "py", "js", "ts", "tsx", "jsx", "c", "h", "m", "cpp", "rs", "go", "java", "kt",
         "rb", "php", "html", "css", "json", "sh", "yml", "yaml", "sql", "cs", "ps1", "bat"}
_ARCHIVE = {"zip", "gz", "tar", "rar", "7z", "dmg", "xz", "bz2"}
_AUDIO = {"mp3", "wav", "aiff", "aif", "m4a", "flac", "ogg", "aac"}
_VIDEO = {"mp4", "mov", "m4v", "avi", "mkv", "webm"}
_TEXT = {"txt", "md", "rtf", "doc", "docx", "pages", "log"}
_SHEET = {"xls", "xlsx", "csv", "numbers", "tsv"}
_SLIDES = {"ppt", "pptx", "key"}


def classify_files(paths) -> FileKind:
    """Classify dropped files by extension only — the files are never opened or changed."""
    if len(paths) > 5:
        return FileKind.many
    if not paths:
        return FileKind.other
    p = paths[0]
    ext = os.path.splitext(p)[1].lower().lstrip(".")
    if ext == "exe" or ext == "app":
        return FileKind.app
    if os.path.isdir(p):
        return FileKind.folder
    if ext in _IMAGE:
        return FileKind.image
    if ext == "pdf":
        return FileKind.pdf
    if ext in _CODE:
        return FileKind.code
    if ext in _ARCHIVE:
        return FileKind.archive
    if ext in _AUDIO:
        return FileKind.audio
    if ext in _VIDEO:
        return FileKind.video
    if ext in _TEXT:
        return FileKind.text
    if ext in _SHEET:
        return FileKind.spreadsheet
    if ext in _SLIDES:
        return FileKind.presentation
    return FileKind.other
