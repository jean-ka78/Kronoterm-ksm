"""Numbers for Kronoterm KSM: setpoints, offsets, curves + local pump powers."""
from __future__ import annotations

from homeassistant.components.number import NumberMode, RestoreNumber, NumberDeviceClass, NumberEntity
from homeassistant.const import UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import KronotermConfigEntry, registers, values
from .coordinator import KronotermCoordinator
from .entity import KronotermEntity

# Local (not on the heat pump) nameplate powers for the pump energy estimate
PUMP_DEFAULTS = {
    "main_pump_power": 45.0,
    "loop_1_pump_power": 25.0,
    "dhw_pump_power": 25.0,
    "circulation_pump_power": 10.0,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: KronotermConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[NumberEntity] = [KronotermNumber(coordinator, d) for d in registers.NUMBERS]
    entities += [KronotermPumpPower(coordinator, key, default) for key, default in PUMP_DEFAULTS.items()]
    async_add_entities(entities)


class KronotermNumber(KronotermEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: KronotermCoordinator, desc: dict) -> None:
        super().__init__(coordinator, desc["key"], desc)
        self._attr_native_min_value = desc["min"]
        self._attr_native_max_value = desc["max"]
        self._attr_native_step = desc["step"]
        unit = desc.get("unit")
        if unit == "°C":
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_device_class = NumberDeviceClass.TEMPERATURE
        else:
            self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self) -> float | None:
        return values.number_value(self._desc, self.regs)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_write(self._desc["address"], values.number_raw(self._desc, value))


class KronotermPumpPower(KronotermEntity, RestoreNumber):
    """Nameplate power of a circulation pump, stored in Home Assistant."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 500
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = NumberDeviceClass.POWER

    def __init__(self, coordinator: KronotermCoordinator, key: str, default: float) -> None:
        super().__init__(coordinator, key)
        self._key = key
        self._value = default
        coordinator.pump_power[key] = default

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_number_data()) is not None and last.native_value is not None:
            self._value = float(last.native_value)
        self.coordinator.pump_power[self._key] = self._value

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> float:
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        self._value = value
        self.coordinator.pump_power[self._key] = value
        self.async_write_ha_state()
