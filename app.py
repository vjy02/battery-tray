import threading
import time
from config import POLL_SECONDS, LOW_BATTERY_PERCENT
from devices.base import BatteryState
from devices.attackshark_x11 import AttackSharkX11, find_x11_interfaces
from devices.hyperx_cloud3s import HyperXCloud3S, find_hyperx_interfaces
from ui.tray import TrayUI

class BatteryManager:
    def __init__(self):
        self.low_threshold=LOW_BATTERY_PERCENT
        self.states={}
        self.hyperx=None   # long-lived: keeps the device open and caches the frame

    def poll(self):
        x=find_x11_interfaces()
        if x:
            # MI_02 contains the receiver's vendor/control collections.
            # Try every interface until the battery frame appears.
            state=None
            for d in x:
                state=AttackSharkX11(d["path"]).battery_state()
                if state.battery is not None:
                    break
        else:
            state=BatteryState("Attack Shark X11",connected=False,
                               error="Device not found")
        self.states["Attack Shark X11"]=state

        h=find_hyperx_interfaces()
        if h:
            path=h[0]["path"]
            if self.hyperx is None or self.hyperx.path!=path:
                if self.hyperx is not None:
                    self.hyperx.stop()
                self.hyperx=HyperXCloud3S(path)
            state=self.hyperx.battery_state()
        else:
            if self.hyperx is not None:
                self.hyperx.stop()
                self.hyperx=None
            state=BatteryState("HyperX Cloud III S",connected=False,
                               error="Vendor interface not found")
        self.states["HyperX Cloud III S"]=state

def main():
    manager=BatteryManager()
    ui=TrayUI(manager)

    def loop():
        while True:
            try:
                manager.poll()
                ui.refresh()
            except Exception as exc:
                print("Polling error:",exc)
            time.sleep(POLL_SECONDS)   # poll first, then sleep

    threading.Thread(target=loop,daemon=True).start()
    ui.run()

if __name__=="__main__":
    main()