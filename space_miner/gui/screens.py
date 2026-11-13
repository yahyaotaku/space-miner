"""All menu screens for the SPACE MINER GUI."""
import pygame

from ..data_fleet import (SHIPS, DRONES, BUILDINGS, UPGRADES, EMPLOYEES,
                          SHIP_ORDER, DRONE_ORDER, BUILDING_ORDER, UPGRADE_ORDER,
                          EMPLOYEE_ORDER)
from ..data_tech import RESEARCH, RESEARCH_ORDER, BRANCHES, BRANCH_NAMES, ACHIEVEMENTS, MISSIONS
from ..data_world import PLANETS, PLANET_IDS, planet, galaxy, GALAXIES, mineral_name, mineral_rarity
from ..state import (mults, storage_cap, cost_of_ship, cost_of_drone, cost_of_building,
                     cost_of_upgrade, cost_of_employee, drone_count, drone_cap,
                     ship_count, fleet_cap, unlocked_planets, unlocked_galaxies,
                     company_level, defense_power, offline_capacity_hours,
                     offline_efficiency, laser_power, crit_chance, essence_mult,
                     building_level, has_research, ESSENCE_UPGRADES,
                     ESSENCE_UPGRADE_ORDER, cost_of_essence_upgrade, xp_needed_player)
from ..production import planet_rates, total_rates, energy_rate, research_rate
from ..economy import price
from ..prestige import rebirth_preview, can_rebirth
from .. import ui
from ..util import fmt
from . import theme
from .widgets import Button, draw_text, draw_panel, draw_bar, Scroller, draw_tooltip, wrap_text

ROW_H = 36


class Screen:
    title = ""

    def __init__(self, app):
        self.app = app
        self.scroller = Scroller()
        self._tooltip = None

    @property
    def g(self):
        return self.app.game

    def back_rect(self, surface):
        return pygame.Rect(16, surface.get_height() - 44, 110, 32)

    def content_rect(self, surface):
        r = surface.get_rect()
        return pygame.Rect(16, 84, r.w - 32, r.h - 140)

    def widgets(self, mouse_pos):
        btns = [Button(self.back_rect(self.app.surface), "< BACK (Esc)",
                       self.app.pop, tooltip="Return to the mining view")]
        btns += self.extra_widgets(mouse_pos)
        return btns

    def extra_widgets(self, mouse_pos):
        return []

    def draw(self, surface, rect):
        return 0

    def handle_event(self, event):
        pass

    def draw_frame(self, surface, mouse_pos):
        r = surface.get_rect()
        draw_panel(surface, pygame.Rect(8, 8, r.w - 16, 64))
        draw_text(surface, self.title, (24, 24), "xl", theme.CYAN)
        rect = self.content_rect(surface)
        pygame.draw.rect(surface, (6, 9, 20), rect, border_radius=6)
        pygame.draw.rect(surface, theme.BORDER, rect, 1, border_radius=6)
        clip = surface.get_clip()
        surface.set_clip(rect.inflate(-8, -8))
        content_h = self.draw(surface, rect.inflate(-8, -8))
        surface.set_clip(clip)
        self.scroller.clamp(content_h, rect.h - 16)
        pygame.draw.rect(surface, (6, 9, 20), self.back_rect(surface), border_radius=4)
        for b in self.widgets(mouse_pos):
            b.draw(surface, mouse_pos)
        if self._tooltip:
            draw_tooltip(surface, self._tooltip)

    def wheel(self, event, content_h, view_h):
        self.scroller.wheel(event, content_h, view_h)

    def notify(self, msg, sound="buy"):
        self.app.notify(msg, sound)


# ---------------------------------------------------------------- market

