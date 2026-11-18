"""Config flow for Kronoterm KSM."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_PROTOCOL,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    CONF_THERMAL_MULTIPLIER,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    DEFAULT_THERMAL_MULTIPLIER,
    DOMAIN,
    PROBE_ADDRESS,
)
from .modbus import PROTOCOL_RTU_OVER_TCP, PROTOCOL_TCP, KronotermModbusClient, ModbusError

_LOGGER = logging.getLogger(__name__)


def _user_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=65535)
            ),
            vol.Required(CONF_PROTOCOL, default=defaults.get(CONF_PROTOCOL, PROTOCOL_RTU_OVER_TCP)): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[PROTOCOL_RTU_OVER_TCP, PROTOCOL_TCP],
                    translation_key="protocol",
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Required(CONF_SLAVE_ID, default=defaults.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=247)
            ),
        }
    )


async def _probe(data: dict[str, Any]) -> None:
    client = KronotermModbusClient(data[CONF_HOST], data[CONF_PORT], data[CONF_SLAVE_ID], data[CONF_PROTOCOL])
    try:
        await client.read_holding(PROBE_ADDRESS, 1)
    finally:
        await client.close()


class KronotermConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}:{user_input[CONF_SLAVE_ID]}"
            )
            self._abort_if_unique_id_configured()
            try:
                await _probe(user_input)
            except ModbusError as err:
                _LOGGER.debug("Connection test failed: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during connection test")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="Kronoterm", data=user_input)
        return self.async_show_form(
            step_id="user", data_schema=_user_schema(user_input or {}), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return KronotermOptionsFlow()


class KronotermOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL, default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
                vol.Required(
                    CONF_THERMAL_MULTIPLIER,
                    default=options.get(CONF_THERMAL_MULTIPLIER, DEFAULT_THERMAL_MULTIPLIER),
                ): vol.All(vol.Coerce(float), vol.Range(min=0.001, max=1000)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
