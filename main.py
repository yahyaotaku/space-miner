#!/usr/bin/env python3
"""SPACE MINER - a terminal idle game. Run: python main.py"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from space_miner import save as save_sys
from space_miner.game import Game
from space_miner import ui, screens
from space_miner.offline import render_summary
from space_miner.util import BOLD, DIM, YELLOW, CYAN, fmt, fmt_time

try:
    import termios
    import tty
    import select
    HAS_TTY = True
except ImportError:
    HAS_TTY = False


class IO:
    def __init__(self):
        self.is_tty = sys.stdin.isatty() and HAS_TTY
        self._old_attrs = None
        if self.is_tty:
            self._old_attrs = termios.tcgetattr(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())

    def close(self):
        if self._old_attrs is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old_attrs)

    def clear(self):
        if sys.stdout.isatty():
            sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

    def read_key(self, timeout=None):
        if not self.is_tty:
            line = sys.stdin.readline()
            if line == "":
                return "q"
            return line.strip()[:1] if line.strip() else None
        fd = sys.stdin.fileno()
        ready, _, _ = select.select([fd], [], [], timeout)
        if not ready:
            return None
        ch = sys.stdin.read(1)
        if ch == "" or ch == "\x04":
            return "q"
        if ch == "\x1b":
            return "escape"
        if ch in ("\r", "\n"):
            return None
        return ch

    def read_line(self):
        if self._old_attrs is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old_attrs)
        try:
            return input()
        finally:
            if self._old_attrs is not None:
                tty.setcbreak(sys.stdin.fileno())

    def echo(self, text):
        print(text)

    def notify(self, g, msg, pause=0.9):
        g.log(msg)
        print(f"\n  >> {msg}")
        sys.stdout.flush()
        if pause and self.is_tty:
            time.sleep(pause)


BANNER = r"""
   _____  _____  _____  _____  __      ___    __  __
  / ___/ / ___/ / ___/ / ___/ / /     /   \  / \/ /
  \__ \ / /_   / /_   / /_   / /     / /\ / / /\ /
 ___/ // __/  / __/  / __/  / /___  / /  / / /  / /
/____//_/     /_/    /_/    /_____/ /_/  /_/ /__/\_\
        From a tiny mining ship to a galactic empire.
"""


INTRO = [
    BOLD("An old mining ship. A pile of debts. A whole galaxy of rock."),
    "",
    "You inherited the Rustbucket from your uncle, along with his debts",
    "and his claim on the Asteroid-01 belt. The laser still works. Barely.",
    "",
    "Fire the laser with SPACE. Sell ore in the Market (s). Buy drones (d)",
    "to mine while you sleep. The galaxy is waiting.",
    "",
    DIM("Press any key to begin..."),
]


def show_offline_summary(g, io):
    io.clear()
    print()
    for ln in render_summary(g._offline_summary):
        print(" " + ln)
    print()
    print(DIM(" Press any key..."))
    io.read_key()


def main():
    if "--gui" in sys.argv:
        try:
            import pygame  # noqa: F401
        except ImportError:
            print("The graphical interface needs pygame:  pip install pygame")
            return 1
        from space_miner.gui.app import run_gui
        return run_gui()
    reset = "--reset" in sys.argv
    if reset:
        for p in (save_sys.save_path(), save_sys.backup_path()):
            try:
                os.unlink(p)
            except OSError:
                pass
        print("Save erased.")

    if "--sim" in sys.argv:
        return run_simulation()

    io = IO()
    try:
        state, source = save_sys.load()
        g = Game(state)
        g._offline_summary = None
        if source:
            summary = g.apply_offline(time.time())
            g._offline_summary = summary
        io.clear()
        print(CYAN(BANNER))
        if source is None:
            for ln in INTRO:
                print(" " + ln)
            io.read_key()
        elif g._offline_summary:
            show_offline_summary(g, io)
        else:
            print(BOLD(" Welcome back, Commander."))
            time.sleep(0.6)
        run_loop(g, io)
    finally:
        io.close()
    return 0


def run_loop(g, io):
    from space_miner.screens import (market_screen, upgrades_screen, drones_screen,
                                     fleet_screen, galaxy_screen, buildings_screen,
                                     research_screen, employees_screen, missions_screen,
                                     achievements_screen, stats_screen, settings_screen,
                                     rebirth_screen, help_screen)
    screen_map = {
        "s": market_screen, "m": market_screen, "u": upgrades_screen,
        "d": drones_screen, "f": fleet_screen, "p": galaxy_screen,
        "b": buildings_screen, "r": research_screen, "e": employees_screen,
        "j": missions_screen, "a": achievements_screen, "t": stats_screen,
        "v": settings_screen, "x": rebirth_screen, "?": help_screen,
    }
    while not g.quit_requested:
        g.tick()
        io.clear()
        print(ui.dashboard(g))
        key = io.read_key(timeout=0.25)
        if key is None:
            continue
        if key == " " or key == "z":
            g.do_mine()
        elif key.isdigit() and key != "0":
            g.select_node(int(key) - 1)
        elif key == "0":
            g.select_node(5)
        elif key == "n":
            g.cycle_planet(1)
        elif key == "o":
            g.overdrive()
        elif key in ("Q", "q"):
            if key == "Q" or True:
                g.save()
                g.quit_requested = True
        elif key in screen_map:
            screen_map[key](g, io)


def run_simulation():
    """Headless smoke test: simulate active play for N virtual seconds."""
    import random
    seconds = 3600
    for i, a in enumerate(sys.argv):
        if a == "--sim" and i + 1 < len(sys.argv):
            seconds = int(sys.argv[i + 1])
    rng = random.Random(42)
    g = Game(rng=rng)
    g.log("Simulation started.")
    t0 = g.now
    for step in range(seconds):
        now = t0 + step
        g.now = now
        g.state["last_tick"] = g.now - 1.0
        g.tick(now)
        if step % 2 == 0:
            g.do_mine(silent=True)
        if step % 5 == 0:
            g.sell_everything()
        if step % 60 == 0 and g.state["credits"] > 800:
            g.buy_drone("mining")
        if step % 120 == 0 and g.state["credits"] > 300:
            g.buy_upgrade("laser_power")
    s = g.state
    print("=== SIMULATION COMPLETE ===")
    print(f"Simulated seconds : {seconds}")
    print(f"Credits           : {fmt(s['credits'])} (lifetime {fmt(s['lifetime_credits'])})")
    print(f"Ore mined         : {fmt(s['ore_mined'])}")
    print(f"Player level      : {s['player_level']}")
    print(f"Drones            : {sum(d['count'] for d in s['drones'].values())}")
    print(f"Ships             : {sum(v['count'] for v in s['ships'].values())}")
    print(f"Research done     : {len(s['research'])}")
    print(f"Missions done     : {s['missions_done']}")
    print(f"Achievements      : {len(s['achievements'])}")
    print(f"Kills             : {s['kills']}")
    ok = g.save()
    print(f"Save written      : {ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
