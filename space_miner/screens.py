"""Interactive screens. Each screen loops: tick -> draw -> key -> act."""
from .data_world import (PLANETS, PLANET_IDS, planet, galaxy, GALAXIES, mineral_name,
                         mineral_price, mineral_rarity)
from .data_fleet import (SHIPS, DRONES, BUILDINGS, UPGRADES, EMPLOYEES,
                         SHIP_ORDER, DRONE_ORDER, BUILDING_ORDER, UPGRADE_ORDER,
                         EMPLOYEE_ORDER)
from .data_tech import RESEARCH, RESEARCH_ORDER, BRANCHES, BRANCH_NAMES, ACHIEVEMENTS
from .state import (mults, storage_cap, cost_of_ship, cost_of_drone, cost_of_building,
                    cost_of_upgrade, cost_of_employee, drone_count, drone_cap,
                    ship_count, fleet_cap, unlocked_planets, unlocked_galaxies,
                    company_level, defense_power, offline_capacity_hours,
                    offline_efficiency, laser_power, crit_chance, essence_mult,
                    building_level, has_research, ESSENCE_UPGRADES, ESSENCE_UPGRADE_ORDER,
                    cost_of_essence_upgrade, planet_hazard)
from .production import planet_rates, total_rates, energy_rate, research_rate
from .economy import price, sell
from .prestige import rebirth_preview, can_rebirth, REBIRTH_THRESHOLD
from . import ui
from .util import fmt, fmt_time, bar, BOLD, DIM, CYAN, YELLOW, GREEN, MAGENTA, GRAY, RED, BRIGHT_CYAN

KEYS = "1234567890acdefghijklmnopqrstuvwxyz"


def key_for(i):
    return KEYS[i] if i < len(KEYS) else "?"


class Screen:
    def __init__(self, g, io):
        self.g = g
        self.io = io

    def run(self, title, render, handlers, hint="b: back"):
        while True:
            self.g.tick()
            self.io.clear()
            print(ui.header(self.g))
            print(BOLD(f" {title} ".ljust(ui.W, "-")))
            print(render())
            print(f" {DIM(hint)}")
            key = self.io.read_key()
            if key in ("b", "escape", "\x1b"):
                return
            fn = handlers.get(key)
            if fn:
                fn()


def confirm(io, prompt):
    io.clear()
    print(BOLD(prompt))
    print(" Type YES to confirm, anything else to cancel.")
    return io.read_line().strip().upper() == "YES"


# ---------------------------------------------------------------- market

def market_screen(g, io):
    scr = Screen(g, io)
    s = g.state

    def render():
        out = [f" {'RESOURCE':<18}{'RARITY':<11}{'HELD':>10}{'PRICE':>10}{'VALUE':>12}",
               ""]
        cap = storage_cap(s)
        for i, mid in enumerate(s["discovered"]):
            held = s["resources"].get(mid, 0.0)
            p = price(s, mid)
            key = key_for(i)
            out.append(f" [{key}] {mineral_name(mid):<16}{mineral_rarity(mid):<11}"
                       f"{fmt(held):>10}{fmt(p):>10}{fmt(held * p):>12}")
        out.append("")
        out.append(f" [A] Sell entire hold      [T] Toggle auto-sell "
                   f"({'ON' if s['settings']['autosell'] else 'off'}"
                   f"{'' if has_research(s, 'market_ai') or 'autosell' in s['upgrades'] else ' - LOCKED (Market AI research or upgrade)'})")
        return "\n".join(out)

    def make_handler(mid):
        def fn():
            gained = g.sell_resource(mid)
            io.notify(g, f"Sold {mineral_name(mid)} for {fmt(gained)} credits." if gained else "Nothing to sell.")
        return fn

    def sell_all_fn():
        gained = g.sell_everything()
        io.notify(g, f"Sold hold for {fmt(gained)} credits." if gained else "Hold is empty.")

    def toggle_autosell():
        if not (has_research(s, "market_ai") or "autosell" in s["upgrades"]):
            io.notify(g, "Auto-sell is locked. Research Market AI or buy the Market AI upgrade.")
            return
        s["settings"]["autosell"] = not s["settings"]["autosell"]
        io.notify(g, f"Auto-sell {'enabled' if s['settings']['autosell'] else 'disabled'}.")

    handlers = {key_for(i): make_handler(mid) for i, mid in enumerate(s["discovered"])}
    handlers["a"] = sell_all_fn
    handlers["t"] = toggle_autosell
    scr.run("MARKET", render, handlers)


