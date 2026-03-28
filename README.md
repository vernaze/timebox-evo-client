# timebox-evo-client

**_This project contains AI-generated code._**

Python library to control Divoom Timebox EVO from macOS.

## Supported devices

- Divoom Timebox EVO (16x16 LED pixel display)

Communicates over Bluetooth Classic RFCOMM. Other Divoom models using the same protocol may work but are untested.

## Requirements

- macOS (IOBluetooth framework required; does not work in Docker or on Linux)
- Python >= 3.9
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync
```

## Finding your device address

The library requires the Bluetooth MAC address of your Timebox EVO. To find it:

1. Open **System Settings > Bluetooth** on macOS
2. Make sure your Timebox EVO is paired and connected
3. Hold **Option** and click the Bluetooth icon in the menu bar
4. Find your Timebox EVO in the list and note the **Address** field (e.g. `XX:XX:XX:XX:XX:XX`)

Alternatively, use the terminal:

```bash
system_profiler SPBluetoothDataType | grep -A 10 "Timebox"
```

## Usage

```python
from timebox import Timebox

tb = Timebox("{device_address}")
tb.connect()

tb.disable_animations()                           # stop auto-play slideshow
tb.set_clock(style=4, color=(0xAA, 0xFF, 0x00))   # digital clock (yellow-green)
tb.set_brightness(1)                               # brightness 0-100
tb.set_volume(0)                                   # volume 0-16
tb.show_image([0xFF0000] * 256)                    # 16x16 custom image (all red)
tb.set_light((0, 0, 0xFF), brightness=50)          # lamp mode
tb.screen_off()                                    # screen off
tb.screen_on(80)                                   # screen on

tb.disconnect()
```

## Protocol

### Connection

| Item      | Value                                        |
| --------- | -------------------------------------------- |
| Protocol  | Bluetooth Classic RFCOMM                     |
| Channel   | 1 (SDP "Serial Port 1")                      |
| macOS API | IOBluetooth (`pyobjc-framework-IOBluetooth`) |

Notes:

- BLE/GATT does not work (pairing shim only)
- `socket.AF_BLUETOOTH` is not available in macOS Python
- Node.js `bluetooth-serial-port` does not support macOS
- Only pyobjc IOBluetooth RFCOMM Sync API is confirmed working
- IOBluetooth is macOS-only and does not work inside Docker containers

### Connection sequence

1. Open RFCOMM directly via `openRFCOMMChannelSync` (does not interrupt active audio connection)
2. On failure: `closeConnection` -> `openConnection` -> retry

### Frame structure

```
[0x01] [len_lo, len_hi, cmd, ...data, csum_lo, csum_hi] [0x02]
```

- Length = cmd(1) + data + checksum(2). Does not include the length field itself
- Checksum = lower 16 bits of the sum of all payload bytes
- No byte masking required (Timebox EVO `escapePayload=False`)

### Commands

| Command              | Byte | Parameters                         |
| -------------------- | ---- | ---------------------------------- |
| Volume               | 0x08 | [0-16]                             |
| Stop playback        | 0x0A | [0x00]                             |
| Disable hot/trending | 0x26 | [0x00] (stops auto-play slideshow) |
| Time format          | 0x2D | [0=12h, 1=24h]                     |
| Disable sleep        | 0x40 | [0x00 x 10] (stops screensaver)    |
| Static image         | 0x44 | header + palette + pixels          |
| View switch          | 0x45 | channel-dependent (see below)      |
| Get state            | 0x46 | []                                 |
| Brightness           | 0x74 | [0-100] (0 = screen off)           |

### View switch (0x45) channels

#### Clock (0x00)

```
[0x00, 24h, style, 0x01, weather, temp, calendar, R, G, B]
```

- style 0-15 selects clock design; style=4 is a simple digital clock

#### Lamp (0x01)

```
[0x01, R, G, B, brightness, 0x00, power, 0x00, 0x00, 0x00]
```

#### Other channels

| Value | Channel                |
| ----- | ---------------------- |
| 0x03  | Effects                |
| 0x04  | Visualizer             |
| 0x05  | Design (favorites)     |
| 0x06  | Stopwatch / scoreboard |

### Image encoding (0x44)

```
Header:  44 00 0A 0A 04 AA 2D 00 00 00 00
Palette: [color_count 1B] [R,G,B] x color_count
Pixels:  bit-packed (bits/px = ceil(log2(color_count)), LSB first)
Frame:   01 [len_lo, len_hi] [header+palette+pixels] [crc_lo, crc_hi] 02
```

### Auto-play animations

The device plays a pixel art slideshow when idle. To stop it:

1. `0x26 [0x00]` — disable hot/trending
2. `0x40 [0x00 x 10]` — disable sleep/screensaver

`tb.disable_animations()` sends both commands.

## References

- [d03n3rfr1tz3/hass-divoom](https://github.com/d03n3rfr1tz3/hass-divoom) — comprehensive Home Assistant integration
- [RomRider/node-divoom-timebox-evo](https://github.com/RomRider/node-divoom-timebox-evo) — protocol specification
- [spezifisch/divo](https://github.com/spezifisch/divo) — image encoding reference
- [MarcG046/timebox protocol](https://github.com/MarcG046/timebox/blob/master/doc/protocol.md) — protocol documentation