class MarketScreen(Screen):
    title = "MARKET"

    def draw(self, surface, rect):
        s = self.g.state
        cap = storage_cap(s)
        y = rect.y - self.scroller.offset
        for mid in s["discovered"]:
            held = s["resources"].get(mid, 0.0)
            p = price(s, mid)
            color = theme.RARITY[mineral_rarity(mid)]
            if rect.collidepoint((rect.x, y)):
                row = pygame.Rect(rect.x, y, rect.w, ROW_H - 4)
                pygame.draw.rect(surface, theme.PANEL, row, border_radius=4)
                draw_text(surface, mineral_name(mid), (rect.x + 10, y + 6), "md", color)
                draw_text(surface, mineral_rarity(mid), (rect.x + 210, y + 7), "sm", theme.DIM)
                draw_text(surface, f"{fmt(held)}", (rect.x + 330, y + 6), "md", theme.TEXT)
                draw_text(surface, f"{fmt(p)} cr", (rect.x + 470, y + 6), "md", theme.TEXT)
                draw_text(surface, f"total {fmt(held * p)}", (rect.x + 640, y + 6), "md", theme.GOLD)
                if held > cap * 0.999:
                    draw_text(surface, "FULL", (rect.x + rect.w - 70, y + 7), "sm", theme.RED)
                draw_text(surface, "click to sell all", (rect.x + rect.w - 260, y + 7), "xs",
                          theme.DIM if held > 0 else (60, 66, 84))
            y += ROW_H
        return y + self.scroller.offset - rect.y + 60

    def widgets(self, mouse_pos):
        btns = super().widgets(mouse_pos)
        s = self.g.state
        rect = self.content_rect(self.app.surface)
        y = rect.bottom - 44
        autosell_unlocked = has_research(s, "market_ai") or "autosell" in s["upgrades"]
        btns.append(Button((rect.x + 8, y, 150, 34), "SELL ENTIRE HOLD", self._sell_all))
        btns.append(Button((rect.x + 170, y, 220, 34),
                           f"AUTO-SELL: {'ON' if s['settings']['autosell'] else 'OFF'}",
                           self._toggle_autosell, enabled=autosell_unlocked,
                           tooltip="" if autosell_unlocked else "Locked: research Market AI or buy the Market AI upgrade"))
        btns.append(Button((rect.x + 400, y, 220, 34),
                           f"THRESHOLD: {s['settings']['autosell_threshold'] * 100:.0f}%",
                           self._cycle_threshold, enabled=autosell_unlocked))
        return btns

    def _sell_all(self):
        gained = self.g.sell_everything()
        self.notify(f"Sold hold for {fmt(gained)} credits." if gained else "Hold is empty.",
                    "buy" if gained else "error")

    def _toggle_autosell(self):
        s = self.g.state
        s["settings"]["autosell"] = not s["settings"]["autosell"]
        self.notify(f"Auto-sell {'enabled' if s['settings']['autosell'] else 'disabled'}.", "buy")

    def _cycle_threshold(self):
        st = self.g.state["settings"]
        st["autosell_threshold"] = 0.5 if st["autosell_threshold"] >= 0.95 else round(st["autosell_threshold"] + 0.1, 2)

    def handle_click(self, pos):
        s = self.g.state
        rect = self.content_rect(self.app.surface)
        y = rect.y - self.scroller.offset
        for mid in s["discovered"]:
            row = pygame.Rect(rect.x, y, rect.w, ROW_H - 4)
            if row.collidepoint(pos):
                gained = self.g.sell_resource(mid)
                self.notify(f"Sold {mineral_name(mid)} for {fmt(gained)} credits." if gained
                            else f"No {mineral_name(mid)} to sell.", "buy" if gained else "error")
                return
            y += ROW_H


# ---------------------------------------------------------------- upgrades

class UpgradesScreen(Screen):
    title = "UPGRADES"

    def draw(self, surface, rect):
        s = self.g.state
        y = rect.y - self.scroller.offset
        for uid in UPGRADE_ORDER:
            u = UPGRADES[uid]
            lvl = s["upgrades"].get(uid, 0)
            maxed = lvl >= u["max"]
            cost = cost_of_upgrade(s, uid)
            if rect.collidepoint((rect.x, y)):
                row = pygame.Rect(rect.x, y, rect.w, ROW_H - 4)
                pygame.draw.rect(surface, theme.PANEL, row, border_radius=4)
                draw_text(surface, u["name"], (rect.x + 10, y + 6), "md", theme.TEXT)
                draw_text(surface, f"Lv {lvl}/{u['max']}", (rect.x + 250, y + 7), "sm", theme.DIM)
                if maxed:
                    draw_text(surface, "MAXED", (rect.x + rect.w - 240, y + 6), "md", theme.GREEN)
                else:
                    ok = s["credits"] >= cost
                    draw_text(surface, f"{fmt(cost)} cr", (rect.x + rect.w - 240, y + 6), "md",
                              theme.GOLD if ok else theme.RED)
                draw_text(surface, u["desc"], (rect.x + 340, y + 7), "xs", theme.DIM)
            y += ROW_H
        return y + self.scroller.offset - rect.y + 40

    def handle_click(self, pos):
        s = self.g.state
        rect = self.content_rect(self.app.surface)
        y = rect.y - self.scroller.offset
        for uid in UPGRADE_ORDER:
            row = pygame.Rect(rect.x, y, rect.w, ROW_H - 4)
            if row.collidepoint(pos):
                ok, msg = self.g.buy_upgrade(uid)
                self.notify(msg if not ok else f"Upgraded {UPGRADES[uid]['name']}!", "buy" if ok else "error")
                return
            y += ROW_H


# ---------------------------------------------------------------- drones