# ---------------------------------------------------------------- upgrades

def upgrades_screen(g, io):
    scr = Screen(g, io)
    s = g.state

    def render():
        out = []
        for i, uid in enumerate(UPGRADE_ORDER):
            u = UPGRADES[uid]
            lvl = s["upgrades"].get(uid, 0)
            cost = cost_of_upgrade(s, uid)
            maxed = lvl >= u["max"]
            afford = s["credits"] >= cost
            status = "MAX" if maxed else (f"{fmt(cost)} cr" if afford else DIM(f"{fmt(cost)} cr"))
            out.append(f" [{key_for(i)}] {u['name']:<18} Lv {lvl:>2}/{u['max']:<2}  {status:<14} {u['desc']}")
        return "\n".join(out)

    def make_handler(uid):
        def fn():
            ok, msg = g.buy_upgrade(uid)
            if not ok:
                io.notify(g, msg)
        return fn

    handlers = {key_for(i): make_handler(uid) for i, uid in enumerate(UPGRADE_ORDER)}
    scr.run("UPGRADES", render, handlers)


# ---------------------------------------------------------------- drones

def drones_screen(g, io):
    scr = Screen(g, io)
    s = g.state

    def render():
        out = [f" Drones: {drone_count(s)}/{drone_cap(s)} bays used   "
               f"Mining drones assigned to: {planet(s['drones'].get('mining', {}).get('planet') or s['selected_planet'])['name']}", ""]
        for i, did in enumerate(DRONE_ORDER):
            d = DRONES[did]
            entry = s["drones"].get(did, {"count": 0, "level": 1})
            cost = cost_of_drone(s, did)
            afford = s["credits"] >= cost and drone_count(s) < drone_cap(s)
            status = f"{fmt(cost)} cr" if afford else DIM(f"{fmt(cost)} cr")
            out.append(f" [{key_for(i)}] {d['name']:<16} x{entry['count']:<3} Lv {entry['level']:<3} {status:<14} {d['desc']}")
        out.append("")
        out.append(" [z] Reassign mining drones to another planet")
        return "\n".join(out)

    def make_handler(did):
        def fn():
            ok, msg = g.buy_drone(did)
            if not ok:
                io.notify(g, msg)
        return fn

    def reassign():
        choose_planet(g, io, lambda pid: g.assign_drones("mining", pid))

    handlers = {key_for(i): make_handler(did) for i, did in enumerate(DRONE_ORDER)}
    handlers["z"] = reassign
    scr.run("DRONE BAY", render, handlers)


# ---------------------------------------------------------------- fleet

