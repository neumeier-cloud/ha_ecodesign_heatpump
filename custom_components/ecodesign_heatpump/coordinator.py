from __future__ import annotations

import contextlib
import json
import logging
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Iterable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import (
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_ID,
    DEFAULT_MODEL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UNIT_ID,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class RegisterDef:
    """Light-weight description of a single Modbus register."""

    key: str
    name: str
    reg_type: str
    address: int
    scale: float | None = None
    unit: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    options: list[tuple[str, int]] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegisterDef:
        """Create a :class:`RegisterDef` from the JSON profile description."""

        raw_options = data.get("options") or []
        options: list[tuple[str, int]] | None
        if raw_options:
            options = [(str(label), int(code)) for label, code in raw_options]
        else:
            options = None

        def _to_float(value: Any | None) -> float | None:
            return float(value) if value is not None else None

        scale = data.get("scale")
        if scale is not None:
            try:
                scale = float(scale)
            except (TypeError, ValueError):  # pragma: no cover - defensive
                scale = None

        return cls(
            key=str(data["key"]),
            name=str(data.get("name", data["key"])),
            reg_type=str(data.get("register_type", "holding")),
            address=int(data["address"]),
            scale=scale,
            unit=data.get("unit"),
            min_value=_to_float(data.get("min")),
            max_value=_to_float(data.get("max")),
            step=_to_float(data.get("step")),
            options=options,
        )


class ED300Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Central Modbus coordinator for the EcoDesign ED300 device."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry

        config: dict[str, Any] = {**entry.data, **(entry.options or {})}
        self.host: str = config.get(CONF_HOST) or entry.data[CONF_HOST]
        self.port: int = int(config.get(CONF_PORT, DEFAULT_PORT))
        self.unit_id: int = int(config.get(CONF_UNIT_ID, DEFAULT_UNIT_ID))
        self.model: str = str(config.get(CONF_MODEL, DEFAULT_MODEL))
        scan_interval = int(config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

        profile = self._load_profile(self.model)
        device = profile.get("device", {})
        self.device: dict[str, Any] = {
            "manufacturer": device.get("manufacturer"),
            "model": device.get("model"),
        }

        self.registers: dict[str, Any] = {}
        raw_registers: dict[str, Any] = profile.get("registers", {})
        for category in ("sensors", "numbers", "selects", "switches"):
            items = raw_registers.get(category, [])
            self.registers[category] = [RegisterDef.from_dict(item) for item in items]
        if "climate" in raw_registers:
            self.registers["climate"] = raw_registers["climate"]

        self._client: AsyncModbusTcpClient | None = None
        self._registers_by_address: dict[int, list[RegisterDef]] = {}
        for reg in self._iter_all_registers(("sensors", "numbers", "selects", "switches")):
            self._registers_by_address.setdefault(reg.address, []).append(reg)

        super().__init__(
            hass,
            _LOGGER,
            name=f"EcoDesign ED300 ({self.host})",
            update_interval=timedelta(seconds=scan_interval),
        )

    def _iter_all_registers(self, categories: Iterable[str]) -> Iterable[RegisterDef]:
        for category in categories:
            for reg in self.registers.get(category, []):
                yield reg

    def _load_profile(self, model: str) -> dict[str, Any]:
        """Load the integration profile for the configured model."""

        filename = f"{model.lower()}.json"
        profile_path = Path(__file__).resolve().parent / "profiles" / filename
        if not profile_path.exists():
            raise FileNotFoundError(f"Unknown EcoDesign profile '{model}' ({profile_path})")

        with profile_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    async def async_write_register(self, address: int, value: int) -> None:
        """Write a Modbus holding register and update cached coordinator data."""

        await self._ensure_client()
        assert self._client is not None  # for mypy/static linters

        _LOGGER.debug("Writing register @%s = %s (unit=%s)", address, value, self.unit_id)
        result = await self._client.write_register(address=address, value=value, unit=self.unit_id)
        if result.isError():
            raise ModbusException(str(result))

        if self.data is None:
            current: dict[str, Any] = {}
        else:
            current = dict(self.data)

        for reg in self._registers_by_address.get(address, []):
            new_value: Any = value
            if reg.scale:
                try:
                    new_value = value * reg.scale
                except TypeError:  # pragma: no cover - defensive
                    new_value = value
            current[reg.key] = new_value

        if current:
            self.async_set_updated_data(current)

        await self.async_request_refresh()

    async def _ensure_client(self) -> None:
        if self._client is None:
            self._client = AsyncModbusTcpClient(host=self.host, port=self.port, timeout=6)
        if not self._client.connected:
            await self._client.connect()

    async def _async_update_data(self) -> dict[str, Any]:
        await self._ensure_client()
        data: dict[str, Any] = {}
        ok_reads = 0
        errors = 0

        async def _read(reg) -> int | None:
            try:
                if reg.reg_type == "input":
                    rr = await self._client.read_input_registers(address=reg.address, count=1, unit=self.unit_id)
                else:
                    rr = await self._client.read_holding_registers(address=reg.address, count=1, unit=self.unit_id)
                if rr.isError():
                    raise ModbusException(str(rr))
                return rr.registers[0]
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Read failed for %s @%s: %s", reg.key, reg.address, err)
                return None

        # read sensors/numbers/selects/switches gracefully
        for category in ("sensors", "numbers", "selects", "switches"):
            for r in self.registers.get(category, []):
                val = await _read(r)
                if val is None:
                    errors += 1
                    continue
                if getattr(r, "scale", None):
                    try:
                        val = val * r.scale  # type: ignore[operator]
                    except Exception:
                        pass
                data[r.key] = val
                ok_reads += 1

        if ok_reads == 0:
            # Keine brauchbaren Daten – aber: NICHT crashen, leer zurückgeben.
            _LOGGER.warning("No registers could be read (host=%s port=%s unit=%s)", self.host, self.port, self.unit_id)

        return data

    async def async_close(self) -> None:
        if self._client is not None:
            with contextlib.suppress(Exception):
                await self._client.close()
            self._client = None
