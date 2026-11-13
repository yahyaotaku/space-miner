"""Random events: timed multipliers, instant rewards, pirate encounters."""
import random

from .data_tech import EVENTS
from .economy import sell_all
from .state import defense_power, mults
from .util import fmt


def pick_event(rng):
    total = sum(e[2] for e in EVENTS)
    roll = rng.random() * total
    acc = 0.0
    for e in EVENTS:
        acc += e[2]
        if roll <= acc:
            return e
    return EVENTS[0]


def trigger(s, now, rng):
    eid, name, _w, kind, value, duration, desc = pick_event(rng)
    event = {"id": eid, "name": name, "kind": kind, "value": value,
             "until": now + duration if duration else now, "desc": desc}
    s["events_survived"] += 1
    msg = f"EVENT: {name} - {desc}"
    if kind == "instant_research":
        amount = 30 + 15 * s["player_level"]
        s["research_data"] += amount
        msg += f" (+{fmt(amount)} research)"
        s["event"] = None
    elif kind == "instant_credits":
        amount = s["lifetime_credits"] * 0.05 + 1000
        s["credits"] += amount
        s["lifetime_credits"] += amount
        msg += f" (+{fmt(amount)} credits)"
        s["event"] = None
    elif kind == "pirates":
        strength = 15 * (1.25 ** min(12, s["events_survived"] // 25))
        defense = defense_power(s)
        if defense >= strength:
            loot = strength * 30
            s["credits"] += loot
            s["lifetime_credits"] += loot
            s["pirates_defeated"] += 1
            msg += f" Your fleet drove them off! (+{fmt(loot)} credits bounty)"
        else:
            lost = 0.0
            for mid in list(s["resources"].keys()):
                take = s["resources"][mid] * 0.15
                lost += take
                s["resources"][mid] -= take
            msg += (f" Pirates raided your holds! Lost {fmt(lost)} ore."
                    f" (defense {defense:.0f} vs {strength:.0f} - build Defender ships)")
        s["event"] = None
    else:
        s["event"] = event
    return msg


def active_event(s, now):
    ev = s.get("event")
    if ev and now < ev["until"]:
        return ev
    if ev:
        s["event"] = None
    return None
