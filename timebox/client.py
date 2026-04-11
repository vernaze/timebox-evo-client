"""High-level Timebox EVO client."""

from __future__ import annotations

import time
from datetime import datetime

from .connection import TimeboxConnection
from .protocol import TimeboxProtocol as P


class Timebox:
    """High-level Timebox EVO controller for macOS.

    Example::

        tb = Timebox("{device_id}")
        tb.connect()
        tb.disable_animations()
        tb.set_clock(style=4, color=(0xAA, 0xFF, 0x00))
        tb.set_brightness(1)
        tb.disconnect()
    """

    def __init__(self, address: str, channel_id: int = 1):
        self._conn = TimeboxConnection(address, channel_id)

    def connect(self) -> None:
        self._conn.connect()

    def disconnect(self) -> None:
        self._conn.disconnect()

    def send(self, data: bytes, delay: float = 0.3) -> None:
        self._conn.send(data)
        if delay:
            self._conn._tick(delay)

    # --- Display ---

    def set_clock(
        self,
        style: int = 4,
        format_24h: bool = False,
        weather: bool = False,
        temp: bool = False,
        calendar: bool = False,
        color: tuple[int, int, int] | None = None,
    ) -> None:
        """Switch to clock view. style=4 is simple digital (device confirmed)."""
        self.send(P.clock(style, format_24h, weather, temp, calendar, color))

    def set_light(
        self,
        color: tuple[int, int, int] = (0xFF, 0xFF, 0xFF),
        brightness: int = 100,
        power: bool = True,
    ) -> None:
        self.send(P.light(color, brightness, power))

    def show_image(self, colours: list[int]) -> None:
        """Display 16x16 pixel art. colours: 256-element list of RGB ints."""
        self.send(P.build_image(colours), delay=0.5)

    def screen_off(self) -> None:
        self.send(P.brightness(0))

    def screen_on(self, level: int = 80) -> None:
        self.send(P.brightness(level))

    # --- Audio ---

    def set_volume(self, level: int) -> None:
        """Volume 0-16."""
        self.send(P.volume(level))

    # --- Brightness ---

    def set_brightness(self, level: int) -> None:
        """Brightness 0-100."""
        self.send(P.brightness(level))

    # --- Misc ---

    def sync_time(self) -> None:
        """Sync device clock to host system time and set 24h format."""
        now = datetime.now()
        self.send(P.set_time(now.year, now.month, now.day, now.hour, now.minute, now.second))
        self.send(P.set_time_format(True))

    def set_time_format(self, format_24h: bool = True) -> None:
        """Set 12h/24h display format."""
        self.send(P.set_time_format(format_24h))

    def disable_animations(self) -> None:
        """Disable hot/trending auto-play and screensaver."""
        self.send(P.disable_animations(), delay=0.5)
