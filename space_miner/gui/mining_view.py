"""The main mining view: starfield, asteroids, laser, particles, HUD."""
import math
import random

import pygame

from ..data_world import planet, galaxy, mineral_rarity, MINERALS
from ..data_fleet import UPGRADES
from ..state import (mults, xp_needed_player, company_level, storage_cap, drone_count,
                     drone_cap, ship_count, fleet_cap, unlocked_planets, defense_power,
                     planet_hazard, laser_power, crit_chance)
from ..production import planet_rates, total_rates, energy_rate, research_rate
from ..util import fmt, fmt_time
from . import theme
from .widgets import Button, draw_text, draw_panel, draw_bar
from .screens import (MarketScreen, UpgradesScreen, DronesScreen, FleetScreen,
                      GalaxyScreen, BuildingsScreen, ResearchScreen, MissionsScreen,
                      CrewScreen, AchievementsScreen, StatsScreen, SettingsScreen,
                      RebirthScreen, HelpScreen)

ASTEROID_RADIUS = {"Small": 24, "Medium": 34, "Large": 46, "Giant": 60, "Ancient": 70}

SCREEN_MAP = {
    "s": MarketScreen, "u": UpgradesScreen, "d": DronesScreen, "f": FleetScreen,
    "p": GalaxyScreen, "b": BuildingsScreen, "r": ResearchScreen, "j": MissionsScreen,
    "e": CrewScreen, "a": AchievementsScreen, "t": StatsScreen, "v": SettingsScreen,
    "x": RebirthScreen, "?": HelpScreen, "m": MarketScreen,
}


def make_starfield(w, h, count=140, seed=42):
    rng = random.Random(seed)
    stars = []
    for _ in range(count):
        stars.append({
            "x": rng.uniform(0, w), "y": rng.uniform(0, h),
            "r": rng.choice((1, 1, 1, 2, 2, 3)),
            "v": rng.uniform(2.0, 9.0),
            "tw": rng.uniform(0.5, 1.5),
            "b": rng.uniform(90, 220),
        })
    return stars


def asteroid_shape(index, radius, seed=7):
    rng = random.Random(seed + index * 131)
    pts = []
    n = rng.randint(8, 11)
    for i in range(n):
        ang = 2 * math.pi * i / n
        r = radius * rng.uniform(0.78, 1.12)
        pts.append((math.cos(ang) * r, math.sin(ang) * r))
    return pts