def fleet_screen(g, io):
    scr = Screen(g, io)
    s = g.state

    def render():
        out = [f" Fleet: {ship_count(s)}/{fleet_cap(s)} ships   Defense: {fmt(defense_power(s))}", ""]
        for i, sid in enumerate(SHIP_ORDER):
            sh = SHIPS[sid]
            entry = s["ships"].get(sid, {"count": 0, "level": 1, "planet": None})
            locked = s["player_level"] < sh["unlock_level"]
            cost = cost_of_ship(s, sid)
            if locked:
                status = DIM(f"LOCKED - player level {sh['unlock_level']}")
            elif s["credits"] >= cost and ship_count(s) < fleet_cap(s):
                status = f"{fmt(cost)} cr"
            else:
                status = DIM(f"{fmt(cost)} cr")
            where = planet(entry["planet"])["name"] if entry.get("planet") else "unassigned"
            out.append(f" [{key_for(i)}] {sh['name']:<18} x{entry['count']:<2} Lv {entry['level']:<3} "
                       f"@ {where:<12} {status:<24} {DIM(sh['desc'] if not locked else '')}")
        out.append("")
        out.append(" [z] Reassign a ship type to another planet (then pick ship, then planet)")
        return "\n".join(out)

    def make_handler(sid):
        def fn():
            ok, msg = g.buy_ship(sid)
            if not ok:
                io.notify(g, msg)
        return fn

    def reassign():
        types = [sid for sid in SHIP_ORDER if s["ships"].get(sid, {}).get("count", 0) > 0]
        if not types:
            io.notify(g, "You own no ships yet.")
            return
        io.notify(g, "Pick a ship type:")
        for i, sid in enumerate(types):
            io.echo(f"  [{key_for(i)}] {SHIPS[sid]['name']}")
        k = io.read_key()
        idx = KEYS.find(k)
        if idx < 0 or idx >= len(types):
            return
        choose_planet(g, io, lambda pid: g.assign_ship(types[idx], pid))

    handlers = {key_for(i): make_handler(sid) for i, sid in enumerate(SHIP_ORDER)}
    handlers["z"] = reassign
    scr.run("FLEET COMMAND", render, handlers)


def choose_planet(g, io, then):
    pids = unlocked_planets(g.state)
    if not pids:
        io.notify(g, "No planets unlocked.")
        return
    io.notify(g, "Choose a planet:")
    for i, pid in enumerate(pids):
        io.echo(f"  [{key_for(i)}] {planet(pid)['name']}")
    k = io.read_key()
    idx = KEYS.find(k)
    if 0 <= idx < len(pids):
        then(pids[idx])
        io.notify(g, f"Assigned to {planet(pids[idx])['name']}.")


# ---------------------------------------------------------------- planets & galaxy

def galaxy_screen(g, io):
    scr = Screen(g, io)
    s = g.state

    def render():
        out = []
        for gid in [g_["id"] for g_ in GALAXIES]:
            info = galaxy(gid)
            unlocked = gid in unlocked_galaxies(s)
            tag = GREEN("UNLOCKED") if unlocked else RED("LOCKED")
            rich = f"richness x{info['richness']}  difficulty x{info['difficulty']}"
            out.append(f" {BOLD(info['name'])}  {tag}  {DIM(rich)}")
            if not unlocked:
                req = f"Requires {fmt(info['unlock_credits'])} lifetime credits and player level {info['unlock_level']}"
                out.append(f"    {DIM(req)}")
            for pid in PLANET_IDS:
                if PLANETS[pid][1] != gid:
                    continue
                pinfo = planet(pid)
                pstate = s["planets"][pid]
                if pstate["unlocked"]:
                    rates = sum(planet_rates(s, pid).values())
                    out.append(f"    - {pinfo['name']:<12} {DIM('dev lv ' + str(pstate['dev_level']))}  "
                               f"{DIM(', '.join(m.replace('_', ' ').title() for m in pinfo['weights']))}  "
                               f"{GREEN(fmt(rates) + ' ore/s')}")
                else:
                    can = s["lifetime_credits"] >= pinfo["unlock_credits"] and s["player_level"] >= pinfo["unlock_level"]
                    mark = "*" if can else " "
                    out.append(f"   [{mark}] {pinfo['name']:<12} {DIM('unlock: ' + fmt(pinfo['unlock_credits']) + ' cr, lv ' + str(pinfo['unlock_level']))}")
        out.append("")
        out.append(" [*] = eligible. Press the planet's marker key to claim it.")
        return "\n".join(out)

    handlers = {}
    idx = 0
    for pid in PLANET_IDS:
        if not s["planets"][pid]["unlocked"]:
            handlers[key_for(idx)] = _make_unlock(g, io, pid)
            idx += 1
    scr.run("GALAXY MAP", render, handlers)


