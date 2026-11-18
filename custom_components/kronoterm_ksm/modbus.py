"""Minimal asyncio Modbus client for the Kronoterm KSM controller.

No external dependencies (Home Assistant ships pymodbus only for its own
modbus integration, and its API changes between versions).

Supports two framings over a TCP socket:
  * "rtu_over_tcp" - raw Modbus RTU frames (with CRC) tunnelled through a
    transparent RS485<->TCP bridge, e.g. the Pico W bridge firmware.
  * "tcp"          - standard Modbus TCP (MBAP header), for Modbus TCP
    gateways.

Only the functions the KSM needs are implemented:
  0x03 read holding registers, 0x06 write single register.
"""
from __future__ import annotations

import asyncio
import logging
import struct

_LOGGER = logging.getLogger(__name__)

PROTOCOL_RTU_OVER_TCP = "rtu_over_tcp"
PROTOCOL_TCP = "tcp"

MAX_READ = 64  # registers per request


class ModbusError(Exception):
    """Communication failed (timeout, closed connection, bad frame)."""


class ModbusExceptionResponse(ModbusError):
    """The device answered with a Modbus exception code."""

    def __init__(self, function: int, code: int) -> None:
        super().__init__(f"Modbus exception {code} for function {function:#04x}")
        self.function = function
        self.code = code


def crc16(data: bytes) -> int:
    """Modbus RTU CRC-16 (poly 0xA001, init 0xFFFF)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def rtu_frame(slave: int, pdu: bytes) -> bytes:
    body = bytes([slave]) + pdu
    return body + struct.pack("<H", crc16(body))


def _expected_rtu_length(function: int, first_data_byte: int | None) -> int | None:
    """Total RTU response length (incl. slave, function and CRC), or None if unknown yet."""
    if function & 0x80:
        return 5  # slave, func, exception code, crc(2)
    if function == 0x03:
        if first_data_byte is None:
            return None
        return 3 + first_data_byte + 2
    if function in (0x06, 0x10):
        return 8
    return None


class KronotermModbusClient:
    """One connection, one request at a time."""

    def __init__(
        self,
        host: str,
        port: int,
        slave: int,
        protocol: str = PROTOCOL_RTU_OVER_TCP,
        timeout: float = 3.0,
        turnaround: float = 0.03,
    ) -> None:
        self.host = host
        self.port = port
        self.slave = slave
        self.protocol = protocol
        self.timeout = timeout
        self.turnaround = turnaround
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._tid = 0

    # ------------------------------------------------------------ connection
    @property
    def connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def connect(self) -> None:
        if self.connected:
            return
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), self.timeout
            )
        except (TimeoutError, OSError) as err:
            self._reader = self._writer = None
            raise ModbusError(f"cannot connect to {self.host}:{self.port}: {err}") from err
        _LOGGER.debug("Connected to %s:%s", self.host, self.port)

    async def close(self) -> None:
        writer, self._writer, self._reader = self._writer, None, None
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except (OSError, asyncio.CancelledError):  # pragma: no cover - best effort
                pass

    # ------------------------------------------------------------ transport
    async def _read_exactly(self, n: int) -> bytes:
        assert self._reader is not None
        try:
            return await asyncio.wait_for(self._reader.readexactly(n), self.timeout)
        except asyncio.IncompleteReadError as err:
            raise ModbusError("connection closed by bridge") from err
        except TimeoutError as err:
            raise ModbusError("no response from heat pump (timeout)") from err

    async def _transact_rtu(self, pdu: bytes) -> bytes:
        assert self._writer is not None
        self._writer.write(rtu_frame(self.slave, pdu))
        await self._writer.drain()
        head = await self._read_exactly(2)
        slave, function = head[0], head[1]
        length = _expected_rtu_length(function, None)
        if length is None:
            third = await self._read_exactly(1)
            length = _expected_rtu_length(function, third[0])
            if length is None:
                raise ModbusError(f"unexpected function {function:#04x} in response")
            frame = head + third + await self._read_exactly(length - 3)
        else:
            frame = head + await self._read_exactly(length - 2)
        if crc16(frame[:-2]) != struct.unpack("<H", frame[-2:])[0]:
            raise ModbusError("CRC error in response")
        if slave != self.slave:
            raise ModbusError(f"response from slave {slave}, expected {self.slave}")
        return frame[1:-2]  # pdu

    async def _transact_tcp(self, pdu: bytes) -> bytes:
        assert self._writer is not None
        self._tid = (self._tid + 1) & 0xFFFF
        header = struct.pack(">HHHB", self._tid, 0, len(pdu) + 1, self.slave)
        self._writer.write(header + pdu)
        await self._writer.drain()
        while True:
            mbap = await self._read_exactly(7)
            tid, proto, length, _unit = struct.unpack(">HHHB", mbap)
            body = await self._read_exactly(length - 1)
            if proto != 0:
                raise ModbusError("not a Modbus TCP response")
            if tid == self._tid:
                return body
            _LOGGER.debug("Skipping stale Modbus TCP response %s", tid)

    async def _transact(self, pdu: bytes) -> bytes:
        async with self._lock:
            await self.connect()
            try:
                if self.protocol == PROTOCOL_TCP:
                    response = await self._transact_tcp(pdu)
                else:
                    response = await self._transact_rtu(pdu)
            except ModbusError:
                # Drop the connection: leftover bytes would desync the next frame.
                await self.close()
                raise
            except OSError as err:
                await self.close()
                raise ModbusError(str(err)) from err
            if self.protocol != PROTOCOL_TCP and self.turnaround:
                await asyncio.sleep(self.turnaround)
        function = response[0]
        if function & 0x80:
            raise ModbusExceptionResponse(function & 0x7F, response[1])
        if function != pdu[0]:
            raise ModbusError(f"function mismatch {function:#04x} != {pdu[0]:#04x}")
        return response

    # ------------------------------------------------------------ functions
    async def read_holding(self, address: int, count: int) -> list[int]:
        if not 1 <= count <= 125:
            raise ValueError("count must be 1..125")
        response = await self._transact(struct.pack(">BHH", 0x03, address, count))
        byte_count = response[1]
        if byte_count != count * 2 or len(response) != 2 + byte_count:
            raise ModbusError("wrong register count in response")
        return list(struct.unpack(f">{count}H", response[2:]))

    async def write_register(self, address: int, value: int) -> None:
        value &= 0xFFFF
        response = await self._transact(struct.pack(">BHH", 0x06, address, value))
        if response[1:5] != struct.pack(">HH", address, value):
            raise ModbusError("write echo mismatch")


def plan_blocks(addresses: set[int], max_len: int = MAX_READ) -> list[tuple[int, int]]:
    """Group addresses into contiguous (start, count) blocks.

    Gaps are not bridged: the KSM may reject reads of undocumented registers.
    """
    blocks: list[tuple[int, int]] = []
    for addr in sorted(addresses):
        if blocks:
            start, count = blocks[-1]
            if addr == start + count and count < max_len:
                blocks[-1] = (start, count + 1)
                continue
        blocks.append((addr, 1))
    return blocks
