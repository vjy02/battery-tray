from dataclasses import dataclass
from typing import Optional

@dataclass
class BatteryState:
    name: str
    battery: Optional[int] = None
    charging: Optional[bool] = None
    connected: bool = False
    error: Optional[str] = None

class BatteryDevice:
    name = "Unknown device"
    def battery_state(self) -> BatteryState:
        raise NotImplementedError
