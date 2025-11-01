from __future__ import annotations

import asyncio
import contextlib
import json
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_UNIT_ID,
    CONF_SCAN_INTERVAL,
)

@dataclass
class RegisterDef:
    key: str
    name: str
    reg_type: str  # "holding" | "input"
    address: int
    scale: float | int | None = None
    unit: str | None = None
    min_value: float | int | None = None
    max_value: float | int | None = None
    step: float | int | None = None
    options: list[tuple[str, int]] | None = None  # for selects

class ED300Probe:
    @staticmethod
    async def async_test_connection(host: str, port: int, unit_id: int) -> None:
        client = AsyncModbusTcpClient(host=host, port=port, timeout=5)
        try:
            await client.connect()
            rr = await client.read_input_registers(address=8, count=1, unit=unit_id)
            if rr.isError():
                raise TimeoutError("Modbus error")
        finally:
            with contextlib.suppress(Exception):
                await client.close()

class ED300Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.host = entry.data[CONF_HOST]
        self.port = entry.data[CONF_PORT]
        self.unit_id = entry.data[CONF_UNIT_ID]
        self.scan_interval = entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, 30))

        super().__init__(
            hass,
            logger=hass.helpers.logger.logging.getLogger(DOMAIN),
            name="ED300 Modbus",
            update_interval=dt_util.timedelta(seconds=self.scan_interval),
        )

        self._client: AsyncModbusTcpClient | None = None
        self.device: dict[str, Any] = {"manufacturer": "EcoDesign", "model": "ED 300 WT"}
        self.registers: dict[str, list[RegisterDef]] = self._load_profile()

    async def async_config_entry_first_refresh(self) -> None:
        await self._ensure_client()
        await super().async_config_entry_first_refresh()

    async def _ensure_client(self) -> None:
        if self._client is None:
            self._client = AsyncModbusTcpClient(host=self.host, port=self.port, timeout=6)
            await self._client.connect()

    async def _async_update_data(self) -> dict[str, Any]:
        await self._ensure_client()
        data: dict[str, Any] = {}

        # Read all registers defined in profile
        for category in ("sensors", "numbers", "selects", "switches"):
            for r in self.registers.get(category, []):
                try:
                    if r.reg_type == "input":
                        rr = await self._client.read_input_registers(address=r.address, count=1, unit=self.unit_id)
                    else:
                        rr = await self._client.read_holding_registers(address=r.address, count=1, unit=self.unit_id)
                    if rr.isError():
                        raise ModbusException(str(rr))
                    val = rr.registers[0]
                    if r.scale:
                        val = val * r.scale
                    data[r.key] = val
                except Exception as err:  # noqa: BLE001
                    raise UpdateFailed(f"Failed reading {r.key}@{r.address}: {err}") from err

        return data

    async def async_write_register(self, address: int, value: int) -> None:
        await self._ensure_client()
        rr = await self._client.write_register(address=address, value=value, unit=self.unit_id)
        if rr.isError():
            raise ModbusException(str(rr))
        await self.async_request_refresh()

    async def async_close(self) -> None:
        if self._client is not None:
            with contextlib.suppress(Exception):
                await self._client.close()
            self._client = None

    def _load_profile(self) -> dict[str, list[RegisterDef]]:
        import importlib.resources as ir
        raw = ir.files(__package__).joinpath("profiles/ed300.json").read_text(encoding="utf-8")
        j = json.loads(raw)

        def to_defs(items: list[dict]) -> list[RegisterDef]:
            res: list[RegisterDef] = []
            for it in items:
                res.append(RegisterDef(
                    key=it["key"],
                    name=it.get("name", it["key"]),
                    reg_type=it.get("register_type", "holding"),
                    address=it["address"],
                    scale=it.get("scale"),
                    unit=it.get("unit"),
                    min_value=it.get("min"),
                    max_value=it.get("max"),
                    step=it.get("step"),
                    options=[tuple(o) for o in it.get("options", [])] or None,
                ))
            return res

        return {
            "sensors": to_defs(j["registers"].get("sensors", [])),
            "numbers": to_defs(j["registers"].get("numbers", [])),
            "selects": to_defs(j["registers"].get("selects", [])),
            "switches": to_defs(j["registers"].get("switches", [])),
            "climate": j["registers"].get("climate", {}),
        }
