# EcoDesign Heat Pumps (Modbus) — Home Assistant (HACS)

[![release](https://img.shields.io/badge/release-v0.1.0-blue)](https://github.com/neumeier-cloud/ha_ecodesign_heatpump/releases)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

A custom Home Assistant integration (HACS) to connect **EcoDesign heat pumps (ED 300 / WT / KWL variants)** via **Modbus TCP** (using an RS‑485↔IP gateway). Includes reading **input registers** and writing **holding registers** (e.g., setpoint, operating mode, PV/Smart-Grid mode, boost, etc.).

**Repository:** `neumeier-cloud/ha_ecodesign_heatpump`  
**Author:** Timo Neumeier <timo@neumeier.cloud> — *supported by AI*

---

## ✨ Features
- Async Modbus TCP (pymodbus 3.x)
- Entities: Sensors, Numbers (setpoints), Selects (modes), Switches (boost), optional Climate (DHW setpoint)
- Single **profile file** (`profiles/ed300.json`) that maps registers → entities (editable without touching code)
- **Config Flow**: host, port, unit id, scan interval
- Ready for **HACS** (custom repository)

## 🧰 Installation (via HACS — Custom Repository)
1. Install HACS (if not already installed).
2. In HACS → *Integrations* → *Custom repositories* add your repository URL:  
   `https://github.com/neumeier-cloud/ha_ecodesign_heatpump` (category: **Integration**).
3. Install **EcoDesign Wärmepumpen** and restart Home Assistant.
4. Go to *Settings → Devices & Services → Add Integration* and search for **EcoDesign Wärmepumpen**.

## 🔧 Configuration
- **Host/Port**: IP/Port of your RS‑485↔IP gateway (or controller if it exposes Modbus/TCP directly).
- **Unit ID**: Modbus address (often `3`, verify in your device).
- **Register profile**: default is `profiles/ed300.json`. Adjust addresses/scaling/options if your firmware differs.

### Modbus Register Context (from the device manual)
- **Holding (4x)**:  
  Setpoint (**4**), Tmin (**5**), T2min (**6**), **Operating mode** (**12**), **KWL fan mode** (**16**), **PV/Smart-Grid mode** (**17**), `T.PV_WP` (**18**), `T.PV_EL` (**19**), **Boost** (**22**), `Tmax` (**28**).
- **Input (3x)**:  
  Evaporator (**7**, ×0.1 °C), Tank/DHW (**8**, ×0.1 °C), relays (9–14), 0–10 V raw (15), status bits (16), remaining holiday days (17).

> The device speaks **Modbus RTU (RS‑485)**. Use a Modbus/TCP gateway for IP connectivity. Check polarity on CN11: Port 3 = B (−), Port 4 = A (+).

## 🖼️ Branding
- `assets/logo.png` — official brand wordmark (provided by customer).
- `assets/icon.png` — green leaves only (transparent 512×512).

## 📄 License
MIT

---

# 🇩🇪 Deutsch

Eine Home‑Assistant‑Integration (HACS) für **EcoDesign‑Wärmepumpen** via **Modbus TCP** (z. B. per RS‑485↔IP‑Gateway). Liest **Input‑Register** und schreibt **Holding‑Register** (Sollwert, Betriebsart, PV/Smart‑Grid‑Modus, Boost, …).

**Repository:** `neumeier-cloud/ha_ecodesign_heatpump`  
**Ersteller:** Timo Neumeier <timo@neumeier.cloud> — *supported by AI*

### Installation
1. HACS installieren.
2. HACS → *Integrations* → *Custom repositories* →  
   `https://github.com/neumeier-cloud/ha_ecodesign_heatpump` als **Integration** hinzufügen.
3. **EcoDesign Wärmepumpen** installieren, Home Assistant neu starten.
4. *Einstellungen → Geräte & Dienste → Integration hinzufügen* → **EcoDesign Wärmepumpen** auswählen.

### Konfiguration
- **Host/Port**: IP/Port deines RS‑485↔IP‑Gateways.  
- **Unit ID**: Modbus‑Adresse (häufig `3`, im Gerät prüfen).  
- **Registerprofil**: `profiles/ed300.json` (bei Firmware‑Abweichungen Adressen/Skalierung/Optionen anpassen).

### Modbus‑Register (Auszug aus Handbuch)
- **Holding (4x)**: T‑Soll (4), Tmin (5), T2min (6), **Betriebsart** (12), **KWL** (16), **PV‑Modus** (17), `T.PV_WP` (18), `T.PV_EL` (19), **Boost** (22), `Tmax` (28).  
- **Input (3x)**: Verdampfer (7, ×0,1 °C), Speicher (8, ×0,1 °C), Relais (9–14), 0–10 V (15), Statusbits (16), Resttage (17).

> Gerät spricht **Modbus RTU (RS‑485)**. Für IP: Modbus/TCP‑Gateway verwenden; Polung CN11 beachten (3 = B (−), 4 = A (+)).

### Branding
- `assets/logo.png` — offizieller Schriftzug.  
- `assets/icon.png` — nur die grünen Blätter (512×512, transparent).


## Troubleshooting
- After installing via HACS, **restart Home Assistant** so dependencies (pymodbus) are installed.
- If setup shows *Unknown error* during the form, try again after restart; this build now
  performs a raw TCP probe first and should display *cannot_connect* when the host/port is unreachable.
- Enable debug logs:
  ```yaml
  logger:
    default: warning
    logs:
      custom_components.ecodesign_heatpump: debug
      pymodbus: info
  ```
