"""Game state: creation, derived stats, multiplier aggregation, migration.

The state is a plain dict (JSON-friendly). All mutation goes through Game.
"""
import random

from .data_world import (NODES_PER_PLANET, PLANET_IDS, PLANETS, GALAXIES,
                         roll_asteroid, mineral_rarity, RARITY_ORDER, MINERALS, galaxy)
from .data_fleet import SHIPS, DRONES, BUILDINGS, EMPLOYEES, EMPLOYEE_COST_MULT
from .data_tech import MISSIONS, ACHIEVEMENTS, RESEARCH
from .util import clamp

SAVE_VERSION = 3

ESSENCE_UPGRADES = {
    "start_credits":  {"name": "Seed Capital",   "max": 5, "desc": "Start each rebirth with 10K x 10^lvl credits."},
    "keep_research":  {"name": "Archived Data",  "max": 3, "desc": "Keep 25% research data per level after rebirth."},
    "offline_master": {"name": "Dream Network",  "max": 2, "desc": "+25% offline efficiency per level."},
    "rare_luck":      {"name": "Fortune Sense",  "max": 3, "desc": "+60% Ancient asteroid chance per level."},
    "essence_gain":   {"name": "Soul Harvest",   "max": 4, "desc": "+25% Stellar Essence gain per level."},
    "veteran_fleet":  {"name": "Veteran Fleet",  "max": 2, "desc": "New ships & drones start at level 5x lvl."},
}
ESSENCE_UPGRADE_ORDER = list(ESSENCE_UPGRADES.keys())
ESSENCE_COST = lambda lvl: 2 ** lvl  # noqa: E731


def new_state(now):
    s = {
        "version": SAVE_VERSION,
        "created_at": now,
        "last_save": now,
        "last_tick": now,
        "play_time": 0.0,
        # currencies
        "credits": 50.0, "energy": 10.0, "research_data": 0.0, "essence": 0.0,
        "lifetime_credits": 0.0,
        # player / company
        "player_level": 1, "player_xp": 0.0,
        # inventory
        "resources": {},
        "discovered": ["iron", "copper", "silicon"],
        # ownership: id -> {"count","level","xp","planet"}
        "ships": {}, "drones": {},
        "planets": {}, "buildings": {},
        "research": [], "upgrades": {}, "employees": {},
        "essence_upgrades": {},
        "prestige_count": 0, "lifetime_essence": 0.0,
        # missions
        "mission_index": 0,
        "daily_date": "", "daily": [],
        # counters (stats)
        "ore_mined": 0.0, "ore_sold": 0.0, "kills": 0, "ancient_kills": 0,
        "missions_done": 0, "events_survived": 0, "pirates_defeated": 0,
        "session_mined": 0.0,
        # world
        "event": None, "next_event_at": now + 120.0,
        "overdrive_until": 0.0,
        "selected_planet": "asteroid_01",
        "selected_node": 0,
        # settings
        "settings": {"autosell": False, "autosell_threshold": 0.8,
                     "sound": True, "colors": True, "tips": True},
        "achievements": [],
        "log": [],
    }
    for pid in PLANET_IDS:
        s["planets"][pid] = _new_planet_state(now, pid)
    _roll_dailies(s, "1970-01-01")
    return s


def _new_planet_state(now, pid):
    # Stable seed: random.Random(str) is deterministic across processes,
    # unlike hash() which is salted per process.
    rng = random.Random("nodes:" + pid)
    nodes = [roll_asteroid(rng, pid) for _ in range(NODES_PER_PLANET)]
    return {"unlocked": pid == "asteroid_01", "dev_level": 1, "xp": 0.0, "nodes": nodes}


def _roll_dailies(s, date_str):
    import random as _r
    rng = _r.Random("daily-" + date_str)
    from .data_tech import DAILY_TEMPLATES
    picks = rng.sample(DAILY_TEMPLATES, 3)
    s["daily_date"] = date_str
    s["daily"] = [{"kind": k, "target": n * (3 ** s["prestige_count"]), "base": n,
                   "progress": 0.0, "done": False,
                   "desc": d.format(n=fmt_target(n * (3 ** s["prestige_count"])))}
                  for k, n, d in picks]


def fmt_target(n):
    from .util import fmt
    return fmt(n, 0)


# ---------------------------------------------------------------- derived

def xp_needed_player(level):
    return 80 * 1.4 ** (level - 1)


def xp_needed_unit(level):
    return 50 * 1.3 ** (level - 1)


def xp_needed_planet(level):
    return 200 * 1.5 ** (level - 1)


def company_level(lifetime_credits):
    import math
    if lifetime_credits < 1000:
        return 1
    return 1 + max(0, int(math.log10(lifetime_credits / 1000)))


def unit_level_mult(level):
    return 1.12 ** (level - 1)


