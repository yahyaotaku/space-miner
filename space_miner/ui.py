"""Dashboard rendering. Pure string building — no input handling."""
from .data_world import (PLANETS, planet, galaxy, mineral_name, mineral_rarity,
                         RARITY_COLORS, MINERALS)
from .data_tech import EVENTS
from .production import planet_rates, total_rates, energy_rate, research_rate
from .state import (mults, xp_needed_player, company_level, storage_cap, drone_count,
                    drone_cap, ship_count, fleet_cap, unlocked_planets, defense_power,
                    planet_hazard, laser_power, crit_chance, offline_capacity_hours)
from .util import fmt, fmt_time, fmt_clock, bar, BOLD, DIM, CYAN, YELLOW, GREEN, MAGENTA, GRAY, WHITE, BRIGHT_CYAN

W = 78


def line(ch="-"):
    return ch * W


def colorize_rarity(text, mid):
    code = RARITY_COLORS[mineral_rarity(mid)]
    return f"\033[{code}m{text}\033[0m"


def header(g):
    s = g.state
    ev = s.get("event")
    ev_txt = ""
    if ev:
        remaining = max(0, int(ev["until"] - g.now))
        ev_txt = f" [{ev['name']}: {ev['desc']} {remaining}s]"
    out = []
    out.append(BOLD(f" SPACE MINER ".center(W, "=")))
    cur = (f" Credits: {YELLOW(fmt(s['credits']))}   Energy: {CYAN(fmt(s['energy']))}   "
           f"Research: {MAGENTA(fmt(s['research_data']))}   Essence: {BRIGHT_CYAN(fmt(s['essence']))}")
    out.append(cur)
    if ev_txt:
        out.append(YELLOW(ev_txt))
    need = xp_needed_player(s["player_level"])
    pl = (f" Player Lv {s['player_level']} [{bar(s['player_xp'] / need)}] "
          f"{fmt(s['player_xp'])}/{fmt(need)} XP   Company Lv {company_level(s['lifetime_credits'])}   "
          f"Uptime {fmt_clock(s['play_time'])}")
    out.append(pl)
    out.append(line())
    return "\n".join(out)


def planet_panel(g):
    s = g.state
    pid = s["selected_planet"]
    info = planet(pid)
    p = s["planets"][pid]
    out = []
    out.append(f" {BOLD(info['name'])} ({galaxy(info['galaxy'])['name']})   "
               f"Dev Lv {p['dev_level']}   Laser {fmt(laser_power(s))}   Crit {crit_chance(s) * 100:.0f}%")
    if info["hazard"]:
        pen = planet_hazard(s, pid) * 100
        out.append(f" {DIM(info['hazard'])} {DIM(f'(current penalty: {pen:.0f}%)')}")
    out.append(f" {DIM('Production this planet:')} {fmt(sum(planet_rates(s, pid).values()))} ore/s")
    out.append("")
    out.append(f"  #  Asteroid        HP            Contents")
    for i, node in enumerate(p["nodes"]):
        sel = ">" if i == s["selected_node"] else " "
        if node["hp"] <= 0:
            remaining = max(0, node["depleted_until"] - g.now)
            out.append(f" {sel}{i + 1:<2} {DIM('regenerating')}  {fmt_time(remaining):<12}")
        else:
            hp = f"{fmt(node['hp'])}/{fmt(node['max_hp'])}"
            frac = node["hp"] / node["max_hp"]
            hp_txt = f"{hp:<12}"
            out.append(f" {sel}{i + 1:<2} {node['size']:<14} {hp_txt} {bar(frac, 10)}  {content_str(node)}")
    return "\n".join(out)


def content_str(node):
    parts = []
    for mid, amt in sorted(node["content"].items(), key=lambda kv: -MINERALS[kv[0]][2]):
        name = mineral_name(mid)
        txt = f"{name} x{amt:.0f}"
        if node["ancient"]:
            txt = MAGENTA(txt)
        parts.append(txt)
    return ", ".join(parts[:3])


