#!/usr/bin/env python3
"""SPACE MINER - graphical (pygame) entry point. Run: python gui_main.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import pygame  # noqa: F401
except ImportError:
    print("The graphical interface needs pygame:  pip install pygame")
    print("You can still play the terminal version:  python main.py")
    sys.exit(1)

from space_miner.gui.app import run_gui

if __name__ == "__main__":
    sys.exit(run_gui())
