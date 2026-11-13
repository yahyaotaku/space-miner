"""Active mining: laser hits, asteroid destruction, rewards. Pure logic."""
import random

from .data_world import roll_asteroid, MINERALS, mineral_rarity, RARITY_ORDER
from .state import laser_power, crit_chance, mults, xp_needed_player


def mine_hit(s, node, rng):
    """Fire one laser hit at a node. Mutates node. Returns result dict."""
    if node["hp"] <= 0:
        return {"hit": False, "reason": "regenerating"}
    dmg = laser_power(s) * random.uniform(0.9, 1.1)
    crit = rng.random() < crit_chance(s)
    if crit:
        dmg *= 3.0
    node["hp"] -= dmg
    result = {"hit": True, "damage": dmg, "crit": crit, "destroyed": False,
              "yield": {}, "research": 0.0, "xp": dmg * 0.1}
    if node["hp"] <= 0:
        result["destroyed"] = True
        result["yield"] = _collect(s, node, rng)
        result["research"] = 5.0 if node["ancient"] else 0.0
        result["xp"] += 5.0
    return result


def _collect(s, node, rng):
    mult = mults(s)
    yield_mult = 1.0
    if node["ancient"] and mult["rare_luck"] > 1.0:
        yield_mult *= 1.0 + (mult["rare_luck"] - 1.0) * 0.5
    out = {}
    for mid, amount in node["content"].items():
        amt = amount * yield_mult
        out[mid] = out.get(mid, 0.0) + amt
        s["resources"][mid] = s["resources"].get(mid, 0.0) + amt
        if mid not in s["discovered"]:
            s["discovered"].append(mid)
    s["ore_mined"] += sum(out.values())
    s["session_mined"] += sum(out.values())
    s["kills"] += 1
    if node["ancient"]:
        s["ancient_kills"] += 1
    return out


def respawn_node(s, pid, index, rng, now):
    """Regenerate a depleted node into a fresh asteroid."""
    luck = mults(s)["rare_luck"]
    p = s["planets"][pid]
    p["nodes"][index] = roll_asteroid(rng, pid, richness=1.0 + 0.1 * (p["dev_level"] - 1), luck=luck)
    return p["nodes"][index]


def respawn_delay(s, node):
    from .state import mults as _m
    return node["respawn"] * _m(s)["respawn"]


def grant_player_xp(s, xp):
    s["player_xp"] += xp
    leveled = False
    while s["player_xp"] >= xp_needed_player(s["player_level"]):
        s["player_xp"] -= xp_needed_player(s["player_level"])
        s["player_level"] += 1
        leveled = True
    return leveled


def asteroid_label(node):
    if node["hp"] <= 0:
        return "regenerating"
    return node["size"]


def content_label(node):
    parts = []
    for mid, amt in sorted(node["content"].items(),
                           key=lambda kv: -RARITY_ORDER[mineral_rarity(kv[0])]):
        tag = MINERALS[mid][0]
        if node["ancient"]:
            tag = "* " + tag
        parts.append(f"{tag} x{amt:.0f}")
    return ", ".join(parts)
