import math
import threading
import time

import pystray
from PIL import Image, ImageDraw

from ui.icons import GLYPH, GLYPH_OFF, GREY, OUT, S, draw_headset, draw_mouse, draw_ring, has_reading, ring_color

DEVICES = [
    ("Attack Shark X11", "mouse"),
    ("HyperX Cloud III S", "headset"),
]

def render(state, kind):
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    has = has_reading(state)
    pct = state.battery if has else None
    color = ring_color(pct) if has else GREY
    draw_ring(d, pct, color)

    glyph = GLYPH if has else GLYPH_OFF
    if kind == "mouse":
        draw_mouse(d, glyph)
    else:
        draw_headset(d, glyph)

    return img.resize((OUT, OUT), Image.LANCZOS)


class TrayUI:
    def __init__(self, manager):
        self.manager = manager
        self._quit = threading.Event()
        self._notified_low = {}
        self.icons = {}

        for name, kind in DEVICES:
            self.icons[name] = pystray.Icon(
                "battery_" + name.replace(" ", "_"),
                render(None, kind),
                f"{name}: waiting...",
                menu=self._menu(name),
            )

    # ----- text ---------------------------------------------------------

    def _status_text(self, name):
        state = self.manager.states.get(name)
        if state is None:
            return f"{name}: waiting..."
        if has_reading(state):
            return f"{name}: {state.battery}%"
        if not state.connected:
            return f"{name}: not connected"
        return f"{name}: {state.error or 'no data yet'}"

    # ----- menu ---------------------------------------------------------

    def _menu(self, name):
        return pystray.Menu(
            pystray.MenuItem(lambda item: self._status_text(name), None, enabled=False),
            pystray.MenuItem("Refresh now", self._on_refresh),
            pystray.MenuItem("Quit", self._on_quit),
        )

    def _on_refresh(self, icon=None, item=None):
        def work():
            try:
                self.manager.poll()
            finally:
                self.refresh()
        threading.Thread(target=work, daemon=True).start()

    def _on_quit(self, icon=None, item=None):
        self.stop()

    # ----- updating -----------------------------------------------------

    def refresh(self):
        """Redraw every icon from manager.states. Safe to call from any thread."""
        low = self.manager.low_threshold
        for name, kind in DEVICES:
            icon = self.icons[name]
            if not icon.visible:
                continue
            state = self.manager.states.get(name)
            try:
                icon.icon = render(state, kind)
                icon.title = self._status_text(name)     # number shows on hover
                icon.update_menu()
            except Exception as exc:
                print("Tray update error:", exc)
            self._maybe_notify(icon, name, state, low)

    def _maybe_notify(self, icon, name, state, low):
        if not has_reading(state):
            return
        if state.battery <= low:
            if not self._notified_low.get(name):
                self._notified_low[name] = True
                try:
                    icon.notify(f"{name} is at {state.battery}%", "Low battery")
                except Exception:
                    pass
        elif state.battery > low + 5:
            self._notified_low[name] = False

    # ----- lifecycle ----------------------------------------------------

    def run(self):
        """Show all icons and block until Quit is chosen."""
        for icon in self.icons.values():
            icon.run_detached()

        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not all(i.visible for i in self.icons.values()):
            time.sleep(0.1)
        self.refresh()

        self._quit.wait()

    def stop(self):
        for icon in self.icons.values():
            try:
                icon.stop()
            except Exception:
                pass
        self._quit.set()