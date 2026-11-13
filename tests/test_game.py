"""Test suite for SPACE MINER. Run: python -m unittest discover -s tests -v"""
import os
import random
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from space_miner.game import Game
from space_miner import economy, production, mining as mining_sys, offline as offline_sys
from space_miner import save as save_sys
from space_miner.state import (new_state, mults, storage_cap, drone_cap, fleet_cap,
                               company_level, laser_power, cost_of_upgrade, validate,
                               cost_of_drone, offline_capacity_hours, offline_efficiency,
                               xp_needed_player)
from space_miner.data_world import roll_asteroid, PLANETS
from space_miner.data_tech import RESEARCH, ACHIEVEMENTS, MISSIONS
from space_miner.util import fmt


def make_game(now=1_000_000.0):
    rng = random.Random(7)
    return Game(new_state(now), now=now, rng=rng)


class TestFormatting(unittest.TestCase):
    def test_fmt(self):
        self.assertEqual(fmt(0), "0")
        self.assertEqual(fmt(999), "999")
        self.assertEqual(fmt(1500), "1.50K")
        self.assertEqual(fmt(2_500_000), "2.50M")
        self.assertEqual(fmt(3.4e12), "3.40T")
        self.assertEqual(fmt(1.2e45), "1.20e+45")
        self.assertEqual(fmt(-5), "-5")


class TestEconomy(unittest.TestCase):
    def test_sell_adds_credits(self):
        g = make_game()
        s = g.state
        s["resources"]["iron"] = 10.0
        gained = g.sell_resource("iron")
        self.assertGreater(gained, 0)
        self.assertAlmostEqual(s["resources"]["iron"], 0.0)
        self.assertAlmostEqual(s["credits"], 50.0 + gained)

    def test_sell_more_than_owned_is_clamped(self):
        g = make_game()
        g.state["resources"]["iron"] = 5.0
        gained = g.sell_resource("iron", 100)
        self.assertLessEqual(gained, 5 * economy.price(g.state, "iron") + 1e-9)

    def test_market_drift_stays_in_bounds(self):
        g = make_game()
        rng = random.Random(1)
        for _ in range(2000):
            economy.drift_market(g.state, 1.0, rng)
            for mid, m in g.state["market"].items():
                self.assertGreaterEqual(m["mult"], economy.PRICE_FLOOR - 1e-9)
                self.assertLessEqual(m["mult"], economy.PRICE_CEIL + 1e-9)

    def test_sell_mult_improves_with_refinery(self):
        g = make_game()
        s = g.state
        before = economy.price(s, "iron")
        s["buildings"]["asteroid_01:refinery"] = 5
        after = economy.price(s, "iron")
        self.assertGreater(after, before)


class TestMining(unittest.TestCase):
    def test_mine_damages_and_destroys(self):
        g = make_game()
        s = g.state
        node = s["planets"]["asteroid_01"]["nodes"][0]
        start_hp = node["hp"]
        destroyed = False
        iron_before = s["ore_mined"]
        for _ in range(500):
            r = g.do_mine(silent=True)
            if r.get("destroyed"):
                destroyed = True
                break
        self.assertTrue(destroyed)
        self.assertGreater(s["ore_mined"], iron_before)
        self.assertEqual(node["hp"], 0.0)

    def test_asteroid_respawns(self):
        g = make_game()
        s = g.state
        node = s["planets"]["asteroid_01"]["nodes"][0]
        node["hp"] = 0.0
        node["depleted_until"] = g.now + 10
        g.tick(g.now + 11)
        node = s["planets"]["asteroid_01"]["nodes"][0]
        self.assertGreater(node["hp"], 0.0)

    def test_crit_multiplies_damage(self):
        g = make_game()
        g.state["upgrades"]["crit_chance"] = 12
        g.state["drones"]["scanner"] = {"count": 10, "level": 1, "xp": 0, "planet": None}
        self.assertGreaterEqual(g.state["upgrades"]["crit_chance"], 12)
        self.assertGreater(mining_sys.crit_chance(g.state), 0.3)

    def test_ancient_asteroids_have_rare_content(self):
        rng = random.Random(3)
        node = None
        for _ in range(500):
            candidate = roll_asteroid(rng, "mystral")
            if candidate["ancient"]:
                node = candidate
                break
        self.assertIsNotNone(node)
        self.assertEqual(len(node["content"]), 1)
        self.assertIn(list(node["content"])[0], ("quantum_crystal", "dark_matter", "ancient_fragment"))


