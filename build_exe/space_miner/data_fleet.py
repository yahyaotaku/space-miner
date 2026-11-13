"""Static content: ships, drones, buildings, upgrades, employees."""

# ships: id -> dict(name, cost, rate ore/s, cargo, research/s, defense, unlock_level, desc)
SHIPS = {
    "scout":          {"name": "Scout MK-I",        "cost": 2_000,     "rate": 1.0,  "cargo": 0,   "research": 0.0, "defense": 2,  "unlock_level": 3,  "desc": "Cheap survey ship. Good first fleet addition."},
    "miner":          {"name": "M-40 Miner",        "cost": 12_000,    "rate": 4.0,  "cargo": 0,   "research": 0.0, "defense": 3,  "unlock_level": 5,  "desc": "Dedicated ore-gutted workhorse."},
    "transporter":    {"name": "Haulmaster",        "cost": 60_000,    "rate": 1.5,  "cargo": 400, "research": 0.0, "defense": 2,  "unlock_level": 7,  "desc": "Each one adds +400 global storage per resource."},
    "heavy_miner":    {"name": "Titan Borer",       "cost": 90_000,    "rate": 15.0, "cargo": 0,   "research": 0.0, "defense": 5,  "unlock_level": 8,  "desc": "Industrial asteroid shredder."},
    "defender":       {"name": "Aegis Warden",      "cost": 400_000,   "rate": 1.0,  "cargo": 0,   "research": 0.0, "defense": 30, "unlock_level": 11, "desc": "Protects convoys from pirates."},
    "research_vessel":{"name": "Lumen Observatory", "cost": 250_000,   "rate": 1.0,  "cargo": 0,   "research": 0.5, "defense": 2,  "unlock_level": 10, "desc": "Generates 0.5 research data/s."},
    "industrial":     {"name": "Forgecruiser",      "cost": 1_000_000, "rate": 6.0,  "cargo": 100, "research": 0.0, "defense": 8,  "unlock_level": 12, "desc": "Each one cuts ship & building costs by 2%."},
}

SHIP_ORDER = ["scout", "miner", "transporter", "heavy_miner", "defender", "research_vessel", "industrial"]

# drones: id -> dict(name, cost, rate, desc)
DRONES = {
    "mining":   {"name": "Mining Drone",   "cost": 800,   "rate": 0.4, "desc": "Mines 0.4 ore/s on its assigned planet."},
    "cargo":    {"name": "Cargo Drone",    "cost": 1_200, "rate": 0.0, "desc": "+8% storage capacity per drone."},
    "scanner":  {"name": "Scanner Drone",  "cost": 1_600, "rate": 0.0, "desc": "+1.5% critical extraction chance per drone."},
    "repair":   {"name": "Repair Drone",   "cost": 2_000, "rate": 0.0, "desc": "-3% hazard penalty per drone."},
    "guardian": {"name": "Guardian Drone", "cost": 2_400, "rate": 0.0, "desc": "+8 defense against pirate encounters."},
}
DRONE_ORDER = ["mining", "cargo", "scanner", "repair", "guardian"]

# buildings: id -> dict(name, base_cost, desc). Built per planet, levels scale 1.6x.
BUILDINGS = {
    "mining_station": {"name": "Mining Station",  "cost": 1_500,   "desc": "+8% mining production on this planet per level."},
    "refinery":       {"name": "Refinery",        "cost": 3_000,   "desc": "+4% sell prices per level (global)."},
    "warehouse":      {"name": "Warehouse",       "cost": 2_500,   "desc": "+20% storage capacity per level (global)."},
    "energy_plant":   {"name": "Energy Plant",    "cost": 4_000,   "desc": "+2.0 energy/s per level (global)."},
    "laboratory":     {"name": "Research Lab",    "cost": 5_000,   "desc": "+0.3 research data/s per level (global)."},
    "shipyard":       {"name": "Shipyard",        "cost": 12_000,  "desc": "+2 fleet capacity and -2% ship costs per level."},
    "trading_hub":    {"name": "Trading Hub",     "cost": 8_000,   "desc": "+3% sell prices per level (global)."},
    "command_center": {"name": "Command Center",  "cost": 25_000,  "desc": "+5% all production and +1 drone cap per level."},
}
BUILDING_ORDER = list(BUILDINGS.keys())

# upgrades: id -> dict(name, base_cost, cost_mult, max_level, desc)
UPGRADES = {
    "laser_power":  {"name": "Laser Power",       "cost": 150,    "cost_mult": 2.2, "max": 40, "desc": "+60% laser damage per level."},
    "crit_chance":  {"name": "Crit Extraction",   "cost": 500,    "cost_mult": 2.0, "max": 12, "desc": "+2% critical extraction chance per level."},
    "storage":      {"name": "Storage Expansion", "cost": 400,    "cost_mult": 2.5, "max": 30, "desc": "+50% storage capacity per level."},
    "drone_cap":    {"name": "Drone Bays",        "cost": 2_500,  "cost_mult": 2.2, "max": 30, "desc": "+3 drone capacity per level."},
    "fleet_cap":    {"name": "Fleet Licenses",    "cost": 20_000, "cost_mult": 2.5, "max": 20, "desc": "+2 fleet capacity per level."},
    "respawn":      {"name": "Survey Beacons",    "cost": 2_000,  "cost_mult": 2.2, "max": 8,  "desc": "-8% asteroid respawn time per level."},
    "market_insight":{"name": "Market Insight",   "cost": 3_000,  "cost_mult": 2.4, "max": 10, "desc": "+5% sell prices per level."},
    "offline_cap":  {"name": "Deep Sleep Uplink", "cost": 5_000,  "cost_mult": 3.0, "max": 11, "desc": "+2h offline production capacity per level."},
    "offline_eff":  {"name": "Idle Protocols",    "cost": 10_000, "cost_mult": 2.5, "max": 10, "desc": "+5% offline efficiency per level."},
    "autosell":     {"name": "Market AI",         "cost": 50_000, "cost_mult": 1.0, "max": 1,  "desc": "Unlocks automatic selling of surplus ore."},
    "auto_miner":   {"name": "Auto-Turret Rig",   "cost": 250_000,"cost_mult": 1.0, "max": 1,  "desc": "Automatically fires your laser once per second."},
}
UPGRADE_ORDER = list(UPGRADES.keys())

# employees: id -> dict(name, base_cost, desc)
EMPLOYEES = {
    "engineer":  {"name": "Mining Engineer",    "cost": 5_000, "desc": "+2% mining production each."},
    "scientist": {"name": "Scientist",          "cost": 8_000, "desc": "+3% research rate each."},
    "pilot":     {"name": "Pilot",              "cost": 6_000, "desc": "+3% ship production each."},
    "mechanic":  {"name": "Mechanic",           "cost": 7_000, "desc": "-1.5% building & ship costs each (max 45%)."},
    "logistics": {"name": "Logistics Manager",  "cost": 4_000, "desc": "+6% storage capacity each."},
    "security":  {"name": "Security Officer",   "cost": 9_000, "desc": "+8 fleet defense each."},
}
EMPLOYEE_ORDER = list(EMPLOYEES.keys())

EMPLOYEE_COST_MULT = 1.6
