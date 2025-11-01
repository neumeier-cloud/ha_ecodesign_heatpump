from __future__ import annotations

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import HVACMode, ClimateEntityFeature
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ED300Coordinator

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: ED300Coordinator = hass.data[DOMAIN][entry.entry_id]
    c = coordinator.registers.get("climate") or {}
    if c:
        async_add_entities([ED300Climate(coordinator, c)])

class ED300Climate(CoordinatorEntity[ED300Coordinator], ClimateEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: ED300Coordinator, cfg: dict) -> None:
        super().__init__(coordinator)
        self.cfg = cfg
        self._attr_name = cfg.get("name", "Warmwasser")
        self._attr_unique_id = f"{coordinator.host}-{coordinator.unit_id}-climate-{cfg.get('key','wh')}"
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
        self._attr_min_temp = float(cfg.get("min_temp", 5))
        self._attr_max_temp = float(cfg.get("max_temp", 62))
        self._attr_precision = float(cfg.get("precision", 1))
        self.setpoint_register = int(cfg["setpoint_register"])  # holding
        self.current_temp_key = cfg.get("current_temp_key", "ww_temp")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{coordinator.host}:{coordinator.unit_id}")},
            "manufacturer": coordinator.device["manufacturer"],
            "model": coordinator.device["model"],
            "name": "EcoDesign ED300",
        }

    @property
    def hvac_mode(self):
        tt = self.target_temperature
        return HVACMode.OFF if (tt is None or tt < 5) else HVACMode.HEAT

    @property
    def target_temperature(self):
        return self.coordinator.data.get("setpoint")

    @property
    def current_temperature(self):
        return self.coordinator.data.get(self.current_temp_key)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.async_write_register(self.setpoint_register, 0)
        else:
            return

    async def async_set_temperature(self, **kwargs) -> None:
        value = kwargs.get("temperature")
        if value is None:
            return
        raw = int(round(value / 1))
        await self.coordinator.async_write_register(self.setpoint_register, raw)
