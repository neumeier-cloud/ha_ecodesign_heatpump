from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ED300Coordinator, RegisterDef

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: ED300Coordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ED300Sensor] = []
    for r in coordinator.registers.get("sensors", []):
        entities.append(ED300Sensor(coordinator, r))
    async_add_entities(entities)

class ED300Sensor(CoordinatorEntity[ED300Coordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: ED300Coordinator, reg: RegisterDef) -> None:
        super().__init__(coordinator)
        self.reg = reg
        self._attr_name = reg.name
        self._attr_unique_id = f"{coordinator.host}-{coordinator.unit_id}-sensor-{reg.key}"
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
