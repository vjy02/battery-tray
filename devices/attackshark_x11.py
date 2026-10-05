import time

import hid
from .base import BatteryDevice, BatteryState
from config import X11_VENDOR_ID, X11_PRODUCT_ID

# Captured frame: 03 07 40 <state> <battery_percent>
#   e.g. 03 07 40 01 61  ->  state=0x01, battery=0x61=97%
#
# Some platforms/backends strip the leading report ID (0x03), so we search
# for the 07 40 marker instead of relying on fixed offsets.
FRAME_MARKER = (0x07, 0x40)
CHARGING_STATE = 0x01  # unconfirmed: log frames plugged in vs. unplugged
READ_TIMEOUT_S = 3.0   # how long to wait for the next battery frame
POLL_INTERVAL_S = 0.05
DEBUG = False          # set True to print every raw report received


def parse_battery_frame(report):
    """Return (state, battery) if the report contains a battery frame, else None."""
    for i in range(len(report) - 3):
        if (report[i], report[i + 1]) == FRAME_MARKER:
            state = report[i + 2]
            battery = report[i + 3]
            if 0 <= battery <= 100:
                return state, battery
    return None


class AttackSharkX11(BatteryDevice):
    name = "Attack Shark X11"

    def __init__(self, path):
        self.path = path

    def battery_state(self):
        device = hid.device()
        try:
            device.open_path(self.path)
            device.set_nonblocking(True)

            deadline = time.monotonic() + READ_TIMEOUT_S
            while time.monotonic() < deadline:
                report = device.read(64)

                # Non-blocking read returns [] when nothing is pending.
                if not report:
                    time.sleep(POLL_INTERVAL_S)
                    continue

                if DEBUG:
                    print("raw:", " ".join(f"{b:02X}" for b in report))

                parsed = parse_battery_frame(report)
                if parsed:
                    state, battery = parsed
                    return BatteryState(
                        self.name,
                        battery,
                        state == CHARGING_STATE,
                        True,
                    )

            return BatteryState(
                self.name,
                connected=True,
                error="X11 battery frame not received yet",
            )
        except Exception as exc:
            return BatteryState(self.name, connected=False, error=str(exc))
        finally:
            try:
                device.close()
            except Exception:
                pass


def find_x11_interfaces():
    return [
        d for d in hid.enumerate()
        if d["vendor_id"] == X11_VENDOR_ID
        and d["product_id"] == X11_PRODUCT_ID
    ]