class DronesScreen(Screen):
    title = "DRONE BAY"

    def draw(self, surface, rect):
        s = self.g.state
        y = rect.y - self.scroller.offset
        n = drone_count(s)
        assigned = s["drones"].get("mining", {}).get("planet") or s["selected_planet"]
        draw_text(surface, f"Drones: {n}/{drone_cap(s)} bays   Mining drones assigned to: "
                          f"{planet(assigned)['name']}", (rect.x + 8, y + 4), "sm", theme.CYAN)
        y += ROW_H + 8
        for did in DRONE_ORDER:
            d = DRONES[did]
            entry = s["drones"].get(did, {"count": 0, "level": 1})
            cost = cost_of_drone(s, did)
            if rect.collidepoint((rect.x, y)):
                row = pygame.Rect(rect.x, y, rect.w, ROW_H - 4)
                pygame.draw.rect(surface, theme.PANEL, row, border_radius=4)
                draw_text(surface, d["name"], (rect.x + 10, y + 6), "md", theme.TEXT)
                draw_text(surface, f"x{entry['count']}  Lv {entry['level']}", (rect.x + 250, y + 7), "sm", theme.DIM)
                ok = s["credits"] >= cost and n < drone_cap(s)
                draw_text(surface, f"{fmt(cost)} cr", (rect.x + rect.w - 240, y + 6), "md",
                          theme.GOLD if ok else theme.RED)
                draw_text(surface, d["desc"], (rect.x + 360, y + 7), "xs", theme.DIM)
            y += ROW_H
        return y + self.scroller.offset - rect.y + 60

    def handle_click(self, pos):
        s = self.g.state
        rect = self.content_rect(self.app.surface)
        y = rect.y - self.scroller.offset + ROW_H + 8
        n = drone_count(s)
        for did in DRONE_ORDER:
            row = pygame.Rect(rect.x, y, rect.w, ROW_H - 4)
            if row.collidepoint(pos):
                ok, msg = self.g.buy_drone(did)
                self.notify(msg if not ok else f"Built {DRONES[did]['name']}!", "buy" if ok else "error")
                return
            y += ROW_H

    def extra_widgets(self, mouse_pos):
        rect = self.content_rect(self.app.surface)
        y = rect.bottom - 44
        return [Button((rect.x + 8, y, 320, 34), "REASSIGN MINING DRONES TO NEXT PLANET",
                       self._cycle_planet, style="accent")]

    def _cycle_planet(self):
        pids = unlocked_planets(self.g.state)
        if not pids:
            return
        cur = self.g.state["drones"].get("mining", {}).get("planet") or pids[0]
        nxt = pids[(pids.index(cur) + 1) % len(pids)] if cur in pids else pids[0]
        self.g.assign_drones("mining", nxt)
        self.notify(f"Mining drones reassigned to {planet(nxt)['name']}.", "buy")


# ---------------------------------------------------------------- fleet

class FleetScreen(Screen):
    title = "FLEET COMMAND"

    def draw(self, surface, rect):
        s = self.g.state
        y = rect.y - self.scroller.offset
        draw_text(surface, f"Fleet: {ship_count(s)}/{fleet_cap(s)} ships   Defense: {fmt(defense_power(s))}",
                  (rect.x + 8, y + 4), "sm", theme.CYAN)
        y += ROW_H + 8
        for sid in SHIP_ORDER:
            sh = SHIPS[sid]
            entry = s["ships"].get(sid, {"count": 0, "level": 1, "planet": None})
            locked = s["player_level"] < sh["unlock_level"]
            cost = cost_of_ship(s, sid)
            if rect.collidepoint((rect.x, y)):
                row = pygame.Rect(rect.x, y, rect.w, ROW_H - 4)
                pygame.draw.rect(surface, theme.PANEL, row, border_radius=4)
                color = theme.DIM if locked else theme.TEXT
                draw_text(surface, sh["name"], (rect.x + 10, y + 6), "md", color)
                draw_text(surface, f"x{entry['count']}  Lv {entry['level']}", (rect.x + 260, y + 7), "sm", theme.DIM)
                where = planet(entry["planet"])["name"] if entry.get("planet") else "-"
                draw_text(surface, f"@ {where}", (rect.x + 380, y + 7), "sm", theme.CYAN)
                if locked:
                    draw_text(surface, f"needs player lv {sh['unlock_level']}", (rect.x + rect.w - 230, y + 7), "sm", theme.RED)
                else:
                    ok = s["credits"] >= cost and ship_count(s) < fleet_cap(s)
                    draw_text(surface, f"{fmt(cost)} cr", (rect.x + rect.w - 230, y + 6), "md",
                              theme.GOLD if ok else theme.RED)
                draw_text(surface, sh["desc"], (rect.x + 470, y + 7), "xs", theme.DIM)
            y += ROW_H
        return y + self.scroller.offset - rect.y + 60

    def handle_click(self, pos):
        s = self.g.state
        rect = self.content_rect(self.app.surface)
        y = rect.y - self.scroller.offset + ROW_H + 8
        for sid in SHIP_ORDER:
            row = pygame.Rect(rect.x, y, rect.w, ROW_H - 4)
            if row.collidepoint(pos):
                ok, msg = self.g.buy_ship(sid)
                self.notify(msg if not ok else f"Purchased {SHIPS[sid]['name']}!", "buy" if ok else "error")
                return
            y += ROW_H

    def extra_widgets(self, mouse_pos):
        rect = self.content_rect(self.app.surface)
        y = rect.bottom - 44
        return [Button((rect.x + 8, y, 340, 34), "REASSIGN LAST BOUGHT SHIP TO NEXT PLANET",
                       self._cycle_ship, style="accent")]

    def _cycle_ship(self):
        s = self.g.state
        types = [sid for sid in SHIP_ORDER if s["ships"].get(sid, {}).get("count", 0) > 0]
        if not types:
            self.notify("You own no ships yet.", "error")
            return
        pids = unlocked_planets(s)
        if not pids:
            return
        sid = types[-1]
        cur = s["ships"][sid].get("planet") or pids[0]
        nxt = pids[(pids.index(cur) + 1) % len(pids)] if cur in pids else pids[0]
        self.g.assign_ship(sid, nxt)
        self.notify(f"{SHIPS[sid]['name']} reassigned to {planet(nxt)['name']}.", "buy")


