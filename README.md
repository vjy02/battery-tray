# Battery Tray

Windows tray battery monitor for:

- Attack Shark X11 (1D57:FA60)
- HyperX Cloud III S Wireless (03F0:02CC)

## Important

The X11 reports battery through a vendor/receiver HID report:
`03 E5 40 <state> <battery_percent>`

The HyperX Cloud III S exposes the vendor HID collection:
`03F0:02CC / FF13:0001`

The HyperX command/response protocol is intentionally isolated until the exact command used by the Cloud III S is confirmed on hardware.

## Install

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Diagnose

Run:

```powershell
python tools\list_devices.py
python tools\inspect_hid.py
```

The inspector passively listens to the X11 and HyperX interfaces and does not send vendor commands.

## Run

```powershell
python app.py
```
