# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a weather station project that collects and processes weather data via MQTT. The system consists of:

- **Data Sources**: Multiple sensors including weather meters and magnetic flux sensors
- **Communication**: MQTT-based messaging using topic structure `backacres/house/weatherstation/`
- **Data Types**:
  - Weather metrics (temperature, humidity, pressure, irradiance, wind, rain)
  - Magnetic flux sensor data (x, y, z coordinates)

## MQTT Topics Structure

The system uses a hierarchical MQTT topic structure:
- `backacres/house/weatherstation/weathermeters/` - Weather sensor data
- `backacres/house/weatherstation/magneticfluxsensor/` - Magnetic field measurements

## Development Environment

- **Python**: 3.12.6 with virtual environment in `./venv/`
- **MQTT Tools**: mosquitto_sub available at `/usr/bin/mosquitto_sub`

## Common Commands

### Environment Setup
```bash
# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# For GTK GUI support, install system dependencies:
sudo apt install libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0
pip install PyGObject
```

### Running the Application
```bash
# Start Tkinter GUI (recommended)
python weather_gui_tk.py

# Start daemon mode (background data collection)
python main.py --daemon

# Console mode (real-time display)
python main.py --console

# Silent daemon mode (no console output)
python main.py --daemon --silent

# Daemon mode with verbose logging
python main.py --daemon --verbose

# Specify MQTT broker
python main.py --host 192.168.1.100 --port 1883

# Custom database and log files
python main.py --daemon --db /path/to/weather.db --log /path/to/daemon.log

# GUI with custom database
python weather_gui_tk.py --db /path/to/weather.db
```

### Testing and Development
```bash
# Test all components
python test_components.py

# Test MQTT subscriber only
python mqtt_subscriber.py

# Subscribe to MQTT topics manually
./weathersub.sh
mosquitto_sub -v -t 'backacres/house/weatherstation/#'
```

## Data Format

Weather sensor data includes:
- `utc`: Unix timestamp
- `sampleinterval`: Sampling interval in milliseconds
- `temperature`: Temperature in Celsius
- `humidity`: Relative humidity percentage
- `pressure`: Atmospheric pressure in hPa
- `irradiance`: Solar irradiance
- `winddirectionsensor`: Wind direction sensor reading
- `raingaugecount`: Rain gauge count
- `anemometercount`: Anemometer count

Magnetic flux sensor data includes:
- `x`, `y`, `z`: Magnetic field coordinates (HMC5883L raw LSb values)

## Database Timezone Conventions

**All times in the database are stored in UTC.**

| Column | Format | Description |
|--------|--------|-------------|
| `timestamp` | Unix epoch (integer) | Sensor UTC time - preferred for queries |
| `created_at` | ISO datetime string | SQLite CURRENT_TIMESTAMP (UTC, no TZ marker) |

### Guidelines

1. **Storage:** Always store times in UTC
2. **Queries:** Use UTC times when querying `created_at` or comparing `timestamp`
3. **Display:** Convert to local time only at the presentation layer
4. **Prefer Unix timestamps:** They are unambiguous; use `datetime.fromtimestamp()` for auto-conversion to local

### Code Patterns

```python
from datetime import datetime, timezone

# Query with UTC times
end_utc = datetime.now(timezone.utc).replace(tzinfo=None)
start_utc = end_utc - timedelta(hours=1)
# Use start_utc, end_utc in WHERE created_at BETWEEN ? AND ?

# Display: Unix timestamp to local time
local_time = datetime.fromtimestamp(row[0])  # Automatic UTC->local

# Display: created_at (UTC string) to local time
utc_time = datetime.fromisoformat(created_at_str).replace(tzinfo=timezone.utc)
local_time = utc_time.astimezone().replace(tzinfo=None)
```

See `TIMEZONE_BUG_LESSONS_LEARNED.md` for detailed analysis of timezone handling issues.

## Recent Enhancements (Latest Session)

### NIST SP 330 Compliance & HMC5883L Calibration
- **Standards Implementation**: Full NIST Special Publication 330 (SI units) compliance
- **HMC5883L Integration**: Automatic calibration based on Honeywell datasheet specifications
- **Calibration Values**: 9.174×10⁻⁸ T/LSb (derived from 1090 LSb/Gauss × 10000 Gauss/Tesla)
- **Cross-tool Integration**: Same calibration file used by GUI and 3D plotter
- **File**: `weather_station_calibration.json` - persistent calibration storage

### Performance Optimizations
- **Intelligent Sampling**: Automatic data sampling for large datasets (>2000 points)
- **Background Processing**: Non-blocking chart updates using threading
- **Data Caching**: 30-second cache for repeated queries
- **Database Optimization**: SQL-level row sampling with ROW_NUMBER()
- **Performance Gains**: 10-50x faster for large date ranges, no GUI freezing

### GUI Enhancements
- **Calibration Window**: Resizable 700px width, organized magnetic flux parameter layout
- **Chart Selection**: Enhanced chart selection with improved layout
- **Date Range Performance**: Optimized for ranges from minutes to months
- **Status Indicators**: Real-time feedback during chart generation

### 3D Magnetic Flux Visualization
- **Automatic Calibration**: Loads calibration from weather_station_calibration.json
- **5 Plot Types**: 3D vectors, magnitude/time, direction analysis, 3D trajectory, 2D polar
- **2D Polar Charts**: XY plane analysis with compass orientation and time coloring
- **NIST Compliance**: All plots use calibrated Tesla values, displayed in microtesla
- **Performance**: Intelligent sampling for large datasets

### Key Files Modified
- `weather_gui_tk.py`: Performance optimizations, magnetic flux calibration UI
- `database.py`: Added sampling and limits to data range queries
- `magnetic_flux_3d_plotter.py`: Calibration integration, updated plot labels
- `README.md`: Comprehensive documentation updates
- `asd2613-r.pdf`: HMC5883L datasheet used for calibration factors

### Command Examples
```bash
# GUI with performance optimizations
python weather_gui_tk.py

# 3D plotter with automatic calibration
python magnetic_flux_3d_plotter.py --hours 24 --plots polar

# Test calibration integration
python -c "import json; print(json.load(open('weather_station_calibration.json'))['calibration'])"
```