"""Selects for Kronoterm KSM (modes and programs, translated options)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import KronotermConfigEntry, registers, values
from .coordinator import KronotermCoordinator
from .entity import KronotermEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: KronotermConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(KronotermSelect(coordinator, d) for d in registers.SELECTS)


class KronotermSelect(KronotermEntity, SelectEntity):
    def __init__(self, coordinator: KronotermCoordinator, desc: dict) -> None:
        super().__init__(coordinator, desc["key"], desc)
        self._attr_options = list(desc["map"])

    @property
    def current_option(self) -> str | None:
        return values.select_option(self._desc, self.regs)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_write(self._desc["address"], self._desc["map"][option])
