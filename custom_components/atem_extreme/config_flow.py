"""Config flow for the ATEM Extreme integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .atem.client import AtemClient, AtemConnectionError, SwitcherFullyBooked
from .const import (
    CONF_HOST,
    CONF_METER_HZ,
    CONF_PORT,
    DEFAULT_METER_HZ,
    DEFAULT_PORT,
    DOMAIN,
    METER_HZ_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_METER_HZ, default=DEFAULT_METER_HZ): vol.In(METER_HZ_OPTIONS),
    }
)


async def _probe(host: str, port: int) -> str:
    client = AtemClient(host, port)
    try:
        await client.start()
        await client.wait_until_ready(8)
        return client.state.product_name or host
    finally:
        await client.stop()


class AtemConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for the switcher's IP and confirm it answers the ATEM handshake."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            port = int(user_input[CONF_PORT])
            hz = int(user_input[CONF_METER_HZ])
            if not host or not (1 <= port <= 65535):
                errors["base"] = "invalid_host"
            else:
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()
                try:
                    title = await _probe(host, port)
                except SwitcherFullyBooked:
                    errors["base"] = "fully_booked"
                except (AtemConnectionError, TimeoutError, OSError):
                    errors["base"] = "cannot_connect"
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Unexpected error probing %s", host)
                    errors["base"] = "unknown"
                else:
                    return self.async_create_entry(
                        title=title,
                        data={
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_METER_HZ: hz,
                        },
                    )
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return AtemOptionsFlow()


class AtemOptionsFlow(OptionsFlow):
    """Change how often audio meters are published to Home Assistant."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=dict(user_input))
        current = self.config_entry.options.get(
            CONF_METER_HZ, self.config_entry.data.get(CONF_METER_HZ, DEFAULT_METER_HZ)
        )
        schema = vol.Schema(
            {vol.Required(CONF_METER_HZ, default=current): vol.In(METER_HZ_OPTIONS)}
        )
        return self.async_show_form(step_id="init", data_schema=schema)