# ---------------------------------------------------------------- galaxy

class GalaxyScreen(Screen):
    title = "GALAXY MAP"

    def draw(self, surface, rect):
        s = self.g.state
        y = rect.y - self.scroller.offset
        for info in GALAXIES:
            gid = info["id"]
            unlocked = gid in unlocked_galaxies(s)
            color = theme.GREEN if unlocked else theme.RED
            draw_text(surface, f"{info['name']}  ({'unlocked' if unlocked else 'locked'})",
                      (rect.x + 8, y + 4), "lg", color)
            y += 30
            if not unlocked:
                draw_text(surface, f"Requires {fmt(info['unlock_credits'])} lifetime credits and player level {info['unlock_level']}",
                          (rect.x + 24, y + 2), "xs", theme.DIM)
                y += 22
            for pid in PLANET_IDS:
                if PLANETS[pid][1] != gid:
                    continue
                pinfo = planet(pid)
                pstate = s["planets"][pid]
                if rect.collidepoint((rect.x, y)):
                    row = pygame.Rect(rect.x + 16, y, rect.w - 16, ROW_H - 6)
                    if pstate["unlocked"]:
                        here = s["selected_planet"] == pid
                        pygame.draw.rect(surface, (24, 46, 60) if here else theme.PANEL, row, border_radius=4)
                        if here:
                            pygame.draw.rect(surface, theme.CYAN, row, 1, border_radius=4)
                        rates = sum(planet_rates(s, pid).values())
                        draw_text(surface, pinfo["name"], (row.x + 10, y + 5), "md",
                                  theme.CYAN if here else theme.TEXT)
                        draw_text(surface, f"dev lv {pstate['dev_level']}   {fmt(rates)} ore/s",
                                  (row.x + 220, y + 6), "sm", theme.DIM)
                        draw_text(surface, ", ".join(m.replace("_", " ").title() for m in pinfo["weights"]),
                                  (row.x + 430, y + 6), "xs", theme.DIM)
                        draw_text(surface, "CLICK TO TRAVEL" if not here else "YOU ARE HERE",
                                  (row.x + row.w - 150, y + 6), "xs", theme.CYAN if not here else theme.GREEN)
                    else:
                        can = s["lifetime_credits"] >= pinfo["unlock_credits"] and s["player_level"] >= pinfo["unlock_level"]
                        pygame.draw.rect(surface, theme.PANEL, row, border_radius=4)
                        draw_text(surface, pinfo["name"], (row.x + 10, y + 5), "md", theme.DIM)
                        req = f"unlock: {fmt(pinfo['unlock_credits'])} cr, player lv {pinfo['unlock_level']}"
                        draw_text(surface, req, (row.x + 220, y + 6), "sm", theme.TEXT if can else theme.DIM)
                        if can:
                            draw_text(surface, "CLICK TO CLAIM", (row.x + row.w - 150, y + 6), "xs", theme.GOLD)
                    self._planet_rows[(rect.x + 16, y, rect.w - 16, ROW_H - 6)] = pid
                y += ROW_H
            y += 10
        return y + self.scroller.offset - rect.y + 20

    def __init__(self, app):
        super().__init__(app)
        self._planet_rows = {}

    def handle_click(self, pos):
        s = self.g.state
        for (rx, ry, rw, rh), pid in self._planet_rows.items():
            if pygame.Rect(rx, ry, rw, rh).collidepoint(pos):
                if s["planets"][pid]["unlocked"]:
                    s["selected_planet"] = pid
                    s["selected_node"] = 0
                    self.notify(f"Now orbiting {planet(pid)['name']}.", "buy")
                else:
                    ok, msg = self.g.unlock_planet(pid)
                    self.notify(msg if not ok else f"NEW WORLD CLAIMED: {planet(pid)['name']}!",
                                "levelup" if ok else "error")
                return


