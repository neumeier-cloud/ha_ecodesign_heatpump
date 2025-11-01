from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ED300Coordinator, RegisterDef

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: ED300Coordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ED300Switch] = []
    for r in coordinator.registers.get("switches", []):
        entities.append(ED300Switch(coordinator, r))
    async_add_entities(entities)

class ED300Switch(CoordinatorEntity[ED300Coordinator], SwitchEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: ED300Coordinator, reg: RegisterDef) -> None:
        super().__init__(coordinator)
        self.reg = reg
        self._attr_name = reg.name
        self._attr_unique_id = f"{coordinator.host}-{coordinator.unit_id}-switch-{reg.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{coordinator.host}:{coordinator.unit_id}")},
            "manufacturer": coordinator.device["manufacturer"],
            "model": coordinator.device["model"],
            "name": "EcoDesign ED300",
        }

    @property
    def is_on(self) -> bool | None:
        val = self.coordinator.data.get(self.reg.key)
        return bool(int(val)) if val is not None else None

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_write_register(self.reg.address, 1)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_write_register(self.reg.address, 0)
