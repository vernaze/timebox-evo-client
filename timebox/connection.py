"""macOS IOBluetooth RFCOMM connection for Timebox EVO."""

import logging

import objc

log = logging.getLogger(__name__)
from Foundation import NSDate, NSObject, NSRunLoop
from IOBluetooth import IOBluetoothDevice


class _Delegate(NSObject):
    def init(self):
        self = objc.super(_Delegate, self).init()
        if self is None:
            return None
        self.connected = False
        self.recv_data = bytearray()
        return self

    def rfcommChannelOpenComplete_status_(self, channel, status):
        if status == 0:
            self.connected = True

    def rfcommChannelData_data_length_(self, channel, data, length):
        self.recv_data.extend(bytes(data[:length]))

    def rfcommChannelClosed_(self, channel):
        self.connected = False


class TimeboxConnection:
    """RFCOMM connection to Timebox EVO via macOS IOBluetooth.

    Opens RFCOMM directly without disrupting existing audio connection.
    Falls back to disconnect+reconnect if direct open fails.
    """

    def __init__(self, address: str, channel_id: int = 1):
        self.address = address
        self.channel_id = channel_id
        self.device = None
        self.channel = None
        self._delegate = None

    def connect(self) -> None:
        self.device = IOBluetoothDevice.deviceWithAddressString_(self.address)
        if self.device is None:
            raise ConnectionError(f"Device not found: {self.address}")

        self._delegate = _Delegate.alloc().init()

        log.info("Trying direct RFCOMM...")
        result, channel = self.device.openRFCOMMChannelSync_withChannelID_delegate_(
            None, self.channel_id, self._delegate
        )
        log.info(f"Direct RFCOMM result={result}, channel={channel}")

        if result != 0 or channel is None:
            log.info("Direct failed, reconnecting...")
            self._reconnect()
            log.info("Retrying RFCOMM...")
            result, channel = self.device.openRFCOMMChannelSync_withChannelID_delegate_(
                None, self.channel_id, self._delegate
            )
            log.info(f"Retry result={result}, channel={channel}")
            if result != 0 or channel is None:
                raise ConnectionError(f"RFCOMM open failed: result={result}")

        self.channel = channel
        for _ in range(10):
            self._tick(1.0)
            if self._delegate.connected:
                break

    def _reconnect(self) -> None:
        if self.device.isConnected():
            self.device.closeConnection()
            for _ in range(5):
                self._tick(1.0)
                if not self.device.isConnected():
                    break
        self._tick(2.0)
        self.device.openConnection()
        for _ in range(5):
            self._tick(1.0)
            if self.device.isConnected():
                break

    def send(self, data: bytes) -> None:
        if self.channel is None:
            raise ConnectionError("Not connected")
        buf = bytearray(data)
        self.channel.writeSync_length_(bytes(buf), len(buf))

    def disconnect(self) -> None:
        if self.channel is not None:
            self.channel.closeChannel()
            self.channel = None
        self._tick(1.0)

    def _tick(self, seconds: float) -> None:
        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(seconds)
        )