# ---------------------------------------------------------------- buildings

class BuildingsScreen(Screen):
    title = "BUILDINGS"

    def draw(self, surface, rect):
        s = self.g.state
        pid = s["selected_planet"]
        y = rect.y - self.scroller.offset
        draw_text(surface, f"Construction on {planet(pid)['name']}", (rect.x + 8, y + 4), "sm", theme.CYAN)
        y += ROW_H + 4
        for bid in BUILDING_ORDER:
            b = BUILDINGS[bid]
            lvl = building_level(s, pid, bid)
            cost = cost_of_building(s, pid, bid)
            if rect.collidepoint((rect.x, y)):
                row = pygame.Rect(rect.x, y, rect.w, ROW_H - 4)
                pygame.draw.rect(surface, theme.PANEL, row, border_radius=4)
                draw_text(surface, b["name"], (rect.x + 10, y + 6), "md", theme.TEXT)
                draw_text(surface, f"Lv {lvl}", (rect.x + 250, y + 7), "sm", theme.DIM)
                ok = s["credits"] >= cost
                draw_text(surface, f"{fmt(cost)} cr", (rect.x + rect.w - 240, y + 6), "md",
                          theme.GOLD if ok else theme.RED)
                draw_text(surface, b["desc"], (rect.x + 340, y + 7), "xs", theme.DIM)
            y += ROW_H
        return y + self.scroller.offset - rect.y + 40

    def handle_click(self, pos):
        s = self.g.state
        pid = s["selected_planet"]
        rect = self.content_rect(self.app.surface)
        y = rect.y - self.scroller.offset + ROW_H + 4
        for bid in BUILDING_ORDER:
            row = pygame.Rect(rect.x, y, rect.w, ROW_H - 4)
            if row.collidepoint(pos):
                ok, msg = self.g.build(pid, bid)
                self.notify(msg if not ok else f"Built {BUILDINGS[bid]['name']} lv {s['buildings'][f'{pid}:{bid}']}!",
                            "buy" if ok else "error")
                return
            y += ROW_H


# ---------------------------------------------------------------- research

class ResearchScreen(Screen):
    title = "RESEARCH TREE"

    def draw(self, surface, rect):
        s = self.g.state
        y = rect.y - self.scroller.offset
        draw_text(surface, f"Research data: {fmt(s['research_data'])}   Generation: {fmt(research_rate(s))}/s",
                  (rect.x + 8, y + 4), "sm", theme.MAGENTA)
        y += ROW_H + 6
        for branch in BRANCHES:
            draw_text(surface, BRANCH_NAMES[branch], (rect.x + 8, y + 2), "md", theme.CYAN)
            y += 30
            for rid in RESEARCH_ORDER:
                info = RESEARCH[rid]
                if info[0] != branch:
                    continue
                done = rid in s["research"]
                avail = all(p in s["research"] for p in info[4])
                if rect.collidepoint((rect.x, y)):
                    row = pygame.Rect(rect.x + 16, y, rect.w - 16, ROW_H - 6)
                    pygame.draw.rect(surface, (22, 44, 34) if done else theme.PANEL, row, border_radius=4)
                    if done:
                        mark, color = "[x]", theme.GREEN
                    elif avail:
                        mark, color = "[ ]", theme.TEXT
                    else:
                        mark, color = "-", theme.DIM
                    draw_text(surface, f"{mark} {info[2]}", (row.x + 10, y + 5), "md", color)
                    if done:
                        draw_text(surface, info[7], (row.x + 300, y + 6), "xs", theme.GREEN)
                    elif avail:
                        ok = s["research_data"] >= info[3]
                        draw_text(surface, f"{fmt(info[3])} data", (row.x + 300, y + 6), "sm",
                                  theme.MAGENTA if ok else theme.RED)
                        draw_text(surface, info[7], (row.x + 440, y + 6), "xs", theme.DIM)
                    else:
                        missing = ", ".join(RESEARCH[p][2] for p in info[4] if p not in s["research"])
                        draw_text(surface, f"needs: {missing}", (row.x + 300, y + 6), "xs", theme.DIM)
                    if avail and not done:
                        self._clickable[(rect.x + 16, y, rect.w - 16, ROW_H - 6)] = rid
                y += ROW_H - 6
            y += 8
        return y + self.scroller.offset - rect.y + 20

    def __init__(self, app):
        super().__init__(app)
        self._clickable = {}

    def handle_click(self, pos):
        for (rx, ry, rw, rh), rid in self._clickable.items():
            if pygame.Rect(rx, ry, rw, rh).collidepoint(pos):
                ok, msg = self.g.research(rid)
                self.notify(msg if not ok else f"RESEARCH COMPLETE: {RESEARCH[rid][2]}!",
                            "levelup" if ok else "error")
                return


