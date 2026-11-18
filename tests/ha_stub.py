"""Very small stand-ins for the Home Assistant classes the integration uses.

They only exist to execute the integration's own code in tests without a
Home Assistant installation. They do not check HA's real API.
"""
from __future__ import annotations

import enum
import sys
import types
from typing import Any, Generic, TypeVar

T = TypeVar("T")


def _mod(name: str, **attrs: Any) -> types.ModuleType:
    module = sys.modules.get(name) or types.ModuleType(name)
    module.__dict__.update(attrs)
    sys.modules[name] = module
    return module


class _Entity:
    hass: Any = None
    _attr_translation_key = None
    _attr_unique_id = None

    def async_write_ha_state(self) -> None:
        self._written = getattr(self, "_written", 0) + 1

    async def async_added_to_hass(self) -> None:
        return None


class CoordinatorEntity(_Entity, Generic[T]):
    def __init__(self, coordinator: Any) -> None:
        self.coordinator = coordinator

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class UpdateFailed(Exception):
    pass


class DataUpdateCoordinator(Generic[T]):
    def __init__(self, hass, logger, *, config_entry=None, name=None, update_interval=None):
        self.hass = hass
        self.config_entry = config_entry
        self.update_interval = update_interval
        self.data = None
        self.last_update_success = True
        self.listeners: list = []

    async def async_refresh(self) -> None:
        try:
            self.data = await self._async_update_data()
            self.last_update_success = True
        except UpdateFailed:
            self.last_update_success = False

    async def async_config_entry_first_refresh(self) -> None:
        await self.async_refresh()

    def async_set_updated_data(self, data) -> None:
        self.data = data

    async def async_request_refresh(self) -> None:
        await self.async_refresh()


class HomeAssistantError(Exception):
    def __init__(self, *args, translation_domain=None, translation_key=None, translation_placeholders=None):
        super().__init__(*args or (translation_key,))
        self.translation_key = translation_key


class _StrEnum(str, enum.Enum):
    pass


Platform = _StrEnum("Platform", {n.upper(): n for n in ("binary_sensor", "button", "climate", "number", "select", "sensor", "switch")})
SensorDeviceClass = _StrEnum("SensorDeviceClass", {n.upper(): n for n in ("temperature", "power", "pressure", "energy", "water", "duration", "enum")})
SensorStateClass = _StrEnum("SensorStateClass", {n.upper(): n for n in ("measurement", "total_increasing")})
BinarySensorDeviceClass = _StrEnum("BinarySensorDeviceClass", {n.upper(): n for n in ("running", "heat", "problem")})
NumberDeviceClass = _StrEnum("NumberDeviceClass", {n.upper(): n for n in ("temperature", "power")})
NumberMode = _StrEnum("NumberMode", {"BOX": "box"})
EntityCategory = _StrEnum("EntityCategory", {"CONFIG": "config", "DIAGNOSTIC": "diagnostic"})
HVACMode = _StrEnum("HVACMode", {"OFF": "off", "HEAT": "heat", "AUTO": "auto"})
HVACAction = _StrEnum("HVACAction", {"OFF": "off", "HEATING": "heating", "IDLE": "idle"})


class ClimateEntityFeature(enum.IntFlag):
    TARGET_TEMPERATURE = 1
    TURN_OFF = 128
    TURN_ON = 256


class _Last:
    def __init__(self, value):
        self.native_value = value


class RestoreSensor(_Entity):
    restored = None

    async def async_get_last_sensor_data(self):
        return None if self.restored is None else _Last(self.restored)


class RestoreNumber(_Entity):
    restored = None

    async def async_get_last_number_data(self):
        return None if self.restored is None else _Last(self.restored)


class ConfigEntry(Generic[T]):
    def __init__(self, data, options=None, unique_id="uid", entry_id="eid"):
        self.data = data
        self.options = options or {}
        self.unique_id = unique_id
        self.entry_id = entry_id
        self.runtime_data = None

    def async_on_unload(self, func):
        return func

    def add_update_listener(self, func):
        return func


class ConfigFlow:
    def __init_subclass__(cls, **kwargs):
        return super().__init_subclass__()


class OptionsFlow:
    pass


def install() -> None:
    _mod("homeassistant")
    _mod("homeassistant.const", CONF_HOST="host", CONF_PORT="port", Platform=Platform,
         UnitOfTemperature=types.SimpleNamespace(CELSIUS="°C"), UnitOfPower=types.SimpleNamespace(WATT="W"),
         UnitOfEnergy=types.SimpleNamespace(KILO_WATT_HOUR="kWh"))
    _mod("homeassistant.core", HomeAssistant=object, callback=lambda f: f)
    _mod("homeassistant.exceptions", HomeAssistantError=HomeAssistantError)
    _mod("homeassistant.config_entries", ConfigEntry=ConfigEntry, ConfigFlow=ConfigFlow, OptionsFlow=OptionsFlow,
         ConfigFlowResult=dict)
    _mod("homeassistant.helpers")
    _mod("homeassistant.helpers.update_coordinator", DataUpdateCoordinator=DataUpdateCoordinator,
         UpdateFailed=UpdateFailed, CoordinatorEntity=CoordinatorEntity)
    _mod("homeassistant.helpers.device_registry", DeviceInfo=dict)
    _mod("homeassistant.helpers.entity", EntityCategory=EntityCategory)
    _mod("homeassistant.helpers.entity_platform", AddEntitiesCallback=object)
    _mod("homeassistant.helpers.selector")
    _mod("homeassistant.components")
    _mod("homeassistant.components.sensor", SensorEntity=_Entity, RestoreSensor=RestoreSensor,
         SensorDeviceClass=SensorDeviceClass, SensorStateClass=SensorStateClass)
    _mod("homeassistant.components.binary_sensor", BinarySensorEntity=_Entity, BinarySensorDeviceClass=BinarySensorDeviceClass)
    _mod("homeassistant.components.switch", SwitchEntity=_Entity)
    _mod("homeassistant.components.select", SelectEntity=_Entity)
    _mod("homeassistant.components.number", NumberEntity=_Entity, RestoreNumber=RestoreNumber,
         NumberMode=NumberMode, NumberDeviceClass=NumberDeviceClass)
    _mod("homeassistant.components.button", ButtonEntity=_Entity)
    _mod("homeassistant.components.climate", ClimateEntity=_Entity, ClimateEntityFeature=ClimateEntityFeature,
         HVACMode=HVACMode, HVACAction=HVACAction, ATTR_TEMPERATURE="temperature")
