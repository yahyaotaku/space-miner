"""Offline progression: capped, efficiency-scaled catch-up with a summary."""
from .data_world import PLANETS
from .production import apply_production, total_rates, energy_rate, research_rate
from .economy import autosell_pass
from .state import offline_capacity_hours, offline_efficiency
from .util import fmt, fmt_time


def offline_progress(s, now):
    """Compute offline gains since last_save. Returns (state_mutated, summary) or None."""
    elapsed = now - s.get("last_save", now)
    if elapsed < 60:
        return None
    cap_seconds = offline_capacity_hours(s) * 3600
    capped = elapsed > cap_seconds
    effective = min(elapsed, cap_seconds)
    eff = offline_efficiency(s)

    # Temporarily scale rates by applying production in one call with adjusted dt.
    dt = effective * eff
    before = dict(s["resources"])
    result = apply_production(s, dt)
    research_before = s["research_data"]
    missions_ok = _progress_dailies_offline(s, effective)

    sold_total, sold_map = autosell_pass(s)
    summary = {
        "elapsed": elapsed,
        "effective": effective,
        "capped": capped,
        "efficiency": eff,
        "produced": result["produced"],
        "full": result["full"],
        "research_gained": s["research_data"] - research_before,
        "research_rate": research_rate(s),
        "energy_rate": energy_rate(s),
        "rates": total_rates(s),
        "sold_total": sold_total,
        "sold_map": sold_map,
        "dailies": missions_ok,
    }
    return summary


def _progress_dailies_offline(s, seconds):
    from .production import total_rates
    rates = total_rates(s)
    ore = sum(rates.values()) * seconds * 0.5
    for d in s.get("daily", []):
        if d["done"]:
            continue
        if d["kind"] == "mine_ore":
            d["progress"] += ore
        elif d["kind"] == "lifetime_credits":
            d["progress"] += sum(rates.values()) * seconds * 0.5 * 5
        if d["progress"] >= d["target"]:
            d["done"] = True
    return True


def render_summary(summary):
    lines = []
    lines.append("WELCOME BACK, COMMANDER")
    lines.append("")
    away = fmt_time(summary["elapsed"])
    lines.append(f"  You were away for {away}.")
    if summary["capped"]:
        lines.append(f"  Offline capacity limited gains to {fmt_time(summary['effective'])}"
                     f" (upgrade Deep Sleep Uplink for more).")
    lines.append(f"  Offline efficiency: {summary['efficiency'] * 100:.0f}%")
    lines.append("")
    lines.append("  Resources mined:")
    if summary["produced"]:
        for mid, amt in sorted(summary["produced"].items(), key=lambda kv: -kv[1]):
            lines.append(f"    +{fmt(amt)} {mid.replace('_', ' ').title()}")
    else:
        lines.append("    (no idle production assigned)")
    if summary["sold_total"] > 0:
        lines.append("")
        lines.append(f"  Auto-sold surplus for {fmt(summary['sold_total'])} credits.")
    lines.append("")
    lines.append(f"  Research data gained: +{fmt(summary['research_gained'])}")
    if summary["full"]:
        lines.append("")
        lines.append("  WARNING: storage was full for some resources. Build Warehouses.")
    return lines