# ---------------------------------------------------------------- missions

class MissionsScreen(Screen):
    title = "MISSIONS"

    def draw(self, surface, rect):
        s = self.g.state
        y = rect.y - self.scroller.offset
        idx = s["mission_index"]
        draw_text(surface, "STORY MISSIONS", (rect.x + 8, y + 2), "md", theme.CYAN)
        y += 30
        for i in range(max(0, idx - 2), min(len(MISSIONS), idx + 10)):
            name, kind, target, rewards = MISSIONS[i]
            val = self.g._objective_value(kind)
            rw = ", ".join(f"{fmt(v)} {k}" for k, v in rewards.items())
            if i < idx:
                draw_text(surface, f"[done] {name}", (rect.x + 16, y + 2), "sm", theme.DIM)
                y += 24
            elif i == idx:
                draw_text(surface, f"> {name}: {ui.MISSION_OBJECTIVE_LABELS[kind].format(fmt(target, 0))}",
                          (rect.x + 16, y + 2), "md", theme.GOLD)
                draw_text(surface, f"Progress: {fmt(min(val, target), 0)}/{fmt(target, 0)}   Rewards: {rw}",
                          (rect.x + 32, y + 24), "sm", theme.TEXT)
                y += 52
            else:
                draw_text(surface, f"[locked] ???", (rect.x + 16, y + 2), "sm", theme.DIM)
                y += 24
        y += 14
        draw_text(surface, "DAILY MISSIONS", (rect.x + 8, y + 2), "md", theme.CYAN)
        y += 30
        for d in s.get("daily", []):
            mark = "[x]" if d["done"] else "[ ]"
            color = theme.GREEN if d["done"] else theme.TEXT
            draw_text(surface, f"{mark} {d['desc']}  ({fmt(min(d['progress'], d['target']), 0)}/{fmt(d['target'], 0)})",
                      (rect.x + 16, y + 2), "sm", color)
            y += 26
        return y + self.scroller.offset - rect.y + 20


# ---------------------------------------------------------------- crew

class CrewScreen(Screen):
    title = "CREW LOUNGE"

    def draw(self, surface, rect):
        s = self.g.state
        y = rect.y - self.scroller.offset
        for eid in EMPLOYEE_ORDER:
            e = EMPLOYEES[eid]
            count = s["employees"].get(eid, 0)
            cost = cost_of_employee(s, eid)
            if rect.collidepoint((rect.x, y)):
                row = pygame.Rect(rect.x, y, rect.w, ROW_H - 4)
                pygame.draw.rect(surface, theme.PANEL, row, border_radius=4)
                draw_text(surface, e["name"], (rect.x + 10, y + 6), "md", theme.TEXT)
                draw_text(surface, f"x{count}", (rect.x + 260, y + 7), "sm", theme.DIM)
                ok = s["credits"] >= cost
                draw_text(surface, f"{fmt(cost)} cr", (rect.x + rect.w - 240, y + 6), "md",
                          theme.GOLD if ok else theme.RED)
                draw_text(surface, e["desc"], (rect.x + 340, y + 7), "xs", theme.DIM)
            y += ROW_H
        return y + self.scroller.offset - rect.y + 40

    def handle_click(self, pos):
        s = self.g.state
        rect = self.content_rect(self.app.surface)
        y = rect.y - self.scroller.offset
        for eid in EMPLOYEE_ORDER:
            row = pygame.Rect(rect.x, y, rect.w, ROW_H - 4)
            if row.collidepoint(pos):
                ok, msg = self.g.hire(eid)
                self.notify(msg if not ok else f"Hired a {EMPLOYEES[eid]['name']}!", "buy" if ok else "error")
                return
            y += ROW_H


# ---------------------------------------------------------------- achievements

class AchievementsScreen(Screen):
    title = "ACHIEVEMENTS"

    def draw(self, surface, rect):
        s = self.g.state
        y = rect.y - self.scroller.offset
        done = len(s["achievements"])
        draw_text(surface, f"{done}/{len(ACHIEVEMENTS)} unlocked", (rect.x + 8, y + 2), "md", theme.GOLD)
        y += 34
        for aid, name, desc, reward, key, value in ACHIEVEMENTS:
            earned = aid in s["achievements"]
            if earned:
                draw_text(surface, f"[x] {name}: {desc}", (rect.x + 16, y + 2), "sm", theme.GREEN)
            else:
                draw_text(surface, f"[ ] ??? - {desc}", (rect.x + 16, y + 2), "sm", theme.DIM)
            y += 26
        return y + self.scroller.offset - rect.y + 20


# ---------------------------------------------------------------- stats