def _make_unlock(g, io, pid):
    def fn():
        ok, msg = g.unlock_planet(pid)
        if not ok:
            io.notify(g, msg)
    return fn


# ---------------------------------------------------------------- buildings

def buildings_screen(g, io):
    scr = Screen(g, io)
    s = g.state
    pid = s["selected_planet"]

    def render():
        pinfo = planet(pid)
        out = [f" Construction on {BOLD(pinfo['name'])}", ""]
        for i, bid in enumerate(BUILDING_ORDER):
            b = BUILDINGS[bid]
            lvl = building_level(s, pid, bid)
            cost = cost_of_building(s, pid, bid)
            afford = s["credits"] >= cost
            status = f"{fmt(cost)} cr" if afford else DIM(f"{fmt(cost)} cr")
            out.append(f" [{key_for(i)}] {b['name']:<16} Lv {lvl:<3} {status:<16} {b['desc']}")
        return "\n".join(out)

    def make_handler(bid):
        def fn():
            ok, msg = g.build(pid, bid)
            if not ok:
                io.notify(g, msg)
        return fn

    handlers = {key_for(i): make_handler(bid) for i, bid in enumerate(BUILDING_ORDER)}
    scr.run("BUILDINGS", render, handlers)


# ---------------------------------------------------------------- research

def research_screen(g, io):
    scr = Screen(g, io)
    s = g.state
    order = [rid for rid in RESEARCH_ORDER]

    def render():
        out = [f" Research data: {MAGENTA(fmt(s['research_data']))}   "
               f"Generation: {fmt(research_rate(s))}/s", ""]
        for branch in BRANCHES:
            out.append(BOLD(f" {BRANCH_NAMES[branch]}"))
            for i, rid in enumerate(order):
                info = RESEARCH[rid]
                if info[0] != branch:
                    continue
                done = rid in s["research"]
                avail = all(p in s["research"] for p in info[4])
                cost = info[3]
                if done:
                    out.append(f"   {GREEN('[x] ' + info[2] + ' - ' + info[7])}")
                elif avail:
                    afford = s["research_data"] >= cost
                    tag = f"[{key_for(order.index(rid))}] {info[2]} ({fmt(cost)} data)"
                    out.append(f"   {tag}  {info[7]}" if afford else f"   {DIM(tag)}  {DIM(info[7])}")
                else:
                    missing = ", ".join(RESEARCH[p][2] for p in info[4] if p not in s["research"])
                    out.append(f"   {DIM('[ ] ' + info[2] + '  (needs: ' + missing + ')')}")
            out.append("")
        return "\n".join(out)

    def make_handler(rid):
        def fn():
            ok, msg = g.research(rid)
            if not ok:
                io.notify(g, msg)
        return fn

    handlers = {}
    for i, rid in enumerate(order):
        info = RESEARCH[rid]
        if rid not in s["research"] and all(p in s["research"] for p in info[4]):
            handlers[key_for(i)] = make_handler(rid)
    scr.run("RESEARCH TREE", render, handlers)


# ---------------------------------------------------------------- employees

def employees_screen(g, io):
    scr = Screen(g, io)
    s = g.state

    def render():
        out = []
        for i, eid in enumerate(EMPLOYEE_ORDER):
            e = EMPLOYEES[eid]
            count = s["employees"].get(eid, 0)
            cost = cost_of_employee(s, eid)
            afford = s["credits"] >= cost
            status = f"{fmt(cost)} cr" if afford else DIM(f"{fmt(cost)} cr")
            out.append(f" [{key_for(i)}] {e['name']:<20} x{count:<3} {status:<16} {e['desc']}")
        return "\n".join(out)

    def make_handler(eid):
        def fn():
            ok, msg = g.hire(eid)
            if not ok:
                io.notify(g, msg)
        return fn

    handlers = {key_for(i): make_handler(eid) for i, eid in enumerate(EMPLOYEE_ORDER)}
    scr.run("CREW LOUNGE", render, handlers)