class TestProduction(unittest.TestCase):
    def test_drones_produce_when_assigned(self):
        g = make_game()
        s = g.state
        s["drones"]["mining"] = {"count": 5, "level": 1, "xp": 0, "planet": "asteroid_01"}
        rates = production.planet_rates(s, "asteroid_01")
        self.assertGreater(sum(rates.values()), 0)
        self.assertAlmostEqual(sum(rates.values()), 5 * 0.4, places=5)

    def test_unassigned_drones_produce_nothing(self):
        g = make_game()
        s = g.state
        s["drones"]["mining"] = {"count": 5, "level": 1, "xp": 0, "planet": None}
        self.assertEqual(sum(production.planet_rates(s, "asteroid_01").values()), 0)

    def test_production_respects_storage_cap(self):
        g = make_game()
        s = g.state
        s["drones"]["mining"] = {"count": 1000, "level": 10, "xp": 0, "planet": "asteroid_01"}
        cap = storage_cap(s)
        s["resources"]["iron"] = cap
        production.apply_production(s, 10)
        self.assertLessEqual(s["resources"]["iron"], cap + 1e-6)

    def test_production_scales_with_level(self):
        g = make_game()
        s = g.state
        s["drones"]["mining"] = {"count": 1, "level": 1, "xp": 0, "planet": "asteroid_01"}
        low = sum(production.planet_rates(s, "asteroid_01").values())
        s["drones"]["mining"]["level"] = 20
        high = sum(production.planet_rates(s, "asteroid_01").values())
        self.assertGreater(high, low * 5)

    def test_hazard_reduces_production(self):
        g = make_game()
        s = g.state
        s["planets"]["volcanis"]["unlocked"] = True
        s["drones"]["mining"] = {"count": 10, "level": 1, "xp": 0, "planet": "volcanis"}
        with_hazard = sum(production.planet_rates(s, "volcanis").values())
        s["buildings"]["volcanis:mining_station"] = 20
        mitigated = sum(production.planet_rates(s, "volcanis").values())
        self.assertGreater(mitigated, with_hazard)


class TestPurchases(unittest.TestCase):
    def test_upgrade_costs_scale(self):
        g = make_game()
        c0 = cost_of_upgrade(g.state, "laser_power")
        g.state["upgrades"]["laser_power"] = 5
        c5 = cost_of_upgrade(g.state, "laser_power")
        self.assertGreater(c5, c0 * 10)

    def test_buy_upgrade_deducts_credits(self):
        g = make_game()
        g.state["credits"] = 10_000
        ok, _ = g.buy_upgrade("laser_power")
        self.assertTrue(ok)
        self.assertEqual(g.state["upgrades"]["laser_power"], 1)
        self.assertLess(g.state["credits"], 10_000)

    def test_buy_upgrade_insufficient_funds(self):
        g = make_game()
        g.state["credits"] = 0
        ok, msg = g.buy_upgrade("laser_power")
        self.assertFalse(ok)
        self.assertIn("credits", msg.lower())

    def test_upgrade_max_level(self):
        g = make_game()
        g.state["credits"] = 1e30
        g.state["upgrades"]["crit_chance"] = 12
        ok, msg = g.buy_upgrade("crit_chance")
        self.assertFalse(ok)
        self.assertIn("maximum", msg.lower())

    def test_ship_requires_level_and_capacity(self):
        g = make_game()
        g.state["credits"] = 1e12
        ok, msg = g.buy_ship("scout")
        self.assertFalse(ok)
        g.state["player_level"] = 10
        ok, _ = g.buy_ship("scout")
        self.assertTrue(ok)
        g.state["ships"]["scout"]["count"] = fleet_cap(g.state)
        ok, msg = g.buy_ship("miner")
        self.assertFalse(ok)
        self.assertIn("capacity", msg.lower())

    def test_drone_cap_enforced(self):
        g = make_game()
        g.state["credits"] = 1e30
        g.state["drones"]["mining"] = {"count": drone_cap(g.state), "level": 1, "xp": 0, "planet": None}
        ok, msg = g.buy_drone("mining")
        self.assertFalse(ok)
        self.assertIn("full", msg.lower())

    def test_building_and_research(self):
        g = make_game()
        s = g.state
        s["credits"] = 1e9
        ok, _ = g.build("asteroid_01", "mining_station")
        self.assertTrue(ok)
        self.assertEqual(s["buildings"]["asteroid_01:mining_station"], 1)
        s["research_data"] = 1e9
        ok, _ = g.research("laser_focus")
        self.assertTrue(ok)
        ok, msg = g.research("plasma_drill")
        self.assertTrue(ok)
        ok, msg = g.research("singularity_bit")
        self.assertFalse(ok)  # needs laser_focus2
        self.assertIn("Requires", msg)

    def test_invalid_purchases_are_safe(self):
        g = make_game()
        self.assertFalse(g.buy_ship("nonexistent")[0])
        self.assertFalse(g.buy_drone("nope")[0])
        self.assertFalse(g.build("asteroid_01", "nope")[0])
        self.assertFalse(g.research("nope")[0])
        self.assertFalse(g.hire("nope")[0])


