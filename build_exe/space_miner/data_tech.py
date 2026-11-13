"""Static content: research tree, missions, achievements, events."""

# research: id -> (branch, tier, name, cost, prereqs, effect_key, effect_value, desc)
RESEARCH = {
    # Mining Technology
    "laser_focus":    ("mining", 1, "Laser Focus I",    20,    [],                 "laser_mult", 0.5,  "+50% laser damage."),
    "crit_matrix":    ("mining", 1, "Crit Matrix",      45,    ["laser_focus"],    "crit",       0.10, "+10% critical extraction chance."),
    "plasma_drill":   ("mining", 2, "Plasma Drill",     120,   ["laser_focus"],    "laser_mult", 1.0,  "+100% laser damage."),
    "rare_scan":      ("mining", 2, "Rare Scan",        180,   ["crit_matrix"],    "rare_luck",  1.0,  "Ancient asteroids yield 2x ore."),
    "laser_focus2":   ("mining", 3, "Laser Focus II",   400,   ["plasma_drill"],   "laser_mult", 1.5,  "+150% laser damage."),
    "deep_scan":      ("mining", 3, "Deep Survey",      600,   ["rare_scan"],      "respawn",    0.25, "Asteroids respawn 25% faster."),
    "singularity_bit":("mining", 4, "Singularity Bit",  1500,  ["laser_focus2"],   "laser_mult", 3.0,  "+300% laser damage."),
    # Space Engineering
    "engines":        ("engineering", 1, "Ion Engines",     25,   [],                "ship_mult",   0.25, "+25% ship production."),
    "cargo_racks":    ("engineering", 1, "Cargo Racks",     50,   [],                "storage_mult",1.0,  "+100% storage capacity."),
    "reactor":        ("engineering", 2, "Fusion Reactor",  130,  ["engines"],       "energy_mult", 0.5,  "+50% energy production."),
    "fleet_logistics":("engineering", 2, "Fleet Logistics", 200,  ["engines"],       "fleet_cap",   4,    "+4 fleet capacity."),
    "engines2":       ("engineering", 3, "Antimatter Drive",500,  ["reactor"],       "ship_mult",   0.75, "+75% ship production."),
    "hull_frame":     ("engineering", 3, "Reinforced Hulls",700,  ["fleet_logistics"],"all_mult",   0.20, "+20% all production."),
    "dyson_tap":      ("engineering", 4, "Dyson Tap",       1800, ["engines2"],      "energy_mult", 2.0,  "+200% energy production."),
    # Automation
    "drone_swarms":   ("automation", 1, "Drone Swarms",     30,   [],               "drone_cap",   2,   "+2 drone capacity."),
    "drone_ai":       ("automation", 1, "Neural Drill AI",  70,   ["drone_swarms"], "drone_mult",  0.5, "+50% drone production."),
    "drone_swarms2":  ("automation", 2, "Swarm Logistics",  150,  ["drone_swarms"], "drone_cap",   3,   "+3 drone capacity."),
    "market_ai":      ("automation", 2, "Market AI",        250,  ["drone_ai"],     "autosell",    1,   "Unlocks automatic selling (also toggle in Options)."),
    "drone_ai2":      ("automation", 3, "Swarm Mind",       650,  ["drone_swarms2"],"drone_mult",  1.5, "+150% drone production."),
    "factory_ai":     ("automation", 3, "Factory AI",       900,  ["market_ai"],    "build_cost",  0.15,"Buildings & ships cost 15% less."),
    "logistics_ai":   ("automation", 4, "Quantum Warehousing",2200,["drone_ai2"],   "storage_mult",1.5, "+150% storage capacity."),
    # Scientific Research
    "data_pipeline":  ("science", 1, "Data Pipeline",      35,   [],               "research_mult",0.5, "+50% research data generation."),
    "market_theory":  ("science", 1, "Market Theory",      60,   ["data_pipeline"],"sell_mult",   0.10,"+10% sell prices."),
    "xenology":       ("science", 2, "Xenology",           160,  ["data_pipeline"],"xeno",        5,   "Ancient asteroids drop +5 research data."),
    "astro_survey":   ("science", 2, "Deep Space Survey",  300,  ["market_theory"],"all_mult",    0.15,"+15% all production."),
    "ancient_studies":("science", 3, "Ancient Studies",    800,  ["xenology"],     "essence_gain",0.25,"+25% Stellar Essence from rebirths."),
    "exotic_energy":  ("science", 3, "Exotic Energy",      1000, ["astro_survey"], "overdrive",   0.5, "Overdrive costs 50% less energy."),
    "star_song":      ("science", 4, "Song of Stars",      2600, ["ancient_studies"],"all_mult",  0.50,"+50% all production."),
}
RESEARCH_ORDER = list(RESEARCH.keys())
BRANCHES = ["mining", "engineering", "automation", "science"]
BRANCH_NAMES = {
    "mining": "Mining Technology", "engineering": "Space Engineering",
    "automation": "Automation", "science": "Scientific Research",
}