# ---------------------------------------------------------------- info screens

def missions_screen(g, io):
    scr = Screen(g, io)
    scr.run("MISSIONS", lambda: ui.mission_list(g), {}, hint="b: back")


def achievements_screen(g, io):
    scr = Screen(g, io)
    s = g.state

    def render():
        out = []
        done = 0
        for aid, name, desc, reward, key, value in ACHIEVEMENTS:
            earned = aid in s["achievements"]
            if earned:
                done += 1
            mark = GREEN("[x]") if earned else DIM("[ ]")
            txt = f" {mark} {name}: {desc}"
            out.append(txt if earned else DIM(f" {mark} ??? - {desc}"))
        out.insert(0, f" Achievements: {done}/{len(ACHIEVEMENTS)}")
        out.insert(1, "")
        return "\n".join(out)

    scr.run("ACHIEVEMENTS", render, {}, hint="b: back")


def stats_screen(g, io):
    scr = Screen(g, io)
    s = g.state

    def render():
        from .state import essence_mult
        rates = total_rates(s)
        out = [
            f" Lifetime credits earned : {fmt(s['lifetime_credits'])}",
            f" Lifetime ore mined      : {fmt(s['ore_mined'])}",
            f" Lifetime ore sold       : {fmt(s['ore_sold'])}",
            f" Asteroids destroyed     : {s['kills']} ({s['ancient_kills']} Ancient)",
            f" Missions completed      : {s['missions_done']}",
            f" Events survived         : {s['events_survived']} (pirates beaten: {s['pirates_defeated']})",
            f" Rebirths                : {s['prestige_count']}   Lifetime essence: {fmt(s['lifetime_essence'])}",
            f" Player level            : {s['player_level']}   Company level: {company_level(s['lifetime_credits'])}",
            f" Laser power             : {fmt(laser_power(s))}   Crit: {crit_chance(s) * 100:.0f}%",
            f" Idle production         : {fmt(sum(rates.values()))} ore/s",
            f" Energy / research rates : {fmt(energy_rate(s))}/s, {fmt(research_rate(s))}/s",
            f" Storage capacity        : {fmt(storage_cap(s))} per resource",
            f" Offline                 : {offline_capacity_hours(s)}h capacity, {offline_efficiency(s) * 100:.0f}% efficiency",
            f" Essence bonus           : x{essence_mult(s):.2f} production & sell prices",
            f" Fleet / drones          : {ship_count(s)}/{fleet_cap(s)}, {drone_count(s)}/{drone_cap(s)}",
            f" Defense power           : {fmt(defense_power(s))}",
        ]
        return "\n".join(out)

    scr.run("STATISTICS", render, {}, hint="b: back")


def settings_screen(g, io):
    scr = Screen(g, io)
    s = g.state

    def render():
        st = s["settings"]
        out = [
            f" [1] Auto-sell surplus     : {'ON' if st['autosell'] else 'OFF'}"
            f"{'' if (has_research(s, 'market_ai') or 'autosell' in s['upgrades']) else '  (locked - needs Market AI)'}",
            f" [2] Auto-sell threshold   : {st['autosell_threshold'] * 100:.0f}% of storage",
            f" [3] Sound (terminal bell) : {'ON' if st['sound'] else 'OFF'}",
            f" [4] Colors                : {'ON' if st['colors'] else 'OFF'}",
            f" [5] Save now",
            f" [6] Erase save and restart  {RED('(dangerous)')}",
        ]
        return "\n".join(out)

    def toggle_autosell():
        if not (has_research(s, "market_ai") or "autosell" in s["upgrades"]):
            io.notify(g, "Locked: research Market AI or buy the Market AI upgrade.")
            return
        s["settings"]["autosell"] = not s["settings"]["autosell"]

    def threshold():
        st = s["settings"]
        st["autosell_threshold"] = 0.5 if st["autosell_threshold"] >= 0.95 else st["autosell_threshold"] + 0.1

    def toggle_colors():
        from .util import Colors
        s["settings"]["colors"] = not s["settings"]["colors"]
        Colors.enabled = s["settings"]["colors"] and io.is_tty

    def erase():
        if confirm(io, "ERASE SAVE AND RESTART? All progress will be lost."):
            from .state import new_state
            g.state = new_state(g.now)
            g.feed.clear()
            g.log("Fresh start. Good luck, miner.")
            io.notify(g, "Save erased.")

    handlers = {
        "1": toggle_autosell, "2": threshold, "3": lambda: s["settings"].__setitem__("sound", not s["settings"]["sound"]),
        "4": toggle_colors, "5": lambda: io.notify(g, "Saved." if g.save() else "Save failed!"),
        "6": erase,
    }
    scr.run("OPTIONS", render, handlers)


