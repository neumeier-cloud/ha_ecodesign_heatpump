# Changelog

## [0.1.0] - 2025-11-01
### Added
- Initial public release of **EcoDesign Heat Pumps (Modbus)** for Home Assistant (HACS).
- Async Modbus TCP client using `pymodbus` 3.x.
- Entities: sensors, numbers (setpoints), selects (modes), switches (boost), optional climate (DHW setpoint).
- Config Flow (host, port, unit id, scan interval).
- Register mapping profile at `custom_components/ecodesign_waermepumpen/profiles/ed300.json`.
- Translations: English (`en.json`) and German (`de.json`).
- Branding assets: `assets/logo.png`, `assets/icon.png`.

### Notes
- Device uses Modbus RTU (RS-485); connect via Modbus/TCP gateway.
- Register addresses may differ by firmware; adjust the profile as needed.