def research_info(rid):
    branch, tier, name, cost, prereqs, key, val, desc = RESEARCH[rid]
    return {"id": rid, "branch": branch, "tier": tier, "name": name, "cost": cost,
            "prereqs": prereqs, "effect": (key, val), "desc": desc}


# story missions, completed in order. objective: (kind, target)
MISSIONS = [
    ("First Ore",        "mine_ore",       10,     {"credits": 200}),
    ("Salesman",         "sell_count",     10,     {"credits": 300}),
    ("Tools of Trade",   "buy_upgrade",    1,      {"credits": 500, "research": 5}),
    ("Drone Age",        "own_drones",     1,      {"credits": 1_000}),
    ("Fleet of One",     "own_ships",      1,      {"credits": 2_000}),
    ("Veteran",          "player_level",   3,      {"energy": 20}),
    ("Ore Mountains",    "mine_ore",       500,    {"credits": 5_000}),
    ("New Horizons",     "unlock_planet",  1,      {"research": 20}),
    ("Rising Star",      "lifetime_credits", 50_000,  {"credits": 10_000}),
    ("Swarm",            "own_drones",     5,      {"credits": 15_000}),
    ("Infrastructure",   "building_level", 1,      {"credits": 20_000}),
    ("Science!",         "research_count", 2,      {"research": 30}),
    ("Millionaire",      "lifetime_credits", 1e6,   {"credits": 100_000}),
    ("Heavy Metal",      "own_ship_type",  1,      {"credits": 150_000}),
    ("Cold Frontier",    "unlock_planet",  2,      {"research": 80}),
    ("Trader",           "sell_count",     1_000,  {"credits": 300_000}),
    ("Ace Miner",        "player_level",   10,     {"energy": 100}),
    ("Centimillionaire", "lifetime_credits", 1e8,  {"credits": 2e6}),
    ("Star Chaser",      "unlock_planet",  3,      {"research": 200}),
    ("Drone Baron",      "own_drones",     20,     {"credits": 5e6}),
    ("Tech Core",        "research_count", 8,      {"research": 500}),
    ("Legend",           "player_level",   15,     {"energy": 500}),
    ("Billionaire",      "lifetime_credits", 1e9,  {"credits": 5e7}),
    ("Into the Fog",     "unlock_planet",  4,      {"research": 1500}),
    ("Ancient Echoes",   "ancient_kills",  10,     {"research": 3000}),
    ("Corporation",      "company_level",  5,      {"credits": 1e8}),
    ("Trillionaire",     "lifetime_credits", 1e12, {"credits": 5e9}),
    ("Galactic Rebirth", "prestige",       1,      {"research": 5000}),
]
DAILY_TEMPLATES = [
    ("mine_ore", 300, "Mine {n} ore today"),
    ("sell_count", 200, "Sell {n} resources today"),
    ("destroy", 25, "Destroy {n} asteroids today"),
    ("lifetime_credits", 20_000, "Earn {n} credits today"),
]

