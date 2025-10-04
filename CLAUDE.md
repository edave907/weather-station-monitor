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
- `x`, `y`, `z`: Magnetic field coordinates