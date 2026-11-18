"""Base entity for Kronoterm KSM."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import KronotermCoordinator

CATEGORIES = {"config": EntityCategory.CONFIG, "diagnostic": EntityCategory.DIAGNOSTIC}
PLATFORM_DOMAINS = {"sensor", "binary_sensor", "switch", "select", "number", "button", "climate"}


class KronotermEntity(CoordinatorEntity[KronotermCoordinator]):
    """Entity with a translated name, attached to the heat pump device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: KronotermCoordinator, key: str, desc: dict | None = None) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._desc = desc or {}
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{key}"
        # Fixed, language-independent entity_id (otherwise HA builds it from the name
        # translated into the system language). Domain = platform module (sensor.py -> sensor).
        domain = type(self).__module__.rsplit(".", 1)[-1]
        if domain in PLATFORM_DOMAINS:
            self.entity_id = f"{domain}.kronoterm_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name="Kronoterm",
        )
        if self._desc.get("dis"):
            self._attr_entity_registry_enabled_default = False
        if (cat := self._desc.get("cat")) in CATEGORIES:
            self._attr_entity_category = CATEGORIES[cat]

    @property
    def regs(self) -> dict[int, int]:
        return self.coordinator.data or {}