def storage_panel(g):
    s = g.state
    cap = storage_cap(s)
    discovered = s.get("discovered", [])
    owned = [(mid, s["resources"].get(mid, 0.0)) for mid in discovered]
    owned = [(m, a) for m, a in owned if a > 0.01]
    out = [f" {BOLD('CARGO HOLD')}  {DIM('(capacity ' + fmt(cap) + ' per resource)')}"]
    if not owned:
        out.append("   (empty - mine some asteroids!)")
        return "\n".join(out)
    cells = []
    for mid, amt in owned:
        pct = min(1.0, amt / cap)
        flag = " FULL" if pct >= 0.999 else ""
        cells.append(colorize_rarity(f"{mineral_name(mid)} {fmt(amt)}{flag}", mid))
    wrapped = [cells[i:i + 4] for i in range(0, len(cells), 4)]
    for row in wrapped:
        out.append("   " + "   ".join(f"{c:<22}" for c in row))
    return "\n".join(out)


def production_panel(g):
    s = g.state
    rates = total_rates(s)
    total = sum(rates.values())
    out = [f" {BOLD('AUTO-PRODUCTION')}  {GREEN(fmt(total) + ' ore/s')}   "
           f"Energy {GREEN('+' + fmt(energy_rate(s)) + '/s')}   "
           f"Research {MAGENTA('+' + fmt(research_rate(s)) + '/s')}   "
           f"Fleet {ship_count(s)}/{fleet_cap(s)}   Drones {drone_count(s)}/{drone_cap(s)}   "
           f"Defense {fmt(defense_power(s))}"]
    if not rates:
        out.append(f"   {DIM('No idle production yet. Buy drones (d) or ships (f) and assign them.')}")
    return "\n".join(out)


def feed_panel(g):
    out = [f" {BOLD('LOG')}"]
    msgs = list(g.feed)[-6:]
    if not msgs:
        out.append(f"   {DIM('Welcome, miner. Press SPACE to fire your laser at the asteroid.')}   ")
    for m in msgs:
        out.append(f"   {m}")
    return "\n".join(out)


MENU = (" [SPACE]Mine [1-6]Target [n]Next planet [o]Overdrive [s]Market [u]pgrades [d]rones [f]leet\n"
        " [p]lanets [b]uildings [r]esearch [j]obs [e]mployees [a]chievements [t]stats [v]options\n"
        " [x]rebirth [?]help [Q]save&quit")


def dashboard(g):
    parts = [header(g), planet_panel(g), line(), production_panel(g), storage_panel(g), feed_panel(g), line(), MENU]
    return "\n".join(parts)


MISSION_OBJECTIVE_LABELS = {
    "mine_ore": "Mine {} ore (lifetime)", "sell_count": "Sell {} resources (lifetime)",
    "buy_upgrade": "Buy {} upgrades", "own_drones": "Own {} drones",
    "own_ships": "Own {} ships", "own_ship_type": "Own {} ship types",
    "player_level": "Reach player level {}", "unlock_planet": "Unlock {} new planets",
    "lifetime_credits": "Earn {} lifetime credits", "building_level": "Reach {} total building levels",
    "research_count": "Complete {} technologies", "ancient_kills": "Destroy {} Ancient asteroids",
    "company_level": "Reach company level {}", "prestige": "Perform {} Galactic Rebirth",
    "destroy": "Destroy {} asteroids (today)",
}


def mission_list(g):
    from .data_tech import MISSIONS
    s = g.state
    out = []
    idx = s["mission_index"]
    for i in range(max(0, idx - 2), min(len(MISSIONS), idx + 8)):
        name, kind, target, rewards = MISSIONS[i]
        val = g._objective_value(kind)
        status = "DONE" if i < idx else ("ACTIVE" if i == idx else "locked")
        rw = ", ".join(f"{fmt(v)} {k}" for k, v in rewards.items())
        if i == idx:
            out.append(f" > {name}: {MISSION_OBJECTIVE_LABELS[kind].format(fmt(target, 0))}")
            out.append(f"     Progress: {fmt(min(val, target), 0)}/{fmt(target, 0)}   Rewards: {rw}")
        elif i < idx:
            out.append(f"   {DIM('[done] ' + name)}")
        else:
            out.append(f"   {DIM('[locked] ???')}")
    out.append("")
    out.append(BOLD(" DAILY MISSIONS"))
    for d in s.get("daily", []):
        mark = "[x]" if d["done"] else "[ ]"
        out.append(f"  {mark} {d['desc']}  ({fmt(min(d['progress'], d['target']), 0)}/{fmt(d['target'], 0)})")
    return "\n".join(out)
