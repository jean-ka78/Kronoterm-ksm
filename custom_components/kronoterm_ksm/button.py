"""Button: acknowledge the error shown on the controller."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import KronotermConfigEntry
from .const import REG_ERROR_ACK
from .coordinator import KronotermCoordinator
from .entity import KronotermEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: KronotermConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([KronotermAckButton(entry.runtime_data)])


class KronotermAckButton(KronotermEntity, ButtonEntity):
    _attr_icon = "mdi:alert-remove"

    def __init__(self, coordinator: KronotermCoordinator) -> None:
        super().__init__(coordinator, "acknowledge_error")

    async def async_press(self) -> None:
        await self.coordinator.async_write(REG_ERROR_ACK, 0)
