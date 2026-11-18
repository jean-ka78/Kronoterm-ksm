"""Thermostats (climate) for hot water, buffer tank, heating loops and pool.

Mode mapping (circuit operation register): off = 0 (Off), heat = 1 (Normal),
auto = 2 (Schedule).

Heating loops work in one of two ways, chosen automatically:
  * room thermostat (KT-1/KT-2) connected - current = room temperature,
    target = desired room temperature (17-27 °C);
  * no room thermostat - current = loop temperature, target = calculated
    flow temperature; changing it shifts both points of the loop's heating
    curve by the difference.
The buffer tank always works like the second case (its setpoint comes from
its own curve and cannot be written).
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ATTR_TEMPERATURE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import KronotermConfigEntry, values
from .const import REG_FUNCTION
from .coordinator import KronotermCoordinator
from .entity import KronotermEntity

MODE_TO_RAW = {HVACMode.OFF: 0, HVACMode.HEAT: 1, HVACMode.AUTO: 2}
RAW_TO_MODE = {v: k for k, v in MODE_TO_RAW.items()}
REG_COMPRESSOR = 2317

ROOM_MIN, ROOM_MAX = 17.0, 27.0

CIRCUITS: list[dict] = [
    {"key": "dhw", "kind": "setpoint", "current": 2101, "target": 2022, "min": 10, "max": 60,
     "mode": 2025, "functions": (1, 4)},
    {"key": "buffer", "kind": "curve", "current": 2130, "calculated": 2033, "curve": (2307, 2312),
     "min": 10, "max": 70, "mode": 2034, "functions": (0,), "needs_compressor": True},
    {"key": "loop_1", "kind": "loop", "current": 2129, "calculated": 2127, "room": 2159, "target": 2186,
     "curve": (2308, 2313), "min": 10, "max": 60, "mode": 2041, "pump": 2044},
    {"key": "loop_2", "kind": "loop", "current": 2109, "calculated": 2187, "room": 2160, "target": 2048,
     "curve": (2309, 2314), "min": 10, "max": 60, "mode": 2051, "pump": 2054, "dis": True},
    {"key": "loop_3", "kind": "loop", "current": 2110, "calculated": 2188, "room": 2161, "target": 2058,
     "curve": (2310, 2315), "min": 10, "max": 60, "mode": 2061, "pump": 2064, "dis": True},
    {"key": "loop_4", "kind": "loop", "current": 2111, "calculated": 2189, "room": 2162, "target": 2068,
     "curve": (2311, 2316), "min": 10, "max": 60, "mode": 2071, "pump": 2074, "dis": True},
    {"key": "pool", "kind": "setpoint", "current": 2108, "target": 2078, "min": 20, "max": 35,
     "mode": 2080, "functions": (3,), "dis": True},
]


async def async_setup_entry(
    hass: HomeAssistant, entry: KronotermConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(KronotermClimate(coordinator, c) for c in CIRCUITS)


def _t(regs: dict[int, int], address: int | None, zero_invalid: bool = False) -> float | None:
    return None if address is None else values.temp(regs.get(address), zero_invalid)


def _x10(regs: dict[int, int], address: int) -> float | None:
    raw = regs.get(address)
    return None if raw is None else values.s16(raw) / 10


class KronotermClimate(KronotermEntity, ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.AUTO]
    _attr_target_temperature_step = 0.5
    _attr_precision = 0.1
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: KronotermCoordinator, circuit: dict) -> None:
        super().__init__(coordinator, circuit["key"], circuit)
        self._c = circuit

    # ------------------------------------------------------------ helpers
    @property
    def _room_mode(self) -> bool:
        return self._c["kind"] == "loop" and _t(self.regs, self._c["room"], zero_invalid=True) is not None

    @property
    def _curve_mode(self) -> bool:
        return self._c["kind"] == "curve" or (self._c["kind"] == "loop" and not self._room_mode)

    # ------------------------------------------------------------ state
    @property
    def available(self) -> bool:
        return super().available and _t(self.regs, self._c["current"]) is not None

    @property
    def current_temperature(self) -> float | None:
        if self._room_mode:
            return _t(self.regs, self._c["room"], zero_invalid=True)
        return _t(self.regs, self._c["current"])

    @property
    def target_temperature(self) -> float | None:
        if self._curve_mode:
            return _t(self.regs, self._c["calculated"])
        return _x10(self.regs, self._c["target"])

    @property
    def min_temp(self) -> float:
        return ROOM_MIN if self._room_mode else float(self._c["min"])

    @property
    def max_temp(self) -> float:
        return ROOM_MAX if self._room_mode else float(self._c["max"])

    @property
    def hvac_mode(self) -> HVACMode | None:
        raw = self.regs.get(self._c["mode"])
        return None if raw is None else RAW_TO_MODE.get(raw)

    @property
    def hvac_action(self) -> HVACAction | None:
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        regs = self.regs
        if "pump" in self._c:
            raw = regs.get(self._c["pump"])
            return None if raw is None else (HVACAction.HEATING if raw & 1 else HVACAction.IDLE)
        function = regs.get(REG_FUNCTION)
        if function is None:
            return None
        heating = function in self._c["functions"]
        if heating and self._c.get("needs_compressor"):
            heating = bool(regs.get(REG_COMPRESSOR, 0) & 1)
        return HVACAction.HEATING if heating else HVACAction.IDLE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        regs = self.regs
        attrs: dict[str, Any] = {}
        if "calculated" in self._c:
            attrs["calculated_temperature"] = _t(regs, self._c["calculated"])
        if "curve" in self._c:
            low, high = self._c["curve"]
            attrs["curve_minus_15"] = _x10(regs, low)
            attrs["curve_plus_15"] = _x10(regs, high)
        if self._c["kind"] == "loop":
            attrs["control"] = "room" if self._room_mode else "curve"
            attrs["flow_temperature"] = _t(regs, self._c["current"])
        return attrs

    # ------------------------------------------------------------ control
    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        temperature = float(temperature)
        if not self._curve_mode:
            temperature = min(max(temperature, self.min_temp), self.max_temp)
            await self.coordinator.async_write(self._c["target"], int(round(temperature * 10)))
            return
        # Shift the whole curve so the calculated temperature becomes the requested one
        calculated = _t(self.regs, self._c["calculated"])
        if calculated is None:
            return
        delta = round((temperature - calculated) * 2) / 2
        if delta == 0:
            return
        for address in self._c["curve"]:
            current = _x10(self.regs, address)
            if current is None:
                continue
            new = min(max(current + delta, self._c["min"]), self._c["max"])
            await self.coordinator.async_write(address, int(round(new * 10)))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self.coordinator.async_write(self._c["mode"], MODE_TO_RAW[hvac_mode])

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.AUTO)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)
