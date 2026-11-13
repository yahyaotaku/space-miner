"""Headless GUI tests (SDL dummy driver). Skipped if pygame is unavailable."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

if HAS_PYGAME:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"

    from space_miner.gui import theme
    from space_miner.gui.app import App, OfflineModal
    from space_miner.game import Game
    from space_miner.state import new_state
    from space_miner.gui.mining_view import SCREEN_MAP

    def make_app():
        pygame.init()
        theme.init_fonts()
        surface = pygame.display.set_mode((1280, 800))
        game = Game(new_state(1000.0), now=1000.0)
        return App(game, surface)


@unittest.skipUnless(HAS_PYGAME, "pygame not installed")
class TestGui(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = make_app()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.app.pop()
        self.app.modal = None

    def test_mining_view_frames(self):
        app = self.app
        for i in range(300):
            events = []
            if i % 5 == 0:
                events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, unicode=" "))
            app.step(events, dt=1 / 60)
            app.draw_frame()
        self.assertGreater(app.game.state["kills"], 0)
        self.assertGreater(app.game.state["ore_mined"], 0)

    def test_all_menu_screens_render(self):
        for key, cls in SCREEN_MAP.items():
            self.app.open(cls)
            for _ in range(3):
                self.app.step([], dt=1 / 60)
                self.app.draw_frame()
            self.assertIsNotNone(self.app.menu)
            self.app.pop()
        self.assertIsNone(self.app.menu)

    def test_market_click_sells(self):
        app = self.app
        app.open(SCREEN_MAP["s"])
        app.game.state["resources"]["iron"] = 20
        for _ in range(2):
            app.step([], dt=1 / 60)
            app.draw_frame()
        r = app.menu.content_rect(app.surface)
        app.menu.handle_click((r.x + 50, r.y + 10))
        self.assertGreater(app.game.state["ore_sold"], 0)

    def test_keyboard_screen_opening(self):
        app = self.app
        app.pop()
        app.step([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_u, unicode="u")], dt=1 / 60)
        self.assertEqual(type(app.menu).__name__, "UpgradesScreen")
        app.step([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="")], dt=1 / 60)
        self.assertIsNone(app.menu)

    def test_overdrive_button(self):
        app = self.app
        app.pop()
        app.game.state["energy"] = 100
        app.do_overdrive()
        self.assertGreater(app.game.state["overdrive_until"], app.game.now)

    def test_offline_modal_dismiss(self):
        app = self.app
        app.modal = OfflineModal(["WELCOME BACK", "  +10 Iron"])
        app.draw_frame()
        app.step([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(640, 400))], dt=1 / 60)
        self.assertIsNone(app.modal)

    def test_quit_saves(self):
        app = self.app
        app.quit()
        self.assertFalse(app.running)


if __name__ == "__main__":
    unittest.main(verbosity=2)
