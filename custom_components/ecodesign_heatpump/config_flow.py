from __future__ import annotations

import asyncio
from typing import Any

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

async def _probe_modbus_tcp(host: str, port: int, unit_id: int) -> None:
    """Try to connect to Modbus TCP endpoint.

    We import pymodbus lazily here to avoid import errors before HA restarts.
    If pymodbus is not yet available, we still do a raw TCP probe to ensure
    at least the socket is reachable.
    """
    try:
        from pymodbus.client import AsyncModbusTcpClient  # type: ignore
    except Exception:
        # fallback: raw TCP connect with asyncio open_connection
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=5.0)
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
        except Exception as err:
            raise asyncio.TimeoutError(str(err))
    else:
        client = AsyncModbusTcpClient(host=host, port=port, timeout=5)
        try:
            await client.connect()
            # minimal read to validate slave answers; some gateways allow 0-count illegal,
            # so we read 1 input register at address 0 safely guarded.
            rr = await client.read_input_registers(address=0, count=1, unit=unit_id)
            if rr.isError():  # device could still be fine; connectivity is proven
                return
        finally:
            try:
                await client.close()
            except Exception:
                pass


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
                await _probe_modbus_tcp(host, port, unit_id)
            except asyncio.TimeoutError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
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
