"""Timebox EVO protocol encoder."""

from __future__ import annotations

import math
import struct
from collections import OrderedDict


class TimeboxProtocol:
    """Encodes commands into Timebox EVO Bluetooth frames.

    Frame format:
        [0x01] [len_lo, len_hi, cmd, ...data, csum_lo, csum_hi] [0x02]

    Length = cmd(1) + data + checksum(2). Does NOT include the 2 length bytes.
    No byte masking (Timebox EVO escapePayload=False).
    """

    @staticmethod
    def build(cmd: int, data: bytes | list[int]) -> bytes:
        data = bytes(data)
        length = 1 + len(data) + 2
        payload = bytes([length & 0xFF, (length >> 8) & 0xFF, cmd]) + data
        csum = sum(payload) & 0xFFFF
        payload += bytes([csum & 0xFF, (csum >> 8) & 0xFF])
        return bytes([0x01]) + payload + bytes([0x02])

    @staticmethod
    def build_image(colours: list[int]) -> bytes:
        """Build static image frame (16x16 pixels).

        Args:
            colours: Flat list of 256 RGB ints (e.g. 0xFF0000 for red).
        """
        palette_map: dict[int, int] = OrderedDict()
        indices = []
        for c in colours:
            if c not in palette_map:
                palette_map[c] = len(palette_map)
            indices.append(palette_map[c])

        palette = list(palette_map.keys())
        n = len(palette)
        bits = max(1, math.ceil(math.log2(n))) if n > 1 else 1

        img = bytearray([n % 256])
        for c in palette:
            img.extend([(c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF])

        bit_string = ""
        for idx in indices:
            b = format(idx, f"0{bits}b")
            bit_string += b[::-1][:bits]

        i = 0
        while i < len(bit_string):
            chunk = bit_string[i:i + 8].ljust(8, "0")
            img.append(int(chunk[::-1], 2))
            i += 8

        header = bytes([0x44, 0x00, 0x0A, 0x0A, 0x04, 0xAA, 0x2D, 0x00, 0x00, 0x00, 0x00])
        payload = header + bytes(img)
        total_len = 2 + len(payload)
        frame = struct.pack("<H", total_len) + payload
        crc = sum(frame) & 0xFFFF
        frame += bytes([crc & 0xFF, (crc >> 8) & 0xFF])
        return b"\x01" + frame + b"\x02"

    # --- Command builders ---

    @classmethod
    def clock(
        cls,
        style: int = 4,
        format_24h: bool = False,
        weather: bool = False,
        temp: bool = False,
        calendar: bool = False,
        color: tuple[int, int, int] | None = None,
    ) -> bytes:
        """Clock view.

        Args:
            style: 0-15. style=4 is simple digital clock (confirmed on device).
            color: (R, G, B) tuple.
        """
        args = [
            0x00,
            0x01 if format_24h else 0x00,
            style & 0x0F,
            0x01,
            0x01 if weather else 0x00,
            0x01 if temp else 0x00,
            0x01 if calendar else 0x00,
        ]
        if color:
            args.extend([color[0] & 0xFF, color[1] & 0xFF, color[2] & 0xFF])
        return cls.build(0x45, args)

    @classmethod
    def light(
        cls,
        color: tuple[int, int, int] = (0xFF, 0xFF, 0xFF),
        brightness: int = 100,
        power: bool = True,
    ) -> bytes:
        """Lamp/light view."""
        args = [
            0x01,
            color[0] & 0xFF, color[1] & 0xFF, color[2] & 0xFF,
            max(0, min(100, brightness)),
            0x00,
            0x01 if power else 0x00,
            0x00, 0x00, 0x00,
        ]
        return cls.build(0x45, args)

    @classmethod
    def volume(cls, level: int) -> bytes:
        """Volume 0-16."""
        return cls.build(0x08, [max(0, min(16, level))])

    @classmethod
    def brightness(cls, level: int) -> bytes:
        """Brightness 0-100. 0 = screen off."""
        return cls.build(0x74, [max(0, min(100, level))])

    @classmethod
    def set_time_format(cls, format_24h: bool = True) -> bytes:
        """Set 12h/24h display format. Separate from clock view command."""
        return cls.build(0x2D, [0x01 if format_24h else 0x00])

    @classmethod
    def set_time(cls, year: int, month: int, day: int, hour: int, minute: int, second: int) -> bytes:
        """Sync device clock. Timebox EVO command 0x18."""
        return cls.build(0x18, [
            year & 0xFF, (year >> 8) & 0xFF,
            month, day, hour, minute, second,
        ])

    @classmethod
    def disable_animations(cls) -> bytes:
        """Disable hot/trending auto-play and screensaver."""
        return cls.build(0x26, [0x00]) + cls.build(0x40, [0x00] * 10)

    @classmethod
    def get_state(cls) -> bytes:
        """Request current device state."""
        return cls.build(0x46, [])
