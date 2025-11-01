from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ED300Coordinator, RegisterDef

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: ED300Coordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ED300Number] = []
    for r in coordinator.registers.get("numbers", []):
        entities.append(ED300Number(coordinator, r))
    async_add_entities(entities)

class ED300Number(CoordinatorEntity[ED300Coordinator], NumberEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: ED300Coordinator, reg: RegisterDef) -> None:
        super().__init__(coordinator)
        self.reg = reg
        self._attr_name = reg.name
        self._attr_unique_id = f"{coordinator.host}-{coordinator.unit_id}-number-{reg.key}"
        self._attr_native_min_value = reg.min_value if reg.min_value is not None else 0
        self._attr_native_max_value = reg.max_value if reg.max_value is not None else 100
        self._attr_native_step = reg.step if reg.step is not None else 1
        self._attr_native_unit_of_measurement = reg.unit
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{coordinator.host}:{coordinator.unit_id}")},
            "manufacturer": coordinator.device["manufacturer"],
            "model": coordinator.device["model"],
            "name": "EcoDesign ED300",
        }

    @property
    def native_value(self):
        return self.coordinator.data.get(self.reg.key)

    async def async_set_native_value(self, value: float) -> None:
        raw = int(round(value / (self.reg.scale or 1)))
        await self.coordinator.async_write_register(self.reg.address, raw)
