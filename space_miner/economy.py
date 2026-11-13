"""Market: dynamic prices, selling, auto-sell."""
import random

from .data_world import MINERALS
from .state import mults, storage_cap

PRICE_FLOOR, PRICE_CEIL = 0.7, 1.4


def init_market(s, now):
    s.setdefault("market", {})
    for mid in MINERALS:
        s["market"].setdefault(mid, {"mult": 1.0})


def drift_market(s, dt, rng):
    """Random walk with mean reversion toward 1.0."""
    for mid, m in s["market"].items():
        pull = (1.0 - m["mult"]) * 0.02 * dt
        noise = rng.gauss(0, 0.05) * (dt ** 0.5) * 0.2
        m["mult"] = min(PRICE_CEIL, max(PRICE_FLOOR, m["mult"] + pull + noise))


def price(s, mid, now=None):
    base = MINERALS[mid][2]
    m = mults(s)
    pm = s.get("market", {}).get(mid, {}).get("mult", 1.0)
    return base * pm * m["sell"]


def sell(s, mid, amount):
    amount = min(amount, s["resources"].get(mid, 0.0))
    if amount <= 0:
        return 0.0
    gained = amount * price(s, mid)
    s["resources"][mid] -= amount
    s["credits"] += gained
    s["lifetime_credits"] += gained
    s["ore_sold"] += amount
    return gained


def sell_all(s, exclude=None):
    exclude = exclude or set()
    total = 0.0
    for mid in list(s["resources"].keys()):
        if mid in exclude or s["resources"].get(mid, 0) <= 0:
            continue
        total += sell(s, mid, s["resources"][mid])
    return total


def autosell_pass(s, reserve=None):
    """Sell resources above the autosell threshold. Returns (credits, sold)."""
    if not s["settings"]["autosell"]:
        return 0.0, {}
    reserve = reserve or set()
    threshold = s["settings"]["autosell_threshold"]
    cap = storage_cap(s)
    sold = {}
    total = 0.0
    for mid, amount in list(s["resources"].items()):
        if mid in reserve or amount <= 0:
            continue
        if amount > cap * threshold:
            excess = amount - cap * threshold
            gained = sell(s, mid, excess)
            if gained > 0:
                sold[mid] = sold.get(mid, 0.0) + excess
                total += gained
    return total, sold
