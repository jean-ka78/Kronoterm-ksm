"""Switches for Kronoterm KSM (on/off registers)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import KronotermConfigEntry, registers
from .coordinator import KronotermCoordinator
from .entity import KronotermEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: KronotermConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(KronotermSwitch(coordinator, d) for d in registers.SWITCHES)


class KronotermSwitch(KronotermEntity, SwitchEntity):
    def __init__(self, coordinator: KronotermCoordinator, desc: dict) -> None:
        super().__init__(coordinator, desc["key"], desc)

    @property
    def is_on(self) -> bool | None:
        raw = self.regs.get(self._desc["address"])
        return None if raw is None else bool(raw & 1)

    async def _write(self, on: bool) -> None:
        raw = self.regs.get(self._desc["address"], 0)
        await self.coordinator.async_write(self._desc["address"], (raw | 1) if on else (raw & ~1))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._write(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._write(False)
