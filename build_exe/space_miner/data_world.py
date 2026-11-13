"""Static game content: minerals, planets, galaxies, asteroids."""
from .util import clamp

RARITY_COLORS = {
    "common": "37", "uncommon": "32", "rare": "36",
    "epic": "35", "legendary": "93",
}
RARITY_ORDER = {"common": 0, "uncommon": 1, "rare": 2, "epic": 3, "legendary": 4}

MINERALS = {
    "iron":            ("Iron",            "common",    6,    "The backbone of early space industry."),
    "copper":          ("Copper",          "common",    9,    "Conductive metal used in every circuit."),
    "silicon":         ("Silicon",         "common",    12,   "Refined into processors and solar glass."),
    "sulfur":          ("Sulfur",          "common",    15,   "Volatile element mined near volcanoes."),
    "nickel":          ("Nickel",          "uncommon",  26,   "Hardens alloys for hull plating."),
    "titanium":        ("Titanium",        "uncommon",  30,   "Lightweight frame metal for ships."),
    "frozen_gas":      ("Frozen Gas",      "uncommon",  28,   "Cryo-stabilized fuel compound."),
    "cobalt":          ("Cobalt",          "uncommon",  35,   "Energy-dense battery material."),
    "ice_crystal":     ("Ice Crystal",     "uncommon",  40,   "Crystalline water with odd resonance."),
    "gold":            ("Gold",            "rare",      75,   "Precious conductor of star forges."),
    "platinum":        ("Platinum",        "rare",      90,   "Catalyst for advanced refining."),
    "uranium":         ("Uranium",         "rare",      120,  "Fissile fuel for reactors."),
    "iridium":         ("Iridium",         "rare",      150,  "Ultra-dense rare metal."),
    "solar_crystal":   ("Solar Crystal",   "rare",      200,  "Stores raw sunlight as energy."),
    "quantum_crystal": ("Quantum Crystal", "epic",      450,  "Phases in and out of reality."),
    "dark_matter":     ("Dark Matter",     "epic",      600,  "Invisible mass with immense pull."),
    "ancient_fragment":("Ancient Fragment","epic",      800,  "Shard of a forgotten civilization."),
    "ancient_core":    ("Ancient Core",    "legendary", 2500, "Still humming after eons."),
    "star_essence":    ("Star Essence",    "legendary", 4000, "Condensed light of a dying star."),
}


def mineral_name(mid):
    return MINERALS[mid][0]


def mineral_price(mid):
    return MINERALS[mid][2]


def mineral_rarity(mid):
    return MINERALS[mid][1]


GALAXIES = [
    {"id": "frontier", "name": "Frontier",        "unlock_credits": 0,    "unlock_level": 1,  "richness": 1.0,  "difficulty": 1.0, "cost_mult": 1.0},
    {"id": "orion",    "name": "Orion Reach",     "unlock_credits": 2e8,  "unlock_level": 18, "richness": 2.5,  "difficulty": 1.6, "cost_mult": 3.0},
    {"id": "nebula",   "name": "Nebula Expanse",  "unlock_credits": 5e10, "unlock_level": 26, "richness": 6.0,  "difficulty": 2.3, "cost_mult": 8.0},
    {"id": "void",     "name": "Ancient Void",    "unlock_credits": 4e12, "unlock_level": 34, "richness": 15.0, "difficulty": 3.2, "cost_mult": 20.0},
    {"id": "core",     "name": "Celestial Core",  "unlock_credits": 3e14, "unlock_level": 42, "richness": 40.0, "difficulty": 4.2, "cost_mult": 50.0},
]


def galaxy(gid):
    for g in GALAXIES:
        if g["id"] == gid:
            return g
    return GALAXIES[0]