def rebirth_screen(g, io):
    scr = Screen(g, io)
    s = g.state

    def render():
        lines, gain = rebirth_preview(s)
        out = list(lines)
        out.append("")
        out.append(BOLD(" ESSENCE UPGRADES (permanent):"))
        for i, uid in enumerate(ESSENCE_UPGRADE_ORDER):
            u = ESSENCE_UPGRADES[uid]
            lvl = s["essence_upgrades"].get(uid, 0)
            cost = cost_of_essence_upgrade(s, uid)
            maxed = lvl >= u["max"]
            status = "MAX" if maxed else f"{cost} essence"
            out.append(f" [{key_for(i)}] {u['name']:<16} Lv {lvl}/{u['max']}  {status}  {u['desc']}")
        if can_rebirth(s):
            out.append("")
            out.append(" [R] INITIATE GALACTIC REBIRTH (asks for confirmation)")
        return "\n".join(out)

    def make_handler(uid):
        def fn():
            ok, msg = g.buy_essence_upgrade(uid)
            if not ok:
                io.notify(g, msg)
        return fn

    def do_rebirth():
        lines, gain = rebirth_preview(s)
        io.clear()
        print("\n".join(lines))
        print()
        print(BOLD(f" Are you absolutely sure? Type REBIRTH to confirm."))
        if io.read_line().strip().upper() == "REBIRTH":
            gain = g.do_rebirth()
            io.notify(g, f"The stars realign. +{gain} Stellar Essence.")

    handlers = {key_for(i): make_handler(uid) for i, uid in enumerate(ESSENCE_UPGRADE_ORDER)}
    if can_rebirth(s):
        handlers["r"] = do_rebirth
    scr.run("GALACTIC REBIRTH", render, handlers)


def help_screen(g, io):
    scr = Screen(g, io)
    text = "\n".join([
        " HOW TO PLAY",
        "",
        " 1. Press SPACE (or m) to fire your mining laser at the selected asteroid.",
        " 2. Destroy asteroids to collect minerals, then sell them in the Market (s).",
        " 3. Spend credits in Upgrades (u): laser power first, then storage.",
        " 4. Buy Mining Drones (d) and assign them - they mine while you are away.",
        " 5. Buy ships (f) for bigger passive production and fleet defense.",
        " 6. Build structures (b) on planets: stations boost production, labs make research.",
        " 7. Spend research data in the Research Tree (r) for powerful multipliers.",
        " 8. Unlock new planets in the Galaxy Map (p) for rarer, pricier minerals.",
        " 9. Follow Missions (j) - they guide progression and pay well.",
        " 10. At 1B lifetime credits, perform a Galactic Rebirth (x) for permanent power.",
        "",
        " Tips:",
        " - Storage caps production. Sell often or research Market AI for auto-sell.",
        " - Ancient asteroids (rare, purple) hold the rarest minerals and research data.",
        " - Pirates attack during events. Defender ships and Guardian drones protect you.",
        " - The game autosaves every 30s and grants offline production when you return.",
    ])
    scr.run("HELP", lambda: text, {}, hint="b: back")
