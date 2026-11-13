"""Galactic Rebirth (prestige)."""
from .data_world import PLANET_IDS
from .state import (new_state, mults, ESSENCE_UPGRADES, ESSENCE_COST,
                    unlocked_planets, unlocked_galaxies)
from .util import fmt

REBIRTH_THRESHOLD = 1e9


def essence_gain(s):
    if s["lifetime_credits"] < REBIRTH_THRESHOLD:
        return 0
    base = 10 * (s["lifetime_credits"] / REBIRTH_THRESHOLD) ** 0.5
    return int(base * mults(s)["essence_gain"])


def can_rebirth(s):
    return essence_gain(s) > 0


def rebirth(s, now):
    """Reset temporary progress, keep meta progression. Returns new state."""
    gain = essence_gain(s)
    keep_research_pct = 0.25 * s["essence_upgrades"].get("keep_research", 0)
    kept_research = s["research_data"] * keep_research_pct
    start_credits = 0
    sc_lvl = s["essence_upgrades"].get("start_credits", 0)
    if sc_lvl > 0:
        start_credits = 10_000 * 10 ** (sc_lvl - 1)
    veteran_level = 5 * s["essence_upgrades"].get("veteran_fleet", 0)

    achievements = s["achievements"]
    stats_keep = {
        "kills": s["kills"], "ancient_kills": s["ancient_kills"],
        "ore_mined": s["ore_mined"], "ore_sold": s["ore_sold"],
        "missions_done": s["missions_done"], "events_survived": s["events_survived"],
        "pirates_defeated": s["pirates_defeated"],
    }
    essence_total = s["essence"] + gain
    lifetime_essence = s["lifetime_essence"] + gain
    prestige_count = s["prestige_count"] + 1
    essence_upgrades = s["essence_upgrades"]
    settings = s["settings"]

    ns = new_state(now)
    ns["achievements"] = achievements
    ns["essence"] = essence_total
    ns["lifetime_essence"] = lifetime_essence
    ns["prestige_count"] = prestige_count
    ns["essence_upgrades"] = essence_upgrades
    ns["settings"] = settings
    ns["research_data"] = kept_research
    ns["credits"] = max(ns["credits"], start_credits)
    ns["kills"] = stats_keep["kills"]
    ns["ancient_kills"] = stats_keep["ancient_kills"]
    ns["ore_mined"] = stats_keep["ore_mined"]
    ns["ore_sold"] = stats_keep["ore_sold"]
    ns["missions_done"] = stats_keep["missions_done"]
    ns["events_survived"] = stats_keep["events_survived"]
    ns["pirates_defeated"] = stats_keep["pirates_defeated"]
    ns["lifetime_credits"] = 0.0
    ns["mission_index"] = 0
    if veteran_level > 1:
        ns["veteran_level"] = veteran_level
    from .state import _roll_dailies
    import datetime
    _roll_dailies(ns, datetime.date.today().isoformat())
    return ns, gain


def rebirth_preview(s):
    gain = essence_gain(s)
    lines = []
    lines.append("GALACTIC REBIRTH")
    lines.append("")
    if not can_rebirth(s):
        lines.append(f"  Requires {fmt(REBIRTH_THRESHOLD)} lifetime credits this run.")
        lines.append(f"  Current: {fmt(s['lifetime_credits'])}")
        return lines, gain
    lines.append(f"  You will gain: {gain} Stellar Essence (+{gain * 2}% permanent production).")
    lines.append("")
    lines.append("  RESET:")
    lines.append("    - Credits, energy, research data (partial keep via Archived Data)")
    lines.append("    - All resources, ships, drones, buildings, employees")
    lines.append("    - Planet unlocks and development")
    lines.append("    - Research tree progress")
    lines.append("    - Story mission progress")
    lines.append("")
    lines.append("  KEPT:")
    lines.append("    - Stellar Essence and Essence upgrades")
    lines.append("    - All achievements")
    lines.append("    - Lifetime statistics and settings")
    return lines, gain
