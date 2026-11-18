"""Polling coordinator: reads all used KSM registers in contiguous blocks."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import alarms, registers
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_THERMAL_MULTIPLIER,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_THERMAL_MULTIPLIER,
    DOMAIN,
    REG_ELECTRICAL_POWER,
    REG_ERROR_STATUS,
    REG_FUNCTION,
)
from .modbus import KronotermModbusClient, ModbusError, ModbusExceptionResponse, plan_blocks

_LOGGER = logging.getLogger(__name__)

ILLEGAL_ADDRESS = 2


def needed_addresses() -> set[int]:
    """Every register any entity of this integration reads."""
    addrs: set[int] = set()
    for desc in registers.SENSORS:
        addrs.add(desc["address"])
        if desc["kind"] == "u32":
            addrs.add(desc["address"] + 1)
    for group in (
        registers.ENUM_SENSORS,
        registers.BINARY_SENSORS,
        registers.SELECTS,
        registers.SWITCHES,
        registers.NUMBERS,
    ):
        addrs.update(desc["address"] for desc in group)
    addrs.update(alarms.REGISTERS)
    addrs.update((REG_FUNCTION, REG_ERROR_STATUS, REG_ELECTRICAL_POWER))
    return addrs


class KronotermCoordinator(DataUpdateCoordinator[dict[int, int]]):
    """Holds the latest raw register values: {address: uint16}."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: KronotermModbusClient) -> None:
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.client = client
        self._addresses = needed_addresses()
        self._blocks = plan_blocks(self._addresses)
        self._unsupported: set[int] = set()
        # power values (W) of circulation pumps, set by the local number entities
        self.pump_power: dict[str, float] = {}

    @property
    def thermal_multiplier(self) -> float:
        return float(self.config_entry.options.get(CONF_THERMAL_MULTIPLIER, DEFAULT_THERMAL_MULTIPLIER))

    async def _read_block(self, start: int, count: int, data: dict[int, int]) -> None:
        try:
            values = await self.client.read_holding(start, count)
        except ModbusExceptionResponse as err:
            if err.code != ILLEGAL_ADDRESS:
                raise
            # Some controllers lack some registers: find them one by one, once.
            for addr in range(start, start + count):
                try:
                    data[addr] = (await self.client.read_holding(addr, 1))[0]
                except ModbusExceptionResponse as single:
                    if single.code != ILLEGAL_ADDRESS:
                        raise
                    _LOGGER.info("Register %s is not supported by this controller", addr + 1)
                    self._unsupported.add(addr)
            self._blocks = plan_blocks(self._addresses - self._unsupported)
            return
        data.update(zip(range(start, start + count), values, strict=True))

    async def _async_update_data(self) -> dict[int, int]:
        data: dict[int, int] = {}
        errors: list[str] = []
        for start, count in list(self._blocks):
            try:
                await self._read_block(start, count, data)
            except ModbusError as err:
                errors.append(f"{start + 1}-{start + count}: {err}")
                if not self.client.connected:
                    # bridge unreachable or heat pump silent: don't wait for every block
                    break
        if not data:
            raise UpdateFailed(f"Heat pump not reachable: {'; '.join(errors) or 'no data'}")
        if errors:
            _LOGGER.debug("Partial read, missing blocks: %s", errors)
            # keep last known values for blocks that failed this time
            if self.data:
                for addr, value in self.data.items():
                    data.setdefault(addr, value)
        return data

    async def async_write(self, address: int, value: int) -> None:
        """Write one register and refresh the cached value immediately."""
        try:
            await self.client.write_register(address, value)
        except ModbusError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        if self.data is not None:
            new = dict(self.data)
            new[address] = value & 0xFFFF
            self.async_set_updated_data(new)
        await self.async_request_refresh()
