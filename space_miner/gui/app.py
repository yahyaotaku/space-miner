"""GUI application: pygame loop, screen routing, offline modal."""
import math
import os
import time

import pygame

from .. import save as save_sys
from ..data_world import mineral_rarity
from ..game import Game
from ..offline import render_summary
from ..util import fmt
from . import theme
from .sfx import Sfx
from .widgets import draw_text
from .mining_view import MiningView


class OfflineModal:
    def __init__(self, lines):
        self.lines = lines

    def draw(self, surface):
        w, h = surface.get_size()
        dim = pygame.Surface((w, h), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        surface.blit(dim, (0, 0))
        pw = 560
        ph = 90 + 20 * len(self.lines)
        rect = pygame.Rect((w - pw) // 2, (h - ph) // 2, pw, ph)
        pygame.draw.rect(surface, theme.PANEL, rect, border_radius=8)
        pygame.draw.rect(surface, theme.CYAN, rect, 2, border_radius=8)
        y = rect.y + 16
        for i, ln in enumerate(self.lines):
            color = theme.CYAN if i == 0 else theme.TEXT
            draw_text(surface, ln.strip(), (rect.x + 20, y), "sm" if i else "lg", color)
            y += 22
        draw_text(surface, "Click anywhere to continue", (rect.centerx, rect.bottom - 28),
                  "sm", theme.GOLD, center=True)


class App:
    SCREEN_SIZE = (1280, 800)

    def __init__(self, game, surface):
        self.game = game
        self.surface = surface
        self.running = True
        self.mining = MiningView(self)
        self.menu = None          # top menu screen or None
        self.modal = None
        self.particles = []
        self.floaters = []
        self.laser_timer = 0.0
        self.hover_asteroid = None
        self.hud_buttons = []
        self.toast = None
        self.sfx = Sfx(enabled=game.state["settings"].get("sound", True))
        self._last_frame = time.time()

    # ------------------------------------------------------------ screens
    def open(self, screen_cls):
        self.menu = screen_cls(self)

    def pop(self):
        self.menu = None

    def notify(self, msg, sound="buy"):
        self.game.log(msg)
        self.toast = (msg, time.time() + 2.6)
        self.sfx.play(sound)

    def quit(self):
        self.game.save()
        self.running = False

    # ------------------------------------------------------------ actions
    def do_mine(self):
        result = self.game.do_mine()
        if not result.get("hit"):
            self.notify("Asteroid is regenerating - pick another target.", "error")
            return
        self.laser_timer = 0.16
        self.sfx.play("crit" if result.get("crit") else "mine")
        cx, cy = self.mining.asteroid_centers()[self.game.state["selected_node"]]
        self._spawn_sparks(cx, cy, 4, theme.YELLOW)
        if result.get("destroyed"):
            self.sfx.play("destroy")
            self._spawn_burst(cx, cy, 34, theme.CYAN)
            for mid, amt in result["yield"].items():
                self._spawn_floater(f"+{fmt(amt)} {mid.replace('_', ' ').title()}", cx, cy,
                                    theme.RARITY[mineral_rarity(mid)])
            if result.get("research"):
                self._spawn_floater(f"+{fmt(result['research'])} research", cx, cy - 26, theme.MAGENTA)

    def do_overdrive(self):
        if self.game.overdrive():
            self.sfx.play("prestige")
            self._spawn_floater("OVERDRIVE!", *self.mining.asteroid_centers()[self.game.state["selected_node"]],
                                theme.CYAN)
        else:
            self.sfx.play("error")

    # ------------------------------------------------------------ particles
    def _spawn_sparks(self, x, y, n, color):
        for _ in range(n):
            self._add_particle(x, y, color, speed=140, life=0.3)

    def _spawn_burst(self, x, y, n, color):
        for _ in range(n // 2):
            self._add_particle(x, y, color, speed=260, life=0.9)
        for _ in range(n - n // 2):
            self._add_particle(x, y, theme.GOLD, speed=180, life=0.7)

    def _add_particle(self, x, y, color, speed, life):
        if len(self.particles) > 600:
            self.particles.pop(0)
        import random as _r
        ang = _r.uniform(0, 6.283)
        v = _r.uniform(speed * 0.3, speed)
        self.particles.append({"x": x, "y": y, "vx": math.cos(ang) * v, "vy": math.sin(ang) * v,
                               "life": life, "max_life": life, "color": color})

    def _spawn_floater(self, text, x, y, color):
        if len(self.floaters) > 30:
            self.floaters.pop(0)
        self.floaters.append({"text": text, "x": x, "y": y - 20, "vy": -34,
                              "life": 1.4, "max_life": 1.4, "color": color})

    def _update_fx(self, dt):
        self.laser_timer = max(0.0, self.laser_timer - dt)
        for p in self.particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += 60 * dt
            p["life"] -= dt
        self.particles = [p for p in self.particles if p["life"] > 0]
        for f in self.floaters:
            f["y"] += f["vy"] * dt
            f["life"] -= dt
        self.floaters = [f for f in self.floaters if f["life"] > 0]

    # ------------------------------------------------------------ frame
    def process_event(self, event):
        if self.modal:
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                self.modal = None
            return
        if event.type == pygame.QUIT:
            self.quit()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.menu:
                for b in self.menu.widgets(pos):
                    if b.clicked(pos):
                        b.cb()
                        return
                if hasattr(self.menu, "handle_click"):
                    self.menu.handle_click(pos)
            else:
                for b in self.hud_buttons:
                    if b.clicked(pos):
                        b.cb()
                        return
                self.mining.handle_click(pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self.menu:
                rect = self.menu.content_rect(self.surface)
                self.menu.wheel(event, 4000, rect.h)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.pop()
                return
            if self.menu:
                self.menu.handle_event(event)
            else:
                self.mining.handle_event(event)

    def step(self, events=None, dt=None):
        """Advance one frame. Exposed for headless testing."""
        if events is None:
            events = pygame.event.get()
        for event in events:
            self.process_event(event)
        now = time.time()
        dt = dt if dt is not None else min(0.1, now - self._last_frame)
        self._last_frame = now
        self.game.tick(now)
        self._update_fx(dt)
        self.mining.tick(dt)

    def draw_frame(self):
        mouse_pos = pygame.mouse.get_pos()
        self.surface.fill(theme.BG)
        if self.menu:
            self.menu.draw_frame(self.surface, mouse_pos)
        else:
            self.mining.draw(self.surface, mouse_pos)
        if self.toast and time.time() < self.toast[1]:
            txt = self.toast[0]
            f = theme.font("sm")
            tw = f.size(txt)[0] + 24
            rect = pygame.Rect((self.surface.get_width() - tw) // 2, 96, tw, 30)
            pygame.draw.rect(self.surface, (10, 16, 32), rect, border_radius=6)
            pygame.draw.rect(self.surface, theme.GOLD, rect, 1, border_radius=6)
            draw_text(self.surface, txt, rect.center, "sm", theme.GOLD, center=True)
        if self.modal:
            self.modal.draw(self.surface)

    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            self.step()
            self.draw_frame()
            pygame.display.flip()
            clock.tick(60)
        self.sfx.shutdown()


def _make_icon():
    icon = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.circle(icon, (30, 44, 80), (16, 16), 14)
    pygame.draw.circle(icon, (255, 208, 92), (22, 10), 5)
    pygame.draw.polygon(icon, (80, 220, 255), [(6, 26), (26, 26), (16, 8)])
    return icon


def run_gui(save_state=None, size=None):
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
    pygame.init()
    theme.init_fonts()
    size = size or App.SCREEN_SIZE
    surface = pygame.display.set_mode(size, pygame.RESIZABLE)
    pygame.display.set_caption("SPACE MINER")
    pygame.display.set_icon(_make_icon())

    state, source = save_sys.load()
    game = Game(state if state is not None else save_state)
    app = App(game, surface)
    if source is not None:
        summary = game.apply_offline(time.time())
        if summary:
            app.modal = OfflineModal(render_summary(summary))
    try:
        app.run()
    finally:
        game.save()
        pygame.quit()
    return 0
