# Weather Station Monitor

A Python application that subscribes to MQTT weather data, stores it in a SQLite database, and displays real-time data using either GTK GUI or console interface.

## Features

- **MQTT Integration**: Subscribes to weather station topics on localhost
- **Database Storage**: Stores weather and magnetic flux sensor data in SQLite
- **Real-time Display**: Shows current weather conditions with automatic updates
- **Dual Interface**: GTK GUI or console-based display
- **Flexible Configuration**: Configurable MQTT broker and database settings

## Quick Start

1. **Install Dependencies**:
   ```bash
   # Activate virtual environment
   source venv/bin/activate

   # Install Python packages
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   # Console mode (always works)
   python main.py --console

   # GTK GUI mode (if GTK available)
   python main.py
   ```

3. **Test Components**:
   ```bash
   python test_components.py
   ```

## GUI Options

### Option 1: Tkinter GUI (Recommended)

Tkinter is included with Python and requires no system dependencies:

```bash
# Run Tkinter GUI (works with virtual environment)
python weather_gui_tk.py

# Or use the launcher script
python run_gui_tk.py

# Specify custom database
python weather_gui_tk.py --db /path/to/weather.db
```

**Tkinter GUI Features:**
- Real-time weather data display
- Interactive charts (temperature, humidity, pressure)
- Auto-refresh every 30 seconds
- Quick time ranges (30min to 7 days)
- **Custom date/time range picker** - view any historical period
- Date picker with calendar widget
- Smart chart formatting for different time spans
- Database statistics
- Completely decoupled from backend

### Option 2: GTK GUI (Advanced)

For GTK interface with system Python:

```bash
# Install GTK system dependencies
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0

# Install packages for system Python 3.11
/usr/bin/python3.11 -m pip install --user paho-mqtt matplotlib numpy

# Run GTK GUI
/usr/bin/python3.11 run_gui.py
```

### Option 3: Console Mode

```bash
# Real-time console display
python main.py --console
```

## Historical Data Analysis

The Tkinter GUI includes powerful date range selection for viewing historical data:

### Quick Ranges
- 30 Minutes, 1 Hour, 6 Hours, 24 Hours, 7 Days
- Perfect for recent data analysis

### Custom Date Ranges
- **Calendar date picker** for easy date selection
- **Time specification** (HH:MM format) for precise ranges
- **Flexible periods** - view any time span from minutes to months
- **Smart formatting** - charts automatically adapt to time span
- **Validation** - prevents invalid date ranges

### Usage Examples
```bash
# View data from yesterday 9 AM to 5 PM
1. Check "Use custom range"
2. Set From: 2025-10-02 09:00
3. Set To: 2025-10-02 17:00
4. Click "Apply Range"

# Analyze last week's weather patterns
1. Use Quick Range: "7 Days"
2. Charts update automatically

# Compare specific dates
1. Enable custom range
2. Select start/end dates with calendar
3. Fine-tune with time fields
```

## Usage Examples

```bash
# Start Tkinter GUI
python weather_gui_tk.py

# Start daemon mode
python main.py --daemon

# Start console mode
python main.py --console

# Run in daemon mode (background, console logging)
python main.py --daemon

# Daemon mode with verbose logging
python main.py --daemon --verbose

# Silent daemon mode (no console output, file logging only)
python main.py --daemon --silent

# Connect to remote MQTT broker
python main.py --host 192.168.1.100 --port 1883

# Use custom database and log files
python main.py --daemon --db /path/to/custom.db --log /path/to/daemon.log

# Show help
python main.py --help
```

## Daemon Mode

For long-term data collection without any display interface:

```bash
# Run daemon in foreground with console output (testing)
python main.py --daemon

# Run silent daemon in background (production)
nohup python main.py --daemon --silent > /dev/null 2>&1 &

# Or use the silent flag for truly background operation
python main.py --daemon --silent

# Check daemon logs
tail -f weather_daemon.log

# Kill background daemon
pkill -f "python main.py --daemon"
```

### Systemd Service (Recommended)

For automatic startup and management:

1. **Copy service file**:
   ```bash
   sudo cp systemd/weather-daemon.service /etc/systemd/system/
   sudo systemctl daemon-reload
   ```

2. **Enable and start service**:
   ```bash
   sudo systemctl enable weather-daemon
   sudo systemctl start weather-daemon
   ```

3. **Check service status**:
   ```bash
   sudo systemctl status weather-daemon
   journalctl -u weather-daemon -f
   ```

### Daemon Features