class StatsScreen(Screen):
    title = "STATISTICS"

    def draw(self, surface, rect):
        s = self.g.state
        rates = total_rates(s)
        lines = [
            f"Lifetime credits earned : {fmt(s['lifetime_credits'])}",
            f"Lifetime ore mined      : {fmt(s['ore_mined'])}",
            f"Lifetime ore sold       : {fmt(s['ore_sold'])}",
            f"Asteroids destroyed     : {s['kills']} ({s['ancient_kills']} Ancient)",
            f"Missions completed      : {s['missions_done']}",
            f"Events survived         : {s['events_survived']} (pirates beaten: {s['pirates_defeated']})",
            f"Rebirths                : {s['prestige_count']}   Lifetime essence: {fmt(s['lifetime_essence'])}",
            f"Player level            : {s['player_level']}   Company level: {company_level(s['lifetime_credits'])}",
            f"Laser power             : {fmt(laser_power(s))}   Crit: {crit_chance(s) * 100:.0f}%",
            f"Idle production         : {fmt(sum(rates.values()))} ore/s",
            f"Energy / research rates : {fmt(energy_rate(s))}/s, {fmt(research_rate(s))}/s",
            f"Storage capacity        : {fmt(storage_cap(s))} per resource",
            f"Offline                 : {offline_capacity_hours(s)}h capacity, {offline_efficiency(s) * 100:.0f}% efficiency",
            f"Essence bonus           : x{essence_mult(s):.2f} production & sell prices",
            f"Fleet / drones          : {ship_count(s)}/{fleet_cap(s)}, {drone_count(s)}/{drone_cap(s)}",
            f"Defense power           : {fmt(defense_power(s))}",
        ]
        y = rect.y - self.scroller.offset
        for ln in lines:
            draw_text(surface, ln, (rect.x + 16, y + 2), "sm", theme.TEXT)
            y += 28
        return y + self.scroller.offset - rect.y + 20


# ---------------------------------------------------------------- settings

class SettingsScreen(Screen):
    title = "OPTIONS"

    def __init__(self, app):
        super().__init__(app)
        self.erase_armed = False

    def draw(self, surface, rect):
        return 0

    def extra_widgets(self, mouse_pos):
        s = self.g.state
        st = s["settings"]
        rect = self.content_rect(self.app.surface)
        autosell_unlocked = has_research(s, "market_ai") or "autosell" in s["upgrades"]
        btns = [
            Button((rect.x + 8, rect.y + 12, 420, 36),
                   f"AUTO-SELL SURPLUS: {'ON' if st['autosell'] else 'OFF'}",
                   self._toggle_autosell, enabled=autosell_unlocked,
                   tooltip="" if autosell_unlocked else "Locked: needs Market AI research or upgrade"),
            Button((rect.x + 8, rect.y + 60, 420, 36),
                   f"AUTO-SELL THRESHOLD: {st['autosell_threshold'] * 100:.0f}% of storage",
                   self._cycle_threshold, enabled=autosell_unlocked),
            Button((rect.x + 8, rect.y + 108, 420, 36),
                   f"SOUND EFFECTS: {'ON' if self.app.sfx.enabled else 'OFF'}",
                   self._toggle_sound),
            Button((rect.x + 8, rect.y + 156, 420, 36), "SAVE GAME NOW", self._save, style="accent"),
            Button((rect.x + 8, rect.y + 204, 420, 36),
                   "ERASE SAVE AND RESTART" + (" - CLICK AGAIN TO CONFIRM" if self.erase_armed else ""),
                   self._erase, style="danger"),
            Button((rect.x + 8, rect.y + 252, 420, 36), "QUIT TO DESKTOP", self.app.quit, style="danger"),
        ]
        return btns

    def _toggle_autosell(self):
        s = self.g.state
        s["settings"]["autosell"] = not s["settings"]["autosell"]

    def _cycle_threshold(self):
        st = self.g.state["settings"]
        st["autosell_threshold"] = 0.5 if st["autosell_threshold"] >= 0.95 else round(st["autosell_threshold"] + 0.1, 2)

    def _toggle_sound(self):
        self.app.sfx.enabled = not self.app.sfx.enabled

    def _save(self):
        self.notify("Game saved." if self.g.save() else "Save failed!", "buy")

    def _erase(self):
        if not self.erase_armed:
            self.erase_armed = True
            self.notify("Click again to CONFIRM erasing your save!", "error")
            return
        from ..state import new_state
        self.g.state = new_state(self.g.now)
        self.app.feed_clear()
        self.notify("Save erased. Fresh start, miner.", "prestige")
        self.erase_armed = False


# ---------------------------------------------------------------- rebirth

