# SPACE MINER

*From a tiny mining ship to a galactic empire.*

A complete, playable **terminal-based idle/incremental game** written in pure Python 3
(standard library only — no dependencies). Inspired by classic space-tycoon idle games.

```
python3 main.py
```

## Features

- **Active mining** — fire your laser at asteroids (Small → Ancient), target nodes,
  critical extractions, satisfying destruction with loot logs.
- **Idle production** — mining drones and 7 ship classes mine assigned planets
  around the clock. Mathematical simulation, not per-entity physics.
- **19 minerals** across 5 rarity tiers, dynamic market with drifting prices,
  auto-sell, market events.
- **17 planets across 5 galaxies** (Frontier → Orion Reach → Nebula Expanse →
  Ancient Void → Celestial Core), each with hazards, deposits and dev levels.
- **8 building types** per planet (mining stations, refineries, warehouses, labs,
  shipyards, trading hubs, command centers...).
- **26-node research tree** in 4 branches — every node has a real gameplay effect.
- **Fleet & drones** with levels/XP, assignment, capacity management.
- **6 employee roles** with scaling costs and passive bonuses.
- **28 story missions + rotating daily missions.**
- **Random events**: market booms, mineral rushes, solar flares, alien signals,
  ancient discoveries, and pirate raids resolved by your fleet defense.
- **Galactic Rebirth (prestige)** with Stellar Essence and 6 permanent essence upgrades.
- **34 achievements** that persist across rebirths.
- **Offline progression** — capped, efficiency-scaled, with a detailed welcome-back summary.
- **Versioned saves** — autosave every 30s, atomic writes, `.bak` backup,
  corruption recovery, migration. (`Ctrl+C`/`Q` always safe.)

## Controls

| Key | Action | Key | Action |
|-----|--------|-----|--------|
| `SPACE` | Fire mining laser | `p` | Galaxy map / planets |
| `1`–`6` | Select target asteroid | `b` | Buildings |
| `n` | Next unlocked planet | `r` | Research tree |
| `o` | Overdrive (energy) | `j` | Missions |
| `s` | Market / sell | `e` | Employees |
| `u` | Upgrades | `a` | Achievements |
| `d` | Drones | `t` | Statistics |
| `f` | Fleet | `v` | Options |
| `x` | Galactic Rebirth | `?` | Help |
| `Q` | Save & quit | | |

## CLI

```
python3 main.py            # play
python3 main.py --reset    # erase save and start fresh
python3 main.py --sim 3600 # headless simulation smoke test (3600 virtual seconds)
```

## Executables

**Windows .exe (no Python needed):**
- Easiest: open the repo's **Actions** tab → *Build Windows EXE* → latest run →
  download the **SPACE_MINER-windows-exe** artifact.
- Or build locally: double-click `build_exe.bat` (needs Python installed);
  the finished game appears at `dist\SPACE_MINER.exe`.

**Any OS (Linux/macOS/Windows), single file:**
```
python3 SPACE_MINER.pyz        # committed at the repo root, zero dependencies
./SPACE_MINER.pyz              # on Linux/macOS
```
Rebuild it after code changes with `./build_pyz.sh`.

## Project layout

```
main.py                     entry point, input handling, main loop
space_miner/
    util.py                 formatting, colors, bars
    data_world.py           minerals, galaxies, planets, asteroids
    data_fleet.py           ships, drones, buildings, upgrades, employees
    data_tech.py            research, missions, achievements, events
    state.py                state creation, derived stats, multipliers, migration
    production.py           passive production math (pure functions)
    mining.py               active mining logic (pure functions)
    economy.py              market drift, selling, auto-sell
    events.py               random events & pirate combat resolution
    offline.py              offline progression & summary
    prestige.py             Galactic Rebirth math
    save.py                 versioned atomic saves with backup/recovery
    game.py                 orchestrator: ticks, actions, missions, achievements
    ui.py                   dashboard rendering (pure string building)
    screens.py              all interactive screens
tests/test_game.py          46 unit tests
```

Save location: `~/.space_miner/save.json` (override with `SPACE_MINER_HOME`).

## Design notes

- **Numbers**: production uses floats with suffix formatting up to `Dc` (1e36),
  then scientific notation — safe for very long progression.
- **Performance**: idle production is computed per planet per tick (a few dozen
  multiplications), never per drone. Asteroids are 6 nodes per planet, not thousands.
- **No pay-to-win, no energy walls**: energy gates only the optional Overdrive
  ability; infrastructure scales it freely.
- **Renewable by design**: asteroids respawn (speed upgradable), so progression
  can never permanently stall.

## Known limitations

- Terminal presentation (ANSI colors, bell for sound) instead of graphical sprites —
  this is a deliberate zero-dependency Python build of the SPACE MINER design.
- Ship levels are tracked per ship type rather than per individual hull.
- Combat is event-driven auto-resolve (fleet defense vs pirate strength), not tactical.