# planets: id -> (name, galaxy, {mineral: weight}, unlock_credits, unlock_level, hazard)
HAZARD_NONE = None
PLANETS = {
    "asteroid_01": ("Asteroid-01", "frontier", {"iron": 5, "copper": 3, "silicon": 2}, 0, 1, None),
    "volcanis":    ("Volcanis",    "frontier", {"titanium": 4, "cobalt": 3, "sulfur": 3}, 25_000, 5, "Lava storms: -15% mining efficiency"),
    "glaciera":    ("Glaciera",    "frontier", {"ice_crystal": 4, "platinum": 3, "frozen_gas": 3}, 500_000, 10, "Deep freeze: -20% mining efficiency"),
    "solara":      ("Solara",      "frontier", {"gold": 4, "iridium": 3, "solar_crystal": 3}, 10_000_000, 15, "Solar flares: -25% mining efficiency"),
    "mystral":     ("Mystral",     "frontier", {"quantum_crystal": 3, "dark_matter": 3, "ancient_fragment": 2}, 250_000_000, 20, "Quantum fog: -30% mining efficiency"),
    "ferron":      ("Ferron",      "orion",    {"iron": 3, "copper": 3, "titanium": 4}, 2e9, 20, "Iron dust: -20% mining efficiency"),
    "chromis":     ("Chromis",     "orion",    {"cobalt": 3, "nickel": 3, "platinum": 4}, 1.5e10, 23, "Magnetic shear: -25% mining efficiency"),
    "aurel":       ("Aurel",       "orion",    {"gold": 3, "iridium": 4, "solar_crystal": 3}, 1e11, 26, "Blinding light: -30% mining efficiency"),
    "vortexa":     ("Vortexa",     "nebula",   {"titanium": 3, "platinum": 3, "quantum_crystal": 4}, 4e11, 28, "Ion vortices: -30% mining efficiency"),
    "umbra":       ("Umbra",       "nebula",   {"uranium": 3, "dark_matter": 4, "ancient_fragment": 3}, 3e12, 31, "Light hunger: -35% mining efficiency"),
    "prismis":     ("Prismis",     "nebula",   {"quantum_crystal": 3, "solar_crystal": 3, "dark_matter": 4}, 2e13, 34, "Prismatic storms: -35% mining efficiency"),
    "reliqua":     ("Reliqua",     "void",     {"ancient_fragment": 4, "ancient_core": 3, "dark_matter": 3}, 1.5e13, 36, "Ancient wards: -40% mining efficiency"),
    "silence":     ("Silence",     "void",     {"ancient_core": 3, "star_essence": 3, "iridium": 4}, 1.2e14, 39, "Null silence: -45% mining efficiency"),
    "echo":        ("Echo",        "void",     {"uranium": 3, "ancient_fragment": 3, "star_essence": 4}, 9e14, 42, "Echoing screams: -45% mining efficiency"),
    "zenith":      ("Zenith",      "core",     {"star_essence": 4, "ancient_core": 3, "quantum_crystal": 3}, 7e15, 44, "Gravity shear: -50% mining efficiency"),
    "infinity":    ("Infinity",    "core",     {"star_essence": 3, "dark_matter": 3, "ancient_core": 4}, 5e16, 47, "Eventide horizon: -50% mining efficiency"),
    "genesis":     ("Genesis",     "core",     {"star_essence": 2, "ancient_core": 2, "quantum_crystal": 3, "dark_matter": 3}, 4e17, 50, "Crucible storms: -55% mining efficiency"),
}

PLANET_IDS = list(PLANETS.keys())


def planet(pid):
    name, gid, weights, uc, ul, hazard = PLANETS[pid]
    return {
        "id": pid, "name": name, "galaxy": gid, "weights": weights,
        "unlock_credits": uc, "unlock_level": ul, "hazard": hazard,
    }


def planets_of_galaxy(gid):
    return [pid for pid in PLANET_IDS if PLANETS[pid][1] == gid]


def planet_minerals(pid):
    weights = PLANETS[pid][2]
    total = sum(weights.values())
    return {m: w / total for m, w in weights.items()}


# size: (hp, ore, weight, respawn_seconds, is_ancient)
ASTEROID_SIZES = [
    ("Small",   30,   8,   42, 20,  False),
    ("Medium",  90,   25,  30, 35,  False),
    ("Large",   250,  70,  18, 55,  False),
    ("Giant",   700,  200, 8,  90,  False),
    ("Ancient", 2000, 520, 2,  180, True),
]

NODES_PER_PLANET = 6


def roll_asteroid(rng, pid, richness=1.0, luck=0.0):
    """Pick an asteroid size and split its ore across the planet's minerals."""
    galaxy_id = PLANETS[pid][1]
    g = galaxy(galaxy_id)
    weights = []
    for name, hp, ore, w, respawn, ancient in ASTEROID_SIZES:
        weight = w
        if ancient:
            weight *= 1.0 + luck
        weights.append(weight)
    total = sum(weights)
    roll = rng.random() * total
    acc = 0.0
    size = ASTEROID_SIZES[0]
    for i, entry in enumerate(ASTEROID_SIZES):
        acc += weights[i]
        if roll <= acc:
            size = entry
            break
    name, hp, ore, _w, respawn, ancient = size
    hp = hp * g["difficulty"] * (1.0 + 0.05 * richness)
    ore_total = ore * g["richness"] * richness * (2.2 if ancient else 1.0)
    split = planet_minerals(pid)
    content = {m: ore_total * share for m, share in split.items()}
    if ancient:
        # Ancient asteroids concentrate into the rarest mineral on the planet.
        rarest = max(split, key=lambda m: RARITY_ORDER[MINERALS[m][1]])
        content = {rarest: ore_total}
    return {
        "size": name, "hp": hp, "max_hp": hp, "content": content,
        "respawn": respawn, "ancient": ancient, "depleted_until": 0.0,
    }