class RebirthScreen(Screen):
    title = "GALACTIC REBIRTH"

    def __init__(self, app):
        super().__init__(app)
        self.armed = False

    def draw(self, surface, rect):
        s = self.g.state
        lines, gain = rebirth_preview(s)
        y = rect.y - self.scroller.offset
        for i, ln in enumerate(lines):
            color = theme.GOLD if i == 2 and gain else theme.TEXT
            if ln.startswith("  RESET") or ln.startswith("  KEPT"):
                color = theme.CYAN
            draw_text(surface, ln.strip(), (rect.x + 16, y + 2), "sm" if i else "lg", color)
            y += 24
        y += 10
        draw_text(surface, "ESSENCE UPGRADES (permanent)", (rect.x + 16, y + 2), "md", theme.CYAN)
        y += 32
        for i, uid in enumerate(ESSENCE_UPGRADE_ORDER):
            u = ESSENCE_UPGRADES[uid]
            lvl = s["essence_upgrades"].get(uid, 0)
            maxed = lvl >= u["max"]
            cost = cost_of_essence_upgrade(s, uid)
            row = pygame.Rect(rect.x + 16, y, rect.w - 32, ROW_H - 6)
            pygame.draw.rect(surface, theme.PANEL, row, border_radius=4)
            draw_text(surface, u["name"], (row.x + 10, y + 5), "md", theme.TEXT)
            draw_text(surface, f"Lv {lvl}/{u['max']}", (row.x + 240, y + 6), "sm", theme.DIM)
            if maxed:
                draw_text(surface, "MAX", (row.x + row.w - 120, y + 6), "md", theme.GREEN)
            else:
                ok = s["essence"] >= cost
                draw_text(surface, f"{cost} essence", (row.x + row.w - 160, y + 6), "sm",
                          theme.MAGENTA if ok else theme.RED)
            draw_text(surface, u["desc"], (row.x + 330, y + 6), "xs", theme.DIM)
            if not maxed:
                self._upg_rows[(row.x, row.y, row.w, row.h)] = uid
            y += ROW_H - 6
        return y + self.scroller.offset - rect.y + 60

    def __init__(self, app):
        super().__init__(app)
        self._upg_rows = {}

    def extra_widgets(self, mouse_pos):
        rect = self.content_rect(self.app.surface)
        if not can_rebirth(self.g.state):
            return []
        label = "CONFIRM GALACTIC REBIRTH" if self.armed else "INITIATE GALACTIC REBIRTH"
        return [Button((rect.x + 8, rect.bottom - 44, 340, 36), label, self._rebirth, style="gold")]

    def _rebirth(self):
        if not self.armed:
            self.armed = True
            self.notify("Click CONFIRM again to reset your run!", "error")
            return
        gain = self.g.do_rebirth()
        self.notify(f"The stars realign. +{gain} Stellar Essence!", "prestige")
        self.app.pop()

    def handle_click(self, pos):
        s = self.g.state
        for (rx, ry, rw, rh), uid in self._upg_rows.items():
            if pygame.Rect(rx, ry, rw, rh).collidepoint(pos):
                ok, msg = self.g.buy_essence_upgrade(uid)
                self.notify(msg if not ok else f"{ESSENCE_UPGRADES[uid]['name']} upgraded!", "buy" if ok else "error")
                return


# ---------------------------------------------------------------- help

HELP_TEXT = [
    ("HOW TO PLAY", theme.CYAN),
    ("Click asteroids to fire your mining laser. Destroyed asteroids drop minerals.", theme.TEXT),
    ("Sell minerals in the MARKET for credits, then buy UPGRADES (laser power first).", theme.TEXT),
    ("Buy MINING DRONES and SHIPS - they mine automatically, even while the game is closed.", theme.TEXT),
    ("BUILD structures on planets: stations boost production, labs generate research data.", theme.TEXT),
    ("Spend research data in the RESEARCH TREE for powerful permanent multipliers.", theme.TEXT),
    ("Unlock new planets in the GALAXY MAP for rarer, pricier minerals.", theme.TEXT),
    ("Follow MISSIONS - they guide progression and pay well.", theme.TEXT),
    ("", theme.TEXT),
    ("TIPS", theme.CYAN),
    ("Storage caps production. Sell often, or research Market AI for auto-sell.", theme.TEXT),
    ("Ancient asteroids (rare, gold shimmer) hold the rarest minerals and research data.", theme.TEXT),
    ("Pirates attack during events. Defender ships and Guardian drones protect your cargo.", theme.TEXT),
    ("Overdrive (O) doubles everything for 30 seconds using energy.", theme.TEXT),
    ("At 1B lifetime credits, perform a Galactic Rebirth (X) for permanent Stellar Essence power.", theme.TEXT),
    ("", theme.TEXT),
    ("KEYBOARD: SPACE mine | 1-6 target | N next planet | O overdrive | ESC back", theme.DIM),
]


class HelpScreen(Screen):
    title = "HELP"

    def draw(self, surface, rect):
        y = rect.y - self.scroller.offset
        for text, color in HELP_TEXT:
            draw_text(surface, text, (rect.x + 16, y + 2), "md", color)
            y += 30
        return y + self.scroller.offset - rect.y + 20
