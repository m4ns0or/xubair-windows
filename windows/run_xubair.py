"""Entry point for Xubair (Windows). Double-click the built Xubair.exe, or run:
    python run_xubair.py

Any startup crash is written to %APPDATA%\\Xubair\\xubair.log and shown in a dialog,
so a windowed (no-console) build never fails silently.
"""
import datetime
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _log_path() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "Xubair")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        d = os.path.expanduser("~")
    return os.path.join(d, "xubair.log")


def main():
    try:
        import faulthandler
        faulthandler.enable(open(_log_path(), "a", encoding="utf-8"))
    except Exception:
        pass
    try:
        from xubair.app.application import Application
        Application().run()
    except SystemExit:
        raise
    except BaseException:
        tb = traceback.format_exc()
        try:
            with open(_log_path(), "a", encoding="utf-8") as f:
                f.write("\n===== %s =====\n%s\n" % (datetime.datetime.now().isoformat(), tb))
        except Exception:
            pass
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0, "Xubair hit an error:\n\n%s\n\nAlso saved to:\n%s" % (tb[-1400:], _log_path()),
                "Xubair", 0x10)
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
