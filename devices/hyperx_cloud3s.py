import threading
import time

import hid
from .base import BatteryDevice, BatteryState
from config import (
    HYPERX_VENDOR_ID,
    HYPERX_PRODUCT_ID,
    HYPERX_USAGE_PAGE,   # 0x01C0 in config.py
    HYPERX_USAGE,        # 0x0001 in config.py
)

# Battery reply:  0C 02 03 01 00 06 4F 0F 76 ...
#   byte 5 = 0x06 type "battery", byte 6 = percent, bytes 7-8 = mV (probably)
REPORT_ID = 0x0C
TYPE_INDEX = 5
BATTERY_TYPE = 0x06
BATTERY_INDEX = 6
VOLTAGE_INDEX = 7

# Captured from NGENUITY: HID SET_REPORT, Output report ID 0x0C, 64 bytes.
BATTERY_REQUEST = bytes([0x0C, 0x02, 0x03, 0x01, 0x00, 0x06]) + bytes(58)
REQUEST_INTERVAL_S = 30

POLL_INTERVAL_S = 0.05
FIRST_FRAME_WAIT_S = 5.0    # how long battery_state() waits when it has nothing yet
STALE_S = 900               # drop a reading older than this
REOPEN_S = 120              # reopen the handle if no battery frame for this long
RETRY_S = 2


def parse_battery_frame(report):
    """Return (percent, millivolts) or None."""
    if len(report) <= VOLTAGE_INDEX + 1:
        return None
    if report[0] != REPORT_ID or report[TYPE_INDEX] != BATTERY_TYPE:
        return None
    percent = report[BATTERY_INDEX]
    if not 0 <= percent <= 100:
        return None
    millivolts = (report[VOLTAGE_INDEX] << 8) | report[VOLTAGE_INDEX + 1]
    return percent, millivolts


def is_power_off_frame(report):
    # Seen once when the headset was turned off: 0D 02 03 00 0C 00
    # (inferred from a single power cycle, not confirmed)
    return (
        len(report) > 5
        and report[0] == 0x0D
        and report[4] == 0x0C
        and report[5] == 0x00
    )


class HyperXCloud3S(BatteryDevice):
    name = "HyperX Cloud III S"

    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        self._latest = None          # (percent, mv, monotonic_time)
        self._error = None
        self._note = None
        self.writer_label = None     # which collection accepted the request
        self.last_raw = None         # hex of the last battery frame (for debugging)
        self._got_frame = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _open_writer(self, reader):
        """Find the collection that accepts output report 0x0C.

        Returns (device, owned, label) or (None, False, None).
        """
        if reader.write(BATTERY_REQUEST) > 0:
            return reader, False, "listening collection"
        for d in hid.enumerate(HYPERX_VENDOR_ID, HYPERX_PRODUCT_ID):
            if d["path"] == self.path:
                continue
            w = hid.device()
            try:
                w.open_path(d["path"])
            except Exception:
                continue
            if w.write(BATTERY_REQUEST) > 0:
                return w, True, f"usage page 0x{d.get('usage_page', 0):04X}"
            w.close()
        return None, False, None

    def _run(self):
        while not self._stop.is_set():
            device = hid.device()
            writer, owned = None, False
            try:
                device.open_path(self.path)
                device.set_nonblocking(True)
                self._error = None
                last_frame = time.monotonic()
                next_request = 0.0

                while not self._stop.is_set():
                    now = time.monotonic()

                    if now >= next_request:
                        if writer is None:
                            writer, owned, self.writer_label = self._open_writer(device)
                            self._note = (
                                None if writer
                                else "No collection accepted the battery request"
                            )
                        elif writer.write(BATTERY_REQUEST) <= 0:
                            if owned:
                                writer.close()
                            writer, owned = None, False
                        next_request = now + REQUEST_INTERVAL_S

                    report = device.read(64)
                    now = time.monotonic()
                    if not report:
                        if now - last_frame > REOPEN_S:
                            break  # reopen the handle and ask again
                        time.sleep(POLL_INTERVAL_S)
                        continue

                    parsed = parse_battery_frame(report)
                    if parsed:
                        with self._lock:
                            self._latest = (parsed[0], parsed[1], now)
                        self.last_raw = " ".join(f"{b:02X}" for b in report[:16])
                        self._got_frame.set()
                        last_frame = now
                    elif is_power_off_frame(report):
                        with self._lock:
                            self._latest = None
                        self._got_frame.clear()
            except Exception as exc:
                self._error = str(exc)
            finally:
                if owned and writer is not None:
                    try:
                        writer.close()
                    except Exception:
                        pass
                try:
                    device.close()
                except Exception:
                    pass
            self._stop.wait(RETRY_S)

    def battery_state(self):
        if self._latest is None and self._error is None:
            self._got_frame.wait(FIRST_FRAME_WAIT_S)

        with self._lock:
            latest = self._latest

        if latest is not None:
            percent, _mv, ts = latest
            if time.monotonic() - ts <= STALE_S:
                # Charging flag not identified yet.
                return BatteryState(self.name, percent, False, True)

        if self._error:
            return BatteryState(self.name, connected=False, error=self._error)
        return BatteryState(
            self.name,
            connected=True,
            error=self._note or "Waiting for a battery frame from the headset",
        )


def find_hyperx_interfaces():
    return [
        d for d in hid.enumerate()
        if (
            d["vendor_id"] == HYPERX_VENDOR_ID
            and d["product_id"] == HYPERX_PRODUCT_ID
            and d.get("usage_page") == HYPERX_USAGE_PAGE
            and d.get("usage") == HYPERX_USAGE
        )
    ]


if __name__ == "__main__":
    # Prints the cached state every 2s for 2 minutes.
    interfaces = find_hyperx_interfaces()
    if not interfaces:
        raise SystemExit("No matching HyperX interface found")
    dev = HyperXCloud3S(interfaces[0]["path"])
    end = time.monotonic() + 120
    while time.monotonic() < end:
        s = dev.battery_state()
        print(time.strftime("%H:%M:%S"), s)
        print("          request accepted by:", dev.writer_label, "| last frame:", dev.last_raw)
        time.sleep(2)
    dev.stop()