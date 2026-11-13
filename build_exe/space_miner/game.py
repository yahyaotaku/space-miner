"""Game orchestrator: ticks, player actions, missions, achievements."""
import datetime
import random
from collections import deque

from . import production, mining as mining_sys, economy, events as events_sys
from . import save as save_sys, prestige as prestige_sys, offline as offline_sys
from .data_world import PLANETS, PLANET_IDS, planet, galaxy, GALAXIES, roll_asteroid
from .data_fleet import (SHIPS, DRONES, BUILDINGS, UPGRADES, EMPLOYEES,
                         SHIP_ORDER, DRONE_ORDER, BUILDING_ORDER, UPGRADE_ORDER,
                         EMPLOYEE_ORDER)
from .data_tech import MISSIONS, ACHIEVEMENTS, RESEARCH, research_info, EVENT_INTERVAL
from .state import (new_state, mults, laser_power, crit_chance, drone_count, drone_cap,
                    ship_count, fleet_cap, storage_cap, cost_of_ship, cost_of_drone,
                    cost_of_employee, cost_of_building, cost_of_upgrade,
                    cost_of_essence_upgrade, unlocked_planets, unlocked_galaxies,
                    xp_needed_player, xp_needed_unit, company_level, defense_power,
                    unit_level_mult, has_research, ESSENCE_UPGRADES, ESSENCE_UPGRADE_ORDER,
                    planet_production_mult, planet_hazard, offline_capacity_hours,
                    offline_efficiency, total_building_levels, validate, migrate)
from .util import fmt, fmt_time, beep

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


