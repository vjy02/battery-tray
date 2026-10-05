import math

OUT = 64         
SS = 4            
S = OUT * SS

DISC = (26, 26, 30, 255)        
TRACK = (66, 66, 74, 255)        
GLYPH = (240, 240, 244, 255)
GLYPH_OFF = (125, 125, 132, 255)
GREY = (110, 110, 118, 255)

RED = (225, 60, 55)
YELLOW = (245, 200, 45)
GREEN = (60, 200, 95)
RING_WIDTH = 5.5   

def ring_color(pct):
    """Smooth red (0%) -> yellow (50%) -> green (100%)."""
    pct = max(0, min(100, pct))
    if pct <= 50:
        a, b, t = RED, YELLOW, pct / 50
    else:
        a, b, t = YELLOW, GREEN, (pct - 50) / 50
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)


def _sc(*values):
    return [v * SS for v in values]


def has_reading(state):
    return state is not None and state.connected and state.battery is not None


def draw_ring(d, pct, color):
    box = [0, 0, S - 1, S - 1]                
    width = int(RING_WIDTH * SS)
    d.ellipse(box, fill=DISC)
    d.ellipse(box, outline=TRACK, width=width)
    if pct is None or pct <= 0:
        return
    if pct >= 100:
        d.ellipse(box, outline=color, width=width)
        return

    end = -90 + 360 * pct / 100         
    d.arc(box, -90, end, fill=color, width=width)

    cap = RING_WIDTH / 2
    r_mid = 32 - cap
    for angle in (-90, end):
        a = math.radians(angle)
        cx = 32 + r_mid * math.cos(a)
        cy = 32 + r_mid * math.sin(a)
        d.ellipse(_sc(cx - cap, cy - cap, cx + cap, cy + cap), fill=color)


def draw_mouse(d, col):
    d.rounded_rectangle(_sc(21, 12.5, 43, 51.5), radius=int(11 * SS), fill=col)
    d.line(_sc(21, 27.5, 43, 27.5), fill=DISC, width=int(1.8 * SS))                     # button split
    d.rounded_rectangle(_sc(30, 16.5, 34, 24.5), radius=int(2 * SS), fill=DISC)          # scroll wheel


def draw_headset(d, col):
    cy = 34.25                                                                           # band centre
    d.arc(_sc(13.5, cy - 18.5, 50.5, cy + 18.5), 180, 360, fill=col, width=int(5 * SS))   # headband
    d.rounded_rectangle(_sc(13.5, cy, 21.5, cy + 14), radius=int(4 * SS), fill=col)       # left cup
    d.rounded_rectangle(_sc(42.5, cy, 50.5, cy + 14), radius=int(4 * SS), fill=col)       # right cup