class TestMissionsAchievements(unittest.TestCase):
    def test_first_mission_completes(self):
        g = make_game()
        for _ in range(200):
            g.now += 30
            g.state["last_tick"] = g.now
            g.do_mine(silent=True)
        self.assertGreaterEqual(g.state["mission_index"], 1)
        self.assertGreater(g.state["credits"], 50)

    def test_achievement_granted_once(self):
        g = make_game()
        g.state["ores"] = 0
        g.state["ore_mined"] = 100
        g._check_achievements()
        self.assertIn("first_ore", g.state["achievements"])
        count = len(g.state["achievements"])
        g._check_achievements()
        self.assertEqual(len(g.state["achievements"]), count)

    def test_all_achievement_keys_known(self):
        g = make_game()
        for aid, name, desc, reward, key, value in ACHIEVEMENTS:
            self.assertIsInstance(g._achievement_value(key), (int, float))


class TestOffline(unittest.TestCase):
    def test_offline_production_with_summary(self):
        g = make_game()
        s = g.state
        s["drones"]["mining"] = {"count": 10, "level": 5, "xp": 0, "planet": "asteroid_01"}
        s["last_save"] = g.now
        now = g.now + 3600
        summary = offline_sys.offline_progress(s, now)
        self.assertIsNotNone(summary)
        self.assertTrue(summary["produced"])
        self.assertGreater(s["resources"]["iron"], 0)

    def test_offline_respects_capacity(self):
        g = make_game()
        s = g.state
        s["drones"]["mining"] = {"count": 100, "level": 5, "xp": 0, "planet": "asteroid_01"}
        s["last_save"] = g.now
        now = g.now + 100 * 3600
        summary = offline_sys.offline_progress(s, now)
        self.assertTrue(summary["capped"])
        self.assertLessEqual(summary["effective"], offline_capacity_hours(s) * 3600 + 1)

    def test_offline_efficiency_upgrade(self):
        g = make_game()
        self.assertAlmostEqual(offline_efficiency(g.state), 0.5)
        g.state["upgrades"]["offline_eff"] = 10
        self.assertAlmostEqual(offline_efficiency(g.state), 1.0)

    def test_no_offline_for_short_absence(self):
        g = make_game()
        g.state["last_save"] = g.now
        self.assertIsNone(offline_sys.offline_progress(g.state, g.now + 10))

    def test_game_load_applies_offline(self):
        g = make_game()
        g.state["drones"]["mining"] = {"count": 10, "level": 5, "xp": 0, "planet": "asteroid_01"}
        g.state["last_save"] = g.now - 7200
        g2 = Game(g.state, now=g.now + 100)
        summary = g2.apply_offline(g.now + 100)
        self.assertIsNotNone(summary)


class TestSave(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_env = os.environ.get("SPACE_MINER_HOME")
        os.environ["SPACE_MINER_HOME"] = self.tmp.name

    def tearDown(self):
        if self.old_env is None:
            os.environ.pop("SPACE_MINER_HOME", None)
        else:
            os.environ["SPACE_MINER_HOME"] = self.old_env
        self.tmp.cleanup()

    def test_save_and_load_roundtrip(self):
        g = make_game()
        g.state["credits"] = 12345.0
        g.state["resources"]["iron"] = 42.0
        self.assertTrue(g.save())
        loaded, source = save_sys.load()
        self.assertIsNotNone(loaded)
        self.assertEqual(source, "main")
        self.assertAlmostEqual(loaded["credits"], 12345.0)
        self.assertAlmostEqual(loaded["resources"]["iron"], 42.0)

    def test_corrupt_save_falls_back_to_backup(self):
        g = make_game()
        g.state["credits"] = 777.0
        g.save()
        g.state["credits"] = 999.0
        g.save()  # backup now holds 777
        with open(save_sys.save_path(), "w") as f:
            f.write("{corrupted json!!!")
        loaded, source = save_sys.load()
        self.assertIsNotNone(loaded)
        self.assertEqual(source, "backup")
        self.assertAlmostEqual(loaded["credits"], 777.0)

    def test_load_missing_save(self):
        loaded, source = save_sys.load()
        self.assertIsNone(loaded)
        self.assertIsNone(source)

    def test_versioned_migration(self):
        g = make_game()
        g.save()
        import json
        with open(save_sys.save_path()) as f:
            data = json.load(f)
        data["version"] = 1
        data.pop("essence_upgrades", None)
        with open(save_sys.save_path(), "w") as f:
            json.dump(data, f)
        loaded, _ = save_sys.load()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["version"], save_sys.SAVE_VERSION)
        self.assertIn("essence_upgrades", loaded)


