"""Passive production math. Pure functions over state — no I/O, fully testable."""
from .data_world import planet_minerals, PLANETS
from .data_fleet import SHIPS, DRONES
from .state import (mults, unit_level_mult, building_level, planet_production_mult,
                    planet_hazard, storage_cap)


def planet_rates(s, pid):
    """Ore/s per resource produced by drones + ships assigned to a planet."""
    if not s["planets"][pid]["unlocked"]:
        return {}
    m = mults(s)
    eff = planet_production_mult(s, pid)
    rates = {}
    drones = s["drones"].get("mining", {})
    if drones.get("count", 0) and drones.get("planet") == pid:
        per = DRONES["mining"]["rate"] * unit_level_mult(drones["level"])
        total = drones["count"] * per * m["drone"] * eff
        for mid, share in planet_minerals(pid).items():
            rates[mid] = rates.get(mid, 0.0) + total * share
    drones_total = sum(d.get("count", 0) for d in s["drones"].values())
    for sid, info in s["ships"].items():
        if info.get("count", 0) and info.get("planet") == pid:
            per = SHIPS[sid]["rate"] * unit_level_mult(info["level"])
            total = info["count"] * per * m["ship"] * eff
            for mid, share in planet_minerals(pid).items():
                rates[mid] = rates.get(mid, 0.0) + total * share
    return rates


def total_rates(s):
    out = {}
    for pid in PLANETS:
        for mid, r in planet_rates(s, pid).items():
            out[mid] = out.get(mid, 0.0) + r
    return out


def energy_rate(s):
    m = mults(s)
    base = 0.2
    plants = 2.0 * _btotal(s, "energy_plant")
    return (base + plants) * m["energy"]


def research_rate(s):
    m = mults(s)
    base = 0.05
    labs = 0.3 * _btotal(s, "laboratory")
    ships = sum(info["count"] * SHIPS[sid]["research"] * unit_level_mult(info["level"])
                for sid, info in s["ships"].items() if info.get("count"))
    return (base + labs + ships) * m["research"]


def _btotal(s, bid):
    return sum(v for k, v in s["buildings"].items() if k.endswith(":" + bid))


def apply_production(s, dt):
    """Advance passive production by dt seconds. Returns summary dict."""
    produced = {}
    full = []
    caps_hit = False
    for pid in PLANETS:
        rates = planet_rates(s, pid)
        if not rates:
            continue
        for mid, rate in rates.items():
            if rate <= 0:
                continue
            cap = storage_cap(s)
            current = s["resources"].get(mid, 0.0)
            space = max(0.0, cap - current)
            gained = min(rate * dt, space)
            if gained > 0:
                s["resources"][mid] = current + gained
                produced[mid] = produced.get(mid, 0.0) + gained
                _grant_planet_xp(s, pid, gained * 0.1)
                _grant_drone_xp(s, gained * 0.1)
            if current + rate * dt > cap and rate > 0:
                caps_hit = True
                full.append(mid)
    s["energy"] = min(s["energy"] + energy_rate(s) * dt, 500 + 100 * _btotal(s, "energy_plant"))
    s["research_data"] += research_rate(s) * dt
    return {"produced": produced, "full": sorted(set(full)), "caps_hit": caps_hit}


def _grant_planet_xp(s, pid, xp):
    p = s["planets"][pid]
    p["xp"] += xp
    from .state import xp_needed_planet
    while p["xp"] >= xp_needed_planet(p["dev_level"]):
        p["xp"] -= xp_needed_planet(p["dev_level"])
        p["dev_level"] += 1


def _grant_drone_xp(s, xp):
    d = s["drones"].get("mining", {})
    if not d.get("count"):
        return
    d["xp"] = d.get("xp", 0.0) + xp
    from .state import xp_needed_unit
    while d["xp"] >= xp_needed_unit(d["level"]):
        d["xp"] -= xp_needed_unit(d["level"])
        d["level"] += 1
