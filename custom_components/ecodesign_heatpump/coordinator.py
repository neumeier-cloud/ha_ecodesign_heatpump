from __future__ import annotations
import contextlib
import logging
from typing import Any
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

_LOGGER = logging.getLogger(__name__)

class ED300Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    ...
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
