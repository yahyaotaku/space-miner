"""Sound effects for the GUI: tiny synthesized beeps, no audio files needed."""
import array
import math

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False


class Sfx:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.ok = False
        self._cache = {}
        if not (HAS_PYGAME and enabled):
            return
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.ok = True
        except Exception:
            self.ok = False

    def _tone(self, freq, ms, volume=0.35, decay=True):
        rate = 22050
        n = int(rate * ms / 1000)
        buf = array.array("h")
        for i in range(n):
            t = i / rate
            amp = volume * (1.0 - i / n) if decay else volume
            buf.append(int(amp * 32767 * math.sin(2 * math.pi * freq * t)))
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def play(self, name):
        if not (self.ok and self.enabled):
            return
        try:
            if name not in self._cache:
                table = {
                    "mine": (180, 60, 0.18),
                    "destroy": (90, 220, 0.4),
                    "crit": (520, 140, 0.4),
                    "buy": (440, 90, 0.3),
                    "error": (140, 160, 0.3),
                    "levelup": (660, 200, 0.35),
                    "event": (330, 260, 0.3),
                    "prestige": (220, 500, 0.4),
                }
                self._cache[name] = self._tone(*table[name])
            self._cache[name].play()
        except Exception:
            self.ok = False

    def shutdown(self):
        if self.ok:
            try:
                pygame.mixer.quit()
            except Exception:
                pass