class Game:
    def __init__(self, state=None, now=None, rng=None):
        self.now = now if now is not None else _now()
        self.rng = rng or random.Random()
        self.state = state if state is not None else new_state(self.now)
        if not validate(self.state):
            self.state = new_state(self.now)
        self.state = migrate(self.state)
        economy.init_market(self.state, self.now)
        self.feed = deque(self.state.get("log", []), maxlen=8)
        self.autosave_at = self.now + 30.0
        self._auto_mine_acc = 0.0
        self.quit_requested = False

    # ------------------------------------------------------------- logging
    def log(self, msg):
        self.feed.append(msg)
        self.state["log"] = list(self.feed)

    # ------------------------------------------------------------- ticking
    def tick(self, now=None):
        now = now if now is not None else _now()
        s = self.state
        dt = now - s["last_tick"]
        if dt <= 0:
            s["last_tick"] = now
            return
        dt = min(dt, 120.0)
        s["last_tick"] = now
        s["play_time"] += dt

        prod = production.apply_production(s, dt)
        if prod["caps_hit"]:
            self._warn_storage_once(prod["full"])
        economy.drift_market(s, dt, self.rng)

        self._respawn_nodes(now)
        self._auto_mine(now)
        self._maybe_event(now)
        sold, sold_map = economy.autosell_pass(s)
        if sold > 0:
            s["credits_today"] = s.get("credits_today", 0.0) + sold
            s["today_sold"] = s.get("today_sold", 0.0) + sum(sold_map.values())
        self._check_missions()
        self._check_achievements()
        if now >= self.autosave_at:
            save_sys.save(s)
            self.autosave_at = now + 30.0

    _storage_warned = False

    def _warn_storage_once(self, full):
        if not self._storage_warned and full:
            self.log(f"Storage full for: {', '.join(full[:4])}. Build Warehouses or sell.")
            self._storage_warned = True

    def _respawn_nodes(self, now):
        s = self.state
        for pid in unlocked_planets(s):
            p = s["planets"][pid]
            for i, node in enumerate(p["nodes"]):
                if node["hp"] <= 0 and now >= node["depleted_until"]:
                    mining_sys.respawn_node(s, pid, i, self.rng, now)

    def _auto_mine(self, now):
        if "auto_miner" not in self.state["upgrades"]:
            return
        self._auto_mine_acc += min(1.0, now - getattr(self, "_last_auto", now))
        self._last_auto = now
        while self._auto_mine_acc >= 1.0:
            self._auto_mine_acc -= 1.0
            self.do_mine(silent=True)

    def _maybe_event(self, now):
        s = self.state
        if now < s.get("next_event_at", now + 120):
            return
        s["next_event_at"] = now + self.rng.uniform(*EVENT_INTERVAL)
        if self.rng.random() < 0.8:
            msg = events_sys.trigger(s, now, self.rng)
            self.log(msg)
            if s["settings"].get("sound"):
                beep()

    # ------------------------------------------------------------- mining
    def do_mine(self, silent=False):
        s = self.state
        pid = s["selected_planet"]
        node = s["planets"][pid]["nodes"][s["selected_node"]]
        result = mining_sys.mine_hit(s, node, self.rng)
        if not result["hit"]:
            if not silent:
                self.log("Asteroid is regenerating. Wait or switch targets.")
            return result
        mining_sys.grant_player_xp(s, result["xp"])
        if result["destroyed"]:
            s["today_kills"] = s.get("today_kills", 0) + 1
            s["today_ore"] = s.get("today_ore", 0.0) + sum(result["yield"].values())
            from .state import mults as _m
            node["depleted_until"] = self.now + node["respawn"] * _m(s)["respawn"]
            node["hp"] = 0.0
            p = s["planets"][pid]
            p["xp"] += 10
            gain = result["yield"]
            label = ", ".join(f"+{fmt(v)} {k.replace('_', ' ').title()}" for k, v in gain.items())
            crit = "CRIT! " if result["crit"] else ""
            self.log(f"{crit}Destroyed {node['size']} asteroid: {label}")
            if result["research"]:
                s["research_data"] += result["research"]
                self.log(f"Ancient data recovered: +{fmt(result['research'])} research")
            if s["settings"].get("sound"):
                beep()
        self._check_missions()
        self._check_achievements()
        return result

    def select_node(self, index):
        s = self.state
        if 0 <= index < len(s["planets"][s["selected_planet"]]["nodes"]):
            s["selected_node"] = index
            return True
        return False

    def cycle_planet(self, direction=1):
        pids = unlocked_planets(self.state)
        if not pids:
            return
        cur = pids.index(self.state["selected_planet"]) if self.state["selected_planet"] in pids else 0
        self.state["selected_planet"] = pids[(cur + direction) % len(pids)]
        self.state["selected_node"] = 0

    def overdrive(self):
        s = self.state
        cost = 25.0 * (0.5 if has_research(s, "exotic_energy") else 1.0)
        if s["energy"] < cost:
            self.log(f"Overdrive needs {cost:.0f} energy.")
            return False
        if s.get("overdrive_until", 0) > self.now:
            self.log("Overdrive already active.")
            return False
        s["energy"] -= cost
        s["overdrive_until"] = self.now + 30.0
        self.log("OVERDRIVE ENGAGED: double laser & production for 30s!")
        return True

    # ------------------------------------------------------------- economy
    def sell_resource(self, mid, amount=None):
        amount = amount if amount is not None else self.state["resources"].get(mid, 0.0)
        gained = economy.sell(self.state, mid, amount)
        if gained > 0:
            self.state["credits_today"] = self.state.get("credits_today", 0.0) + gained
            self.state["today_sold"] = self.state.get("today_sold", 0.0) + amount
            mining_sys.grant_player_xp(self.state, gained * 0.02)
            self._check_missions()
        return gained

    def sell_everything(self):
        before = sum(self.state["resources"].values())
        gained = economy.sell_all(self.state)
        if gained > 0:
            sold_amount = before - sum(self.state["resources"].values())
            self.state["credits_today"] = self.state.get("credits_today", 0.0) + gained
            self.state["today_sold"] = self.state.get("today_sold", 0.0) + sold_amount
            mining_sys.grant_player_xp(self.state, gained * 0.02)
            self.log(f"Sold entire hold for {fmt(gained)} credits.")
            self._check_missions()
        return gained

    # ------------------------------------------------------------- purchases
    def buy_upgrade(self, uid):
        s = self.state
        if uid not in UPGRADES:
            return False, "Unknown upgrade."
        lvl = s["upgrades"].get(uid, 0)
        if lvl >= UPGRADES[uid]["max"]:
            return False, "Already at maximum level."
        cost = cost_of_upgrade(s, uid)
        if s["credits"] < cost:
            return False, f"Not enough credits (need {fmt(cost)})."
        s["credits"] -= cost
        s["upgrades"][uid] = lvl + 1
        s["upgrades_bought"] = s.get("upgrades_bought", 0) + 1
        self.log(f"Upgraded {UPGRADES[uid]['name']} to level {lvl + 1}.")
        self._check_missions()
        self._check_achievements()
        return True, "OK"

    def buy_ship(self, sid):
        s = self.state
        if sid not in SHIPS:
            return False, "Unknown ship."
        if s["player_level"] < SHIPS[sid]["unlock_level"]:
            return False, f"Requires player level {SHIPS[sid]['unlock_level']}."
        if ship_count(s) >= fleet_cap(s):
            return False, "Fleet at capacity. Buy Fleet Licenses or a Shipyard."
        cost = cost_of_ship(s, sid)
        if s["credits"] < cost:
            return False, f"Not enough credits (need {fmt(cost)})."
        s["credits"] -= cost
        entry = s["ships"].setdefault(sid, {"count": 0, "level": 1, "xp": 0.0, "planet": None})
        entry["count"] += 1
        if entry["level"] == 1 and s.get("veteran_level"):
            entry["level"] = s["veteran_level"]
        if entry["planet"] is None:
            entry["planet"] = s["selected_planet"]
        self.log(f"Purchased {SHIPS[sid]['name']} ({entry['count']} owned).")
        self._check_missions()
        self._check_achievements()
        return True, "OK"

    def assign_ship(self, sid, pid):
        s = self.state
        if sid not in s["ships"] or pid not in PLANETS:
            return False
        if not s["planets"][pid]["unlocked"]:
            return False
        s["ships"][sid]["planet"] = pid
        return True

    def buy_drone(self, did):
        s = self.state
        if did not in DRONES:
            return False, "Unknown drone."
        if drone_count(s) >= drone_cap(s):
            return False, "Drone bays full. Buy Drone Bays or research Swarm Logistics."
        cost = cost_of_drone(s, did)
        if s["credits"] < cost:
            return False, f"Not enough credits (need {fmt(cost)})."
        s["credits"] -= cost
        entry = s["drones"].setdefault(did, {"count": 0, "level": 1, "xp": 0.0, "planet": None})
        entry["count"] += 1
        if entry["level"] == 1 and s.get("veteran_level"):
            entry["level"] = s["veteran_level"]
        if entry["planet"] is None:
            entry["planet"] = s["selected_planet"]
        self.log(f"Built {DRONES[did]['name']} ({entry['count']} owned).")
        self._check_missions()
        self._check_achievements()
        return True, "OK"

    def assign_drones(self, did, pid):
        s = self.state
        if did not in s["drones"] or pid not in PLANETS:
            return False
        if not s["planets"][pid]["unlocked"]:
            return False
        s["drones"][did]["planet"] = pid
        return True

    def build(self, pid, bid):
        s = self.state
        if bid not in BUILDINGS or not s["planets"][pid]["unlocked"]:
            return False, "Unavailable."
        cost = cost_of_building(s, pid, bid)
        if s["credits"] < cost:
            return False, f"Not enough credits (need {fmt(cost)})."
        s["credits"] -= cost
        key = f"{pid}:{bid}"
        s["buildings"][key] = s["buildings"].get(key, 0) + 1
        self.log(f"Built {BUILDINGS[bid]['name']} lvl {s['buildings'][key]} on {planet(pid)['name']}.")
        self._check_missions()
        self._check_achievements()
        return True, "OK"

    def research(self, rid):
        s = self.state
        if rid not in RESEARCH:
            return False, "Unknown technology."
        info = research_info(rid)
        if rid in s["research"]:
            return False, "Already researched."
        for pre in info["prereqs"]:
            if pre not in s["research"]:
                return False, f"Requires {RESEARCH[pre][2]}."
        if s["research_data"] < info["cost"]:
            return False, f"Not enough research data (need {fmt(info['cost'])})."
        s["research_data"] -= info["cost"]
        s["research"].append(rid)
        self.log(f"RESEARCH COMPLETE: {info['name']} - {info['desc']}")
        self._check_missions()
        self._check_achievements()
        return True, "OK"

    def hire(self, eid):
        s = self.state
        if eid not in EMPLOYEES:
            return False, "Unknown role."
        cost = cost_of_employee(s, eid)
        if s["credits"] < cost:
            return False, f"Not enough credits (need {fmt(cost)})."
        s["credits"] -= cost
        s["employees"][eid] = s["employees"].get(eid, 0) + 1
        self.log(f"Hired a {EMPLOYEES[eid]['name']}.")
        self._check_achievements()
        return True, "OK"

    def unlock_planet(self, pid):
        s = self.state
        info = planet(pid)
        if s["planets"][pid]["unlocked"]:
            return False, "Already unlocked."
        if s["lifetime_credits"] < info["unlock_credits"] or s["player_level"] < info["unlock_level"]:
            return False, "Requirements not met."
        s["planets"][pid]["unlocked"] = True
        if s["player_level"] >= info["unlock_level"] and s["lifetime_credits"] >= info["unlock_credits"]:
            pass
        self.log(f"NEW WORLD CLAIMED: {info['name']}!")
        self._check_missions()
        self._check_achievements()
        return True, "OK"

    def buy_essence_upgrade(self, uid):
        s = self.state
        if uid not in ESSENCE_UPGRADES:
            return False, "Unknown upgrade."
        lvl = s["essence_upgrades"].get(uid, 0)
        if lvl >= ESSENCE_UPGRADES[uid]["max"]:
            return False, "Maximum level reached."
        cost = cost_of_essence_upgrade(s, uid)
        if s["essence"] < cost:
            return False, f"Need {cost} essence."
        s["essence"] -= cost
        s["essence_upgrades"][uid] = lvl + 1
        self.log(f"Essence upgrade: {ESSENCE_UPGRADES[uid]['name']} level {lvl + 1}.")
        return True, "OK"

    # ------------------------------------------------------------- missions
    def _objective_value(self, kind):
        s = self.state
        if kind == "mine_ore":
            return s["ore_mined"]
        if kind == "sell_count":
            return s["ore_sold"]
        if kind == "buy_upgrade":
            return s.get("upgrades_bought", 0)
        if kind == "own_drones":
            return drone_count(s)
        if kind == "own_ships":
            return ship_count(s)
        if kind == "own_ship_type":
            return len([1 for v in s["ships"].values() if v["count"] > 0])
        if kind == "player_level":
            return s["player_level"]
        if kind == "unlock_planet":
            return len(unlocked_planets(s)) - 1
        if kind == "lifetime_credits":
            return s["lifetime_credits"]
        if kind == "building_level":
            return total_building_levels(s)
        if kind == "research_count":
            return len(s["research"])
        if kind == "ancient_kills":
            return s["ancient_kills"]
        if kind == "company_level":
            return company_level(s["lifetime_credits"])
        if kind == "prestige":
            return s["prestige_count"]
        if kind == "destroy":
            return s["kills"]
        return 0

    def _check_missions(self):
        s = self.state
        idx = s["mission_index"]
        if idx < len(MISSIONS):
            name, kind, target, rewards = MISSIONS[idx]
            if self._objective_value(kind) >= target:
                s["mission_index"] = idx + 1
                s["missions_done"] += 1
                if "credits" in rewards:
                    s["credits"] += rewards["credits"]
                    s["lifetime_credits"] += rewards["credits"]
                if "research" in rewards:
                    s["research_data"] += rewards["research"]
                if "energy" in rewards:
                    s["energy"] += rewards["energy"]
                self.log(f"MISSION COMPLETE: {name}! Rewards received.")
                if s["settings"].get("sound"):
                    beep()
        self._roll_daily_if_needed()
        for d in s.get("daily", []):
            if not d["done"] and self._daily_value(d["kind"]) >= d["target"]:
                d["done"] = True
                s["research_data"] += 15
                s["credits"] += 1000
                s["lifetime_credits"] += 1000
                self.log("DAILY MISSION COMPLETE: +15 research, +1K credits")

    def _daily_value(self, kind):
        s = self.state
        if kind == "mine_ore":
            return s.get("today_ore", 0.0) + s.get("session_mined", 0.0) * 0
        if kind == "sell_count":
            return s.get("today_sold", 0.0)
        if kind == "destroy":
            return s.get("today_kills", 0)
        if kind == "lifetime_credits":
            return s.get("credits_today", 0.0)
        return 0.0

    def _roll_daily_if_needed(self):
        s = self.state
        today = datetime.date.today().isoformat()
        if s.get("daily_date") != today:
            from .state import _roll_dailies
            _roll_dailies(s, today)
            s["today_ore"] = 0.0
            s["today_sold"] = 0.0
            s["today_kills"] = 0
            s["credits_today"] = 0.0

    # ------------------------------------------------------------- achievements
    def _achievement_value(self, key):
        s = self.state
        return {
            "ore_mined": s["ore_mined"], "lifetime_credits": s["lifetime_credits"],
            "drones": drone_count(s), "ships": ship_count(s),
            "ship_types": len([1 for v in s["ships"].values() if v["count"] > 0]),
            "planets": len(unlocked_planets(s)), "galaxies": len(unlocked_galaxies(s)),
            "research": len(s["research"]), "kills": s["kills"],
            "ancient_kills": s["ancient_kills"], "player_level": s["player_level"],
            "company_level": company_level(s["lifetime_credits"]),
            "employees": sum(s["employees"].values()), "prestige": s["prestige_count"],
            "essence": s["essence"], "building_levels": total_building_levels(s),
        }.get(key, 0)

    def _check_achievements(self):
        s = self.state
        for aid, name, desc, reward, key, value in ACHIEVEMENTS:
            if aid in s["achievements"]:
                continue
            if self._achievement_value(key) >= value:
                s["achievements"].append(aid)
                if reward > 0:
                    s["credits"] += reward
                    s["lifetime_credits"] += reward
                    self.log(f"ACHIEVEMENT: {name} (+{fmt(reward)} credits)")
                else:
                    self.log(f"ACHIEVEMENT: {name}")
                if s["settings"].get("sound"):
                    beep()

    # ------------------------------------------------------------- offline & save
    def apply_offline(self, now):
        summary = offline_sys.offline_progress(self.state, now)
        if summary:
            self.state["last_tick"] = now
            self.autosave_at = now + 30.0
            self._check_missions()
            self._check_achievements()
        return summary

    def save(self):
        return save_sys.save(self.state)

    def do_rebirth(self, now=None):
        now = now if now is not None else _now()
        ns, gain = prestige_sys.rebirth(self.state, now)
        self.state = ns
        self.now = now
        self.feed.clear()
        self.log(f"GALACTIC REBIRTH! +{gain} Stellar Essence. The universe begins anew.")
        return gain


def _now():
    import time
    return time.time()
