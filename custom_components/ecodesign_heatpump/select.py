from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ED300Coordinator, RegisterDef

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: ED300Coordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ED300Select] = []
    for r in coordinator.registers.get("selects", []):
        entities.append(ED300Select(coordinator, r))
    async_add_entities(entities)

class ED300Select(CoordinatorEntity[ED300Coordinator], SelectEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: ED300Coordinator, reg: RegisterDef) -> None:
        super().__init__(coordinator)
        self.reg = reg
        self._attr_name = reg.name
        self._attr_unique_id = f"{coordinator.host}-{coordinator.unit_id}-select-{reg.key}"
        self._attr_options = [label for label, _ in (reg.options or [])]
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{coordinator.host}:{coordinator.unit_id}")},
            "manufacturer": coordinator.device["manufacturer"],
            "model": coordinator.device["model"],
            "name": "EcoDesign ED300",
        }

    @property
    def current_option(self) -> str | None:
        val = self.coordinator.data.get(self.reg.key)
        if val is None:
            return None
        for label, code in (self.reg.options or []):
            if code == int(val):
                return label
        return None

    async def async_select_option(self, option: str) -> None:
        mapping = dict(self.reg.options or [])
        code = mapping.get(option)
        if code is None:
            raise ValueError("invalid option")
        await self.coordinator.async_write_register(self.reg.address, int(code))