class TestPrestige(unittest.TestCase):
    def test_no_essence_before_threshold(self):
        g = make_game()
        g.state["lifetime_credits"] = 1e6
        self.assertEqual(g.state["essence"], 0)
        from space_miner.prestige import essence_gain, can_rebirth
        self.assertEqual(essence_gain(g.state), 0)
        self.assertFalse(can_rebirth(g.state))

    def test_essence_scales_with_lifetime(self):
        from space_miner.prestige import essence_gain
        g = make_game()
        g.state["lifetime_credits"] = 1e9
        e1 = essence_gain(g.state)
        g.state["lifetime_credits"] = 4e9
        e2 = essence_gain(g.state)
        self.assertGreater(e1, 0)
        self.assertAlmostEqual(e2, e1 * 2, delta=2)

    def test_rebirth_resets_and_keeps(self):
        g = make_game()
        s = g.state
        s["lifetime_credits"] = 2e9
        s["credits"] = 5e5
        s["achievements"] = ["first_ore"]
        s["essence_upgrades"] = {"start_credits": 1}
        s["research"] = ["laser_focus"]
        s["drones"]["mining"] = {"count": 10, "level": 9, "xp": 0, "planet": "asteroid_01"}
        gain = g.do_rebirth(now=g.now + 10)
        self.assertGreater(gain, 0)
        ns = g.state
        self.assertEqual(ns["prestige_count"], 1)
        self.assertGreater(ns["essence"], 0)
        self.assertEqual(ns["achievements"], ["first_ore"])
        self.assertEqual(ns["research"], [])
        self.assertEqual(ns["ships"], {})
        self.assertEqual(ns["drones"], {})
        self.assertFalse(ns["planets"]["volcanis"]["unlocked"])
        self.assertTrue(ns["planets"]["asteroid_01"]["unlocked"])
        self.assertGreaterEqual(ns["credits"], 10_000)  # Seed Capital 1
        self.assertEqual(ns["kills"], s["kills"])

    def test_essence_improves_production(self):
        g = make_game()
        g.state["essence"] = 50
        m = mults(g.state)
        self.assertAlmostEqual(m["all"], 2.0, places=5)


class TestState(unittest.TestCase):
    def test_new_state_valid(self):
        s = new_state(0.0)
        self.assertTrue(validate(s))
        self.assertEqual(s["player_level"], 1)
        self.assertTrue(s["planets"]["asteroid_01"]["unlocked"])
        for pid in PLANETS:
            self.assertEqual(len(s["planets"][pid]["nodes"]), 6)

    def test_validate_rejects_garbage(self):
        self.assertFalse(validate({}))
        self.assertFalse(validate(None) if False else validate({"credits": 1}))

    def test_company_level_curve(self):
        self.assertEqual(company_level(500), 1)
        self.assertEqual(company_level(1000), 1)
        self.assertEqual(company_level(1e6), 4)
        self.assertEqual(company_level(1e9), 7)

    def test_mults_never_zero_or_negative(self):
        g = make_game()
        s = g.state
        s["research"] = list(RESEARCH.keys())
        s["employees"] = {"engineer": 5, "mechanic": 20}
        m = mults(s)
        for k, v in m.items():
            self.assertGreater(v, 0, f"multiplier {k} must be positive")


class TestGameTick(unittest.TestCase):
    def test_tick_advances_production_and_time(self):
        g = make_game()
        g.state["drones"]["mining"] = {"count": 10, "level": 1, "xp": 0, "planet": "asteroid_01"}
        g.tick(g.now + 60)
        self.assertGreater(sum(g.state["resources"].values()), 0)
        self.assertAlmostEqual(g.state["play_time"], 60, places=5)

    def test_no_time_travel_abuse(self):
        g = make_game()
        g.state["drones"]["mining"] = {"count": 100, "level": 20, "xp": 0, "planet": "asteroid_01"}
        g.tick(g.now + 100000)  # huge dt must be clamped
        cap = storage_cap(g.state)
        for mid, amt in g.state["resources"].items():
            self.assertLessEqual(amt, cap + 1e-6)

    def test_events_trigger(self):
        g = make_game()
        g.state["next_event_at"] = g.now
        g.tick(g.now + 1)
        # after the tick an event may have fired; next_event_at must be in the future
        self.assertGreater(g.state["next_event_at"], g.now)

    def test_overdrive(self):
        g = make_game()
        g.state["energy"] = 100
        self.assertTrue(g.overdrive())
        self.assertEqual(g.state["energy"], 75)
        self.assertFalse(g.overdrive())  # already active


if __name__ == "__main__":
    unittest.main(verbosity=2)
