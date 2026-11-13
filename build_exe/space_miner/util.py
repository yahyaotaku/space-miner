"""Small shared helpers: number formatting, time formatting, colors."""
import math
import os
import sys

SUFFIXES = ["", "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No", "Dc"]


def fmt(n, dec=1):
    """Format a number for display: 999 -> 999, 12_400 -> 12.40K, huge -> 1.23e+25."""
    n = float(n)
    if math.isnan(n) or math.isinf(n):
        return "0"
    if n < 0:
        return "-" + fmt(-n, dec)
    if n < 1:
        return f"{n:.2f}" if n > 0 else "0"
    if n < 1000:
        return f"{n:.0f}" if n >= 100 or n == int(n) else f"{n:.1f}"
    if n >= 10 ** (3 * len(SUFFIXES)):
        return f"{n:.2e}"
    i = 0
    while n >= 1000 and i < len(SUFFIXES) - 1:
        n /= 1000.0
        i += 1
    if n >= 1000:
        return f"{n:.2e}"
    return f"{n:.2f}{SUFFIXES[i]}"


def fmt_time(seconds):
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}h{m:02d}m"
    if m > 0:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def fmt_clock(seconds):
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Colors:
    enabled = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

    def __call__(self, on=True):
        Colors.enabled = on


def _c(code):
    def apply(text):
        if Colors.enabled:
            return f"\033[{code}m{text}\033[0m"
        return text
    return apply


BOLD = _c("1")
DIM = _c("2")
RED = _c("31")
GREEN = _c("32")
YELLOW = _c("33")
BLUE = _c("34")
MAGENTA = _c("35")
CYAN = _c("36")
WHITE = _c("37")
GRAY = _c("90")
BRIGHT_CYAN = _c("96")
BRIGHT_YELLOW = _c("93")
BRIGHT_GREEN = _c("92")
BRIGHT_MAGENTA = _c("95")


def bar(fraction, width=14, fill="=", empty="-"):
    fraction = clamp(float(fraction), 0.0, 1.0)
    filled = int(round(fraction * width))
    return fill * filled + empty * (width - filled)


def beep():
    if Colors.enabled:
        sys.stdout.write("\a")
        sys.stdout.flush()