def laser_power(s):
    base = 5.0 * 1.6 ** s["upgrades"].get("laser_power", 0)
    return base * mults(s)["laser"]


def crit_chance(s):
    base = 0.05 + 0.02 * s["upgrades"].get("crit_chance", 0)
    base += 0.015 * s["drones"].get("scanner", {}).get("count", 0)
    base += mults(s)["crit"]
    return clamp(base, 0.0, 0.85)


def essence_mult(s):
    return 1.0 + 0.02 * s["essence"]


def drone_count(s):
    return sum(d["count"] for d in s["drones"].values())


def drone_cap(s):
    cap = 10 + 3 * s["upgrades"].get("drone_cap", 0)
    cap += sum(v for k, v in _effect_values(s, "drone_cap"))
    cap += _building_total(s, "command_center")
    return int(cap)


def ship_count(s):
    return sum(v["count"] for v in s["ships"].values())


def fleet_cap(s):
    cap = 6 + 2 * s["upgrades"].get("fleet_cap", 0)
    cap += sum(v for k, v in _effect_values(s, "fleet_cap"))
    cap += 2 * _building_total(s, "shipyard")
    return int(cap)


def storage_cap(s, resource=None):
    cap = 100.0
    cap *= 1 + 0.5 * s["upgrades"].get("storage", 0)
    cap *= 1 + 0.08 * s["drones"].get("cargo", {}).get("count", 0)
    cap *= 1 + 0.20 * _building_total(s, "warehouse")
    cap *= 1 + 0.06 * s["employees"].get("logistics", 0)
    cap *= mults(s)["storage"]
    return cap


def offline_capacity_hours(s):
    return 2 + 2 * s["upgrades"].get("offline_cap", 0)


def offline_efficiency(s):
    eff = 0.5 + 0.05 * s["upgrades"].get("offline_eff", 0)
    eff += 0.25 * s["essence_upgrades"].get("offline_master", 0)
    return clamp(eff, 0.0, 1.0)


def building_level(s, pid, bid):
    return s["buildings"].get(f"{pid}:{bid}", 0)


def _building_total(s, bid):
    return sum(v for k, v in s["buildings"].items() if k.endswith(":" + bid))


def _effect_values(s, key):
    return [(rid, RESEARCH[rid][6]) for rid in s["research"] if RESEARCH[rid][5] == key]


def _effect_sum(s, key, default=0.0):
    return sum(v for _k, v in _effect_values(s, key)) if _effect_values(s, key) else default


def has_research(s, rid):
    return rid in s["research"]


def research_mult(s):
    m = 1.0 + _effect_sum(s, "research_mult")
    m *= 1 + 0.03 * s["employees"].get("scientist", 0)
    m *= event_mult(s, "research_mult")
    return m


def hazard_mitigation(s, pid):
    """0..1 fraction of the planet hazard penalty that is removed."""
    drones = s["drones"].get("repair", {}).get("count", 0)
    mitig = drones * 0.03 + 0.05 * building_level(s, pid, "mining_station")
    return clamp(mitig, 0.0, 1.0)


def planet_hazard(s, pid):
    hazard = PLANETS[pid][5]
    if not hazard:
        return 0.0
    penalties = {"Lava storms": 0.15, "Deep freeze": 0.20, "Solar flares": 0.25,
                 "Quantum fog": 0.30, "Iron dust": 0.20, "Magnetic shear": 0.25,
                 "Blinding light": 0.30, "Ion vortices": 0.30, "Light hunger": 0.35,
                 "Prismatic storms": 0.35, "Ancient wards": 0.40, "Null silence": 0.45,
                 "Echoing screams": 0.45, "Gravity shear": 0.50, "Eventide horizon": 0.50,
                 "Crucible storms": 0.55}
    name = hazard.split(":")[0].strip()
    base = penalties.get(name, 0.2)
    return base * (1.0 - hazard_mitigation(s, pid))


def event_mult(s, kind):
    ev = s.get("event")
    if not ev or ev["kind"] != kind:
        return 1.0
    return 1.0 + ev["value"]


