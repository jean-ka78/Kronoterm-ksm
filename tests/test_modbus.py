from __future__ import annotations

import asyncio

import pytest

from conftest import modbus
from fake_ksm import FakeKSM


def run(coro):
    return asyncio.run(coro)


def test_crc_known_vector():
    # Read 1 register 0x0000 from slave 1: 01 03 00 00 00 01 -> CRC 84 0A
    assert modbus.rtu_frame(1, bytes.fromhex("0300000001")).hex() == "010300000001840a"


def test_plan_blocks_contiguous_only():
    assert modbus.plan_blocks({1, 2, 3, 5, 6, 10}) == [(1, 3), (5, 2), (10, 1)]
    blocks = modbus.plan_blocks(set(range(0, 130)), max_len=64)
    assert blocks == [(0, 64), (64, 64), (128, 2)]


@pytest.mark.parametrize("protocol", ["rtu_over_tcp", "tcp"])
def test_read_and_write(protocol):
    async def scenario():
        ksm = FakeKSM({2102: 41, 2103: 432, 2104: 0xFFF6}, protocol=protocol)
        await ksm.start()
        client = modbus.KronotermModbusClient("127.0.0.1", ksm.port, 20, protocol, timeout=1)
        try:
            assert await client.read_holding(2102, 3) == [41, 432, 0xFFF6]
            await client.write_register(2103, 450)
            assert ksm.registers[2103] == 450
            assert await client.read_holding(2103, 1) == [450]
        finally:
            await client.close()
            await ksm.stop()

    run(scenario())


@pytest.mark.parametrize("protocol", ["rtu_over_tcp", "tcp"])
def test_exception_response(protocol):
    async def scenario():
        ksm = FakeKSM({2102: 1}, protocol=protocol)
        await ksm.start()
        client = modbus.KronotermModbusClient("127.0.0.1", ksm.port, 20, protocol, timeout=1)
        try:
            with pytest.raises(modbus.ModbusExceptionResponse) as info:
                await client.read_holding(2102, 2)
            assert info.value.code == 2
            # connection still usable afterwards
            assert await client.read_holding(2102, 1) == [1]
        finally:
            await client.close()
            await ksm.stop()

    run(scenario())


def test_timeout_wrong_slave_then_recovers():
    async def scenario():
        ksm = FakeKSM({2102: 7}, slave=20)
        await ksm.start()
        wrong = modbus.KronotermModbusClient("127.0.0.1", ksm.port, 21, timeout=0.3)
        right = modbus.KronotermModbusClient("127.0.0.1", ksm.port, 20, timeout=1)
        try:
            with pytest.raises(modbus.ModbusError):
                await wrong.read_holding(2102, 1)
            assert not wrong.connected  # dropped after error
            assert await right.read_holding(2102, 1) == [7]
        finally:
            await wrong.close()
            await right.close()
            await ksm.stop()

    run(scenario())


def test_crc_error_drops_connection_and_reconnects():
    async def scenario():
        ksm = FakeKSM({2102: 7})
        await ksm.start()
        client = modbus.KronotermModbusClient("127.0.0.1", ksm.port, 20, timeout=0.5)
        try:
            ksm.garbage_before_next = b"\x14"  # one stray byte shifts the frame -> CRC/length error
            with pytest.raises(modbus.ModbusError):
                await client.read_holding(2102, 1)
            assert await client.read_holding(2102, 1) == [7]
        finally:
            await client.close()
            await ksm.stop()

    run(scenario())


def test_connect_refused():
    async def scenario():
        client = modbus.KronotermModbusClient("127.0.0.1", 1, 20, timeout=0.5)
        with pytest.raises(modbus.ModbusError):
            await client.read_holding(2102, 1)

    run(scenario())
