#!/usr/bin/env python3
"""Jarvis-549 launcher.

Run the desktop GUI assistant from any directory:

    python run.py

(Equivalent to `python -m jarvis`.)
"""

from jarvis.ui.app import run

if __name__ == "__main__":
    run()
