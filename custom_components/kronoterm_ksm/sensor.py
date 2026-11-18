"""Sensors for Kronoterm KSM."""
from __future__ import annotations

import time

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import KronotermConfigEntry, registers, values
from .const import REG_ELECTRICAL_POWER, REG_FUNCTION
from .coordinator import KronotermCoordinator
from .entity import KronotermEntity

DEVICE_CLASSES = {
    "power": SensorDeviceClass.POWER,
    "pressure": SensorDeviceClass.PRESSURE,
    "energy": SensorDeviceClass.ENERGY,
    "water": SensorDeviceClass.WATER,
    "duration": SensorDeviceClass.DURATION,
}
STATE_CLASSES = {
    "measurement": SensorStateClass.MEASUREMENT,
    "total_increasing": SensorStateClass.TOTAL_INCREASING,
}
TEMP_KINDS = ("temp", "temp0", "troom")

# Pumps for the power estimate: (local number key, register, bitmask)
PUMPS = (
    ("main_pump_power", 2037, 0x1),
    ("loop_1_pump_power", 2044, 0x1),
    ("circulation_pump_power", 2027, 0x1),
    ("dhw_pump_power", 2027, 0x2),
)
MAX_INTEGRATION_GAP = 300  # s; longer gaps (outage) are not integrated


async def async_setup_entry(
    hass: HomeAssistant, entry: KronotermConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [KronotermSensor(coordinator, d) for d in registers.SENSORS]
    entities += [KronotermEnumSensor(coordinator, d) for d in registers.ENUM_SENSORS]
    entities += [
        KronotermAlarmSensor(coordinator, "active_alarms", warnings=False),
        KronotermAlarmSensor(coordinator, "active_warnings", warnings=True),
        KronotermPumpsPowerSensor(coordinator),
    ]
    entities += [KronotermEnergySensor(coordinator, key) for key in ENERGY_FILTERS]
    entities.append(KronotermPumpsEnergySensor(coordinator))
    async_add_entities(entities)


class KronotermSensor(KronotermEntity, SensorEntity):
    """Register value sensor."""

    def __init__(self, coordinator: KronotermCoordinator, desc: dict) -> None:
        super().__init__(coordinator, desc["key"], desc)
        kind = desc["kind"]
        if kind in TEMP_KINDS:
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_suggested_display_precision = 1
        elif kind == "cop":
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_suggested_display_precision = 2
        else:
            self._attr_native_unit_of_measurement = desc.get("unit")
            self._attr_device_class = DEVICE_CLASSES.get(desc.get("dc", ""))
            self._attr_state_class = STATE_CLASSES.get(desc.get("sc", ""))
            if "prec" in desc:
                self._attr_suggested_display_precision = desc["prec"]

    @property
    def native_value(self):
        return values.sensor_value(self._desc, self.regs, self.coordinator.thermal_multiplier)


class KronotermEnumSensor(KronotermEntity, SensorEntity):
    """Text state (current function, schedule state...) with translated states."""

    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, coordinator: KronotermCoordinator, desc: dict) -> None:
        super().__init__(coordinator, desc["key"], desc)
        self._attr_options = list(dict.fromkeys(desc["states"].values()))

    @property
    def native_value(self) -> str | None:
        return values.enum_value(self._desc, self.regs)


class KronotermAlarmSensor(KronotermEntity, SensorEntity):
    """Active alarms / warnings as text, in Home Assistant's language."""

    def __init__(self, coordinator: KronotermCoordinator, key: str, warnings: bool) -> None:
        super().__init__(coordinator, key)
        self._warnings = warnings
        self._attr_icon = "mdi:alert-outline" if warnings else "mdi:alert"

    def _items(self) -> list[str]:
        errs, warns = values.active_alarms(self.regs, values.language(self.hass.config.language))
        return warns if self._warnings else errs

    @property
    def native_value(self) -> str:
        items = self._items()
        if not items:
            return "-"
        text = "; ".join(items)
        return text if len(text) <= 255 else text[:250] + "..."

    @property
    def extra_state_attributes(self) -> dict:
        items = self._items()
        return {"count": len(items), "items": items}


def _function(coordinator: KronotermCoordinator) -> int | None:
    return (coordinator.data or {}).get(REG_FUNCTION)


ENERGY_FILTERS = {
    "energy_heating": lambda f: f == 0,
    "energy_dhw": lambda f: f in (1, 4),
    "energy_other": lambda f: f not in (0, 1, 4),
    "energy_total_calculated": lambda f: True,
}


class _IntegratingSensor(KronotermEntity, RestoreSensor):
    """kWh counter integrated from a power value (left rectangle), survives restarts."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: KronotermCoordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._total = 0.0
        self._last_time: float | None = None
        self._last_power: float | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            try:
                self._total = float(last.native_value or 0)
            except (TypeError, ValueError):
                self._total = 0.0

    def _power(self) -> float | None:
        raise NotImplementedError

    @callback
    def _handle_coordinator_update(self) -> None:
        now = time.monotonic()
        if self._last_time is not None and self._last_power is not None:
            dt = now - self._last_time
            if 0 < dt <= MAX_INTEGRATION_GAP:
                self._total += self._last_power * dt / 3_600_000
        self._last_time = now
        self._last_power = self._power()
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> float:
        return round(self._total, 3)


class KronotermEnergySensor(_IntegratingSensor):
    """Electrical energy split by what the heat pump is doing."""

    def __init__(self, coordinator: KronotermCoordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._filter = ENERGY_FILTERS[key]

    def _power(self) -> float | None:
        regs = self.coordinator.data or {}
        power, function = regs.get(REG_ELECTRICAL_POWER), regs.get(REG_FUNCTION)
        if power is None or function is None:
            return None
        return float(power) if self._filter(function) else 0.0


def pumps_power(coordinator: KronotermCoordinator) -> float | None:
    regs = coordinator.data or {}
    total = 0.0
    for key, address, mask in PUMPS:
        raw = regs.get(address)
        if raw is None:
            return None
        if raw & mask:
            total += coordinator.pump_power.get(key, 0.0)
    return total


class KronotermPumpsEnergySensor(_IntegratingSensor):
    """Estimated energy of the circulation pumps (run time x nameplate power)."""

    _attr_suggested_display_precision = 3

    def __init__(self, coordinator: KronotermCoordinator) -> None:
        super().__init__(coordinator, "energy_pumps")

    def _power(self) -> float | None:
        return pumps_power(self.coordinator)


class KronotermPumpsPowerSensor(KronotermEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator: KronotermCoordinator) -> None:
        super().__init__(coordinator, "pumps_power")

    @property
    def native_value(self) -> float | None:
        return pumps_power(self.coordinator)
