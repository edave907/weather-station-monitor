# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Weather station monitoring system that collects sensor data via MQTT, stores it in SQLite, and provides visualization through a Tkinter GUI. Sensors include weather meters (temperature, humidity, pressure, irradiance, wind, rain) and an HMC5883L magnetometer.

## Architecture

```
┌─────────────────┐     MQTT      ┌──────────────────┐     SQLite     ┌─────────────────┐
│  ESP32 Sensors  │──────────────>│  weather_daemon  │───────────────>│  weather_data.db│
│  (weathermeters,│               │  (mqtt_subscriber│                │                 │
│   magnetometer) │               │   + database.py) │                └────────┬────────┘
└─────────────────┘               └──────────────────┘                         │
                                                                               │ reads
                                                                               ▼
                                                               ┌───────────────────────────┐
                                                               │  weather_gui_tk.py        │
                                                               │  (Tkinter + matplotlib)   │
                                                               │  magnetic_flux_3d_plotter │
                                                               └───────────────────────────┘
```

**Key modules:**
- `database.py` - SQLite interface with `weather_data` and `magnetic_flux_data` tables
- `mqtt_subscriber.py` - Paho MQTT client subscribing to `backacres/house/weatherstation/#`
- `weather_daemon.py` - Production daemon with signal handling, logging, PID file management
- `weather_gui_tk.py` - Read-only GUI (decoupled from backend), includes calibration UI
- `magnetic_flux_3d_plotter.py` - 3D visualization with polar/trajectory plots

## Common Commands

```bash
# Environment
source venv/bin/activate
pip install -r requirements.txt

# GUI (recommended for development)
python weather_gui_tk.py
python weather_gui_tk.py --db /path/to/weather.db

# Testing
python test_components.py
python mqtt_subscriber.py  # Test MQTT only

# Daemon management (production runs via systemd)
sudo systemctl status weather-daemon
sudo systemctl restart weather-daemon
journalctl -u weather-daemon -f

# MQTT debugging
mosquitto_sub -v -t 'backacres/house/weatherstation/#'

# 3D magnetic flux plots
python magnetic_flux_3d_plotter.py --hours 24 --plots polar
```

## Database

Production database: `/deepsink1/weatherstation/data/weather_data.db`

**All times stored in UTC:**
- `timestamp` - Unix epoch (preferred for queries)
- `created_at` - ISO datetime string (UTC, no TZ marker)

**Timezone handling pattern:**
```python
from datetime import datetime, timezone, timedelta

# Query with UTC times
end_utc = datetime.now(timezone.utc).replace(tzinfo=None)
start_utc = end_utc - timedelta(hours=1)
# Use in WHERE created_at BETWEEN ? AND ?

# Display: Unix timestamp to local time
local_time = datetime.fromtimestamp(row[0])  # Automatic UTC->local

# Display: created_at (UTC string) to local time
utc_time = datetime.fromisoformat(created_at_str).replace(tzinfo=timezone.utc)
local_time = utc_time.astimezone().replace(tzinfo=None)
```

See `TIMEZONE_BUG_LESSONS_LEARNED.md` for detailed analysis.

## Calibration

Sensor calibrations stored in `weather_station_calibration.json`, shared between GUI and 3D plotter.

**HMC5883L magnetometer:**
- Scale: 9.174×10⁻⁸ T/LSb (from 1090 LSb/Gauss per Honeywell datasheet)
- Raw values in LSb → converted to Tesla (displayed as μT)

## MQTT Topics

- `backacres/house/weatherstation/weathermeters/` - Weather data (JSON with utc, temperature, humidity, pressure, irradiance, winddirectionsensor, raingaugecount, anemometercount)
- `backacres/house/weatherstation/magneticfluxsensor/` - Magnetic flux (JSON with x, y, z in raw LSb)

## Virtual Observatory

The `virtual_observatory/` module provides spatial interpolation to create synthetic observatory data by combining local measurements with USGS/INTERMAGNET reference stations. Used for validation against known geomagnetic observatories.
