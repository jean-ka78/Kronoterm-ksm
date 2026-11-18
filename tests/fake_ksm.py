"""A fake Kronoterm KSM reachable over TCP, for tests.

Speaks either RTU-over-TCP (like the Pico W bridge) or Modbus TCP.
Registers not in `registers` answer with exception 2 (illegal address).
"""
from __future__ import annotations

import asyncio
import struct

from conftest import modbus


class FakeKSM:
    def __init__(self, registers: dict[int, int], slave: int = 20, protocol: str = "rtu_over_tcp") -> None:
        self.registers = dict(registers)
        self.slave = slave
        self.protocol = protocol
        self.requests: list[tuple[int, int, int]] = []  # (function, address, count/value)
        self.server: asyncio.base_events.Server | None = None
        self.port = 0
        self.garbage_before_next = b""

    async def start(self) -> None:
        self.server = await asyncio.start_server(self._client, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    def _handle_pdu(self, pdu: bytes) -> bytes:
        function = pdu[0]
        if function == 0x03:
            address, count = struct.unpack(">HH", pdu[1:5])
            self.requests.append((function, address, count))
            regs = [self.registers.get(a) for a in range(address, address + count)]
            if any(r is None for r in regs):
                return bytes([0x83, 0x02])
            return bytes([0x03, count * 2]) + struct.pack(f">{count}H", *regs)
        if function == 0x06:
            address, value = struct.unpack(">HH", pdu[1:5])
            self.requests.append((function, address, value))
            if address not in self.registers:
                return bytes([0x86, 0x02])
            self.registers[address] = value
            return pdu[:5]
        return bytes([function | 0x80, 0x01])

    async def _client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                if self.protocol == "tcp":
                    header = await reader.readexactly(7)
                    tid, _proto, length, unit = struct.unpack(">HHHB", header)
                    pdu = await reader.readexactly(length - 1)
                    resp = self._handle_pdu(pdu)
                    writer.write(struct.pack(">HHHB", tid, 0, len(resp) + 1, unit) + resp)
                else:
                    frame = await reader.readexactly(8)  # all our requests are 8 bytes
                    assert modbus.crc16(frame[:-2]) == struct.unpack("<H", frame[-2:])[0]
                    if frame[0] != self.slave:
                        continue  # other slave: silence
                    resp = self._handle_pdu(frame[1:-2])
                    writer.write(self.garbage_before_next + modbus.rtu_frame(self.slave, resp))
                    self.garbage_before_next = b""
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        finally:
            writer.close()
