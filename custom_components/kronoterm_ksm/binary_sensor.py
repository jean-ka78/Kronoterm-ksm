"""Binary sensors for Kronoterm KSM."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import KronotermConfigEntry, registers, values
from .const import REG_ERROR_STATUS
from .coordinator import KronotermCoordinator
from .entity import KronotermEntity

DEVICE_CLASSES = {
    "running": BinarySensorDeviceClass.RUNNING,
    "heat": BinarySensorDeviceClass.HEAT,
    "problem": BinarySensorDeviceClass.PROBLEM,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: KronotermConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = [KronotermBinarySensor(coordinator, d) for d in registers.BINARY_SENSORS]
    entities.append(KronotermProblemSensor(coordinator))
    async_add_entities(entities)


class KronotermBinarySensor(KronotermEntity, BinarySensorEntity):
    def __init__(self, coordinator: KronotermCoordinator, desc: dict) -> None:
        super().__init__(coordinator, desc["key"], desc)
        self._attr_device_class = DEVICE_CLASSES.get(desc.get("dc", ""))

    @property
    def is_on(self) -> bool | None:
        return values.bit_value(self._desc, self.regs)


class KronotermProblemSensor(KronotermEntity, BinarySensorEntity):
    """On when the controller reports a warning or an alarm."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: KronotermCoordinator) -> None:
        super().__init__(coordinator, "problem")

    @property
    def is_on(self) -> bool | None:
        raw = self.regs.get(REG_ERROR_STATUS)
        if raw is None:
            return None
        return raw in (1, 2)
