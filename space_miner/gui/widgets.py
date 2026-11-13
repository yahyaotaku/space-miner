"""Immediate-mode-ish widget toolkit: buttons, panels, bars, text."""
import pygame

from . import theme


def draw_text(surface, text, pos, size="md", color=theme.TEXT, bold=False, right=False, center=False):
    f = theme.font(size)
    img = f.render(str(text), True, color)
    rect = img.get_rect()
    if right:
        rect.topright = pos
    elif center:
        rect.center = pos
    else:
        rect.topleft = pos
    surface.blit(img, rect)
    return rect


def wrap_text(text, size, max_width):
    f = theme.font(size)
    lines = []
    for raw in text.split("\n"):
        cur = ""
        for word in raw.split(" "):
            trial = (cur + " " + word).strip()
            if f.size(trial)[0] <= max_width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def draw_panel(surface, rect, title=None, light=False):
    pygame.draw.rect(surface, theme.PANEL_LIGHT if light else theme.PANEL, rect, border_radius=6)
    pygame.draw.rect(surface, theme.BORDER, rect, 1, border_radius=6)
    if title:
        pygame.draw.rect(surface, theme.BORDER, (rect.x, rect.y, rect.w, 26), border_radius=6)
        pygame.draw.rect(surface, theme.BORDER, (rect.x, rect.y + 20, rect.w, 6))
        draw_text(surface, title, (rect.x + 10, rect.y + 4), "sm", theme.CYAN)


def draw_bar(surface, rect, frac, color=theme.CYAN, bg=(30, 40, 66)):
    frac = max(0.0, min(1.0, frac))
    pygame.draw.rect(surface, bg, rect, border_radius=3)
    if frac > 0:
        inner = rect.copy()
        inner.w = max(2, int(rect.w * frac))
        pygame.draw.rect(surface, color, inner, border_radius=3)
    pygame.draw.rect(surface, theme.BORDER, rect, 1, border_radius=3)


class Button:
    def __init__(self, rect, label, cb=None, enabled=True, style="normal",
                 size="sm", tooltip=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.cb = cb
        self.enabled = enabled
        self.style = style
        self.size = size
        self.tooltip = tooltip

    def draw(self, surface, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos) if mouse_pos else False
        if not self.enabled:
            base = (34, 42, 60)
            border = theme.BORDER
            txt = theme.DIM
        elif self.style == "danger":
            base = (90, 34, 40) if hovered else (70, 26, 32)
            border = theme.RED
            txt = theme.RED
        elif self.style == "accent":
            base = (26, 74, 96) if hovered else (20, 56, 74)
            border = theme.CYAN
            txt = theme.CYAN
        elif self.style == "gold":
            base = (96, 76, 26) if hovered else (74, 58, 20)
            border = theme.GOLD
            txt = theme.GOLD
        else:
            base = (34, 52, 92) if hovered else (26, 40, 72)
            border = theme.BORDER_BRIGHT if hovered else theme.BORDER
            txt = theme.TEXT
        pygame.draw.rect(surface, base, self.rect, border_radius=4)
        pygame.draw.rect(surface, border, self.rect, 1, border_radius=4)
        draw_text(surface, self.label, self.rect.center, self.size, txt, center=True)

    def clicked(self, pos):
        return self.enabled and self.cb and self.rect.collidepoint(pos)


class Tooltip:
    def __init__(self, text, pos):
        self.text = text
        self.pos = pos


def draw_tooltip(surface, tooltip):
    lines = wrap_text(tooltip.text, "xs", 260)
    w = max(theme.font("xs").size(ln)[0] for ln in lines) + 14
    h = 18 * len(lines) + 10
    x, y = tooltip.pos[0] + 14, tooltip.pos[1] + 16
    rect = pygame.Rect(x, y, w, h)
    rect.clamp_ip(surface.get_rect())
    pygame.draw.rect(surface, (10, 14, 28), rect, border_radius=4)
    pygame.draw.rect(surface, theme.BORDER_BRIGHT, rect, 1, border_radius=4)
    for i, ln in enumerate(lines):
        draw_text(surface, ln, (rect.x + 7, rect.y + 5 + i * 18), "xs", theme.TEXT)


class Scroller:
    """Vertical scroll offset with wheel support and clamping."""

    def __init__(self):
        self.offset = 0

    def wheel(self, event, content_height, viewport_height):
        if event.button == 4:
            self.offset -= 40
        elif event.button == 5:
            self.offset += 40
        self.clamp(content_height, viewport_height)

    def clamp(self, content_height, viewport_height):
        self.offset = max(0, min(self.offset, max(0, content_height - viewport_height)))