def mults(s):
    """Aggregate every multiplier in one place. Cached per call is fine (cheap)."""
    res = s["research"]
    def esum(key, default=0.0):
        vals = [RESEARCH[r][6] for r in res if RESEARCH[r][5] == key]
        return sum(vals) if vals else default

    all_m = 1.0 + esum("all_mult")
    all_m *= 1 + 0.02 * (company_level(s["lifetime_credits"]) - 1)
    all_m *= essence_mult(s)

    drone = 1.0 + esum("drone_mult")
    ship = 1.0 + esum("ship_mult")
    ship *= 1 + 0.03 * s["employees"].get("pilot", 0)
    mining = 1.0 + 0.02 * s["employees"].get("engineer", 0)
    mining *= event_mult(s, "mine_mult")
    laser = (1.0 + esum("laser_mult")) * all_m * mining
    sell = (1.0 + esum("sell_mult")
            + 0.05 * s["upgrades"].get("market_insight", 0)
            + 0.04 * _building_total(s, "refinery")
            + 0.03 * _building_total(s, "trading_hub"))
    sell *= event_mult(s, "sell_mult")
    energy = (1.0 + esum("energy_mult")) * event_mult(s, "energy_mult")
    research = research_mult(s)
    storage = 1.0 + esum("storage_mult")
    crit = esum("crit")
    rare = 1.0 + esum("rare_luck")
    respawn = 1.0 - esum("respawn")
    build_cost = 1.0 - min(0.45, 0.015 * s["employees"].get("mechanic", 0) + esum("build_cost"))
    essence_gain = 1.0 + esum("essence_gain") + 0.25 * s["essence_upgrades"].get("essence_gain", 0)

    return {
        "all": all_m, "drone": drone * all_m, "ship": ship * all_m,
        "laser": laser,
        "mining": mining * all_m, "sell": sell, "energy": energy,
        "research": research, "storage": storage, "crit": crit,
        "rare_luck": rare * (1 + 0.6 * s["essence_upgrades"].get("rare_luck", 0)),
        "respawn": max(0.2, respawn), "build_cost": build_cost,
        "essence_gain": essence_gain,
    }


def planet_production_mult(s, pid):
    m = mults(s)["mining"]
    m *= 1 + 0.08 * building_level(s, pid, "mining_station")
    m *= 1 + 0.03 * (s["planets"][pid]["dev_level"] - 1)
    m *= 1.0 - planet_hazard(s, pid)
    if s.get("overdrive_until", 0) > s["last_tick"]:
        m *= 2.0
    return m


def defense_power(s):
    d = 8 * s["drones"].get("guardian", {}).get("count", 0)
    d += 10 * s["employees"].get("security", 0)
    for sid, info in s["ships"].items():
        d += SHIPS[sid]["defense"] * info["count"] * unit_level_mult(info["level"])
    return d


def cost_of_ship(s, sid):
    base = SHIPS[sid]["cost"]
    count = s["ships"].get(sid, {}).get("count", 0)
    base *= 1.25 ** count
    base *= mults(s)["build_cost"]
    base *= 1 - min(0.4, 0.02 * s["ships"].get("industrial", {}).get("count", 0))
    return base


def cost_of_drone(s, did):
    base = DRONES[did]["cost"]
    count = s["drones"].get(did, {}).get("count", 0)
    return base * 1.18 ** count


def cost_of_employee(s, eid):
    return EMPLOYEES[eid]["cost"] * EMPLOYEE_COST_MULT ** s["employees"].get(eid, 0)


def cost_of_building(s, pid, bid, target_level=None):
    lvl = building_level(s, pid, bid)
    if target_level is None:
        target_level = lvl + 1
    base = BUILDINGS[bid]["cost"] * 1.6 ** (target_level - 1)
    base *= galaxy(PLANETS[pid][1])["cost_mult"]
    return base * mults(s)["build_cost"]


def cost_of_upgrade(s, uid):
    u = s["upgrades"].get(uid, 0)
    from .data_fleet import UPGRADES
    return UPGRADES[uid]["cost"] * UPGRADES[uid]["cost_mult"] ** u


def cost_of_essence_upgrade(s, uid):
    return ESSENCE_COST(s["essence_upgrades"].get(uid, 0))


def unlocked_planets(s):
    return [pid for pid in PLANET_IDS if s["planets"][pid]["unlocked"]]


def unlocked_galaxies(s):
    out = []
    for g in GALAXIES:
        if g["unlock_credits"] == 0:
            out.append(g["id"])
        elif s["lifetime_credits"] >= g["unlock_credits"] and s["player_level"] >= g["unlock_level"]:
            out.append(g["id"])
    return out


def discovered_minerals(s):
    return list(dict.fromkeys(s["discovered"]))


def total_building_levels(s):
    return sum(s["buildings"].values())


def migrate(s):
    v = s.get("version", 1)
    if v < 2:
        s.setdefault("essence_upgrades", {})
        s.setdefault("lifetime_essence", 0.0)
        s.setdefault("events_survived", 0)
        s.setdefault("pirates_defeated", 0)
        s.setdefault("overdrive_until", 0.0)
        s.setdefault("session_mined", 0.0)
        s["version"] = 2
    if v < 3:
        s.setdefault("log", [])
        s.setdefault("daily", [])
        s.setdefault("daily_date", "")
        s["version"] = SAVE_VERSION
    return s


def validate(s):
    if not isinstance(s, dict) or "planets" not in s or "credits" not in s:
        return False
    for pid in PLANET_IDS:
        if pid not in s["planets"]:
            return False
    return True
