from __future__ import annotations

import asyncio
from typing import Any
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_UNIT_ID,
    CONF_SCAN_INTERVAL,
    CONF_MODEL,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_MODEL,
)

_LOGGER = logging.getLogger(__name__)

async def _probe_tcp(host: str, port: int) -> None:
    """Raw TCP connect test to avoid dependency timing issues."""
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=5.0)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # pragma: no cover
            pass
    except Exception as err:
        # Re-raise for caller to map to cannot_connect
        raise asyncio.TimeoutError(str(err))

class ED300ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 0

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            unit_id = user_input[CONF_UNIT_ID]
            try:
                await _probe_tcp(host, port)
            except asyncio.TimeoutError as err:
                _LOGGER.warning("TCP probe failed %s:%s -> %s", host, port, err)
                errors["base"] = "cannot_connect"
            except Exception as err:  # ultra safe
                _LOGGER.exception("Unexpected error during config flow probe: %s", err)
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"{host}:{port}:{unit_id}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"ED300 @ {host}", data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
            vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): int,
            vol.Optional(CONF_MODEL, default=DEFAULT_MODEL): vol.In(["ED300"]),
            vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(int, vol.Range(min=5, max=600)),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @callback
    def async_get_options_flow(self, config_entry: config_entries.ConfigEntry):
        return ED300OptionsFlow(config_entry)

class ED300OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data = {**self._entry.data, **(self._entry.options or {})}
        schema = vol.Schema({
            vol.Optional(CONF_SCAN_INTERVAL, default=data.get("scan_interval", DEFAULT_SCAN_INTERVAL)): vol.All(int, vol.Range(min=5, max=600)),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