- **Silent Operation**: No display output, only file logging
- **Automatic Reconnection**: Handles MQTT connection failures
- **Statistics Logging**: Periodic status reports every 5 minutes
- **Graceful Shutdown**: Proper cleanup on SIGTERM/SIGINT
- **File Logging**: All activity logged to `weather_daemon.log`
- **Log Rotation**: Built-in support for logrotate integration
- **PID Management**: Creates PID file for process management

### Log Rotation Setup

To prevent log files from growing too large:

```bash
# Install logrotate configuration
./setup_logrotate.sh

# Manual log rotation (for testing)
sudo logrotate -f /etc/logrotate.d/weather-daemon

# Check logrotate status
sudo cat /var/lib/logrotate/status | grep weather
```

**Log Rotation Features:**
- Daily rotation
- Keep 30 days of compressed logs
- Signal daemon to reopen log file (USR1)
- Graceful handling of missing log files

## Data Sources

The application subscribes to these MQTT topics:

- `backacres/house/weatherstation/weathermeters/` - Weather sensor data
- `backacres/house/weatherstation/magneticfluxsensor/` - Magnetic field measurements

### Weather Data Format
```json
{
  "utc": 1759479845,
  "sampleinterval": 5000,
  "temperature": 5.22,
  "humidity": 61.5,
  "pressure": 1004.94,
  "irradiance": 0.83,
  "winddirectionsensor": 96,
  "raingaugecount": 170,
  "anemometercount": 1047952
}
```

### Magnetic Flux Data Format
```json
{
  "x": 1115,
  "y": -558,
  "z": -305
}
```

## File Structure

- `main.py` - Main application entry point
- `database.py` - SQLite database interface
- `mqtt_subscriber.py` - MQTT client for data collection
- `weather_gui.py` - GTK GUI and console display
- `test_components.py` - Component testing script
- `requirements.txt` - Python dependencies
- `CLAUDE.md` - Development guidance

## Requirements

- Python 3.12+
- MQTT broker running on localhost (e.g., Mosquitto)
- SQLite (included with Python)
- Optional: GTK 3.0 for graphical interface

## Measurement Standards and Units

This project adheres to **NIST Special Publication 330** (The International System of Units - SI) for all measurement units and calibrations.

### SI Base Units Used

| Measurement | SI Unit | Symbol | Notes |
|-------------|---------|--------|-------|
| **Temperature** | Kelvin | K | Displayed as Celsius (°C) for user convenience |
| **Time** | Second | s | Used for all time intervals and calculations |
| **Length** | Meter | m | For wind speed calculations (m/s) |
| **Mass** | Kilogram | kg | For pressure calculations via Pascal (kg⋅m⁻¹⋅s⁻²) |

### Derived SI Units

| Measurement | SI Unit | Symbol | Formula | Display Units |
|-------------|---------|--------|---------|---------------|
| **Wind Speed** | Meter per second | m/s | m⋅s⁻¹ | m/s or km/h (3.6 × m/s) |
| **Pressure** | Pascal | Pa | kg⋅m⁻¹⋅s⁻² | hPa (hectopascal) |
| **Magnetic Flux Density** | Tesla | T | kg⋅s⁻²⋅A⁻¹ | μT (microtesla) for earth field |

### Calibration Standards

All sensor calibration functions convert raw sensor readings to proper SI units:

- **Anemometer**: Calibration converts count deltas to meters per second (m/s)
- **Pressure Sensor**: Calibration ensures readings are in Pascal (Pa)
- **Temperature Sensor**: Calibration provides Kelvin (K), displayed as Celsius
- **Magnetometer**: Calibration converts to Tesla (T)
- **Rain Gauge**: Calibration converts counts to millimeters (mm) of precipitation

### Calibration Persistence

Sensor calibrations are automatically saved to `weather_station_calibration.json` and persist across application restarts. The file contains:

- **Metadata**: Version, creation date, and description
- **Calibration Values**: All sensor calibration parameters in SI units
- **Automatic Backup**: Values are saved each time calibrations are updated

If the calibration file is missing or corrupted, the application automatically uses safe default values.

**Reference**: NIST Special Publication 330 (2019 Edition)
**Standard**: International System of Units (SI) as adopted by the 26th General Conference on Weights and Measures (2018)

## Troubleshooting

**MQTT Connection Failed**:
- Ensure Mosquitto broker is running: `sudo systemctl start mosquitto`
- Check firewall settings
- Verify broker host/port settings

**GTK Not Available**:
- The application automatically falls back to console mode
- Install system GTK packages as shown above

**Database Errors**:
- Check file permissions in the working directory
- Ensure sufficient disk space