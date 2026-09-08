#!/usr/bin/env python3
"""Compatibility entry point (thin wrapper) for Jarvis-549.

Runs the GUI desktop assistant. For the CLI variant see the archived
original in the `archived/` folder.

    python main.py
"""

from jarvis.ui.app import run

if __name__ == "__main__":
    run()