# achievements: id -> (name, desc, reward_credits, check_key, check_value)
ACHIEVEMENTS = [
    ("first_ore",     "First Ore",        "Mine your first ore.",              100,    "ore_mined", 1),
    ("credits_1k",    "Pocket Change",    "Earn 1K lifetime credits.",         200,    "lifetime_credits", 1e3),
    ("credits_1m",    "Millionaire",      "Earn 1M lifetime credits.",         5_000,  "lifetime_credits", 1e6),
    ("credits_1b",    "Billionaire",      "Earn 1B lifetime credits.",         5e5,    "lifetime_credits", 1e9),
    ("credits_1t",    "Trillionaire",     "Earn 1T lifetime credits.",         1e7,    "lifetime_credits", 1e12),
    ("credits_1qa",   "Quadrillionaire",  "Earn 1Qa lifetime credits.",        1e9,    "lifetime_credits", 1e15),
    ("drones_10",     "Drone Keeper",     "Own 10 drones.",                    2_000,  "drones", 10),
    ("drones_50",     "Swarm Lord",       "Own 50 drones.",                    50_000, "drones", 50),
    ("drones_150",    "Hive Mind",        "Own 150 drones.",                   1e6,    "drones", 150),
    ("ships_5",       "Collector",        "Own 5 ships.",                      10_000, "ships", 5),
    ("ships_15",      "Armada",           "Own 15 ships.",                     2e5,    "ships", 15),
    ("ship_types_5",  "Fleet Admiral",    "Own 5 different ship types.",       1e5,    "ship_types", 5),
    ("planets_2",     "Colonizer",        "Unlock 2 planets.",                 1_000,  "planets", 2),
    ("planets_5",     "Frontier Barony",  "Unlock all 5 Frontier planets.",    1e5,    "planets", 5),
    ("planets_8",     "Cross-Galactic",   "Unlock 8 planets.",                 1e6,    "planets", 8),
    ("planets_all",   "Universal Baron",  "Unlock every planet.",              1e8,    "planets", 17),
    ("galaxy_2",      "Pathfinder",       "Unlock a second galaxy.",           5e5,    "galaxies", 2),
    ("galaxy_all",    "Galactic Emperor", "Unlock all 5 galaxies.",            1e10,   "galaxies", 5),
    ("research_5",    "Student",          "Complete 5 technologies.",          2_000,  "research", 5),
    ("research_15",   "Professor",        "Complete 15 technologies.",         1e5,    "research", 15),
    ("research_all",  "Omniscient",       "Complete every technology.",        1e7,    "research", 26),
    ("kills_100",     "Rock Breaker",     "Destroy 100 asteroids.",            1_000,  "kills", 100),
    ("kills_1000",    "Belt Clearer",     "Destroy 1,000 asteroids.",          1e5,    "kills", 1000),
    ("ancient_1",     "Echoes of Old",    "Destroy an Ancient asteroid.",      5_000,  "ancient_kills", 1),
    ("ancient_50",    "Archaeologist",    "Destroy 50 Ancient asteroids.",     5e5,    "ancient_kills", 50),
    ("level_10",      "Seasoned Miner",   "Reach player level 10.",            5_000,  "player_level", 10),
    ("level_25",      "Space Veteran",    "Reach player level 25.",            1e5,    "player_level", 25),
    ("level_50",      "Living Legend",    "Reach player level 50.",            1e7,    "player_level", 50),
    ("company_10",    "CEO",              "Reach company level 10.",           1e6,    "company_level", 10),
    ("employees_10",  "Human Resources",  "Hire 10 employees.",                20_000, "employees", 10),
    ("prestige_1",    "Reborn",           "Perform a Galactic Rebirth.",       0,      "prestige", 1),
    ("prestige_5",    "Cycle Master",     "Perform 5 Galactic Rebirths.",      0,      "prestige", 5),
    ("essence_100",   "Star Soul",        "Hold 100 Stellar Essence.",         0,      "essence", 100),
    ("buildings_10",  "Urban Planner",    "Reach 10 total building levels.",   10_000, "building_levels", 10),
]

# random events: id -> (name, weight, kind, value, duration, desc)
EVENTS = [
    ("market_boom",   "Market Boom",     20, "sell_mult",  0.5,  90,  "Sell prices +50%."),
    ("mineral_rush",  "Mineral Rush",    20, "mine_mult",  1.0,  90,  "Mining production +100%."),
    ("asteroid_storm","Asteroid Storm",  15, "mine_mult",  0.5,  60,  "Mining production +50%."),
    ("solar_flare",   "Solar Flare",     15, "energy_mult",2.0,  90,  "Energy production +200%."),
    ("data_stream",   "Data Stream",     12, "research_mult", 1.0, 90,"Research generation +100%."),
    ("alien_signal",  "Alien Signal",    8,  "instant_research", 60, 0, "A burst of alien data: +research now."),
    ("ancient_find",  "Ancient Discovery",5, "instant_credits", 0,   0,  "A vault of ancient wealth: +credits now."),
    ("pirates",       "Pirate Encounter",10, "pirates",    0,    0,   "Pirates demand tribute. Your defense decides."),
]
EVENT_INTERVAL = (150, 360)
