"""GUI theme: colors and fonts for the pygame front-end."""
import pygame

BG = (8, 12, 26)
BG_NEBULA = (30, 18, 60)
PANEL = (16, 24, 46)
PANEL_LIGHT = (24, 36, 66)
BORDER = (58, 78, 128)
BORDER_BRIGHT = (90, 130, 200)
TEXT = (216, 226, 242)
DIM = (125, 138, 165)
CYAN = (80, 220, 255)
GOLD = (255, 208, 92)
GREEN = (118, 240, 158)
RED = (255, 96, 96)
MAGENTA = (226, 120, 255)
YELLOW = (255, 232, 130)
WHITE = (240, 245, 255)

RARITY = {
    "common": (196, 208, 226),
    "uncommon": (118, 240, 158),
    "rare": (80, 220, 255),
    "epic": (226, 120, 255),
    "legendary": (255, 208, 92),
}

FONTS = {}


def init_fonts():
    for name, size in (("xs", 13), ("sm", 15), ("md", 17), ("lg", 22), ("xl", 30), ("title", 44)):
        try:
            FONTS[name] = pygame.font.SysFont("consolas,menlo,dejavusansmono,monospace", size, bold=name in ("lg", "xl", "title"))
        except Exception:
            FONTS[name] = pygame.font.Font(None, size + 4)
    return FONTS


def font(name="md"):
    return FONTS.get(name) or FONTS["md"]
