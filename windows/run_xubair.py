"""Entry point for Xubair (Windows). Double-click the built Xubair.exe, or run:
    python run_xubair.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    from xubair.app.application import Application
    Application().run()


if __name__ == "__main__":
    main()