class MiningView:
    def __init__(self, app):
        self.app = app
        w, h = app.surface.get_size()
        self.stars = make_starfield(w, h)
        self.shapes = {i: asteroid_shape(i, 1.0) for i in range(6)}

    @property
    def g(self):
        return self.app.game

    # ------------------------------------------------------------ layout
    def asteroid_centers(self):
        w, h = self.app.surface.get_size()
        cx = int(w * 0.36)
        cy = int(h * 0.42)
        spots = [(-260, -120), (0, -150), (260, -110),
                 (-300, 40), (10, 20), (290, 60)]
        return [(cx + dx, cy + dy) for dx, dy in spots]

    def ship_pos(self):
        w, h = self.app.surface.get_size()
        return (int(w * 0.36), int(h * 0.42) + 250)

    # ------------------------------------------------------------ update
    def tick(self, dt):
        for star in self.stars:
            star["y"] += star["v"] * dt
            if star["y"] > self.app.surface.get_height():
                star["y"] -= self.app.surface.get_height()

    # ------------------------------------------------------------ drawing
    def draw_background(self, surface):
        surface.fill(theme.BG)
        now = pygame.time.get_ticks() / 1000.0
        w, h = surface.get_size()
        for gx, gy, gr, col in ((0.2, 0.3, 260, (36, 20, 70)), (0.75, 0.65, 320, (20, 30, 72)),
                                (0.55, 0.15, 200, (46, 22, 64))):
            blob = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
            pygame.draw.circle(blob, col + (46,), (gr, gr), gr)
            surface.blit(blob, (w * gx - gr, h * gy - gr))
        t = now
        for star in self.stars:
            b = int(star["b"] * (0.75 + 0.25 * math.sin(t * star["tw"] * 3)))
            pygame.draw.circle(surface, (b, b, min(255, b + 30)), (int(star["x"]), int(star["y"])), star["r"])

    def draw_asteroids(self, surface, mouse_pos):
        s = self.g.state
        pid = s["selected_planet"]
        nodes = s["planets"][pid]["nodes"]
        centers = self.asteroid_centers()
        self.app.hover_asteroid = None
        for i, node in enumerate(nodes):
            cx, cy = centers[i]
            if node["hp"] <= 0:
                remaining = max(0.0, node["depleted_until"] - self.app.game.now)
                pygame.draw.circle(surface, (40, 48, 70), (cx, cy), 20, 1)
                draw_text(surface, f"regen {fmt_time(remaining)}", (cx, cy), "xs", theme.DIM, center=True)
                continue
            dominant = max(node["content"].items(), key=lambda kv: MINERALS[kv[0]][2])[0]
            base = theme.RARITY[mineral_rarity(dominant)]
            radius = ASTEROID_RADIUS[node["size"]]
            scale = radius
            pts = [(cx + x * scale, cy + y * scale) for x, y in self.shapes[i]]
            frac = node["hp"] / node["max_hp"]
            fill = tuple(int(c * (0.35 + 0.4 * frac)) for c in base)
            selected = s["selected_node"] == i
            pygame.draw.polygon(surface, fill, pts)
            pygame.draw.polygon(surface, base if selected else theme.BORDER, pts, 2 if selected else 1)
            if node["ancient"]:
                pulse = 3 + int(2 * math.sin(pygame.time.get_ticks() / 200.0))
                pygame.draw.circle(surface, theme.GOLD, (cx, cy), radius + pulse, 1)
            draw_bar(surface, pygame.Rect(cx - radius, cy + radius + 6, radius * 2, 6), frac,
                     theme.GREEN if frac > 0.4 else theme.RED)
            draw_text(surface, node["size"], (cx, cy + radius + 20), "xs",
                      theme.GOLD if node["ancient"] else theme.DIM, center=True)
            if pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2).collidepoint(mouse_pos):
                self.app.hover_asteroid = i
                if not selected:
                    pygame.draw.circle(surface, theme.TEXT, (cx, cy), radius + 4, 1)

    def draw_ship_and_laser(self, surface):
        s = self.g.state
        sx, sy = self.ship_pos()
        pygame.draw.polygon(surface, theme.CYAN, [(sx - 18, sy + 14), (sx + 18, sy + 14), (sx, sy - 16)])
        pygame.draw.rect(surface, theme.BORDER_BRIGHT, (sx - 10, sy + 14, 20, 6))
        flame = 6 + int(5 * abs(math.sin(pygame.time.get_ticks() / 90.0)))
        pygame.draw.polygon(surface, theme.GOLD, [(sx - 6, sy + 20), (sx + 6, sy + 20), (sx, sy + 20 + flame)])
        if self.app.laser_timer > 0:
            cx, cy = self.asteroid_centers()[s["selected_node"]]
            width = 4 if self.app.laser_timer > 0.1 else 2
            pygame.draw.line(surface, theme.RED, (sx, sy - 16), (cx, cy), width + 3)
            pygame.draw.line(surface, theme.YELLOW, (sx, sy - 16), (cx, cy), width)
            pygame.draw.circle(surface, theme.WHITE, (cx, cy), 6)

    def draw_particles(self, surface):
        for p in self.app.particles:
            x, y = p["x"], p["y"]
            alpha = max(0, min(255, int(255 * p["life"] / p["max_life"])))
            size = max(1, int(3 * p["life"] / p["max_life"] + 1))
            pygame.draw.circle(surface, p["color"], (int(x), int(y)), size)
        for f in self.app.floaters:
            color = tuple(min(255, int(c * min(1.0, f["life"] / f["max_life"] * 2))) for c in f["color"])
            draw_text(surface, f["text"], (int(f["x"]), int(f["y"])), "md", color, center=True)

    def draw_hud(self, surface):
        s = self.g.state
        w = surface.get_width()
        draw_panel(surface, pygame.Rect(8, 8, w - 16, 64))
        draw_text(surface, "SPACE MINER", (20, 12), "lg", theme.CYAN)
        draw_text(surface, f"Credits: {fmt(s['credits'])}", (260, 14), "md", theme.GOLD)
        draw_text(surface, f"Energy: {fmt(s['energy'])}", (460, 14), "md", theme.CYAN)
        draw_text(surface, f"Research: {fmt(s['research_data'])}", (640, 14), "md", theme.MAGENTA)
        draw_text(surface, f"Essence: {fmt(s['essence'])}", (860, 14), "md", (170, 240, 255))
        need = xp_needed_player(s["player_level"])
        draw_text(surface, f"Lv {s['player_level']}", (260, 40), "sm", theme.TEXT)
        draw_bar(surface, pygame.Rect(330, 44, 220, 12), s["player_xp"] / need, theme.GREEN)
        draw_text(surface, f"Company Lv {company_level(s['lifetime_credits'])}", (580, 40), "sm", theme.DIM)
        pinfo = planet(s["selected_planet"])
        draw_text(surface, f"{pinfo['name']} ({galaxy(pinfo['galaxy'])['name']})",
                  (780, 40), "sm", theme.TEXT)
        if s.get("event"):
            ev = s["event"]
            remaining = max(0, int(ev["until"] - self.g.now))
            draw_text(surface, f"{ev['name']}: {ev['desc']}  {remaining}s", (w // 2, 84), "sm",
                      theme.YELLOW, center=True)

    def draw_side_panels(self, surface):
        s = self.g.state
        w, h = surface.get_size()
        pw = w - int(w * 0.72) - 16
        px = w - pw - 12
        # production panel
        prod_rect = pygame.Rect(px, 84, pw, 120)
        draw_panel(surface, prod_rect, "PRODUCTION")
        rates = total_rates(s)
        draw_text(surface, f"{fmt(sum(rates.values()))} ore/s", (px + 12, 118), "lg", theme.GREEN)
        draw_text(surface, f"Energy +{fmt(energy_rate(s))}/s   Research +{fmt(research_rate(s))}/s",
                  (px + 12, 150), "sm", theme.DIM)
        draw_text(surface, f"Fleet {ship_count(s)}/{fleet_cap(s)}   Drones {drone_count(s)}/{drone_cap(s)}   "
                          f"Defense {fmt(defense_power(s))}", (px + 12, 174), "sm", theme.DIM)
        # cargo panel
        cargo_rect = pygame.Rect(px, 212, pw, 200)
        draw_panel(surface, cargo_rect, "CARGO HOLD")
        cap = storage_cap(s)
        y = cargo_rect.y + 32
        owned = [(m, s["resources"].get(m, 0.0)) for m in s["discovered"] if s["resources"].get(m, 0.0) > 0.01]
        for mid, amt in owned[:8]:
            frac = min(1.0, amt / cap)
            color = theme.RARITY[mineral_rarity(mid)]
            draw_text(surface, MINERALS[mid][0][:14], (px + 12, y), "xs", color)
            draw_text(surface, f"{fmt(amt)}", (px + pw - 12, y), "xs", color, right=True)
            draw_bar(surface, pygame.Rect(px + 130, y + 4, pw - 200, 8), frac, color)
            y += 22
        if not owned:
            draw_text(surface, "(empty - mine asteroids!)", (px + 12, y), "xs", theme.DIM)
        # log panel
        log_rect = pygame.Rect(px, 420, pw, h - 420 - 108)
        draw_panel(surface, log_rect, "LOG")
        y = log_rect.y + 32
        for msg in list(self.app.game.feed)[-9:]:
            for ln in self._wrap(msg, pw - 24):
                draw_text(surface, ln, (px + 12, y), "xs", theme.TEXT)
                y += 17
            y += 2

    def _wrap(self, text, width):
        f = theme.font("xs")
        lines, cur = [], ""
        for word in text.split(" "):
            trial = (cur + " " + word).strip()
            if f.size(trial)[0] <= width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
        return lines

    def draw_bottom_bar(self, surface, mouse_pos):
        w, h = surface.get_size()
        rect = pygame.Rect(8, h - 100, w - 16, 92)
        draw_panel(surface, rect)
        labels = [
            ("MARKET (s)", "s"), ("UPGRADES (u)", "u"), ("DRONES (d)", "d"), ("FLEET (f)", "f"),
            ("GALAXY (p)", "p"), ("BUILD (b)", "b"), ("RESEARCH (r)", "r"), ("MISSIONS (j)", "j"),
            ("CREW (e)", "e"), ("AWARDS (a)", "a"), ("STATS (t)", "t"), ("OPTIONS (v)", "v"),
            ("REBIRTH (x)", "x"), ("HELP (?)", "?"),
        ]
        bw, bh = 118, 30
        cols = 7
        self.app.hud_buttons = []
        for i, (label, key) in enumerate(labels):
            col, row = i % cols, i // cols
            b = Button((rect.x + 12 + col * (bw + 8), rect.y + 10 + row * (bh + 8), bw, bh),
                       label, lambda k=key: self.app.open(SCREEN_MAP[k]))
            b.draw(surface, mouse_pos)
            self.app.hud_buttons.append(b)
        od_rect = pygame.Rect(rect.right - 140, rect.y + 10, 128, 30)
        active = self.g.state.get("overdrive_until", 0) > self.g.now
        od = Button(od_rect, "OVERDRIVE!" if active else "OVERDRIVE (o)",
                    self.app.do_overdrive, enabled=not active, style="accent",
                    tooltip="25 energy: double laser & production for 30s")
        od.draw(surface, mouse_pos)
        q = Button((rect.right - 140, rect.y + 48, 128, 30), "SAVE & QUIT", self.app.quit, style="danger")
        q.draw(surface, mouse_pos)

    def draw(self, surface, mouse_pos):
        self.draw_background(surface)
        self.draw_asteroids(surface, mouse_pos)
        self.draw_ship_and_laser(surface)
        self.draw_particles(surface)
        self.draw_hud(surface)
        self.draw_side_panels(surface)
        self.draw_bottom_bar(surface, mouse_pos)
        hint = "Click an asteroid to fire the laser"
        if "auto_miner" in self.g.state["upgrades"]:
            hint += "   [Auto-Turret: ON]"
        draw_text(surface, hint, (16, surface.get_height() - 108), "xs", theme.DIM)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            s = self.g.state
            if event.key == pygame.K_SPACE:
                self.app.do_mine()
            elif pygame.K_1 <= event.key <= pygame.K_6:
                self.g.select_node(event.key - pygame.K_1)
            elif event.key == pygame.K_n:
                self.g.cycle_planet(1)
            elif event.key == pygame.K_o:
                self.app.do_overdrive()
            elif event.key in (pygame.K_q,):
                self.app.quit()
            else:
                for key, cls in SCREEN_MAP.items():
                    if event.unicode and event.unicode.lower() == key:
                        self.app.open(cls)
                        break

    def handle_click(self, pos):
        s = self.g.state
        if self.app.hover_asteroid is not None:
            s["selected_node"] = self.app.hover_asteroid
            self.app.do_mine()
